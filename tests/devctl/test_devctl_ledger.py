"""Offline: ledger entries and last-pass.toml from literal texts."""

from datetime import date

import pytest

from devctl.ledger import Entry, LastPass, read_entry, read_last_pass

FILE = "docs/corrections/2026-10-16-env-read-1.md"
VALID = """date: 2026-10-16
by: reviewer
source: https://github.com/owner/name/pull/42#discussion_r1234567890
category: env-read-outside-settings
rungs: [1, 2]
prevention: Read configuration through settings.
status: open
pr: 42
path: src/app/links.py
"""


def entry_text(fields: str = VALID) -> str:
    return f"---\n{fields}---\nThe review required settings.\n"


def test_a_valid_entry_reads_every_field() -> None:
    assert read_entry(FILE, entry_text()) == Entry(
        file=FILE,
        date=date(2026, 10, 16),
        by="reviewer",
        source="https://github.com/owner/name/pull/42#discussion_r1234567890",
        category="env-read-outside-settings",
        rungs=(1, 2),
        prevention="Read configuration through settings.",
        status="open",
        pr=42,
        path="src/app/links.py",
    )


@pytest.mark.parametrize(
    ("old", "new", "field", "accepts"),
    [
        ("prevention: Read configuration through settings.\n", "", "prevention", "non-empty text"),
        ("", "owner: x\n", "owner", "allowed fields"),
        ("2026-10-16", "2026-10-16T05:00:00", "date", "date without a time"),
        ("by: reviewer", "by: bot", "by", "reviewer, human, incident"),
        (
            "https://github.com/owner/name/pull/42#discussion_r1234567890",
            "http://x",
            "source",
            "https://",
        ),
        ("env-read-outside-settings", "Env_Read", "category", "kebab-case"),
        *[
            ("rungs: [1, 2]", f"rungs: {value}", "rungs", "distinct integers from 1 to 4")
            for value in ("[]", "[1, 1]", "2", "[true]", "[5]")
        ],
        ("pr: 42", 'pr: "42"', "pr", "integer of at least 1"),
        ("status: open", "status: Open", "status", "open, proposed, implemented, rejected, closed"),
        ("status: open", "status: proposed", "task", "non-empty text"),
        ("status: open", "status: rejected", "reason", "non-empty text"),
        ("status: open", "status: closed", "reason", "non-empty text"),
        ("status: open", "status: implemented\nprevented_by: []", "prevented_by", "non-empty list"),
    ],
)
def test_each_invalid_field_names_what_it_accepts(
    old: str, new: str, field: str, accepts: str
) -> None:
    fields = new + VALID if not old else VALID.replace(old, new)
    result = read_entry(FILE, entry_text(fields))
    assert isinstance(result, list)
    assert any(problem.startswith(f"{FILE}: {field}:") and accepts in problem for problem in result)


def test_no_front_matter_and_all_field_problems_are_reported() -> None:
    assert isinstance(read_entry(FILE, "No front matter"), list)
    problems = read_entry(FILE, "---\nowner: x\n---\n")
    assert isinstance(problems, list)
    assert len(problems) == 8


@pytest.mark.parametrize(
    "text",
    [
        'through = "' + "a" * 40 + '"\ndate = 2026-10-16\nextra = 1',
        'through = "abc"\ndate = 2026-10-16',
        'through = "' + "a" * 40 + '"',
    ],
)
def test_last_pass_has_exactly_through_and_date(text: str) -> None:
    assert isinstance(read_last_pass(text), list)


def test_a_valid_last_pass() -> None:
    assert read_last_pass('through = "' + "a" * 40 + '"\ndate = 2026-10-16') == LastPass(
        "a" * 40, date(2026, 10, 16)
    )


def test_typed_fields_and_status_specific_fields_are_preserved() -> None:
    parsed = read_entry(FILE, entry_text())
    assert isinstance(parsed, Entry)
    assert parsed.by == "reviewer"
    assert parsed.category == "env-read-outside-settings"
    assert parsed.rungs == (1, 2)
    assert parsed.prevention == "Read configuration through settings."
    assert parsed.pr == 42
    proposed = read_entry(
        FILE,
        entry_text(
            VALID.replace("status: open", "status: proposed\ntask: https://tracker.example/task/1")
        ),
    )
    assert isinstance(proposed, Entry)
    assert proposed.task == "https://tracker.example/task/1"
    implemented = read_entry(
        FILE,
        entry_text(VALID.replace("status: open", "status: implemented\nprevented_by: [check:map]")),
    )
    assert isinstance(implemented, Entry)
    assert implemented.prevented_by == ("check:map",)
    closed = read_entry(
        FILE, entry_text(VALID.replace("status: open", "status: closed\nreason: Code removed"))
    )
    assert isinstance(closed, Entry)
    assert closed.reason == "Code removed"
