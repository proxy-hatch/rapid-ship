"""Offline: the status rule."""

import pytest

from devctl.metrics.model import (
    NEEDS_IDENTITY,
    Measured,
    ThresholdStatus,
    judge,
    threshold_status,
)


@pytest.mark.parametrize(
    ("value", "unknown", "complete", "threshold", "expected"),
    [
        (2, 0, True, 1, "breached"),
        (1, 0, True, 1, "ok"),
        (0, 2, True, 1, "unknown"),
        (0, 1, True, 1, "ok"),
        (2, 5, True, 1, "breached"),
        (1, 0, False, 1, "unknown"),
        (None, 0, True, 1, "unknown"),
        (0.7, 0, True, 1.0, "ok"),
    ],
)
def test_threshold_status(
    value: float | None,
    unknown: int,
    complete: bool,
    threshold: float,
    expected: ThresholdStatus,
) -> None:
    measured = Measured(value=value, unknown=unknown, complete=complete)
    assert threshold_status(measured, threshold) == expected


def test_judge_shows_needs_agent_identity_in_place_of_a_status() -> None:
    needs_id_measured = Measured(value=None, reason=NEEDS_IDENTITY)
    report = judge(
        metric_id="revisions",
        title="Revisions",
        kind="count",
        population="agent",
        measured=needs_id_measured,
        threshold=1.0,
    )
    assert report.status == NEEDS_IDENTITY
    assert report.threshold == 1.0
    assert report.metric_id == "revisions"
    assert report.title == "Revisions"
    assert report.kind == "count"
    assert report.population == "agent"

    no_threshold_report = judge(
        metric_id="corrections",
        title="Corrections",
        kind="count",
        population="ledger",
        measured=Measured(value=5),
        threshold=None,
    )
    assert no_threshold_report.status is None
    assert no_threshold_report.threshold is None

    ok_report = judge(
        metric_id="reverts",
        title="Reverts",
        kind="count",
        population="all",
        measured=Measured(value=0, complete=True),
        threshold=1.0,
    )
    assert ok_report.status == "ok"
