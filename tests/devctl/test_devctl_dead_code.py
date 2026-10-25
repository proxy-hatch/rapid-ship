"""Offline: the dead-code step against a simulated uv that stands in for vulture and deptry."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import devctl
from check_workspace import Workspace, fake_tool
from devctl.check.stacks.python_dead_code import DeadCodeStep, dead_code_gaps

# The tool is uv's third argument: `uv run --locked <tool> ...`.
UV = """
args = sys.argv[1:]
here = pathlib.Path(__file__).parent
tool = args[2]
if (here / f"{tool}.out").exists():
    sys.stdout.write((here / f"{tool}.out").read_text())
if "--json-output" in args and (here / "deptry.json").exists():
    target = pathlib.Path(args[args.index("--json-output") + 1])
    target.write_text((here / "deptry.json").read_text())
code = here / f"{tool}.exit"
sys.exit(int(code.read_text()) if code.exists() else 0)
"""
PYPROJECT = '[dependency-groups]\ndev = ["deptry", "vulture"]\n\n[tool.vulture]\npaths = ["src"]\n'
UNUSED = "src/app/a.py:3: unused function 'helper' (60% confidence)"
TOOLS = "[dependency-groups] dev lacks vulture, deptry; add them to pyproject.toml and run uv lock"
PATHS = (
    '[tool.vulture] paths is not set; list the directories vulture scans, such as ["src", "tests"]'
)


@pytest.fixture
def tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "bin"
    fake_tool(directory, "uv", UV)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return directory


def dead_code(workspace: Workspace, pyproject: str | None = PYPROJECT) -> tuple[str, ...]:
    if pyproject is not None:
        workspace.write("pyproject.toml", pyproject)
    result = DeadCodeStep().run(workspace.context())
    return (result.status, *result.details)


def calls(tools: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in (tools / "uv.log").read_text().splitlines()]


def finding(code: str, message: str, location: dict[str, object]) -> dict[str, object]:
    return {"error": {"code": code, "message": message}, "module": "m", "location": location}


def test_both_tools_pass_and_run_through_uv(workspace: Workspace, tools: Path) -> None:
    assert dead_code(workspace) == ("passed",)

    [vulture, deptry] = calls(tools)
    assert vulture["argv"] == ["run", "--locked", "vulture", "--min-confidence", "0"]
    argv = deptry["argv"]
    assert isinstance(argv, list)
    assert argv[:-1] == ["run", "--locked", "deptry", ".", "--no-ansi", "--json-output"]
    assert str(argv[-1]).endswith("deptry.json")
    assert vulture["cwd"] == deptry["cwd"] == str(workspace.root)


def test_unused_code_fails_with_vultures_lines(workspace: Workspace, tools: Path) -> None:
    (tools / "vulture.out").write_text(f"{UNUSED}\n")
    (tools / "vulture.exit").write_text("3")

    assert dead_code(workspace) == ("failed", f"vulture: {UNUSED}")


@pytest.mark.parametrize(
    ("item", "line"),
    [
        (
            finding(
                "DEP002",
                "'tomli-w' defined as a dependency but not used in the codebase",
                {"file": "pyproject.toml", "line": None, "column": None},
            ),
            "deptry: pyproject.toml: DEP002 'tomli-w' defined as a dependency but not used in the "
            "codebase",
        ),
        (
            finding(
                "DEP003",
                "'cryptography' imported but it is a transitive dependency",
                {"file": "src/app/a.py", "line": 3, "column": 1},
            ),
            "deptry: src/app/a.py:3:1: DEP003 'cryptography' imported but it is a transitive "
            "dependency",
        ),
    ],
)
def test_a_dependency_finding_fails_with_deptrys_line(
    workspace: Workspace, tools: Path, item: dict[str, object], line: str
) -> None:
    (tools / "deptry.json").write_text(json.dumps([item]))
    (tools / "deptry.exit").write_text("1")

    assert dead_code(workspace) == ("failed", line)


@pytest.mark.parametrize("report", [None, [], {"error": {}}, [{"error": {"code": "DEP002"}}]])
def test_deptry_exit_1_without_a_readable_report_is_blocked(
    workspace: Workspace, tools: Path, report: object
) -> None:
    if report is not None:
        (tools / "deptry.json").write_text(json.dumps(report))
    (tools / "deptry.exit").write_text("1")

    status, *details = dead_code(workspace)

    assert status == "blocked"
    assert details[0] == "deptry: deptry exited 1 and wrote no readable report"


@pytest.mark.parametrize(("tool", "code"), [("vulture", 1), ("vulture", 2), ("deptry", 2)])
def test_any_other_exit_is_blocked(workspace: Workspace, tools: Path, tool: str, code: int) -> None:
    (tools / f"{tool}.exit").write_text(str(code))

    status, *details = dead_code(workspace)

    assert status == "blocked"
    assert details[0].startswith(f"{tool}: uv run --locked {tool}")
    assert details[0].endswith(f"exited {code}")


def test_a_blocked_tool_outranks_a_failed_one(workspace: Workspace, tools: Path) -> None:
    (tools / "vulture.out").write_text(f"{UNUSED}\n")
    (tools / "vulture.exit").write_text("3")
    (tools / "deptry.exit").write_text("2")

    status, *details = dead_code(workspace)

    assert status == "blocked"
    assert details[0] == f"vulture: {UNUSED}"
    assert details[1].startswith("deptry: uv run --locked deptry")
    assert details[1].endswith("exited 2")


@pytest.mark.parametrize(
    ("pyproject", "messages"),
    [
        ('[dependency-groups]\ndev = ["ruff"]\n\n[tool.vulture]\npaths = ["src"]\n', [TOOLS]),
        ('[dependency-groups]\ndev = ["vulture", "deptry"]\n', [PATHS]),
        ('[dependency-groups]\ndev = ["ruff"]\n', [TOOLS, PATHS]),
        (None, [TOOLS, PATHS]),
    ],
)
@pytest.mark.parametrize("version", ["0.2.0", "0.3.0"])
def test_without_the_tools_or_paths_the_step_warns_in_kit_0_2_0_and_blocks_after(
    workspace: Workspace,
    tools: Path,
    monkeypatch: pytest.MonkeyPatch,
    pyproject: str | None,
    messages: list[str],
    version: str,
) -> None:
    monkeypatch.setattr(devctl, "__version__", version)

    result = dead_code(workspace, pyproject)

    if version == "0.2.0":
        warnings = (f"warning: {m}; this fails from the next Kit version" for m in messages)
        assert result == ("not_applicable", *warnings)
    else:
        assert result == ("blocked", *messages)
    assert not (tools / "uv.log").exists()


def test_an_invalid_pyproject_blocks_the_dead_code_step(workspace: Workspace, tools: Path) -> None:
    status, *details = dead_code(workspace, "[tool.vulture\n")

    assert status == "blocked"
    assert details[0].startswith("pyproject.toml: ")
    assert not (tools / "uv.log").exists()


def test_the_floor_names_vultures_paths_and_ruffs_external() -> None:
    def pyproject(external: list[str]) -> dict[str, object]:
        return {"tool": {"vulture": {"paths": ["src"]}, "ruff": {"lint": {"external": external}}}}

    assert dead_code_gaps({}) == ["vulture: paths is not set", "ruff: external lacks V"]
    assert dead_code_gaps(pyproject(["V"])) == []
    assert dead_code_gaps(pyproject(["V1", "V2"])) == []
    assert dead_code_gaps(pyproject(["V1"])) == ["ruff: external lacks V"]
