"""Offline: allowlist items in pyproject.toml, and the lines that vulture and deptry read, as
suppressions in fixture repositories."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.check.exceptions import ExceptionsStep
from devctl.check.stacks.python_dead_code import AllowlistItem, toml_allowlist
from devctl.check.steps import StepResult

ENTRY = """
[[exception]]
id = "{id}"
path = "{path}"
rule = "{rule}"
reason = "A framework calls these names"
remove_when = "Nothing calls them by name"
"""
VULTURE = '[tool.vulture]\npaths = ["src"]\nignore_names = [\n'
MARKED = f'{VULTURE}    "do_[A-Z]*",  # rs-exception: EX-1\n]\n'
UNMARKED = f'{VULTURE}    "do_[A-Z]*",\n]\n'
# vulture reads its noqa comment anywhere on a line, this file's lines included, so it is built
# from parts.
NOQA = "# " + "noqa"


def setup(
    workspace: Workspace, pyproject: str, *entries: tuple[str, str, str], stack: str = "python"
) -> StepResult:
    workspace.write(".rapid-ship/kit.lock", f'kit_version = "0.2.0"\nstack = "{stack}"\n')
    workspace.write("pyproject.toml", pyproject)
    text = "".join(ENTRY.format(id=i, path=p, rule=r) for i, p, r in entries)
    workspace.write(".rapid-ship/exceptions.toml", text)
    return ExceptionsStep().run(workspace.context(stack=stack))


def test_a_marked_item_with_its_entry_passes(workspace: Workspace) -> None:
    result = setup(workspace, MARKED, ("EX-1", "pyproject.toml", "vulture.ignore_names:do_[A-Z]*"))

    assert result.status == "passed", result.details


def test_an_unmarked_item_fails(workspace: Workspace) -> None:
    result = setup(workspace, UNMARKED)

    assert (result.status, *result.details) == (
        "failed",
        "pyproject.toml:4: suppression vulture.ignore_names:do_[A-Z]* needs "
        "'# rs-exception: EX-<n>' and an entry in .rapid-ship/exceptions.toml",
    )


@pytest.mark.parametrize(
    ("text", "items"),
    [
        (
            '[tool.vulture]\nignore_names = ["pytestmark"]\n',
            [AllowlistItem(2, "vulture.ignore_names:pytestmark")],
        ),
        (
            '[tool.vulture]\nignore_decorators = [\n    "@app.route",\n]\n',
            [AllowlistItem(3, "vulture.ignore_decorators:@app.route")],
        ),
        ('[tool.deptry]\nignore = ["DEP003"]\n', [AllowlistItem(2, "deptry.ignore:DEP003")]),
        (
            '[tool.deptry.per_rule_ignores]\nDEP002 = [\n    "psycopg2",\n]\n',
            [AllowlistItem(3, "deptry.per_rule_ignores.DEP002:psycopg2")],
        ),
        (
            '[tool.deptry]\noptional_dependencies_dev_groups = [\n    "docs",\n]\n',
            [AllowlistItem(3, "deptry.optional_dependencies_dev_groups:docs")],
        ),
        (
            '[tool.deptry.package_module_name_map]\nfoo-python = "foo"\n"bar-py" = [\n'
            '    "bar",\n]\n',
            [
                AllowlistItem(2, "deptry.package_module_name_map:foo-python"),
                AllowlistItem(3, "deptry.package_module_name_map:bar-py"),
            ],
        ),
    ],
)
def test_each_allowlist_key_names_its_rule(text: str, items: list[AllowlistItem]) -> None:
    assert toml_allowlist(text) == (items, [])


def test_two_items_on_one_line_fail(workspace: Workspace) -> None:
    result = setup(
        workspace,
        '[tool.vulture]\npaths = ["src"]\n'
        'ignore_names = ["a", "b"]  # rs-exception: EX-1  # rs-exception: EX-2\n',
        ("EX-1", "pyproject.toml", "vulture.ignore_names:a"),
        ("EX-2", "pyproject.toml", "vulture.ignore_names:b"),
    )

    assert (result.status, *result.details) == (
        "failed",
        "pyproject.toml:3: vulture.ignore_names holds 2 items on one line; write each alone on its "
        "own line, with its own marker",
    )


def unplaced(key: str, item: str, table: str) -> str:
    return (
        f"pyproject.toml: {key} lists '{item}' on no line devctl can read; write it alone on its "
        f"own line under [tool.{table}]"
    )


@pytest.mark.parametrize(
    ("text", "error"),
    [
        (
            '[tool.deptry]\nper_rule_ignores = { DEP002 = ["psycopg2"] }\n',
            unplaced("deptry.per_rule_ignores.DEP002", "psycopg2", "deptry.per_rule_ignores"),
        ),
        (
            '[tool.deptry]\npackage_module_name_map = { foo-python = "foo" }\n',
            unplaced(
                "deptry.package_module_name_map", "foo-python", "deptry.package_module_name_map"
            ),
        ),
        ('tool.vulture.ignore_names = ["x"]\n', unplaced("vulture.ignore_names", "x", "vulture")),
        (
            '[tool.vulture]\nignore_names = ["""x"""]\n',
            unplaced("vulture.ignore_names", "x", "vulture"),
        ),
    ],
)
def test_an_item_devctl_cannot_place_on_a_line_fails(
    workspace: Workspace, text: str, error: str
) -> None:
    assert toml_allowlist(text) == ([], [error])
    result = setup(workspace, text)
    assert (result.status, *result.details) == ("failed", error)


SCOPE = """\
[tool.vulture]
paths = ["src"]
exclude = ["src/generated/"]

[tool.deptry]
extend_exclude = ["tools/devctl"]
known_first_party = ["app"]
non_dev_dependency_groups = ["docs"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]
"""


def test_scope_settings_are_not_suppressions(workspace: Workspace) -> None:
    assert toml_allowlist(SCOPE) == ([], [])
    result = setup(workspace, SCOPE)
    assert result.status == "passed", result.details


def test_the_agnostic_stack_reads_no_allowlist(workspace: Workspace) -> None:
    result = setup(workspace, UNMARKED, stack="agnostic")

    assert result.status == "passed", result.details


def test_an_invalid_pyproject_blocks_the_exceptions_step(workspace: Workspace) -> None:
    result = setup(workspace, "[tool.vulture\n")

    assert result.status == "blocked"
    assert result.details[0].startswith("pyproject.toml: ")


def needs_marker(where: str, rule: str) -> str:
    return (
        f"{where}: suppression {rule} needs '# rs-exception: EX-<n>' and an entry in "
        ".rapid-ship/exceptions.toml"
    )


def test_the_dead_code_tools_suppressions_fail_at_once(workspace: Workspace) -> None:
    # Before GA the Kit keeps no backward compatibility, so a project that already holds these
    # lines fails in the Kit version that reads them.
    workspace.write(
        "src/app/run.py",
        "import yaml  # deptry: ignore\n"
        f"def unused(tag: str = '{NOQA}') -> str: ...\n"
        "x = 1  # type: ignore[assignment]\n",
    )
    inline = '\n[tool.deptry]\nper_rule_ignores = { DEP002 = ["psycopg2"] }\n'

    result = setup(workspace, UNMARKED + inline)

    assert (result.status, *result.details) == (
        "failed",
        needs_marker("pyproject.toml:4", "vulture.ignore_names:do_[A-Z]*"),
        needs_marker("src/app/run.py:1", "deptry"),
        needs_marker("src/app/run.py:2", "noqa"),
        needs_marker("src/app/run.py:3", "assignment"),
        unplaced("deptry.per_rule_ignores.DEP002", "psycopg2", "deptry.per_rule_ignores"),
    )
