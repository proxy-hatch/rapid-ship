"""Offline: the merge guard against RecordedOwner, a simulated owner reader. No live GitHub."""

from __future__ import annotations

import base64
from dataclasses import replace
from pathlib import Path

import pytest

from check_workspace import new_workspace
from devctl.codeowners import FileChange
from devctl.command_line import simple_commands
from devctl.doctor_items import OwnerGet, OwnerReadError, gh_get
from devctl.hook import run_hook
from devctl.hook_protocols import Decision, HookSettings, ToolCall
from devctl.merge_guard import LocalBranches, Merge, find_merge, guard
from devctl.merge_guard_github import PullRequest, changed_files
from devctl.process import ProcessResult
from github_fakes import FakeRun, RecordedOwner

HEAD = "a" * 40
OTHER = "b" * 40
PR = "repos/o/r/pulls/7"
CODEOWNERS = "repos/o/r/contents/.github/CODEOWNERS?ref=main"
FILES = "repos/o/r/pulls/7/files?per_page=100&page=1"
FILE_FIELDS = "[.[] | {filename, status, previous_filename}]"
REVIEWS = "repos/o/r/pulls/7/reviews?per_page=100&page=1"
RUNS = f"repos/o/r/commits/{HEAD}/check-runs?check_name=devctl%20check&filter=latest&per_page=100"
BY_BRANCH = "repos/o/r/pulls?head=o:task&state=open&per_page=100"
# GitHub gives a pull request without a body "body": null.
PULL = {"number": 7, "head": {"sha": HEAD}, "base": {"ref": "main"}, "body": None}
OWNERS = base64.b64encode(b"* @o\n# /.github/ @o\n# /**/AGENTS.md @o\n").decode()
TASK = LocalBranches(frozenset({"main"}), "task")
OFF = HookSettings(  # Flight, with Agent identity off
    agent_identity=False,
    protected=(),
    repository="o/r",
    reviewer_app_slug=None,
    every_pr=False,
    unit_tests=("tests/unit/**",),
)
ON = replace(OFF, agent_identity=True, reviewer_app_slug="o-reviewer")
WALK = replace(OFF, every_pr=True)
CHECKED = f"merge denied: devctl check on PR #7 at {HEAD} is {{}}; "
CHECKED += "wait for it to pass or fix what it reports, then merge again"
UNAPPROVED = f"merge denied: PR #7 has no Reviewer App approval of its head {HEAD}; "
UNAPPROVED += "have the Reviewer review that commit, then merge again"
TOUCHES = "merge denied: PR #7 touches the Protected set ({}); "
TOUCHES += "the owner merges it in GitHub's web interface"
CANNOT = "merge denied: the merge guard cannot check this merge: {}; fix that, then merge again"
NO_REPOSITORY = "no repository: set [github] repository in .rapid-ship/project.toml "
NO_REPOSITORY += "or pass -R OWNER/NAME"
BUDGET = "its GitHub reads would pass the 300-second budget; fix that, then merge again"
IN_WALK = "merge denied: in Walk the owner merges every pull request; ask the owner to merge "
IN_WALK += "PR #7"
DECLARES = "merge denied: PR #7 declares {}, so the owner merges it"
REMOVED_BEHAVIOURAL = "a removed behavioural test"
OVER_CAP = "an overage of the diff cap"
APPS = (
    'worker_app_id = 1\nworker_app_slug = "o-worker"\n'
    'reviewer_app_id = 2\nreviewer_app_slug = "o-reviewer"\n'
)


def run(status: str = "completed", conclusion: str | None = "success", **fields: object) -> object:
    found = {"id": 1, "name": "devctl check", "status": status, "conclusion": conclusion}
    return {**found, "app": {"id": 15368}, **fields}


def review(state: str = "APPROVED", commit: str = HEAD, **fields: object) -> object:
    found = {"id": 1, "user": {"login": "o-reviewer[bot]"}, "state": state, "commit_id": commit}
    return {**found, **fields}


def evidence(*lines: str) -> str:
    """A PR body whose Evidence section holds a command, these lines and Not covered."""
    section = ["## Evidence", "", "- `uv run pytest`: 12 passed", *lines, "", "Not covered: none"]
    return "\n".join(section) + "\n"


REMOVES_BEHAVIOURAL = evidence(
    "", "Removed tests:", "- `tests/test_api.py::TestApi::test_delete`: gone"
)
REMOVES_UNIT = evidence("", "Removed tests:", "- `tests/unit/test_core.py::test_old`: replaced")
OVER = evidence("", "Over the diff cap: a generated client, accepted by the owner")


def owner(
    files: object = None, runs: object = None, reviews: object = None, body: str | None = None
) -> RecordedOwner:
    return RecordedOwner(
        {
            PR: {**PULL, "body": body},
            CODEOWNERS: {"encoding": "base64", "content": OWNERS},
            FILES: files or [{"filename": "src/app/core.py", "status": "modified"}],
            REVIEWS: [review()] if reviews is None else reviews,
            RUNS: {"check_runs": [run()] if runs is None else runs},
        }
    )


def guarded(line: str, reader: RecordedOwner, settings: HookSettings | None = OFF) -> str | None:
    merge = find_merge(simple_commands(line)[0], lambda: TASK)
    assert merge is not None
    return guard(merge, settings, reader, lambda: TASK, lambda: 0.0)


def project(tmp_path: Path, github: str = "", mode: str = "every_pr = false") -> Path:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(
        ".rapid-ship/project.toml",
        f'stack = "python"\n\n[escalation]\n{mode}\n\n[github]\nrepository = "o/r"\n{github}',
    )
    return workspace.root


def hooked(root: Path, line: str, reader: OwnerGet) -> tuple[Decision, str]:
    return run_hook(ToolCall(line, (), root), reader)


def unread_github(path: str, jq: str | None = None) -> object:
    raise AssertionError(f"GitHub was read: {path}")


@pytest.mark.parametrize(
    ("settings", "paths"),
    [(OFF, [PR, CODEOWNERS, FILES, RUNS]), (ON, [PR, CODEOWNERS, FILES, REVIEWS, RUNS])],
)
def test_a_passing_unprotected_merge_at_the_checked_head_gets_no_decision(
    settings: HookSettings, paths: list[str]
) -> None:
    reader = owner()
    assert guarded(f"gh pr merge 7 --squash --match-head-commit {HEAD}", reader, settings) is None
    assert reader.paths == paths


@pytest.mark.parametrize(
    ("runs", "state"),
    [
        ([run("queued", None)], "queued"),
        ([run("in_progress", None)], "in_progress"),
        ([run(conclusion="failure")], "failure"),
        ([run(conclusion="cancelled")], "cancelled"),
        ([run(conclusion="skipped")], "skipped"),
        ([], "missing"),
        ([run(app={"id": 999})], "missing"),
        ([run(), run(conclusion="failure", id=2)], "failure"),
    ],
)
def test_a_check_that_has_not_passed_denies(runs: list[object], state: str) -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    assert guarded(line, owner(runs=runs)) == CHECKED.format(state)


@pytest.mark.parametrize(
    ("change", "paths"),
    [
        ({"filename": ".github/workflows/x.yml", "status": "modified"}, ".github/workflows/x.yml"),
        ({"filename": "docs/AGENTS.md", "status": "added"}, "docs/AGENTS.md"),
        (
            {"filename": "x.md", "status": "renamed", "previous_filename": ".github/x.md"},
            ".github/x.md",
        ),
        ({"filename": "docs/corrections/c1.md", "status": "modified"}, "docs/corrections/c1.md"),
        ({"filename": "docs/corrections/c1.md", "status": "removed"}, "docs/corrections/c1.md"),
    ],
)
def test_a_protected_change_at_the_base_denies(change: object, paths: str) -> None:
    assert guarded("gh pr merge 7", owner(files=[change])) == (
        f"merge denied: PR #7 touches the Protected set ({paths}); "
        "the owner merges it in GitHub's web interface"
    )


@pytest.mark.parametrize("status", ["open", "implemented"])
def test_an_added_ledger_entry_is_not_protected_whatever_its_status(status: str) -> None:
    reader = owner(files=[{"filename": f"docs/corrections/{status}.md", "status": "added"}])
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", reader) is None
    assert not any("corrections" in path for path in reader.paths)


@pytest.mark.parametrize(
    ("line", "retry"),
    [
        ("gh pr merge 7 --squash", "gh pr merge 7 --squash"),
        (f"gh pr merge 7 --squash --match-head-commit {OTHER}", "gh pr merge 7 --squash"),
        ("./devctl as worker gh pr merge 7 --squash", "./devctl as worker gh pr merge 7 --squash"),
    ],
)
def test_a_merge_not_pinned_to_the_checked_head_is_denied_with_the_exact_retry(
    line: str, retry: str
) -> None:
    assert guarded(line, owner()) == (
        f"merge denied: PR #7 merges only at the checked head {HEAD}; "
        f"run {retry} --match-head-commit {HEAD}"
    )


@pytest.mark.parametrize(
    "reviews",
    [
        [],
        [review(user={"login": "octo"})],
        [review(user={"login": "o-reviewer"})],
        [review(commit=OTHER)],
        [review(), review("CHANGES_REQUESTED", id=2)],
        [review("COMMENTED")],
        [review("DISMISSED")],
    ],
)
def test_with_agent_identity_a_head_without_the_reviewer_apps_approval_is_denied(
    reviews: list[object],
) -> None:
    line = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
    assert guarded(line, owner(reviews=reviews), ON) == UNAPPROVED


def test_comments_and_dismissed_reviews_do_not_decide() -> None:
    reviews = [review(), review("COMMENTED", OTHER, id=2), review("DISMISSED", id=3)]
    line = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
    assert guarded(line, owner(reviews=reviews), ON) is None


@pytest.mark.parametrize(
    ("line", "first"),
    [
        ("gh pr merge task", BY_BRANCH),
        ("gh pr merge", BY_BRANCH),
        ("gh pr merge fork:task", "repos/o/r/pulls?head=fork:task&state=open&per_page=100"),
        ("gh pr merge 'fix#1'", "repos/o/r/pulls?head=o:fix%231&state=open&per_page=100"),
        ("gh pr merge '#7'", PR),
        ("gh pr merge https://github.com/x/y/pull/7", "repos/x/y/pulls/7"),
        ("gh pr merge https://github.com/x/y/pull/7/files", "repos/x/y/pulls/7"),
        # gh merges the PR a URL names, in the URL's repository, whatever -R says.
        ("gh pr merge https://github.com/x/y/pull/7 -R a/b", "repos/x/y/pulls/7"),
        ("gh pr merge 7 -R x/y", "repos/x/y/pulls/7"),
        ("gh pr -R x/y merge 7", "repos/x/y/pulls/7"),
    ],
)
def test_each_target_reads_its_pull_request(line: str, first: str) -> None:
    reader = owner()
    reader.serve(BY_BRANCH, [PULL])
    guarded(line, reader)
    assert reader.paths[0] == first


def test_a_pr_found_by_its_branch_is_checked_by_its_number() -> None:
    reader = owner()
    reader.serve(BY_BRANCH, [PULL])
    assert guarded(f"gh pr merge --match-head-commit {HEAD}", reader) is None
    assert reader.paths == [BY_BRANCH, CODEOWNERS, FILES, RUNS]


def test_a_pr_the_guard_cannot_identify_or_read_is_denied() -> None:
    unreadable = owner()
    unreadable.fail(PR, OwnerReadError(404, "HTTP 404: Not Found"))
    assert guarded("gh pr merge 7", unreadable) == CANNOT.format("HTTP 404: Not Found")

    nowhere = owner()
    assert guarded("gh pr merge 7", nowhere, replace(OFF, repository=None)) == (
        CANNOT.format(NO_REPOSITORY)
    )
    assert nowhere.paths == []

    unopened = owner()
    unopened.serve(BY_BRANCH, [])
    assert guarded("gh pr merge task", unopened) == (
        CANNOT.format("no open pull request has head o:task")
    )

    doubled = owner()
    doubled.serve(BY_BRANCH, [PULL, {**PULL, "number": 8}])
    assert guarded("gh pr merge task", doubled) == (
        CANNOT.format("2 open pull requests have head o:task; name one by number")
    )

    detached = LocalBranches(frozenset({"main"}), None)
    loose = owner()
    merge = Merge("pr-merge", command=("gh", "pr", "merge"))
    assert guard(merge, OFF, loose, lambda: detached, lambda: 0.0) == (
        CANNOT.format("HEAD is detached and the command names no pull request")
    )
    assert loose.paths == []


def test_an_error_inside_the_guard_is_denied() -> None:
    reader = owner()
    reader.serve(PR, [])
    denial = guarded("gh pr merge 7", reader)
    assert denial is not None
    assert denial.startswith(
        "merge denied: the merge guard cannot check this merge: the guard failed: "
    )
    assert denial.endswith("; fix that, then merge again")


def test_files_are_read_page_by_page() -> None:
    page = [{"filename": f"src/app/m{at}.py", "status": "modified"} for at in range(100)]
    reader = owner(files=page)
    second = "repos/o/r/pulls/7/files?per_page=100&page=2"
    reader.serve(second, [{"filename": ".github/x", "status": "added"}])
    assert guarded("gh pr merge 7", reader) == TOUCHES.format(".github/x")
    assert reader.paths == [PR, CODEOWNERS, FILES, second]
    assert reader.filters == {FILES: FILE_FIELDS, second: FILE_FIELDS}


def test_gh_prints_only_the_fields_of_the_files_that_the_guard_reads(fake_run: FakeRun) -> None:
    """Simulated gh: the whole page, patches included, passes gh_get's output cap."""
    whole = ["gh", "api", "--method", "GET", FILES]
    fake_run.answer(whole, ProcessResult(whole, 0, "[", "", 0.0, stdout_truncated=True))
    page = '[{"filename": "a.py", "status": "renamed", "previous_filename": "b.py"}]'
    fake_run.answer([*whole, "--jq", FILE_FIELDS], ProcessResult(whole, 0, page, "", 0.0))
    pull = PullRequest("o/r", 7, HEAD, "main", body="")
    assert changed_files(gh_get, pull) == [FileChange("a.py", "renamed", "b.py")]


def test_a_pr_with_more_files_than_github_lists_is_denied() -> None:
    page = [{"filename": f"src/app/m{at}.py", "status": "modified"} for at in range(100)]
    reader = owner(files=page)
    for number in range(2, 32):
        reader.serve(f"repos/o/r/pulls/7/files?per_page=100&page={number}", page)
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", reader) == CANNOT.format(
        "GitHub lists at most 3,000 files of a pull request, and this one has more"
    )
    assert reader.paths[-1] == "repos/o/r/pulls/7/files?per_page=100&page=30"


def test_codeowners_is_read_where_github_reads_it() -> None:
    root_file = "repos/o/r/contents/CODEOWNERS?ref=main"
    docs_file = "repos/o/r/contents/docs/CODEOWNERS?ref=main"
    guide = [{"filename": "docs/AGENTS.md", "status": "modified"}]
    reader = owner(files=guide)
    reader.fail(CODEOWNERS, OwnerReadError(404, "Not Found"))
    reader.serve(root_file, {"encoding": "base64", "content": OWNERS})
    assert guarded("gh pr merge 7", reader) == TOUCHES.format("docs/AGENTS.md")
    assert reader.paths == [PR, CODEOWNERS, root_file, FILES]

    unowned = owner(files=guide)
    unowned.fail(CODEOWNERS, OwnerReadError(404, "Not Found"))
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", unowned) is None
    assert unowned.paths == [PR, CODEOWNERS, root_file, docs_file, FILES, RUNS]


def test_codeowners_that_cannot_be_read_denies() -> None:
    reader = owner()
    reader.fail(CODEOWNERS, OwnerReadError(403, "Resource not accessible by integration"))
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", reader) == CANNOT.format(
        "Resource not accessible by integration"
    )
    assert reader.paths == [PR, CODEOWNERS]


def test_each_merge_on_the_line_is_guarded(tmp_path: Path) -> None:
    root = project(tmp_path)
    reader = owner()
    line = f"gh pr merge 7 --match-head-commit {HEAD} && gh pr merge 8 --squash"
    assert hooked(root, line, reader) == ("deny", CANNOT.format("Not Found"))
    assert reader.paths == [PR, CODEOWNERS, FILES, RUNS, "repos/o/r/pulls/8"]


def test_a_merge_on_a_line_that_shell_rules_cannot_split_is_denied(tmp_path: Path) -> None:
    root = project(tmp_path)
    line = "gh pr merge 7 --squash; echo 'unclosed"
    assert hooked(root, line, unread_github) == (
        "deny",
        CANNOT.format("shell rules cannot split the command line: No closing quotation"),
    )
    with pytest.raises(ValueError, match="No closing quotation"):
        hooked(root, "git push -f origin task; echo 'unclosed", unread_github)


def test_the_guard_denies_before_a_read_could_pass_its_budget() -> None:
    clock = iter([0.0, 250.0])
    merge = find_merge(simple_commands("gh pr merge 7")[0], lambda: TASK)
    assert merge is not None
    reader = owner()
    denial = guard(merge, OFF, reader, lambda: TASK, lambda: next(clock))
    assert reader.paths == [PR]
    assert denial is not None
    assert denial.endswith(BUDGET)

    edge = owner()  # a read that could end at the budget itself is still made
    assert guard(merge, OFF, edge, lambda: TASK, lambda: 240.0) is not None
    assert edge.paths == [PR, CODEOWNERS, FILES, RUNS]


def test_the_merges_on_a_line_share_one_budget(tmp_path: Path) -> None:
    root = project(tmp_path)
    reader = owner()
    clock = iter([0.0, 0.0, 0.0, 0.0, 0.0, 240.1])  # the run's start, then one tick per read
    line = f"gh pr merge 7 --match-head-commit {HEAD}; gh pr merge 7 --match-head-commit {HEAD}"
    decision, reason = run_hook(ToolCall(line, (), root), reader, clock=lambda: next(clock))
    assert decision == "deny"
    assert reason.endswith(BUDGET)
    assert reader.paths == [PR, CODEOWNERS, FILES, RUNS]


def test_only_gh_pr_merge_reads_github(tmp_path: Path) -> None:
    root = project(tmp_path)
    for line in [
        "git status",
        "gh pr view 7",
        "gh api repos/o/r/pulls/7",
        "git push origin task",
        "gh pr merge 7 --admin",
    ]:
        hooked(root, line, unread_github)

    reader = RecordedOwner({})
    hooked(root, "gh pr merge 7", reader)
    assert reader.paths[:1] == [PR]


def test_with_agent_identity_a_direct_merge_is_denied_before_the_guard_runs(tmp_path: Path) -> None:
    root = project(tmp_path, APPS)
    decision, reason = hooked(root, "gh pr merge 7", unread_github)
    assert (decision, reason[:4]) == ("deny", "G8: ")

    reader = RecordedOwner({})
    assert hooked(root, "./devctl as worker gh pr merge 7", reader) == (
        "deny",
        CANNOT.format("Not Found"),
    )
    assert reader.paths == [PR]


def test_reviews_are_read_page_by_page() -> None:
    crowd = [review(user={"login": "octo"}, id=at) for at in range(1, 101)]
    reader = owner(reviews=crowd)
    second = "repos/o/r/pulls/7/reviews?per_page=100&page=2"
    reader.serve(second, [review(id=101)])
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", reader, ON) is None
    assert reader.paths == [PR, CODEOWNERS, FILES, REVIEWS, second, RUNS]


def test_the_denials_come_in_the_order_protected_check_review_head() -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    protected = owner(
        files=[{"filename": ".github/x", "status": "modified"}],
        reviews=[],
        runs=[run(conclusion="failure")],
    )
    assert guarded(line, protected, ON) == TOUCHES.format(".github/x")

    failed = owner(reviews=[], runs=[run(conclusion="failure")])
    assert guarded(line, failed, ON) == CHECKED.format("failure")

    assert guarded("gh pr merge 7 --squash", owner(reviews=[]), ON) == UNAPPROVED


@pytest.mark.parametrize("settings", [WALK, replace(ON, every_pr=True)])
def test_in_walk_every_merge_is_denied_once_the_pull_request_is_read(
    settings: HookSettings,
) -> None:
    reader = owner()
    assert (
        guarded(f"gh pr merge 7 --squash --match-head-commit {HEAD}", reader, settings) == IN_WALK
    )
    assert reader.paths == [PR]

    by_branch = owner()
    by_branch.serve(BY_BRANCH, [PULL])
    assert guarded("gh pr merge task", by_branch, settings) == IN_WALK
    assert by_branch.paths == [BY_BRANCH]


@pytest.mark.parametrize(
    ("body", "what"),
    [
        (REMOVES_BEHAVIOURAL, REMOVED_BEHAVIOURAL),
        (OVER, OVER_CAP),
        (
            evidence(
                "",
                "Over the diff cap: a generated client, accepted by the owner",
                "",
                "Removed tests:",
                "- `tests/unit/test_core.py::test_old`: replaced",
                "- tests/test_api.py::test_delete: gone",
            ),
            f"{REMOVED_BEHAVIOURAL} and {OVER_CAP}",
        ),
    ],
)
@pytest.mark.parametrize("settings", [OFF, ON])
def test_in_flight_a_body_that_declares_a_removed_behavioural_test_or_an_overage_is_denied(
    body: str, what: str, settings: HookSettings
) -> None:
    reader = owner(body=body)
    line = f"gh pr merge 7 --squash --match-head-commit {HEAD}"
    assert guarded(line, reader, settings) == DECLARES.format(what)
    assert reader.paths == [PR, CODEOWNERS, FILES]


@pytest.mark.parametrize(
    "body",
    [
        None,
        "",
        REMOVES_UNIT,
        evidence("", "Over the diff cap:"),
        evidence("", "```", "Over the diff cap: a generated client", "```"),
        # The Evidence parsers read only the Evidence section.
        "## Notes\n\nOver the diff cap: a generated client\n\n"
        "Removed tests:\n- `tests/test_api.py::test_delete`: gone\n",
    ],
)
def test_in_flight_a_body_without_either_declaration_passes_to_the_next_rule(
    body: str | None,
) -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    assert guarded(line, owner(body=body, runs=[run(conclusion="failure")])) == (
        CHECKED.format("failure")
    )
    assert guarded(line, owner(body=body)) is None


def test_the_unit_patterns_decide_which_declared_removals_stop_the_merge() -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    every_test_unit = replace(OFF, unit_tests=("tests/**",))
    assert guarded(line, owner(body=REMOVES_BEHAVIOURAL), every_test_unit) is None
    no_unit_tests = replace(OFF, unit_tests=())
    assert guarded(line, owner(body=REMOVES_UNIT), no_unit_tests) == (
        DECLARES.format(REMOVED_BEHAVIOURAL)
    )


def test_walk_comes_first_and_the_declarations_after_the_protected_set() -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    protected = [{"filename": ".github/x", "status": "modified"}]
    failing = [run(conclusion="failure")]

    walk = owner(files=protected, reviews=[], runs=failing, body=OVER)
    assert guarded(line, walk, replace(ON, every_pr=True)) == IN_WALK
    flight = owner(files=protected, reviews=[], runs=failing, body=OVER)
    assert guarded(line, flight, ON) == TOUCHES.format(".github/x")
    declared = owner(reviews=[], runs=failing, body=OVER)
    assert guarded(line, declared, ON) == DECLARES.format(OVER_CAP)


def test_the_hook_reads_the_mode_and_the_unit_tests_from_project_toml(tmp_path: Path) -> None:
    line = f"gh pr merge 7 --match-head-commit {HEAD}"
    walk = owner()
    assert hooked(project(tmp_path / "walk", mode=""), line, walk) == ("deny", IN_WALK)
    assert walk.paths == [PR]

    flight = project(tmp_path / "flight", github='\n[tests]\nunit = ["tests/**"]\n')
    assert hooked(flight, line, owner(body=REMOVES_BEHAVIOURAL)) == (None, "")


def test_without_agent_identity_the_guard_reads_no_review() -> None:
    reader = owner(reviews=[])
    assert guarded(f"gh pr merge 7 --match-head-commit {HEAD}", reader, OFF) is None
    assert REVIEWS not in reader.paths


def test_unreadable_settings_deny_every_merge(tmp_path: Path) -> None:
    line = f"gh pr merge 7 -R o/r --match-head-commit {HEAD}"
    reader = owner()
    assert guarded(line, reader, None) == CANNOT.format(
        "the hook cannot read .rapid-ship/project.toml or .github/CODEOWNERS"
    )
    assert reader.paths == []

    workspace = new_workspace(tmp_path / "main")
    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n\n[linear]\nteam = "x"\n')
    decision, reason = hooked(workspace.root, line, reader)
    assert decision == "deny"
    assert reason.startswith("merge denied: the merge guard cannot check this merge: ")
    assert "[linear] was removed" in reason
    assert reason.endswith("; fix that, then merge again")
    assert reader.paths == []
