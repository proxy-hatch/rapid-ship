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
_FIRST_UTC = datetime.min.replace(tzinfo=UTC)
_LAST_UTC = datetime.max.replace(tzinfo=UTC)
_Called = tuple[object, Exception | None]  # a call's result, or the Exception it raised


def _call(function: Callable[[], object]) -> _Called:
    """What function returns, or the Exception it raised.

    Project code is arbitrary, so its errors must become unknown values, not end the run.
    """
    try:
        return function(), None
    except Exception as error:  # noqa: BLE001  # rs-exception: EX-31
        return None, error


def _written(text: str) -> str:
    """text with each character that UTF-8 cannot write, such as a lone surrogate, escaped."""
    return text.encode("utf-8", "backslashreplace").decode("utf-8")


def _described(error: Exception) -> str:
    """The type of error and the first line of its message, or only the type if str(error) fails.

    A character of the message that UTF-8 cannot write stays in it as its escape.
    """
    name = type(error).__name__
    message, _ = _call(lambda: _written(first_line(str(error))))
    return f"{name}: {message}" if isinstance(message, str) and message else name


def _text(value: object) -> bool:
    """A str that UTF-8 can write."""
    return isinstance(value, str) and value == _written(value)


def _aware(value: object) -> bool:
    return isinstance(value, datetime) and value.tzinfo is not None


def _whole(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _number(value: object) -> bool:
    return _whole(value) or isinstance(value, float)


def _pr_number(value: object) -> bool:
    """A number that names a PR: above 0, and within the 15 digits that every JSON reader keeps."""
    return _whole(value) and 0 < cast("int", value) < 10**15


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
    if not _text(title) or not title:
        return f"id = {shown}: title = {title!r}: use a non-empty string that can be written"
    return None


def _checked(metric: object, seen: set[str]) -> str | None:
    """The problem with metric, or None.

    Project code defines the attributes that are checked, so reading one can raise.
    """
    problem, error = _call(lambda: _metric_problem(metric, seen))
    if error is not None:
        return f"{type(metric).__name__} cannot be checked: {_described(error)}"
    return problem if isinstance(problem, str) else None


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
    problems = [_checked(metric, seen) for metric in found]
    if any(problems):
        raise MetricsSettingsError(tuple(f"{_PREFIX}: {p}" for p in problems if p is not None))
    return tuple(found)


def _time_problem(record: str, when: datetime) -> str | None:
    if not _aware(when):
        return f"{record} with a time without a time zone"
    if not _FIRST_UTC <= when <= _LAST_UTC:
        return f"{record} with a time that UTC cannot hold"
    return None


def _incident_problem(item: Incident) -> str | None:
    if not _text(item.url):
        return "an incident with a url that is not text that can be written"
    if problem := _time_problem("an incident", item.time):
        return problem
    cause = item.cause
    if isinstance(cause, str) and not _text(cause):
        return "an incident with a cause that is not text that can be written"
    if cause is not None and not _text(cause) and not _pr_number(cause):
        return "an incident with a cause that is not a PR number or a commit"
    return None


def _item_problem(item: object, incident_metric: bool) -> str | None:
    if isinstance(item, Incident):
        return _incident_problem(item)
    if isinstance(item, Item) and not incident_metric:
        if not _text(item.label):
            return "an item with a label that is not text that can be written"
        if item.url is not None and not _text(item.url):
            return "an item with a url that is not text that can be written"
        return None if item.time is None else _time_problem("an item", item.time)
    allowed = "Incident" if incident_metric else "Item or Incident"
    return f"an item of type {type(item).__name__}: use {allowed} records"


def _result_problem(metric: Metric, result: MetricResult) -> str | None:
    value = result.value
    if value is None:
        if not isinstance(result.reason, str) or not result.reason:
            return "no value and no reason"
        if not _text(result.reason):
            return "a reason that is not text that can be written"
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


def _converted(metric: Metric, result: object) -> Measured:
    if not isinstance(result, MetricResult):
        return Measured(None, f"measure returned {type(result).__name__}, not a MetricResult")
    problem = _result_problem(metric, result)
    if problem is not None:
        return Measured(None, f"measure returned {problem}")
    reason = result.reason if result.value is None else None
    return Measured(result.value, reason, items=tuple(_record(item) for item in result.items))


def _measured(metric: Metric, result: object, error: Exception | None, timed_out: str) -> Measured:
    if isinstance(error, AllowanceUsedUp):
        return Measured(None, error.reason())
    if isinstance(error, MeasurementClosed):
        return Measured(None, timed_out)
    if error is not None:
        return Measured(None, _described(error))
    # Validation cannot foresee every value that fails to convert; such a result is unknown too.
    converted, failure = _call(lambda: _converted(metric, result))
    if failure is not None:
        why = _described(failure)
        return Measured(None, f"measure returned a result that cannot be reported: {why}")
    return cast("Measured", converted)


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
