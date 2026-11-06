"""Typed readers for Corrections entries and the gardening cursor."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import date as Date
from typing import cast

import yaml

from devctl.codeowners import LEDGER

LAST_PASS = LEDGER + "last-pass.toml"
STATUSES = ("open", "proposed", "implemented", "rejected", "closed")
WRITERS = ("reviewer", "human", "incident")
REQUIRED_FIELDS = ("date", "by", "source", "category", "rungs", "prevention", "status")
OPTIONAL_FIELDS = ("pr", "path", "task", "prevented_by", "reason")


@dataclass(frozen=True)
class Entry:
    file: str
    date: Date
    by: str
    source: str
    category: str
    rungs: tuple[int, ...]
    prevention: str
    status: str
    pr: int | None = None
    path: str | None = None
    task: str | None = None
    prevented_by: tuple[str, ...] = ()
    reason: str | None = None


@dataclass(frozen=True)
class LastPass:
    through: str
    date: Date


def _date(value: object) -> Date | None:
    if type(value) is Date:
        return value
    if isinstance(value, str):
        try:
            return Date.fromisoformat(value)
        except ValueError:
            pass
    return None


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _rungs(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(type(item) is int and 1 <= item <= 4 for item in value)
        and len(value) == len(set(value))
    )


def read_entry(file: str, text: str) -> Entry | list[str]:
    # check initializes map_ledger, which imports these public readers and dataclasses.
    from devctl.check.markdown import front_matter

    try:
        data = front_matter(text)
    except (ValueError, yaml.YAMLError) as error:
        return [f"{file}: front matter: {error}; use a YAML mapping between --- lines"]
    if not isinstance(data, dict):
        return [
            f"{file}: front matter: missing or not a mapping; use required fields "
            f"{', '.join(REQUIRED_FIELDS)} between --- lines"
        ]
    problems = [
        f"{file}: {key}: unknown field; allowed fields: "
        f"{', '.join((*REQUIRED_FIELDS, *OPTIONAL_FIELDS))}"
        for key in data
        if key not in (*REQUIRED_FIELDS, *OPTIONAL_FIELDS)
    ]
    day = _date(data.get("date"))
    checks = [
        ("date", day is not None, "a date without a time, as YAML date or ISO date text"),
        ("by", data.get("by") in WRITERS, ", ".join(WRITERS)),
        (
            "source",
            isinstance(data.get("source"), str)
            and (data["source"] == "session" or data["source"].startswith("https://")),
            "session or a URL starting with https://",
        ),
        (
            "category",
            isinstance(data.get("category"), str)
            and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["category"]) is not None,
            "a kebab-case name matching [a-z0-9]+(?:-[a-z0-9]+)*",
        ),
        ("rungs", _rungs(data.get("rungs")), "a non-empty list of distinct integers from 1 to 4"),
        ("prevention", _text(data.get("prevention")), "non-empty text naming the prevention"),
        ("status", data.get("status") in STATUSES, ", ".join(STATUSES)),
    ]
    if "pr" in data:
        checks.append(
            ("pr", type(data["pr"]) is int and data["pr"] >= 1, "an integer of at least 1")
        )
    for key, status in (("path", None), ("task", "proposed"), ("reason", "rejected")):
        required = data.get("status") == status if status else False
        required = required or (key == "reason" and data.get("status") == "closed")
        if key in data or required:
            checks.append((key, _text(data.get(key)), "non-empty text"))
    if "prevented_by" in data or data.get("status") == "implemented":
        items = data.get("prevented_by")
        checks.append(
            (
                "prevented_by",
                isinstance(items, list) and bool(items) and all(_text(item) for item in items),
                "a non-empty list of reference or repository path strings",
            )
        )
    problems.extend(
        f"{file}: {key}: {data.get(key)!r} is invalid or missing; use {allowed}"
        for key, valid, allowed in checks
        if not valid
    )
    if problems:
        return problems
    return Entry(
        file,
        cast("Date", day),
        data["by"],
        data["source"],
        data["category"],
        tuple(data["rungs"]),
        data["prevention"],
        data["status"],
        data.get("pr"),
        data.get("path"),
        data.get("task"),
        tuple(data.get("prevented_by", ())),
        data.get("reason"),
    )


def read_last_pass(text: str) -> LastPass | list[str]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        return [f"{LAST_PASS}: format: {error}; use TOML with exactly through and date"]
    problems = [
        f"{LAST_PASS}: {key}: unknown field; allowed fields: through, date"
        for key in data
        if key not in ("through", "date")
    ]
    through = data.get("through")
    day = _date(data.get("date"))
    if not isinstance(through, str) or re.fullmatch(r"[0-9a-fA-F]{40}", through) is None:
        problems.append(f"{LAST_PASS}: through: use a full 40-character hexadecimal commit SHA")
    if day is None:
        problems.append(
            f"{LAST_PASS}: date: use a date without a time, as TOML date or ISO date text"
        )
    return problems or LastPass(cast("str", through), cast("Date", day))
