"""The headless Sessions that doctor starts, and how it reads their output.

doctor spends a little of the owner's quota, whatever the Provider, to prove a sign-in, and with
--skills to ask which skills a Harness loads. Each Harness runs its cheapest model.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass

from devctl import process
from devctl.process import ProcessResult
from devctl.settings import Harness

HarnessName = Harness
# The cheapest model per Harness, as the Checked facts of plan 4 (Doctor and Agent identity)
# record it. That plan's live trial confirms each one.
PROBE_MODELS: dict[HarnessName, str] = {
    "claude": "haiku",
    "codex": "gpt-6-luna",
    "agy": "gemini-3.8-flash-low",
}
PROBE_TIMEOUT_SECONDS = 120.0
# agy has no sign-in status command, so doctor asks it for a reply. These are the arguments
# after the executable; --print-timeout ends the turn before PROBE_TIMEOUT_SECONDS does.
AGY_PROBE_ARGS: tuple[str, ...] = (
    "-p",
    "hi",
    "--model",
    PROBE_MODELS["agy"],
    "--print-timeout",
    "90s",
)
# Google's eligibility check failing, or the gateway behind it: the service, not the sign-in.
SERVICE_ERROR = re.compile(r"Eligibility check failed|\(code 50[234]\)")
_ERROR_PREFIXES = ("error:", "AGY_ERROR:")
SKILLS_PROMPT = "List the name of every skill you can load, one name per line, and nothing else."
_CODEX_EFFORT = 'model_reasoning_effort="low"'


def error_line(stderr: str) -> str | None:
    """The first stderr line that starts `error:` or `AGY_ERROR:`, cut to 300 characters."""
    for line in stderr.splitlines():
        if line.startswith(_ERROR_PREFIXES):
            return line[:300]
    return None


@dataclass(frozen=True)
class SkillReport:
    names: frozenset[str] | None  # None when the Session gave no skill list
    error: str | None  # why not, cut to 300 characters


def skills_args(harness: HarnessName) -> list[str]:
    """The arguments after the executable that make a new headless Session list its skills.

    A Harness that prints its own skill list is asked for that list; Codex has none, so its
    reply is the list.
    """
    model = PROBE_MODELS[harness]
    if harness == "claude":
        return [
            "-p",
            SKILLS_PROMPT,
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            model,
        ]
    if harness == "codex":
        return [
            "exec",
            "--json",
            "--model",
            model,
            "-c",
            _CODEX_EFFORT,
            "--sandbox",
            "read-only",
            "--ephemeral",
            SKILLS_PROMPT,
        ]
    return ["-p", "/skills", "--output-format", "json", "--model", model]


def _events(stdout: str) -> list[dict[str, object]]:
    """Each stdout line that is a JSON object, in order. Other lines are skipped."""
    found: list[dict[str, object]] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            found.append(event)
    return found


def _strings(value: object) -> list[str] | None:
    """value when it is a list of strings, else None."""
    if not isinstance(value, list):
        return None
    texts = [item for item in value if isinstance(item, str)]
    return texts if len(texts) == len(value) else None


def _reply_name(line: str) -> str:
    """One skill name from a reply line: without a bullet, backticks or a leading / or $."""
    name = line.strip()
    if name.startswith(("- ", "* ")):
        name = name[2:]
    name = name.strip().strip("`")
    if name[:1] in ("/", "$"):
        name = name[1:]
    return name.strip()


def _reply_names(text: str) -> frozenset[str]:
    """The names in a reply: one per non-empty line."""
    return frozenset(name for name in map(_reply_name, text.splitlines()) if name)


def _claude_skills(result: ProcessResult) -> SkillReport:
    """The `init` event's skills, else the final reply, else why there is neither."""
    events = _events(result.stdout)
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            listed = _strings(event.get("skills"))
            if listed is not None:
                return SkillReport(frozenset(listed), None)
    final = next((event for event in reversed(events) if event.get("type") == "result"), {})
    text = final.get("result")
    if final and final.get("is_error") is False and isinstance(text, str):
        return SkillReport(_reply_names(text), None)
    detail = process.first_line(text) if isinstance(text, str) else ""
    return SkillReport(None, detail or f"claude exited {result.returncode} with no skill list")


def _agent_message(event: dict[str, object]) -> str | None:
    item = event.get("item")
    if event.get("type") != "item.completed" or not isinstance(item, dict):
        return None
    text = item.get("text")
    return text if item.get("type") == "agent_message" and isinstance(text, str) else None


def _codex_error(events: list[dict[str, object]]) -> str | None:
    """A failed turn's message, else an error event's. Each is cut to 300 characters."""
    for event in events:
        failure = event.get("error") if event.get("type") == "turn.failed" else None
        message = failure.get("message") if isinstance(failure, dict) else None
        if isinstance(message, str) and message:
            return process.first_line(message)
    for event in events:
        message = event.get("message") if event.get("type") == "error" else None
        if isinstance(message, str) and message:
            return process.first_line(message)
    return None


def _codex_skills(result: ProcessResult) -> SkillReport:
    """The names in Codex's last agent message. No event lists skills (Checked facts)."""
    events = _events(result.stdout)
    replies = [text for text in map(_agent_message, events) if text is not None]
    if replies:
        return SkillReport(_reply_names(replies[-1]), None)
    detail = _codex_error(events) or f"codex exited {result.returncode} with no reply"
    return SkillReport(None, detail)


def _agy_names(listed: object) -> frozenset[str] | None:
    """The names in a JSON array of objects that each have a string name, else None."""
    if not isinstance(listed, list):
        return None
    names = [item.get("name") if isinstance(item, dict) else None for item in listed]
    texts = [name for name in names if isinstance(name, str)]
    return frozenset(texts) if len(texts) == len(names) else None


def _agy_skills(result: ProcessResult) -> SkillReport:
    """agy's `/skills`: a JSON array. It starts no agent turn (Checked facts)."""
    try:
        names = _agy_names(json.loads(result.stdout))
    except ValueError:
        names = None
    if names is not None:
        return SkillReport(names, None)
    detail = error_line(result.stderr) or f"agy printed no skill list (exit {result.returncode})"
    return SkillReport(None, detail)


_SKILL_PARSERS: dict[HarnessName, Callable[[ProcessResult], SkillReport]] = {
    "claude": _claude_skills,
    "codex": _codex_skills,
    "agy": _agy_skills,
}


def parse_skills(harness: HarnessName, result: ProcessResult) -> SkillReport:
    """The skills a headless Session listed, or why it listed none. Cut output is never a list."""
    if result.timed_out or result.stdout_truncated or result.stderr_truncated:
        detail = (
            f"{harness} did not finish within {PROBE_TIMEOUT_SECONDS:.0f} s, or its output was cut"
        )
        return SkillReport(None, detail)
    return _SKILL_PARSERS[harness](result)
