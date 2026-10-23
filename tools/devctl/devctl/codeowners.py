"""The Protected set: the CODEOWNERS lines that name Protected paths, their matcher, and the
ledger rule.

Every check that names the Protected set reads it here, so they agree on which paths it holds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# GitHub reads the first of these that exists.
CODEOWNERS_FILES = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
LEDGER = "docs/corrections/"  # the Corrections ledger; CODEOWNERS holds only its README.md
_LEDGER_README = LEDGER + "README.md"
# A pattern, then one or more owners: @user, @org/team or an email address. Walk comments out the
# Protected lines, so a leading '#' is allowed; prose comments name no owner and do not match.
_OWNED_LINE = re.compile(r"^#?\s*(?P<pattern>[^\s#]+)(?:\s+(?:@[\w./-]+|\S+@\S+))+\s*$")


def _glob(pattern: str) -> str:
    parts, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        else:
            char = pattern[index]
            parts.append("[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char))
            index += 1
    return "".join(parts)


def glob_match(pattern: str, path: str) -> bool:
    """Whether path matches pattern; "**" spans directories, "*" and "?" do not."""
    return re.fullmatch(_glob(pattern), path) is not None


def codeowners_match(pattern: str, path: str) -> bool:
    """Whether a CODEOWNERS pattern covers path, by gitignore's rules.

    A pattern with a '/' before its end is anchored at the root; any other matches at any depth.
    A trailing '/' matches only below that directory. Otherwise the pattern matches the path or
    anything below it.
    """
    below_only = pattern.endswith("/")
    name = pattern.rstrip("/")
    anywhere = "" if "/" in name else "(?:.*/)?"
    below = "/.*" if below_only else "(?:/.*)?"
    return re.fullmatch(anywhere + _glob(name.lstrip("/")) + below, path) is not None


def patterns_in(text: str) -> list[str]:
    """The pattern of each line of text that names an owner, commented out or not.

    The catch-all '*' is Walk's line for every path, not a Protected path, so it is left out.
    """
    matches = (_OWNED_LINE.match(line) for line in text.splitlines())
    return [match["pattern"] for match in matches if match and match["pattern"] != "*"]


def protected_patterns(root: Path) -> list[str] | None:
    """The Protected-path patterns in the CODEOWNERS file GitHub reads; None without one.

    Commented-out lines count, so the set is listed in Walk too. Raises OSError when the file
    cannot be read.
    """
    for name in CODEOWNERS_FILES:
        path = root / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise OSError(f"{name} is not UTF-8: {error}") from error
        return patterns_in(text)
    return None


FileStatus = Literal["added", "modified", "removed", "renamed"]


@dataclass(frozen=True)
class FileChange:
    """One file a change touches, with its status mapped to one of four."""

    path: str
    status: FileStatus
    previous: str | None = None  # renamed: the path before


def ledger_entry(path: str) -> bool:
    """Whether path is a Corrections ledger entry: a .md file below docs/corrections/, at any
    depth, other than docs/corrections/README.md.

    Spec 1 says "under" the ledger, so a deeper entry counts too; a wider Protected rule fails
    safe.
    """
    return path.startswith(LEDGER) and path.endswith(".md") and path != _LEDGER_README


def protected_changes(patterns: Sequence[str], changes: Iterable[FileChange]) -> list[str]:
    """The sorted, unique paths of changes in the Protected set (Spec 1 sections 4 and 5).

    A path counts when a pattern covers it, both paths of a rename included. The ledger rule adds
    each existing ledger entry that a change modifies, removes or renames away from. An added
    entry is never checked, whatever its status, and neither is a rename's new path as an entry.
    """
    found: set[str] = set()
    for change in changes:
        paths = (change.path, change.previous) if change.previous else (change.path,)
        found.update(path for path in paths if _covered(patterns, path))
        if change.status == "renamed" and change.previous and ledger_entry(change.previous):
            found.add(change.previous)
        elif change.status in ("modified", "removed") and ledger_entry(change.path):
            found.add(change.path)
    return sorted(found)


def _covered(patterns: Sequence[str], path: str) -> bool:
    return any(codeowners_match(pattern, path) for pattern in patterns)
