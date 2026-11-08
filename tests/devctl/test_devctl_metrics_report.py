"""Offline: the report's text and JSON from built reports."""

import json
from datetime import UTC, datetime
from pathlib import Path

from devctl.metrics.report import Report, exit_code, render_json, render_text

from devctl.metrics.model import Measured, judge
from test_devctl_metrics_revisions import sample_window


def report() -> Report:
    return Report(
        "o/r",
        datetime(2026, 10, 16, 5, 41, 7, tzinfo=UTC),
        "main",
        "tip",
        sample_window(),
        True,
        (
            judge("revisions", "Revisions", "count", "agent", Measured(2), 1.0),
            judge("red_merges", "Red merges", "count", "agent", Measured(0, unknown=2), 1),
        ),
        (),
    )


def test_the_json_matches_the_recorded_report() -> None:
    expected = Path(__file__).parent / "fixtures/metrics/report.json"
    assert json.loads(render_json(report())) == json.loads(expected.read_text())


def test_the_text_follows_its_layout() -> None:
    text = render_text(report())
    assert text.splitlines() == [
        "rapid-ship metrics for o/r at 2026-10-16 05:41 UTC",
        "Agent identity: on. Window: 1 of 30 merged agent PRs, #1 to #1, merged since 2026-10-10.",
        "",
        "metric      population  value         suggested  status",
        "revisions   agent PRs   2 per PR      <= 1.0     breached",
        "red_merges  agent PRs   0, 2 unknown  <= 1       unknown",
        "",
        "Corrections are agent-reported: agents write the ledger entries they count.",
        "1 Suggested threshold breached and 1 unknown. rapid-ship takes no action.",
    ]
    assert exit_code(report()) == 1
