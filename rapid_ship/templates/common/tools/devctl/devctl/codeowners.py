"""The Protected set: the CODEOWNERS lines that name Protected paths, and the matcher for them.

Every check that names the Protected set reads it here, so they agree on which paths it holds.
"""

from __future__ import annotations

import re
from pathlib import Path

# GitHub reads the first of these that exists.
CODEOWNERS_FILES = (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
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
