"""Offline: the TypeScript steps against fake tools in a fake node_modules/.bin."""

import dataclasses
import json
from pathlib import Path

import pytest

from check_workspace import Workspace, fake_tool, node_tools
from devctl.check import core_steps, run_check
from devctl.check.filesize import line_counts, size_errors
from devctl.check.stacks import typescript as ts
from devctl.check.steps import CheckContext
from devctl.settings import ProjectStack


def context(workspace: Workspace) -> CheckContext:
    workspace.write("frontend/package-lock.json", "{}")
    return dataclasses.replace(
        workspace.context(stacks=(ProjectStack("typescript", "frontend"),)),
        stack=ProjectStack("typescript", "frontend"),
    )


def test_each_step_runs_its_tool_in_the_stack_directory(workspace: Workspace) -> None:
    ctx = context(workspace)
    steps = [ts.FORMAT, ts.LINT, ts.TYPES, ts.DEAD_CODE, ts.TESTS]
    node_tools(ctx.directory, **{step.argv[0]: "sys.exit(0)" for step in steps})
    expected = [
        ("prettier", "--check", "."),
        ("eslint", "--max-warnings", "0", "."),
        ("tsc", "--noEmit"),
        (
            "knip",
            "--include",
            "files,dependencies,unlisted,binaries,unresolved,"
            "exports,types,enumMembers,namespaceMembers",
        ),
        ("vitest", "run"),
    ]
    assert [step.argv for step in steps] == expected
    for step in steps:
        assert step.run(ctx).status == "passed"
        log = json.loads((ctx.directory / "node_modules/.bin" / f"{step.argv[0]}.log").read_text())
        assert log["argv"] == list(step.argv[1:])
        assert log["cwd"] == str(ctx.directory)
    names = [s.name for s in core_steps(ctx.project)]
    assert names == [
        "format (frontend)",
        "lint (frontend)",
        "map",
        "exceptions",
        "file-size",
        "kit",
        "types (frontend)",
        "dead-code (frontend)",
        "tests (frontend)",
        "audit (frontend)",
        "secrets",
        "workflows",
        "diff",
        "evidence",
    ]


@pytest.mark.parametrize(
    ("step", "code", "status"),
    [
        (ts.DEAD_CODE, 0, "passed"),
        (ts.DEAD_CODE, 1, "failed"),
        (ts.DEAD_CODE, 2, "blocked"),
        (ts.TYPES, 1, "failed"),
        (ts.TYPES, 2, "failed"),
        (ts.TYPES, 3, "blocked"),
        *[
            (step, code, status)
            for step in (ts.FORMAT, ts.LINT, ts.TESTS)
            for code, status in ((1, "failed"), (2, "blocked"))
        ],
    ],
)
def test_exit_codes_pass_fail_or_block(
    workspace: Workspace, step: ts.NodeStep, code: int, status: str
) -> None:
    ctx = context(workspace)
    node_tools(ctx.directory, **{step.argv[0]: f"sys.exit({code})"})
    assert step.run(ctx).status == status


def test_a_missing_tool_blocks_with_the_install_command(workspace: Workspace) -> None:
    ctx = context(workspace)
    result = ts.FORMAT.run(ctx)
    assert result.status == "blocked"
    assert result.details == (
        "cannot run prettier in frontend: prettier is not installed; run npm ci there",
    )
    (ctx.directory / "package-lock.json").unlink()
    assert (
        ts.FORMAT.run(ctx).details[0].endswith("run npm install there and commit package-lock.json")
    )


def test_npm_audit_reads_its_report(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = context(workspace)
    monkeypatch.setenv("PATH", str(workspace.root / "bin"))
    tool = fake_tool(
        workspace.root / "bin",
        "npm",
        'sys.stdout.write(\'{"vulnerabilities":{"vite":{"severity":"high",'
        '"via":[{"title":"Path traversal"}]}}}\'); sys.exit(1)',
    )
    assert ts.AuditStep().run(ctx).details == ("vite high: Path traversal",)
    fake_tool(
        tool.parent,
        "npm",
        'sys.stdout.write(\'{"error":{"code":"ENOLOCK","summary":"no lockfile"}}\'); sys.exit(1)',
    )
    assert ts.AuditStep().run(ctx).details == ("npm audit: ENOLOCK no lockfile",)
    fake_tool(tool.parent, "npm", "sys.exit(0)")
    assert ts.AuditStep().run(ctx).status == "passed"
    tool.with_suffix(".log").unlink()
    (ctx.directory / "package-lock.json").unlink()
    assert ts.AuditStep().run(ctx).status == "blocked"
    assert not tool.with_suffix(".log").exists()


def test_install_runs_npm_ci_first(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = context(workspace)
    monkeypatch.setenv("PATH", str(workspace.root / "bin"))
    fake_tool(workspace.root / "bin", "npm", "sys.exit(0)")
    results = run_check(ctx, "fast", install=True)
    assert results[0].name == "install (frontend)"
    assert results[0].status == "passed"
    log = json.loads((workspace.root / "bin/npm.log").read_text())
    assert log["argv"] == ["ci", "--no-audit", "--no-fund"]
    assert log["cwd"] == str(ctx.directory)
    assert all(not r.name.startswith("install") for r in run_check(ctx, "fast"))


def test_install_without_a_lock_blocks(workspace: Workspace) -> None:
    ctx = context(workspace)
    (ctx.directory / "package-lock.json").unlink()
    result = ts.InstallStep().run(ctx)
    assert result.status == "blocked"
    assert "there is no package-lock.json" in result.details[0]


def test_file_size_counts_typescript_sources(workspace: Workspace) -> None:
    ctx = context(workspace)
    for suffix in ("tsx", "css"):
        workspace.write(f"frontend/src/a.{suffix}", "line\n" * 501)
    sizes = line_counts(
        workspace.root,
        ["frontend/src/a.tsx", "frontend/src/a.css"],
        ("frontend/src",),
        frozenset(),
        ctx.project,
    )
    assert sizes == {"frontend/src/a.tsx": 501}
    assert len(size_errors(sizes, ())) == 1


@pytest.mark.parametrize(
    "step", [ts.FORMAT, ts.LINT, ts.TYPES, ts.DEAD_CODE, ts.TESTS, ts.AuditStep(), ts.InstallStep()]
)
def test_tools_have_bounded_timeouts(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
    step: ts.NodeStep | ts.AuditStep | ts.InstallStep,
) -> None:
    from collections.abc import Mapping, Sequence

    from devctl import process
    from devctl.process import ProcessResult

    ctx = context(workspace)
    if isinstance(step, ts.NodeStep):
        node_tools(ctx.directory, **{step.argv[0]: "sys.exit(0)"})
    observed: list[tuple[list[str], Path, float]] = []

    def timeout(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        assert env is not None
        assert input_text is None
        observed.append((list(argv), cwd, timeout_seconds))
        return ProcessResult(list(argv), 0, "", "", timeout_seconds, timed_out=True)

    monkeypatch.setattr(process, "run_process", timeout)
    assert step.run(ctx).status == "blocked"
    assert observed[0][1] == ctx.directory
    expected = (
        1800 if isinstance(step, ts.NodeStep) else (600 if isinstance(step, ts.AuditStep) else 1200)
    )
    assert observed[0][2] == expected
    if isinstance(step, ts.NodeStep):
        assert observed[0][0] == [
            str(ctx.directory / "node_modules/.bin" / step.argv[0]),
            *step.argv[1:],
        ]
    else:
        assert observed[0][0] == (
            ["npm", "audit", "--json"]
            if isinstance(step, ts.AuditStep)
            else ["npm", "ci", "--no-audit", "--no-fund"]
        )
