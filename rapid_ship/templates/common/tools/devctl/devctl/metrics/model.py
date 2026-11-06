"""devctl metrics: data models and status evaluation."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

Population = Literal["agent", "all", "ledger", "repository"]
Kind = Literal["count", "incident"]
ThresholdStatus = Literal["ok", "breached", "unknown"]
NEEDS_IDENTITY = "needs Agent identity"


@dataclass(frozen=True)
class Measured:
    value: float | None  # None: the whole metric is unknown
    reason: str | None = None  # why value is None
    unknown: int = 0  # unknown parts
    complete: bool = True  # False: value is a lower bound, as with PRs not gardened yet
    items: tuple[Mapping[str, object], ...] = ()  # JSON-ready; each has "state"
    extra: Mapping[str, object] = field(default_factory=dict)  # by_rung, repeats, not_gardened


@dataclass(frozen=True)
class MetricReport:
    metric_id: str
    title: str
    kind: Kind
    population: Population
    measured: Measured
    threshold: float | None
    status: ThresholdStatus | Literal["needs Agent identity"] | None  # None: no threshold


def threshold_status(measured: Measured, threshold: float) -> ThresholdStatus:
    if measured.value is None:
        return "unknown"
    if measured.value > threshold:
        return "breached"
    if measured.value + measured.unknown <= threshold and measured.complete:
        return "ok"
    return "unknown"


def judge(
    metric_id: str,
    title: str,
    kind: Kind,
    population: Population,
    measured: Measured,
    threshold: float | None,
) -> MetricReport:
    if threshold is None:
        status: ThresholdStatus | Literal["needs Agent identity"] | None = None
    elif measured.reason == NEEDS_IDENTITY:
        status = NEEDS_IDENTITY
    else:
        status = threshold_status(measured, threshold)
    return MetricReport(
        metric_id=metric_id,
        title=title,
        kind=kind,
        population=population,
        measured=measured,
        threshold=threshold,
        status=status,
    )
