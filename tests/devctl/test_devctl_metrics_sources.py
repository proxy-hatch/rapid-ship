"""Offline: the issues and deployments sources against recorded GitHub responses and a local
repository.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pytest

from devctl.metrics.github import GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.sources import count_deployments, count_issues
from devctl.repo import Repo
from github_fakes import RecordedOwner
from metrics_fakes import MergedHistory, report_json, served_project

SINCE = datetime(2026, 10, 1, tzinfo=UTC)
UNTIL = datetime(2026, 10, 16, tzinfo=UTC)
ISSUES = (
    "repos/o/r/issues?labels=needs%20triage&state=all&sort=created&direction=desc"
    "&per_page=64&page=1"
)
Row = tuple[int, str, str, Sequence[str]]  # id, commit, created, statuses newest first


def issue(number: int, created: str, *, pr: bool = False) -> dict[str, object]:
    return {
        "number": number,
        "created_at": created,
        "html_url": f"https://example.invalid/issues/{number}",
        "pull_request": {"url": "https://example.invalid/pulls"} if pr else None,
    }


def counted_issue(number: int, created: str) -> dict[str, object]:
    return {
        "label": f"#{number}",
        "url": f"https://example.invalid/issues/{number}",
        "time": created,
        "state": "counted",
    }


def labelled(owner: RecordedOwner) -> Measured:
    return count_issues(GitHubReader("o/r", owner), "needs triage", SINCE, UNTIL)


def test_issues_count_only_labelled_issues_opened_in_the_span() -> None:
    older = [issue(n, "2026-09-01T00:00:00Z") for n in range(60)]
    page = [
        issue(9, "2026-10-20T00:00:00Z"),
        issue(8, "2026-10-10T00:00:00Z"),
        issue(7, "2026-10-01T00:00:00Z"),
        issue(6, "2026-09-30T23:59:59Z"),
        *older,
    ]
    owner = RecordedOwner({ISSUES: page})
    assert labelled(owner) == Measured(
        2,
        items=(
            counted_issue(8, "2026-10-10T00:00:00Z"),
            counted_issue(7, "2026-10-01T00:00:00Z"),
        ),
    )
    assert owner.paths == [ISSUES]


def test_pull_requests_are_not_issues() -> None:
    owner = RecordedOwner(
        {
            ISSUES: [
                issue(5, "2026-10-09T00:00:00Z", pr=True),
                issue(4, "2026-10-08T00:00:00Z"),
                issue(3, "2026-10-07T00:00:00Z", pr=True),
            ]
        }
    )
    assert labelled(owner) == Measured(1, items=(counted_issue(4, "2026-10-08T00:00:00Z"),))


def history(tmp_path: Path) -> tuple[MergedHistory, Repo, tuple[str, str, str]]:
    """A repository of three commits, oldest first."""
    h = MergedHistory(tmp_path)
    first, second, third = (h.push({"file": str(n)}) for n in range(3))
    return h, Repo.discover(h.path), (first, second, third)


def serve(h: MergedHistory, rows: Sequence[Row], page: int = 1) -> None:
    """Serve one page of deployments to production, newest first, and each one's statuses."""
    path = f"repos/o/r/deployments?environment=production&per_page=64&page={page}"
    h.owner.serve(path, [{"id": i, "sha": sha, "created_at": at} for i, sha, at, _ in rows])
    for i, _, at, states in rows:
        statuses = [
            {"id": 1000 * i - n, "state": state, "created_at": f"{at[:11]}00:00:{59 - n:02d}Z"}
            for n, state in enumerate(states)
        ]
        h.owner.serve(f"repos/o/r/deployments/{i}/statuses?per_page=64&page=1", statuses)


def deployed(
    h: MergedHistory,
    repo: Repo,
    count: Literal["rollbacks", "failures"] = "rollbacks",
) -> Measured:
    return count_deployments(repo, GitHubReader("o/r", h.owner), "production", count, SINCE, UNTIL)


def item(i: int, sha: str, created: str, state: str, detail: str) -> dict[str, object]:
    return {
        "label": f"deployment {i}: {sha[:7]}",
        "url": None,
        "time": created,
        "state": state,
        "detail": detail,
    }


# GitHub adds an inactive status to a successful deployment once a later one succeeds
@pytest.mark.parametrize("settled", [["success"], ["inactive", "success"]])
def test_a_deployment_of_an_older_commit_is_a_rollback(tmp_path: Path, settled: list[str]) -> None:
    h, repo, (c1, c2, c3) = history(tmp_path)
    serve(
        h,
        [
            (3, c1, "2026-10-10T00:00:00Z", ["success"]),
            (2, c3, "2026-10-05T00:00:00Z", settled),
            (1, c2, "2026-09-01T00:00:00Z", settled),
        ],
    )
    assert deployed(h, repo) == Measured(
        1,
        items=(
            item(3, c1, "2026-10-10T00:00:00Z", "counted", f"older than {c3[:7]} (deployment 2)"),
        ),
    )


def test_redeploying_the_same_commit_is_not_a_rollback(tmp_path: Path) -> None:
    h, repo, (_, c2, _) = history(tmp_path)
    serve(
        h,
        [
            (2, c2, "2026-10-05T00:00:00Z", ["success"]),
            (1, c2, "2026-09-01T00:00:00Z", ["success"]),
        ],
    )
    assert deployed(h, repo) == Measured(0)


def test_failures_count_the_last_status(tmp_path: Path) -> None:
    h, repo, (c1, c2, c3) = history(tmp_path)
    serve(
        h,
        [
            (5, c3, "2026-10-12T00:00:00Z", ["error", "in_progress"]),
            (4, c3, "2026-10-10T00:00:00Z", ["success", "failure"]),
            (3, c2, "2026-10-05T00:00:00Z", ["failure", "success"]),
            (2, c1, "2026-10-02T00:00:00Z", []),
            (1, c1, "2026-09-01T00:00:00Z", ["failure"]),
        ],
    )
    assert deployed(h, repo, "failures") == Measured(
        2,
        items=(
            item(5, c3, "2026-10-12T00:00:00Z", "counted", "last status error"),
            item(3, c2, "2026-10-05T00:00:00Z", "counted", "last status failure"),
        ),
    )
    assert not any("deployments/1/statuses" in path for path in h.owner.paths)


@pytest.mark.parametrize("missing", ["current", "previous"])
def test_a_deployment_outside_local_history_is_unknown(tmp_path: Path, missing: str) -> None:
    h, repo, (c1, _, c3) = history(tmp_path)
    absent = "f" * 40
    current, previous = (absent, c3) if missing == "current" else (c1, absent)
    serve(
        h,
        [
            (2, current, "2026-10-05T00:00:00Z", ["success"]),
            (1, previous, "2026-09-01T00:00:00Z", ["success"]),
        ],
    )
    assert deployed(h, repo) == Measured(
        0,
        unknown=1,
        items=(
            item(
                2,
                current,
                "2026-10-05T00:00:00Z",
                "unknown",
                "commit fffffff is not in the local history: run git fetch origin",
            ),
        ),
    )


@pytest.mark.parametrize("settled", [["success"], ["inactive", "success"]])
def test_the_previous_success_can_be_before_the_span_on_a_later_page(
    tmp_path: Path, settled: list[str]
) -> None:
    h, repo, (c1, c2, c3) = history(tmp_path)
    failed: list[Row] = [(n, c2, "2026-09-01T00:00:00Z", ["failure"]) for n in range(99, 36, -1)]
    serve(h, [(100, c1, "2026-10-10T00:00:00Z", ["success"]), *failed])
    serve(h, [(36, c3, "2026-08-01T00:00:00Z", settled)], page=2)
    assert deployed(h, repo) == Measured(
        1,
        items=(
            item(
                100, c1, "2026-10-10T00:00:00Z", "counted", f"older than {c3[:7]} (deployment 36)"
            ),
        ),
    )
    assert len([path for path in h.owner.paths if "/statuses" in path]) == 65


@pytest.mark.parametrize(
    "source",
    ['source = "issues"\nlabel = "alarm"', 'source = "deployments"\nenvironment = "production"'],
)
def test_a_source_github_refuses_is_unknown_not_exit_2(tmp_path: Path, source: str) -> None:
    h = served_project(tmp_path, f'[[metric]]\nid = "alarms"\ntitle = "Alarms"\n{source}\n')
    metrics = {m["id"]: m for m in report_json(h)["metrics"]}
    assert metrics["alarms"]["value"] is None
    assert "GitHub refused repos/o/r/" in metrics["alarms"]["reason"]
    assert "HTTP 404" in metrics["alarms"]["reason"]
    assert metrics["red_merges"]["value"] == 0
