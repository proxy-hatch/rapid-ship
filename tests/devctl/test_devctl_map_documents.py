"""Offline: feature files, Pattern files and Rules bullets in fixture repositories."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.check.map import (
    MapStep,
    feature_errors,
    guides,
    pattern_errors,
    pattern_lesson_errors,
    registered_verbs,
    rule_errors,
)
from devctl.check.markdown import rules_items

FEATURE = """---
purpose: Sign users in
entry_points: [src/app/auth.py]
data: [src/app/models.py]
observe: The auth.login log line with the user ID.
reproduce: ./devctl check --tier fast
---
# Sign-in
"""


def features(workspace: Workspace) -> list[str]:
    workspace.stage()
    context = workspace.context()
    return feature_errors(context, context.repo.tracked_files())


def test_valid_feature_and_readme_pass(workspace: Workspace) -> None:
    workspace.write("src/app/auth.py", "")
    workspace.write("src/app/models.py", "")
    workspace.write("docs/features/README.md", "# Feature files\n")
    workspace.write("docs/features/sign-in.md", FEATURE)

    assert features(workspace) == []


def test_feature_without_front_matter_fails(workspace: Workspace) -> None:
    workspace.write("docs/features/sign-in.md", "# Sign-in\n")

    assert features(workspace) == [
        "docs/features/sign-in.md: no front matter; start the file with --- and the keys "
        "purpose, entry_points, data, observe and reproduce"
    ]


def test_feature_names_missing_path_missing_key_and_unknown_verb(workspace: Workspace) -> None:
    workspace.write(
        "docs/features/sign-in.md",
        "---\npurpose: Sign in\nentry_points: [src/app/gone.py]\ndata: []\n"
        "reproduce: ./devctl seed-demo\n---\n",
    )

    assert features(workspace) == [
        "docs/features/sign-in.md: entry_points names src/app/gone.py, which does not exist",
        "docs/features/sign-in.md: observe is missing or empty",
        "docs/features/sign-in.md: reproduce runs ./devctl seed-demo; "
        "seed-demo is not a devctl verb",
    ]


def test_feature_needs_at_least_one_entry_point(workspace: Workspace) -> None:
    workspace.write("src/app/models.py", "")
    workspace.write("docs/features/sign-in.md", FEATURE.replace("[src/app/auth.py]", "[]"))

    assert features(workspace) == ["docs/features/sign-in.md: entry_points is missing or empty"]


def test_unclosed_or_invalid_front_matter_fails(workspace: Workspace) -> None:
    workspace.write("docs/features/a.md", "---\npurpose: x\n")
    workspace.write("docs/features/b.md", "---\n- a list\n---\n")

    assert features(workspace) == [
        "docs/features/a.md: front matter is not closed with ---",
        "docs/features/b.md: front matter must be a mapping",
    ]


def test_registered_verbs_include_check() -> None:
    assert "check" in registered_verbs()


def test_nested_feature_files_are_checked_too(workspace: Workspace) -> None:
    workspace.write("docs/features/billing/invoices.md", "# Invoices\n")

    assert features(workspace) == [
        "docs/features/billing/invoices.md: no front matter; start the file with --- and the "
        "keys purpose, entry_points, data, observe and reproduce"
    ]


def test_invalid_yaml_is_reported_on_one_line(workspace: Workspace) -> None:
    workspace.write("docs/features/a.md", "---\npurpose: [unclosed\nobserve: x\n---\n")

    [error] = features(workspace)

    assert error.startswith("docs/features/a.md: ")
    assert "\n" not in error


@pytest.mark.parametrize(
    ("reproduce", "problem"),
    [
        ("./devctl", "reproduce names no verb after ./devctl"),
        ("devctl check", "reproduce must be a ./devctl command"),
        ("./devctl 'check", "reproduce must be a ./devctl command"),
        ("''", "reproduce is missing or empty"),
        ("7", "reproduce is missing or empty"),
    ],
)
def test_feature_reproduce_must_be_a_devctl_verb(
    workspace: Workspace, reproduce: str, problem: str
) -> None:
    workspace.write("src/app/auth.py", "")
    workspace.write("src/app/models.py", "")
    text = FEATURE.replace("reproduce: ./devctl check --tier fast", f"reproduce: {reproduce}")
    workspace.write("docs/features/sign-in.md", text)

    assert features(workspace) == [f"docs/features/sign-in.md: {problem}"]


def test_feature_paths_cannot_leave_the_repository(workspace: Workspace) -> None:
    workspace.write("src/app/models.py", "")
    text = FEATURE.replace("[src/app/auth.py]", "[../repo/src/app/models.py]")
    workspace.write("docs/features/sign-in.md", text)

    assert features(workspace) == [
        "docs/features/sign-in.md: entry_points names ../repo/src/app/models.py, "
        "which does not exist"
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

    errors = pattern_errors(context, context.repo.tracked_files())

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
    return pattern_lesson_errors(context, context.repo.tracked_files())


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
    assert pattern_errors(context, context.repo.tracked_files()) == [
        f"docs/patterns/settings.md: {message}"
    ]


def test_the_pattern_readme_is_not_a_pattern(workspace: Workspace) -> None:
    workspace.write("docs/patterns/README.md", "# Patterns\n")
    workspace.stage()

    context = workspace.context()
    assert pattern_lesson_errors(context, context.repo.tracked_files()) == []


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
    found = guides(context.repo.root, context.repo.tracked_files(), context.project)

    assert rule_errors(context, found) == [
        "AGENTS.md:19: end the rule with 'enforced by: <reference>' or 'advisory'",
        "AGENTS.md:20: check:nope: no devctl check step is named nope",
    ]


def test_the_map_step_reports_features_patterns_rules_and_skills(workspace: Workspace) -> None:
    workspace.root_guide("[Docs](docs/)\n\n## Rules\n\n- Forgot the marker.\n")
    workspace.write("docs/AGENTS.md", "# Docs\n")
    workspace.write("docs/features/sign-in.md", "# Sign-in\n")
    workspace.write("docs/patterns/settings.md", "# Settings\n")
    workspace.write(".agents/skills/notes/SKILL.md", "# Notes\n")
    workspace.link(".claude/skills/notes", "../../.agents/skills/notes")
    workspace.stage()

    result = MapStep().run(workspace.context(source_roots=()))

    assert result.status == "failed"
    assert [detail.split(": ")[0] for detail in result.details] == [
        "docs/features/sign-in.md",
        "docs/patterns/settings.md",
        "AGENTS.md:5",
        ".agents/skills/notes/SKILL.md",
    ]


def test_untracked_feature_and_pattern_files_are_not_checked(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.stage()
    workspace.write("docs/features/sign-in.md", "# Sign-in\n")
    workspace.write("docs/patterns/settings.md", "# Settings\n")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == ("passed", ())
