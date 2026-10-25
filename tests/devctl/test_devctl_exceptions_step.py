"""The exceptions step: each suppression has exactly one listed, current exception."""

from __future__ import annotations

from pathlib import Path

import pytest

import devctl
from check_workspace import Workspace
from devctl.check.exceptions import ExceptionsStep, normal_rule, scan
from devctl.check.steps import StepResult

ENTRY = """
[[exception]]
id = "{id}"
path = "{path}"
rule = "{rule}"
reason = "Runs the build tool with fixed arguments"
remove_when = "The build tool has a Python API"
"""
KIT_FILE_LOCK = (
    'kit_version = "0.2.0"\nstack = "python"\n\n[[file]]\n'
    'path = "tools/devctl/devctl/run.py"\nkind = "managed"\nsha256 = "' + "a" * 64 + '"\n'
)


def setup(
    workspace: Workspace, source: str, *entries: tuple[str, str, str], version: str = "0.3.0"
) -> StepResult:
    """Run the step with `source` in src/app/run.py, as devctl `version`.

    The default is the Kit version after GRACE_VERSION, in which Kit 0.2.0's suppressions fail.
    """
    workspace.write(".rapid-ship/kit.lock", 'kit_version = "0.2.0"\nstack = "python"\n')
    workspace.write("src/app/run.py", source)
    text = "".join(ENTRY.format(id=i, path=p, rule=r) for i, p, r in entries)
    workspace.write(".rapid-ship/exceptions.toml", text)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(devctl, "__version__", version)
        return ExceptionsStep().run(workspace.context())


def test_marked_suppression_with_entry_passes(workspace: Workspace) -> None:
    result = setup(
        workspace,
        "import subprocess\nsubprocess.run(['make'])  # noqa: S603  # rs-exception: EX-1\n",
        ("EX-1", "src/app/run.py", "S603"),
    )

    assert result.status == "passed", result.details


def test_unmarked_suppression_fails(workspace: Workspace) -> None:
    result = setup(workspace, "x = 1  # type: ignore[assignment]\n")

    assert result.details == (
        "src/app/run.py:1: suppression assignment needs '# rs-exception: EX-<n>' "
        "and an entry in .rapid-ship/exceptions.toml",
    )


def test_stale_entry_fails(workspace: Workspace) -> None:
    result = setup(workspace, "x = 1\n", ("EX-1", "src/app/run.py", "S603"))

    assert result.details == ("EX-1 is stale: no suppression carries it; delete the entry",)


def test_id_used_twice_fails(workspace: Workspace) -> None:
    result = setup(
        workspace,
        "a = 1  # noqa: E501  # rs-exception: EX-1\nb = 2  # noqa: E501  # rs-exception: EX-1\n",
        ("EX-1", "src/app/run.py", "E501"),
    )

    assert "EX-1 is used on 2 lines; each ID is used once" in result.details


def test_marker_for_another_path_or_rule_fails(workspace: Workspace) -> None:
    result = setup(
        workspace,
        "a = 1  # noqa: E501  # rs-exception: EX-1\nb = 2  # noqa: E501  # rs-exception: EX-2\n",
        ("EX-1", "src/app/other.py", "E501"),
        ("EX-2", "src/app/run.py", "S603"),
    )

    assert "src/app/run.py:1: EX-1 names src/app/other.py, not this file" in result.details
    assert (
        "src/app/run.py:2: EX-2 is for rule S603, which is not suppressed on this line"
        in result.details
    )


def test_unknown_id_fails(workspace: Workspace) -> None:
    result = setup(workspace, "a = 1  # noqa: E501  # rs-exception: EX-9\n")

    assert "src/app/run.py:1: EX-9 is not in .rapid-ship/exceptions.toml" in result.details


def test_invalid_exceptions_file_blocks_the_step(workspace: Workspace) -> None:
    # Plan 2's load_exceptions rejects blank fields, malformed IDs and repeated IDs.
    result = setup(
        workspace, "x = 1\n", ("EX-1", "src/app/run.py", "E501"), ("EX-1", "src/app/run.py", "S603")
    )

    assert result.status == "blocked"
    assert "EX-1" in result.details[0]


def test_skip_markers_and_calls_are_suppressions(workspace: Workspace) -> None:
    result = setup(
        workspace,
        "import pytest\n"
        "@pytest.mark.skipif(True, reason='x')\n"
        "def test_a():\n"
        "    pytest.skip('later')\n",
    )

    assert [d.split(":")[1] for d in result.details] == ["2", "4"]


def test_a_byte_order_mark_does_not_hide_a_skip_marker(workspace: Workspace) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version = "0.2.0"\nstack = "python"\n')
    workspace.write_with_bom(
        "src/app/run.py", "import pytest\n@pytest.mark.skip(reason='x')\ndef test_a(): pass\n"
    )
    workspace.write(".rapid-ship/exceptions.toml", "")

    result = ExceptionsStep().run(workspace.context())

    assert [d.split(":")[1] for d in result.details] == ["2"]


def test_strings_and_kit_files_are_not_suppressions(workspace: Workspace) -> None:
    workspace.write("tools/devctl/devctl/run.py", "x = 1  # noqa: E501\n")
    workspace.write(".rapid-ship/kit.lock", KIT_FILE_LOCK)
    workspace.write("src/app/run.py", "TEXT = '# noqa: E501'\n")
    workspace.write("docs/notes.md", "Write `# noqa: S603  # rs-exception: EX-<n>`.\n")
    workspace.write(".rapid-ship/exceptions.toml", "")

    assert ExceptionsStep().run(workspace.context()).status == "passed"


def test_a_kit_file_under_kit_exclude_is_scanned(workspace: Workspace) -> None:
    # [kit] exclude lists tools/devctl, so the project owns the file and its suppressions.
    workspace.write("tools/devctl/devctl/run.py", "x = 1  # noqa: E501\n")
    workspace.write(".rapid-ship/kit.lock", KIT_FILE_LOCK)
    workspace.write(".rapid-ship/exceptions.toml", "")

    result = ExceptionsStep().run(workspace.context(excluded=("tools/devctl",)))

    assert result.details == (
        "tools/devctl/devctl/run.py:1: suppression E501 needs '# rs-exception: EX-<n>' "
        "and an entry in .rapid-ship/exceptions.toml",
    )


def test_workflow_ignore_comment_needs_an_exception(workspace: Workspace) -> None:
    workspace.write(
        ".github/workflows/ci.yml", "permissions: {}  # zizmor: ignore[excessive-permissions]\n"
    )

    result = setup(workspace, "x = 1\n")

    assert result.details == (
        ".github/workflows/ci.yml:1: suppression zizmor:excessive-permissions needs "
        "'# rs-exception: EX-<n>' and an entry in .rapid-ship/exceptions.toml",
    )


def test_workflow_ignore_with_several_names_matches_its_entry(workspace: Workspace) -> None:
    workspace.write(
        ".github/workflows/ci.yml",
        "permissions: write-all  # zizmor: ignore[excessive-permissions, artipacked]"
        "  # rs-exception: EX-1\n",
    )

    result = setup(
        workspace,
        "x = 1\n",
        ("EX-1", ".github/workflows/ci.yml", "zizmor:artipacked,excessive-permissions"),
    )

    assert result.status == "passed", result.details


@pytest.mark.parametrize(
    ("comment", "rule"),
    [
        ("# deptry: ignore", "deptry"),
        ("# deptry: ignored", "deptry"),
        ("# deptry: ignore[DEP003, DEP001]", "deptry:DEP001,DEP003"),
        ("# Deptry: Ignore[DEP003]", "deptry:DEP003"),
        # deptry reads only upper-case codes; with any other bracket it ignores every rule.
        ("# deptry: ignore[dep003]", "deptry"),
        ("# deptry: ignore[DEP003, dep001]", "deptry"),
    ],
)
def test_deptrys_inline_comment_is_a_suppression(
    workspace: Workspace, comment: str, rule: str
) -> None:
    unmarked = setup(workspace, f"import yaml  {comment}\n")
    marked = setup(
        workspace,
        f"import yaml  {comment}  # rs-exception: EX-1\n",
        ("EX-1", "src/app/run.py", rule),
    )

    assert unmarked.details == (
        f"src/app/run.py:1: suppression {rule} needs '# rs-exception: EX-<n>' "
        "and an entry in .rapid-ship/exceptions.toml",
    )
    assert marked.status == "passed", marked.details


# vulture reads its noqa comment anywhere on a line, this file's lines included, so these sources
# build it from parts.
NOQA = "# " + "noqa"
TOOL_LINES = (
    f"def a() -> None: ...  {NOQA}_hidden\n"
    f"def b(tag: str = '{NOQA}') -> str: ...\n"
    f"def c(tag: str = '{NOQA}: V103, E501') -> str: ...\n"
    f"def d() -> None: ...  {NOQA}:  V107\n"
    f"def e() -> None: ...  {NOQA}: V103\n"
    f"TEXT = '{NOQA}: E501'\n"
    "import yaml; TAG = '# deptry: ignore'\n"
    "TAG = '# deptry: ignore'\n"
    "from toml import (\n"
    "    load,\n"
    "); TAG = '# deptry: ignore[DEP001]'\n"
    "import click  # deptry: ignore[DEP003]\n"
    "from importlib import import_module\n"
    "jwt = import_module('jwt'); TAG = '# deptry: ignore'\n"
    'def f() -> None:\n    """Write\n'
    f"    {NOQA} to silence Ruff.\n"
    '    """\n'
    f'X = """{NOQA}\n'
    '"""\n'
    "# page\fbreak\n"
    f"def g(tag: str = '{NOQA}') -> str: ...\n"
    "def h() -> None: ...\n"
    "import os, \\\n"
    "    yaml; TAG = '# deptry: ignore'\n"
)


def test_vulture_and_deptry_read_the_whole_line(tmp_path: Path) -> None:
    # Each tool searches a line's whole text, a string included, and acts on its first match,
    # but only on the first line of what it reports: lines 11 and 17 hide nothing. Line 19 hides
    # X, and no comment fits there. vulture numbers lines as str.splitlines does, so after line
    # 21's form feed it reads line 22's text as line 23's. deptry reads line 25 for yaml, the
    # second name of line 24's import.
    (tmp_path / "run.py").write_text(TOOL_LINES)

    lines = scan(tmp_path, ["run.py"], frozenset(), "python")

    assert {line.number: list(line.rules) for line in lines} == {
        1: ["noqa"],
        2: ["noqa"],
        3: ["V103"],
        4: ["V107", "noqa"],
        5: ["V103"],
        7: ["deptry"],
        12: ["deptry:DEP003"],
        14: ["deptry"],
        19: ["noqa"],
        23: ["noqa"],
        25: ["deptry"],
    }


def test_where_the_source_does_not_parse_every_line_counts_for_vulture(tmp_path: Path) -> None:
    # vulture's Python may parse what devctl's cannot, such as newer syntax.
    (tmp_path / "run.py").write_text(f"X = 1 +\n'''\n{NOQA}\n'''\n")

    lines = scan(tmp_path, ["run.py"], frozenset(), "python")

    assert [(line.number, line.rules) for line in lines] == [(3, ("noqa",))]


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        (f"def unused(tag: str = '{NOQA}') -> str: ...", "noqa"),
        ("import yaml; TAG = '# deptry: ignore'", "deptry"),
    ],
)
def test_a_line_that_vulture_or_deptry_reads_as_a_suppression_needs_its_marker(
    workspace: Workspace, source: str, rule: str
) -> None:
    unmarked = setup(workspace, f"{source}\n")
    marked = setup(workspace, f"{source}  # rs-exception: EX-1\n", ("EX-1", "src/app/run.py", rule))

    assert unmarked.details == (
        f"src/app/run.py:1: suppression {rule} needs '# rs-exception: EX-<n>' "
        "and an entry in .rapid-ship/exceptions.toml",
    )
    assert marked.status == "passed", marked.details


@pytest.mark.parametrize(
    ("rule", "normal"),
    [
        ("S607, S603", "S603,S607"),
        ("zizmor:excessive-permissions,artipacked", "zizmor:artipacked,excessive-permissions"),
        ("zizmor: unpinned-uses, artipacked", "zizmor:artipacked,unpinned-uses"),
        ("mypy:disable-error-code", "mypy:disable-error-code"),
        ("arg-type,call-arg", "arg-type,call-arg"),
        ("file-size", "file-size"),
    ],
)
def test_normal_rule_sorts_the_names_after_a_tool_prefix(rule: str, normal: str) -> None:
    assert normal_rule(rule) == normal


def test_marked_autouse_fixture_is_validated_unmarked_one_is_left_to_diff(
    workspace: Workspace,
) -> None:
    workspace.write(
        "tests/conftest.py",
        "import pytest\n"
        "@pytest.fixture(autouse=True)  # rs-exception: EX-1\n"
        "def fake_clock(): pass\n"
        "@pytest.fixture(autouse=True)\n"
        "def other(): pass\n",
    )

    result = setup(workspace, "x = 1\n", ("EX-1", "tests/conftest.py", "autouse"))

    assert result.status == "passed", result.details


# The gitleaks line is split so that documents quoting this test hold no allow comment, and so
# that vulture, which reads its noqa comment anywhere on a line, reads none on this file's line.
EVERY_PYTHON_SUPPRESSION = (
    "# ruff: noqa: e501\n"
    "# flake8: noqa\n"
    '# mypy: disable-error-code="arg-type"\n'
    "import pytest\n"
    "from pytest import mark\n"
    "yaml = pytest.importorskip('yaml')  # noqa: f401\n"
    "pytestmark = mark.xfail\n"
    "x = f()  # type: ignore[call-arg, arg-type]  # noqa: E501, F821\n"
    "KEY = 'k'  # gitleaks" + ":allow  # " + "NOQA\n"
    "TEXT = '# noqa: E501  # type: ignore'\n"
    "y = g()  # type: ignore\n"
    "@pytest.mark.skipif(\n"
    "    True, reason='r'\n"
    ")\n"
    "def test_a() -> None:  # pragma: no cover\n"
    "    pytest.skip('later')\n"
    "    pytest.xfail('known')  # mypy: ignore-errors\n"
)


def test_each_python_suppression_names_its_rule(tmp_path: Path) -> None:
    (tmp_path / "test_all.py").write_text(EVERY_PYTHON_SUPPRESSION)

    lines = scan(tmp_path, ["test_all.py"], frozenset(), "python")

    assert {line.number: list(line.rules) for line in lines} == {
        1: ["E501"],
        2: ["noqa"],
        3: ["mypy:disable-error-code"],
        6: ["F401", "importorskip"],
        7: ["xfail"],
        8: ["E501,F821", "arg-type,call-arg"],
        9: ["noqa", "gitleaks"],
        11: ["type-ignore"],
        12: ["skipif"],
        15: ["no-cover"],
        16: ["skip"],
        17: ["mypy:ignore-errors", "xfail"],
    }


def test_the_agnostic_stack_reads_only_text_rules(workspace: Workspace) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version = "0.2.0"\nstack = "agnostic"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write("src/run.py", "x = 1  # noqa: E501\n")
    workspace.write("notes.txt", "token  # gitleaks" + ":allow\n")

    result = ExceptionsStep().run(workspace.context(stack="agnostic"))

    assert result.details == (
        "notes.txt:1: suppression gitleaks needs '# rs-exception: EX-<n>' "
        "and an entry in .rapid-ship/exceptions.toml",
    )


def test_a_marker_on_a_python_line_without_a_suppression_fails(workspace: Workspace) -> None:
    result = setup(workspace, "x = 1  # rs-exception: EX-1\n", ("EX-1", "src/app/run.py", "S603"))

    assert result.details == (
        "src/app/run.py:1: EX-1 is for rule S603, which is not suppressed on this line",
    )


def test_symlinks_and_files_that_are_not_utf8_are_not_scanned(workspace: Workspace) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version = "0.2.0"\nstack = "python"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    (workspace.root.parent / "outside.py").write_text("x = 1  # noqa: E501\n")
    (workspace.root / "alias.py").symlink_to("../outside.py")
    (workspace.root / "latin1.py").write_bytes(b"x = 1  # noqa: E501 \xe9\n")

    assert ExceptionsStep().run(workspace.context()).status == "passed"


def test_a_missing_kit_lock_blocks_the_step(workspace: Workspace) -> None:
    workspace.write(".rapid-ship/exceptions.toml", "")

    result = ExceptionsStep().run(workspace.context())

    assert result.status == "blocked"
    assert result.details == (".rapid-ship/kit.lock: missing; run rapid-ship init",)
