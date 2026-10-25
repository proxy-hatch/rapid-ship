"""The Kit's migrations: edits to seeded files whose old content this Kit version refuses.

sync never applies one silently (Spec 1 section 3). It commits them on their own branch and pull
request, or with --in-place lists them and writes none.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rapid_ship.files import UnsafePath, safe_path
from rapid_ship.kit.templates import KitError, is_excluded

PROJECT_SETTINGS = ".rapid-ship/project.toml"
ROOT_GUIDE = "AGENTS.md"

_KEY = r"""(?:[A-Za-z0-9_-]+|"[^"\n]*"|'[^'\n]*')"""
# A table header, [name], [name.sub] or [[name]], with an optional comment after it.
_HEADER = re.compile(
    rf"[ \t]*\[\[?[ \t]*({_KEY})(?:[ \t]*\.[ \t]*{_KEY})*[ \t]*\]\]?[ \t]*(?:#.*)?"
)
_SEPARATOR = re.compile(r"[ \t]*\|?(?:[ \t]*:?-+:?[ \t]*\|)+(?:[ \t]*:?-+:?[ \t]*)?")
# Fenced code and inline code spans, as devctl's check/markdown.py finds them.
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})")
_CODE_SPAN = re.compile(r"(?<![\\`])(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)")
# A single-line reference definition, and a full, collapsed or shortcut reference, as devctl's
# check/markdown.py reads them.
_LABEL = r"\[((?:\\.|[^\]\\\n])*)\]"
_DEFINITION = re.compile(rf"^ {{0,3}}{_LABEL}:[ \t]*(.*)$", re.MULTILINE)
_REFERENCE = re.compile(rf"(?<!\\){_LABEL}(?!\()(?:{_LABEL})?")
# Task 9's Find the change rows, which map rule 8 requires: the target each links, and the row.
ROOT_ROWS = (
    ("README.md", "| What the project does, and how to run and check it | [README](README.md) |"),
    (
        "ARCHITECTURE.md",
        "| The system's parts and how data moves between them | [Architecture](ARCHITECTURE.md) |",
    ),
)


@dataclass(frozen=True)
class Migration:
    id: str  # "<kit version>-<slug>", unique
    path: str  # the seeded file it edits
    applies: Callable[[str], bool]  # the file holds the old content
    edit: Callable[[str], str]  # the new content; applies(edit(text)) is False
    explanation: str  # one line for the PR body


@dataclass(frozen=True)
class Pending:
    """A migration that applies: the file's text before its edit and after it."""

    migration: Migration
    before: str
    after: str


def _table_name(line: str) -> str | None:
    """The first key of the table a header line opens; None when the line is no header."""
    match = _HEADER.fullmatch(line.rstrip("\r\n"))
    return match.group(1).strip("\"'") if match else None


def _holds_table(name: str) -> Callable[[str], bool]:
    def applies(text: str) -> bool:
        return any(_table_name(line) == name for line in text.splitlines())

    return applies


def _comments_above(lines: Sequence[str], start: int, end: int) -> int:
    """Where the comment lines right above the header at end begin, at or after start."""
    first = end
    while first > start and lines[first - 1].lstrip().startswith("#"):
        first -= 1
    return first


def _without_table(name: str) -> Callable[[str], str]:
    """Delete each header of the table and its lines up to the next header, with the blank
    lines that end them. Comments right above a header stay: they describe that header."""

    def edit(text: str) -> str:
        lines = text.splitlines(keepends=True)
        kept: list[str] = []
        index = 0
        while index < len(lines):
            if _table_name(lines[index]) != name:
                kept.append(lines[index])
                index += 1
                continue
            following = (
                i for i in range(index + 1, len(lines)) if _table_name(lines[i]) is not None
            )
            end = next(following, len(lines))
            if end == len(lines):  # the table ends the file: so do the blank lines before it
                while kept and not kept[-1].strip():
                    kept.pop()
            else:
                kept += lines[_comments_above(lines, index + 1, end) : end]
            index = end
        return "".join(kept)

    return edit


def _blank(text: str) -> str:
    """Spaces for every character but the line breaks that str.splitlines finds, so the blanked
    text has the same lines as text."""
    return re.sub(r"[^\n\r\v\f\x1c-\x1e\x85\u2028\u2029]", " ", text)


def _without_code(text: str) -> str:
    """The text with fenced code and inline code spans blanked, so a link in code does not count,
    as in map rule 8. rapid_ship cannot import devctl, so this repeats its without_code."""
    lines: list[str] = []
    fence = ""
    for line in text.splitlines(keepends=True):
        if fence:
            if re.fullmatch(rf" {{0,3}}{re.escape(fence[0])}{{{len(fence)},}}\s*", line):
                fence = ""
            line = _blank(line)
        elif opening := _FENCE.match(line):
            fence = opening.group(1)
            line = _blank(line)
        lines.append(line)
    return _CODE_SPAN.sub(lambda match: _blank(match.group()), "".join(lines))


def _label_key(label: str) -> str:
    return " ".join(label.split()).casefold()


def _links(text: str, name: str) -> bool:
    """Whether text links the root file name outside code, as map rule 8 reads links: inline, or
    through the first definition of a label that a full, collapsed or shortcut reference uses."""
    text = _without_code(text)
    target = rf"<?(?:\./|/)?{re.escape(name)}(?:#[^\s)>]*)?>?"
    if re.search(rf"\]\([ \t]*{target}(?:[ \t]+[^)\n]*)?\)", text):
        return True
    definitions: dict[str, str] = {}
    for match in _DEFINITION.finditer(text):
        definitions.setdefault(_label_key(match.group(1)), match.group(2))
    uses = _REFERENCE.finditer(_DEFINITION.sub("", text))
    destinations = (definitions.get(_label_key(use.group(2) or use.group(1)), "") for use in uses)
    return any(re.match(rf"{target}(?:\s|$)", destination) for destination in destinations)


def _separator(text: str) -> int | None:
    """The index, in text.splitlines(), of the Find the change table's separator line; None
    without the table. A heading or line in fenced code or a code span does not count."""
    lines = _without_code(text).splitlines()
    heading = next(
        (i for i, line in enumerate(lines) if line.rstrip() == "## Find the change"), None
    )
    if heading is None:
        return None
    for index in range(heading + 1, len(lines)):
        if lines[index].startswith("#"):
            return None
        if _SEPARATOR.fullmatch(lines[index]):
            return index
    return None


def _lacks_root_links(text: str) -> bool:
    has_table = _separator(text) is not None
    return has_table and not all(_links(text, name) for name, _ in ROOT_ROWS)


def _add_root_links(text: str) -> str:
    """Insert Task 9's row for each root document the guide does not link, below the separator."""
    lines = text.splitlines(keepends=True)
    separator = _separator(text)
    if separator is None:
        return text
    if not lines[separator].endswith("\n"):
        lines[separator] += "\n"
    rows = [f"{row}\n" for name, row in ROOT_ROWS if not _links(text, name)]
    return "".join([*lines[: separator + 1], *rows, *lines[separator + 1 :]])


def _removal(name: str, reason: str) -> Migration:
    return Migration(
        id=f"0.2.0-remove-{name}",
        path=PROJECT_SETTINGS,
        applies=_holds_table(name),
        edit=_without_table(name),
        explanation=f"deletes the [{name}] table, which devctl refuses: {reason}",
    )


_PROVIDERS = "rapid-ship does not run agents across several Providers"
MIGRATIONS: tuple[Migration, ...] = (
    _removal("agents", _PROVIDERS),
    _removal("dispatch", "rapid-ship no longer starts Workers"),
    _removal("linear", "devctl never talks to the issue tracker"),
    _removal("release", "a project defines its own deploy metrics (Spec 3)"),
    _removal("roster", _PROVIDERS),
    Migration(
        id="0.2.0-root-guide-links",
        path=ROOT_GUIDE,
        applies=_lacks_root_links,
        edit=_add_root_links,
        explanation=(
            "adds the Find the change rows for README.md and ARCHITECTURE.md that it lacks, "
            "because map rule 8 requires the root guide to link both"
        ),
    ),
)


def _read(root: Path, path: str) -> str | None:
    """The file's text with its line endings; None when it is absent or passes through a symlink,
    which sync never reads or writes."""
    try:
        return safe_path(root, path).read_bytes().decode("utf-8")
    except (FileNotFoundError, IsADirectoryError, UnsafePath):
        return None
    except (OSError, UnicodeDecodeError) as error:
        raise KitError(f"cannot read {path}: {error}") from error


def pending(root: Path, excluded: Sequence[str]) -> list[Pending]:
    """Each migration that applies, in order, to a file that exists and is not under [kit] exclude.

    A migration sees the edits of the ones before it on the same file, so the last Pending for a
    file holds its final text.
    """
    texts: dict[str, str | None] = {}
    found: list[Pending] = []
    for migration in MIGRATIONS:
        if is_excluded(migration.path, excluded):
            continue
        if migration.path not in texts:
            texts[migration.path] = _read(root, migration.path)
        before = texts[migration.path]
        if before is None or not migration.applies(before):
            continue
        after = migration.edit(before)
        texts[migration.path] = after
        found.append(Pending(migration, before, after))
    return found


def migration_body(found: Sequence[Pending], version: str) -> str:
    """The migration pull request's text. The Evidence section comes last, as in sync's."""
    edits = [f"- `{item.migration.path}`: {item.migration.explanation}" for item in found]
    count = f"{len(found)} {'migration' if len(found) == 1 else 'migrations'}"
    parts = [
        f"This pull request migrates seeded files to what rapid-ship Kit {version} requires. "
        "`rapid-ship sync` generated it, because the Kit no longer accepts their old content "
        "and sync never edits a seeded file silently.",
        "## Changes",
        "\n".join(edits),
        "## Needs the owner",
        "These files are Protected, so the owner reviews and merges this pull request.",
        "## Evidence",
        f"- `rapid-ship sync`: {count} for Kit {version}",
        "Not covered: sync did not run ./devctl check; CI runs it on this pull request.",
    ]
    return "\n\n".join(parts) + "\n"
