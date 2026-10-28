"""Offline: the edges of doctor's GitHub items. The owner's reads are recorded (RecordedOwner), the
Apps and GitHub's answers to them are simulated (FakeGitHub), and the Keychain holds test keys. No
live GitHub, gh login or Keychain is read."""

import base64
import dataclasses
import json
from pathlib import Path

import pytest

from devctl.doctor import (
    PROTECTED_PATHS,
    Item,
    OwnerReadError,
    codeowners_problems,
    github_items,
    ruleset_problems,
)
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_INSTALLATION,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    FakeGitHub,
    FakeKeychain,
    MakeContext,
    RecordedOwner,
)

FIXTURES = Path(__file__).parent / "fixtures" / "github"
REPOSITORY = "repos/o/r"
RULESET_LIST = "repos/o/r/rulesets?targets=branch"
FORK_APPROVAL = "repos/o/r/actions/permissions/fork-pr-contributor-approval"
CODEOWNERS = "repos/o/r/contents/.github/CODEOWNERS?ref=main"
NO_RULESET = "no ruleset targets the default branch"
REPOSITORY_ITEMS = {"ruleset", "CODEOWNERS", "delete branch on merge", "fork PR workflow approval"}
APP_ITEMS = {
    "Worker App installation",
    "Reviewer App installation",
    "Worker App key",
    "Reviewer App key",
}


def fixture(name: str) -> dict[str, object]:
    loaded = json.loads((FIXTURES / name).read_text())
    assert isinstance(loaded, dict)
    return loaded


def by_name(items: list[Item]) -> dict[str, Item]:
    return {item.name: item for item in items}


def contents(text: str) -> dict[str, object]:
    """GitHub's contents response for a file: base64 text with newlines in it."""
    encoded = base64.encodebytes(text.encode()).decode()
    return {"type": "file", "encoding": "base64", "content": encoded}


def named(ctx: MakeContext, item: str) -> Item:
    return by_name(github_items(ctx()))[item]


def test_a_private_repository_needs_no_fork_approval(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(REPOSITORY, {**fixture("repository.json"), "visibility": "private"})
    item = named(ctx_github, "fork PR workflow approval")
    assert (item.status, item.detail) == ("ok", "not applicable: private repository")
    assert FORK_APPROVAL not in recorded.paths


@pytest.mark.parametrize(
    ("setting", "found"),
    [
        ({"approval_policy": "first_time_contributors"}, "approval_policy is first_time"),
        ({"approval_policy": None}, "approval_policy is unreadable"),
        ({}, "approval_policy is unreadable"),
    ],
)
def test_a_weaker_fork_policy_is_missing(
    ctx_github: MakeContext, recorded: RecordedOwner, setting: dict[str, object], found: str
) -> None:
    recorded.serve(FORK_APPROVAL, setting)
    item = named(ctx_github, "fork PR workflow approval")
    assert item.status == "missing"
    assert found in item.detail


def test_an_unreadable_fork_setting_is_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.fail(FORK_APPROVAL, OwnerReadError(403, "Resource not accessible by integration"))
    item = named(ctx_github, "fork PR workflow approval")
    assert item.status == "unknown"
    assert "Resource not accessible by integration (HTTP 403)" in item.detail


@pytest.mark.parametrize(
    ("setting", "status"), [(False, "missing"), (None, "unknown")], ids=["off", "not reported"]
)
def test_head_branches_must_be_deleted_after_merge(
    ctx_github: MakeContext, recorded: RecordedOwner, setting: bool | None, status: str
) -> None:
    recorded.serve(REPOSITORY, {**fixture("repository.json"), "delete_branch_on_merge": setting})
    assert named(ctx_github, "delete branch on merge").status == status


@pytest.mark.parametrize(
    ("served", "status", "detail"),
    [
        (OwnerReadError(404, "Not Found"), "missing", ".github/CODEOWNERS is not on main"),
        (OwnerReadError(403, "Forbidden"), "unknown", "Forbidden (HTTP 403)"),
        ({"encoding": "none", "content": ""}, "unknown", "not base64 text"),
        ({"encoding": "base64", "content": "!!!"}, "unknown", "not UTF-8 text"),
        ({"encoding": "base64", "content": "/w=="}, "unknown", "not UTF-8 text"),
        (contents("* @someone-else\n"), "missing", "is not * @o"),
        (contents("* @O  # the owner\n"), "ok", "matches Walk"),
    ],
)
def test_codeowners_reads_what_the_base_branch_holds(
    ctx_github: MakeContext,
    recorded: RecordedOwner,
    served: OwnerReadError | dict[str, object],
    status: str,
    detail: str,
) -> None:
    if isinstance(served, OwnerReadError):
        recorded.fail(CODEOWNERS, served)
    else:
        recorded.serve(CODEOWNERS, served)
    item = named(ctx_github, "CODEOWNERS")
    assert item.status == status
    assert detail in item.detail


@pytest.mark.parametrize("code_owner", ["@octocat", "@o/platform-team"], ids=["login", "team"])
def test_codeowners_is_checked_against_the_code_owner_not_the_repository_owner(
    ctx_github: MakeContext, recorded: RecordedOwner, code_owner: str
) -> None:
    context = ctx_github()
    context = dataclasses.replace(
        context, project=dataclasses.replace(context.project, code_owner=code_owner)
    )
    recorded.serve(CODEOWNERS, contents(f"* {code_owner}\n"))
    assert by_name(github_items(context))["CODEOWNERS"].status == "ok"
    # o owns o/r, as an organisation would, but only the recorded code owner counts.
    recorded.serve(CODEOWNERS, contents("* @o\n"))
    item = by_name(github_items(context))["CODEOWNERS"]
    assert (item.status, item.detail) == (
        "missing",
        f"the one active CODEOWNERS line is not * {code_owner}",
    )


def test_codeowners_is_missing_while_no_code_owner_is_recorded(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    context = ctx_github()
    context = dataclasses.replace(
        context, project=dataclasses.replace(context.project, code_owner=None)
    )
    items = by_name(github_items(context))
    assert items["CODEOWNERS"].status == "missing"
    assert "set [github] code_owner in .rapid-ship/project.toml" in items["CODEOWNERS"].detail
    assert CODEOWNERS not in recorded.paths
    assert items["ruleset"].status == "ok"


def test_codeowners_is_read_at_the_default_branch_whatever_its_name(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(REPOSITORY, {**fixture("repository.json"), "default_branch": "release/1"})
    release = "repos/o/r/contents/.github/CODEOWNERS?ref=release/1"
    recorded.serve(release, fixture("codeowners.json"))
    release_errors = "repos/o/r/codeowners/errors?ref=release/1"
    recorded.serve(release_errors, {"errors": []})
    assert named(ctx_github, "CODEOWNERS").status == "ok"
    assert release in recorded.paths
    assert release_errors in recorded.paths
    assert CODEOWNERS not in recorded.paths
    assert "repos/o/r/codeowners/errors?ref=main" not in recorded.paths


@pytest.mark.parametrize("served", [OwnerReadError(None, "gh could not start"), [], {}])
def test_an_unreadable_repository_leaves_its_four_items_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner, served: OwnerReadError | list[object]
) -> None:
    if isinstance(served, OwnerReadError):
        recorded.fail(REPOSITORY, served)
    else:
        recorded.serve(REPOSITORY, served)
    items = by_name(github_items(ctx_github()))
    assert {name for name, item in items.items() if item.status == "unknown"} == REPOSITORY_ITEMS
    assert {items[name].status for name in APP_ITEMS} == {"ok"}
    assert recorded.paths == [REPOSITORY]


def test_a_repository_without_a_default_branch_makes_only_its_readers_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(REPOSITORY, {**fixture("repository.json"), "default_branch": None})
    items = by_name(github_items(ctx_github()))
    assert items["ruleset"].status == items["CODEOWNERS"].status == "unknown"
    assert "no default_branch" in items["ruleset"].detail
    assert items["delete branch on merge"].status == "ok"


def test_an_inherited_ruleset_is_not_the_repositorys(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    inherited = {"id": 4, "name": "org", "target": "branch", "source_type": "Organization"}
    recorded.serve(RULESET_LIST, [inherited])
    item = named(ctx_github, "ruleset")
    assert (item.status, item.detail) == ("missing", NO_RULESET)
    assert "repos/o/r/rulesets/4" not in recorded.paths


def test_a_repository_with_no_ruleset_is_missing(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(RULESET_LIST, [])
    item = named(ctx_github, "ruleset")
    assert (item.status, item.detail) == ("missing", NO_RULESET)


def test_a_listed_ruleset_without_a_numeric_id_is_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(RULESET_LIST, [{"id": "9", "source_type": "Repository"}])
    assert named(ctx_github, "ruleset").status == "unknown"


def test_a_ruleset_that_cannot_be_read_is_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.fail("repos/o/r/rulesets/9", OwnerReadError(500, "Server Error"))
    item = named(ctx_github, "ruleset")
    assert item.status == "unknown"
    assert "Server Error (HTTP 500)" in item.detail


def test_one_good_ruleset_is_enough() -> None:
    good = fixture("ruleset.json")
    bad = {**good, "id": 10, "enforcement": "disabled"}
    assert ruleset_problems([bad, good], "main", every_pr=True, agent_identity=True) == []
    assert ruleset_problems([good, bad], "main", every_pr=True, agent_identity=True) == []


def test_the_problems_reported_are_those_of_the_closest_ruleset() -> None:
    close = {**fixture("ruleset.json"), "enforcement": "disabled"}
    far = {**close, "rules": [], "bypass_actors": []}
    assert ruleset_problems([far, close], "main", every_pr=True, agent_identity=True) == [
        "the ruleset is not active"
    ]
    assert ruleset_problems([], "main", every_pr=True, agent_identity=True) == [NO_RULESET]


def test_the_ruleset_must_name_the_default_branch_and_exclude_nothing_of_it() -> None:
    ruleset = fixture("ruleset.json")
    ruleset["conditions"] = {"ref_name": {"include": ["refs/heads/trunk"], "exclude": []}}
    assert ruleset_problems([ruleset], "trunk", every_pr=True, agent_identity=True) == []
    assert ruleset_problems([ruleset], "main", every_pr=True, agent_identity=True)
    ruleset["conditions"] = {"ref_name": {"include": ["~ALL"], "exclude": ["~DEFAULT_BRANCH"]}}
    assert ruleset_problems([ruleset], "main", every_pr=True, agent_identity=True)


def test_codeowners_owners_are_compared_without_regard_to_case() -> None:
    assert codeowners_problems("# note\n\n*  @O   # the owner\n", True, "@o", "python") == []
    assert codeowners_problems("* @o @team\n", True, "@o", "python")
    assert codeowners_problems("* @o\n* @o\n", True, "@o", "python")
    assert codeowners_problems("# only a comment\n", True, "@o", "python")
    team = "@my-org/platform-team"
    assert codeowners_problems("* @My-Org/Platform-Team\n", True, team, "python") == []
    assert codeowners_problems(f"* {team}\n", True, "@My-Org/Platform-Team", "python") == []


def test_a_flight_path_must_be_owned_by_the_owner_alone() -> None:
    lines = "".join(f"/{path} @o\n" for path in PROTECTED_PATHS)
    assert codeowners_problems(lines, False, "@o", "agnostic") == []
    # The last line for a path is the one GitHub applies.
    assert codeowners_problems(lines + "/devctl @other\n", False, "@o", "agnostic")
    assert codeowners_problems(lines + "/devctl @o\n", False, "@o", "agnostic") == []
    for owners in ("@other", "@o @other", ""):
        changed = lines.replace("/devctl @o\n", f"/devctl {owners}\n")
        assert "for: devctl" in " ".join(codeowners_problems(changed, False, "@o", "agnostic"))


def test_a_run_without_github_access_leaves_the_apps_unknown(ctx_github: MakeContext) -> None:
    context = dataclasses.replace(ctx_github(), access=None)
    items = by_name(github_items(context))
    assert {name for name, item in items.items() if item.status == "unknown"} == APP_ITEMS


def test_an_extra_permission_makes_the_installation_missing(
    ctx_github: MakeContext, github: FakeGitHub
) -> None:
    permissions = {**REVIEWER_PERMISSIONS, "workflows": "write"}
    github.install(REVIEWER_ID, "o/r", permissions, REVIEWER_INSTALLATION)
    items = by_name(github_items(ctx_github()))
    assert items["Reviewer App installation"].status == "missing"
    assert items["Reviewer App installation"].detail == (
        "permissions differ from those the Reviewer App needs: workflows: write must not be granted"
    )
    assert items["Reviewer App key"].status == "ok"
    assert items["Worker App installation"].status == "ok"


def test_a_github_error_makes_the_app_items_unknown(
    ctx_github: MakeContext, github: FakeGitHub
) -> None:
    github.route(
        "GET", r"/repos/o/r/installation", lambda call, match: (500, {"message": "Server Error"})
    )
    items = by_name(github_items(ctx_github()))
    for label in ("Worker", "Reviewer"):
        assert items[f"{label} App installation"].status == "unknown"
        assert items[f"{label} App key"].status == "unknown"
    assert items["ruleset"].status == "ok"


def test_a_missing_key_names_the_command_that_imports_it(
    ctx_github: MakeContext, keychain_without_reviewer: FakeKeychain
) -> None:
    items = by_name(github_items(ctx_github(keychain=keychain_without_reviewer)))
    tagged = "uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.2.0 rapid-ship app"
    expected = (
        f"Keychain item rapid-ship/reviewer-app/{REVIEWER_ID} not found; in the App's settings on "
        "GitHub, open Credentials, then Key pairs, and click New key to generate a private key; "
        f"then run {tagged} --import-key reviewer with the key on stdin"
    )
    for name in ("Reviewer App installation", "Reviewer App key"):
        assert items[name].detail == expected


def test_a_key_that_is_not_a_pem_is_unknown_and_quotes_none_of_it(
    ctx_github: MakeContext, app_keys: dict[str, tuple[bytes, bytes]]
) -> None:
    keychain = FakeKeychain(
        {
            f"rapid-ship/worker-app/{WORKER_ID}": app_keys["worker"][0],
            f"rapid-ship/reviewer-app/{REVIEWER_ID}": b"-----BEGIN PRIVATE KEY-----\nnot a key\n",
        }
    )
    items = by_name(github_items(ctx_github(keychain=keychain)))
    assert items["Reviewer App key"].status == "unknown"
    assert "cannot mint a token" in items["Reviewer App key"].detail
    assert "BEGIN" not in items["Reviewer App key"].detail
    assert items["Worker App key"].status == "ok"


def test_no_item_holds_a_token_or_a_key(ctx_github: MakeContext, github: FakeGitHub) -> None:
    text = "\n".join(f"{i.area} {i.name} {i.status} {i.detail}" for i in github_items(ctx_github()))
    assert len(github.issued_tokens) == 2  # one per App key; the installation reads mint none
    assert not any(token in text for token in github.issued_tokens)
    assert "BEGIN" not in text
