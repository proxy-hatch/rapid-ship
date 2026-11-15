"""Render measured values without changing their threshold decisions."""

import html
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from devctl.metrics.model import Measured, MetricReport
from devctl.metrics.window import Window

CORRECTIONS_NOTE = "Corrections are agent-reported: agents write the ledger entries they count."

# value_text cuts an unknown value's reason to this many characters wherever it shows one: the
# terminal text, the Markdown (the issue body and the job summary), the status-change comment and
# the job log's change lines. Project code can return a reason of any length, which would make a
# posted report too large for an issue; the JSON keeps the whole reason.
_REASON_LIMIT = 500


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


def _reverted(item: Mapping[str, object]) -> str:
    text = f"#{item['pr']}"
    if item["revert"] == "whole":
        return text
    parts = [
        f"{len(names)} {noun}{'' if len(names) == 1 else 's'}"
        for names, noun in (
            (cast("list[str]", item["files"]), "file"),
            (cast("list[str]", item["sections"]), "section"),
        )
        if names
    ]
    return f"{text} in part: {' and '.join(parts)}"


def _closed(measured: Measured) -> str:
    named = [f"#{item['pr']}" for item in measured.items if item["state"] == "counted"]
    return f" ({', '.join(named)})" if named else ""


def _ledger(measured: Measured) -> str:
    """The rungs of the counted entries, then the repeats and the PRs not gardened yet."""
    rungs = cast("Mapping[str, int]", measured.extra.get("by_rung", {}))
    named = [f"rung {rung}: {count}" for rung, count in rungs.items() if count]
    text = f" ({', '.join(named)})" if named else ""
    for key, noun, rest in (("repeats", "repeat", ""), ("not_gardened", "PR", " not gardened")):
        count = len(cast("Sequence[object]", measured.extra.get(key, ())))
        if count:
            text += f", {count} {noun}{'' if count == 1 else 's'}{rest}"
    return text


def _shortened(reason: str | None) -> str | None:
    """reason cut after _REASON_LIMIT characters; the JSON keeps all of it."""
    if reason is None or len(reason) <= _REASON_LIMIT:
        return reason
    return f"{reason[:_REASON_LIMIT]}..."


def value_text(metric: MetricReport) -> str:
    measured = metric.measured
    if measured.value is None:
        return f"unknown: {_shortened(measured.reason)}"
    value = f"{measured.value:g}"
    if metric.metric_id == "revisions":
        value += " per PR"
    if measured.unknown:
        value += f", {measured.unknown} unknown"
    if metric.metric_id == "reverts":
        named = [_reverted(item) for item in measured.items if item["state"] == "counted"]
        if named:
            value += f" ({', '.join(named)})"
    if metric.metric_id == "closed_unmerged":
        value += _closed(measured)
    if metric.metric_id == "corrections":
        value += _ledger(measured)
    return value


def _table(report: Report) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = [("metric", "population", "value", "suggested", "status")]
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
                value_text(metric),
                "-" if metric.threshold is None else f"<= {metric.threshold}",
                metric.status or "-",
            )
        )
    return rows


def _when(report: Report) -> str:
    return f"{report.generated_at.astimezone(UTC):%Y-%m-%d %H:%M UTC}"


def _context(report: Report) -> str:
    return f"Agent identity: {'on' if report.agent_identity else 'off'}. {_window(report)}"


def _totals(report: Report) -> str:
    breached = sum(m.status == "breached" for m in report.metrics)
    unknown = sum(m.status == "unknown" for m in report.metrics)
    return (
        f"{breached} Suggested threshold breached and {unknown} unknown. "
        "rapid-ship takes no action."
    )


def render_text(report: Report) -> str:
    rows = _table(report)
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    lines = [f"rapid-ship metrics for {report.repository} at {_when(report)}", _context(report), ""]
    lines.extend(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
        for row in rows
    )
    lines.extend(["", CORRECTIONS_NOTE])
    lines.extend(report.notes)
    lines.append(_totals(report))
    return "\n".join(lines) + "\n"


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def _cell(text: str) -> str:
    return _escape(text).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: Report) -> str:
    """The report for a job summary or an issue. Values are escaped, so none can start a tag."""
    header, *rows = _table(report)
    lines = [
        f"## rapid-ship metrics for {_escape(report.repository)}",
        "",
        _escape(f"Generated {_when(report)}. {_context(report)}"),
        "",
        *(
            f"| {' | '.join(_cell(cell) for cell in row)} |"
            for row in (header, ("---",) * len(header), *rows)
        ),
        "",
        CORRECTIONS_NOTE,
    ]
    if report.notes:
        lines.extend(["", *(f"- {_escape(note)}" for note in report.notes)])
    lines.extend(["", _totals(report)])
    return "\n".join(lines) + "\n"


def exit_code(report: Report) -> int:
    return int(any(metric.status == "breached" for metric in report.metrics))
