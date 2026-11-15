"""Offline: Corrections over local repositories."""

from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from devctl.codeowners import LEDGER
from devctl.ledger import LAST_PASS
from devctl.metrics.corrections import corrections
from devctl.metrics.model import Measured
from devctl.metrics.window import Window
from devctl.repo import Repo
from github_fakes import git
from metrics_fakes import MergedHistory, entry_text
from test_devctl_metrics_window import window as local_window

NO_RUNGS = {"1": 0, "2": 0, "3": 0, "4": 0}


def path(date: str, category: str, n: int = 1) -> str:
    return f"{LEDGER}{date}-{category}-{n}.md"


def last_pass(through: str) -> str:
    return f'through = "{through}"\ndate = 2026-10-16\n'


def counted(*paths: str) -> tuple[dict[str, object], ...]:
    return tuple({"entry": found, "state": "counted"} for found in paths)


def measure(h: MergedHistory) -> Measured:
    h.publish()
    window = local_window(h)
    assert window.since is not None
    return corrections(Repo.discover(h.path), window, window.since)


def test_entries_in_the_span_are_counted_by_rung(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    nested = f"{LEDGER}archive/2026-10-03-nested-1.md"
    h.merge(
        1,
        {
            path("2026-09-30", "old"): entry_text("2026-09-30", "old", "[4]"),
            path("2026-10-01", "first-day"): entry_text("2026-10-01", "first-day", "[1]"),
            path("2026-10-02", "two-rungs"): entry_text("2026-10-02", "two-rungs", "[1, 2]"),
            nested: entry_text("2026-10-03", "nested", "[3]"),
            f"{LEDGER}README.md": "# Corrections\n",
        },
    )
    h.merge(2, {})
    result = measure(h)
    assert result.value == 3
    assert result.unknown == 0
    assert result.extra["by_rung"] == {"1": 2, "2": 1, "3": 1, "4": 0}
    assert result.items == counted(
        path("2026-10-01", "first-day"), path("2026-10-02", "two-rungs"), nested
    )


def test_a_file_name_that_git_would_quote_is_read(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    plain = path("2026-10-02", "plain")
    quoted = f"{LEDGER}2026-10-03-café with space-1.md"
    h.merge(
        1,
        {
            plain: entry_text("2026-10-02", "plain"),
            quoted: entry_text("2026-10-03", "cafe"),
        },
    )
    assert measure(h).items == counted(plain, quoted)


def test_the_span_starts_on_its_utc_day(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(
        1,
        {
            path("2026-10-01", "before"): entry_text("2026-10-01", "before"),
            path("2026-10-02", "after"): entry_text("2026-10-02", "after"),
        },
    )
    h.publish()
    evening_in_new_york = datetime(2026, 10, 1, 22, 0, tzinfo=timezone(timedelta(hours=-5)))
    result = corrections(Repo.discover(tmp_path), local_window(h), evening_in_new_york)
    assert result.items == counted(path("2026-10-02", "after"))


def test_repeats_need_an_earlier_entry_of_the_category(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(
        1,
        {
            path("2026-09-01", "env-read"): entry_text("2026-09-01", "env-read"),
            path("2026-10-02", "env-read"): entry_text("2026-10-02", "env-read"),
            path("2026-10-03", "logging"): entry_text("2026-10-03", "logging"),
            path("2026-10-04", "naming", 1): entry_text("2026-10-04", "naming"),
            path("2026-10-04", "naming", 2): entry_text("2026-10-04", "naming"),
            # The file names run against the dates: the entry dated 10-08 comes second.
            path("2026-10-05", "order"): entry_text("2026-10-08", "order"),
            path("2026-10-06", "order"): entry_text("2026-10-07", "order"),
        },
    )
    result = measure(h)
    assert result.value == 6
    assert result.extra["repeats"] == [
        path("2026-10-02", "env-read"),
        path("2026-10-04", "naming", 2),
        path("2026-10-05", "order"),
    ]


def test_prs_after_through_are_not_gardened(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {})
    through = h.merge(2, {})
    h.merge(3, {LAST_PASS: last_pass(through)})
    result = measure(h)
    assert result.extra["not_gardened"] == [3]
    assert result.complete is False


def test_every_pr_up_to_through_is_gardened(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {})
    through = h.merge(2, {})
    h.push({LAST_PASS: last_pass(through)})
    result = measure(h)
    assert result.extra["not_gardened"] == []
    assert result.complete is True


def test_without_last_pass_no_pr_is_gardened(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {})
    h.merge(2, {})
    result = measure(h)
    assert result.value == 0
    assert result.complete is False
    assert result.items == ()
    assert result.extra == {"by_rung": NO_RUNGS, "repeats": [], "not_gardened": [2, 1]}


def test_an_invalid_entry_is_unknown(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    good, bad = path("2026-10-02", "good"), path("2026-10-03", "bad")
    h.merge(1, {good: entry_text("2026-10-02", "good"), bad: "No front matter.\n"})
    result = measure(h)
    assert result.value == 1
    assert result.unknown == 1
    assert result.items[0] == {"entry": good, "state": "counted"}
    unknown = result.items[1]
    assert (unknown["entry"], unknown["state"]) == (bad, "unknown")
    assert str(unknown["detail"]).startswith("front matter: ")


def test_an_entry_whose_blob_is_missing_is_unknown(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    good, lost = path("2026-10-02", "good"), path("2026-10-03", "lost")
    h.merge(1, {good: entry_text("2026-10-02", "good"), lost: entry_text("2026-10-03", "lost")})
    blob = git(tmp_path, "rev-parse", f"HEAD:{lost}")
    (tmp_path / ".git/objects" / blob[:2] / blob[2:]).unlink()
    result = measure(h)
    assert (result.value, result.unknown) == (1, 1)
    assert [(item["entry"], item["state"]) for item in result.items] == [
        (good, "counted"),
        (lost, "unknown"),
    ]


def test_an_unreadable_last_pass_is_unknown_and_gardens_nothing(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {LAST_PASS: 'through = "abc"\ndate = 2026-10-16\n'})
    result = measure(h)
    assert result.unknown == 1
    assert result.complete is False
    assert result.extra["not_gardened"] == [1]
    (item,) = result.items
    assert (item["entry"], item["state"]) == (LAST_PASS, "unknown")
    assert "through" in str(item["detail"])


def test_entries_are_read_at_origin_not_in_the_work_tree(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    at_origin = path("2026-10-02", "at-origin")
    h.merge(1, {at_origin: entry_text("2026-10-02", "at-origin", "[1]")})
    h.publish()
    window = local_window(h)
    assert window.since is not None
    h.push({path("2026-10-03", "local"): entry_text("2026-10-03", "local", "[2]")})
    (tmp_path / at_origin).write_text(entry_text("2026-09-01", "at-origin", "[3]"))
    (tmp_path / path("2026-10-04", "untracked")).write_text(
        entry_text("2026-10-04", "untracked", "[4]")
    )
    result = corrections(Repo.discover(tmp_path), window, window.since)
    assert result.value == 1
    assert result.items == counted(at_origin)
    assert result.extra["by_rung"] == {**NO_RUNGS, "1": 1}


@pytest.mark.parametrize(
    "filter_spec",
    [pytest.param("blob:none", id="blobless"), pytest.param("tree:0", id="treeless")],
)
def test_a_partial_clone_is_unknown_and_fetches_nothing(tmp_path: Path, filter_spec: str) -> None:
    source = MergedHistory(tmp_path / "source")
    git(source.path, "config", "uploadpack.allowFilter", "true")
    source.push({path("2026-10-02", "first"): entry_text("2026-10-02", "first")})
    clone = tmp_path / "clone"
    git(
        tmp_path,
        "clone",
        "-q",
        "--no-local",
        f"--filter={filter_spec}",
        f"file://{source.path}",
        str(clone),
    )
    source.push({path("2026-10-03", "second"): entry_text("2026-10-03", "second")})
    git(clone, "fetch", "-q", "origin")
    listed = git(clone, "rev-list", "--objects", "--missing=print", "origin/main")
    assert any(line.startswith("?") for line in listed.splitlines())
    objects = git(clone, "count-objects", "-v")
    window = Window("main", git(clone, "rev-parse", "origin/main"), 30, None, (), (), 0)
    result = corrections(Repo.discover(clone), window, datetime(2026, 10, 1, tzinfo=UTC))
    assert result.value is None
    assert result.reason == (
        "this clone is partial, and reading the ledger would fetch it: "
        "clone again without --filter and rerun"
    )
    assert git(clone, "count-objects", "-v") == objects
