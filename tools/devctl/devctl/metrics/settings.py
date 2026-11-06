"""devctl metrics: .rapid-ship/metrics.toml loader and types."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from devctl.metrics._order import Problems
from devctl.settings import SettingsError

METRICS = ".rapid-ship/metrics.toml"
GATE = ".rapid-ship/gate.toml"
BASIC_METRICS = (
    "revisions",
    "reverts",
    "red_merges",
    "closed_unmerged",
    "corrections",
)

_ID_RE = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class IssuesSource:
    label: str


@dataclass(frozen=True)
class DeploymentsSource:
    environment: str
    count: Literal["rollbacks", "failures"] = "rollbacks"


@dataclass(frozen=True)
class SettingsMetric:
    metric_id: str
    title: str
    source: IssuesSource | DeploymentsSource


@dataclass(frozen=True)
class MetricsSettings:
    window: int
    thresholds: Mapping[str, float]  # metric ID -> upper limit
    metrics: tuple[SettingsMetric, ...]  # in file order


class MetricsSettingsError(SettingsError):  # str() joins problems with newlines
    problems: tuple[str, ...]

    def __init__(self, problems: tuple[str, ...]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


def gate_note(root: Path) -> str | None:
    if (root / GATE).is_file():
        return (
            f"{GATE}: devctl no longer reads it; delete it, and carry any threshold"
            f" worth keeping into {METRICS}"
        )
    return None


def _collect_valid_settings_ids(
    raw_metric_list: object, code_metric_ids: Collection[str]
) -> list[str]:
    valid_ids: list[str] = []
    seen: set[str] = set()
    if not isinstance(raw_metric_list, list):
        return valid_ids
    for item in raw_metric_list:
        if not isinstance(item, dict):
            continue
        metric_id = item.get("id")
        if (
            isinstance(metric_id, str)
            and _ID_RE.fullmatch(metric_id)
            and metric_id not in BASIC_METRICS
            and metric_id not in seen
            and metric_id not in code_metric_ids
        ):
            valid_ids.append(metric_id)
        if isinstance(metric_id, str):
            seen.add(metric_id)
    return valid_ids


def _validate_window(val: object, problems: list[str]) -> None:
    if isinstance(val, bool) or not isinstance(val, int) or val < 1:
        problems.append(f"metrics.toml: window = {val}: use an integer of at least 1")


def _validate_thresholds(
    val: object, known_ids: Sequence[str], problems: Problems
) -> dict[str, float]:
    parsed: dict[str, float] = {}
    if not isinstance(val, dict):
        problems.append("metrics.toml: thresholds: expected a table")
        return parsed
    for t_key, t_val in val.items():
        problems.at(("thresholds", t_key))
        if t_key not in known_ids:
            problems.append(
                f"metrics.toml [thresholds] {t_key} = {t_val}: {t_key} names no metric; "
                f"use one of {', '.join(known_ids)}"
            )
        elif isinstance(t_val, bool) or not isinstance(t_val, (int, float)) or not (t_val >= 0):
            problems.append(
                f"metrics.toml [thresholds] {t_key} = {t_val}: use a number of at least 0"
            )
        else:
            parsed[t_key] = t_val
    return parsed


def _validate_metric_id_field(
    v: object,
    where: str,
    seen_ids: set[str],
    code_metric_ids: Collection[str],
    problems: list[str],
) -> None:
    if not isinstance(v, str):
        problems.append(f"{where}: id: use a string")
        return
    if not _ID_RE.fullmatch(v):
        problems.append(
            f'{where}: id = "{v}": use lowercase letters, digits and _, starting with a letter'
        )
    elif v in BASIC_METRICS:
        problems.append(f'{where}: id = "{v}": {v} is a basic metric; choose another id')
    elif v in seen_ids:
        problems.append(
            f'{where}: id = "{v}": another metric already defines {v}; choose another id'
        )
    elif v in code_metric_ids:
        problems.append(
            f'{where}: id = "{v}": devctl_project.metrics() already defines {v}; choose another id'
        )
    seen_ids.add(v)


def _validate_source_specific_field(
    k: str,
    v: object,
    raw_source: object,
    where: str,
    problems: list[str],
) -> None:
    if k == "label":
        if raw_source == "deployments":
            problems.append(
                f'{where}: label is not read by source "deployments"; '
                "it reads environment and count"
            )
        elif raw_source == "issues" and (not isinstance(v, str) or not v):
            problems.append(f'{where}: label = "{v}": use a non-empty string')
    elif k == "environment":
        if raw_source == "issues":
            problems.append(f'{where}: environment is not read by source "issues"; it reads label')
        elif raw_source == "deployments" and (not isinstance(v, str) or not v):
            problems.append(f'{where}: environment = "{v}": use a non-empty string')
    elif k == "count":
        if raw_source == "issues":
            problems.append(f'{where}: count is not read by source "issues"; it reads label')
        elif raw_source == "deployments" and v not in ("rollbacks", "failures"):
            problems.append(f'{where}: count = "{v}": use "rollbacks" or "failures"')


def _validate_unknown_field(
    k: str,
    raw_source: object,
    where: str,
    problems: list[str],
) -> None:
    if raw_source == "issues":
        problems.append(f"{where}: unknown key {k!r}; it accepts id, title, source, label")
    elif raw_source == "deployments":
        problems.append(
            f"{where}: unknown key {k!r}; it accepts id, title, source, environment, count"
        )
    else:
        problems.append(
            f"{where}: unknown key {k!r}; it accepts id, title, source, label, environment, count"
        )


def _validate_present_metric_field(
    k: str,
    v: object,
    raw_source: object,
    where: str,
    seen_ids: set[str],
    code_metric_ids: Collection[str],
    problems: list[str],
) -> None:
    if k == "id":
        _validate_metric_id_field(v, where, seen_ids, code_metric_ids, problems)
    elif k == "title":
        if not isinstance(v, str) or not v:
            problems.append(f'{where}: title = "{v}": use a non-empty string')
    elif k == "source":
        if v not in ("issues", "deployments"):
            problems.append(f'{where}: source = "{v}": use "issues" or "deployments"')
    elif k in ("label", "environment", "count"):
        _validate_source_specific_field(k, v, raw_source, where, problems)
    else:
        _validate_unknown_field(k, raw_source, where, problems)


def _validate_missing_metric_fields(
    m: Mapping[str, object],
    raw_source: object,
    where: str,
    problems: list[str],
) -> None:
    if "id" not in m:
        problems.append(f"{where}: id: required")
    if "title" not in m:
        problems.append(f"{where}: title: required")
    if "source" not in m:
        problems.append(f"{where}: source: required")
    elif raw_source == "issues" and "label" not in m:
        problems.append(f"{where}: label: required")
    elif raw_source == "deployments" and "environment" not in m:
        problems.append(f"{where}: environment: required")


def _validate_single_metric(
    idx: int,
    m: object,
    seen_ids: set[str],
    code_metric_ids: Collection[str],
    problems: Problems,
) -> SettingsMetric | None:
    where = f"metrics.toml [[metric]] #{idx}"
    if not isinstance(m, dict):
        problems.append(f"{where}: expected a table")
        return None

    raw_source = m.get("source")
    problems_before = len(problems)

    for k, v in m.items():
        problems.at(("metric", idx - 1, k))
        _validate_present_metric_field(k, v, raw_source, where, seen_ids, code_metric_ids, problems)

    problems.at(("metric", idx - 1), missing=True)
    _validate_missing_metric_fields(m, raw_source, where, problems)

    if len(problems) == problems_before:
        if raw_source == "issues":
            src_obj: IssuesSource | DeploymentsSource = IssuesSource(label=str(m["label"]))
        else:
            count_val = m.get("count", "rollbacks")
            if count_val in ("rollbacks", "failures"):
                src_obj = DeploymentsSource(
                    environment=str(m["environment"]),
                    count=count_val,
                )
            else:
                return None
        return SettingsMetric(
            metric_id=str(m["id"]),
            title=str(m["title"]),
            source=src_obj,
        )
    return None


def _validate_data(
    data: Mapping[str, object],
    code_metric_ids: Collection[str],
    problems: Problems,
) -> tuple[dict[str, float], list[SettingsMetric]]:
    valid_settings_ids = _collect_valid_settings_ids(data.get("metric"), code_metric_ids)
    known_ids = [*BASIC_METRICS, *valid_settings_ids, *sorted(code_metric_ids)]
    seen_ids: set[str] = set()
    thresholds: dict[str, float] = {}
    metrics: list[SettingsMetric] = []
    for key, val in data.items():
        problems.at((key,))
        if key == "window":
            _validate_window(val, problems)
        elif key == "thresholds":
            thresholds = _validate_thresholds(val, known_ids, problems)
        elif key == "metric":
            if not isinstance(val, list):
                problems.append("metrics.toml: metric: expected a list of tables")
            else:
                for idx, item in enumerate(val, start=1):
                    problems.at(("metric", idx - 1))
                    metric = _validate_single_metric(idx, item, seen_ids, code_metric_ids, problems)
                    if metric is not None:
                        metrics.append(metric)
        else:
            problems.append(
                f"metrics.toml: unknown key {key!r}; it accepts window, thresholds, metric"
            )
    return thresholds, metrics


def load_metrics(root: Path, code_metric_ids: Collection[str] = ()) -> MetricsSettings:
    path = root / METRICS
    if not path.is_file():
        raise MetricsSettingsError(
            (f"{METRICS}: missing; run rapid-ship sync to add it with the defaults",)
        )

    try:
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise MetricsSettingsError((f"metrics.toml: {error}",)) from error

    if not isinstance(data, dict):
        raise MetricsSettingsError(("metrics.toml: expected a table",))

    problems = Problems(text)
    thresholds, metrics = _validate_data(data, code_metric_ids, problems)
    ordered = problems.ordered()
    if "window" not in data:
        ordered = ("metrics.toml: window: use an integer of at least 1", *ordered)
    if ordered:
        raise MetricsSettingsError(ordered)
    return MetricsSettings(window=data["window"], thresholds=thresholds, metrics=tuple(metrics))
