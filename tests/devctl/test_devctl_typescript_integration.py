"""Offline: TypeScript exception policies and references with simulated Node tools."""

import json

import pytest

from check_workspace import Workspace, fake_tool
from devctl.check.exceptions import ExceptionsStep
from devctl.check.references import resolve
from devctl.check.tracked import TrackedFiles
from devctl.settings import ProjectStack

TS = ProjectStack("typescript", "frontend")


def test_an_unmarked_suppression_fails_and_a_marked_one_passes(workspace: Workspace) -> None:
    path = "frontend/src/a.ts"
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write(path, "console.log(x); // eslint-disable-line no-console\n")
    ctx = workspace.context(stacks=(TS,))
    result = ExceptionsStep().run(ctx)
    assert result.status == "failed"
    assert f"{path}:1: suppression eslint:no-console needs" in result.details[0]
    workspace.write(
        path, "console.log(x); // eslint-disable-line no-console -- rs-exception: EX-1\n"
    )
    workspace.write(
        ".rapid-ship/exceptions.toml",
        f'[[exception]]\nid="EX-1"\npath="{path}"\nrule="eslint:no-console"\n'
        'reason="Calls a diagnostic"\nremove_when="Diagnostic is removed"\n',
    )
    assert ExceptionsStep().run(ctx).status == "passed"


def test_a_file_outside_the_typescript_stack_has_no_typescript_forms(workspace: Workspace) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write("scripts/a.ts", "// eslint-disable-line no-console\n")
    assert ExceptionsStep().run(workspace.context(stacks=(TS,))).status == "passed"


@pytest.mark.parametrize(
    "name",
    [
        "knip.json",
        ".knip.json",
        ".knip.jsonc",
        "knip.ts",
        "knip.config.ts",
        "knip.js",
        "knip.config.js",
        "package.json",
    ],
)
def test_another_knip_settings_file_fails(workspace: Workspace, name: str) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write(f"frontend/{name}", '{"knip": {}}')
    result = ExceptionsStep().run(workspace.context(stacks=(TS,)))
    assert result.status == "failed"
    assert (
        f"frontend/{name}: devctl reads knip's settings only from knip.jsonc; move them there"
        in result.details
    )


@pytest.mark.parametrize("name", ["knip.jsonc", "package.json"])
def test_malformed_knip_settings_name_the_path(workspace: Workspace, name: str) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write(f"frontend/{name}", "{")
    result = ExceptionsStep().run(workspace.context(stacks=(TS,)))
    assert result.status == "blocked"
    assert result.details[0].startswith(f"frontend/{name}:")


@pytest.mark.parametrize("severity", ['"error"', "2", '["error", {}]', '"warn"', "0", "null"])
def test_an_eslint_reference_resolves_when_the_rule_is_an_error(
    workspace: Workspace, severity: str
) -> None:
    for name in ("package.json", "tsconfig.json", "eslint.config.js"):
        workspace.write(f"frontend/{name}", "{}")
    tool = fake_tool(
        workspace.root / "frontend/node_modules/.bin",
        "eslint",
        f"print({json.dumps({'rules': {'no-console': json.loads(severity)}})!r})",
    )
    workspace.stage()
    ctx = workspace.context(stacks=(TS,))
    tracked = TrackedFiles.read(ctx.repo)
    for _ in range(2):
        reason = resolve("eslint:no-console", ctx, tracked, "frontend/AGENTS.md")
        assert (reason is None) == (severity in ('"error"', "2", '["error", {}]'))
    rows = [json.loads(line) for line in tool.with_suffix(".log").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["argv"] == ["--print-config", "src/index.ts"]
    assert rows[0]["cwd"] == str(workspace.root / "frontend")


def test_a_type_reference_resolves_when_tsc_lists_the_file(workspace: Workspace) -> None:
    workspace.write("frontend/tsconfig.json", "{}")
    for name in ("a.ts", "b.mts", "c.cts", "d.tsx", "unchecked.ts"):
        workspace.write(f"frontend/src/{name}", "")
    paths = [
        str(workspace.root / f"frontend/src/{name}") for name in ("a.ts", "b.mts", "c.cts", "d.tsx")
    ]
    tool = fake_tool(
        workspace.root / "frontend/node_modules/.bin", "tsc", f"print({chr(10).join(paths)!r})"
    )
    workspace.stage()
    ctx = workspace.context(stacks=(TS, ProjectStack("python", "frontend")))
    tracked = TrackedFiles.read(ctx.repo)
    for name in ("a.ts", "b.mts", "c.cts", "d.tsx"):
        assert resolve(f"type:frontend/src/{name}", ctx, tracked, "frontend/AGENTS.md") is None
    assert (
        resolve("type:frontend/src/unchecked.ts", ctx, tracked, "README.md")
        == "type:frontend/src/unchecked.ts: tsc does not check frontend/src/unchecked.ts"
    )
    rows = [json.loads(line) for line in tool.with_suffix(".log").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["argv"] == ["--listFilesOnly", "-p", "tsconfig.json"]
    assert rows[0]["cwd"] == str(workspace.root / "frontend")


@pytest.mark.parametrize(
    ("name", "reference"),
    [
        ("package.json", "eslint:no-console"),
        ("eslint.config.js", "eslint:no-console"),
        ("tsconfig.json", "eslint:no-console"),
        ("tsconfig.json", "type:frontend/src/a.ts"),
        ("src/a.ts", "type:frontend/src/a.ts"),
    ],
)
@pytest.mark.parametrize("state", ["untracked", "ignored", "symlink"])
def test_typescript_references_require_tracked_inputs(
    workspace: Workspace, name: str, reference: str, state: str
) -> None:
    for item in ("package.json", "tsconfig.json", "eslint.config.js", "src/a.ts"):
        workspace.write(f"frontend/{item}", "{}")
        if item != name:
            workspace.git("add", f"frontend/{item}")
    if state == "ignored":
        workspace.write(".gitignore", f"/frontend/{name}\n")
    elif state == "symlink":
        (workspace.root / "frontend" / name).unlink()
        workspace.write("untracked-target", "{}")
        workspace.link(f"frontend/{name}", str(workspace.root / "untracked-target"))
        workspace.git("add", f"frontend/{name}")
    tool = fake_tool(
        workspace.root / "frontend/node_modules/.bin",
        "eslint" if reference.startswith("eslint") else "tsc",
        "raise RuntimeError('must not run')",
    )
    ctx = workspace.context(stacks=(TS,))
    reason = resolve(reference, ctx, TrackedFiles.read(ctx.repo), "frontend/AGENTS.md")
    assert reason
    assert "tracked" in reason
    assert not tool.with_suffix(".log").exists()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('{"ignore": ["a", "b"]}', "holds 2 items on one line"),
        ('{"workspaces": {"app": {"ignore": ["a"]}}}', "allowlist below the top level"),
        (
            '{\n"ignoreDependencies": [\n"unused",\n],\n}',
            "suppression knip.ignoreDependencies:unused needs",
        ),
    ],
)
def test_knip_allowlist_policy_reaches_the_step(
    workspace: Workspace, text: str, expected: str
) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write("frontend/knip.jsonc", text)
    result = ExceptionsStep().run(workspace.context(stacks=(TS,)))
    assert result.status == "failed"
    assert any(expected in detail for detail in result.details)


def test_marked_knip_item_uses_its_literal_rule(workspace: Workspace) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(
        "frontend/knip.jsonc", '{\n"ignore": [\n"src/a file.ts", // rs-exception: EX-1\n],\n}'
    )
    workspace.write(
        ".rapid-ship/exceptions.toml",
        '[[exception]]\nid="EX-1"\npath="frontend/knip.jsonc"\nrule="knip.ignore:src/a file.ts"\n'
        'reason="External entry point"\nremove_when="Entry point is tracked"\n',
    )
    result = ExceptionsStep().run(workspace.context(stacks=(TS,)))
    assert result.status == "passed", result.details


def test_type_references_choose_the_checker_in_a_shared_directory(workspace: Workspace) -> None:
    workspace.write("frontend/pyproject.toml", '[tool.mypy]\nfiles=["src"]\n')
    workspace.write("frontend/src/a.py", "")
    workspace.write("frontend/src/a.pyi", "")
    workspace.stage()
    ctx = workspace.context(stacks=(TS, ProjectStack("python", "frontend")))
    tracked = TrackedFiles.read(ctx.repo)
    for extension in ("py", "pyi"):
        assert (
            resolve(f"type:frontend/src/a.{extension}", ctx, tracked, "frontend/AGENTS.md") is None
        )
    ts_ctx = workspace.context(stacks=(TS,))
    assert "unknown reference kind type" in (
        resolve("type:frontend/src/a.py", ts_ctx, tracked, "README.md") or ""
    )
    assert "unknown reference kind ruff" in (
        resolve("ruff:F401", ts_ctx, tracked, "frontend/AGENTS.md") or ""
    )
    ambiguous = workspace.context(stacks=(TS, ProjectStack("typescript", "other")))
    reason = resolve("type:frontend/src/a.ts", ambiguous, tracked, "README.md")
    assert reason
    assert "typescript (frontend), typescript (other)" in reason
    assert "test:<path>::<name>" in reason


def test_a_typescript_reference_without_node_modules_names_npm_ci(workspace: Workspace) -> None:
    for name in ("package.json", "package-lock.json", "tsconfig.json", "eslint.config.js"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.stage()
    ctx = workspace.context(stacks=(TS,))
    assert (
        resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md")
        == "eslint:no-console: cannot run eslint in frontend: "
        "eslint is not installed; run npm ci there"
    )


def test_staging_inputs_and_a_fresh_snapshot_allow_resolution(workspace: Workspace) -> None:
    for name in ("package.json", "tsconfig.json", "eslint.config.js", "src/a.ts"):
        workspace.write(f"frontend/{name}", "{}")
    tool = fake_tool(
        workspace.root / "frontend/node_modules/.bin",
        "tsc",
        f"print({str(workspace.root / 'frontend/src/a.ts')!r})",
    )
    ctx = workspace.context(stacks=(TS,))
    old = TrackedFiles.read(ctx.repo)
    assert resolve("type:frontend/src/a.ts", ctx, old, "README.md") is not None
    assert not tool.with_suffix(".log").exists()
    workspace.stage()
    current = TrackedFiles.read(ctx.repo)
    assert resolve("type:frontend/src/a.ts", ctx, current, "README.md") is None
    tool.write_text(tool.read_text().replace("frontend/src/a.ts", "frontend/src/other.ts"))
    assert resolve("type:frontend/src/a.ts", ctx, current, "README.md") is None
    assert (
        resolve("type:frontend/src/a.ts", ctx, TrackedFiles.read(ctx.repo), "README.md") is not None
    )


def test_case_mismatched_input_is_rejected_before_running_tools(workspace: Workspace) -> None:
    workspace.write("frontend/tsconfig.json", "{}")
    workspace.write("frontend/src/a.ts", "")
    workspace.stage()
    ctx = workspace.context(stacks=(TS,))
    tracked = TrackedFiles.read(ctx.repo)
    reason = resolve("type:frontend/src/A.ts", ctx, tracked, "README.md")
    assert reason
    assert "case" in reason


def test_eslint_inputs_can_be_staged_then_resolved(workspace: Workspace) -> None:
    for name in ("package.json", "tsconfig.json", "eslint.config.js"):
        workspace.write(f"frontend/{name}", "{}")
    tool = fake_tool(
        workspace.root / "frontend/node_modules/.bin",
        "eslint",
        'print(\'{"rules": {"no-console": "error"}}\')',
    )
    ctx = workspace.context(stacks=(TS,))
    assert resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md") is not None
    assert not tool.with_suffix(".log").exists()
    workspace.stage()
    assert resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md") is None


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("/* eslint no-console: 'off' */", "eslint:no-console"),
        (" * @beta", "knip:@beta"),
        ("test('x', {skip: true}, () => {})", "skip"),
        ("# prettier-ignore", "prettier-ignore"),
    ],
)
def test_typescript_forms_reach_the_exception_step(
    workspace: Workspace, source: str, rule: str
) -> None:
    workspace.write(".rapid-ship/kit.lock", 'kit_version="0.2.0"\nstack="typescript"\n')
    workspace.write(".rapid-ship/exceptions.toml", "")
    workspace.write("frontend/src/a.ts", source)
    result = ExceptionsStep().run(workspace.context(stacks=(TS,)))
    assert result.status == "failed"
    assert any(f"suppression {rule} needs" in detail for detail in result.details)
