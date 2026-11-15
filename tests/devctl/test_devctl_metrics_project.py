"""Offline: code metrics with monkeypatched devctl_project.metrics."""

from __future__ import annotations

import inspect
import math
import threading
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

import devctl_project
from devctl.cli import main
from devctl.doctor_items import OwnerGet, OwnerReadError
from devctl.metrics.api import Incident, Item, Metric, MetricContext, MetricResult
from devctl.metrics.github import AllowanceUsedUp, GitHubReader, MeasurementClosed
from devctl.metrics.model import Measured
from devctl.metrics.project import MEASURE_SECONDS, measure, project_metrics
from devctl.metrics.settings import MetricsSettingsError
from github_fakes import RecordedOwner
from metrics_fakes import (
    ALLOWANCE,
    RESET,
    WAIT,
    Gate,
    GatedOwner,
    IncidentProbe,
    Probe,
    block_gh,
    report_json,
    served_project,
    use_metrics,
)

SINCE = datetime(2026, 10, 1, tzinfo=UTC)
UNTIL = datetime(2026, 10, 16, tzinfo=UTC)
NAIVE = datetime.fromisoformat("2026-10-02T00:00:00")
TIMED_OUT = "measure ran longer than 0.1 seconds"
LIMITED = {"repos/o/r/limited": OwnerReadError(403, "API rate limit exceeded"), "rate_limit": RESET}


def run(metric: Metric, reader: GitHubReader | None = None, timeout: float = WAIT) -> Measured:
    reader = reader or GitHubReader("o/r", RecordedOwner({}))
    context = MetricContext("o/r", SINCE, UNTIL, (1,), reader.get)
    return measure(metric, context, reader, timeout)


def read(path: str) -> Callable[[MetricContext], MetricResult]:
    return lambda context: MetricResult(cast("float", context.get(path)))


def attempt(
    path: str, outcomes: list[object], go: threading.Event | None = None
) -> Callable[[MetricContext], MetricResult]:
    """A metric body that waits for go, then reads path and records what that did."""

    def body(context: MetricContext) -> MetricResult:
        if go is not None:
            assert go.wait(WAIT)
        try:
            outcomes.append(context.get(path))
        except (AllowanceUsedUp, MeasurementClosed) as error:
            outcomes.append(error)
        return MetricResult(9)

    return body


def bad(value: object = 1, items: object = ()) -> MetricResult:
    """A result that breaks the types devctl_project is annotated with."""
    return MetricResult(cast("float", value), items=cast("tuple[Item, ...]", items))


class Untitled(Metric):
    id = "untitled"

    def measure(self, context: MetricContext) -> MetricResult:
        return MetricResult(1)


def raises() -> list[Metric]:
    raise RuntimeError("no metrics today")


def steady(metric_id: str) -> Probe:
    return Probe(lambda _: MetricResult(1), metric_id)


LIMITS = (0.5, 1.0, 2.0)  # a stalled machine moves a timing test on to the next limit
Parked = tuple[GatedOwner, Gate, GitHubReader, Probe, list[object]]


def park(served: Mapping[str, object], gated: str, *paths: str) -> Parked:
    """Time out a metric that visits paths while its request for gated is in flight.

    A stall can delay that request past the deadline; the next limit then starts a fresh run.
    """
    outcomes: list[object] = []

    def visits(context: MetricContext) -> MetricResult:
        for path in paths:
            attempt(path, outcomes)(context)
        return MetricResult(9)

    for limit in LIMITS:
        outcomes.clear()
        owner = GatedOwner(served)
        gate = owner.gate(gated)
        reader = GitHubReader("o/r", owner)
        metric = Probe(visits)
        late = Measured(None, f"measure ran longer than {limit:g} seconds")
        measured = run(metric, reader, limit)
        if gate.entered.is_set():
            assert measured == late
            return owner, gate, reader, metric, outcomes
        gate.release.set()
        metric.join()
    pytest.fail(f"the request for {gated} was never in flight before the deadline")


def test_a_code_metric_returns_a_value() -> None:
    seen = datetime(2026, 10, 2, 3, 4, 5, tzinfo=UTC)
    items = (Item("rebuilt", "https://example.invalid/1", seen), Item("bare"))
    assert run(Probe(lambda _: MetricResult(2, items=items))) == Measured(
        2,
        items=(
            {
                "label": "rebuilt",
                "url": "https://example.invalid/1",
                "time": "2026-10-02T03:04:05Z",
                "state": "counted",
            },
            {"label": "bare", "url": None, "time": None, "state": "counted"},
        ),
    )


def test_a_code_metric_returns_unknown_with_a_reason() -> None:
    unknown = MetricResult(None, "the tool is down")
    assert run(Probe(lambda _: unknown)) == Measured(None, "the tool is down")


def test_a_raising_metric_is_unknown_and_the_rest_stands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(_: MetricContext) -> MetricResult:
        raise RuntimeError("boom\nsecond line")

    use_metrics(monkeypatch, Probe(explode, "broken"), steady("steady"))
    metrics = {m["id"]: m for m in report_json(served_project(tmp_path))["metrics"]}
    assert (metrics["broken"]["value"], metrics["broken"]["reason"]) == (None, "RuntimeError: boom")
    assert metrics["steady"]["value"] == 1
    assert metrics["red_merges"]["value"] == 0


def test_a_code_metric_that_github_refuses_is_unknown() -> None:
    measured = run(Probe(read("/repos/o/r/missing")))
    assert measured.value is None
    assert measured.reason is not None
    assert measured.reason.startswith("GitHubError: GitHub refused repos/o/r/missing (HTTP 404)")


def test_the_default_timeout_is_sixty_seconds() -> None:
    assert MEASURE_SECONDS == 60.0
    assert inspect.signature(measure).parameters["timeout"].default == 60.0


def test_a_metric_past_its_timeout_is_unknown() -> None:
    go = threading.Event()
    hung = Probe(attempt("/repos/o/r/x", [], go))
    assert run(hung, timeout=0.1) == Measured(None, TIMED_OUT)
    go.set()
    hung.join()


@pytest.mark.parametrize(
    ("incident", "returned", "reason"),
    [
        (False, None, "NoneType, not a MetricResult"),
        (False, MetricResult(-1), "of type int: use a finite number of at least 0"),
        (False, MetricResult(float("nan")), "of type float: use a finite number of at least 0"),
        (False, MetricResult(math.inf), "of type float: use a finite number of at least 0"),
        (False, bad(True), "of type bool: use a finite number of at least 0"),
        (False, bad("3"), "of type str: use a finite number of at least 0"),
        (False, MetricResult(None), "no value and no reason"),
        (False, MetricResult(None, ""), "no value and no reason"),
        (False, bad(1, None), "items of type NoneType"),
        (False, MetricResult(10**400), "use a finite number of at least 0"),
        (False, MetricResult(10**5000), "of type int: use a finite number of at least 0"),
        (False, bad(1, ("x",)), "an item of type str"),
        (False, bad(1, (Item("a", time=NAIVE),)), "a time without a time zone"),
        (False, bad(1, (Item(cast("str", 7)),)), "a label that is not text"),
        (False, bad(1, (Incident("u", SINCE, cast("int", SINCE)),)), "a cause that is not"),
        (True, MetricResult(1, items=(Item("a"),)), "an item of type Item"),
    ],
)
def test_a_bad_result_is_unknown(incident: bool, returned: object, reason: str) -> None:
    probe = (IncidentProbe if incident else Probe)(lambda _: cast("MetricResult", returned))
    measured = run(probe)
    assert measured.value is None
    assert measured.reason is not None
    assert reason in measured.reason
    assert measured.items == ()


def test_an_incident_metric_returns_records_with_and_without_a_cause() -> None:
    at = datetime(2026, 10, 3, 4, 5, 6, tzinfo=UTC)
    causes = ((1, 42), (2, "a" * 40), (3, None))
    found = tuple(Incident(f"https://example.invalid/i/{n}", at, cause) for n, cause in causes)
    assert run(IncidentProbe(lambda _: MetricResult(3, items=found))) == Measured(
        3,
        items=tuple(
            {
                "url": f"https://example.invalid/i/{n}",
                "time": "2026-10-03T04:05:06Z",
                "cause": cause,
                "state": "counted",
            }
            for n, cause in causes
        ),
    )


def test_an_incident_metric_is_marked_incident_when_empty_and_when_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_metrics(
        monkeypatch,
        IncidentProbe(lambda _: MetricResult(0), "outages"),
        IncidentProbe(lambda _: MetricResult(None, "the pager is unreachable"), "pages"),
        Probe(lambda _: MetricResult(0), "probes"),
    )
    metrics = {m["id"]: m for m in report_json(served_project(tmp_path))["metrics"]}
    assert [
        (metrics[i]["kind"], metrics[i]["value"], metrics[i]["population"])
        for i in ("outages", "pages", "probes")
    ] == [
        ("incident", 0, "repository"),
        ("incident", None, "repository"),
        ("count", 0, "repository"),
    ]


BROKEN: dict[str, tuple[Callable[[], object], str]] = {
    "raises": (raises, "RuntimeError: no metrics today"),
    "repeats an id": (
        lambda: [steady("same"), steady("same")],
        'id = "same": another metric already defines same',
    ),
    "invalid id": (lambda: [steady("Not-An-ID")], 'id = "Not-An-ID": use lowercase letters'),
    "basic metric": (lambda: [steady("reverts")], 'id = "reverts": reverts is a basic metric'),
    "no title": (lambda: [Untitled()], 'id = "untitled": title = None: use a non-empty string'),
    "not a metric": (lambda: ["probes"], "str, not a Metric"),
    "not a list": (lambda: None, "NoneType, not a list"),
}


@pytest.mark.parametrize("name", list(BROKEN))
def test_metrics_that_raises_or_repeats_an_id_exits_2(
    name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    build, fragment = BROKEN[name]
    monkeypatch.setattr(devctl_project, "metrics", build, raising=False)
    monkeypatch.chdir(served_project(tmp_path).path)
    block_gh(tmp_path / "bin", monkeypatch)
    assert main(["metrics"]) == 2
    error = capsys.readouterr().err
    assert error.startswith("devctl metrics: devctl_project.metrics(): ")
    assert fragment in error


def test_a_project_without_metrics_has_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(devctl_project, "metrics", raising=False)
    assert project_metrics() == ()


def test_project_metrics_come_from_devctl_project_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first, second = steady("first"), steady("second")
    use_metrics(monkeypatch, first, second)
    assert project_metrics() == (first, second)


def test_a_threshold_may_name_a_code_metric(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = served_project(tmp_path, "[thresholds]\nprobes = 1\n")
    monkeypatch.delattr(devctl_project, "metrics", raising=False)
    with pytest.raises(MetricsSettingsError, match="probes names no metric"):
        report_json(h)
    use_metrics(monkeypatch, Probe(lambda _: MetricResult(2)))
    probes = report_json(h)["metrics"][-1]
    assert (probes["id"], probes["threshold"], probes["status"]) == ("probes", 1, "breached")


def test_exhaustion_latches_code_metric_reads_too() -> None:
    owner = RecordedOwner({**LIMITED, "repos/o/r/late": 1})
    reader = GitHubReader("o/r", owner)
    go = threading.Event()
    outcomes: list[object] = []
    stale = Probe(attempt("/repos/o/r/late", outcomes, go))
    assert run(stale, reader, 0.1) == Measured(None, TIMED_OUT)
    first = run(Probe(read("/repos/o/r/limited")), reader)
    later = steady("later")
    skipped = run(later, reader)
    go.set()
    stale.join()
    assert first == skipped == Measured(None, ALLOWANCE)
    assert later.threads == []
    assert [type(outcome) for outcome in outcomes] == [MeasurementClosed]
    assert owner.paths == ["repos/o/r/limited", "rate_limit"]


def test_a_timed_out_metric_cannot_resume_reads_with_healthy_allowance() -> None:
    owner = RecordedOwner({"repos/o/r/late": 1, "repos/o/r/other": 2})
    reader = GitHubReader("o/r", owner)
    go = threading.Event()
    outcomes: list[object] = []
    stale = Probe(attempt("/repos/o/r/late", outcomes, go))
    assert run(stale, reader, 0.1) == Measured(None, TIMED_OUT)
    assert run(Probe(read("/repos/o/r/other")), reader) == Measured(2)
    go.set()
    stale.join()
    assert [type(outcome) for outcome in outcomes] == [MeasurementClosed]
    assert owner.paths == ["repos/o/r/other"]


@pytest.mark.parametrize("ending", ["value", "error", "invalid"])
def test_a_completed_metric_cannot_reuse_its_getter(ending: str) -> None:
    owner = RecordedOwner({"repos/o/r/x": 1})
    reader = GitHubReader("o/r", owner)
    kept: list[OwnerGet] = []

    def finish(context: MetricContext) -> MetricResult:
        kept.append(context.get)
        if ending == "error":
            raise RuntimeError("boom")
        return cast("MetricResult", MetricResult(1) if ending == "value" else None)

    run(Probe(finish), reader)
    with pytest.raises(MeasurementClosed):
        kept[0]("/repos/o/r/x")
    assert owner.paths == []


def test_a_queued_measurement_read_rechecks_its_deadline() -> None:
    owner = GatedOwner({"repos/o/r/first": 1, "repos/o/r/second": 2})
    gate = owner.gate("repos/o/r/first")
    reader = GitHubReader("o/r", owner)
    holder = threading.Thread(target=reader.get, args=("first",))
    holder.start()
    assert gate.entered.wait(WAIT)
    outcomes: list[object] = []
    queued = Probe(attempt("/repos/o/r/second", outcomes))
    assert run(queued, reader, 0.2) == Measured(None, "measure ran longer than 0.2 seconds")
    gate.release.set()
    holder.join(WAIT)
    queued.join()
    assert not holder.is_alive()
    assert [type(outcome) for outcome in outcomes] == [MeasurementClosed]
    assert owner.paths == ["repos/o/r/first"]


def test_an_in_flight_read_finishes_without_reopening_a_timed_out_scope() -> None:
    served = {"repos/o/r/slow": 1, "repos/o/r/second": 2, "repos/o/r/later": 3}
    owner, gate, reader, slow, outcomes = park(
        served, "repos/o/r/slow", "/repos/o/r/slow", "/repos/o/r/second"
    )
    gate.release.set()
    slow.join()
    assert run(Probe(read("/repos/o/r/later")), reader) == Measured(3)
    assert outcomes[0] == 1
    assert isinstance(outcomes[1], MeasurementClosed)
    assert owner.paths == ["repos/o/r/slow", "repos/o/r/later"]


def test_an_in_flight_read_that_exhausts_the_allowance_still_latches_it() -> None:
    served = {"repos/o/r/slow": OwnerReadError(403, "rate limit"), "rate_limit": RESET}
    owner, gate, reader, slow, outcomes = park(served, "repos/o/r/slow", "/repos/o/r/slow")
    gate.release.set()
    slow.join()
    later = steady("later")
    assert run(later, reader) == Measured(None, ALLOWANCE)
    assert [type(outcome) for outcome in outcomes] == [AllowanceUsedUp]
    assert later.threads == []
    assert owner.paths == ["repos/o/r/slow", "rate_limit"]


def test_metrics_measured_around_an_exhaustion_report_the_same_reason() -> None:
    served = {**LIMITED, "repos/o/r/other": 1}
    _, gate, reader, stale, _ = park(served, "rate_limit", "/repos/o/r/limited")

    def release_then_read(context: MetricContext) -> MetricResult:
        gate.release.set()
        return MetricResult(cast("float", context.get("/repos/o/r/other")))

    during = run(Probe(release_then_read), reader)
    gate.release.set()
    stale.join()
    assert during == run(steady("later"), reader) == Measured(None, ALLOWANCE)


def test_a_read_refused_after_the_deadline_reports_the_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = [100.0]
    monkeypatch.setattr("devctl.metrics.project.time.monotonic", lambda: now[0])

    def late_read(context: MetricContext) -> MetricResult:
        now[0] += 10  # the deadline passes before the metric's first request
        return MetricResult(cast("float", context.get("/repos/o/r/x")))

    probe = Probe(late_read)
    assert run(probe, timeout=1.0) == Measured(None, "measure ran longer than 1 seconds")
    probe.join()


def test_a_stall_before_the_join_shortens_the_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Offline: a simulated clock moves 0.9 seconds before the join, leaving 0.1 to wait."""
    readings = iter([100.0, 100.9])  # the scope's deadline, then the join, 0.9 seconds later
    monkeypatch.setattr("devctl.metrics.project.time.monotonic", lambda: next(readings, 100.9))
    finish = threading.Event()

    def slow(_: MetricContext) -> MetricResult:
        finish.wait(0.4)  # makes no read, and ends 0.4 seconds after it starts
        return MetricResult(1)

    probe = Probe(slow)
    assert run(probe, timeout=1.0) == Measured(None, "measure ran longer than 1 seconds")
    finish.set()
    probe.join()
