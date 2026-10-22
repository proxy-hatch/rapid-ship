"""doctor's Harness wiring item: whether the Kit's .claude/settings.json runs devctl hook.

doctor reads only .claude/settings.json, the file the Kit seeds. .claude/settings.local.json and
the user's settings are the owner's own, so a hook or a disableAllHooks they hold is outside this
item. The item has a module of its own because doctor_rules.py imports doctor_local.py, so the
wiring rules there would make the two import each other.
"""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path

from devctl.doctor_items import Item
from devctl.hook_protocols import GUARD_BUDGET_SECONDS, HOOK_COMMAND, WIRED_TOOLS

WIRING_FILE = ".claude/settings.json"
_ITEM = "Harness wiring"
# Claude Code reads a matcher made only of these characters as a list of exact tool names, and
# any other matcher as a regular expression (its hooks reference, read 2026-10-21).
_NAME_LIST = re.compile(r"[A-Za-z0-9_\- ,|]*")
_NAME_SEPARATORS = re.compile(r"[|,]")
_QUOTES = re.compile(r"[\"']")
# Claude Code replaces only ${...} placeholders in an exec-form command.
_PLACEHOLDER = re.compile(r"\$\{[^}]*\}")
# A command hook with either field set to true runs in the background (hooks reference).
_BACKGROUND = ("async", "asyncRewake")
_PROGRAM, *_HOOK_ARGS = HOOK_COMMAND.split()
# The shortest timeout that leaves the merge guard its budget after the devctl shim has started
# uv and Python, which took 2.39 seconds on the hook spike's one cold run.
_SHORTEST_TIMEOUT = GUARD_BUDGET_SECONDS + 60.0
# A shell-form command as quoted strings, escapes and single characters, in order.
_SHELL_PIECE = re.compile(r"""'[^']*'|"(?:\\.|[^"\\])*"|\\.|.""", re.DOTALL)
_ESCAPE = re.compile(r"\\(.)", re.DOTALL)
_LITERAL_DOLLAR = "\x00"  # a $ that the shell keeps as it is, which no path to devctl holds


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
    """A command hook that runs devctl hook claude pre-tool, and nothing more, on every call.

    A hook with async or asyncRewake runs in the background, so it cannot block the call; an if
    condition narrows the calls the hook runs on; and a timeout below _SHORTEST_TIMEOUT lets
    Claude Code kill the merge guard before its budget ends. None of them counts.
    """
    if hook.get("type") != "command" or "if" in hook or not _waits(hook):
        return False
    if any(hook.get(field) is True for field in _BACKGROUND):
        return False
    words = _exec_words(hook) if "args" in hook else _shell_words(hook.get("command"))
    program, *args = words or [""]
    named = program == _PROGRAM or program.endswith(f"/{_PROGRAM}")
    return named and _LITERAL_DOLLAR not in program and args == _HOOK_ARGS


def _waits(hook: Mapping[str, object]) -> bool:
    """Whether Claude Code waits _SHORTEST_TIMEOUT for the hook: no timeout means 600 seconds."""
    timeout = hook.get("timeout", _SHORTEST_TIMEOUT)
    if isinstance(timeout, bool) or not isinstance(timeout, int | float):
        return False
    return timeout >= _SHORTEST_TIMEOUT


def _exec_words(hook: Mapping[str, object]) -> list[str] | None:
    """The words of an exec-form hook, one with args: Claude Code starts command with no shell
    and passes each args element as one word. It replaces only ${...} placeholders and keeps
    every quote and other "$" as it is, so a command that holds one names no file: None."""
    words = [hook.get("command"), *_sequence(hook.get("args"))]
    text = [word for word in words if isinstance(word, str)]
    if len(text) != len(words) or not text:
        return None
    if _QUOTES.search(text[0]) or "$" in _PLACEHOLDER.sub("", text[0]):
        return None
    return text


def _shell_words(command: object) -> list[str] | None:
    """The words of a shell-form command, split and unquoted as the shell does; None when it
    cannot be split. A $ in single quotes or after a backslash becomes _LITERAL_DOLLAR. An
    operator or a redirection stays a word, so the hook's command must stand alone."""
    if not isinstance(command, str):
        return None
    pieces = (piece[0] for piece in _SHELL_PIECE.finditer(command))
    try:
        return shlex.split("".join(map(_literal_dollars, pieces)))
    except ValueError:
        return None


def _literal_dollars(piece: str) -> str:
    """One piece of a shell-form command, with each $ that the shell keeps as _LITERAL_DOLLAR."""
    if piece.startswith("'"):
        return piece.replace("$", _LITERAL_DOLLAR)
    return _ESCAPE.sub(lambda found: _LITERAL_DOLLAR if found[1] == "$" else found[0], piece)


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
