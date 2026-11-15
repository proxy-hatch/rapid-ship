"""The types that a project's metrics() imports to define a metric."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from devctl.doctor_items import OwnerGet


@dataclass(frozen=True)
class Item:
    """One thing that a count found."""

    label: str
    url: str | None = None
    time: datetime | None = None  # needs a time zone


@dataclass(frozen=True)
class Incident:
    """Something that users saw go wrong."""

    url: str
    time: datetime  # needs a time zone
    cause: int | str | None = None  # a PR number, or a commit's full SHA


@dataclass(frozen=True)
class MetricResult:
    value: float | None  # a finite number of at least 0, or None when the metric is unknown
    reason: str | None = None  # required when value is None
    items: tuple[Item | Incident, ...] = ()


@dataclass(frozen=True)
class MetricContext:
    repository: str  # "owner/name"
    since: datetime  # the span: from the merge of the window's oldest PR to the report
    until: datetime
    prs: tuple[int, ...]  # the window's PR numbers, newest first
    get: OwnerGet  # GET a full API path, usable only while measure runs


class Metric(ABC):
    id: str  # lowercase letters, digits and _, starting with a letter; unique among metrics
    title: str

    @abstractmethod
    def measure(self, context: MetricContext) -> MetricResult: ...


class IncidentMetric(Metric):
    """A metric whose items are Incident records; devctl marks it incident whatever it returns."""
