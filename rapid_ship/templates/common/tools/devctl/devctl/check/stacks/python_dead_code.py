"""The dead-code step for Python, its floor settings, and the allowlist items in pyproject.toml.

vulture reports unused code and deptry reports dependencies that do not match the imports. The
exceptions step reads each allowlist item as a suppression, so each needs its own line.
"""

from __future__ import annotations

import json
import re
import tempfile
import tomllib
from collections import Counter
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from devctl.check.map import graced
from devctl.check.stacks.python import requirement_names, toml_strings, toml_table
from devctl.check.steps import (
    CheckContext,
    StepResult,
    Tier,
    blocked,
    command_result,
    failed,
    not_applicable,
    output_tail,
    passed,
    run_tool,
)

PYPROJECT = "pyproject.toml"
# The command line's --min-confidence replaces the file's, so a project cannot switch a kind off.
VULTURE = ("uv", "run", "--locked", "vulture", "--min-confidence", "0")
# deptry runs every rule; the step appends the report's path.
DEPTRY = ("uv", "run", "--locked", "deptry", ".", "--no-ansi", "--json-output")
DEAD_CODE_TOOLS = ("vulture", "deptry")
VULTURE_CODES = ("V101", "V102", "V103", "V104", "V105", "V106", "V107", "V201")
# Each item of these keys under [tool] hides a finding, so each item is a suppression. Every key of
# the last two tables is one.
ALLOWLIST_KEYS = (
    "vulture.ignore_names",
    "vulture.ignore_decorators",
    "deptry.ignore",
    "deptry.per_rule_ignores",
    "deptry.package_module_name_map",
    "deptry.optional_dependencies_dev_groups",
    "deptry.pep621_dev_dependency_groups",
)
_RULE_TABLE = "deptry.per_rule_ignores"  # each key is a rule code that holds an array
_NAME_MAP = "deptry.package_module_name_map"  # each key is a distribution name
_ARRAYS = frozenset(ALLOWLIST_KEYS) - {_RULE_TABLE, _NAME_MAP}
_TIMEOUT_SECONDS = 600

_BARE = r"[A-Za-z0-9_-]+"
_HEADER = re.compile(rf"\s*\[\[?\s*(?P<name>{_BARE}(?:\s*\.\s*{_BARE})*)\s*\]\]?\s*(?:#.*)?")
_ARRAY_OPEN = re.compile(rf"\s*(?P<key>{_BARE})\s*=\s*\[")
_STRING = r""""(?:[^"\\]|\\.)*"|'[^']*'"""
_MAP_KEY = re.compile(rf"\s*(?P<key>{_BARE}|{_STRING})\s*=")
_TOKEN = re.compile(rf"{_STRING}|#")


class DeadCodeStep:
    """Unused code and unused or undeclared dependencies: vulture and deptry, both every time."""

    name = "dead-code"
    tier: Tier = "full"

    def run(self, context: CheckContext) -> StepResult:
        root = context.repo.root
        try:
            pyproject = _read(root / PYPROJECT)
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            return blocked(self.name, f"{PYPROJECT}: {error}")
        gaps = _run_gaps(pyproject)
        if gaps:
            errors, notes = graced(gaps)
            return blocked(self.name, *errors) if errors else not_applicable(self.name, *notes)
        vulture = run_tool(root, VULTURE, _TIMEOUT_SECONDS)
        results = {
            "vulture": command_result(self.name, VULTURE, vulture, frozenset({3})),
            "deptry": _deptry(self.name, root),
        }
        details = [f"{tool}: {line}" for tool, r in results.items() for line in r.details]
        statuses = {result.status for result in results.values()}
        if "blocked" in statuses:
            return blocked(self.name, *details)
        return failed(self.name, *details) if "failed" in statuses else passed(self.name, *details)


def _read(path: Path) -> Mapping[str, object]:
    """The parsed file; an empty table when it does not exist."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    return tomllib.loads(text)


def _paths(pyproject: Mapping[str, object]) -> list[str]:
    return toml_strings(toml_table(pyproject, "tool", "vulture").get("paths"))


def _run_gaps(pyproject: Mapping[str, object]) -> list[str]:
    """What the step needs before it runs a tool: both tools in the dev group, and paths."""
    present = requirement_names(toml_table(pyproject, "dependency-groups").get("dev"))
    lacking = [tool for tool in DEAD_CODE_TOOLS if tool not in present]
    gaps: list[str] = []
    if lacking:
        gaps.append(
            f"[dependency-groups] dev lacks {', '.join(lacking)}; add them to pyproject.toml and "
            "run uv lock"
        )
    if not _paths(pyproject):
        gaps.append(
            "[tool.vulture] paths is not set; list the directories vulture scans, such as "
            '["src", "tests"]'
        )
    return gaps


def _deptry(name: str, root: Path) -> StepResult:
    """deptry exits 1 for findings and for its own errors, so exit 1 reads the report."""
    with tempfile.TemporaryDirectory(prefix="devctl-dead-code-") as scratch:
        argv = (*DEPTRY, str(Path(scratch, "deptry.json")))
        result = run_tool(root, argv, _TIMEOUT_SECONDS)
        if result is None or result.timed_out or result.returncode != 1:
            return command_result(name, argv, result, frozenset())
        findings = _findings(Path(argv[-1]))
    if findings is None:
        return blocked(name, "deptry exited 1 and wrote no readable report", *output_tail(result))
    return failed(name, *findings)


def _findings(report: Path) -> list[str] | None:
    """One line per violation in deptry's JSON report; None when it is unreadable or empty."""
    try:
        document = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, list) or not document:
        return None
    lines = [_finding(item) for item in document]
    return None if None in lines else [line for line in lines if line is not None]


def _finding(item: object) -> str | None:
    error = item.get("error") if isinstance(item, dict) else None
    location = item.get("location") if isinstance(item, dict) else None
    if not isinstance(error, dict) or not isinstance(location, dict):
        return None
    code, message, file = error.get("code"), error.get("message"), location.get("file")
    if not (isinstance(code, str) and isinstance(message, str) and isinstance(file, str)):
        return None
    # A dependency's own finding has no line or column.
    where = (file, location.get("line"), location.get("column"))
    return f"{':'.join(str(part) for part in where if part is not None)}: {code} {message}"


def dead_code_gaps(pyproject: Mapping[str, object]) -> list[str]:
    """The dead-code settings of doctor's Python floor that pyproject lacks, one message each."""
    gaps = [] if _paths(pyproject) else ["vulture: paths is not set"]
    lint = toml_table(pyproject, "tool", "ruff", "lint")
    external = [item for item in toml_strings(lint.get("external")) if item]
    if not all(any(code.startswith(item) for item in external) for code in VULTURE_CODES):
        gaps.append("ruff: external lacks V")  # Ruff then reports each vulture noqa as RUF102
    return gaps


@dataclass(frozen=True)
class AllowlistItem:
    line: int  # 1-based, in pyproject.toml
    rule: str  # "<key under [tool]>:<item>", not normalised; exceptions.py normalises it


def toml_allowlist(text: str) -> tuple[list[AllowlistItem], list[str]]:
    """The allowlist items of pyproject.toml's text, each on its line, and the errors.

    tomllib keeps no line numbers, so a line scan finds each item, and tomllib's own reading of
    the same keys finds any item the scan missed: each one is an error, as is a line with two
    items. Raises tomllib.TOMLDecodeError for invalid TOML.
    """
    expected = list(_parsed_items(tomllib.loads(text)))
    items: list[AllowlistItem] = []
    errors: list[str] = []
    unplaced = Counter(expected)
    for number, key, found in _scanned(text):
        items += [AllowlistItem(number, f"{key}:{item}") for item in found]
        unplaced.subtract((key, item) for item in found)
        if len(found) > 1:
            errors.append(
                f"{PYPROJECT}:{number}: {key} holds {len(found)} items on one line; write each "
                "alone on its own line, with its own marker"
            )
    for key, item in expected:
        if unplaced[(key, item)] > 0:
            unplaced[(key, item)] -= 1
            errors.append(
                f"{PYPROJECT}: {key} lists '{item}' on no line devctl can read; write it alone on "
                f"its own line under [tool.{_table_of(key)}]"
            )
    return items, errors


def _table_of(key: str) -> str:
    if key.startswith(f"{_RULE_TABLE}."):
        return _RULE_TABLE
    return _NAME_MAP if key == _NAME_MAP else key.rsplit(".", 1)[0]


def _parsed_items(data: Mapping[str, object]) -> Iterator[tuple[str, str]]:
    """(key name, item) for each allowlist item that tomllib reads, key by key."""
    tool = toml_table(data, "tool")
    for key in sorted(_ARRAYS, key=ALLOWLIST_KEYS.index):
        table, name = key.split(".")
        for item in toml_strings(toml_table(tool, table).get(name)):
            yield key, item
    for code, value in toml_table(tool, *_RULE_TABLE.split(".")).items():
        for item in toml_strings(value):
            yield f"{_RULE_TABLE}.{code}", item
    for distribution in toml_table(tool, *_NAME_MAP.split(".")):
        yield _NAME_MAP, distribution


def _scanned(text: str) -> Iterator[tuple[int, str, list[str]]]:
    """(line, key name, items) for each line of an allowlist array, and each name map key."""
    table, array = "", None  # the current table, without "tool."; the open array's key name
    # Split as the exceptions step splits, so the line numbers agree.
    for number, line in enumerate(text.split("\n"), start=1):
        if array is None:
            header = _header(line)
            if header is not None:
                table = header
                continue
            array = _opened(table, line)
            if array is None:
                if table == _NAME_MAP and (key := _MAP_KEY.match(line)):
                    yield number, _NAME_MAP, [_key(key["key"])]
                continue
        strings, code = _tokens(line)
        if '"""' not in line and "'''" not in line:
            yield number, array, [s for s in map(_decoded, strings) if s is not None]
        if "]" in code:
            array = None


def _header(line: str) -> str | None:
    """The table that a header line opens, without "tool."; None when the line is no header.

    A header devctl cannot read, such as one with a quoted key, opens no table it knows, so the
    items under it are reported as unplaced.
    """
    if not line.lstrip().startswith("["):
        return None
    header = _HEADER.fullmatch(line)
    name = re.sub(r"\s+", "", header["name"]) if header else ""
    return name.removeprefix("tool.") if name.startswith("tool.") else ""


def _opened(table: str, line: str) -> str | None:
    """The key name of the allowlist array that opens on this line, if one does."""
    opened = _ARRAY_OPEN.match(line)
    if opened is None:
        return None
    key = f"{table}.{opened['key']}"
    return key if key in _ARRAYS or table == _RULE_TABLE else None


def _tokens(line: str) -> tuple[list[str], str]:
    """The string tokens before the first # outside a string, and the text outside them."""
    strings: list[str] = []
    code, position = [], 0
    for token in _TOKEN.finditer(line):
        code.append(line[position : token.start()])
        position = token.end()
        if token.group() == "#":
            return strings, "".join(code)
        strings.append(token.group())
    return strings, "".join([*code, line[position:]])


def _key(token: str) -> str:
    """A key as TOML reads it: a bare key as written, a quoted one decoded."""
    decoded = _decoded(token) if token[:1] in ("'", '"') else None
    return token if decoded is None else decoded


def _decoded(token: str) -> str | None:
    """A TOML string token's value; None when TOML rejects it."""
    try:
        value = tomllib.loads(f"v = {token}")["v"]
    except tomllib.TOMLDecodeError:
        return None
    return value if isinstance(value, str) else None
