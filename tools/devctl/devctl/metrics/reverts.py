"""Merged PRs that later commits reverted, whole or in part. Local git and the window only."""

from __future__ import annotations

import re
from typing import cast

from devctl.metrics.model import Measured
from devctl.metrics.partial_reverts import Unfinished, undoing
from devctl.metrics.window import PullRequest, Window
from devctl.repo import Repo

NO_PARENT = "its merge commit has no parent in this clone: run git fetch --unshallow and rerun"


def _revert_line(repo: Repo, merge_commit: str, tip: str) -> str | None:
    """The earliest commit after merge_commit with the line `This reverts commit <merge_commit>`."""
    line = re.compile(rf"^This reverts commit {merge_commit}\b", re.MULTILINE)
    log = repo.git(
        "log",
        "--reverse",
        "--topo-order",
        "--no-show-signature",
        "-z",
        "--fixed-strings",
        f"--grep=This reverts commit {merge_commit}",
        "--format=%H%n%B",
        f"{merge_commit}..{tip}",
    )
    for record in log.split("\0"):
        commit, _, message = record.partition("\n")
        if line.search(message):
            return commit
    return None


def _revert_buttons(window: Window, repository: str) -> dict[int, str]:
    """PR number -> merge commit of the earliest later PR whose body has `Reverts <repo>#<n>`."""
    line = re.compile(rf"^Reverts {re.escape(repository)}#(\d+)\b", re.IGNORECASE | re.MULTILINE)
    merged: set[int] = set()
    named: dict[int, str] = {}
    for pr in reversed(window.merged):
        for number in map(int, line.findall(pr.body)):
            if number in merged:
                named.setdefault(number, cast("str", pr.merge_commit))
        merged.add(pr.number)
    return named


def _reverted(
    repo: Repo, window: Window, pr: PullRequest, buttons: dict[int, str]
) -> dict[str, object] | None:
    merge_commit = cast("str", pr.merge_commit)
    commit = _revert_line(repo, merge_commit, window.tip) or buttons.get(pr.number)
    if commit is not None:
        return {"pr": pr.number, "state": "counted", "revert": "whole", "commit": commit}
    if len(repo.git("rev-list", "--parents", "-n", "1", merge_commit).split()) == 1:
        return {"pr": pr.number, "state": "unknown", "detail": NO_PARENT}
    try:
        undone = undoing(repo, merge_commit, window.tip)
    except Unfinished as error:
        return {"pr": pr.number, "state": "unknown", "detail": str(error)}
    if undone is None:
        return None
    item: dict[str, object] = {
        "pr": pr.number,
        "state": "counted",
        "revert": "whole" if undone.whole else "partial",
        "commit": undone.commit,
    }
    if not undone.whole:
        item["files"] = list(undone.files)
        item["sections"] = list(undone.sections)
    return item


def reverts(repo: Repo, window: Window, repository: str) -> Measured:
    """Count each PR of the window once. A whole revert outranks a partial one."""
    buttons = _revert_buttons(window, repository)
    found = [_reverted(repo, window, pr, buttons) for pr in window.prs]
    items = tuple(item for item in found if item is not None)
    unknown = sum(item["state"] == "unknown" for item in items)
    return Measured(len(items) - unknown, unknown=unknown, items=items)
