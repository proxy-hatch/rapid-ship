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
