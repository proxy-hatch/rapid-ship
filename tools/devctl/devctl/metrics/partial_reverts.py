"""The content check: what later commits undid of a merged PR, read from local git alone."""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from devctl.metrics.window import MetricsError
from devctl.repo import Repo

SIMILARITY = 0.8
MIN_CHANGED_LINES = 3
# What the content check may compare for one PR, in units. A similarity check spends CHECK_COST and
# 10 for each character of its two texts before it may reject them cheaply, so that the number of
# checks is bounded even when the texts are short or empty. The full ratio, which takes time in
# proportion to the product of their lengths, spends that product too.
CHECK_COST = 1_000
COMPARISON_BUDGET = 800_000_000
CUT_SHORT = (
    "the content check was cut short in {}, where its comparison budget ran out: "
    "the PR is neither counted nor cleared"
)
PARTIAL_CLONE = (
    "this clone is partial, and reading file contents would fetch them: "
    "clone again without --filter and rerun"
)

# Fixed options and config keys keep git's output the plain text that the readers below parse, and
# the same on every machine, whatever the user has set for them. They do not cover what the
# repository itself sets: its .git/info/attributes, which no option disables, or a committed
# .gitattributes can make git treat a file as binary. The GIT_DIFF_OPTS environment variable still
# overrides -U0. --first-parent reads a merge commit as its change from its first parent.
LOG = (
    "log",
    "--first-parent",
    "--reverse",
    "--no-renames",
    "--no-show-signature",
    "--ignore-submodules=none",
    "--no-color",
    "--no-textconv",
)
PATCH = ("-p", "-U0", "--inter-hunk-context=0", "--diff-algorithm=myers", "--indent-heuristic")
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@.*$", re.MULTILINE)
COMMIT = re.compile(r"^commit ([0-9a-f]+)$", re.MULTILINE)

type Entry = tuple[str, str]  # file mode and object id; all zeros stand for a missing path
type Ids = dict[str, tuple[Entry, Entry]]  # path -> (entry before, entry after)


class Unfinished(Exception):
    """The content check could not finish a PR. The message is the unknown item's detail."""


class _OverBudget(Exception):
    """A similarity check would pass the PR's comparison budget."""


@dataclass
class Budget:
    left: int

    def spend(self, cost: int) -> None:
        if cost > self.left:
            raise _OverBudget
        self.left -= cost


@dataclass(frozen=True)
class Undoing:
    commit: str  # the earliest later commit that undid part of the PR
    whole: bool  # every file the PR changed was restored
    files: tuple[str, ...]  # restored files
    sections: tuple[str, ...]  # "<path>:<first>-<last>", the PR's hunk in its merge commit


@dataclass(frozen=True)
class Hunk:
    first: int
    last: int
    removed: tuple[str, ...]
    added: tuple[str, ...]


def _literal(path: str) -> str:
    return f":(literal){path}"


def _entries(fields: str) -> Ids:
    """The entries of the paths that one commit of git's NUL-separated --raw output changed."""
    tokens = fields.split("\0") if fields else []
    ids: Ids = {}
    for meta, path in zip(tokens[0::2], tokens[1::2], strict=True):
        old_mode, new_mode, before, after, _ = meta.split()
        ids[path] = ((old_mode.removeprefix(":"), before), (new_mode, after))
    return ids


def _partial(repo: Repo) -> bool:
    """Whether git has a promisor remote, which it fetches the file contents it lacks from.

    A clone records it as remote.<name>.promisor, which git reads as a boolean, whatever its
    spelling; extensions.partialclone names one too.
    """
    for entry in repo.git("config", "--list", "-z").split("\0"):
        key, _, value = entry.partition("\n")
        if key == "extensions.partialclone" and value:
            return True
        if (
            key.startswith("remote.")
            and key.endswith(".promisor")
            and repo.git("config", "--type=bool", "--get", key).strip() == "true"
        ):
            return True
    return False


def _changes(repo: Repo, rev_range: str) -> list[tuple[str, Ids]]:
    """Each commit of the range, oldest first, with the entries of the paths it changed."""
    output = repo.git(*LOG, "--raw", "--no-abbrev", "-z", "--format=%x00%H", rev_range)
    commits = []
    for record in output.split("\0\0"):
        commit, _, fields = record.strip("\0").partition("\0")
        if not commit:
            continue
        try:
            commits.append((commit, _entries(fields)))
        except ValueError:
            raise MetricsError(
                f"cannot read the files that git log --raw lists for {rev_range}: {record[:200]!r}"
            ) from None
    return commits


def _hunks(patch: str) -> list[Hunk]:
    """The zero-context hunks of a patch, as stripped lines."""
    parts = HUNK.split(patch)  # the text before the first hunk, then start, count and body
    hunks = []
    for start, count, body in zip(parts[1::3], parts[2::3], parts[3::3], strict=True):
        # split("\n"), not splitlines(): a line may hold characters that splitlines also splits on.
        lines = body.split("\n")
        first = max(int(start), 1)
        hunks.append(
            Hunk(
                first,
                max(int(start) + int(count or 1) - 1, first),
                tuple(line[1:].strip() for line in lines if line.startswith("-")),
                tuple(line[1:].strip() for line in lines if line.startswith("+")),
            )
        )
    return hunks


def _patches(repo: Repo, rev_range: str, path: str) -> list[tuple[str, list[Hunk]]]:
    """The hunks in path of each commit of the range that changed it, oldest first."""
    # log.follow would follow a rename of this single path, whatever --no-renames says. A user's
    # attributes file, or a big-file threshold below the file's size, would make git read the file
    # as binary and print no hunks.
    output = repo.git(
        "-c",
        "log.follow=false",
        "-c",
        "core.attributesFile=/dev/null",
        "-c",
        "core.bigFileThreshold=512m",
        *LOG,
        *PATCH,
        "--format=commit %H",
        rev_range,
        "--",
        _literal(path),
    )
    parts = COMMIT.split(output)
    return [(commit, _hunks(patch)) for commit, patch in zip(parts[1::2], parts[2::2], strict=True)]


def _qualifies(hunk: Hunk) -> bool:
    changed = sum(1 for line in (*hunk.removed, *hunk.added) if line)
    return bool(hunk.removed) and changed >= MIN_CHANGED_LINES


def _similar(ours: Sequence[str], theirs: Sequence[str], budget: Budget) -> bool:
    a, b = "\n".join(ours), "\n".join(theirs)
    budget.spend(CHECK_COST + 10 * (len(a) + len(b)))
    # autojunk=False: from 200 characters on, difflib otherwise skips every character that is more
    # than 1% of the text, and the ratio of the same edit falls as the hunk grows.
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    # The cheaper ratios are upper bounds of ratio(), so they only skip work.
    if matcher.real_quick_ratio() < SIMILARITY or matcher.quick_ratio() < SIMILARITY:
        return False
    budget.spend(len(a) * len(b))
    return matcher.ratio() >= SIMILARITY


def _undone(hunk: Hunk, later: Hunk, budget: Budget) -> bool:
    return _similar(hunk.added, later.removed, budget) and _similar(
        hunk.removed, later.added, budget
    )


def _sections(
    repo: Repo, merge_commit: str, tip: str, path: str, budget: Budget
) -> Iterator[tuple[str, str]]:
    """Each section of the PR in path that a later commit undid, with the earliest such commit."""
    patches = _patches(repo, f"{merge_commit}^1..{tip}", path)
    ours = [
        h for commit, hunks in patches if commit == merge_commit for h in hunks if _qualifies(h)
    ]
    theirs = [(commit, hunks) for commit, hunks in patches if commit != merge_commit]
    for hunk in ours:
        commit = next(
            (c for c, hunks in theirs if any(_undone(hunk, h, budget) for h in hunks)), None
        )
        if commit is not None:
            yield f"{path}:{hunk.first}-{hunk.last}", commit


def _undone_sections(
    repo: Repo, merge_commit: str, tip: str, paths: Sequence[str]
) -> tuple[list[tuple[str, str]], str | None]:
    """The undone sections of the files, and the file where the PR's budget ran out, if it did."""
    budget = Budget(COMPARISON_BUDGET)
    undone: list[tuple[str, str]] = []
    for path in paths:
        try:
            for section in _sections(repo, merge_commit, tip, path, budget):
                undone.append(section)
        except _OverBudget:
            return undone, path
    return undone, None


def undoing(repo: Repo, merge_commit: str, tip: str) -> Undoing | None:
    """What commits after merge_commit, up to tip, restored or undid of the PR it merged.

    merge_commit needs a parent to compare with. Unfinished: the clone is partial, so reading file
    contents would fetch them, or the comparison budget ran out before the check found anything. A
    PR with something found counts, whatever else is unread.
    """
    if _partial(repo):
        raise Unfinished(PARTIAL_CLONE)
    commits = _changes(repo, f"{merge_commit}^1..{tip}")
    changed = next((ids for commit, ids in commits if commit == merge_commit), {})
    later = [(commit, ids) for commit, ids in commits if commit != merge_commit]
    restored: dict[str, str] = {}
    unread: list[str] = []
    for path, (before, _) in sorted(changed.items()):
        touches = [(commit, ids[path][1]) for commit, ids in later if path in ids]
        restoring = next((commit for commit, after in touches if after == before), None)
        if restoring is not None:
            restored[path] = restoring
        elif touches and before[1].strip("0"):  # a file the PR added has no removed lines to undo
            unread.append(path)
    undone, stopped = _undone_sections(repo, merge_commit, tip, unread)
    found = [*restored.values(), *(commit for _, commit in undone)]
    if not found:
        if stopped is not None:
            raise Unfinished(CUT_SHORT.format(stopped))
        return None
    position = {commit: index for index, (commit, _) in enumerate(later)}
    return Undoing(
        min(found, key=position.__getitem__),
        len(restored) == len(changed),
        tuple(restored),
        tuple(section for section, _ in undone),
    )
