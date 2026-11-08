"""Offline: ESLint lookup and tracked-input boundaries through the public resolver."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from check_workspace import Workspace
from devctl import node
from devctl.check.references import resolve
from devctl.check.tracked import TrackedFiles
from devctl.settings import ProjectStack


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    calls: list[Path] = []

    def read(directory: Path) -> Mapping[str, object]:
        calls.append(directory)
        return {"rules": {"no-console": "error"}}

    monkeypatch.setattr(node, "eslint_config", read)
    return calls


@pytest.mark.parametrize(
    ("selected", "other"),
    [
        ("js", "mjs"),
        ("js", "cjs"),
        ("js", "ts"),
        ("js", "mts"),
        ("js", "cts"),
        ("mjs", "cjs"),
        ("mjs", "ts"),
        ("mjs", "mts"),
        ("mjs", "cts"),
        ("cjs", "ts"),
        ("cjs", "mts"),
        ("cjs", "cts"),
        ("ts", "mts"),
        ("ts", "cts"),
        ("mts", "cts"),
    ],
)
@pytest.mark.parametrize("location", ["frontend", "frontend/src"])
def test_the_preferred_config_must_be_tracked_before_the_reader_runs(
    workspace: Workspace, reader: list[Path], selected: str, other: str, location: str
) -> None:
    for name in ("package.json", "tsconfig.json"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.write(f"{location}/eslint.config.{other}", "")
    workspace.stage()
    chosen = f"{location}/eslint.config.{selected}"
    workspace.write(chosen, "")
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    reason = resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md")
    assert reason
    assert chosen in reason
    assert "git add" in reason
    assert reader == []


@pytest.mark.parametrize("extension", ["js", "mjs", "cjs", "ts", "mts", "cts"])
def test_supported_configs_ignore_unrelated_backups(
    workspace: Workspace, reader: list[Path], extension: str
) -> None:
    for name in ("package.json", "tsconfig.json", f"eslint.config.{extension}"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.stage()
    workspace.write("frontend/eslint.config.backup", "")
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    tracked = TrackedFiles.read(ctx.repo)
    for _ in range(2):
        assert resolve("eslint:no-console", ctx, tracked, "README.md") is None
    assert reader == [workspace.root / "frontend"]


@pytest.mark.parametrize("state", ["untracked", "ignored", "symlink", "missing"])
def test_probe_directory_config_shadows_the_stack_config(
    workspace: Workspace, reader: list[Path], state: str
) -> None:
    for name in ("package.json", "tsconfig.json", "eslint.config.js"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.stage()
    chosen = "frontend/src/eslint.config.cts"
    workspace.write(chosen, "")
    if state == "ignored":
        workspace.write(".gitignore", f"/{chosen}\n")
    elif state in ("symlink", "missing"):
        (workspace.root / chosen).unlink()
        if state == "symlink":
            workspace.write("untracked-config", "")
        workspace.link(chosen, "../../untracked-config")
        workspace.git("add", chosen)
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    reason = resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md")
    assert reason
    assert chosen in reason
    assert "tracked" in reason
    assert reader == []


def test_a_parent_config_cannot_replace_a_missing_stack_config(
    workspace: Workspace, reader: list[Path]
) -> None:
    for name in ("package.json", "tsconfig.json"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.write("eslint.config.js", "")
    workspace.stage()
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    reason = resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md")
    assert reason
    assert "frontend/eslint.config.js" in reason
    assert reader == []


def test_a_tracked_probe_config_is_used_without_the_stack_config(
    workspace: Workspace, reader: list[Path]
) -> None:
    for name in ("package.json", "tsconfig.json", "src/eslint.config.mts"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.stage()
    workspace.write("frontend/eslint.config.js", "")
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    tracked = TrackedFiles.read(ctx.repo)
    assert resolve("eslint:no-console", ctx, tracked, "README.md") is None
    assert reader == [workspace.root / "frontend"]
    # Input validation must still precede a cached result.
    workspace.write("frontend/src/eslint.config.js", "")
    reason = resolve("eslint:no-console", ctx, tracked, "README.md")
    assert reason
    assert "frontend/src/eslint.config.js" in reason
    assert reader == [workspace.root / "frontend"]


def test_config_case_must_match_the_tracked_name(workspace: Workspace, reader: list[Path]) -> None:
    for name in ("package.json", "tsconfig.json", "ESLint.config.js"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.stage()
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    reason = resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md")
    assert reason
    assert "case" in reason
    assert reader == []


def test_eslint_caches_are_isolated_by_stack_directory(
    workspace: Workspace, reader: list[Path]
) -> None:
    stacks = (ProjectStack("typescript", "frontend"), ProjectStack("typescript", "other"))
    for stack in stacks:
        for name in ("package.json", "tsconfig.json", "eslint.config.js"):
            workspace.write(f"{stack.directory}/{name}", "{}")
    workspace.stage()
    ctx = workspace.context(stacks=stacks)
    tracked = TrackedFiles.read(ctx.repo)
    for stack in stacks:
        for _ in range(2):
            assert (
                resolve("eslint:no-console", ctx, tracked, f"{stack.directory}/AGENTS.md") is None
            )
    assert reader == [workspace.root / "frontend", workspace.root / "other"]


def test_a_directory_named_like_a_config_does_not_shadow_a_file(
    workspace: Workspace, reader: list[Path]
) -> None:
    for name in ("package.json", "tsconfig.json", "eslint.config.cjs"):
        workspace.write(f"frontend/{name}", "{}")
    workspace.stage()
    (workspace.root / "frontend/eslint.config.js").mkdir()
    ctx = workspace.context(stacks=(ProjectStack("typescript", "frontend"),))
    assert resolve("eslint:no-console", ctx, TrackedFiles.read(ctx.repo), "README.md") is None
    assert reader == [workspace.root / "frontend"]
