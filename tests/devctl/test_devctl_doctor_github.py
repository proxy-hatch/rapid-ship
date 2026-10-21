"""Offline: doctor's GitHub items with recorded responses and simulated Apps. No live GitHub."""

import copy
import dataclasses
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from devctl.doctor import (
    PROTECTED_PATHS,
    PYTHON_PROTECTED_PATHS,
    OwnerReadError,
    codeowners_problems,
    gh_get,
    github_items,
    installation_problems,
    ruleset_problems,
    run_doctor,
)
from devctl.process import ProcessResult
from devctl.settings import App
from github_fakes import (
    REVIEWER_ID,
    FakeGitHub,
    FakeKeychain,
    FakeRun,
    MakeContext,
    RecordedOwner,
)
from rapid_ship.kit.templates import render_files

FIXTURES = Path(__file__).parent / "fixtures" / "github"
# Plan 4's Task 10 Step 11a live read-back, with require_last_push_approval set to false by hand:
# rs-setup's ruleset as GitHub reads it back.
RULESET: dict[str, Any] = json.loads((FIXTURES / "ruleset.json").read_text())
# (every_pr, agent_identity): Walk and Flight, each with Agent identity off and on.
MODES = ((True, False), (True, True), (False, False), (False, True))
APPROVAL_IN_FLIGHT = (
    "the pull_request rule requires an approval, so GitHub may refuse the Worker App's merge of an "
    "agent PR outside the Protected set on the Reviewer App's approval, as in plan 4's trial"
)
LAST_PUSH_IN_FLIGHT = (
    "the pull_request rule requires approval of the most recent push, so GitHub refuses the Worker "
    "App's merge of an agent PR outside the Protected set on the Reviewer App's approval, as in "
    "plan 4's trial"
)
PROTECTED = "".join(
    f"/{path} @o\n"
    for path in (
        ".github/",
        ".githooks/",
        "devctl",
        "tools/devctl/",
        ".agents/skills/",
        ".claude/",
        "**/AGENTS.md",
        "**/CLAUDE.md",
        ".rapid-ship/",
        ".gitleaks.toml",
        ".gitleaksignore",
        "zizmor.yml",
        "zizmor.yaml",
    )
)


def rule(ruleset: dict[str, Any], kind: str) -> dict[str, Any]:
    return next(r for r in ruleset["rules"] if r["type"] == kind)


def snapshot(root: Path) -> dict[Path, tuple[int, int]]:
    return {p: (p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*")}


def test_the_rs_setup_ruleset_passes() -> None:
    assert ruleset_problems([RULESET], "main", every_pr=True, agent_identity=True) == []


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (
            lambda r: rule(r, "pull_request")["parameters"].update(require_code_owner_review=False),
            "code-owner review",
        ),
        (
            lambda r: rule(r, "pull_request")["parameters"].update(
                dismiss_stale_reviews_on_push=False
            ),
            "stale approvals",
        ),
        (
            lambda r: rule(r, "pull_request")["parameters"].update(
                allowed_merge_methods=["merge", "squash"]
            ),
            "squash merges only",
        ),
        (
            lambda r: rule(r, "pull_request")["parameters"].update(
                required_review_thread_resolution=False
            ),
            "review threads",
        ),
        (
            lambda r: rule(r, "required_status_checks")["parameters"]["required_status_checks"][
                0
            ].pop("integration_id"),
            "GitHub Actions",
        ),
        (
            lambda r: r["bypass_actors"].append(
                {"actor_id": 101, "actor_type": "Integration", "bypass_mode": "always"}
            ),
            "bypass",
        ),
        (lambda r: r.update(enforcement="evaluate"), "not active"),
        (
            lambda r: r["conditions"]["ref_name"].update(include=["refs/heads/release"]),
            "default branch",
        ),
        (
            lambda r: r.update(rules=[x for x in r["rules"] if x["type"] != "non_fast_forward"]),
            "force pushes",
        ),
    ],
)
def test_ruleset_problems(change: Callable[[dict[str, Any]], object], problem: str) -> None:
    ruleset = copy.deepcopy(RULESET)
    change(ruleset)
    assert any(
        problem in p
        for p in ruleset_problems([ruleset], "main", every_pr=True, agent_identity=True)
    )


@pytest.mark.parametrize(("every_pr", "agent_identity"), MODES)
def test_the_decided_ruleset_passes_in_every_mode(every_pr: bool, agent_identity: bool) -> None:
    params = rule(RULESET, "pull_request")["parameters"]
    assert params["required_approving_review_count"] == 0
    assert params["require_last_push_approval"] is False
    assert params["require_code_owner_review"] is True
    problems = ruleset_problems([RULESET], "main", every_pr=every_pr, agent_identity=agent_identity)
    assert problems == []


@pytest.mark.parametrize(
    ("required", "problem"),
    [
        ({"required_approving_review_count": 1}, APPROVAL_IN_FLIGHT),
        ({"require_last_push_approval": True}, LAST_PUSH_IN_FLIGHT),
    ],
)
def test_only_flight_with_agent_identity_refuses_a_required_approval(
    required: dict[str, object], problem: str
) -> None:
    ruleset = copy.deepcopy(RULESET)
    rule(ruleset, "pull_request")["parameters"].update(required)
    # Only Flight with Agent identity relies on the Reviewer App's approval alone, which either
    # setting stops or may stop (plan 4's live trial).
    assert ruleset_problems([ruleset], "main", every_pr=False, agent_identity=True) == [problem]
    for every_pr, agent_identity in ((True, False), (True, True), (False, False)):
        assert (
            ruleset_problems([ruleset], "main", every_pr=every_pr, agent_identity=agent_identity)
            == []
        )


def test_flight_with_agent_identity_reads_the_approvals_of_every_enforced_ruleset() -> None:
    strict = copy.deepcopy(RULESET)
    strict["id"] = 10
    rule(strict, "pull_request")["parameters"].update(required_approving_review_count=2)
    # GitHub applies every active ruleset on the branch, so the strictest one decides.
    assert ruleset_problems([RULESET, strict], "main", every_pr=False, agent_identity=True) == [
        APPROVAL_IN_FLIGHT
    ]
    elsewhere = {"ref_name": {"include": ["refs/heads/release"], "exclude": []}}
    for inert in ({**strict, "enforcement": "disabled"}, {**strict, "conditions": elsewhere}):
        assert ruleset_problems([RULESET, inert], "main", every_pr=False, agent_identity=True) == []


@pytest.mark.parametrize(("every_pr", "agent_identity"), MODES)
def test_every_mode_names_a_missing_pull_request_rule(every_pr: bool, agent_identity: bool) -> None:
    ruleset = copy.deepcopy(RULESET)
    ruleset["rules"] = [r for r in ruleset["rules"] if r["type"] != "pull_request"]
    problems = ruleset_problems([ruleset], "main", every_pr=every_pr, agent_identity=agent_identity)
    assert problems == ["the ruleset has no pull_request rule"]


def test_owner_reads_are_get_requests(fake_run: FakeRun) -> None:
    fake_run.answer(
        ["gh", "api", "--method", "GET", "repos/o/r"],
        ProcessResult(["gh"], 0, '{"id": 2}', "", 0.0),
    )
    assert gh_get("repos/o/r") == {"id": 2}
    fake_run.answer(
        ["gh", "api", "--method", "GET", "repos/o/r/rulesets"],
        ProcessResult(
            ["gh"],
            1,
            '{"message": "Upgrade to GitHub Pro"}',
            "gh: Upgrade to GitHub Pro (HTTP 403)",
            0.0,
        ),
    )
    with pytest.raises(OwnerReadError) as caught:
        gh_get("repos/o/r/rulesets")
    assert (caught.value.status, caught.value.message) == (403, "Upgrade to GitHub Pro")
    fake_run.answer(
        ["gh", "api", "--method", "GET", "repos/o/r/rulesets/9"],
        ProcessResult(["gh"], 0, '{"id": 9', "", 0.0, stdout_truncated=True),
    )
    with pytest.raises(OwnerReadError, match="exceeded"):
        gh_get("repos/o/r/rulesets/9")


def test_codeowners_must_match_the_mode() -> None:
    assert codeowners_problems("* @o\n", True, "@o", "python") == []
    assert codeowners_problems("* @o\n/src/ @team\n", True, "@o", "python")
    assert codeowners_problems(PROTECTED, False, "@o", "agnostic") == []
    assert codeowners_problems("* @o\n" + PROTECTED, False, "@o", "agnostic")
    assert codeowners_problems(PROTECTED.replace("/devctl @o\n", ""), False, "@o", "agnostic")


def test_codeowners_must_name_a_team_that_is_the_code_owner() -> None:
    team = "@my-org/platform-team"
    assert codeowners_problems(f"* {team}\n", True, team, "agnostic") == []
    assert codeowners_problems("* @my-org\n", True, team, "agnostic") == [
        f"the one active CODEOWNERS line is not * {team}"
    ]
    owned = PROTECTED.replace(" @o\n", f" {team}\n")
    assert codeowners_problems(owned, False, team, "agnostic") == []
    # Flight checks every Protected path against the code owner, not only the first.
    assert codeowners_problems(PROTECTED, False, team, "agnostic") == [
        f"CODEOWNERS must name only {team} for: {', '.join(PROTECTED_PATHS)}"
    ]
    one_path = owned.replace(f"/.rapid-ship/ {team}\n", "/.rapid-ship/ @my-org\n")
    assert codeowners_problems(one_path, False, team, "agnostic") == [
        f"CODEOWNERS must name only {team} for: .rapid-ship/"
    ]


def test_python_flight_codeowners_protects_the_guardrail_settings() -> None:
    assert any("pyproject.toml" in p for p in codeowners_problems(PROTECTED, False, "@o", "python"))
    python = "".join(f"/{path} @o\n" for path in PYTHON_PROTECTED_PATHS)
    assert codeowners_problems(PROTECTED + python, False, "@o", "python") == []


def test_protected_paths_match_the_seeded_codeowners() -> None:
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    templates = render_files("python", variables, ())
    [template] = [t for t in templates if t.path == ".github/CODEOWNERS"]
    assert template.content is not None
    flight = [
        line.removeprefix("# ")
        for line in template.content.decode().splitlines()
        if re.fullmatch(r"# /\S+ @o", line)
    ]
    protected = {line.split()[0].removeprefix("/") for line in flight}
    assert protected == {*PROTECTED_PATHS, *PYTHON_PROTECTED_PATHS}
    assert codeowners_problems("".join(f"{line}\n" for line in flight), False, "@o", "python") == []


def test_installation_permissions_must_match_exactly() -> None:
    worker = {"contents": "write", "pull_requests": "write", "issues": "write", "metadata": "read"}
    assert installation_problems({"permissions": worker}, "worker") == []
    assert installation_problems({"permissions": {**worker, "workflows": "write"}}, "worker")


def test_all_github_items_ok(ctx_github: MakeContext) -> None:
    items = github_items(ctx_github())
    assert {(i.name, i.status) for i in items} == {
        ("ruleset", "ok"),
        ("CODEOWNERS", "ok"),
        ("delete branch on merge", "ok"),
        ("fork PR workflow approval", "ok"),
        ("Worker App installation", "ok"),
        ("Reviewer App installation", "ok"),
        ("Worker App key", "ok"),
        ("Reviewer App key", "ok"),
    }


def test_plan_limited_rulesets_are_missing(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.fail(
        "repos/o/r/rulesets?targets=branch",
        OwnerReadError(
            403, "Upgrade to GitHub Pro or make this repository public to enable this feature."
        ),
    )
    [ruleset] = [i for i in github_items(ctx_github()) if i.name == "ruleset"]
    assert ruleset.status == "missing"
    assert "public repository or a paid GitHub plan" in ruleset.detail


def test_unreadable_bypass_list_is_unknown(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve(
        "repos/o/r/rulesets/9", {k: v for k, v in RULESET.items() if k != "bypass_actors"}
    )
    [ruleset] = [i for i in github_items(ctx_github()) if i.name == "ruleset"]
    assert ruleset.status == "unknown"


def test_missing_reviewer_key(
    ctx_github: MakeContext, keychain_without_reviewer: FakeKeychain
) -> None:
    items = {i.name: i for i in github_items(ctx_github(keychain=keychain_without_reviewer))}
    assert items["Reviewer App key"].status == "missing"
    assert items["Reviewer App installation"].status == "missing"  # no key, no JWT to look it up
    assert items["Worker App key"].status == "ok"


def test_uninstalled_app(ctx_github: MakeContext, github: FakeGitHub) -> None:
    github.uninstall(202, "o/r")
    items = {i.name: i for i in github_items(ctx_github())}
    assert items["Reviewer App installation"].status == "missing"
    assert items["Reviewer App key"].status == "unknown"
    assert items["Reviewer App key"].detail == "key found; minting needs the App installed"


def test_doctor_makes_no_writes(
    ctx_github: MakeContext, fake_run: FakeRun, github: FakeGitHub
) -> None:
    ctx = ctx_github()
    before = snapshot(ctx.root)
    run_doctor(ctx)
    assert snapshot(ctx.root) == before
    assert not any(
        a in {"fetch", "push", "worktree", "commit", "add"} for argv in fake_run.argv for a in argv
    )
    writes = [(c.method, c.path) for c in github.calls if c.method != "GET"]
    assert writes
    assert all(m == "POST" and p.endswith("/access_tokens") for m, p in writes)


@pytest.mark.parametrize(("every_pr", "agent_identity"), MODES)
def test_every_mode_requires_code_owner_review(
    ctx_github: MakeContext, recorded: RecordedOwner, every_pr: bool, agent_identity: bool
) -> None:
    context = ctx_github()
    escalation = dataclasses.replace(context.project.escalation, every_pr=every_pr)
    project = dataclasses.replace(context.project, escalation=escalation)
    if not agent_identity:
        project = dataclasses.replace(project, worker_app=None, reviewer_app=None)
    mode = dataclasses.replace(context, project=project)
    [whole] = [i for i in github_items(mode) if i.name == "ruleset"]
    assert (whole.status, whole.detail) == (
        "ok",
        "an active ruleset on main has every setting rs-setup applies",
    )
    # One ruleset in every setup: no Mode accepts it without code-owner review (Spec 1 section 8).
    ruleset = copy.deepcopy(RULESET)
    rule(ruleset, "pull_request")["parameters"].update(require_code_owner_review=False)
    recorded.serve("repos/o/r/rulesets/9", ruleset)
    [without] = [i for i in github_items(mode) if i.name == "ruleset"]
    assert (without.status, without.detail) == (
        "missing",
        "the pull_request rule does not require code-owner review",
    )


def test_agent_identity_off_has_no_app_items_and_asks_github_nothing(
    ctx_github: MakeContext, github: FakeGitHub
) -> None:
    context = ctx_github()
    off = dataclasses.replace(context.project, worker_app=None, reviewer_app=None)
    items = github_items(dataclasses.replace(context, project=off, access=None))
    assert [i.name for i in items] == [
        "ruleset",
        "CODEOWNERS",
        "delete branch on merge",
        "fork PR workflow approval",
    ]
    assert {i.area for i in items} == {"github"}
    assert github.calls == []


def test_app_items_are_in_the_agent_identity_area(ctx_github: MakeContext) -> None:
    areas = {i.name: i.area for i in github_items(ctx_github())}
    assert areas["Worker App installation"] == areas["Reviewer App key"] == "agent identity"


def test_an_installed_app_whose_slug_differs_from_the_record_is_missing(
    ctx_github: MakeContext,
) -> None:
    context = ctx_github()
    project = dataclasses.replace(context.project, reviewer_app=App(REVIEWER_ID, "o-rs-reviewer"))
    items = {i.name: i for i in github_items(dataclasses.replace(context, project=project))}
    reviewer = items["Reviewer App installation"]
    assert reviewer.status == "missing"
    assert reviewer.detail == (
        "the installed App's slug is rs-reviewer, but .rapid-ship/project.toml records "
        "o-rs-reviewer"
    )
    assert items["Worker App installation"].status == "ok"
