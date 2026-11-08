"""The evidence step and the Removed tests declarations it carries."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.check.evidence import EvidenceStep, over_cap_reason, removed_test_declarations

GOOD = """Fixes the parser.

## Evidence

- `uv run pytest tests/test_dates.py`: 12 passed
- **Before:** test_parse_dates failed. **After:** it passes.

Removed tests:
- tests/test_flags.py::test_legacy_flag: the flag was deleted in this PR
- `tests/test_cli.py::TestCli::test_old`: covered by test_new

Not covered: behaviour on Windows.

## Notes

Not covered: this line is outside the section.
"""

FENCED = (
    "## Evidence\n\n~~~console\n$ ./devctl check\npassed         format\n~~~\n\nNot covered: x\n"
)
NO_COMMAND = "Evidence: list a command you ran with its result, as '- `<command>`: <result>'"


def test_evidence_outside_a_pull_request_is_not_applicable(workspace: Workspace) -> None:
    assert EvidenceStep().run(workspace.context(pr_body=None)).status == "not_applicable"


@pytest.mark.parametrize("body", [GOOD, FENCED])
def test_complete_evidence_passes(workspace: Workspace, body: str) -> None:
    assert EvidenceStep().run(workspace.context(pr_body=body)).status == "passed"


@pytest.mark.parametrize(
    ("body", "detail"),
    [
        ("", "add an '## Evidence' section with a command, its result and a 'Not covered:' line"),
        ("## Evidence\n\nNot covered: x\n", NO_COMMAND),
        ("## Evidence\n\n- `make test`:\n\nNot covered: x\n", NO_COMMAND),
        ("## Evidence\n\n~~~\n$ make test\n~~~\n\nNot covered: x\n", NO_COMMAND),
        (
            "## Evidence\n\nRemoved tests:\n- `tests/test_a.py::test_a`: gone\n\nNot covered: x\n",
            NO_COMMAND,
        ),
        (
            "## Evidence\n\n- `make test`: ok\n\nNot covered:\n",
            "Evidence: add a line starting 'Not covered:' that names what the commands do not show",
        ),
        (
            "## Evidence\n\n- `make test`: ok\n\nRemoved tests:\n- test_a\n\nNot covered: x\n",
            "Removed tests: cannot read '- test_a'; write '- `<path>::<test>`: <reason>' "
            "(use backticks for spaces)",
        ),
    ],
)
def test_incomplete_evidence_fails(workspace: Workspace, body: str, detail: str) -> None:
    result = EvidenceStep().run(workspace.context(pr_body=body))

    assert result.status == "failed"
    assert result.details == (detail,)


def test_declarations_are_read_from_the_evidence_section() -> None:
    assert removed_test_declarations(GOOD) == (
        {
            "tests/test_flags.py::test_legacy_flag": "the flag was deleted in this PR",
            "tests/test_cli.py::TestCli::test_old": "covered by test_new",
        },
        [],
    )


def test_only_the_evidence_section_counts(workspace: Workspace) -> None:
    body = (
        "## Evidence\n\n- `make test`: ok\n\n## Notes\n\nNot covered: x\n\n"
        "Removed tests:\n- test_a\n"
    )

    result = EvidenceStep().run(workspace.context(pr_body=body))

    assert result.details == (
        "Evidence: add a line starting 'Not covered:' that names what the commands do not show",
    )
    assert removed_test_declarations(body) == ({}, [])


def test_a_subheading_stays_inside_the_evidence_section(workspace: Workspace) -> None:
    body = "## Evidence\n\n### Commands\n\n- `make test`: ok\n\n### Gaps\n\nNot covered: x\n"

    assert EvidenceStep().run(workspace.context(pr_body=body)).status == "passed"


def test_fenced_text_is_not_read_as_prose(workspace: Workspace) -> None:
    body = (
        "## Evidence\n\n- `make test`: ok\n\n```\nNot covered: x\nRemoved tests:\n- test_a\n```\n"
    )

    result = EvidenceStep().run(workspace.context(pr_body=body))

    assert result.details == (
        "Evidence: add a line starting 'Not covered:' that names what the commands do not show",
    )


def test_every_unreadable_declaration_is_reported(workspace: Workspace) -> None:
    body = (
        "## Evidence\n\n- `make test`: ok\n\nRemoved tests:\n"
        "- `tests/test_a.py::test_a`: gone\n- tests/test_b.py::test_b\n"
        "+ tests/test_c.py::test_c: x\n\nNot covered: x\n"
    )

    result = EvidenceStep().run(workspace.context(pr_body=body))

    assert result.details == (
        "Removed tests: cannot read '- tests/test_b.py::test_b'; "
        "write '- `<path>::<test>`: <reason>' "
        "(use backticks for spaces)",
        "Removed tests: cannot read '+ tests/test_c.py::test_c: x'; "
        "write '- `<path>::<test>`: <reason>' "
        "(use backticks for spaces)",
    )
    assert removed_test_declarations(body)[0] == {"tests/test_a.py::test_a": "gone"}


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        (
            "## Evidence\n\n- `make`: ok\n\nOver the diff cap: a generated parser\n",
            "a generated parser",
        ),
        ("## Evidence\n\n- `make`: ok\n\n## Notes\n\nOver the diff cap: a parser\n", None),
        ("## Evidence\n\n~~~\nOver the diff cap: a parser\n~~~\n", None),
        ("## Evidence\n\n- `make`: ok\n\nOver the diff cap:   \n", None),
        ("Over the diff cap: a parser\n", None),
    ],
    ids=["in-evidence", "outside-evidence", "fenced", "no-reason", "no-evidence"],
)
def test_over_cap_reason_reads_the_evidence_section(body: str, reason: str | None) -> None:
    assert over_cap_reason(body) == reason


@pytest.mark.parametrize(
    "identity", ["frontend/src/a.test.ts::a > b", "front end/a.test.ts::a > b"]
)
def test_backticked_test_identities_can_hold_spaces(workspace: Workspace, identity: str) -> None:
    body = (
        f"## Evidence\n\n- `pytest`: passed\n\nRemoved tests:\n- `{identity}`: gone\n"
        "\nNot covered: live tools\n"
    )
    assert removed_test_declarations(body) == ({identity: "gone"}, [])
    assert EvidenceStep().run(workspace.context(pr_body=body)).status == "passed"
    for item in (f"- `{identity}`:", f"- {identity}: gone", f"- `{identity}: gone"):
        assert removed_test_declarations(f"## Evidence\nRemoved tests:\n{item}\n")[1] == [item]


def rs_pr_body() -> str:
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2]
        / "rapid_ship/templates/common/.agents/skills/rs-pr/SKILL.md"
    )
    return path.read_text().split("```markdown\n", 1)[1].split("\n```", 1)[0]


def test_the_rs_pr_template_passes_the_evidence_step(workspace: Workspace) -> None:
    body = rs_pr_body()
    assert EvidenceStep().run(workspace.context(pr_body=body)).status == "passed"
    assert over_cap_reason(body) is None
    assert removed_test_declarations(body) == ({}, [])


def test_the_rs_pr_template_without_not_covered_fails(workspace: Workspace) -> None:
    body = "\n".join(
        line for line in rs_pr_body().splitlines() if not line.startswith("Not covered:")
    )
    result = EvidenceStep().run(workspace.context(pr_body=body))
    assert result.status == "failed"
    assert (
        "Evidence: add a line starting 'Not covered:' that names what the commands do not show"
        in result.details
    )
