"""Offline: --post with a recorded reader and a recording writer; simulated."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from check_workspace import fake_tool
from devctl.cli import main
from devctl.metrics import post as post_module
from devctl.metrics.github import GitHubError, GitHubReader
from devctl.metrics.model import Measured, MetricReport, judge
from devctl.metrics.post import (
    ACTIONS_LOGIN,
    ISSUE_TITLE,
    MARKER,
    PostTarget,
    gh_write,
    post,
    prepare_post,
    status_changes,
)
from devctl.metrics.report import Report, render_markdown
from github_fakes import RecordedOwner
from metrics_fakes import fake_gh, gh_argv, gh_bodies
from test_devctl_metrics_command import responses
from test_devctl_metrics_command import setup as merged_project
from test_devctl_metrics_report import revert
from test_devctl_metrics_revisions import sample_window

NOW = datetime(2026, 10, 16, 5, 41, 7, tzinfo=UTC)
LIMIT = 65_536  # the size that GitHub is believed to refuse above, for an issue body and a comment
ISSUES = "repos/o/r/issues"
LIST = f"{ISSUES}?state=open&creator=github-actions%5Bbot%5D&per_page=64&page=1"
CREATED = {"number": 7, "html_url": "https://github.com/o/r/issues/7"}
REFUSAL = (
    "devctl metrics: --post runs only in GitHub Actions with GH_TOKEN set; "
    "run ./devctl metrics without it to read the report\n"
)
RESET = {"resources": {"core": {"reset": 1791007920}}}  # 06:12 UTC
HOSTILE_STATUS = "ok\n- closed_unmerged: ok -> breached @octocat"  # a person edited the issue body
SIZE_REFUSAL = {"error": "gh: Validation Failed (HTTP 422)"}
SIZE_TAIL = (
    "; GitHub may have found the body too large, and the job summary holds this run's report\n"
)
COMMENT_SIZE_TAIL = (
    "; GitHub may have found the body too large. The issue already holds this run's report, but "
    "its status-change comment was not posted, and a rerun does not post it again. "
    "The job summary holds this run's report too\n"
)


@pytest.fixture
def laptop(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """A monkeypatch for a run outside Actions: CI sets GITHUB_ACTIONS, so clear it first."""
    for name in ("GITHUB_ACTIONS", "GH_TOKEN", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def metric(
    metric_id: str,
    value: float | None,
    threshold: float,
    *,
    unknown: int = 0,
    reason: str | None = None,
) -> MetricReport:
    return judge(
        metric_id, metric_id, "count", "agent", Measured(value, reason, unknown), threshold
    )


OK = metric("reverts", 0, 1)
BREACHED = metric("closed_unmerged", 4, 3)
UNKNOWN = metric("red_merges", 0, 1, unknown=2)


def sample(*metrics: MetricReport) -> Report:
    return Report("o/r", NOW, "main", "tip", sample_window(), True, metrics, ())


def counted_issues(count: int) -> Report:
    """A report whose project-defined metric counts issues, each an item with a URL."""
    found = tuple(
        {
            "label": f"#{n}",
            "url": f"https://github.com/o/r/issues/{n}",
            "time": "2026-10-15T06:12:00Z",
            "state": "counted",
        }
        for n in range(1, count + 1)
    )
    bugs = judge("bugs", "Bugs", "count", "repository", Measured(count, items=found), 5)
    return sample(OK, BREACHED, bugs)


def partly_reverted(files: int, sections: int) -> Report:
    """A report whose one counted revert restored many files and undid many sections."""
    item = revert(
        4,
        files=[f"src/pkg/module_{n}.py" for n in range(files)],
        sections=[f"src/pkg/module_{n}.py:{n + 1}-{n + 4}" for n in range(sections)],
    )
    reverts = judge("reverts", "Reverts", "count", "agent", Measured(1, items=(item,)), 0)
    return sample(reverts, BREACHED)


def unexplained(reason: str) -> Report:
    """A report whose project-defined metric is unknown for a reason that its own code wrote."""
    bugs = judge("bugs", "Bugs", "count", "repository", Measured(None, reason), 5)
    return sample(OK, BREACHED, bugs)


def with_unknown_items() -> Report:
    """A report whose items are not all counted: --json lists an unknown revert and rollback too."""
    revert = {"pr": 9, "state": "unknown", "detail": "its merge commit has no parent in this clone"}
    absent = "commit 0123456 is not in the local history: run git fetch origin"
    when = "2026-10-15T06:12:00Z"
    rollbacks = (
        {"label": "deployment 11", "url": None, "time": when, "state": "counted"},
        {"label": "deployment 12", "url": None, "time": when, "state": "counted"},
        {"label": "deployment 13", "url": None, "time": when, "state": "unknown", "detail": absent},
    )
    return sample(
        judge("reverts", "Reverts", "count", "agent", Measured(0, unknown=1, items=(revert,)), 1),
        BREACHED,
        judge(
            "rollbacks",
            "Rollbacks",
            "count",
            "repository",
            Measured(2, unknown=1, items=rollbacks),
            5,
        ),
    )


def detail(number: int) -> str:
    return f"{ISSUES}/{number}"


class Writes:
    """A GitHubWrite that records each call and answers as GitHub does."""

    def __init__(self, number: int = 7) -> None:
        self.number = number
        self.calls: list[tuple[str, str, Mapping[str, object]]] = []

    def __call__(self, method: str, path: str, body: Mapping[str, object]) -> object:
        self.calls.append((method, path, body))
        if (method, path) == ("POST", ISSUES):
            return {
                "number": self.number,
                "html_url": f"https://github.com/o/r/issues/{self.number}",
            }
        if method == "PATCH":
            number = int(path.rsplit("/", 1)[1])
            return {"number": number, "html_url": f"https://github.com/o/r/issues/{number}"}
        return {"id": 1}

    @property
    def requests(self) -> list[tuple[str, str]]:
        return [(method, path) for method, path, _ in self.calls]

    def body(self, index: int) -> str:
        return str(self.calls[index][2]["body"])


def embedded(body: str) -> str:
    """The JSON that a posted body keeps in its trailing comment."""
    match = re.search(r"\n<!-- rapid-ship-metrics-json\n(.*)-->\n\Z", body, re.DOTALL)
    assert match, body
    return match[1]


def with_json(text: str) -> str:
    """A body that a person might have left: the marker, a report and a JSON comment."""
    return f"{MARKER}\n## older report\n\n<!-- rapid-ship-metrics-json\n{text}\n-->\n"


def previous_body(statuses: Mapping[str, str]) -> str:
    metrics = [{"id": key, "status": value} for key, value in statuses.items()]
    return with_json(json.dumps({"version": 1, "metrics": metrics}))


def projected(
    number: int, login: str = ACTIONS_LOGIN, *, marker: bool = True, pull: bool = False
) -> dict[str, object]:
    """One entry of the body-free list that gh returns for the lookup's projection."""
    return {"number": number, "user": {"login": login}, "has_marker": marker, "pull_request": pull}


def reader_for(served: Mapping[str, object]) -> GitHubReader:
    return GitHubReader("o/r", get=RecordedOwner(served))


def install_gh(
    directory: Path, monkeypatch: pytest.MonkeyPatch, served: Mapping[str, object]
) -> Path:
    fake_gh(directory, served)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return directory


def post_main(
    history_path: Path, monkeypatch: pytest.MonkeyPatch, served: Mapping[str, object], *args: str
) -> int:
    install_gh(history_path.parent / "bin", monkeypatch, served)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GH_TOKEN", "workflow-token")
    monkeypatch.chdir(history_path)
    return main(["metrics", "--post", *args])


@pytest.mark.parametrize(
    ("actions", "token"),
    [(None, None), ("true", None), (None, "token"), ("false", "token"), ("true", "")],
)
def test_post_is_refused_outside_github_actions(
    tmp_path: Path,
    laptop: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    actions: str | None,
    token: str | None,
) -> None:
    bin_dir = install_gh(tmp_path / "bin", laptop, {})
    for name, value in (("GITHUB_ACTIONS", actions), ("GH_TOKEN", token)):
        if value is not None:
            laptop.setenv(name, value)
    laptop.chdir(tmp_path)  # not a repository: the refusal comes before anything reads one

    assert main(["metrics", "--post"]) == 2
    assert capsys.readouterr().err == REFUSAL
    assert not (bin_dir / "gh.log").exists()


def test_the_first_run_opens_the_issue_and_comments_only_on_a_breach_or_unknown() -> None:
    quiet = Writes()
    url = post(sample(OK), PostTarget("o/r", None, {}), quiet, None)

    assert url == "https://github.com/o/r/issues/7"
    assert quiet.requests == [("POST", ISSUES)]
    assert quiet.calls[0][2]["title"] == ISSUE_TITLE
    assert quiet.body(0).startswith(f"{MARKER}\n")

    noisy = Writes()
    post(sample(OK, BREACHED, UNKNOWN), PostTarget("o/r", None, {}), noisy, None)

    assert noisy.requests == [("POST", ISSUES), ("POST", f"{ISSUES}/7/comments")]
    comment = noisy.body(1)
    assert "closed_unmerged: none -> breached (4, at most 3)" in comment
    assert "red_merges: none -> unknown (0, 2 unknown, at most 1)" in comment
    assert "reverts" not in comment


def test_a_later_run_replaces_the_body_and_comments_only_on_a_change() -> None:
    first = Writes(number=5)
    post(sample(OK, BREACHED), PostTarget("o/r", None, {}), first, None)
    target = prepare_post(
        reader_for({LIST: [projected(5)], detail(5): {"body": first.body(0)}}),
    )
    assert target == PostTarget("o/r", 5, {"reverts": "ok", "closed_unmerged": "breached"})

    same = Writes()
    assert post(sample(OK, BREACHED), target, same, None) == "https://github.com/o/r/issues/5"
    assert same.requests == [("PATCH", detail(5))]
    assert same.body(0).startswith(MARKER)

    changed = Writes()
    post(sample(OK, metric("closed_unmerged", 2, 3)), target, changed, None)
    assert changed.requests == [("PATCH", detail(5)), ("POST", f"{detail(5)}/comments")]
    assert "closed_unmerged: breached -> ok (2, at most 3)" in changed.body(1)
    assert "reverts" not in changed.body(1)


def test_the_issue_is_github_actions_lowest_open_one() -> None:
    page_one = [projected(50), *(projected(100 + n, "octo") for n in range(63))]
    page_two = [
        projected(3, "octo"),  # the marker on an issue another account opened
        projected(5),
        projected(2, pull=True),  # a pull request that carries the marker
        projected(4, marker=False),
        projected(9),
    ]
    owner = RecordedOwner(
        {
            LIST: page_one,
            LIST.replace("page=1", "page=2"): page_two,
            detail(5): {"body": previous_body({"reverts": "ok"})},
        }
    )

    target = prepare_post(GitHubReader("o/r", get=owner))

    assert target == PostTarget("o/r", 5, {"reverts": "ok"})
    assert owner.paths == [LIST, LIST.replace("page=1", "page=2"), detail(5)]


def test_no_open_issue_of_the_workflow_means_a_new_one() -> None:
    other = [projected(3, "octo"), projected(4, marker=False), projected(6, pull=True)]

    assert prepare_post(reader_for({LIST: other})) == PostTarget("o/r", None, {})
    assert prepare_post(reader_for({LIST: []})) == PostTarget("o/r", None, {})


@pytest.mark.parametrize(
    "body",
    [
        None,
        "",
        MARKER,
        f"{MARKER}\nedited by hand\n",
        with_json("not json"),
        with_json("[1, 2]"),
        with_json('{"metrics": 3}'),
        with_json('{"metrics": [7, {"id": "x"}, {"status": "ok"}]}'),
        with_json('{"metrics": [{"id": 1, "status": "ok"}]}'),
        pytest.param(
            with_json(json.dumps({"metrics": [{"id": "reverts", "status": HOSTILE_STATUS}]})),
            id="a status that adds a line and a mention",
        ),
        pytest.param(
            with_json('{"metrics": [{"id": "reverts", "status": ["ok"]}]}'),
            id="a status that is not a string",
        ),
        pytest.param(with_json("[" * 20_000 + "]" * 20_000), id="20,000 nested arrays"),
    ],
)
def test_a_body_without_json_has_no_previous_statuses(body: str | None) -> None:
    target = prepare_post(reader_for({LIST: [projected(5)], detail(5): {"body": body}}))

    assert target == PostTarget("o/r", 5, {})
    writes = Writes()
    post(sample(OK), target, writes, None)
    assert writes.requests == [("PATCH", detail(5)), ("POST", f"{detail(5)}/comments")]
    assert "reverts: none -> ok (0, at most 1)" in writes.body(1)


def test_the_four_known_statuses_are_kept_from_the_previous_body() -> None:
    kept = {"a": "ok", "b": "breached", "c": "unknown", "d": "needs Agent identity"}
    body = previous_body({**kept, "e": HOSTILE_STATUS, "f": "OK", "g": ""})

    target = prepare_post(reader_for({LIST: [projected(5)], detail(5): {"body": body}}))

    assert target.previous == kept


def test_lookup_omits_bodies_and_fetches_only_the_selected_issue(
    tmp_path: Path, laptop: pytest.MonkeyPatch
) -> None:
    # Three of these exceed the 1 MiB that one gh answer may hold, so the list must leave them out.
    big = f"{MARKER}\n" + "x" * 400_000

    def issue(number: int, login: str = ACTIONS_LOGIN) -> dict[str, object]:
        return {"number": number, "user": {"login": login}, "body": big}

    served = {
        LIST: [issue(9), issue(5), issue(2, "octo")],
        detail(5): {"body": previous_body({"reverts": "ok"})},
        detail(9): {"body": big},
    }
    bin_dir = install_gh(tmp_path / "bin", laptop, served)

    target = prepare_post(GitHubReader("o/r"))

    assert target == PostTarget("o/r", 5, {"reverts": "ok"})
    calls = gh_argv(bin_dir)
    assert [call[3] for call in calls] == [LIST, detail(5)]
    assert all(call[:3] == ["api", "--method", "GET"] for call in calls)
    assert calls[1][4:] == ["--jq", "{body}"]


@pytest.mark.parametrize("failure", ["list", "detail", "allowance"])
def test_a_failed_target_lookup_never_opens_a_duplicate(
    tmp_path: Path,
    laptop: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
) -> None:
    h = merged_project(tmp_path)
    existing = {"number": 5, "user": {"login": ACTIONS_LOGIN}, "body": previous_body({})}
    served: dict[str, object] = {
        **responses(h),
        LIST: [existing],
        detail(5): {"body": previous_body({})},
        f"POST {ISSUES}": CREATED,
    }
    refusal = {"error": "gh: Server Error (HTTP 500)"}
    if failure == "list":
        served[LIST] = refusal
    elif failure == "detail":
        served[detail(5)] = refusal
    else:
        served[LIST] = {"error": "gh: API rate limit exceeded for 192.0.2.1. (HTTP 403)"}
        served["rate_limit"] = RESET

    assert post_main(h.path, laptop, served) == 2

    error = capsys.readouterr().err
    assert error.startswith("devctl metrics: cannot look up the metrics issue")
    assert ("it resets at 06:12 UTC" in error) == (failure == "allowance")
    assert error.endswith("; nothing was posted\n")
    bin_dir = h.path.parent / "bin"
    assert all(call[2] == "GET" for call in gh_argv(bin_dir))
    assert gh_bodies(bin_dir) == []
    assert not any(call[3] == "repos/o/r" for call in gh_argv(bin_dir))  # measurement never began


def test_the_job_summary_gets_the_markdown_report(tmp_path: Path) -> None:
    summary = tmp_path / "summary.md"
    summary.write_text("an earlier step\n")
    report = sample(OK, BREACHED)

    post(report, PostTarget("o/r", None, {}), Writes(), summary)

    assert summary.read_text() == "an earlier step\n" + render_markdown(report)
    post(report, PostTarget("o/r", None, {}), Writes(), None)  # without a summary file: no error


def test_a_job_summary_that_cannot_be_written_exits_2_before_any_write(
    tmp_path: Path, laptop: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "no-such-directory" / "summary.md"
    laptop.setenv("GITHUB_STEP_SUMMARY", str(summary))
    h = merged_project(tmp_path / "project")
    served: dict[str, object] = {**responses(h), LIST: [], f"POST {ISSUES}": CREATED}

    assert post_main(h.path, laptop, served) == 2

    assert capsys.readouterr().err == (
        f"devctl metrics: cannot append the report to the job summary {summary}: "
        "No such file or directory; nothing was posted\n"
    )
    bin_dir = h.path.parent / "bin"
    assert all(call[2] == "GET" for call in gh_argv(bin_dir))
    assert gh_bodies(bin_dir) == []


@pytest.mark.parametrize("phase", ["before", "walk"])
def test_exhaustion_after_target_lookup_posts_unknown_without_another_get(
    tmp_path: Path,
    laptop: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    phase: str,
) -> None:
    h = merged_project(tmp_path)
    if phase == "walk":
        for _ in range(8):
            h.push({})
        h.publish()
    read = responses(h)
    exhausted = "repos/o/r" if phase == "before" else [p for p in read if "/commits/" in p][5]
    existing = {"number": 5, "user": {"login": ACTIONS_LOGIN}, "body": previous_body({})}
    served: dict[str, object] = {
        **read,
        LIST: [existing],
        detail(5): {"body": previous_body({"revisions": "ok", "red_merges": "ok"})},
        exhausted: {"error": "gh: API rate limit exceeded for 192.0.2.1. (HTTP 403)"},
        "rate_limit": RESET,
        f"PATCH {detail(5)}": {"number": 5, "html_url": "https://github.com/o/r/issues/5"},
        f"POST {detail(5)}/comments": {"id": 1},
    }

    assert post_main(h.path, laptop, served) == 0

    bin_dir = h.path.parent / "bin"
    methods = [call[2] for call in gh_argv(bin_dir)]
    first_write = methods.index("PATCH")
    assert methods[first_write:] == ["PATCH", "POST"]  # nothing is read after the first write
    assert gh_argv(bin_dir)[first_write - 1][3] == "rate_limit"  # the single reset-time lookup
    body, comment = (str(sent["body"]) for sent in gh_bodies(bin_dir))
    rows = [line for line in body.splitlines() if line.startswith("| ")][2:]  # past the header
    reason = "unknown: GitHub API allowance used up; it resets at 06:12 UTC"
    assert len(rows) == 5
    assert all(reason in row for row in rows)
    assert json.loads(embedded(body))["metrics"] == [
        {"id": "revisions", "status": "unknown"},
        {"id": "reverts", "status": None},
        {"id": "red_merges", "status": "unknown"},
        {"id": "closed_unmerged", "status": None},
        {"id": "corrections", "status": None},
    ]
    assert "revisions: ok -> unknown (unknown: GitHub API allowance used up" in comment
    assert capsys.readouterr().out.splitlines()[0] == "https://github.com/o/r/issues/5"


def test_a_breach_exits_0_once_posted_and_a_failed_post_exits_2(
    tmp_path: Path, laptop: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    laptop.setenv("GITHUB_STEP_SUMMARY", str(summary))
    changes = [
        {"state": "CHANGES_REQUESTED", "commit_id": head, "submitted_at": "2026-10-01T00:00:00Z"}
        for head in ("A", "B")
    ]
    posted = merged_project(tmp_path / "posted")
    posted.owner.serve("repos/o/r/pulls/1/reviews?per_page=64&page=1", changes)
    served: dict[str, object] = {
        **responses(posted),
        LIST: [],
        f"POST {ISSUES}": CREATED,
        f"POST {detail(7)}/comments": {"id": 1},
    }

    assert post_main(posted.path, laptop, served) == 0

    out = capsys.readouterr().out.splitlines()
    assert out[0] == "https://github.com/o/r/issues/7"
    assert "revisions: none -> breached (2 per PR, at most 1.0)" in out
    sent = gh_bodies(posted.path.parent / "bin")
    assert [call[2:4] for call in gh_argv(posted.path.parent / "bin")][-2:] == [
        ["POST", ISSUES],
        ["POST", f"{detail(7)}/comments"],
    ]
    assert str(sent[0]["body"]).startswith(MARKER)
    assert str(sent[1]["body"]).count("breached") == 1
    assert summary.read_text().startswith("## rapid-ship metrics for o/r\n")

    refused = merged_project(tmp_path / "refused")
    refused.owner.serve("repos/o/r/pulls/1/reviews?per_page=64&page=1", changes)
    served = {
        **responses(refused),
        LIST: [],
        f"POST {ISSUES}": {"error": "gh: Resource not accessible by integration (HTTP 403)"},
    }

    assert post_main(refused.path, laptop, served) == 2

    error = capsys.readouterr().err
    assert error.startswith("devctl metrics: GitHub refused POST repos/o/r/issues")
    assert "issues: write" in error
    writes = [call for call in gh_argv(refused.path.parent / "bin") if call[2] != "GET"]
    assert len(writes) == 1  # a refused write is never retried, and no comment follows it


@pytest.mark.parametrize(
    ("report", "statuses"),
    [
        pytest.param(
            counted_issues(1_000),
            {"reverts": "ok", "closed_unmerged": "breached", "bugs": "breached"},
            id="1,000 counted issues",
        ),
        pytest.param(
            partly_reverted(1_500, 1_500),
            {"reverts": "breached", "closed_unmerged": "breached"},
            id="one revert of 1,500 files and 1,500 sections",
        ),
        pytest.param(
            unexplained("x" * 200_000),
            {"reverts": "ok", "closed_unmerged": "breached", "bugs": "unknown"},
            id="a reason of 200,000 characters",
        ),
    ],
)
def test_a_large_report_posts_a_body_and_a_comment_under_the_limit(
    report: Report, statuses: dict[str, str]
) -> None:
    writes = Writes()

    post(report, PostTarget("o/r", None, {}), writes, None)

    assert writes.requests == [("POST", ISSUES), ("POST", f"{ISSUES}/7/comments")]
    assert len(writes.body(0)) < LIMIT
    assert len(writes.body(1)) < LIMIT
    comment = json.loads(embedded(writes.body(0)))
    assert [entry["id"] for entry in comment["metrics"]] == list(statuses)
    target = prepare_post(reader_for({LIST: [projected(7)], detail(7): {"body": writes.body(0)}}))
    assert target.previous == statuses


def test_a_later_run_reads_the_statuses_from_a_large_body_and_comments_on_a_change() -> None:
    first = Writes(number=5)
    post(counted_issues(1_000), PostTarget("o/r", None, {}), first, None)
    assert len(first.body(0)) < LIMIT
    target = prepare_post(reader_for({LIST: [projected(5)], detail(5): {"body": first.body(0)}}))
    assert target.previous == {"reverts": "ok", "closed_unmerged": "breached", "bugs": "breached"}

    same = Writes()
    post(counted_issues(1_000), target, same, None)
    assert same.requests == [("PATCH", detail(5))]

    bugs = judge("bugs", "Bugs", "count", "repository", Measured(3), 5)
    changed = Writes()
    post(sample(OK, BREACHED, bugs), target, changed, None)
    assert changed.requests == [("PATCH", detail(5)), ("POST", f"{detail(5)}/comments")]
    assert changed.body(1) == (
        "Suggested threshold status changed:\n\n- bugs: breached -> ok (3, at most 5)"
    )


@pytest.mark.parametrize(
    ("report", "held"),
    [
        pytest.param(counted_issues(1_000), "1000 items", id="1,000 counted issues"),
        pytest.param(counted_issues(1), "1 item", id="1 counted issue"),
        pytest.param(with_unknown_items(), "4 items", id="2 counted and 2 unknown items"),
    ],
)
def test_the_body_says_how_many_items_it_leaves_out_and_where_the_report_is(
    tmp_path: Path, report: Report, held: str
) -> None:
    note = (
        f"The report holds {held} that this issue does not list; "
        "./devctl metrics --json prints the whole report."
    )
    summary = tmp_path / "summary.md"
    writes = Writes()

    post(report, PostTarget("o/r", None, {}), writes, summary)

    markdown = writes.body(0).partition("\n<!-- rapid-ship-metrics-json\n")[0]
    assert markdown.endswith(f"\n\n{note}\n")
    assert summary.read_text() == render_markdown(report)  # the summary lists no item either


def test_a_small_reports_body_is_the_marker_the_markdown_and_each_metrics_id_and_status() -> None:
    corrections = judge("corrections", "Corrections", "count", "ledger", Measured(9), None)
    report = sample(OK, BREACHED, UNKNOWN, corrections)  # none of them has an item
    writes = Writes()

    post(report, PostTarget("o/r", None, {}), writes, None)

    body = writes.body(0)
    opener = "<!-- rapid-ship-metrics-json"
    assert body == f"{MARKER}\n{render_markdown(report)}\n{opener}\n{embedded(body)}-->\n"
    assert json.loads(embedded(body)) == {
        "version": 1,
        "metrics": [
            {"id": "reverts", "status": "ok"},
            {"id": "closed_unmerged", "status": "breached"},
            {"id": "red_merges", "status": "unknown"},
            {"id": "corrections", "status": None},
        ],
    }


def test_the_json_comment_cannot_end_early() -> None:
    nasty = "--> <!-- rapid-ship-metrics-json\n--!> end"
    report = sample(
        judge(
            "red_merges",
            "Red merges",
            "count",
            "agent",
            Measured(0, unknown=1, items=({"pr": 1, "state": "unknown", "detail": nasty},)),
            1,
        ),
        metric("reverts", None, 1, reason="boom --> <b>x</b>"),
        metric("a-->b", 0, 1),  # no loader accepts this id, but post takes any report
    )
    writes = Writes()

    post(report, PostTarget("o/r", None, {}), writes, None)

    body = writes.body(0)
    raw = embedded(body)
    assert "\\u003e" in raw
    assert "-->" not in raw
    assert body.count("-->") == 2  # the marker's and the JSON comment's own
    assert json.loads(raw)["metrics"][2] == {"id": "a-->b", "status": "ok"}
    assert nasty not in body
    again = prepare_post(reader_for({LIST: [projected(5)], detail(5): {"body": body}}))
    assert again.previous == {"red_merges": "ok", "reverts": "unknown", "a-->b": "ok"}


def test_status_changes_name_each_difference_and_skip_unchanged_and_unthresholded() -> None:
    corrections = judge("corrections", "Corrections", "count", "ledger", Measured(9), None)
    report = sample(OK, BREACHED, UNKNOWN, corrections)

    assert status_changes({"reverts": "ok", "closed_unmerged": "ok"}, report) == [
        "closed_unmerged: ok -> breached (4, at most 3)",
        "red_merges: none -> unknown (0, 2 unknown, at most 1)",
    ]
    settled = {"reverts": "ok", "closed_unmerged": "breached", "red_merges": "unknown"}
    assert status_changes(settled, report) == []


def test_gh_write_sends_the_json_body_on_stdin_with_only_the_github_token(
    tmp_path: Path, laptop: pytest.MonkeyPatch
) -> None:
    bin_dir = install_gh(tmp_path / "bin", laptop, {f"POST {ISSUES}": CREATED})
    laptop.setenv("GH_TOKEN", "workflow-token")
    laptop.setenv("UNRELATED_SECRET", "x")

    assert gh_write("POST", ISSUES, {"title": "t", "body": "b"}) == CREATED

    assert gh_argv(bin_dir) == [["api", "--method", "POST", ISSUES, "--input", "-"]]
    assert gh_bodies(bin_dir) == [{"title": "t", "body": "b"}]
    env = json.loads((bin_dir / "gh.log").read_text())["env"]
    assert "GH_TOKEN" in env
    assert "UNRELATED_SECRET" not in env


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", ISSUES), ("PATCH", detail(5)), ("POST", f"{detail(5)}/comments")],
    ids=["create", "update", "comment"],
)
def test_a_refused_write_raises_with_the_status_and_the_fix(
    tmp_path: Path, laptop: pytest.MonkeyPatch, method: str, path: str
) -> None:
    refusal = {"error": "gh: Resource not accessible by integration (HTTP 403)"}
    install_gh(tmp_path / "bin", laptop, {f"{method} {path}": refusal})

    with pytest.raises(GitHubError) as raised:
        gh_write(method, path, {"body": "b"})

    assert str(raised.value) == (
        f"GitHub refused {method} {path}: gh: Resource not accessible by integration (HTTP 403); "
        "check that the workflow grants issues: write, then rerun it"
    )


@pytest.mark.parametrize(
    ("write", "method", "path", "tail", "sent"),
    [
        pytest.param("create", "POST", ISSUES, SIZE_TAIL, [ISSUES], id="create"),
        pytest.param("update", "PATCH", detail(5), SIZE_TAIL, [detail(5)], id="update"),
        pytest.param(
            "comment",
            "POST",
            f"{detail(5)}/comments",
            COMMENT_SIZE_TAIL,
            [detail(5), f"{detail(5)}/comments"],
            id="comment",
        ),
    ],
)
def test_a_422_on_a_write_says_the_body_may_be_too_large_and_exits_2(
    tmp_path: Path,
    laptop: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    write: str,
    method: str,
    path: str,
    tail: str,
    sent: list[str],
) -> None:
    summary = tmp_path / "summary.md"
    laptop.setenv("GITHUB_STEP_SUMMARY", str(summary))
    h = merged_project(tmp_path / "project")
    existing = {"number": 5, "user": {"login": ACTIONS_LOGIN}, "body": previous_body({})}
    served: dict[str, object] = {**responses(h), LIST: [] if write == "create" else [existing]}
    if write != "create":
        served[detail(5)] = {"body": previous_body({})}
    if write == "comment":
        served[f"PATCH {detail(5)}"] = {"number": 5, "html_url": "https://github.com/o/r/issues/5"}
    served[f"{method} {path}"] = SIZE_REFUSAL

    assert post_main(h.path, laptop, served) == 2

    assert capsys.readouterr().err == (
        f"devctl metrics: GitHub refused {method} {path}: gh: Validation Failed (HTTP 422){tail}"
    )
    assert summary.read_text().startswith("## rapid-ship metrics for o/r\n")
    writes = [call for call in gh_argv(h.path.parent / "bin") if call[2] != "GET"]
    assert [call[3] for call in writes] == sent  # a refused write is never retried


def test_a_rate_limited_patch_exits_2_and_the_job_summary_keeps_the_report(
    tmp_path: Path, laptop: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    laptop.setenv("GITHUB_STEP_SUMMARY", str(summary))
    h = merged_project(tmp_path / "project")
    existing = {"number": 5, "user": {"login": ACTIONS_LOGIN}, "body": previous_body({})}
    served: dict[str, object] = {
        **responses(h),
        LIST: [existing],
        detail(5): {"body": previous_body({})},
        f"PATCH {detail(5)}": {"error": "gh: API rate limit exceeded for 192.0.2.1. (HTTP 403)"},
    }

    assert post_main(h.path, laptop, served) == 2

    error = capsys.readouterr().err
    assert error.startswith(
        f"devctl metrics: GitHub refused PATCH {detail(5)}: gh: API rate limit exceeded"
    )
    assert error.endswith(
        "; the API allowance is used up, and the job summary holds this run's report: "
        "rerun the workflow after the allowance resets\n"
    )
    assert "issues: write" not in error
    assert summary.read_text().startswith("## rapid-ship metrics for o/r\n")
    writes = [call for call in gh_argv(h.path.parent / "bin") if call[2] != "GET"]
    assert len(writes) == 1  # the refused PATCH: no retry, and no comment after it


def test_a_rate_limited_comment_exits_2_and_a_rerun_posts_no_comment(
    tmp_path: Path, laptop: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = tmp_path / "summary.md"
    laptop.setenv("GITHUB_STEP_SUMMARY", str(summary))
    h = merged_project(tmp_path / "project")
    existing = {"number": 5, "user": {"login": ACTIONS_LOGIN}, "body": previous_body({})}
    comments = f"{detail(5)}/comments"
    served: dict[str, object] = {
        **responses(h),
        LIST: [existing],
        detail(5): {"body": previous_body({})},
        f"PATCH {detail(5)}": {"number": 5, "html_url": "https://github.com/o/r/issues/5"},
        f"POST {comments}": {"error": "gh: API rate limit exceeded for 192.0.2.1. (HTTP 403)"},
    }

    assert post_main(h.path, laptop, served) == 2

    error = capsys.readouterr().err
    assert error.startswith(f"devctl metrics: GitHub refused POST {comments}: gh: API rate limit")
    assert error.endswith(
        "; the API allowance is used up. The issue already holds this run's report, but its "
        "status-change comment was not posted, and a rerun does not post it again. "
        "The job summary holds this run's report too\n"
    )
    assert "issues: write" not in error
    assert summary.read_text().startswith("## rapid-ship metrics for o/r\n")
    bin_dir = h.path.parent / "bin"
    writes = [call for call in gh_argv(bin_dir) if call[2] != "GET"]
    assert [call[3] for call in writes] == [detail(5), comments]  # the comment is not retried
    left_in_issue = gh_bodies(bin_dir)[0]
    assert str(left_in_issue["body"]).startswith(MARKER)

    served[detail(5)] = left_in_issue
    del served[f"POST {comments}"]  # a rerun that comments finds no answer and exits 2
    calls = len(gh_argv(bin_dir))

    assert post_main(h.path, laptop, served) == 0
    assert [call[3] for call in gh_argv(bin_dir)[calls:] if call[2] != "GET"] == [detail(5)]


@pytest.mark.parametrize("message", ["gh: Bad Gateway (HTTP 502)", "gh: HTTP 502"])
def test_a_server_error_on_a_write_is_reported_as_uncertain_and_not_retried(
    tmp_path: Path, laptop: pytest.MonkeyPatch, message: str
) -> None:
    refusal = {"error": message}
    bin_dir = install_gh(tmp_path / "bin", laptop, {f"PATCH {detail(5)}": refusal})

    with pytest.raises(GitHubError, match="may have been applied") as raised:
        gh_write("PATCH", detail(5), {"body": "b"})

    assert str(raised.value).startswith(f"{message} for PATCH {detail(5)}")
    assert "issues: write" not in str(raised.value)
    assert len(gh_argv(bin_dir)) == 1


def test_a_bare_429_is_reported_as_a_rate_limit_and_not_retried(
    tmp_path: Path, laptop: pytest.MonkeyPatch
) -> None:
    refusal = {"error": "gh: HTTP 429"}
    bin_dir = install_gh(tmp_path / "bin", laptop, {f"PATCH {detail(5)}": refusal})

    with pytest.raises(GitHubError, match="the API allowance is used up") as raised:
        gh_write("PATCH", detail(5), {"body": "b"})

    assert "issues: write" not in str(raised.value)
    assert len(gh_argv(bin_dir)) == 1


def test_a_timed_out_write_is_reported_as_uncertain_and_not_retried(
    tmp_path: Path, laptop: pytest.MonkeyPatch, recorded_argv: list[list[str]]
) -> None:
    bin_dir = tmp_path / "bin"
    fake_tool(bin_dir, "gh", "import time\ntime.sleep(30)")
    laptop.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    # The calls are counted where gh_write starts a process, not from the stand-in's own log: an
    # executable written a moment ago can take hundreds of milliseconds to start.
    laptop.setattr(post_module, "WRITE_TIMEOUT_SECONDS", 0.3)

    with pytest.raises(GitHubError, match="may have been applied"):
        gh_write("POST", ISSUES, {"title": "t"})

    assert len(recorded_argv) == 1
