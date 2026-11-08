"""The exceptions step: each suppression has exactly one listed, current exception.

A suppression is a lint, type, coverage, test, dead-code or secret-scan opt-out. It carries
`# rs-exception: EX-<n>` on its line, and .rapid-ship/exceptions.toml has one entry for that
ID. On the Python stack, each allowlist item in its stack's pyproject.toml is one too, and so is a
line that vulture or deptry reads as one, a string included. This module and the stack modules
in stacks/ are the one definition of suppressions and their rule names.
"""

from __future__ import annotations

import re
import tomllib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from devctl.check.kit import KitLockError, managed_paths
from devctl.check.stacks.agnostic import text_rules
from devctl.check.stacks.python import autouse_fixtures, comment_rules, comments, marker_rules
from devctl.check.stacks.python_dead_code import PYPROJECT, toml_allowlist, tool_line_rules
from devctl.check.steps import CheckContext, StepResult, Tier, blocked, failed, passed
from devctl.repo import RepoError
from devctl.settings import ExceptionEntry, ProjectSettings, SettingsError, load_exceptions, under

MARKER = re.compile(r"rs-exception:\s*(?P<id>EX-\d+)")

_PYTHON_SOURCE = (".py", ".pyi")


@dataclass(frozen=True)
class SuppressedLine:
    path: str
    number: int
    rules: tuple[str, ...]  # suppressions that need an exception
    optional: tuple[str, ...]  # autouse fixtures: validated when marked, required only by diff
    markers: tuple[str, ...]


class ExceptionsStep:
    name = "exceptions"
    tier: Tier = "fast"

    def run(self, context: CheckContext) -> StepResult:
        root = context.repo.root
        try:
            entries = load_exceptions(root)
            managed = managed_paths(root, context.project.excluded)
            files = context.repo.files()
            lines = scan(root, files, managed, context.project)
            unplaced = [
                error
                for stack in context.project.stacks
                if stack.name == "python"
                for error in _allowlist_errors(
                    root, files, managed, under(stack.directory, PYPROJECT)
                )
            ]
        except (SettingsError, KitLockError, RepoError, OSError) as error:
            return blocked(self.name, str(error))
        errors = [*exception_errors(lines, entries), *unplaced]
        return failed(self.name, *errors) if errors else passed(self.name)


def scan(
    root: Path, files: Sequence[str], managed: frozenset[str], project: ProjectSettings
) -> list[SuppressedLine]:
    """The lines that carry a suppression or, in Python source, an exception marker.

    Paths are relative to `root`. A file is skipped when it is a Kit file the project does not
    own (`managed`), is not a regular file, is a symlink, or is not UTF-8. Lines come in path
    then line order. Each Python stack's pyproject.toml allowlist items are suppressions on
    their lines;
    invalid TOML raises SettingsError naming that file.
    """
    found: list[SuppressedLine] = []
    for path in sorted(files):
        text = _readable(root, path, managed)
        if text is None:
            continue
        python = any(stack.name == "python" for stack in project.owners(path))
        if python and path.endswith(_PYTHON_SOURCE):
            found += _python_lines(path, text)
        elif any(
            stack.name == "python" and path == under(stack.directory, PYPROJECT)
            for stack in project.stacks
        ):
            found += _pyproject_lines(path, text)
        else:
            found += _text_lines(path, text)
    return found


def _allowlist_errors(
    root: Path, files: Sequence[str], managed: frozenset[str], path: str
) -> list[str]:
    """The selected pyproject.toml's items that the scan could not place on a line, and lines that
    hold two items."""
    text = _readable(root, path, managed) if path in files else None
    return toml_allowlist(text, path)[1] if text is not None else []


def _readable(root: Path, path: str, managed: frozenset[str]) -> str | None:
    """The text of a file that the scan reads; None for a file it skips."""
    target = root / path
    if path in managed or not target.is_file() or target.is_symlink():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def _markers(text: str) -> tuple[str, ...]:
    return tuple(match.group("id") for match in MARKER.finditer(text))


def _python_lines(path: str, source: str) -> list[SuppressedLine]:
    """Suppressions come from comment tokens, the syntax tree and the dead-code tools' reading.

    Ruff, mypy and pytest never read a string. vulture and deptry read a line's whole text, so
    `tool_line_rules` adds what they read beyond the comment.
    """
    comment_by_line = comments(source)
    found = {n: [*comment_rules(c), *text_rules(path, c)] for n, c in comment_by_line.items()}
    tools = tool_line_rules(source, found)
    for number, rule in marker_rules(source):
        found.setdefault(number, []).append(rule)
    autouse: dict[int, list[str]] = {}
    if PurePosixPath(path).name == "conftest.py":
        for _name, number in autouse_fixtures(source):
            autouse.setdefault(number, []).append("autouse")
    lines: list[SuppressedLine] = []
    for number in sorted(found.keys() | tools.keys() | autouse.keys()):
        rules = (*found.get(number, ()), *tools.get(number, ()))
        markers = _markers(comment_by_line.get(number, ""))
        if rules or markers:
            lines.append(
                SuppressedLine(path, number, rules, tuple(autouse.get(number, ())), markers)
            )
    return lines


def _text_lines(
    path: str, text: str, extra: Mapping[int, Sequence[str]] | None = None
) -> list[SuppressedLine]:
    """Every line of a non-Python file. A marker counts only on a line with a suppression.

    `extra` adds rules by line number: pyproject.toml's allowlist items.
    """
    lines: list[SuppressedLine] = []
    for number, line in enumerate(text.split("\n"), start=1):
        if rules := (*text_rules(path, line), *(extra or {}).get(number, ())):
            lines.append(SuppressedLine(path, number, rules, (), _markers(line)))
    return lines


def _pyproject_lines(path: str, text: str) -> list[SuppressedLine]:
    """The text rules, plus each allowlist item as a suppression on its line."""
    items: dict[int, list[str]] = {}
    try:
        allowlist, _errors = toml_allowlist(text, path)
    except tomllib.TOMLDecodeError as error:
        raise SettingsError(f"{path}: {error}") from error
    for item in allowlist:
        items.setdefault(item.line, []).append(normal_rule(item.rule))
    return _text_lines(path, text, items)


def normal_rule(rule: str) -> str:
    """'S607, S603' -> 'S603,S607'; 'zizmor:b, a' -> 'zizmor:a,b'."""
    prefix, colon, names = rule.strip().rpartition(":")
    parts = sorted(part for part in re.split(r"[\s,]+", names) if part)
    return f"{prefix.strip()}{colon}{','.join(parts)}"


def exception_errors(
    lines: Sequence[SuppressedLine], entries: Sequence[ExceptionEntry]
) -> list[str]:
    # load_exceptions has already checked the fields, the ID format and uniqueness.
    by_id = {entry.id: entry for entry in entries}
    errors: list[str] = []
    uses = Counter(marker for line in lines for marker in line.markers)
    for line in lines:
        errors += _line_errors(line, by_id)
    errors += [f"{i} is used on {n} lines; each ID is used once" for i, n in uses.items() if n > 1]
    errors += [
        f"{entry.id} is stale: no suppression carries it; delete the entry"
        for entry in by_id.values()
        if entry.rule != "file-size" and uses[entry.id] == 0
    ]
    return errors


def _line_errors(line: SuppressedLine, by_id: Mapping[str, ExceptionEntry]) -> list[str]:
    where = f"{line.path}:{line.number}"
    required, optional = list(line.rules), list(line.optional)
    errors: list[str] = []
    for marker in line.markers:
        entry = by_id.get(marker)
        if entry is None:
            errors.append(f"{where}: {marker} is not in .rapid-ship/exceptions.toml")
        elif entry.path != line.path:
            errors.append(f"{where}: {marker} names {entry.path}, not this file")
        elif (rule := normal_rule(entry.rule)) in required:
            required.remove(rule)
        elif rule in optional:
            optional.remove(rule)
        else:
            errors.append(
                f"{where}: {marker} is for rule {entry.rule}, which is not suppressed on this line"
            )
    errors += [
        f"{where}: suppression {rule} needs '# rs-exception: EX-<n>' and an entry in "
        ".rapid-ship/exceptions.toml"
        for rule in required
    ]
    return errors
