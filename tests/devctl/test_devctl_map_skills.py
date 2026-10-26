"""Offline: SKILL.md files in fixture repositories: each SKILL.md names its directory,
describes itself and is a regular file. The symlinked SKILL.md is a real symlink; Codex's
rejection of it is not run."""

from __future__ import annotations

import pytest

from check_workspace import Workspace, skill_text
from devctl.check.map import MapStep
from devctl.check.map_skills import skill_errors, skill_file_errors


def add_skill(workspace: Workspace, name: str, text: str) -> None:
    workspace.write(f".agents/skills/{name}/SKILL.md", text)
    workspace.link(f".claude/skills/{name}", f"../../.agents/skills/{name}")


def errors(workspace: Workspace) -> list[str]:
    workspace.stage()
    context = workspace.context()
    return skill_errors(context.repo.root, context.repo.tracked_files())


def test_a_project_authored_skill_passes(workspace: Workspace) -> None:
    workspace.root_guide()
    add_skill(workspace, "rs-tdd", skill_text("rs-tdd"))  # as the Kit vendors it
    add_skill(workspace, "release-notes", skill_text("release-notes"))  # not in the lock
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert result.status == "passed", result.details


def test_skill_name_must_match_its_directory(workspace: Workspace) -> None:
    # An unpatched upstream fork: Claude Code would register /tdd, not /rs-tdd.
    add_skill(workspace, "rs-tdd", skill_text("tdd"))

    assert errors(workspace) == [
        ".agents/skills/rs-tdd/SKILL.md: name must be rs-tdd, the directory name"
    ]


@pytest.mark.parametrize(
    "text", ["---\nname: notes\n---\n", "---\nname: notes\ndescription: '  '\n---\n"]
)
def test_skill_description_must_not_be_empty(workspace: Workspace, text: str) -> None:
    add_skill(workspace, "notes", text)

    assert errors(workspace) == [".agents/skills/notes/SKILL.md: description is missing or empty"]


def test_skill_without_front_matter_fails(workspace: Workspace) -> None:
    add_skill(workspace, "notes", "# Notes\n")

    assert errors(workspace) == [
        ".agents/skills/notes/SKILL.md: no front matter; start the file with --- "
        "and the keys name and description"
    ]


SYMLINK = (
    ".agents/skills/demo/SKILL.md: is a symlink; make it a regular file, "
    "because Codex rejects a symlinked SKILL.md"
)


def symlinked_skill(workspace: Workspace) -> None:
    """The skill `demo` whose SKILL.md links to real.md, a valid SKILL.md in its directory."""
    workspace.write(".agents/skills/demo/real.md", skill_text("demo"))
    (workspace.root / ".agents/skills/demo/SKILL.md").symlink_to("real.md")
    workspace.link(".claude/skills/demo", "../../.agents/skills/demo")


def file_errors(workspace: Workspace) -> list[str]:
    workspace.stage()
    context = workspace.context()
    return skill_file_errors(context.repo.root, context.repo.tracked_files())


def test_a_symlinked_skill_md_fails_the_map_step(workspace: Workspace) -> None:
    workspace.root_guide()
    symlinked_skill(workspace)
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert file_errors(workspace) == [SYMLINK]
    assert (result.status, result.details) == ("failed", (SYMLINK,))


def test_a_regular_skill_md_has_no_file_error(workspace: Workspace) -> None:
    add_skill(workspace, "demo", skill_text("demo"))

    assert file_errors(workspace) == []


def test_an_untracked_skill_is_not_checked(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.stage()
    add_skill(workspace, "draft", "# Draft\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == ("passed", ())


@pytest.mark.parametrize(
    "directory", [".agents/skills/notes", "pkg/skills/notes"], ids=["in place", "in a package"]
)
def test_an_untracked_skill_md_must_be_staged(workspace: Workspace, directory: str) -> None:
    workspace.root_guide()
    workspace.write(f"{directory}/README.md", "# Notes\n")
    if directory != ".agents/skills/notes":
        workspace.link(".agents/skills/notes", f"../../{directory}")
    workspace.link(".claude/skills/notes", "../../.agents/skills/notes")
    workspace.stage()
    # Neither front matter nor a regular file: the skill rules must not read it.
    (workspace.root / directory / "SKILL.md").symlink_to("README.md")

    result = MapStep().run(workspace.context(source_roots=(), unguided=("pkg",)))

    assert (result.status, result.details) == (
        "failed",
        (".agents/skills/notes/SKILL.md: not tracked; stage it with git add",),
    )
