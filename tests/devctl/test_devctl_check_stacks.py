"""Offline: each stack's check steps in fixture repositories, with fake tools on PATH."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from check_workspace import Workspace, fake_tool, project_settings
from devctl.check import core_steps, step_name
from devctl.check.diff import DiffStep
from devctl.check.exceptions import ExceptionsStep
from devctl.check.filesize import FileSizeStep
from devctl.check.references import resolve
from devctl.check.tracked import TrackedFiles
from devctl.settings import ProjectStack
from test_devctl_step_order import PYTHON

BACKEND = ProjectStack("python", "backend")
WORKER = ProjectStack("python", "worker")


def test_one_python_stack_at_the_root_keeps_the_step_names() -> None:
    assert [step.name for step in core_steps(project_settings())] == PYTHON


def test_step_names_follow_the_stacks() -> None:
    stacks = (BACKEND, WORKER)
    expected = [f"{s} ({d})" for d in ("backend", "worker") for s in ("format", "lint")]
    expected += ["map", "exceptions", "file-size", "kit"]
    expected += [
        f"{s} ({d})"
        for d in ("backend", "worker")
        for s in ("types", "contracts", "dead-code", "tests", "audit")
    ]
    assert [s.name for s in core_steps(project_settings(stacks=stacks))] == [
        *expected,
        "secrets",
        "workflows",
        "diff",
        "evidence",
    ]
    mixed = (ProjectStack("python", "."), ProjectStack("typescript", "frontend"))
    assert step_name("lint", mixed[0], mixed) == "lint (.)"
    assert step_name("lint", mixed[1], mixed) == "lint (frontend)"
    shared = (ProjectStack("python", "app"), ProjectStack("typescript", "app"))
    assert step_name("lint", shared[0], shared) == "lint (app, python)"


def test_a_stack_step_runs_in_its_directory(
    workspace: Workspace, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tool = fake_tool(
        tmp_path / "bin",
        "uv",
        'if "--output" in sys.argv:\n'
        '    report = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])\n'
        "    report.write_text('{\"dependencies\": []}')\n"
        "sys.exit(0)",
    )
    monkeypatch.setenv("PATH", f"{tool.parent}{os.pathsep}{os.environ['PATH']}")
    workspace.write(
        "backend/pyproject.toml",
        '[dependency-groups]\ndev=["vulture", "deptry"]\n[tool.vulture]\npaths=["src"]\n',
    )
    ctx = workspace.context(stacks=(BACKEND,))
    for step in core_steps(ctx.project):
        if step.name in ("format (backend)", "dead-code (backend)", "audit (backend)"):
            assert step.run(ctx).status == "passed"
    logs = [json.loads(line) for line in tool.with_suffix(".log").read_text().splitlines()]
    assert len(logs) == 5
    assert {entry["cwd"] for entry in logs} == {str(workspace.root / "backend")}


def test_suppressions_are_read_in_their_owners_forms(workspace: Workspace) -> None:
    workspace.write("backend/src/app/a.py", "x = 1  # noqa: E501\n")
    workspace.write("web/a.py", "x = 1  # noqa: E501\n")
    workspace.write("backend/pyproject.toml", '[tool.vulture]\n\n\nignore_names=["x"]\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="python"\n')
    workspace.stage()
    ctx = workspace.context(stacks=(BACKEND,))
    details = "\n".join(ExceptionsStep().run(ctx).details)
    assert "backend/src/app/a.py:1: suppression E501 needs" in details
    assert "web/a.py" not in details
    assert "backend/pyproject.toml:4: suppression vulture.ignore_names:x needs" in details
    workspace.write("backend/pyproject.toml", '[tool.vulture]\n\n\nignore_names=["x", "y"]\n')
    assert "backend/pyproject.toml:4: vulture.ignore_names holds 2 items" in "\n".join(
        ExceptionsStep().run(ctx).details
    )


def test_file_size_counts_each_owners_source_files(workspace: Workspace) -> None:
    for path in ("backend/src/app/a.py", "backend/src/app/notes.txt", "docs/src/x.txt"):
        workspace.write(path, "x\n" * 501)
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="python"\n')
    workspace.stage()
    ctx = workspace.context(stacks=(BACKEND,), source_roots=("backend/src/app", "docs/src"))
    details = "\n".join(FileSizeStep().run(ctx).details)
    assert "backend/src/app/a.py: 501 lines" in details
    assert "docs/src/x.txt: 501 lines" in details
    assert "notes.txt" not in details


def test_references_resolve_against_the_holders_stack(workspace: Workspace) -> None:
    workspace.write(
        "backend/pyproject.toml",
        '[tool.ruff.lint]\nselect=["BLE"]\n[tool.mypy]\nfiles=["src", "tests"]\n',
    )
    workspace.write("worker/pyproject.toml", "")
    workspace.write("backend/tests/test_inputs.py", "def test_inputs(): pass\n")
    workspace.stage()
    ctx = workspace.context(stacks=(BACKEND, WORKER))
    tracked = TrackedFiles.read(ctx.repo)
    assert resolve("ruff:BLE001", ctx, tracked, "backend/src/app/errors.py") is None
    assert (
        resolve("ruff:BLE001", ctx, tracked, "worker/src/w.py")
        == "ruff:BLE001: Ruff does not select BLE001 in worker/pyproject.toml"
    )
    for holder in ("README.md", "docs/corrections/entry.md"):
        reason = resolve("ruff:BLE001", ctx, tracked, holder)
        assert reason
        assert "python (backend), python (worker)" in reason
        assert "test:<path>::<name>" in reason
        assert "check:" in reason
    assert resolve("check:lint (backend)", ctx, tracked, "README.md") is None
    assert resolve("check:lint (missing)", ctx, tracked, "README.md") is not None
    assert resolve("check:lint", ctx, tracked, "backend/AGENTS.md") is None
    assert (
        resolve("check:nope", ctx, tracked, "AGENTS.md")
        == "check:nope: no devctl check step is named nope"
    )
    assert resolve("type:backend/tests/test_inputs.py", ctx, tracked, "backend/AGENTS.md") is None


def test_the_diff_rules_apply_to_the_python_stacks_files(workspace: Workspace) -> None:
    for path in ("backend/tests/test_a.py", "scripts/test_b.py"):
        workspace.write(path, "def test_removed(): pass\n")
    base = workspace.commit()
    for path in ("backend/tests/test_a.py", "scripts/test_b.py"):
        workspace.write(path, "")
    details = "\n".join(DiffStep().run(workspace.context(base=base, stacks=(BACKEND,))).details)
    assert "removed behavioural test backend/tests/test_a.py::test_removed" in details
    assert "scripts/test_b.py::test_removed" not in details


@pytest.mark.parametrize(
    "kind", ["ruff:BLE001", "type:backend/tests/a.py", "test:backend/tests/a.py::test_a"]
)
@pytest.mark.parametrize("state", ["untracked", "ignored", "symlink"])
def test_nested_reference_targets_must_be_tracked(
    workspace: Workspace, kind: str, state: str
) -> None:
    settings = "backend/pyproject.toml"
    target = settings if kind.startswith("ruff:") else "backend/tests/a.py"
    workspace.write(settings, '[tool.ruff.lint]\nselect=["BLE"]\n[tool.mypy]\nfiles=["tests"]\n')
    workspace.write("backend/tests/a.py", "def test_a(): pass\n")
    if target != settings:
        workspace.git("add", settings)
    if state == "ignored":
        workspace.write(".gitignore", f"/{target}\n")
    elif state == "symlink":
        text = (workspace.root / target).read_text()
        (workspace.root / target).unlink()
        workspace.write("untracked-target", text)
        workspace.link(target, str(workspace.root / "untracked-target"))
        workspace.git("add", target)
    ctx = workspace.context(stacks=(BACKEND,))
    reason = resolve(kind, ctx, TrackedFiles.read(ctx.repo), "AGENTS.md")
    assert reason is not None
    assert "tracked" in reason or "ignored" in reason
    if state != "symlink":
        workspace.git("add", "-f", target)
        assert resolve(kind, ctx, TrackedFiles.read(ctx.repo), "docs/corrections/entry.md") is None
