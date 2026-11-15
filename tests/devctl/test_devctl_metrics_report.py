"""Offline: the report's text and JSON from built reports."""

import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from devctl.metrics.model import Measured, MetricReport, judge
from devctl.metrics.report import (
    Report,
    exit_code,
    render_json,
    render_markdown,
    render_text,
    value_text,
)
from test_devctl_metrics_revisions import sample_window

COMMIT = "c" * 40


def revert(
    pr: int, *, files: list[str] | None = None, sections: list[str] | None = None
) -> dict[str, object]:
    item: dict[str, object] = {"pr": pr, "state": "counted", "commit": COMMIT}
    if files is None and sections is None:
        return {**item, "revert": "whole"}
    return {**item, "revert": "partial", "files": files or [], "sections": sections or []}


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
            judge("reverts", "Reverts", "count", "agent", Measured(1, items=(revert(1),)), 1),
            judge("red_merges", "Red merges", "count", "agent", Measured(0, unknown=2), 1),
        ),
        (),
    )


ENTRIES = (
    "docs/corrections/2026-10-11-env-read-1.md",
    "docs/corrections/2026-10-12-env-read-2.md",
    "docs/corrections/2026-10-13-logging-1.md",
)


def closed_unmerged_report() -> MetricReport:
    items: tuple[dict[str, object], ...] = (
        *({"pr": number, "state": "counted"} for number in (9, 7, 5, 3)),
        {
            "pr": 2,
            "state": "unknown",
            "detail": "its last closed event names no actor, or it has no closed event",
        },
    )
    measured = Measured(4, unknown=1, items=items)
    return judge("closed_unmerged", "Closed unmerged", "count", "agent", measured, 3)


def corrections_report() -> MetricReport:
    measured = Measured(
        3,
        complete=False,
        items=tuple({"entry": entry, "state": "counted"} for entry in ENTRIES),
        extra={
            "by_rung": {"1": 2, "2": 1, "3": 0, "4": 0},
            "repeats": [ENTRIES[1]],
            "not_gardened": [1],
        },
    )
    return judge("corrections", "Corrections", "count", "ledger", measured, None)


def full_report() -> Report:
    basic = report()
    return replace(basic, metrics=(*basic.metrics, closed_unmerged_report(), corrections_report()))


def test_the_json_matches_the_recorded_report() -> None:
    expected = Path(__file__).parent / "fixtures/metrics/report.json"
    assert json.loads(render_json(full_report())) == json.loads(expected.read_text())


def test_the_text_follows_its_layout() -> None:
    text = render_text(report())
    assert text.splitlines() == [
        "rapid-ship metrics for o/r at 2026-10-16 05:41 UTC",
        "Agent identity: on. Window: 1 of 30 merged agent PRs, #1 to #1, merged since 2026-10-10.",
        "",
        "metric      population  value         suggested  status",
        "revisions   agent PRs   2 per PR      <= 1.0     breached",
        "reverts     agent PRs   1 (#1)        <= 1       ok",
        "red_merges  agent PRs   0, 2 unknown  <= 1       unknown",
        "",
        "Corrections are agent-reported: agents write the ledger entries they count.",
        "1 Suggested threshold breached and 1 unknown. rapid-ship takes no action.",
    ]
    assert exit_code(report()) == 1


def test_the_markdown_follows_its_layout() -> None:
    assert render_markdown(report()).splitlines() == [
        "## rapid-ship metrics for o/r",
        "",
        "Generated 2026-10-16 05:41 UTC. Agent identity: on. "
        "Window: 1 of 30 merged agent PRs, #1 to #1, merged since 2026-10-10.",
        "",
        "| metric | population | value | suggested | status |",
        "| --- | --- | --- | --- | --- |",
        "| revisions | agent PRs | 2 per PR | &lt;= 1.0 | breached |",
        "| reverts | agent PRs | 1 (#1) | &lt;= 1 | ok |",
        "| red_merges | agent PRs | 0, 2 unknown | &lt;= 1 | unknown |",
        "",
        "Corrections are agent-reported: agents write the ledger entries they count.",
        "",
        "1 Suggested threshold breached and 1 unknown. rapid-ship takes no action.",
    ]


def test_the_markdown_lists_closed_unmerged_and_corrections_after_red_merges() -> None:
    assert render_markdown(full_report()).splitlines()[4:11] == [
        "| metric | population | value | suggested | status |",
        "| --- | --- | --- | --- | --- |",
        "| revisions | agent PRs | 2 per PR | &lt;= 1.0 | breached |",
        "| reverts | agent PRs | 1 (#1) | &lt;= 1 | ok |",
        "| red_merges | agent PRs | 0, 2 unknown | &lt;= 1 | unknown |",
        "| closed_unmerged | agent PRs | 4, 1 unknown (#9, #7, #5, #3) | &lt;= 3 | breached |",
        "| corrections | ledger | 3 (rung 1: 2, rung 2: 1), 1 repeat, 1 PR not gardened | - | - |",
    ]


def test_markdown_escapes_html_table_pipes_and_newlines() -> None:
    metric = judge(
        "corrections",
        "Corrections",
        "count",
        "ledger",
        Measured(None, "bad | <b>x</b>\nnext --> y"),
        None,
    )
    value = replace(report(), metrics=(metric,), notes=("see <origin/main> & fetch",))

    lines = render_markdown(value).splitlines()

    assert (
        "| corrections | ledger | unknown: bad \\| &lt;b&gt;x&lt;/b&gt; next --&gt; y | - | - |"
        in lines
    )
    assert "- see &lt;origin/main&gt; &amp; fetch" in lines
    assert not any("<" in line or "-->" in line for line in lines)


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


def test_reverts_list_their_prs_and_say_when_a_revert_is_in_part() -> None:
    items = (
        revert(7),
        revert(5, files=["a.txt"]),
        revert(3, files=["a.txt", "b.txt"], sections=["c.txt:1-4"]),
        revert(2, sections=["c.txt:1-4", "c.txt:9-12"]),
        {"pr": 9, "state": "unknown", "detail": "its merge commit has no parent in this clone"},
    )
    metric = judge("reverts", "Reverts", "count", "agent", Measured(4, unknown=1, items=items), 5)
    text = render_text(replace(report(), metrics=(metric,)))
    assert "4, 1 unknown (#7, #5 in part: 1 file, #3 in part: 2 files and 1 section, " in text
    assert "#2 in part: 2 sections)" in text


def test_a_partial_revert_keeps_its_commit_files_and_sections_in_the_json() -> None:
    item = revert(4, files=["a.txt"], sections=["f.txt:5-8"])
    metric = judge("reverts", "Reverts", "count", "agent", Measured(1, items=(item,)), 1)
    data = json.loads(render_json(replace(report(), metrics=(metric,))))
    assert data["metrics"][0]["items"] == [
        {
            "pr": 4,
            "state": "counted",
            "commit": COMMIT,
            "revert": "partial",
            "files": ["a.txt"],
            "sections": ["f.txt:5-8"],
        }
    ]


@pytest.mark.parametrize(
    ("length", "shown"),
    [
        pytest.param(500, "x" * 500, id="500 characters, shown whole"),
        pytest.param(501, "x" * 500 + "...", id="501 characters, cut"),
        pytest.param(200_000, "x" * 500 + "...", id="200,000 characters, cut"),
    ],
)
def test_a_reason_over_500_characters_is_cut_in_the_text_and_kept_in_the_json(
    length: int, shown: str
) -> None:
    metric = judge("incidents", "Incidents", "count", "repository", Measured(None, "x" * length), 1)
    value = replace(report(), metrics=(metric,))

    assert value_text(metric) == f"unknown: {shown}"
    assert f"| incidents | repository | unknown: {shown} | &lt;= 1 | unknown |" in (
        render_markdown(value).splitlines()
    )
    assert f"unknown: {shown}" in render_text(value)
    assert json.loads(render_json(value))["metrics"][0]["reason"] == "x" * length


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


def test_the_text_lists_closed_unmerged_and_corrections_after_red_merges() -> None:
    assert render_text(full_report()).splitlines() == [
        "rapid-ship metrics for o/r at 2026-10-16 05:41 UTC",
        "Agent identity: on. Window: 1 of 30 merged agent PRs, #1 to #1, merged since 2026-10-10.",
        "",
        "metric           population  value"
        "                                                  suggested  status",
        "revisions        agent PRs   2 per PR"
        "                                               <= 1.0     breached",
        "reverts          agent PRs   1 (#1)"
        "                                                 <= 1       ok",
        "red_merges       agent PRs   0, 2 unknown"
        "                                           <= 1       unknown",
        "closed_unmerged  agent PRs   4, 1 unknown (#9, #7, #5, #3)"
        "                          <= 3       breached",
        "corrections      ledger      3 (rung 1: 2, rung 2: 1), 1 repeat, 1 PR not gardened"
        "  -          -",
        "",
        "Corrections are agent-reported: agents write the ledger entries they count.",
        "2 Suggested threshold breached and 1 unknown. rapid-ship takes no action.",
    ]
    assert exit_code(full_report()) == 1


def value_cell(metric: MetricReport) -> str:
    row = render_text(replace(report(), metrics=(metric,))).splitlines()[4]
    return re.split(r"\s{2,}", row)[2]


def counted(*numbers: int) -> tuple[dict[str, object], ...]:
    return tuple({"pr": number, "state": "counted"} for number in numbers)


@pytest.mark.parametrize(
    ("measured", "text"),
    [
        (Measured(0), "0"),
        (Measured(2, items=counted(9, 4)), "2 (#9, #4)"),
        (
            Measured(0, unknown=1, items=({"pr": 2, "state": "unknown", "detail": "no closer"},)),
            "0, 1 unknown",
        ),
        (
            Measured(1, unknown=1, items=(*counted(9), {"pr": 3, "state": "unknown"})),
            "1, 1 unknown (#9)",
        ),
    ],
)
def test_closed_unmerged_lists_the_prs_it_counted(measured: Measured, text: str) -> None:
    metric = judge("closed_unmerged", "Closed unmerged", "count", "agent", measured, None)
    assert value_cell(metric) == text


def ledger(
    value: int,
    *,
    by_rung: dict[str, int],
    repeats: list[str] | None = None,
    not_gardened: list[int] | None = None,
    unknown: int = 0,
) -> Measured:
    extra = {"by_rung": by_rung, "repeats": repeats or [], "not_gardened": not_gardened or []}
    return Measured(value, unknown=unknown, complete=not not_gardened, extra=extra)


@pytest.mark.parametrize(
    ("measured", "text"),
    [
        (ledger(0, by_rung={"1": 0, "2": 0, "3": 0, "4": 0}), "0"),
        (ledger(3, by_rung={"1": 2, "2": 0, "3": 1, "4": 0}), "3 (rung 1: 2, rung 3: 1)"),
        (
            ledger(3, by_rung={"1": 3, "2": 0, "3": 0, "4": 0}, repeats=["a"], not_gardened=[4]),
            "3 (rung 1: 3), 1 repeat, 1 PR not gardened",
        ),
        (
            ledger(
                3, by_rung={"1": 3, "2": 0, "3": 0, "4": 0}, repeats=["a", "b"], not_gardened=[4, 3]
            ),
            "3 (rung 1: 3), 2 repeats, 2 PRs not gardened",
        ),
        (
            ledger(1, by_rung={"1": 1, "2": 0, "3": 0, "4": 0}, unknown=1),
            "1, 1 unknown (rung 1: 1)",
        ),
    ],
)
def test_corrections_names_its_rungs_repeats_and_prs_not_gardened(
    measured: Measured, text: str
) -> None:
    metric = judge("corrections", "Corrections", "count", "ledger", measured, None)
    assert value_cell(metric) == text


def test_the_json_keeps_the_corrections_lists_and_the_closed_unmerged_unknown_item() -> None:
    data = json.loads(render_json(full_report()))
    closed, corrections = data["metrics"][3:]
    assert closed["items"][-1] == {
        "pr": 2,
        "state": "unknown",
        "detail": "its last closed event names no actor, or it has no closed event",
    }
    assert (closed["value"], closed["unknown"], closed["status"]) == (4, 1, "breached")
    assert (corrections["population"], corrections["threshold"], corrections["status"]) == (
        "ledger",
        None,
        None,
    )
    assert corrections["repeats"] == [ENTRIES[1]]
    assert corrections["not_gardened"] == [1]
    assert data["version"] == 1
