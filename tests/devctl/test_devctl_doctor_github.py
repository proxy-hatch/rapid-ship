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
from devctl.doctor_rules import NO_APPROVAL
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
RULESET: dict[str, Any] = json.loads((FIXTURES / "ruleset.json").read_text())
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
                require_last_push_approval=False
            ),
            "most recent push",
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
    assert codeowners_problems("* @o\n", True, "o", "python") == []
    assert codeowners_problems("* @o\n/src/ @team\n", True, "o", "python")
    assert codeowners_problems(PROTECTED, False, "o", "agnostic") == []
    assert codeowners_problems("* @o\n" + PROTECTED, False, "o", "agnostic")
    assert codeowners_problems(PROTECTED.replace("/devctl @o\n", ""), False, "o", "agnostic")


def test_python_flight_codeowners_protects_the_guardrail_settings() -> None:
    assert any("pyproject.toml" in p for p in codeowners_problems(PROTECTED, False, "o", "python"))
    python = "".join(f"/{path} @o\n" for path in PYTHON_PROTECTED_PATHS)
    assert codeowners_problems(PROTECTED + python, False, "o", "python") == []


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
    assert codeowners_problems("".join(f"{line}\n" for line in flight), False, "o", "python") == []


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


def relaxed_ruleset() -> dict[str, Any]:
    """rs-setup's ruleset without the review requirement, which Flight without Agent identity
    drops."""
    ruleset = copy.deepcopy(RULESET)
    rule(ruleset, "pull_request")["parameters"].update(
        required_approving_review_count=0,
        require_code_owner_review=False,
        require_last_push_approval=False,
    )
    return ruleset


def test_only_flight_without_agent_identity_accepts_no_review_requirement() -> None:
    relaxed = relaxed_ruleset()
    assert ruleset_problems([relaxed], "main", every_pr=False, agent_identity=False) == []
    assert ruleset_problems([RULESET], "main", every_pr=False, agent_identity=False) == []
    # The whole ruleset passes in Walk without Agent identity and in Flight with it too.
    for every_pr, agent_identity in ((True, False), (False, True)):
        full = ruleset_problems([RULESET], "main", every_pr=every_pr, agent_identity=agent_identity)
        assert full == []
    for every_pr, agent_identity in ((True, False), (True, True), (False, True)):
        problems = ruleset_problems(
            [relaxed], "main", every_pr=every_pr, agent_identity=agent_identity
        )
        assert NO_APPROVAL in problems
        assert any("code-owner review" in p for p in problems)


def test_the_relaxed_ruleset_still_needs_everything_else() -> None:
    relaxed = relaxed_ruleset()
    rule(relaxed, "pull_request")["parameters"].update(allowed_merge_methods=["merge"])
    assert ruleset_problems([relaxed], "main", every_pr=False, agent_identity=False) == [
        "the pull_request rule must allow squash merges only"
    ]
    relaxed["rules"] = [r for r in relaxed["rules"] if r["type"] != "pull_request"]
    assert ruleset_problems([relaxed], "main", every_pr=False, agent_identity=False) == [
        "the ruleset has no pull_request rule"
    ]


def test_doctor_calls_the_relaxed_ruleset_ok_only_in_flight_without_agent_identity(
    ctx_github: MakeContext, recorded: RecordedOwner
) -> None:
    recorded.serve("repos/o/r/rulesets/9", relaxed_ruleset())
    context = ctx_github()
    walk = {i.name: i for i in github_items(context)}["ruleset"]
    escalation = dataclasses.replace(context.project.escalation, every_pr=False)
    on = dataclasses.replace(context.project, escalation=escalation)
    off = dataclasses.replace(on, worker_app=None, reviewer_app=None)
    with_identity = {i.name: i for i in github_items(dataclasses.replace(context, project=on))}
    flight = {i.name: i for i in github_items(dataclasses.replace(context, project=off))}
    assert walk.status == "missing"
    assert with_identity["ruleset"].status == "missing"
    assert flight["ruleset"].status == "ok"
    assert "without the review requirement" in flight["ruleset"].detail
    # Flight with Agent identity, the Mode Task 10's trial reaches, accepts the whole ruleset.
    recorded.serve("repos/o/r/rulesets/9", RULESET)
    with_identity = {i.name: i for i in github_items(dataclasses.replace(context, project=on))}
    assert with_identity["ruleset"].status == "ok"


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
