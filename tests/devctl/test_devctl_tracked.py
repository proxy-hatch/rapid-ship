"""TrackedFiles: why a file that the work tree holds does not count, and how to fix it."""

from __future__ import annotations

from pathlib import Path

from check_workspace import Workspace
from devctl.check.tracked import TrackedFiles


def why_untracked(workspace: Workspace, path: str) -> str:
    return TrackedFiles.read(workspace.context().repo).why_untracked(path)


def test_an_untracked_file_is_staged_by_its_own_name(workspace: Workspace) -> None:
    workspace.write("docs/AGENTS.md", "# Docs\n")

    assert why_untracked(workspace, "docs/AGENTS.md") == "not tracked; stage it with git add"


def test_a_directory_of_untracked_files_is_staged_by_its_own_name(workspace: Workspace) -> None:
    workspace.write("src/app/api/routes.py", "")

    assert why_untracked(workspace, "src/app/api/") == "not tracked; stage it with git add"


def test_a_file_behind_a_tracked_symlink_is_staged_where_it_lives(workspace: Workspace) -> None:
    workspace.write("lib/auth.py", "")
    workspace.link("src/lib", "../lib")
    workspace.git("add", "src/lib")

    assert why_untracked(workspace, "src/lib/auth.py") == (
        "not tracked; stage lib/auth.py with git add"
    )


def test_a_file_behind_an_untracked_symlink_stages_the_symlink(workspace: Workspace) -> None:
    workspace.write("lib/auth.py", "")
    workspace.stage()
    workspace.link("src/lib", "../lib")

    assert why_untracked(workspace, "src/lib/auth.py") == "not tracked; stage src/lib with git add"


def test_a_name_that_git_tracks_in_another_case_is_named(workspace: Workspace) -> None:
    workspace.write("Readme.md", "# Demo\n")
    workspace.stage()

    assert why_untracked(workspace, "README.md") == (
        "not tracked in that case; git tracks Readme.md, so make the two names' case match"
    )


def test_an_ignored_file_points_to_the_gitignore_rule(workspace: Workspace) -> None:
    workspace.write(".gitignore", "AGENTS.md\n")
    workspace.write("docs/AGENTS.md", "# Docs\n")

    assert why_untracked(workspace, "docs/AGENTS.md") == (
        "not tracked, and git add cannot stage it; if git check-ignore -v docs/AGENTS.md "
        "names a .gitignore rule, narrow or remove that rule, then stage it"
    )


def test_a_path_that_resolves_outside_the_repository_is_named(
    workspace: Workspace, tmp_path: Path
) -> None:
    (tmp_path / "outside").mkdir()
    (tmp_path / "outside" / "auth.py").write_text("")
    workspace.link("src/ext", str(tmp_path / "outside"))
    workspace.git("add", "src/ext")

    assert why_untracked(workspace, "src/ext/auth.py") == (
        "not tracked, because it resolves outside the repository"
    )


def test_an_untracked_intermediate_symlink_is_staged_by_its_own_name(workspace: Workspace) -> None:
    workspace.write("real/file.py", "")
    workspace.link("bridge", "real")
    workspace.link("alias", "bridge")
    workspace.git("add", "real/file.py", "alias")

    assert why_untracked(workspace, "alias/file.py") == "not tracked; stage bridge with git add"


def test_an_ignored_intermediate_symlink_points_to_the_gitignore_rule(
    workspace: Workspace,
) -> None:
    workspace.write(".gitignore", "bridge\n")
    workspace.write("real/file.py", "")
    workspace.link("bridge", "real")
    workspace.link("alias", "bridge")
    workspace.git("add", ".gitignore", "real/file.py", "alias")

    assert "names a .gitignore rule" in why_untracked(workspace, "alias/file.py")


def test_a_fully_tracked_symlink_chain_holds(workspace: Workspace) -> None:
    workspace.write("real/file.py", "")
    workspace.link("bridge", "real")
    workspace.link("alias", "bridge")
    workspace.git("add", "real/file.py", "bridge", "alias")

    assert TrackedFiles.read(workspace.context().repo).holds("alias/file.py")


def test_a_symlink_loop_is_handled_safely(workspace: Workspace) -> None:
    workspace.link("loop_a", "loop_b")
    workspace.link("loop_b", "loop_a")
    workspace.git("add", "loop_a", "loop_b")

    tf = TrackedFiles.read(workspace.context().repo)
    assert not tf.holds("loop_a/file.py")
    assert why_untracked(workspace, "loop_a/file.py") == (
        "not tracked, because it resolves outside the repository"
    )


def test_an_escape_and_reentry_symlink_fails_containment(
    workspace: Workspace, tmp_path: Path
) -> None:
    workspace.write("real/file.py", "")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "reenter").symlink_to(workspace.root / "real")
    workspace.link("alias", str(outside / "reenter"))
    workspace.git("add", "real/file.py", "alias")

    tf = TrackedFiles.read(workspace.context().repo)
    assert not tf.holds("alias/file.py")
    assert why_untracked(workspace, "alias/file.py") == (
        "not tracked, because it resolves outside the repository"
    )
