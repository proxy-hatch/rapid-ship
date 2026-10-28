"""Integration test: needs network access (PyPI and pip-audit's lookups) and gitleaks on PATH.

No GitHub access.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from check_workspace import Workspace, new_workspace
from devctl.check.stacks.agnostic import WorkflowsStep
from devctl.check.stacks.python import AuditStep
from devctl.check.steps import tool_environment
from devctl.process import run_process

# The agnostic seed has no source roots; a local run has no base commit and no PR body.
NOT_APPLICABLE: dict[tuple[str, str], set[str]] = {
    ("python", "fast"): set(),
    ("agnostic", "fast"): {"file-size"},
    ("python", "full"): {"diff", "evidence"},
    ("agnostic", "full"): {"file-size", "diff", "evidence"},
}


def assert_check_passes(project: Workspace, stack: str, tier: str) -> None:
    result = run_process(
        ["./devctl", "check", "--tier", tier, "--json"], project.root, 1200, env=tool_environment()
    )
    assert result.returncode == 0, result.stdout + result.stderr
    statuses = {step["name"]: step["status"] for step in json.loads(result.stdout)}
    assert set(statuses.values()) <= {"passed", "not_applicable"}
    skipped = {name for name, status in statuses.items() if status == "not_applicable"}
    assert skipped == NOT_APPLICABLE[(stack, tier)]


def init_project(path: Path, stack: str) -> Workspace:
    project = new_workspace(path)
    # init commits the Kit, and a CI runner has no git identity of its own.
    for key, value in (("user.name", "devctl tests"), ("user.email", "devctl@example.invalid")):
        project.git("config", key, value)
    init = run_process(
        [sys.executable, "-m", "rapid_ship", "init", "--stack", stack, "--owner", "test-owner"],
        project.root,
        120,
    )
    assert init.returncode == 0, init.stdout + init.stderr
    return project


@pytest.mark.parametrize("stack", ["python", "agnostic"])
def test_new_project_passes_devctl_check(tmp_path: Path, stack: str) -> None:
    project = init_project(tmp_path / "project", stack)
    if stack == "python":
        # pytest imports the package, so it writes __pycache__ under the source root.
        for command in (["uv", "sync", "--quiet"], ["uv", "run", "--locked", "pytest", "-q"]):
            ran = run_process(command, project.root, 600, env=tool_environment())
            assert ran.returncode == 0, ran.stdout + ran.stderr

    assert_check_passes(project, stack, "fast")
    project.commit("rapid-ship init")
    assert "__pycache__" not in project.git("ls-files")
    assert_check_passes(project, stack, "full")


# A project's replacement for the seeded tools/devctl/devctl_project/__init__.py.
PROJECT_EXTENSION = r'''"""This project's devctl verbs and check steps."""

from __future__ import annotations

import argparse
import sys

from devctl.check.steps import CheckContext, Step, StepResult, Tier, passed


def greet(args: argparse.Namespace) -> int:
    sys.stdout.write(f"hello {args.name}\n")
    return 0


class ReleaseNotesStep:
    name = "release-notes"
    tier: Tier = "full"

    def run(self, context: CheckContext) -> StepResult:
        return passed(self.name, "release notes are current")


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    verb = commands.add_parser("greet", help="Print a greeting")
    verb.add_argument("name")
    verb.set_defaults(handler=greet)


def check_steps() -> list[Step]:
    return [ReleaseNotesStep()]
'''


def run_devctl(project: Workspace, *args: str) -> tuple[int, str, str]:
    result = run_process(["./devctl", *args], project.root, 1200, env=tool_environment())
    return result.returncode, result.stdout, result.stderr


def test_a_project_verb_and_check_step_extend_devctl(tmp_path: Path) -> None:
    project = init_project(tmp_path / "project", "agnostic")
    project.write("tools/devctl/devctl_project/__init__.py", PROJECT_EXTENSION)
    project.commit("rapid-ship init, then a project verb and check step")

    greeted = run_devctl(project, "greet", "world")
    fast = run_devctl(project, "check", "--tier", "fast", "--json")
    full = run_devctl(project, "check", "--tier", "full", "--json")

    assert greeted[:2] == (0, "hello world\n"), greeted
    assert "release-notes" not in {step["name"] for step in json.loads(fast[1])}
    assert full[0] == 0, full
    assert json.loads(full[1])[-1] == {
        "name": "release-notes",
        "status": "passed",
        "details": ["release notes are current"],
    }


def test_audit_and_workflows_pass_when_uv_cannot_write_its_tools_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A sandbox can let uv write its cache and nothing else in the owner's home.
    project = init_project(tmp_path / "project", "python")
    locked = run_process(["uv", "lock", "--quiet"], project.root, 600, env=tool_environment())
    assert locked.returncode == 0, locked.stdout + locked.stderr
    tools = tmp_path / "uv-tools"
    tools.mkdir(mode=0o555)
    monkeypatch.setenv("UV_TOOL_DIR", str(tools))

    try:
        # Prove the restriction applies to this process, including on privileged CI runners.
        with pytest.raises(PermissionError):
            (tools / "write-probe").write_text("denied")
        for package, command in (("pip-audit==2.10.1", "pip-audit"), ("zizmor==1.30.1", "zizmor")):
            control = run_process(
                ["uv", "tool", "run", "--from", package, command, "--version"],
                project.root,
                600,
                env=tool_environment(),
            )
            assert control.returncode != 0
            assert str(tools) in control.stderr
            assert (
                "Permission denied" in control.stderr or "Operation not permitted" in control.stderr
            )
        results = [step.run(project.context()) for step in (AuditStep(), WorkflowsStep())]

        statuses = [(result.name, result.status) for result in results]
        assert statuses == [("audit", "passed"), ("workflows", "passed")], results
        assert list(tools.iterdir()) == []
    finally:
        tools.chmod(0o755)


UNUSED_FUNCTION = '''def unused_helper() -> None:
    """Nothing calls this function."""
'''


def test_a_new_project_fails_the_dead_code_step_on_unused_code_and_a_dependency(
    tmp_path: Path,
) -> None:
    # The vendored devctl imports yaml, so the DEP002 line also shows that deptry leaves
    # tools/devctl out, and the absence of any other deptry line that the seed passes every rule.
    project = init_project(tmp_path / "project", "python")
    [package] = [path.parent.name for path in (project.root / "src").glob("*/__init__.py")]
    project.write(f"src/{package}/extra.py", UNUSED_FUNCTION)
    pyproject = project.root / "pyproject.toml"
    seeded = pyproject.read_text()
    assert "dependencies = []" in seeded
    pyproject.write_text(
        seeded.replace("dependencies = []", 'dependencies = ["pyyaml>=6.0.3,<7"]', 1)
    )
    for command in (["uv", "lock", "--quiet"], ["uv", "sync", "--quiet"]):
        ran = run_process(command, project.root, 600, env=tool_environment())
        assert ran.returncode == 0, ran.stdout + ran.stderr
    project.commit("an unused function and an unused dependency")

    code, out, err = run_devctl(project, "check", "--tier", "full", "--json")

    assert code == 1, out + err
    steps = {step["name"]: step for step in json.loads(out)}
    dead_code = steps.pop("dead-code")
    assert dead_code["status"] == "failed", dead_code
    statuses = {name: step["status"] for name, step in steps.items()}
    assert set(statuses.values()) <= {"passed", "not_applicable"}, steps
    skipped = {name for name, status in statuses.items() if status == "not_applicable"}
    assert skipped == NOT_APPLICABLE[("python", "full")]
    details: list[str] = dead_code["details"]
    unused = "unused function 'unused_helper' (60% confidence)"
    assert any(d.startswith("vulture: ") and d.endswith(unused) for d in details), details
    deptry = [d for d in details if d.startswith("deptry: ")]
    assert len(deptry) == 1, details
    assert deptry[0].startswith("deptry: pyproject.toml: DEP002 'pyyaml'"), details
