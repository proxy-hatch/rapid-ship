"""Offline: Pattern files and Rules bullets in fixture repositories."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.check.map import (
    MapStep,
    guides,
    pattern_errors,
    pattern_lesson_errors,
    rule_errors,
)
from devctl.check.markdown import rules_items
from devctl.check.tracked import TrackedFiles


def test_unclosed_or_invalid_pattern_front_matter_fails(workspace: Workspace) -> None:
    workspace.write("docs/patterns/a.md", "---\ntask: x\n")
    workspace.write("docs/patterns/b.md", "---\n- a list\n---\n")
    workspace.stage()
    context = workspace.context()

    assert pattern_errors(context, TrackedFiles.read(context.repo)) == [
        "docs/patterns/a.md: front matter is not closed with ---",
        "docs/patterns/b.md: front matter must be a mapping",
    ]


def test_invalid_yaml_in_pattern_is_reported_on_one_line(workspace: Workspace) -> None:
    workspace.write("docs/patterns/a.md", "---\ntask: [unclosed\nreference: x\n---\n")
    workspace.stage()
    context = workspace.context()

    [error] = pattern_errors(context, TrackedFiles.read(context.repo))

    assert error.startswith("docs/patterns/a.md: ")
    assert "\n" not in error


def test_a_pattern_reference_and_test_that_git_does_not_track_fail(workspace: Workspace) -> None:
    workspace.write("src/app/settings.py", "")
    workspace.write("tests/test_settings.py", "def test_reads(): pass\n")
    workspace.write(
        "docs/patterns/settings.md",
        "---\nreference: src/app/settings.py\n"
        "enforced_by: [test:tests/test_settings.py::test_reads]\n---\n",
    )
    workspace.git("add", "docs/patterns/settings.md")
    context = workspace.context()

    assert pattern_errors(context, TrackedFiles.read(context.repo)) == [
        "docs/patterns/settings.md: reference names src/app/settings.py, which is not tracked; "
        "stage it with git add",
        "docs/patterns/settings.md: test:tests/test_settings.py::test_reads: "
        "tests/test_settings.py is not tracked; stage it with git add",
    ]


def test_pattern_reference_and_enforcement(workspace: Workspace) -> None:
    workspace.write("src/app/settings.py", "")
    workspace.write(
        "docs/patterns/settings.md",
        "---\nreference: src/app/settings.py\nenforced_by: [check:map]\n---\n",
    )
    workspace.write(
        "docs/patterns/empty.md", "---\nreference: src/app/settings.py\nenforced_by: []\n---\n"
    )
    workspace.write(
        "docs/patterns/broken.md",
        "---\nreference: src/app/gone.py\nenforced_by: [check:nope]\n---\n",
    )
    workspace.stage()
    context = workspace.context()

    errors = pattern_errors(context, TrackedFiles.read(context.repo))

    assert errors == [
        "docs/patterns/broken.md: reference names src/app/gone.py, which does not exist",
        "docs/patterns/broken.md: check:nope: no devctl check step is named nope",
        "docs/patterns/empty.md: enforced_by is missing or empty",
    ]


PATTERN = """---
task: Read configuration
reference: src/app/settings.py
enforced_by:
  - check:map
---
One typed settings module reads configuration.

## Lessons

It validates every value where it enters.
"""


def lessons(workspace: Workspace, text: str) -> list[str]:
    workspace.write("src/app/settings.py", "")
    workspace.write("docs/patterns/settings.md", text)
    workspace.stage()
    context = workspace.context()
    return pattern_lesson_errors(context, TrackedFiles.read(context.repo))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (PATTERN.replace("task: Read configuration\n", ""), "task is missing or empty"),
        (PATTERN.replace("task: Read configuration", 'task: ""'), "task is missing or empty"),
        (PATTERN.split("## Lessons")[0], "## Lessons is missing or empty"),
        (
            PATTERN.replace("It validates every value where it enters.\n", ""),
            "## Lessons is missing or empty",
        ),
    ],
    ids=["no task", "empty task", "no Lessons", "empty Lessons"],
)
def test_a_pattern_needs_a_task_and_lessons(workspace: Workspace, text: str, message: str) -> None:
    assert lessons(workspace, text) == [f"docs/patterns/settings.md: {message}"]


def test_a_complete_pattern_passes(workspace: Workspace) -> None:
    assert lessons(workspace, PATTERN) == []


def test_a_pattern_without_either_reports_both(workspace: Workspace) -> None:
    text = PATTERN.replace("task: Read configuration\n", "").split("## Lessons")[0]

    assert lessons(workspace, text) == [
        "docs/patterns/settings.md: task is missing or empty",
        "docs/patterns/settings.md: ## Lessons is missing or empty",
    ]


@pytest.mark.parametrize(
    "text",
    [
        PATTERN.replace(
            "## Lessons\n\nIt validates every value where it enters.\n", "### Lessons\n"
        ),
        PATTERN.replace("## Lessons", "```\n## Lessons\n```\n"),
        PATTERN.replace("## Lessons", "## Lesson"),
    ],
    ids=["a level-3 heading", "a heading in a code fence", "another title"],
)
def test_lessons_is_a_level_2_heading_outside_code(workspace: Workspace, text: str) -> None:
    assert lessons(workspace, text) == ["docs/patterns/settings.md: ## Lessons is missing or empty"]


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (PATTERN.replace("---\nOne", "One"), "front matter is not closed with ---"),
        (
            PATTERN.split("---\n", 2)[2],
            "no front matter; start the file with --- and the keys task, reference and enforced_by",
        ),
        ("---\n- task\n---\n" + PATTERN.split("---\n", 2)[2], "front matter must be a mapping"),
    ],
    ids=["front matter not closed", "no front matter", "front matter is a list"],
)
def test_a_front_matter_problem_is_left_to_pattern_errors(
    workspace: Workspace, text: str, message: str
) -> None:
    assert lessons(workspace, text) == []
    context = workspace.context()
    assert pattern_errors(context, TrackedFiles.read(context.repo)) == [
        f"docs/patterns/settings.md: {message}"
    ]


def test_the_pattern_readme_is_not_a_pattern(workspace: Workspace) -> None:
    workspace.write("docs/patterns/README.md", "# Patterns\n")
    workspace.stage()

    context = workspace.context()
    assert pattern_lesson_errors(context, TrackedFiles.read(context.repo)) == []


def test_a_pattern_without_task_or_lessons_fails_the_map_step(workspace: Workspace) -> None:
    workspace.root_guide("[Docs](docs/)\n")
    workspace.write("docs/AGENTS.md", "# Docs\n")
    incomplete = PATTERN.split("## Lessons")[0].replace("task: Read configuration\n", "")
    workspace.write(
        "docs/patterns/settings.md", incomplete.replace("src/app/settings.py", "README.md")
    )
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == (
        "failed",
        (
            "docs/patterns/settings.md: task is missing or empty",
            "docs/patterns/settings.md: ## Lessons is missing or empty",
        ),
    )


GUIDE = """# Root

Some text.

## Rules

- Read settings through `app.settings`. enforced by: check:map
  - This nested note belongs to the rule above.
- Keep handlers thin; the Reviewer checks this
  advisory
- Run the checks before pushing:

  ~~~sh
  - this dash is code, not a rule
  ~~~

  advisory
1. Numbered rules count too. enforced by: `check:map`
- Forgot the marker.
- Points nowhere. enforced by: check:nope

Closing paragraph after the list.

## Other

- Not a rule.
"""


def test_rules_items_skip_nested_lists_and_code() -> None:
    assert [(item.line, item.text) for item in rules_items(GUIDE)] == [
        (7, "Read settings through `app.settings`. enforced by: check:map"),
        (9, "Keep handlers thin; the Reviewer checks this advisory"),
        (11, "Run the checks before pushing: advisory"),
        (18, "Numbered rules count too. enforced by: `check:map`"),
        (19, "Forgot the marker."),
        (20, "Points nowhere. enforced by: check:nope"),
    ]


def test_every_rule_ends_with_a_resolving_marker(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", GUIDE)
    workspace.stage()
    context = workspace.context()
    tracked = TrackedFiles.read(context.repo)
    found = guides(tracked, context.project)

    assert rule_errors(context, tracked, found) == [
        "AGENTS.md:19: end the rule with 'enforced by: <reference>' or 'advisory'",
        "AGENTS.md:20: check:nope: no devctl check step is named nope",
    ]


def test_a_rule_enforced_by_an_untracked_test_fails_the_map_step(workspace: Workspace) -> None:
    workspace.root_guide(
        "# Root\n\n## Rules\n\n- Settings load once. "
        "enforced by: test:tests/test_settings.py::test_reads\n"
    )
    workspace.stage()
    workspace.write("tests/test_settings.py", "def test_reads(): pass\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == (
        "failed",
        (
            "AGENTS.md:5: test:tests/test_settings.py::test_reads: tests/test_settings.py "
            "is not tracked; stage it with git add",
        ),
    )


def test_the_map_step_reports_patterns_rules_and_skills(workspace: Workspace) -> None:
    workspace.root_guide("[Docs](docs/)\n\n## Rules\n\n- Forgot the marker.\n")
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.write("docs/patterns/settings.md", "# Settings\n")
    workspace.write(".agents/skills/notes/SKILL.md", "# Notes\n")
    workspace.link(".claude/skills/notes", "../../.agents/skills/notes")
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert result.status == "failed"
    assert [detail.split(": ")[0] for detail in result.details] == [
        "docs/patterns/settings.md",
        "AGENTS.md:5",
        ".agents/skills/notes/SKILL.md",
    ]


def test_untracked_pattern_files_are_not_checked(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.stage()
    workspace.write("docs/patterns/settings.md", "# Settings\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == ("passed", ())


def test_a_pattern_symlink_to_an_untracked_target_fails_explicitly(workspace: Workspace) -> None:
    workspace.write("src/app/settings.py", "")
    workspace.write("untracked.md", PATTERN)
    workspace.link("docs/patterns/settings.md", "../../untracked.md")
    workspace.git(
        "add",
        "src/app/settings.py",
        "docs/patterns/settings.md",
    )
    context = workspace.context()

    assert pattern_errors(context, TrackedFiles.read(context.repo)) == [
        "docs/patterns/settings.md: not tracked; stage untracked.md with git add"
    ]


def test_a_pattern_symlink_to_an_ignored_target_fails_explicitly(workspace: Workspace) -> None:
    workspace.write(".gitignore", "ignored_pattern.md\n")
    workspace.write("src/app/settings.py", "")
    workspace.write("ignored_pattern.md", PATTERN)
    workspace.link("docs/patterns/settings.md", "../../ignored_pattern.md")
    workspace.stage()
    context = workspace.context()

    errors = pattern_errors(context, TrackedFiles.read(context.repo))
    assert len(errors) == 1
    assert "docs/patterns/settings.md: not tracked, and git add cannot stage it" in errors[0]


def test_a_fully_tracked_pattern_symlink_passes(workspace: Workspace) -> None:
    workspace.write("src/app/settings.py", "")
    workspace.write("docs/patterns/real.md", PATTERN)
    workspace.link("docs/patterns/alias.md", "real.md")
    workspace.stage()
    context = workspace.context()

    assert pattern_errors(context, TrackedFiles.read(context.repo)) == []


def test_feature_map_rule_removed_and_golden_paths_require_no_checks(workspace: Workspace) -> None:
    workspace.root_guide("[Docs](docs/AGENTS.md)\n")
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.write("docs/features/sign-in.md", "# Sign-in without front matter\n")
    workspace.write("docs/golden-paths/api.md", "# Golden path without front matter\n")
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == ("passed", ())


@pytest.mark.parametrize("path", ["frontend/src/a.test.ts", "front end/a.test.ts"])
def test_backticked_rule_references_can_hold_spaces(workspace: Workspace, path: str) -> None:
    workspace.write(path, 'describe("a", () => { test("b", () => {}); });')
    workspace.root_guide(
        f"# Root\n\n## Rules\n\n- Keep behaviour. enforced by: `test:{path}::a > b`\n"
    )
    workspace.stage()
    context = workspace.context()
    tracked = TrackedFiles.read(context.repo)
    assert rule_errors(context, tracked, guides(tracked, context.project)) == []
