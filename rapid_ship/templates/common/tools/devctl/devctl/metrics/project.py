"""Code metrics: the project's own Metric classes, run under a time limit on a scoped reader."""

from __future__ import annotations

import math
import re
import threading
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import devctl_project
from devctl.metrics.api import Incident, IncidentMetric, Item, Metric, MetricContext, MetricResult
from devctl.metrics.github import AllowanceUsedUp, GitHubReader, MeasurementClosed
from devctl.metrics.model import Measured
from devctl.metrics.settings import BASIC_METRICS, MetricsSettingsError
from devctl.process import first_line

MEASURE_SECONDS = 60.0
_PREFIX = "devctl_project.metrics()"
_ID = re.compile(r"[a-z][a-z0-9_]*")
_Called = tuple[object, Exception | None]  # a call's result, or the Exception it raised


def _call(function: Callable[[], object]) -> _Called:
    """What function returns, or the Exception it raised.

    Project code is arbitrary, so its errors must become unknown values, not end the run.
    """
    try:
        return function(), None
    except Exception as error:  # noqa: BLE001  # rs-exception: EX-31
        return None, error


def _described(error: Exception) -> str:
    name = type(error).__name__
    message = first_line(str(error))
    return f"{name}: {message}" if message else name


def _text(value: object) -> bool:
    return isinstance(value, str)


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None


def _whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _number(value: object) -> bool:
    return _whole(value) or isinstance(value, float)


def _finite(value: object) -> bool:
    try:
        return _number(value) and math.isfinite(float(cast("float", value)))
    except (OverflowError, TypeError, ValueError):  # an int beyond float's range raises
        return False


def _metric_problem(metric: object, seen: set[str]) -> str | None:
    if not isinstance(metric, Metric):
        return f"returned a {type(metric).__name__}, not a Metric"
    name = getattr(metric, "id", None)
    shown = f'"{name}"' if _text(name) else repr(name)
    if not isinstance(name, str) or not _ID.fullmatch(name):
        return f"id = {shown}: use lowercase letters, digits and _, starting with a letter"
    if name in BASIC_METRICS:
        return f"id = {shown}: {name} is a basic metric; choose another id"
    if name in seen:
        return f"id = {shown}: another metric already defines {name}; choose another id"
    seen.add(name)
    title = getattr(metric, "title", None)
    if not isinstance(title, str) or not title:
        return f"id = {shown}: title = {title!r}: use a non-empty string"
    return None


def project_metrics() -> tuple[Metric, ...]:
    """The metrics that devctl_project.metrics() returns, or none when it has no such function."""
    function = getattr(devctl_project, "metrics", None)
    if function is None:
        return ()
    found, error = _call(function)
    if error is not None:
        raise MetricsSettingsError((f"{_PREFIX}: {_described(error)}",)) from error
    if not isinstance(found, list | tuple):
        raise MetricsSettingsError(
            (f"{_PREFIX}: returned {type(found).__name__}, not a list of Metric",)
        )
    seen: set[str] = set()
    problems = [_metric_problem(metric, seen) for metric in found]
    if any(problems):
        raise MetricsSettingsError(tuple(f"{_PREFIX}: {p}" for p in problems if p is not None))
    return tuple(found)


def _incident_problem(item: Incident) -> str | None:
    if not _text(item.url):
        return "an incident with a url that is not text"
    if not _aware(item.time):
        return "an incident with a time without a time zone"
    cause = item.cause
    if cause is not None and not _text(cause) and not _whole(cause):
        return "an incident with a cause that is not a PR number or a commit"
    return None


def _item_problem(item: object, incident_metric: bool) -> str | None:
    if isinstance(item, Incident):
        return _incident_problem(item)
    if isinstance(item, Item) and not incident_metric:
        if not _text(item.label):
            return "an item with a label that is not text"
        if item.url is not None and not _text(item.url):
            return "an item with a url that is not text"
        if item.time is not None and not _aware(item.time):
            return "an item with a time without a time zone"
        return None
    allowed = "Incident" if incident_metric else "Item or Incident"
    return f"an item of type {type(item).__name__}: use {allowed} records"


def _result_problem(metric: Metric, result: MetricResult) -> str | None:
    value = result.value
    if value is None:
        if not _text(result.reason) or not result.reason:
            return "no value and no reason"
    elif not _finite(value) or value < 0:
        return f"value of type {type(value).__name__}: use a finite number of at least 0"
    items: object = result.items  # project code can return what the annotation forbids
    if not isinstance(items, tuple | list):
        return f"items of type {type(items).__name__}: use a tuple of records"
    for item in items:
        problem = _item_problem(item, isinstance(metric, IncidentMetric))
        if problem is not None:
            return problem
    return None


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _record(item: Item | Incident) -> dict[str, object]:
    if isinstance(item, Incident):
        return {"url": item.url, "time": _utc(item.time), "cause": item.cause, "state": "counted"}
    when = None if item.time is None else _utc(item.time)
    return {"label": item.label, "url": item.url, "time": when, "state": "counted"}


def _measured(metric: Metric, result: object, error: Exception | None, timed_out: str) -> Measured:
    if isinstance(error, AllowanceUsedUp):
        return Measured(None, error.reason())
    if isinstance(error, MeasurementClosed):
        return Measured(None, timed_out)
    if error is not None:
        return Measured(None, _described(error))
    if not isinstance(result, MetricResult):
        return Measured(None, f"measure returned {type(result).__name__}, not a MetricResult")
    problem = _result_problem(metric, result)
    if problem is not None:
        return Measured(None, f"measure returned {problem}")
    reason = result.reason if result.value is None else None
    return Measured(result.value, reason, items=tuple(_record(item) for item in result.items))


def _run(metric: Metric, context: MetricContext, outcome: list[_Called]) -> None:
    outcome[0] = _call(lambda: metric.measure(context))


def measure(
    metric: Metric,
    context: MetricContext,
    reader: GitHubReader,
    timeout: float = MEASURE_SECONDS,
) -> Measured:
    """Run metric on a daemon thread that reads GitHub only through a scope of reader.

    The scope closes on every exit, so a thread that outlives timeout starts no later request.
    Python cannot stop that thread's other work. A metric that fails, runs past timeout or
    returns a bad result is unknown with the reason. Once the allowance is used up, the metric
    is not run.
    """
    exhausted = reader.exhausted
    if exhausted is not None:
        return Measured(None, exhausted.reason())
    deadline = time.monotonic() + timeout
    getter = reader.measurement_get(deadline)
    outcome: list[_Called] = [(None, None)]  # still so if the thread ends on a BaseException
    thread = threading.Thread(
        target=_run, args=(metric, replace(context, get=getter), outcome), daemon=True
    )
    try:
        thread.start()
        thread.join(max(0.0, deadline - time.monotonic()))
    finally:
        getter.close()
    timed_out = f"measure ran longer than {timeout:g} seconds"
    if thread.is_alive():
        return Measured(None, timed_out)
    return _measured(metric, *outcome[0], timed_out)
