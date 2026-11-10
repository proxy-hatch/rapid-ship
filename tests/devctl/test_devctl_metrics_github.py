"""Offline: the metrics reader against a recorded owner_get."""

from __future__ import annotations

import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from devctl.doctor_items import OwnerReadError, gh_get
from devctl.metrics.github import (
    AllowanceUsedUp,
    GitHubError,
    GitHubReader,
    MeasurementClosed,
)
from github_fakes import RecordedOwner
from metrics_fakes import fake_gh

PROJECTION = (
    "[.[] | {number, user: {login: .user.login}, merged_at, closed_at, updated_at, "
    "merge_commit_sha, body, html_url}]"
)
LIST_PROJECTION = PROJECTION.replace(", body", "")


def test_empty_suffix_reads_the_repository_without_a_trailing_slash() -> None:
    owner = RecordedOwner({"repos/o/r": {"default_branch": "main"}})
    reader = GitHubReader("o/r", owner)

    assert reader.get("", jq="{default_branch}") == {"default_branch": "main"}
    assert owner.paths == ["repos/o/r"]


def test_pages_reads_until_a_short_page() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls?per_page=64&page=1": [{"number": n} for n in range(64)],
            "repos/o/r/pulls?per_page=64&page=2": [{"number": n} for n in range(64, 67)],
        }
    )
    reader = GitHubReader("o/r", owner)
    assert [p["number"] for p in reader.pages("pulls", jq=LIST_PROJECTION)] == list(range(67))
    assert reader.requests == 2
    assert set(owner.filters.values()) == {LIST_PROJECTION}


def test_pages_stops_before_the_item_until_selects() -> None:
    owner = RecordedOwner(
        {
            "repos/o/r/pulls?state=closed&per_page=64&page=1": [
                {"number": 1},
                {"number": 2},
                {"number": 3},
            ]
        }
    )
    reader = GitHubReader("o/r", owner)
    assert list(
        reader.pages("pulls?state=closed", jq=LIST_PROJECTION, until=lambda p: p["number"] == 2)
    ) == [{"number": 1}]
    assert reader.requests == 1


def test_projected_page_overflow_reduces_size_without_losing_or_repeating_items() -> None:
    calls: list[str] = []
    rows = [{"number": n, "body": "x" * (200 if n < 64 else 40000)} for n in range(135)]

    def get(path: str, jq: str | None = None) -> object:
        assert jq == PROJECTION
        calls.append(path)
        query = parse_qs(urlsplit(path).query)
        size, page = int(query["per_page"][0]), int(query["page"][0])
        result = rows[(page - 1) * size : page * size]
        if len(json.dumps(result)) > 1048576:
            raise OwnerReadError(None, "gh api output exceeded 1048576 bytes")
        return result

    result = list(
        GitHubReader("o/r", get).pages(
            "pulls",
            jq=PROJECTION,
            until=lambda p: p["number"] == 130,
        )
    )
    assert [p["number"] for p in result] == list(range(130))
    assert [p.rsplit("?", 1)[1] for p in calls] == [
        "per_page=64&page=1",
        "per_page=64&page=2",
        "per_page=32&page=3",
        "per_page=16&page=5",
        "per_page=16&page=6",
        "per_page=16&page=7",
        "per_page=16&page=8",
        "per_page=16&page=9",
    ]


def test_a_single_projected_item_overflow_names_the_path_and_fix() -> None:
    owner = RecordedOwner(
        {
            f"repos/o/r/pulls?per_page={size}&page=1": OwnerReadError(
                None, "gh api output exceeded 1048576 bytes"
            )
            for size in (64, 32, 16, 8, 4, 2, 1)
        }
    )
    with pytest.raises(GitHubError, match=r"pulls.*narrow.*projection"):
        list(GitHubReader("o/r", owner).pages("pulls", jq=PROJECTION))
    assert len(owner.paths) == 7


@pytest.mark.parametrize("status", [403, 429, 500])
def test_page_overflow_does_not_retry_an_allowance_or_other_error(status: int) -> None:
    owner = RecordedOwner(
        {"repos/o/r/pulls?per_page=64&page=1": OwnerReadError(status, "RATE LIMIT exceeded")}
    )
    with pytest.raises(AllowanceUsedUp if status != 500 else GitHubError):
        list(GitHubReader("o/r", owner).pages("pulls", jq=PROJECTION))
    assert len(owner.paths) == (2 if status != 500 else 1)


def test_the_allowance_stops_every_later_read() -> None:
    reset = datetime(2026, 10, 16, 6, 12, tzinfo=UTC)
    owner = RecordedOwner(
        {
            "repos/o/r/x": OwnerReadError(403, "API rate limit exceeded"),
            "rate_limit": {"resources": {"core": {"reset": reset.timestamp()}}},
        }
    )
    reader = GitHubReader("o/r", owner)
    with pytest.raises(AllowanceUsedUp) as first:
        reader.get("x")
    assert first.value.reset == reset
    assert first.value.reason() == "GitHub API allowance used up; it resets at 06:12 UTC"
    with pytest.raises(AllowanceUsedUp) as later:
        reader.get("other")
    assert later.value is first.value
    assert owner.paths == ["repos/o/r/x", "rate_limit"]
    assert reader.requests == 2


def test_a_429_is_the_allowance_too() -> None:
    owner = RecordedOwner({"repos/o/r/x": OwnerReadError(429, "Rate Limit exceeded")})
    with pytest.raises(AllowanceUsedUp):
        GitHubReader("o/r", owner).get("x")


def test_without_a_reset_time_the_reason_says_so() -> None:
    owner = RecordedOwner({"repos/o/r/x": OwnerReadError(403, "rate limit")})
    with pytest.raises(AllowanceUsedUp) as error:
        GitHubReader("o/r", owner).get("x")
    assert error.value.reset is None
    assert error.value.reason().endswith("; its reset time could not be read")


@pytest.mark.parametrize(
    ("status", "message", "fix"),
    [
        (None, "gh could not start", "install gh"),
        (None, "gh api timed out", "check connectivity and rerun"),
        (None, "gh api printed no JSON", "inspect the response"),
        (None, "gh api output exceeded 1048576 bytes", "narrow"),
        (401, "Bad credentials", "check gh auth status"),
        (500, "server error", "HTTP 500"),
    ],
)
def test_other_errors_name_the_path_and_the_fix(
    status: int | None,
    message: str,
    fix: str,
) -> None:
    owner = RecordedOwner({"repos/o/r/x": OwnerReadError(status, message)})
    with pytest.raises(GitHubError) as error:
        GitHubReader("o/r", owner).get("x")
    assert error.value.status == status
    assert "repos/o/r/x" in str(error.value)
    assert fix in str(error.value)
    assert ("install gh" in str(error.value)) == (message == "gh could not start")


def test_list_projection_happens_before_the_output_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = [{"number": n, "body": "x" * 20000} for n in range(64)]
    fake_gh(tmp_path, {"repos/o/r/pulls": rows})
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(OwnerReadError, match="output exceeded"):
        gh_get("repos/o/r/pulls")
    result = GitHubReader("o/r", gh_get).get("pulls", jq=LIST_PROJECTION)
    assert isinstance(result, list)
    assert len(result) == 64
    assert all("body" not in row for row in result)


@pytest.mark.parametrize(
    "projection",
    [
        PROJECTION,
        LIST_PROJECTION,
        "[.[] | {id, state, commit_id, submitted_at}]",
        "[.[] | {id, event, created_at, actor: {login: .actor.login}, dismissed_review}]",
        "[.workflow_runs[] | {id, run_number, run_attempt, created_at, conclusion}]",
        "[.[] | {number, user: {login: .user.login}, state, created_at, updated_at, "
        "html_url, pull_request}]",
        "[.[] | {number, user: {login: .user.login}, html_url, pull_request, "
        'has_marker: ((.body // "") | startswith("<!-- rapid-ship-metrics -->"))}]',
        "[.[] | {id, sha, created_at, environment, statuses_url}]",
        "[.[] | {id, state, created_at, target_url}]",
    ],
)
def test_list_filters_keep_cardinality_and_stop_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    projection: str,
) -> None:
    rows = [
        {
            "id": n,
            "number": n,
            "updated_at": "time",
            "pull_request": None,
            "body": "<!-- rapid-ship-metrics -->hello",
        }
        for n in range(67)
    ]
    served: dict[str, object] = {}
    for page, batch in enumerate((rows[:64], rows[64:]), 1):
        served[f"repos/o/r/items?per_page=64&page={page}"] = (
            {"workflow_runs": batch} if "workflow_runs" in projection else batch
        )
    fake_gh(tmp_path, served)
    monkeypatch.setenv("PATH", str(tmp_path))
    result = list(GitHubReader("o/r", gh_get).pages("items", jq=projection))
    assert len(result) == 67
    key = "number" if "{number," in projection else "id"
    assert [row[key] for row in result] == list(range(67))
    if "pull_request" in projection:
        assert result[0]["pull_request"] is None
    if "has_marker" in projection:
        assert result[0]["has_marker"] is True
        assert "body" not in result[0]


def test_scoped_close_and_absolute_paths() -> None:
    owner = RecordedOwner({"rate_limit": 7})
    scope = GitHubReader("o/r", owner).measurement_get(time.monotonic() + 30)
    assert scope("/rate_limit") == 7
    scope.close()
    scope.close()
    with pytest.raises(MeasurementClosed):
        scope("rate_limit")
    assert owner.paths == ["rate_limit"]


@pytest.mark.parametrize(("close", "exhaust"), [(True, False), (False, False), (True, True)])
def test_close_is_immediate_and_queued_admission_rechecks_scope(
    monkeypatch: pytest.MonkeyPatch,
    close: bool,
    exhaust: bool,
) -> None:
    entered, release, queued, closed = (threading.Event() for _ in range(4))
    calls: list[str] = []
    results: list[object] = []
    now = [10.0]
    monkeypatch.setattr("devctl.metrics.github.time.monotonic", lambda: now[0])

    def get(path: str, jq: str | None = None) -> object:
        calls.append(path)
        return blocked_reply(path, entered, release, exhaust)

    reader = GitHubReader("o/r", get)
    monkeypatch.setattr(reader, "_serialization", AdmissionLock(queued))
    scope = reader.measurement_get(20)

    def invoke(path: str) -> None:
        try:
            results.append(scope(path))
        except (AllowanceUsedUp, MeasurementClosed) as error:
            results.append(error)

    first = threading.Thread(target=invoke, args=("first",))
    second = threading.Thread(target=invoke, args=("second",), name="queued")

    def finish_scope() -> None:
        scope.close()
        closed.set()

    closer = threading.Thread(target=finish_scope)
    first.start()
    assert entered.wait(5)
    second.start()
    assert queued.wait(5)
    try:
        if close:
            closer.start()
            assert closed.wait(5)
        else:
            now[0] = 21
    finally:
        release.set()
        first.join(5)
        second.join(5)
        if close:
            closer.join(5)
    assert not first.is_alive()
    assert not second.is_alive()
    assert any(isinstance(result, MeasurementClosed) for result in results)
    assert any(
        isinstance(result, AllowanceUsedUp) if exhaust else result == 42 for result in results
    )
    assert calls == (["first", "rate_limit"] if exhaust else ["first"])
    if exhaust:
        with pytest.raises(AllowanceUsedUp):
            reader.get("later")
        fresh = reader.measurement_get(100)
        with pytest.raises(AllowanceUsedUp):
            fresh("later")
        assert reader.requests == 2


def blocked_reply(
    path: str,
    entered: threading.Event,
    release: threading.Event,
    exhaust: bool,
) -> object:
    if path == "rate_limit":
        return {"resources": {"core": {"reset": 0}}}
    entered.set()
    assert release.wait(5)
    if exhaust:
        raise OwnerReadError(403, "rate limit")
    return 42


class AdmissionLock:
    """Signal the queued thread at lock acquisition, before the occupied lock releases."""

    def __init__(self, queued: threading.Event) -> None:
        self._lock = threading.Lock()
        self._queued = queued

    def __enter__(self) -> None:
        if threading.current_thread().name == "queued":
            self._queued.set()
        self._lock.acquire()

    def __exit__(self, *_exc: object) -> None:
        self._lock.release()
