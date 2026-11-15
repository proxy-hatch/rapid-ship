"""Offline: Closed unmerged against recorded GitHub responses."""

from datetime import UTC, datetime

import pytest

from devctl.metrics.closed_unmerged import closed_unmerged
from devctl.metrics.github import GitHubError, GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.window import PullRequest, Window
from github_fakes import RecordedOwner

WORKER = "o-worker[bot]"
REVIEWER = "o-reviewer[bot]"
APPS = frozenset({WORKER, REVIEWER})
SINCE = datetime(2026, 10, 10, tzinfo=UTC)
REOPENED = {"event": "reopened", "actor": {"login": "person"}}


def closed_path(page: int = 1) -> str:
    return f"repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=64&page={page}"


def events_path(number: int, page: int = 1) -> str:
    return f"repos/o/r/issues/{number}/events?per_page=64&page={page}"


def window(agent: str | None = WORKER) -> Window:
    merged = PullRequest(1, WORKER, SINCE, SINCE, "1", "", "")
    return Window("main", "tip", 30, agent, (merged,), (merged,), 0)


def pull(
    number: int,
    *,
    author: str = WORKER,
    closed: str = "2026-10-12T00:00:00Z",
    updated: str | None = None,
    merged: str | None = None,
) -> dict[str, object]:
    return {
        "number": number,
        "user": {"login": author},
        "merged_at": merged,
        "closed_at": closed,
        "updated_at": updated or closed,
    }


def closed_by(login: str | None) -> dict[str, object]:
    return {"event": "closed", "actor": {"login": login}}


def measure(owner: RecordedOwner, *, identity: bool = True) -> Measured:
    reader = GitHubReader("o/r", owner)
    if identity:
        return closed_unmerged(reader, window(), SINCE, APPS)
    return closed_unmerged(reader, window(None), SINCE, frozenset())


def counted(*numbers: int) -> tuple[dict[str, object], ...]:
    return tuple({"pr": number, "state": "counted"} for number in numbers)


def test_a_pr_a_person_closed_counts() -> None:
    owner = RecordedOwner({closed_path(): [pull(5)], events_path(5): [closed_by("person")]})
    result = measure(owner)
    assert result.value == 1
    assert result.unknown == 0
    assert result.items == counted(5)


def test_a_pr_an_app_closed_does_not_count_with_agent_identity() -> None:
    owner = RecordedOwner(
        {
            closed_path(): [pull(7), pull(6), pull(5)],
            events_path(5): [closed_by(WORKER)],
            events_path(6): [closed_by(REVIEWER)],
            events_path(7): [closed_by("person")],
        }
    )
    result = measure(owner)
    assert result.value == 1
    assert result.items == counted(7)


def test_a_pr_closed_reopened_and_merged_does_not_count() -> None:
    merged = pull(5, merged="2026-10-13T00:00:00Z", updated="2026-10-13T00:00:00Z")
    owner = RecordedOwner({closed_path(): [merged], events_path(5): [closed_by("person")]})
    result = measure(owner)
    assert result.value == 0
    assert result.items == ()
    assert owner.paths == [closed_path()]


def test_the_last_closed_event_decides() -> None:
    owner = RecordedOwner(
        {
            closed_path(): [pull(6), pull(5)],
            events_path(5): [closed_by(WORKER), REOPENED, closed_by("person")],
            events_path(6): [closed_by("person"), REOPENED, closed_by(WORKER)],
        }
    )
    assert measure(owner).items == counted(5)


def test_a_pr_closed_before_the_span_does_not_count() -> None:
    owner = RecordedOwner(
        {
            closed_path(): [
                pull(5, closed="2026-10-09T23:59:59Z", updated="2026-10-11T00:00:00Z"),
                pull(6, closed="2026-10-10T00:00:00Z"),
            ],
            events_path(6): [closed_by("person")],
        }
    )
    result = measure(owner)
    assert result.items == counted(6)
    assert owner.paths == [closed_path(), events_path(6)]


def test_without_agent_identity_every_closed_pr_counts_and_no_events_are_read() -> None:
    owner = RecordedOwner({closed_path(): [pull(6, author="person"), pull(5)]})
    result = measure(owner, identity=False)
    assert result.value == 2
    assert result.items == counted(6, 5)
    assert owner.paths == [closed_path()]


def test_a_pr_of_another_author_is_outside_the_agent_population() -> None:
    owner = RecordedOwner({closed_path(): [pull(5, author="person")]})
    result = measure(owner)
    assert result.value == 0
    assert owner.paths == [closed_path()]


def test_paging_stops_at_the_first_pr_updated_before_the_span() -> None:
    page = [pull(number) for number in range(100, 36, -1)]
    page[-1] = pull(37, closed="2026-10-01T00:00:00Z", updated="2026-10-09T00:00:00Z")
    owner = RecordedOwner({closed_path(): page})
    result = measure(owner, identity=False)
    assert result.value == 63
    assert owner.paths == [closed_path()]


def test_paging_goes_on_while_prs_were_updated_in_the_span() -> None:
    owner = RecordedOwner(
        {
            closed_path(): [pull(number) for number in range(100, 36, -1)],
            closed_path(2): [pull(36)],
        }
    )
    result = measure(owner, identity=False)
    assert result.value == 65
    assert owner.paths == [closed_path(), closed_path(2)]


def test_a_pr_that_two_pages_both_list_counts_once() -> None:
    first = [pull(number) for number in range(100, 36, -1)]
    owner = RecordedOwner({closed_path(): first, closed_path(2): [first[-1], pull(36)]})
    result = measure(owner, identity=False)
    assert result.value == 65
    assert result.items == counted(*range(100, 35, -1))
    assert owner.paths == [closed_path(), closed_path(2)]


def test_events_are_paged_to_the_last_closed_event() -> None:
    labeled = {"event": "labeled", "actor": {"login": "person"}}
    owner = RecordedOwner(
        {
            closed_path(): [pull(5)],
            events_path(5): [closed_by("person"), *[labeled] * 63],
            events_path(5, 2): [closed_by(WORKER)],
        }
    )
    assert measure(owner).value == 0


@pytest.mark.parametrize(
    "events",
    [
        [],
        [{"event": "labeled", "actor": {"login": "person"}}],
        [{"event": "closed", "actor": None}],
        [{"event": "closed", "actor": {"login": None}}],
        [closed_by("person"), {"event": "closed", "actor": None}],
    ],
)
def test_a_pr_whose_closer_no_event_names_is_an_unknown_item(
    events: list[dict[str, object]],
) -> None:
    owner = RecordedOwner({closed_path(): [pull(5)], events_path(5): events})
    result = measure(owner)
    assert result.value == 0
    assert result.unknown == 1
    assert result.items == (
        {
            "pr": 5,
            "state": "unknown",
            "detail": "its last closed event names no actor, or it has no closed event",
        },
    )


def test_an_unreadable_events_response_is_an_error_not_a_zero() -> None:
    owner = RecordedOwner({closed_path(): [pull(5)]})
    with pytest.raises(GitHubError):
        measure(owner)


def test_items_list_the_newest_pr_first() -> None:
    owner = RecordedOwner({closed_path(): [pull(5), pull(9), pull(7)]})
    assert measure(owner, identity=False).items == counted(9, 7, 5)
