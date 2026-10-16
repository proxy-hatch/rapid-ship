"""doctor's Harness sign-ins: one item per Harness the Roster names.

claude and codex report their sign-in through their own status commands. agy has none, so doctor
asks it for a reply. Any sign-in method is ok: a subscription, an API key or a gateway is the
owner's choice of Provider (Spec 1 section 6). A detail never quotes the Harness's output, except
agy's error line, and doctor never reads a token file.
"""

from __future__ import annotations

import json
import re

from devctl import process
from devctl.doctor_items import Item, Status, finished, harness_roles, run_installed
from devctl.harness import (
    AGY_PROBE_ARGS,
    PROBE_MODELS,
    PROBE_TIMEOUT_SECONDS,
    SERVICE_ERROR,
    HarnessName,
    error_line,
)
from devctl.process import ProcessResult
from devctl.settings import ProjectSettings

_STATUS_COMMANDS = {"claude": ("auth", "status", "--json"), "codex": ("login", "status")}
# The first line of `codex login status` names the method, and an API key's line goes on to show
# part of the key, so a detail names only the method.
_CODEX_METHODS = (
    ("Logged in using ChatGPT", "ChatGPT"),
    ("Logged in using an API key", "an API key"),
)


def _sign_in(role: str, harness: str, status: Status, detail: str) -> Item:
    return Item("toolchain", f"{role} sign-in ({harness})", status, detail)


def _method_label(method: object) -> str:
    """An authMethod the detail may name: a short identifier, never free text."""
    if isinstance(method, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,32}", method):
        return method
    return "unreadable" if method is not None else "absent"


def claude_item(role: str, result: ProcessResult) -> Item:
    """Read `claude auth status --json`. Any authMethod is a sign-in; the detail names it."""
    try:
        data = json.loads(result.stdout) if finished(result) else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        return _sign_in(role, "claude", "unknown", "claude auth status gave no readable JSON")
    logged_in, method = data.get("loggedIn"), data.get("authMethod")
    if logged_in is True and result.returncode == 0:
        detail = f"signed in; authMethod is {_method_label(method)}"
        return _sign_in(role, "claude", "ok", detail)
    if logged_in is False and result.returncode == 1:
        return _sign_in(role, "claude", "missing", "not signed in; run claude auth login")
    detail = f"claude auth status exited {result.returncode}, which its answer contradicts"
    return _sign_in(role, "claude", "unknown", detail)


def _codex_method(first: str) -> str:
    for prefix, label in _CODEX_METHODS:
        if first.startswith(prefix):
            return label
    return "a method doctor does not name"


def codex_item(role: str, result: ProcessResult) -> Item:
    """Read the first line of `codex login status`, which codex writes to stderr."""
    first = process.first_line(result.stderr)
    if not finished(result):
        return _sign_in(role, "codex", "unknown", "codex login status did not finish")
    if first == "Not logged in":
        return _sign_in(role, "codex", "missing", "not signed in; run codex login")
    if first.startswith("Logged in using ") and result.returncode == 0:
        return _sign_in(role, "codex", "ok", f"signed in with {_codex_method(first)}")
    return _sign_in(
        role, "codex", "unknown", "codex login status gave an answer doctor cannot read"
    )


def agy_item(role: str, result: ProcessResult) -> Item:
    """Classify the agy probe. Exit 0 alone is not a sign-in: only a reply is (Checked facts)."""
    if result.timed_out:
        detail = f"agy did not finish within {PROBE_TIMEOUT_SECONDS:.0f} s"
        return _sign_in(role, "agy", "unknown", detail)
    if result.stdout_truncated or result.stderr_truncated:
        detail = f"agy printed more than {process.MAX_OUTPUT_BYTES} bytes"
        return _sign_in(role, "agy", "unknown", detail)
    service = next((ln for ln in result.stderr.splitlines() if SERVICE_ERROR.search(ln)), None)
    if service is not None:
        detail = (
            f"agy's service failed, not necessarily the sign-in: {service.strip()[:300]}; "
            "rerun ./devctl doctor"
        )
        return _sign_in(role, "agy", "unknown", detail)
    if result.returncode == 0 and result.stdout.strip():
        return _sign_in(role, "agy", "ok", f"signed in: agy answered on {PROBE_MODELS['agy']}")
    detail = f"agy gave no reply (exit {result.returncode})"
    error = error_line(result.stderr)
    return _sign_in(role, "agy", "missing", f"{detail}: {error}" if error else detail)


def agy_sign_in(role: str) -> Item:
    """Send `hi` to a new headless agy Session on the cheapest model, wherever doctor runs.

    Run inside another Harness's Session, that is a use Google's consumer terms do not support;
    rs-setup warns the owner before it runs doctor there (Spec 1 section 8, step 13).
    """
    result = run_installed("agy", *AGY_PROBE_ARGS, timeout=PROBE_TIMEOUT_SECONDS)
    if result is None:
        return _sign_in(role, "agy", "missing", "agy is not installed")
    return agy_item(role, result)


def _harness_sign_in(harness: HarnessName, role: str) -> Item:
    if harness == "agy":
        return agy_sign_in(role)
    result = run_installed(harness, *_STATUS_COMMANDS[harness])
    if result is None:
        return _sign_in(role, harness, "missing", f"{harness} is not installed")
    return (claude_item if harness == "claude" else codex_item)(role, result)


def sign_in_items(project: ProjectSettings) -> list[Item]:
    """One item per Harness the Roster names, named for the roles that use it; none without one."""
    return [_harness_sign_in(harness, roles) for harness, roles in harness_roles(project).items()]
