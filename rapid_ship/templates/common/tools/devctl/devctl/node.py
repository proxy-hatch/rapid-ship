"""Shared Node.js tool lookup, configuration and installation advice."""

import json
import os
from collections.abc import Mapping
from pathlib import Path

from devctl import process

ESLINT_PROBE = "src/index.ts"


def node_tool(directory: Path, name: str) -> Path | None:
    path = directory / "node_modules" / ".bin" / name
    return path.absolute() if path.is_file() and os.access(path, os.X_OK) else None


def install_advice(directory: Path) -> str:
    if (directory / "package-lock.json").exists():
        return "run npm ci there"
    return "run npm install there and commit package-lock.json"


def cannot_run(tool: str, label: str, reason: str, directory: Path) -> str:
    return f"cannot run {tool} in {label}: {reason}; {install_advice(directory)}"


def eslint_config(directory: Path) -> Mapping[str, object] | str:
    tool = node_tool(directory, "eslint")
    if tool is None:
        return "eslint is not installed"
    result = process.run_process([str(tool), "--print-config", ESLINT_PROBE], directory, 120)
    if result.timed_out:
        return "eslint timed out after 120 seconds"
    if result.returncode:
        lines = result.stderr.strip().splitlines()
        return f"eslint exited {result.returncode}: {lines[-1] if lines else ''}"
    try:
        value = json.loads(result.stdout)
    except ValueError:
        return "eslint printed no JSON object"
    return value if isinstance(value, dict) else "eslint printed no JSON object"


def is_error(severity: object) -> bool:
    if isinstance(severity, list):
        severity = severity[0] if severity else None
    return severity in (2, "error")
