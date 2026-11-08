"""Offline: Revisions against recorded GitHub responses."""

from datetime import UTC, datetime

from devctl.metrics.github import GitHubReader
from devctl.metrics.revisions import revisions
from devctl.metrics.window import PullRequest, Window
from github_fakes import RecordedOwner


def sample_window(count: int = 1) -> Window:
    prs = tuple(
        PullRequest(n, "worker", datetime(2026, 10, 10, tzinfo=UTC), None, str(n), "", "")
        for n in range(1, count + 1)
    )
    return Window("main", "tip", 30, "worker", prs, prs, 0)


def review(state: str, head: str = "A", time: str = "2026-10-09T00:00:00Z") -> dict[str, object]:
    return {"state": state, "commit_id": head, "submitted_at": time}


def test_distinct_heads_count_once() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls/1/reviews?per_page=64&page=1": [review("CHANGES_REQUESTED")] * 3
            + [review("CHANGES_REQUESTED", "B")]
        }
    )
    result = revisions(GitHubReader("o/r", owner), sample_window())
    assert result.value == 2
    assert result.items == ({"pr": 1, "state": "counted", "revisions": 2},)


def test_a_dismissed_change_request_counts() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls/1/reviews?per_page=64&page=1": [review("DISMISSED")],
            "repos/o/r/issues/1/events?per_page=64&page=1": [
                {
                    "event": "review_dismissed",
                    "dismissed_review": {"state": "Changes_Requested", "commit_id": "A"},
                },
                {
                    "event": "review_dismissed",
                    "dismissed_review": {"state": "approved", "commit_id": "B"},
                },
            ],
        }
    )
    assert revisions(GitHubReader("o/r", owner), sample_window()).value == 1


def test_a_review_after_the_merge_is_ignored() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls/1/reviews?per_page=64&page=1": [
                review("CHANGES_REQUESTED", time="2026-10-11T00:00:00Z"),
                review("CHANGES_REQUESTED", "B", "2026-10-10T00:00:00Z"),
            ]
        }
    )
    assert revisions(GitHubReader("o/r", owner), sample_window()).value == 1


def test_approvals_and_comments_are_ignored() -> None:
    owner = RecordedOwner(
        {"repos/o/r/pulls/1/reviews?per_page=64&page=1": [review("APPROVED"), review("COMMENTED")]}
    )
    assert revisions(GitHubReader("o/r", owner), sample_window()).value == 0


def test_events_are_read_only_after_a_dismissed_review() -> None:
    owner = RecordedOwner({"repos/o/r/pulls/1/reviews?per_page=64&page=1": []})
    revisions(GitHubReader("o/r", owner), sample_window())
    assert owner.paths == ["repos/o/r/pulls/1/reviews?per_page=64&page=1"]


def test_the_value_is_the_mean_and_items_list_the_most_revised_first() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls/1/reviews?per_page=64&page=1": [review("CHANGES_REQUESTED")],
            "repos/o/r/pulls/2/reviews?per_page=64&page=1": [
                review("CHANGES_REQUESTED", "A"),
                review("CHANGES_REQUESTED", "B"),
            ],
            "repos/o/r/pulls/3/reviews?per_page=64&page=1": [],
        }
    )
    result = revisions(GitHubReader("o/r", owner), sample_window(3))
    assert result.value == 1
    assert [item["pr"] for item in result.items] == [2, 1]


def test_reviews_and_events_are_paged() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls/1/reviews?per_page=64&page=1": [review("DISMISSED")] * 64,
            "repos/o/r/pulls/1/reviews?per_page=64&page=2": [review("CHANGES_REQUESTED", "B")],
            "repos/o/r/issues/1/events?per_page=64&page=1": [{"event": "closed"}] * 64,
            "repos/o/r/issues/1/events?per_page=64&page=2": [
                {
                    "event": "review_dismissed",
                    "dismissed_review": {"state": "changes_requested", "commit_id": "A"},
                }
            ],
        }
    )
    assert revisions(GitHubReader("o/r", owner), sample_window()).value == 2
