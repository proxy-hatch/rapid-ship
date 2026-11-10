"""Render measured values without changing their threshold decisions."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime

from devctl.metrics.model import MetricReport
from devctl.metrics.window import Window


@dataclass(frozen=True)
class Report:
    repository: str
    generated_at: datetime
    branch: str | None
    tip: str | None
    window: Window | None
    agent_identity: bool
    metrics: tuple[MetricReport, ...]
    notes: tuple[str, ...]


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_json(report: Report) -> str:
    window = report.window
    data = {
        "version": 1,
        "repository": report.repository,
        "generated_at": _utc(report.generated_at),
        "default_branch": {"name": report.branch, "commit": report.tip},
        "agent_identity": report.agent_identity,
        "window": None
        if window is None
        else {
            "size": window.size,
            "prs": len(window.prs),
            "population": "agent" if report.agent_identity else "all",
            "since": _utc(window.since) if window.since else None,
            "not_fetched": window.not_fetched,
        },
        "metrics": [
            {
                "id": m.metric_id,
                "title": m.title,
                "kind": m.kind,
                "population": m.population,
                "value": m.measured.value,
                "unknown": m.measured.unknown,
                "reason": m.measured.reason,
                "items": list(m.measured.items),
                "threshold": m.threshold,
                "status": m.status,
                **m.measured.extra,
            }
            for m in report.metrics
        ],
        "notes": list(report.notes),
    }
    return json.dumps(data, indent=2) + "\n"


def _window(report: Report) -> str:
    window = report.window
    population = "agent PRs" if report.agent_identity else "PRs"
    if window is None:
        return "Window: unavailable."
    if not window.prs:
        return f"Window: no merged {population} yet."
    count = (
        f"the last {window.size}"
        if len(window.prs) == window.size
        else f"{len(window.prs)} of {window.size}"
    )
    since = window.since
    return (
        f"Window: {count} merged {population}, #{window.prs[-1].number} to "
        f"#{window.prs[0].number}, merged since {since:%Y-%m-%d}."
    )


def _value(metric: MetricReport) -> str:
    measured = metric.measured
    if measured.value is None:
        return f"unknown: {measured.reason}"
    value = f"{measured.value:g}"
    if metric.metric_id == "revisions":
        value += " per PR"
    if measured.unknown:
        value += f", {measured.unknown} unknown"
    return value


def render_text(report: Report) -> str:
    rows = [("metric", "population", "value", "suggested", "status")]
    populations = {
        "agent": "agent PRs",
        "all": "all PRs",
        "ledger": "ledger",
        "repository": "repository",
    }
    for metric in report.metrics:
        rows.append(
            (
                metric.metric_id,
                populations[metric.population],
                _value(metric),
                "-" if metric.threshold is None else f"<= {metric.threshold}",
                metric.status or "-",
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    lines = [
        f"rapid-ship metrics for {report.repository} at "
        f"{report.generated_at.astimezone(UTC):%Y-%m-%d %H:%M UTC}",
        f"Agent identity: {'on' if report.agent_identity else 'off'}. {_window(report)}",
        "",
    ]
    lines.extend(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    )
    lines.extend(
        ["", "Corrections are agent-reported: agents write the ledger entries they count."]
    )
    lines.extend(report.notes)
    breached = sum(m.status == "breached" for m in report.metrics)
    unknown = sum(m.status == "unknown" for m in report.metrics)
    lines.append(
        f"{breached} Suggested threshold breached and {unknown} unknown. "
        "rapid-ship takes no action."
    )
    return "\n".join(lines) + "\n"


def exit_code(report: Report) -> int:
    return int(any(metric.status == "breached" for metric in report.metrics))
