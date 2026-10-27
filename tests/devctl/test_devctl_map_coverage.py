"""Every maintained directory has a guide, and every guide is reachable."""

from __future__ import annotations

from check_workspace import Workspace, project_settings, skill_text
from devctl.check.map import MapStep, coverage_errors, guides, reachability_errors
from devctl.check.tracked import TrackedFiles

HINT = "add an AGENTS.md guide, or list the directory under [map] unguided"


def layout(workspace: Workspace) -> TrackedFiles:
    workspace.write("AGENTS.md", "[Docs](docs/AGENTS.md)\n")
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.write("tools/devctl/x.py", "")
    workspace.write("src/app/__init__.py", "")
    workspace.write("src/app/api/routes.py", "")
    workspace.write(".github/workflows/ci.yml", "on: push\n")
    workspace.stage()
    return TrackedFiles.read(workspace.context().repo)


def test_top_level_and_source_root_children_need_guides(workspace: Workspace) -> None:
    tracked = layout(workspace)

    assert coverage_errors(tracked, project_settings(source_roots=("src/app",))) == [
        f"src/: {HINT}",
        f"src/app/api/: {HINT}",
        f"tools/: {HINT}",
    ]


def test_unguided_and_excluded_directories_need_no_guide(workspace: Workspace) -> None:
    tracked = layout(workspace)
    project = project_settings(
        source_roots=("src/app",), unguided=("src", "src/app/api"), map_exclude=("tools",)
    )

    assert coverage_errors(tracked, project) == []


def test_bytecode_directories_need_no_guide(workspace: Workspace) -> None:
    workspace.write("src/app/__init__.py", "")
    workspace.write("src/app/__pycache__/__init__.cpython-312.pyc", "")
    workspace.stage()
    tracked = TrackedFiles.read(workspace.context().repo)
    project = project_settings(source_roots=("src/app",), unguided=("src",))

    assert "src/app/__pycache__/__init__.cpython-312.pyc" in tracked.files
    assert coverage_errors(tracked, project) == []


def test_missing_source_root_is_reported(workspace: Workspace) -> None:
    tracked = layout(workspace)

    errors = coverage_errors(tracked, project_settings(source_roots=("src/other",)))

    assert "src/other: source root holds no tracked files; fix [map] source_roots" in errors


def test_a_source_root_of_untracked_files_must_be_staged(workspace: Workspace) -> None:
    layout(workspace)
    workspace.write("src/other/__init__.py", "")
    tracked = TrackedFiles.read(workspace.context().repo)

    errors = coverage_errors(tracked, project_settings(source_roots=("src/other",)))

    assert (
        "src/other: source root holds no tracked files; stage its files with git add, "
        "or fix [map] source_roots"
    ) in errors


def test_every_guide_is_reachable_from_the_root(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", "[Docs](docs/)\n")
    workspace.write("docs/AGENTS.md", "[Plans](plans/AGENTS.md)\n")
    workspace.write("docs/plans/AGENTS.md", "# Plans\n")
    workspace.write("docs/orphan/AGENTS.md", "# Orphan\n")
    workspace.stage()
    context = workspace.context()
    tracked = TrackedFiles.read(context.repo)
    found = guides(tracked, context.project)

    assert reachability_errors(tracked, found) == [
        "docs/orphan/AGENTS.md: not reachable by links from AGENTS.md; "
        "link it from its parent guide"
    ]


def test_missing_root_guide_is_reported(workspace: Workspace) -> None:
    workspace.write("docs/AGENTS.md", "# Docs\n")
    tracked = TrackedFiles.read(workspace.context().repo)

    assert reachability_errors(tracked, ["docs/AGENTS.md"])[0].startswith("AGENTS.md:")


def test_excluded_template_guides_are_not_part_of_the_map(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.write("pkg/templates/common/AGENTS.md", "[Missing](nowhere.md)\n")
    workspace.stage()

    result = MapStep().run(
        workspace.context(source_roots=(), unguided=("pkg",), map_exclude=("pkg/templates/common",))
    )

    assert result.status == "passed", result.details


def test_link_targets_are_normalised_before_they_reach_a_guide(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", "[Docs](./api/../docs/) and [Spaced](<spaced%20dir/AGENTS.md>)\n")
    workspace.write("docs/AGENTS.md", "[Up](../docs/sub/#top)\n")
    workspace.write("docs/sub/AGENTS.md", "# Sub\n")
    workspace.write("spaced dir/AGENTS.md", "# Spaced\n")
    workspace.stage()
    context = workspace.context()
    tracked = TrackedFiles.read(context.repo)
    found = guides(tracked, context.project)

    assert reachability_errors(tracked, found) == []


def test_links_that_leave_the_repository_or_are_not_files_reach_nothing(
    workspace: Workspace,
) -> None:
    workspace.write(
        "AGENTS.md",
        "[Web](https://example.com/docs/AGENTS.md) [Anchor](#docs) [Out](../docs/)\n",
    )
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.stage()
    context = workspace.context()
    tracked = TrackedFiles.read(context.repo)
    found = guides(tracked, context.project)

    assert reachability_errors(tracked, found) == [
        "docs/AGENTS.md: not reachable by links from AGENTS.md; link it from its parent guide"
    ]


def test_an_unreadable_guide_links_nothing(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", "[Docs](docs/)\n")
    workspace.write("docs/AGENTS.md", "")
    (workspace.root / "docs/AGENTS.md").write_bytes(b"\xff\xfe[Sub](sub/)\n")
    workspace.write("docs/sub/AGENTS.md", "# Sub\n")
    workspace.stage()
    context = workspace.context()
    tracked = TrackedFiles.read(context.repo)
    found = guides(tracked, context.project)

    assert reachability_errors(tracked, found) == [
        "docs/sub/AGENTS.md: not reachable by links from AGENTS.md; link it from its parent guide"
    ]


def test_the_step_fails_on_a_directory_without_a_guide(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.write("tools/devctl/x.py", "")
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert result.status == "failed"
    assert result.details == (f"tools/: {HINT}",)


def test_the_step_fails_on_a_guide_no_link_reaches(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert result.status == "failed"
    assert result.details == (
        "docs/AGENTS.md: not reachable by links from AGENTS.md; link it from its parent guide",
    )


def test_the_step_reports_links_then_coverage_then_reachability_then_aliases(
    workspace: Workspace,
) -> None:
    workspace.root_guide("[Missing](nowhere.md)\n")
    workspace.write("tools/devctl/x.py", "")
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.write(".agents/skills/demo/SKILL.md", skill_text("demo"))
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert result.status == "failed"
    assert result.details == (
        "AGENTS.md:1: missing target 'nowhere.md'; update the navigation link",
        f"tools/: {HINT}",
        "docs/AGENTS.md: not reachable by links from AGENTS.md; link it from its parent guide",
        ".claude/skills/demo: add a relative symlink to ../../.agents/skills/demo "
        "and track it in Git",
    )


def test_an_untracked_directory_and_its_guide_are_not_part_of_the_map(
    workspace: Workspace,
) -> None:
    workspace.root_guide()
    workspace.stage()
    workspace.write("tools/devctl/x.py", "")
    workspace.write("tools/AGENTS.md", "[Missing](nowhere.md)\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == ("passed", ())


def test_an_untracked_guide_does_not_cover_its_directory(workspace: Workspace) -> None:
    workspace.root_guide("[Tools](tools/)\n")
    workspace.write("tools/devctl/x.py", "")
    workspace.stage()
    workspace.write("tools/AGENTS.md", "[Missing](nowhere.md)\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == (
        "failed",
        ("tools/AGENTS.md: not tracked; stage it with git add",),
    )


def test_an_ignored_guide_points_to_the_gitignore_rule(workspace: Workspace) -> None:
    workspace.root_guide("[Tools](tools/)\n")
    workspace.write(".gitignore", "/tools/AGENTS.md\n")
    workspace.write("tools/devctl/x.py", "")
    workspace.stage()
    workspace.write("tools/AGENTS.md", "# Tools\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == (
        "failed",
        (
            "tools/AGENTS.md: not tracked, and git add cannot stage it; if git check-ignore -v "
            "tools/AGENTS.md names a .gitignore rule, narrow or remove that rule, then stage it",
        ),
    )


def test_a_staged_guide_counts_before_its_commit(workspace: Workspace) -> None:
    workspace.root_guide("[Tools](tools/)\n")
    workspace.write("tools/devctl/x.py", "")
    workspace.commit()
    workspace.write("tools/AGENTS.md", "[Missing](nowhere.md)\n")
    workspace.git("add", "tools/AGENTS.md")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == (
        "failed",
        ("tools/AGENTS.md:1: missing target 'nowhere.md'; update the navigation link",),
    )
