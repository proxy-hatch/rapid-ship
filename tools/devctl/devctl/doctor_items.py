"""What every doctor item shares: its type, its context, and the owner's one way to read GitHub.

doctor reads GitHub with the owner's gh sign-in, always as GET (gh api defaults to POST once it
is given a field).
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from devctl import process
from devctl.github.app import GitHubAccess
from devctl.harness import HarnessName
from devctl.process import ProcessResult
from devctl.settings import ROLES, ProjectSettings

Status = Literal["ok", "missing", "unknown"]
TOOL_TIMEOUT_SECONDS = 30.0
_GH_TIMEOUT_SECONDS = 60.0
_HTTP_STATUS = re.compile(r"\(HTTP (\d{3})\)")


@dataclass(frozen=True)
class Item:
    area: str  # toolchain, guardrails, kit, github, agent identity, skills
    name: str
    status: Status
    detail: str


OwnerGet = Callable[[str], object]  # GET with the owner's gh sign-in; raises OwnerReadError


class OwnerReadError(Exception):
    """gh could not read a path: its HTTP status when it printed one, and what it said."""

    def __init__(self, status: int | None, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class DoctorContext:
    root: Path
    project: ProjectSettings
    owner_get: OwnerGet
    access: GitHubAccess | None  # None while Agent identity is off


def harness_roles(project: ProjectSettings) -> dict[HarnessName, str]:
    """Each Harness the Roster names, with the roles that use it: "worker", "reviewer" or
    "worker and reviewer". Empty without a Roster."""
    roles: dict[HarnessName, list[str]] = {}
    for role in ROLES:
        agent = project.roster.get(role)
        if agent is not None:
            roles.setdefault(agent.harness, []).append(role)
    return {harness: " and ".join(names) for harness, names in roles.items()}


def _json_message(stdout: str) -> str:
    """The `message` of the JSON body that gh api printed for a failed request, or ""."""
    try:
        body = json.loads(stdout)
    except ValueError:
        return ""
    message = body.get("message") if isinstance(body, dict) else None
    return process.first_line(message) if isinstance(message, str) else ""


def gh_get(path: str) -> object:
    """GET path with the owner's gh sign-in and return the parsed JSON. Raises OwnerReadError."""
    try:
        result = process.run_process(
            ["gh", "api", "--method", "GET", path], Path(tempfile.gettempdir()), _GH_TIMEOUT_SECONDS
        )
    except OSError:  # gh is not installed, or cannot start
        raise OwnerReadError(None, "gh could not start") from None
    if result.timed_out:
        raise OwnerReadError(None, "gh api timed out")
    if result.stdout_truncated:
        raise OwnerReadError(None, f"gh api output exceeded {process.MAX_OUTPUT_BYTES} bytes")
    if result.returncode != 0:
        status = _HTTP_STATUS.search(result.stderr)
        message = _json_message(result.stdout) or process.first_line(result.stderr)
        raise OwnerReadError(
            int(status[1]) if status else None, message or f"gh api exited {result.returncode}"
        )
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise OwnerReadError(None, "gh api printed no JSON") from None


def run_installed(
    tool: str, *args: str, cwd: Path | None = None, timeout: float = TOOL_TIMEOUT_SECONDS
) -> ProcessResult | None:
    """Run an installed tool; None when it is not on PATH.

    A tool that cannot start gets exit 126, as a shell reports one.
    """
    path = shutil.which(tool)
    if path is None:
        return None
    argv = [path, *args]
    try:
        return process.run_process(argv, cwd or Path(tempfile.gettempdir()), timeout)
    except OSError:
        return ProcessResult(argv, 126, "", "", 0.0)


def finished(result: ProcessResult) -> bool:
    """False for a command that timed out or whose output was cut: it proves nothing."""
    return not (result.timed_out or result.stdout_truncated or result.stderr_truncated)
