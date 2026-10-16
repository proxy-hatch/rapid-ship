"""devctl's typed view of .rapid-ship settings.

Unknown keys are errors, so a typo cannot silently keep a default. Every loader reads
one file and raises SettingsError, which devctl reports with exit 2.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Literal, cast, get_args

PROJECT = ".rapid-ship/project.toml"
EXCEPTIONS = ".rapid-ship/exceptions.toml"

Harness = Literal["claude", "codex", "agy"]  # Proposal: Spec 1 section 11, Roster Harnesses
Role = Literal["worker", "reviewer"]
Stack = Literal["python", "agnostic"]
ROLES: tuple[Role, ...] = ("worker", "reviewer")
# Tables the re-scope of 2026-10-16 removed, and what replaced each (Spec 1 section 4).
REMOVED_TABLES = {
    "agents": "name each role's Harness and exact model under [roster.worker] and "
    "[roster.reviewer] instead",
    "dispatch": "rapid-ship no longer starts Workers, and the Lead brief's Focus caps parallel "
    "Workers; delete the table",
    "linear": "devctl never talks to the issue tracker; delete the table",
    "release": "a project defines its own deploy metrics (Spec 3); delete the table",
}

_TABLES = {"stack", "github", "escalation", "roster", "kit", "map", "tests"}
_GITHUB_KEYS = {
    "repository",
    "worker_app_id",
    "worker_app_slug",
    "reviewer_app_id",
    "reviewer_app_slug",
}
_REPOSITORY = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*/(?!\.{1,2}$)[A-Za-z0-9._-]+")
_APP_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")  # the slugs GitHub gives Apps
_EXCEPTION_ID = re.compile(r"EX-[1-9][0-9]*")
_EXCEPTION_KEYS = ("id", "path", "rule", "reason", "remove_when")


class SettingsError(Exception):
    """A settings file is missing or invalid. devctl exits 2."""


@dataclass(frozen=True)
class Agent:
    harness: Harness
    model: str  # kept exactly


@dataclass(frozen=True)
class App:
    id: int  # [github] <role>_app_id; 0 in the file means unset
    slug: str  # [github] <role>_app_slug; Spec 3 matches agent PR authors against it


@dataclass(frozen=True)
class Escalation:
    every_pr: bool  # default True: Walk
    kinds: tuple[str, ...]  # plain text for the Lead
    revision_rounds: int  # default 3, at least 1


@dataclass(frozen=True)
class ProjectSettings:
    stack: Stack
    repository: str | None  # "owner/name"
    worker_app: App | None  # both Apps recorded, or neither; recorded Apps need repository
    reviewer_app: App | None
    escalation: Escalation
    roster: Mapping[Role, Agent]  # empty without a Roster
    optional_skills: tuple[str, ...]  # [kit] optional
    # [kit] exclude: Kit paths the project owns; a skill directory also covers its link.
    excluded: tuple[str, ...]
    source_roots: tuple[str, ...]  # [map] source_roots
    unguided: tuple[str, ...]  # [map] unguided
    # [map] exclude: directories whose AGENTS.md files are template content, not guides.
    map_exclude: tuple[str, ...]
    unit_tests: tuple[str, ...]  # [tests] unit; default ("tests/unit/**",)

    @property
    def agent_identity(self) -> bool:
        """On when both Apps are recorded; load_project accepts both or neither."""
        return self.worker_app is not None and self.reviewer_app is not None


@dataclass(frozen=True)
class ExceptionEntry:
    id: str  # "EX-<n>", n >= 1, unique
    path: str
    rule: str
    reason: str
    remove_when: str


class _Table:
    """One TOML table with known keys. Each accessor checks the value's type."""

    def __init__(self, value: object, where: str, keys: set[str]) -> None:
        if not isinstance(value, dict):
            raise SettingsError(f"{where}: expected a table")
        unknown = sorted(set(value) - keys)
        if unknown:
            raise SettingsError(f"{where}: unknown key {unknown[0]!r}")
        self.values: dict[str, object] = value
        self.where = where

    def table(self, key: str, keys: set[str]) -> _Table:
        return _Table(self.values.get(key, {}), f"{self.where} [{key}]", keys)

    def _error(self, key: str, expected: str) -> SettingsError:
        return SettingsError(f"{self.where} {key}: expected {expected}")

    def text(self, key: str, default: str = "") -> str:
        value = self.values.get(key, default)
        if not isinstance(value, str):
            raise self._error(key, "a string")
        return value

    def choice(self, key: str, options: tuple[str, ...], default: str | None = None) -> str:
        if key not in self.values and default is None:
            raise SettingsError(f"{self.where} {key}: required")
        value = self.values.get(key, default)
        if value not in options:
            raise self._error(key, " or ".join(options))
        return value

    def integer(self, key: str, default: int, minimum: int) -> int:
        value = self.values.get(key, default)
        # TOML true is a Python bool, which is also an int.
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise self._error(key, f"an integer of at least {minimum}")
        return value

    def boolean(self, key: str, default: bool) -> bool:
        value = self.values.get(key, default)
        if not isinstance(value, bool):
            raise self._error(key, "true or false")
        return value

    def texts(self, key: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
        value = self.values.get(key, list(default))
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise self._error(key, "a list of non-empty strings")
        return tuple(value)


def _read(root: Path, relative: str) -> dict[str, object]:
    try:
        return tomllib.loads((root / relative).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SettingsError(f"{relative}: missing; rapid-ship init seeds it") from None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SettingsError(f"{relative}: {error}") from error


def _inside_repository(entry: str) -> str | None:
    """The repository-relative POSIX path without "./" or a trailing "/", or None if it leaves."""
    path = PurePosixPath(entry)
    if not path.parts or path.is_absolute() or ".." in path.parts or "\\" in entry:
        return None
    return "/".join(path.parts)


def _agent(roster: _Table, role: Role) -> Agent | None:
    if role not in roster.values:
        return None
    table = roster.table(role, {"harness", "model"})
    harness = cast(Harness, table.choice("harness", get_args(Harness)))
    model = table.text("model")
    if not model or model.strip() != model:
        raise SettingsError(f"{table.where} model: required; record the exact model ID")
    return Agent(harness, model)


def _roster(top: _Table) -> Mapping[Role, Agent]:
    roster = top.table("roster", set(ROLES))
    found = {role: agent for role in ROLES if (agent := _agent(roster, role)) is not None}
    return MappingProxyType(found)


def _app(github: _Table, role: Role) -> App | None:
    """The role's App, or None when its ID is 0 and its slug empty."""
    app_id = github.integer(f"{role}_app_id", 0, minimum=0)
    slug = github.text(f"{role}_app_slug")
    if not app_id and not slug:
        return None
    if not app_id or not slug:
        raise SettingsError(
            f"{github.where}: {role}_app_id and {role}_app_slug go together; record both, "
            "as rapid-ship app prints them, or neither"
        )
    if not _APP_SLUG.fullmatch(slug):
        raise github._error(f"{role}_app_slug", "an App slug: lowercase letters, digits and -")
    return App(app_id, slug)


def _apps(github: _Table, repository: str | None) -> tuple[App | None, App | None]:
    """Both Apps, or neither: Agent identity is on or off, never half on."""
    worker, reviewer = _app(github, "worker"), _app(github, "reviewer")
    if (worker is None) != (reviewer is None):
        raise SettingsError(
            f"{github.where}: Agent identity needs both the Worker App and the Reviewer App; "
            "record both or neither"
        )
    if worker is not None and repository is None:
        raise SettingsError(
            f"{github.where}: Apps are recorded but repository is not; "
            'set repository = "owner/name"'
        )
    return worker, reviewer


def _escalation(top: _Table) -> Escalation:
    table = top.table("escalation", {"every_pr", "kinds", "revision_rounds"})
    return Escalation(
        every_pr=table.boolean("every_pr", True),
        kinds=table.texts("kinds"),
        revision_rounds=table.integer("revision_rounds", 3, minimum=1),
    )


def _exclude_paths(table: _Table) -> tuple[str, ...]:
    """A table's `exclude` list, normalised as rapid-ship's read_excluded does."""
    paths = [_inside_repository(entry) for entry in table.texts("exclude")]
    if None in paths:
        raise table._error("exclude", "paths inside the repository")
    return tuple(path for path in paths if path is not None)


def _refuse_removed(data: dict[str, object]) -> None:
    for name, replacement in REMOVED_TABLES.items():
        if name in data:
            raise SettingsError(f"{PROJECT}: [{name}] was removed: {replacement}")


def load_project(root: Path) -> ProjectSettings:
    data = _read(root, PROJECT)
    _refuse_removed(data)
    top = _Table(data, PROJECT, _TABLES)
    stack = cast(Stack, top.choice("stack", get_args(Stack)))
    github = top.table("github", _GITHUB_KEYS)
    kit = top.table("kit", {"optional", "exclude"})
    source_map = top.table("map", {"source_roots", "unguided", "exclude"})
    tests = top.table("tests", {"unit"})

    repository = github.text("repository") or None
    if repository is not None and not _REPOSITORY.fullmatch(repository):
        raise github._error("repository", "owner/name")
    worker_app, reviewer_app = _apps(github, repository)
    return ProjectSettings(
        stack=stack,
        repository=repository,
        worker_app=worker_app,
        reviewer_app=reviewer_app,
        escalation=_escalation(top),
        roster=_roster(top),
        optional_skills=kit.texts("optional"),
        excluded=_exclude_paths(kit),
        source_roots=source_map.texts("source_roots"),
        unguided=source_map.texts("unguided"),
        map_exclude=_exclude_paths(source_map),
        unit_tests=tests.texts("unit", ("tests/unit/**",)),
    )


def load_exceptions(root: Path) -> list[ExceptionEntry]:
    top = _Table(_read(root, EXCEPTIONS), EXCEPTIONS, {"exception"})
    items = top.values.get("exception", [])
    if not isinstance(items, list):
        raise top._error("exception", "a list of tables")
    entries: list[ExceptionEntry] = []
    for number, item in enumerate(items, start=1):
        row = _Table(item, f"{EXCEPTIONS} [[exception]] #{number}", set(_EXCEPTION_KEYS))
        fields = {key: row.text(key) for key in _EXCEPTION_KEYS}
        for key, value in fields.items():
            if not value.strip():
                raise SettingsError(f"{row.where} {key}: required")
        if not _EXCEPTION_ID.fullmatch(fields["id"]):
            raise row._error("id", "EX-<n>")
        if any(entry.id == fields["id"] for entry in entries):
            raise SettingsError(f"{row.where}: {fields['id']} is listed twice")
        if _inside_repository(fields["path"]) is None:
            raise row._error("path", "a path inside the repository")
        entries.append(ExceptionEntry(**fields))
    return entries
