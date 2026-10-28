"""doctor's Harness wiring items: whether the Kit's .claude/settings.json and .agents/hooks.json
run devctl hook.

doctor reads only the files the Kit seeds. .claude/settings.local.json, the user's settings and
agy's user-level hooks are the owner's own, so a hook or a disableAllHooks they hold is outside
these items. The items have a module of their own because doctor_rules.py imports
doctor_local.py, so the wiring rules there would make the two import each other.
"""

from __future__ import annotations

import json
import re
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path

from devctl import process
from devctl.doctor_items import TOOL_TIMEOUT_SECONDS, Item, finished, owner_environment
from devctl.hook_protocols import GUARD_BUDGET_SECONDS, HOOK_COMMANDS, WIRED_TOOLS

WIRING_FILE = ".claude/settings.json"
AGY_WIRING_FILE = ".agents/hooks.json"
_ITEM = "Claude Code wiring"
_AGY_ITEM = "agy wiring"
# Claude Code reads a matcher made only of these characters as a list of exact tool names, and
# any other matcher as a regular expression (its hooks reference, read 2026-10-21).
_NAME_LIST = re.compile(r"[A-Za-z0-9_\- ,|]*")
_NAME_SEPARATORS = re.compile(r"[|,]")
_QUOTES = re.compile(r"[\"']")
# Claude Code replaces only ${...} placeholders in an exec-form command.
_PLACEHOLDER = re.compile(r"\$\{[^}]*\}")
# A command hook with either field set to true runs in the background (hooks reference).
_BACKGROUND = ("async", "asyncRewake")
_HOOK_COMMAND = HOOK_COMMANDS["claude"]
_PROGRAM, *_HOOK_ARGS = _HOOK_COMMAND.split()
_AGY_HOOK_ARGS = HOOK_COMMANDS["agy"].split()[1:]
# The shortest timeout that leaves the merge guard its budget after the devctl shim has started
# uv and Python, which took 2.39 seconds in one measured cold run.
_SHORTEST_TIMEOUT = GUARD_BUDGET_SECONDS + 60.0
_AGY_DEFAULT_TIMEOUT = 30.0  # what agy waits for a hook that sets no timeout
# The probe's command, which G2 denies whatever the settings say.
_PROBE_COMMAND = "git push --force"
# A shell-form command as quoted strings, escapes and single characters, in order.
_SHELL_PIECE = re.compile(r"""'[^']*'|"(?:\\.|[^"\\])*"|\\.|.""", re.DOTALL)
_ESCAPE = re.compile(r"\\(.)", re.DOTALL)
_LITERAL_DOLLAR = "\x00"  # a $ that the shell keeps as it is, which no path to devctl holds
# A shell-form program word after quote removal: path characters, $NAME and ${NAME}. shlex.split
# does not split at an operator, so false&&, #, X= or other punctuation can stand before the path
# in that word, and the shell then runs something else. A space survives only inside quotes.
_PATH_CHARACTERS = r"(?:[\w./~ -]|\$[A-Za-z_]\w*|\$\{[A-Za-z_]\w*\})*"
_PATH_WORD = re.compile(_PATH_CHARACTERS)
# agy runs its hooks in .agents/, so its program word may start with git's top level. No other
# command substitution passes the agy item, and the Claude Code item accepts none.
_AGY_PATH_WORD = re.compile(r"(?:\$\(git rev-parse --show-toplevel\))?" + _PATH_CHARACTERS)


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
    if hook.get("type") != "command" or "if" in hook or not _waits(hook, _SHORTEST_TIMEOUT):
        return False
    if any(hook.get(field) is True for field in _BACKGROUND):
        return False
    words = _exec_words(hook) if "args" in hook else _shell_words(hook.get("command"), _PATH_WORD)
    return _names_the_hook(words, _HOOK_ARGS)


def _names_the_hook(words: list[str] | None, hook_args: list[str]) -> bool:
    """Whether words are devctl, or a path that ends in /devctl, then exactly hook_args."""
    program, *args = words or [""]
    named = program == _PROGRAM or program.endswith(f"/{_PROGRAM}")
    return named and args == hook_args


def _waits(hook: Mapping[str, object], default: float) -> bool:
    """Whether the Harness waits _SHORTEST_TIMEOUT for the hook; default is its timeout when the
    hook sets none."""
    timeout = hook.get("timeout", default)
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


def _shell_words(command: object, program_word: re.Pattern[str]) -> list[str] | None:
    """The words of a shell-form command, split and unquoted as the shell does; None when it
    cannot be split, or when its program word does not match program_word. A $ in single quotes
    or after a backslash becomes _LITERAL_DOLLAR, which no path holds. An operator or a
    redirection after the program stays a word, so the hook's command must stand alone."""
    if not isinstance(command, str):
        return None
    pieces = (piece[0] for piece in _SHELL_PIECE.finditer(command))
    try:
        words = shlex.split("".join(map(_literal_dollars, pieces)))
    except ValueError:
        return None
    return words if words and program_word.fullmatch(words[0]) else None


def _literal_dollars(piece: str) -> str:
    """One piece of a shell-form command, with each $ that the shell keeps as _LITERAL_DOLLAR."""
    if piece.startswith("'"):
        return piece.replace("$", _LITERAL_DOLLAR)
    return _ESCAPE.sub(lambda found: _LITERAL_DOLLAR if found[1] == "$" else found[0], piece)


def wiring_problems(settings: object) -> list[str]:
    """Why parsed settings do not run devctl hook for each of WIRED_TOOLS; [] when they do."""
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
    unwired = [
        tool for tool in WIRED_TOOLS["claude"] if not any(_covers(m, tool) for m in matchers)
    ]
    if unwired:
        problems.append(f"no PreToolUse hook runs {_HOOK_COMMAND} for {', '.join(unwired)}")
    return problems


def _load(root: Path, path: str, tracked: Sequence[str], name: str) -> object:
    """The parsed JSON of a tracked wiring file, or the Item that says why there is none: a file
    doctor cannot read is unknown, and an untracked or invalid one is missing."""
    if path not in tracked:
        return Item("guardrails", name, "missing", f"{path} is not tracked")
    try:
        return json.loads((root / path).read_text(encoding="utf-8"))
    except OSError:
        return Item("guardrails", name, "unknown", f"cannot read {path}")
    except ValueError:  # also bytes that are not UTF-8: UnicodeDecodeError
        return Item("guardrails", name, "missing", f"{path} is not valid JSON")


def wiring_item(root: Path, tracked: Sequence[str]) -> Item:
    """Whether the tracked .claude/settings.json wires devctl hook for Claude Code."""
    settings = _load(root, WIRING_FILE, tracked, _ITEM)
    if isinstance(settings, Item):
        return settings
    problems = wiring_problems(settings)
    if problems:
        return Item("guardrails", _ITEM, "missing", f"{WIRING_FILE}: {'; '.join(problems)}")
    detail = f"{WIRING_FILE} runs {_HOOK_COMMAND} for {', '.join(WIRED_TOOLS['claude'])}"
    return Item("guardrails", _ITEM, "ok", detail)


def _agy_covers(matcher: object, tool: str) -> bool:
    """Whether an agy matcher covers tool. "" and "*" cover every tool; any other matcher covers
    it only as a whole match, so it does whether or not agy anchors the regular expression."""
    if matcher in ("", "*"):
        return True
    if not isinstance(matcher, str):
        return False
    try:
        return re.fullmatch(matcher, tool) is not None
    except re.error:  # doctor cannot tell what it covers, so it counts as covering nothing
        return False


def _runs_agy_hook(hook: Mapping[str, object]) -> bool:
    """A command handler that runs devctl hook agy pre-tool, and nothing more, and that agy waits
    _SHORTEST_TIMEOUT for. agy blocks the call when it kills a hook at its timeout, so a shorter
    timeout blocks a merge that the guard is still checking."""
    if hook.get("type") != "command" or not _waits(hook, _AGY_DEFAULT_TIMEOUT):
        return False
    return _names_the_hook(_shell_words(hook.get("command"), _AGY_PATH_WORD), _AGY_HOOK_ARGS)


def _agy_handlers(hooks: object) -> list[tuple[object, str]]:
    """(matcher, command) for each PreToolUse handler that runs devctl hook agy pre-tool, in each
    named hook whose enabled is absent or true."""
    return [
        (entry.get("matcher"), str(handler["command"]))
        for named in map(_mapping, _mapping(hooks).values())
        if named.get("enabled", True) is True
        for entry in map(_mapping, _sequence(named.get("PreToolUse")))
        for handler in map(_mapping, _sequence(entry.get("hooks")))
        if _runs_agy_hook(handler)
    ]


def agy_wiring_problems(hooks: object) -> list[str]:
    """Why parsed hooks do not run devctl hook agy pre-tool for each of agy's wired tools; [] when
    they do."""
    matchers = [matcher for matcher, _ in _agy_handlers(hooks)]
    unwired = [
        tool for tool in WIRED_TOOLS["agy"] if not any(_agy_covers(m, tool) for m in matchers)
    ]
    if not unwired:
        return []
    return [f"no PreToolUse hook runs {HOOK_COMMANDS['agy']} for {', '.join(unwired)}"]


def agy_wiring_item(root: Path, tracked: Sequence[str]) -> Item:
    """Whether the tracked .agents/hooks.json wires devctl hook for agy, and whether each of its
    wired commands denies a probe force push. agy blocks every call a failing hook is wired for,
    so doctor runs each command as agy does, and the first that does not deny decides."""
    hooks = _load(root, AGY_WIRING_FILE, tracked, _AGY_ITEM)
    if isinstance(hooks, Item):
        return hooks
    problems = agy_wiring_problems(hooks)
    if problems:
        return Item("guardrails", _AGY_ITEM, "missing", f"{AGY_WIRING_FILE}: {'; '.join(problems)}")
    commands = dict.fromkeys(command for _, command in _agy_handlers(hooks))
    items = [_probe_item(root, command) for command in commands]
    return next((item for item in items if item.status != "ok"), items[0])


def _probe_item(root: Path, command: str) -> Item:
    """Run command as agy runs a hook, through sh in the folder that holds hooks.json, on a
    run_command event for _PROBE_COMMAND."""
    call = {"name": "run_command", "args": {"CommandLine": _PROBE_COMMAND}}
    event = json.dumps({"toolCall": call, "workspacePaths": [str(root)]})
    try:
        result = process.run_process(
            ["/bin/sh", "-c", command],
            (root / AGY_WIRING_FILE).parent,
            TOOL_TIMEOUT_SECONDS,
            env=owner_environment("devctl"),
            input_text=event,
        )
    except OSError:
        return Item("guardrails", _AGY_ITEM, "unknown", f"cannot run the hook of {AGY_WIRING_FILE}")
    if not finished(result):
        detail = (
            f"its hook gave no answer to a probe event within {TOOL_TIMEOUT_SECONDS:.0f} seconds"
        )
        return Item("guardrails", _AGY_ITEM, "unknown", f"{AGY_WIRING_FILE}: {detail}")
    if result.returncode != 0:
        detail = (
            f"its hook exited {result.returncode} on a probe event, so agy would block every call "
            "it is wired for"
        )
        return Item("guardrails", _AGY_ITEM, "missing", f"{AGY_WIRING_FILE}: {detail}")
    if not _denies_with_g2(result.stdout):
        detail = f"its hook did not deny a probe {_PROBE_COMMAND} with G2"
        return Item("guardrails", _AGY_ITEM, "missing", f"{AGY_WIRING_FILE}: {detail}")
    detail = (
        f"{AGY_WIRING_FILE} runs {HOOK_COMMANDS['agy']} for {', '.join(WIRED_TOOLS['agy'])}, and "
        f"it denied a probe {_PROBE_COMMAND}"
    )
    return Item("guardrails", _AGY_ITEM, "ok", detail)


def _denies_with_g2(stdout: str) -> bool:
    try:
        answer = json.loads(stdout)
    except ValueError:
        return False
    reason = _mapping(answer).get("reason")
    return _mapping(answer).get("decision") == "deny" and str(reason).startswith("G2: ")
