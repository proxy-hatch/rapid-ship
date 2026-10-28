"""Offline: doctor's CODEOWNERS item with the CODEOWNERS errors that GitHub reports. RecordedOwner
serves the owner's reads: the unknown team's error has the fields GitHub returned, and the other
replies are simulated. No live GitHub or gh login is read."""

import base64
import dataclasses

import pytest

from devctl.doctor import (
    PROTECTED_PATHS,
    CodeownersError,
    DoctorContext,
    Item,
    OwnerReadError,
    codeowners_error_problems,
    github_items,
)
from github_fakes import MakeContext, RecordedOwner

CODEOWNERS = "repos/o/r/contents/.github/CODEOWNERS?ref=main"
ERRORS = "repos/o/r/codeowners/errors?ref=main"
TEAM = "@o/maintainers"
WALK = f"# Walk\n* {TEAM}\n"
UNKNOWN_TEAM_SUGGESTION = (
    f"make sure the team {TEAM} exists, is publicly visible, and has write access to the repository"
)
# The fields doctor reads, as GitHub answered on 2026-10-26 both before the team existed and while
# the visible team had no access to the repository; the team and the line are this file's.
UNKNOWN_TEAM = {"line": 2, "kind": "Unknown owner", "suggestion": UNKNOWN_TEAM_SUGGESTION}
FLIGHT = "".join(f"/{path} {TEAM}\n" for path in PROTECTED_PATHS)
ON_MAIN = "of .github/CODEOWNERS on main"


def contents(text: str) -> dict[str, object]:
    """GitHub's contents response for a file: base64 text with newlines in it."""
    encoded = base64.encodebytes(text.encode()).decode()
    return {"type": "file", "encoding": "base64", "content": encoded}


def owned_by(ctx: MakeContext, code_owner: str, *, every_pr: bool = True) -> DoctorContext:
    """ctx's context with code_owner recorded, in Walk or, with every_pr False, in Flight on the
    agnostic stack."""
    context = ctx()
    escalation = dataclasses.replace(context.project.escalation, every_pr=every_pr)
    stack = context.project.stack if every_pr else "agnostic"
    project = dataclasses.replace(
        context.project, code_owner=code_owner, escalation=escalation, stack=stack
    )
    return dataclasses.replace(context, project=project)


def codeowners_item(context: DoctorContext) -> Item:
    [item] = [i for i in github_items(context) if i.name == "CODEOWNERS"]
    return item


def test_a_team_that_does_not_exist_or_has_no_write_access_is_missing(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    """GitHub returned the same error in both states, so one reply covers both."""
    recorded.serve(CODEOWNERS, contents(WALK))
    recorded.serve(ERRORS, {"errors": [UNKNOWN_TEAM]})
    item = codeowners_item(owned_by(ctx_github, TEAM))
    assert (item.status, item.detail) == (
        "missing",
        f"GitHub reports Unknown owner on line 2 {ON_MAIN}: {UNKNOWN_TEAM_SUGGESTION}",
    )
    assert ERRORS in recorded.paths


def test_the_detail_names_the_file_and_the_branch_that_github_read(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    repository = recorded("repos/o/r")
    assert isinstance(repository, dict)
    recorded.serve("repos/o/r", {**repository, "default_branch": "release/1"})
    recorded.serve("repos/o/r/contents/.github/CODEOWNERS?ref=release/1", contents(WALK))
    recorded.serve("repos/o/r/codeowners/errors?ref=release/1", {"errors": [UNKNOWN_TEAM]})
    item = codeowners_item(owned_by(ctx_github, TEAM))
    assert item.detail == (
        "GitHub reports Unknown owner on line 2 of .github/CODEOWNERS on release/1: "
        f"{UNKNOWN_TEAM_SUGGESTION}"
    )


def test_a_team_with_write_access_is_ok(ctx_github: MakeContext, recorded: RecordedOwner) -> None:
    recorded.serve(CODEOWNERS, contents(WALK))
    recorded.serve(ERRORS, {"errors": []})
    item = codeowners_item(owned_by(ctx_github, TEAM))
    assert (item.status, item.detail) == (
        "ok",
        ".github/CODEOWNERS on main matches Walk, and GitHub reports no error on the lines doctor "
        "checks",
    )


def test_a_login_that_github_does_not_know_is_missing(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(CODEOWNERS, contents("* @octocat\n"))
    # Simulated: GitHub's suggestion for a login was not recorded.
    suggestion = "make sure @octocat exists and has write access to the repository"
    unknown = {"line": 1, "column": 3, "kind": "Unknown owner", "suggestion": suggestion}
    recorded.serve(ERRORS, {"errors": [unknown]})
    item = codeowners_item(owned_by(ctx_github, "@octocat"))
    assert (item.status, item.detail) == (
        "missing",
        f"GitHub reports Unknown owner on line 1 {ON_MAIN}: {suggestion}",
    )


def test_an_error_without_a_suggestion_names_its_kind_and_line(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(CODEOWNERS, contents(WALK))
    recorded.serve(ERRORS, {"errors": [{"line": 2, "kind": "Invalid owner", "suggestion": None}]})
    item = codeowners_item(owned_by(ctx_github, TEAM))
    assert (item.status, item.detail) == (
        "missing",
        f"GitHub reports Invalid owner on line 2 {ON_MAIN}",
    )


def test_in_flight_only_errors_on_protected_lines_count(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(CODEOWNERS, contents(FLIGHT + "/src/ @o/unknown\n"))
    other = {"line": len(PROTECTED_PATHS) + 1, "kind": "Unknown owner", "suggestion": "elsewhere"}
    recorded.serve(ERRORS, {"errors": [other]})
    context = owned_by(ctx_github, TEAM, every_pr=False)
    assert codeowners_item(context).status == "ok"
    first = {**UNKNOWN_TEAM, "line": 1}
    last = {**UNKNOWN_TEAM, "line": len(PROTECTED_PATHS)}
    recorded.serve(ERRORS, {"errors": [first, other, last]})
    item = codeowners_item(context)
    assert (item.status, item.detail) == (
        "missing",
        f"GitHub reports Unknown owner on lines 1 and 13 {ON_MAIN}: {UNKNOWN_TEAM_SUGGESTION}",
    )


def test_an_error_on_every_protected_line_is_reported_once(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    """An unknown team in Flight is an error on every Protected line, each with one suggestion."""
    recorded.serve(CODEOWNERS, contents(FLIGHT))
    lines = range(1, len(PROTECTED_PATHS) + 1)
    recorded.serve(ERRORS, {"errors": [{**UNKNOWN_TEAM, "line": line} for line in lines]})
    item = codeowners_item(owned_by(ctx_github, TEAM, every_pr=False))
    assert (item.status, item.detail) == (
        "missing",
        "GitHub reports Unknown owner on lines 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 and 13 "
        f"{ON_MAIN}: {UNKNOWN_TEAM_SUGGESTION}",
    )


def test_github_is_asked_only_once_the_file_matches_the_mode(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(CODEOWNERS, contents("* @someone-else\n"))
    recorded.fail(ERRORS, OwnerReadError(500, "Server Error"))
    item = codeowners_item(owned_by(ctx_github, TEAM))
    assert (item.status, item.detail) == (
        "missing",
        f"the one active CODEOWNERS line is not * {TEAM}",
    )
    assert ERRORS not in recorded.paths


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (OwnerReadError(500, "Server Error"), "Server Error (HTTP 500)"),
        (OwnerReadError(404, "Not Found"), "Not Found (HTTP 404)"),
        (OwnerReadError(None, "gh api timed out"), "gh api timed out"),
    ],
)
def test_a_failed_read_of_the_errors_leaves_the_item_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner, error: OwnerReadError, detail: str
) -> None:
    recorded.serve(CODEOWNERS, contents(WALK))
    recorded.fail(ERRORS, error)
    items = {i.name: i for i in github_items(owned_by(ctx_github, TEAM))}
    assert (items["CODEOWNERS"].status, items["CODEOWNERS"].detail) == (
        "unknown",
        f"cannot read GitHub's CODEOWNERS errors: {detail}",
    )
    assert items["ruleset"].status == "ok"


NO_LIST = "the CODEOWNERS error list is not a JSON list"
NO_LINE = "a CODEOWNERS error has no numeric line"
NO_KIND = "a CODEOWNERS error has no kind"


@pytest.mark.parametrize(
    ("reply", "detail"),
    [
        ([], "the CODEOWNERS errors reply is not a JSON object"),
        ({}, NO_LIST),
        ({"errors": {}}, NO_LIST),
        ({"errors": ["Unknown owner"]}, "a CODEOWNERS error is not a JSON object"),
        ({"errors": [{"kind": "Unknown owner"}]}, NO_LINE),
        ({"errors": [{"line": "2", "kind": "Unknown owner"}]}, NO_LINE),
        ({"errors": [{"line": True, "kind": "Unknown owner"}]}, NO_LINE),
        ({"errors": [{"line": 2}]}, NO_KIND),
        ({"errors": [{"line": 2, "kind": " "}]}, NO_KIND),
    ],
)
def test_a_reply_not_in_githubs_shape_leaves_the_item_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner, reply: object, detail: str
) -> None:
    recorded.serve(CODEOWNERS, contents(WALK))
    recorded.serve(ERRORS, reply)
    item = codeowners_item(owned_by(ctx_github, TEAM))
    assert (item.status, item.detail) == ("unknown", f"GitHub request failed: {detail}")


def test_only_errors_on_the_lines_doctor_checks_are_problems() -> None:
    walk = [CodeownersError(1, "Unknown owner", None), CodeownersError(2, "Unknown owner", "x")]
    assert codeowners_error_problems(walk, WALK, True, "agnostic", "main") == [
        f"GitHub reports Unknown owner on line 2 {ON_MAIN}: x"
    ]
    # In Flight the last line for a path is the one GitHub applies, so only that line counts.
    overridden = f"/devctl @o/old\n{FLIGHT}"
    devctl_line = 2 + PROTECTED_PATHS.index("devctl")
    errors = [
        CodeownersError(1, "Unknown owner", None),
        CodeownersError(devctl_line, "Unknown owner", None),
    ]
    assert codeowners_error_problems(errors, overridden, False, "agnostic", "main") == [
        f"GitHub reports Unknown owner on line {devctl_line} {ON_MAIN}"
    ]
    assert codeowners_error_problems([], WALK, True, "agnostic", "main") == []


def test_errors_with_one_kind_and_suggestion_are_one_problem_in_line_order() -> None:
    errors = [
        CodeownersError(5, "Unknown owner", "a"),
        CodeownersError(2, "Unknown owner", "a"),
        CodeownersError(3, "Unknown owner", "b"),
        CodeownersError(2, "Unknown owner", "a"),
        CodeownersError(3, "Unknown owner", "a"),
        CodeownersError(4, "Invalid owner", "a"),
        CodeownersError(6, "Invalid owner", None),
    ]
    assert codeowners_error_problems(errors, FLIGHT, False, "agnostic", "main") == [
        f"GitHub reports Unknown owner on lines 2, 3 and 5 {ON_MAIN}: a",
        f"GitHub reports Unknown owner on line 3 {ON_MAIN}: b",
        f"GitHub reports Invalid owner on line 4 {ON_MAIN}: a",
        f"GitHub reports Invalid owner on line 6 {ON_MAIN}",
    ]


@pytest.mark.parametrize("separator", ["\x0c", "\x1c", "\x85", "\u2028", "\u2029"])
def test_only_a_newline_ends_a_codeowners_line(separator: str) -> None:
    """Lines are numbered by newline, as git numbers them. Python's str.splitlines would also end
    one at the separator and number the * line 3."""
    text = f"# Walk{separator}# note\n* {TEAM}\n"
    unknown = [CodeownersError(2, "Unknown owner", "x")]
    assert codeowners_error_problems(unknown, text, True, "agnostic", "main") == [
        f"GitHub reports Unknown owner on line 2 {ON_MAIN}: x"
    ]


def test_crlf_line_ends_keep_the_line_numbers() -> None:
    unknown = [CodeownersError(2, "Unknown owner", "x")]
    crlf = WALK.replace("\n", "\r\n")
    assert codeowners_error_problems(unknown, crlf, True, "agnostic", "main") == [
        f"GitHub reports Unknown owner on line 2 {ON_MAIN}: x"
    ]
