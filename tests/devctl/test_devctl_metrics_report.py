"""Offline: the report's text and JSON from built reports."""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from devctl.metrics.model import Measured, judge
from devctl.metrics.report import Report, exit_code, render_json, render_text
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


def test_a_window_that_is_not_full_or_empty_says_so() -> None:
    value = report()
    window = sample_window()
    assert "Window: 1 of 30 merged agent PRs" in render_text(value)
    assert "Window: the last 1 merged agent PRs" in render_text(
        replace(value, window=replace(window, size=1))
    )
    for identity, population in ((True, "agent PRs"), (False, "PRs")):
        empty = replace(value, window=replace(window, prs=()), agent_identity=identity)
        assert f"Window: no merged {population} yet." in render_text(empty)
        assert json.loads(render_json(empty))["window"]["since"] is None
    unavailable = replace(value, window=None, branch=None, tip=None)
    assert "Window: unavailable." in render_text(unavailable)
    data = json.loads(render_json(unavailable))
    assert data["window"] is None
    assert data["default_branch"] == {"name": None, "commit": None}


def test_unknown_reason_extra_fields_and_utc_are_preserved() -> None:
    metric = judge(
        "corrections",
        "Corrections",
        "count",
        "ledger",
        Measured(
            None,
            "ledger unavailable",
            extra={
                "by_rung": {"1": 2},
                "repeats": 1,
                "not_gardened": 3,
            },
        ),
        None,
    )
    value = replace(
        report(),
        metrics=(metric,),
        generated_at=datetime(2026, 10, 16, 13, 41, 7, tzinfo=timezone(timedelta(hours=8))),
    )
    data = json.loads(render_json(value))
    assert data["generated_at"] == "2026-10-16T05:41:07Z"
    assert data["metrics"][0]["by_rung"] == {"1": 2}
    assert data["metrics"][0]["repeats"] == 1
    assert data["metrics"][0]["not_gardened"] == 3
    assert data["metrics"][0]["status"] is None
    assert "unknown: ledger unavailable" in render_text(value)
    assert "0 Suggested threshold breached and 0 unknown." in render_text(value)
    assert exit_code(value) == 0
