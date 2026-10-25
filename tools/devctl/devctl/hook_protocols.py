"""The types devctl hook's rules share, and each wired Harness's hook protocol.

merge_guard.py uses the types too, and hook.py imports merge_guard.py, so the types live here
rather than in hook.py. read_event and answer hold each Harness's own event and answer format.

Exit codes, a workaround (Spec 1 section 4). devctl's convention, where exit 2 means "could not
run", collides with Claude Code's hook protocol, which reads a hook's exit 2 as "block". This
mapping is the one place that resolves it, and devctl hook never exits 2:

- a deny or an ask is one line of JSON on stdout with exit 0, and no decision is no output with
  exit 0, so the decision never rides on an exit code;
- an internal error, an event the hook cannot parse included, exits 1 with one stderr line.
  Claude Code treats exit 1 as a non-blocking error, so the call goes through, as the hook spike
  observed;
- a missing or unknown Harness or event is exit 1 too: register declares them as optional
  strings, because argparse would exit 2 on a choice it does not know.

The workaround holds only while devctl hook runs. Spec 1 section 4, "When the hook fails before
it decides", lists the other cases: most let the call through, and a failing uv exits 2, which
blocks every wired call.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NamedTuple

# None: no decision. The hook only denies or asks; it never allows (Spec 1 section 4).
Decision = Literal["deny", "ask"] | None
WiredHarness = Literal["claude"]  # each later wiring adds its Harness and protocol


class _Input(NamedTuple):
    """Where read_event finds what a wired tool acts on."""

    key: str  # the tool_input field
    is_shell: bool  # True: the field is a command line; False: a path the tool writes


# The tools Claude Code's seeded wiring sends to the hook (Spec 1 section 4), each with how
# read_event reads it. WIRED_TOOLS comes from this one table, so a tool cannot be wired without
# being read: a wired tool that read_event skipped would reach the rules as an empty ToolCall, a
# silent bypass. Monitor runs a shell command; MultiEdit is legacy, kept for versions that still
# have it.
_WIRED: dict[str, _Input] = {
    "Bash": _Input("command", is_shell=True),
    "Edit": _Input("file_path", is_shell=False),
    "Write": _Input("file_path", is_shell=False),
    "MultiEdit": _Input("file_path", is_shell=False),
    "NotebookEdit": _Input("notebook_path", is_shell=False),
    "Monitor": _Input("command", is_shell=True),
}
WIRED_TOOLS = tuple(_WIRED)
HOOK_COMMAND = "devctl hook claude pre-tool"
# Claude Code lets a call through when it kills a hook at its timeout, 600 seconds by default, as
# the hook spike recorded. The merge guard therefore denies before a read that could end past this
# budget, which every merge on a line shares.
GUARD_BUDGET_SECONDS = 300.0


@dataclass(frozen=True)
class ToolCall:
    """One Harness's pre-tool event, normalised."""

    shell: str | None  # the command line of a shell tool
    edits: tuple[Path, ...]  # the absolute, normalised paths a file-edit tool writes
    cwd: Path


@dataclass(frozen=True)
class HookSettings:
    """What G5, G7, G8 and the merge guard read from the repository."""

    agent_identity: bool
    protected: tuple[str, ...]  # Protected-set patterns; empty without a CODEOWNERS file
    repository: str | None  # [github] repository
    reviewer_app_slug: str | None  # [github] reviewer_app_slug when Agent identity is on, else None


def read_event(harness: WiredHarness, payload: bytes) -> ToolCall:
    """Claude Code's PreToolUse event as a ToolCall. Raises ValueError when it is malformed.

    Bash's and Monitor's tool_input.command is the command line. Edit, Write and MultiEdit write
    tool_input.file_path, and NotebookEdit tool_input.notebook_path. A relative path is resolved
    against cwd, and every path is normalised lexically, without following symlinks, so a ".."
    cannot step past G4 or G5. Any other tool gives a call that no rule matches.
    """
    try:
        event = json.loads(payload)
    except ValueError as error:  # also bytes that are not UTF-8: UnicodeDecodeError
        raise ValueError(f"the event is not JSON: {error}") from error
    if not isinstance(event, dict):
        raise ValueError("the event is not a JSON object")
    name = event.get("hook_event_name")
    if name != "PreToolUse":
        raise ValueError(f"the event's hook_event_name is {name!r}, not 'PreToolUse'")
    cwd = Path(_text(event, "cwd", "the event"))
    if not cwd.is_absolute():
        raise ValueError(f"the event's cwd is not an absolute path: {str(cwd)!r}")
    tool = _text(event, "tool_name", "the event")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        raise ValueError("the event has no tool_input object")
    base = Path(os.path.normpath(cwd))
    wired = _WIRED.get(tool)
    if wired is None:
        return ToolCall(None, (), base)
    value = _text(tool_input, wired.key, f"{tool}'s tool_input")
    if wired.is_shell:
        return ToolCall(value, (), base)
    return ToolCall(None, (Path(os.path.normpath(base / value)),), base)


def _text(fields: Mapping[str, object], key: str, where: str) -> str:
    value = fields.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{where} has no {key} string")
    return value


def answer(harness: WiredHarness, decision: Decision, reason: str) -> tuple[str, int]:
    """The hook's stdout and exit code: one JSON line for a deny or an ask, nothing for none."""
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
