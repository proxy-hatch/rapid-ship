"""The types devctl hook's rules share, and each wired Harness's hook protocol.

merge_guard.py uses the types too, and hook.py imports merge_guard.py, so the types live here
rather than in hook.py. read_event, answer and failure hold each Harness's own event and answer
format.

Exit codes, a workaround. devctl's convention, where exit 2 means "could not run", collides with
the Harnesses' hook protocols, and they disagree with each other. This mapping is the one place
that resolves it, and devctl hook never exits 2:

- Claude Code reads a hook's exit 2 as "block" and exit 1 as a non-blocking error. A deny or an
  ask is one line of JSON on stdout with exit 0, and no decision is no output with exit 0. An
  internal error, an event the hook cannot parse included, exits 1 with one stderr line, so the
  call goes through.
- agy blocks the call when its hook exits 1 or 2 or outlives its timeout. Every answer is one
  line of JSON with exit 0. No decision is "allow", which hands the call to agy's next hook or
  its own permission flow; it approves nothing. An internal error writes one stderr line and
  answers "allow" with that line as its reason, so the call goes through as in Claude Code.
- A missing or unknown Harness exits 1, because the hook cannot tell which protocol to answer
  in: register declares the Harness and the event as optional strings, because argparse would
  exit 2 on a choice it does not know.

The workaround holds only while devctl hook runs. Most failures before it decides let the call
through in Claude Code, but a failing uv exits 2, which blocks every wired call. In agy every
such failure, the shim's exit 127 included, blocks every wired call.
"""

from __future__ import annotations

import json
import os
import typing
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple

# None: no decision. The hook only denies or asks; it never allows.
Decision = Literal["deny", "ask"] | None
WiredHarness = Literal["claude", "agy"]
WIRED_HARNESSES: tuple[WiredHarness, ...] = typing.get_args(WiredHarness)


class _Input(NamedTuple):
    """Where read_event finds what a wired tool acts on."""

    key: str  # the field of the tool's input
    is_shell: bool  # True: the field is a command line; False: a path the tool writes


# The tools each Harness's seeded wiring sends to the hook, each with how read_event reads it.
# WIRED_TOOLS comes from this one table, so a tool cannot be wired without being read: a wired
# tool that read_event skipped would reach the rules as an empty ToolCall, a silent bypass.
_WIRED: dict[WiredHarness, dict[str, _Input]] = {
    # Monitor runs a shell command; MultiEdit is legacy, kept for versions that still have it.
    "claude": {
        "Bash": _Input("command", is_shell=True),
        "Edit": _Input("file_path", is_shell=False),
        "Write": _Input("file_path", is_shell=False),
        "MultiEdit": _Input("file_path", is_shell=False),
        "NotebookEdit": _Input("notebook_path", is_shell=False),
        "Monitor": _Input("command", is_shell=True),
    },
    # The names and arguments agy 1.4.7 sends. Its hooks page names write_to_file and
    # replace_file_content instead, which agy did not send.
    "agy": {
        "run_command": _Input("CommandLine", is_shell=True),
        "write_file": _Input("Path", is_shell=False),
        "edit_file": _Input("Path", is_shell=False),
    },
}
WIRED_TOOLS: Mapping[WiredHarness, tuple[str, ...]] = {
    harness: tuple(tools) for harness, tools in _WIRED.items()
}
HOOK_COMMANDS: Mapping[WiredHarness, str] = {
    harness: f"devctl hook {harness} pre-tool" for harness in WIRED_HARNESSES
}
# The Harnesses whose wiring runs G5. In agy's accept-edits mode an ask before a write shows no
# prompt and the write goes ahead.
PROTECTED_ASK: frozenset[WiredHarness] = frozenset({"claude"})
# Claude Code lets a call through when it kills a hook at its timeout, 600 seconds by default.
# The merge guard therefore denies before a read that could end past this budget, which every
# merge on a line shares.
GUARD_BUDGET_SECONDS = 300.0


@dataclass(frozen=True)
class ToolCall:
    """One Harness's pre-tool event, normalised."""

    shell: str | None  # the command line of a shell tool
    edits: tuple[Path, ...]  # the absolute, normalised paths a file-edit tool writes
    cwd: Path


@dataclass(frozen=True)
class HookSettings:
    """What the Protected-set and Agent identity rules and the merge guard read."""

    agent_identity: bool
    protected: tuple[str, ...]  # Protected-set patterns; empty without a CODEOWNERS file
    repository: str | None  # [github] repository
    reviewer_app_slug: str | None  # [github] reviewer_app_slug when Agent identity is on, else None


def read_event(harness: WiredHarness, payload: bytes) -> ToolCall:
    """The Harness's pre-tool event as a ToolCall. Raises ValueError when it is malformed.

    A wired tool's shell field is the command line, and its path field the one path it writes. A
    relative path is resolved against cwd, and every path is normalised lexically, without
    following symlinks, so a ".." cannot step past the kit.lock or Protected-set rules. Any other
    tool gives a call that no rule matches.
    """
    try:
        event = json.loads(payload)
    except ValueError as error:  # also bytes that are not UTF-8: UnicodeDecodeError
        raise ValueError(f"the event is not JSON: {error}") from error
    if not isinstance(event, dict):
        raise ValueError("the event is not a JSON object")
    cwd, tool, tool_input = _claude_call(event) if harness == "claude" else _agy_call(event)
    if not cwd.is_absolute():
        raise ValueError(f"the event's working directory is not an absolute path: {str(cwd)!r}")
    base = Path(os.path.normpath(cwd))
    wired = _WIRED[harness].get(tool)
    if wired is None:
        return ToolCall(None, (), base)
    value = _text(tool_input, wired.key, f"{tool}'s input")
    if wired.is_shell:
        return ToolCall(value, (), base)
    return ToolCall(None, (Path(os.path.normpath(base / value)),), base)


def _claude_call(event: Mapping[str, object]) -> tuple[Path, str, Mapping[str, object]]:
    """Claude Code's PreToolUse event: its cwd, tool_name and tool_input."""
    name = event.get("hook_event_name")
    if name != "PreToolUse":
        raise ValueError(f"the event's hook_event_name is {name!r}, not 'PreToolUse'")
    cwd = Path(_text(event, "cwd", "the event"))
    tool = _text(event, "tool_name", "the event")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        raise ValueError("the event has no tool_input object")
    return cwd, tool, tool_input


def _agy_call(event: Mapping[str, object]) -> tuple[Path, str, Mapping[str, object]]:
    """agy's event: the first of workspacePaths, which stands in for the cwd agy does not send,
    and toolCall's name and args."""
    paths = event.get("workspacePaths")
    if not isinstance(paths, list) or not paths or not isinstance(paths[0], str):
        raise ValueError("the event has no workspacePaths string")
    call = event.get("toolCall")
    if not isinstance(call, dict):
        raise ValueError("the event has no toolCall object")
    tool = _text(call, "name", "the event's toolCall")
    args = call.get("args")
    if not isinstance(args, dict):
        raise ValueError("the event's toolCall has no args object")
    return Path(paths[0]), tool, args


def _text(fields: Mapping[str, object], key: str, where: str) -> str:
    value = fields.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{where} has no {key} string")
    return value


def answer(harness: WiredHarness, decision: Decision, reason: str) -> tuple[str, int]:
    """The hook's stdout and exit code for a decision; the exit code is always 0."""
    if harness == "agy":
        return _agy_answer(decision or "allow", reason), 0
    if decision is None:
        return "", 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    return json.dumps(output) + "\n", 0


def failure(harness: WiredHarness, message: str) -> tuple[str, int]:
    """The hook's stdout and exit code when devctl cannot decide, so that the call goes through."""
    if harness == "agy":
        return _agy_answer("allow", message), 0
    return "", 1


def _agy_answer(decision: str, reason: str) -> str:
    fields = {"decision": decision, **({"reason": reason} if reason else {})}
    return json.dumps(fields) + "\n"
