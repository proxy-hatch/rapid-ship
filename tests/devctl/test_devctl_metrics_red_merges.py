"""Offline: Red merges against recorded GitHub responses."""

import pytest

from devctl.doctor_items import OwnerReadError
from devctl.metrics.github import GitHubError, GitHubReader
from devctl.metrics.red_merges import red_merges
from github_fakes import RecordedOwner
from test_devctl_metrics_revisions import sample_window


def run(conclusion: str, number: int = 1, attempt: int = 1) -> dict[str, object]:
    return {"id": number, "run_number": number, "run_attempt": attempt, "conclusion": conclusion}


def path(sha: str = "1", page: int = 1) -> str:
    return (
        f"repos/o/r/actions/workflows/devctl-check.yml/runs?head_sha={sha}"
        f"&event=push&per_page=64&page={page}"
    )


def test_failure_and_timed_out_are_red_and_success_green() -> None:
    owner = RecordedOwner(
        {path("1"): [run("failure")], path("2"): [run("timed_out")], path("3"): [run("success")]}
    )
    result = red_merges(GitHubReader("o/r", owner), sample_window(3))
    assert result.value == 2
    assert result.unknown == 0
    assert result.items == ({"pr": 1, "state": "counted"}, {"pr": 2, "state": "counted"})


def test_a_cancelled_or_missing_run_is_unknown() -> None:
    owner = RecordedOwner({path("1"): [run("cancelled")], path("2"): []})
    result = red_merges(GitHubReader("o/r", owner), sample_window(2))
    assert result.value == 0
    assert result.unknown == 2
    assert [item["detail"] for item in result.items] == ["push run cancelled", "no push run"]


def test_a_passing_rerun_does_not_clear_a_failed_first_attempt() -> None:
    owner = RecordedOwner(
        {
            path(): [run("success", attempt=2)],
            "repos/o/r/actions/runs/1/attempts/1": {"conclusion": "failure"},
        }
    )
    assert red_merges(GitHubReader("o/r", owner), sample_window()).value == 1


def test_the_earliest_push_run_decides() -> None:
    owner = RecordedOwner(
        {path(): [run("success", n) for n in range(3, 67)], path(page=2): [run("failure", 1)]}
    )
    assert red_merges(GitHubReader("o/r", owner), sample_window()).value == 1


def test_a_missing_workflow_leaves_every_pr_unknown() -> None:
    owner = RecordedOwner({path(): OwnerReadError(404, "not found")})
    result = red_merges(GitHubReader("o/r", owner), sample_window(2))
    assert result.unknown == 2
    assert all(item["detail"] == "no devctl-check.yml workflow" for item in result.items)


@pytest.mark.parametrize("status", [401, 404, 500])
def test_attempt_errors_propagate(status: int) -> None:
    owner = RecordedOwner(
        {
            path(): [run("success", attempt=2)],
            "repos/o/r/actions/runs/1/attempts/1": OwnerReadError(status, "error"),
        }
    )
    with pytest.raises(GitHubError) as caught:
        red_merges(GitHubReader("o/r", owner), sample_window())
    assert caught.value.status == status
