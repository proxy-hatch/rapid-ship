"""Corrections ledger entries dated in the window's span, read at the window's tip."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from devctl.codeowners import LEDGER, ledger_entry
from devctl.ledger import LAST_PASS, Entry, LastPass, read_entry, read_last_pass
from devctl.metrics.model import Measured
from devctl.metrics.partial_reverts import _partial
from devctl.metrics.window import PullRequest, Window, is_ancestor
from devctl.repo import Repo, RepoError

_PARTIAL = (
    "this clone is partial, and reading the ledger would fetch it: "
    "clone again without --filter and rerun"
)


def _text(repo: Repo, tip: str, path: str) -> str | list[str]:
    """The file as it is at tip, or the problem that git reports when it cannot read it."""
    try:
        return repo.git("show", f"{tip}:{path}")
    except RepoError as error:
        return [f"{path}: {error}"]


def _unknown(path: str, problems: list[str]) -> dict[str, object]:
    detail = "; ".join(problem.removeprefix(f"{path}: ") for problem in problems)
    return {"entry": path, "state": "unknown", "detail": detail}


def _entries(
    repo: Repo, tip: str, names: Sequence[str]
) -> tuple[list[Entry], list[dict[str, object]]]:
    """Every entry in the ledger at tip, and an unknown item for each that cannot be read."""
    entries: list[Entry] = []
    unknown: list[dict[str, object]] = []
    for name in sorted(filter(ledger_entry, names)):
        text = _text(repo, tip, name)
        read = read_entry(name, text) if isinstance(text, str) else text
        if isinstance(read, Entry):
            entries.append(read)
        else:
            unknown.append(_unknown(name, read))
    return entries, unknown


def _through(
    repo: Repo, tip: str, names: Sequence[str]
) -> tuple[str | None, list[dict[str, object]]]:
    """The commit that the last gardening pass covered, or None when no pass is on record."""
    if LAST_PASS not in names:
        return None, []
    text = _text(repo, tip, LAST_PASS)
    read = read_last_pass(text) if isinstance(text, str) else text
    if isinstance(read, LastPass):
        return read.through, []
    return None, [_unknown(LAST_PASS, read)]


def _gardened(repo: Repo, pr: PullRequest, through: str | None) -> bool:
    return (
        through is not None
        and pr.merge_commit is not None
        and is_ancestor(repo, pr.merge_commit, through)
    )


def corrections(repo: Repo, window: Window, since: datetime) -> Measured:
    """Ledger entries dated on or after the UTC day that the span starts, in total and by rung.

    The ledger is read at the window's tip, never in the work tree. A repeat is an entry in the
    span whose category already has an earlier entry anywhere in the ledger. The count is a lower
    bound while a PR of the window is not an ancestor of the last pass's through commit. In a
    partial clone git would fetch the ledger files it lacks, so the metric is unknown before it
    reads one.
    """
    if _partial(repo):
        return Measured(None, _PARTIAL)
    tip = window.tip
    names = repo.git("ls-tree", "-r", "-z", "--name-only", tip, "--", LEDGER).split("\0")
    entries, unknown = _entries(repo, tip, names)
    through, unreadable = _through(repo, tip, names)
    unknown.extend(unreadable)
    entries.sort(key=lambda entry: (entry.date, entry.file))
    first_day = since.astimezone(UTC).date()
    counted: list[Entry] = []
    repeats: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.date >= first_day:
            counted.append(entry)
            if entry.category in seen:
                repeats.append(entry.file)
        seen.add(entry.category)
    not_gardened = [pr.number for pr in window.prs if not _gardened(repo, pr, through)]
    return Measured(
        len(counted),
        unknown=len(unknown),
        complete=not not_gardened,
        items=(*({"entry": entry.file, "state": "counted"} for entry in counted), *unknown),
        extra={
            "by_rung": {
                str(rung): sum(rung in entry.rungs for entry in counted) for rung in range(1, 5)
            },
            "repeats": repeats,
            "not_gardened": not_gardened,
        },
    )
