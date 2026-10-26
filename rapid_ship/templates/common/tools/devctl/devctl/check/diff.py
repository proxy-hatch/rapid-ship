"""The diff step: what a change does to the tests, the Protected set and its size, compared
with its base.

The base is the PR base in CI, or the merge base with the default branch locally. The head is
the work tree, with untracked files that Git does not ignore.

On the Python stack, a change fails when it removes a test that the PR's Evidence section does
not declare, adds an assertion that cannot fail, or adds an autouse fixture to a conftest.py
without an exception marker. A test is removed when it is present at the base and absent
everywhere at the head. A test's identity is its name within its file (`test_x` or
`TestA::test_x`), so a test moved to another file is not removed.

On every stack, a change fails when it adds and removes more than DIFF_CAP counted lines without
a declared overage. The step lists the Protected paths the change touches and the Corrections
ledger entries it modifies or removes, and never fails on them: the merge guard enforces their
approval.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from devctl.check.evidence import over_cap_reason, removed_test_declarations
from devctl.check.exceptions import MARKER
from devctl.check.kit import LOCK_PATH, KitLockError, managed_paths, managed_paths_in
from devctl.check.stacks.python import (
    autouse_fixtures,
    comments,
    is_test_file,
    tautologies,
    test_identities,
)
from devctl.check.steps import (
    CheckContext,
    StepResult,
    Tier,
    blocked,
    failed,
    not_applicable,
    passed,
)
from devctl.codeowners import (
    FileChange,
    FileStatus,
    glob_match,
    protected_changes,
    protected_patterns,
)
from devctl.repo import Repo, RepoError

DIFF_CAP = 1500
LOCK_FILES = frozenset({"uv.lock", "package-lock.json"})  # each stack's lock, at any depth

_UNCOUNTED = (".md", ".txt", ".log")
_BINARY_PROBE = 8000  # Git reads a file with a NUL byte in its first 8,000 bytes as binary

# What reading and parsing a test file raises for text that is not valid Python: bad syntax,
# a null byte, or bytes that are not UTF-8.
_UNPARSABLE = (SyntaxError, ValueError)

_UNDECLARED = "declare it under 'Removed tests:' in the PR's Evidence section"
_NO_BODY = " (pass --pr-body <file> to check a body locally)"
_ALWAYS_TRUE = "is always true; assert on the behaviour instead"
_AUTOUSE = (
    "needs an exception: add '# rs-exception: EX-<n>' on its decorator line and an entry with "
    "rule autouse"
)

_NO_CODEOWNERS = "no CODEOWNERS file; only Corrections ledger entries are listed as Protected"
_OVER_CAP = (
    "the change adds and removes {} counted lines, over the {:,}-line diff cap; split it, or, "
    "once the owner accepts the overage, add 'Over the diff cap: <reason>' to the PR's "
    "Evidence section"
)

_STATUS: dict[str, FileStatus] = {"A": "added", "M": "modified", "D": "removed"}


@dataclass(frozen=True)
class Change:
    path: str
    status: Literal["A", "M", "D"]


def changed_files(repo: Repo, base: str) -> list[Change]:
    """Changes from base to the work tree, plus untracked files that Git does not ignore.

    They come in path order.
    """
    fields = repo.git("diff", "--name-status", "-z", "--no-renames", base).split("\0")
    changes = [
        Change(path, "A" if status == "A" else "D" if status == "D" else "M")
        for status, path in zip(fields[0::2], fields[1::2], strict=False)
        if path
    ]
    known = {change.path for change in changes}
    untracked = repo.git("ls-files", "--others", "--exclude-standard", "-z").split("\0")
    changes += [Change(path, "A") for path in untracked if path and path not in known]
    return sorted(changes, key=lambda change: change.path)


def _removed(identities: Mapping[str, tuple[list[str], list[str]]]) -> list[tuple[str, str]]:
    """The (path, identity) of each removed test, by identity, then path."""
    totals: Counter[str] = Counter()
    places: dict[str, list[str]] = defaultdict(list)
    for path, (before, after) in sorted(identities.items()):
        totals.update(before)
        totals.subtract(after)
        for name, count in sorted((Counter(before) - Counter(after)).items()):
            places[name].extend([path] * count)
    return [
        (path, name)
        for name, paths in sorted(places.items())
        for path in paths[: max(totals[name], 0)]
    ]


def removed_tests(identities: Mapping[str, tuple[list[str], list[str]]]) -> list[str]:
    """identities maps each changed test file to its test identities at (base, head).

    Files that did not change hold the same tests at both ends, so they are left out.
    """
    return [f"{path}::{name}" for path, name in _removed(identities)]


def _protected(root: Path, changes: Sequence[Change]) -> list[str]:
    """A note for each Protected path and ledger entry the changes touch, in path order.

    The ledger rule applies without a CODEOWNERS file too. --no-renames lists a rename as a
    removal and an addition, so a renamed ledger entry is listed by its old path.
    """
    patterns = protected_patterns(root)
    files = [FileChange(change.path, _STATUS[change.status]) for change in changes]
    listed = [f"protected: {path}" for path in protected_changes(patterns or [], files)]
    return listed if patterns is not None else [_NO_CODEOWNERS, *listed]


def _counted(path: str, managed: frozenset[str]) -> bool:
    """Whether path's lines count toward the diff cap."""
    return not (
        path.endswith(_UNCOUNTED)
        or path in managed
        or path == LOCK_PATH
        or PurePosixPath(path).name in LOCK_FILES
    )


def _untracked_lines(path: Path) -> int:
    """An untracked file's lines as Git counts them: 0 when it is binary or not a regular file."""
    if path.is_symlink() or not path.is_file():
        return 0
    data = path.read_bytes()
    if b"\0" in data[:_BINARY_PROBE]:
        return 0
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


def _managed(context: CheckContext, base: str, changes: Sequence[Change]) -> frozenset[str]:
    """The Kit-managed paths, which the cap leaves out.

    A path is managed when the work tree's Kit lock lists it as managed, or when the lock at base
    does and the change deletes the file, as a Kit sync does with a file that the Kit dropped
    and whose lock entry goes with it. The base lock alone would not do: a sync records a managed
    file that the project edited as seeded, so that edit must count. A lock that cannot be read
    lists no path: the count can only grow, and the kit step reports the work tree's lock.
    """
    repo, excluded = context.repo, context.project.excluded
    try:
        head = managed_paths(repo.root, excluded)
    except KitLockError:
        head = frozenset()
    try:
        at_base = managed_paths_in(repo.git("show", f"{base}:{LOCK_PATH}"), excluded)
    except (RepoError, KitLockError):  # git show fails when base has no lock
        return head
    deleted = {change.path for change in changes if change.status == "D"}
    return head | (at_base & deleted)


def counted_lines(context: CheckContext, base: str, changes: Sequence[Change]) -> int:
    """The lines the change adds and removes from base to the work tree, as the cap counts them.

    changes is changed_files' list: one that git diff does not list is an untracked file that Git
    does not ignore, and it counts in full. Documentation, logs, binary files, Kit-managed files,
    the Kit lock and each stack's lock file do not count.
    """
    repo = context.repo
    managed = _managed(context, base, changes)
    total = 0
    diffed: set[str] = set()
    for record in repo.git("diff", "--numstat", "-z", "--no-renames", base).split("\0"):
        if not record:
            continue
        added, removed, path = record.split("\t", 2)
        diffed.add(path)
        if added != "-" and _counted(path, managed):  # "-" marks a binary file
            total += int(added) + int(removed)
    return total + sum(
        _untracked_lines(repo.root / change.path)
        for change in changes
        if change.path not in diffed and _counted(change.path, managed)
    )


def _diff_cap(counted: int, body: str | None) -> tuple[list[str], str]:
    """A problem when the count is over the cap and no overage is declared, and the note.

    A declared overage passes with a note whatever the Mode: the step does not decide who merges
    the pull request.
    """
    note = f"diff cap: {counted} of {DIFF_CAP:,} counted lines"
    if counted <= DIFF_CAP:
        return [], note
    reason = None if body is None else over_cap_reason(body)
    if reason is not None:
        return [], f"diff cap: {counted} counted lines, over {DIFF_CAP:,}, declared: {reason}"
    return [_OVER_CAP.format(counted, DIFF_CAP) + (_NO_BODY if body is None else "")], note


def _base_tests(repo: Repo, base: str, path: str) -> list[str] | None:
    """The tests in path at base; None when that text does not parse."""
    try:
        return test_identities(repo.git("show", f"{base}:{path}"))
    except _UNPARSABLE:
        return None


def _changed_tests(
    repo: Repo, base: str, changes: Sequence[Change]
) -> tuple[dict[str, tuple[list[str], list[str]]], list[str]]:
    """Each changed test file's tests at (base, head), and a problem per file that stops parsing.

    A head that does not parse counts as holding its base's tests, so its problem is reported
    once rather than as a removal of each test.
    """
    identities: dict[str, tuple[list[str], list[str]]] = {}
    problems: list[str] = []
    for change in changes:
        if not is_test_file(change.path):
            continue
        before = None if change.status == "A" else _base_tests(repo, base, change.path)
        head = repo.root / change.path
        try:
            after = (
                [] if change.status == "D" else test_identities(head.read_text(encoding="utf-8"))
            )
        except _UNPARSABLE as error:
            if before is not None:
                problems.append(f"{change.path}: cannot parse the tests at head ({error})")
            after = before or []
        identities[change.path] = (before or [], after)
    return identities, problems


def _removals(
    context: CheckContext, removed: Sequence[tuple[str, str]]
) -> tuple[list[str], list[str]]:
    """A problem for each undeclared removal and a note for each declared one, in removed order.

    A declared removal passes with a note whatever the Mode: the step does not decide who merges
    the pull request.
    """
    body = context.pr_body
    declared = {} if body is None else removed_test_declarations(body)[0]
    problems: list[str] = []
    notes: list[str] = []
    for path, name in removed:
        test = f"{path}::{name}"
        unit = any(glob_match(pattern, path) for pattern in context.project.unit_tests)
        removal = f"removed {'unit' if unit else 'behavioural'} test {test}"
        if test not in declared:
            problems.append(f"{removal}: {_UNDECLARED}{_NO_BODY if body is None else ''}")
        else:
            notes.append(f"{removal}: declared ({declared[test]})")
    return problems, notes


def _found[T](find: Callable[[str], list[T]], source: str) -> list[T]:
    """What find returns for source; nothing when source is not valid Python."""
    try:
        return find(source)
    except _UNPARSABLE:
        return []


def _texts(repo: Repo, base: str, change: Change) -> tuple[str, str]:
    """A changed file's text at base and at head; the change must not delete it.

    An added file is empty at base. A head that is not UTF-8 reads as empty, so, like text that
    does not parse, it holds no tautology or fixture.
    """
    before = "" if change.status == "A" else repo.git("show", f"{base}:{change.path}")
    try:
        return before, (repo.root / change.path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return before, ""


def _added_tautologies(path: str, before: str, after: str) -> list[str]:
    """A problem for each tautology at head beyond the copies of it at base.

    Copies are matched by their text. The first copies in the file count as the existing ones,
    so an added copy is reported at its later line.
    """
    existing = Counter(text for _line, text in _found(tautologies, before))
    problems: list[str] = []
    for line, text in sorted(_found(tautologies, after)):
        if existing[text] > 0:
            existing[text] -= 1
        else:
            problems.append(f"{path}:{line}: {text} {_ALWAYS_TRUE}")
    return problems


def _new_autouse(path: str, before: str, after: str) -> list[str]:
    """A problem for each autouse fixture new at head without a marker on its decorator line.

    The exceptions step checks that the marked ID exists and is for rule autouse.
    """
    existing = {name for name, _line in _found(autouse_fixtures, before)}
    comment_by_line = comments(after)
    return [
        f"{path}:{line}: new autouse fixture {name} {_AUTOUSE}"
        for name, line in sorted(_found(autouse_fixtures, after), key=lambda fixture: fixture[1])
        if name not in existing and not MARKER.search(comment_by_line.get(line, ""))
    ]


def _python_rules(
    context: CheckContext, base: str, changes: Sequence[Change]
) -> tuple[list[str], list[str]]:
    """Problems, then notes, from the removed-test, tautology and autouse rules."""
    repo = context.repo
    identities, unparsable = _changed_tests(repo, base, changes)
    problems, notes = _removals(context, _removed(identities))
    problems += unparsable
    kept = [change for change in changes if change.status != "D"]
    for change in kept:
        if is_test_file(change.path):
            problems += _added_tautologies(change.path, *_texts(repo, base, change))
    for change in kept:
        if PurePosixPath(change.path).name == "conftest.py":
            problems += _new_autouse(change.path, *_texts(repo, base, change))
    return problems, notes


class DiffStep:
    name = "diff"
    tier: Tier = "full"

    def run(self, context: CheckContext) -> StepResult:
        base = context.base
        if base is None:
            return not_applicable(
                self.name, "no base commit: not a change (pass --base to check one)"
            )
        problems: list[str] = []
        notes: list[str] = []
        try:
            changes = changed_files(context.repo, base)
            if context.project.stack == "python":
                problems, notes = _python_rules(context, base, changes)
            notes += _protected(context.repo.root, changes)
            counted = counted_lines(context, base, changes)
        except (RepoError, OSError) as error:
            return blocked(self.name, str(error))
        over, note = _diff_cap(counted, context.pr_body)
        problems += over
        notes.append(note)  # last, so the reader sees the count after the Protected notes
        return failed(self.name, *problems, *notes) if problems else passed(self.name, *notes)
