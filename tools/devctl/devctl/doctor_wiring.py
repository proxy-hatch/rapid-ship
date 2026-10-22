"""doctor's Harness wiring item: whether the Kit's .claude/settings.json runs devctl hook.

doctor reads only .claude/settings.json, the file the Kit seeds. .claude/settings.local.json and
the user's settings are the owner's own, so a hook or a disableAllHooks they hold is outside this
item. The item has a module of its own because doctor_rules.py imports doctor_local.py, so the
wiring rules there would make the two import each other.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from devctl.doctor_items import Item
from devctl.hook_protocols import HOOK_COMMAND, WIRED_TOOLS

WIRING_FILE = ".claude/settings.json"
_ITEM = "Harness wiring"
# Claude Code reads a matcher made only of these characters as a list of exact tool names, and
# any other matcher as a regular expression (its hooks reference, read 2026-10-21).
_NAME_LIST = re.compile(r"[A-Za-z0-9_\- ,|]*")
_NAME_SEPARATORS = re.compile(r"[|,]")
_QUOTES = re.compile(r"[\"']")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def _sequence(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _covers(matcher: object, tool: str) -> bool:
    """Whether a PreToolUse matcher covers tool: "*", "" or none covers every tool."""
    if matcher is None or matcher in ("", "*"):
        return True
    if not isinstance(matcher, str):
        return False
    if _NAME_LIST.fullmatch(matcher):
        return tool in (name.strip() for name in _NAME_SEPARATORS.split(matcher))
    try:
        return re.search(matcher, tool) is not None
    except re.error:  # doctor cannot tell what it covers, so it counts as covering nothing
        return False


def _runs_the_hook(hook: Mapping[str, object]) -> bool:
    """A command hook whose command and args run devctl hook claude pre-tool on every call.

    An async hook cannot block the call, and an if condition narrows the calls the hook runs on,
    so neither counts.
    """
    if hook.get("type") != "command" or hook.get("async") is True or "if" in hook:
        return False
    words = [hook.get("command"), *_sequence(hook.get("args"))]
    text = [word for word in words if isinstance(word, str)]
    return len(text) == len(words) and HOOK_COMMAND in _QUOTES.sub("", " ".join(text))


def wiring_problems(settings: object) -> list[str]:
    """Why parsed settings do not run devctl hook for each of WIRED_TOOLS; [] when they do.

    A tool is wired when a PreToolUse entry's matcher covers it and one of the entry's hooks runs
    the hook command.
    """
    fields = _mapping(settings)
    problems = []
    if fields.get("disableAllHooks") is True:
        problems.append("disableAllHooks is true, so no hook runs")
    entries = map(_mapping, _sequence(_mapping(fields.get("hooks")).get("PreToolUse")))
    matchers = [
        entry.get("matcher")
        for entry in entries
        if any(_runs_the_hook(_mapping(hook)) for hook in _sequence(entry.get("hooks")))
    ]
    unwired = [tool for tool in WIRED_TOOLS if not any(_covers(m, tool) for m in matchers)]
    if unwired:
        problems.append(f"no PreToolUse hook runs {HOOK_COMMAND} for {', '.join(unwired)}")
    return problems


def wiring_item(root: Path, tracked: Sequence[str]) -> Item:
    """Whether the tracked .claude/settings.json wires devctl hook for Claude Code (Spec 1
    section 6). A file it cannot read is unknown; an untracked or invalid one is missing."""
    if WIRING_FILE not in tracked:
        return Item("guardrails", _ITEM, "missing", f"{WIRING_FILE} is not tracked")
    try:
        settings = json.loads((root / WIRING_FILE).read_text(encoding="utf-8"))
    except OSError:
        return Item("guardrails", _ITEM, "unknown", f"cannot read {WIRING_FILE}")
    except ValueError:  # also bytes that are not UTF-8: UnicodeDecodeError
        return Item("guardrails", _ITEM, "missing", f"{WIRING_FILE} is not valid JSON")
    problems = wiring_problems(settings)
    if problems:
        return Item("guardrails", _ITEM, "missing", f"{WIRING_FILE}: {'; '.join(problems)}")
    detail = f"{WIRING_FILE} runs {HOOK_COMMAND} for {', '.join(WIRED_TOOLS)}"
    return Item("guardrails", _ITEM, "ok", detail)
