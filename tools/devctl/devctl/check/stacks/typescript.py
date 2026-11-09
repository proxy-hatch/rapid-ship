"""TypeScript checks using the stack's installed tools and npm lock."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

from devctl.check.steps import (
    CheckContext,
    StepResult,
    Tier,
    blocked,
    command_result,
    run_tool,
)
from devctl.node import cannot_run, node_tool

LiteralAuditStatus = Literal["failed", "blocked"]

SOURCE_EXTENSIONS = (".ts", ".tsx")
KNIP_INCLUDE = (
    "files,dependencies,unlisted,binaries,unresolved,exports,types,enumMembers,namespaceMembers"
)


def _label(context: CheckContext) -> str:
    return context.stack.directory if context.stack else "."


@dataclass
class NodeStep:
    name: str
    tier: Tier
    argv: tuple[str, ...]
    failed_codes: frozenset[int]
    timeout_seconds: float = 1800.0

    def run(self, context: CheckContext) -> StepResult:
        tool = node_tool(context.directory, self.argv[0])
        if tool is None:
            return blocked(
                self.name,
                cannot_run(
                    self.argv[0],
                    _label(context),
                    f"{self.argv[0]} is not installed",
                    context.directory,
                ),
            )
        argv = (str(tool), *self.argv[1:])
        return command_result(
            self.name,
            argv,
            run_tool(context.directory, argv, self.timeout_seconds),
            self.failed_codes,
        )


FORMAT = NodeStep("format", "fast", ("prettier", "--check", "."), frozenset({1}))
LINT = NodeStep("lint", "fast", ("eslint", "--max-warnings", "0", "."), frozenset({1}))
TYPES = NodeStep("types", "full", ("tsc", "--noEmit"), frozenset({1, 2}))
DEAD_CODE = NodeStep("dead-code", "full", ("knip", "--include", KNIP_INCLUDE), frozenset({1}))
TESTS = NodeStep("tests", "full", ("vitest", "run"), frozenset({1}))


def _npm(context: CheckContext, name: str, argv: tuple[str, ...], timeout: float) -> StepResult:
    if not (context.directory / "package-lock.json").is_file():
        return blocked(
            name,
            cannot_run(
                " ".join(argv[:2]),
                _label(context),
                "there is no package-lock.json",
                context.directory,
            ),
        )
    result = run_tool(context.directory, argv, timeout)
    if result is None:
        return blocked(name, "npm is not on PATH; it comes with Node.js")
    if name == "audit" and result.returncode == 1 and not result.timed_out:
        report = _audit_report(result.stdout)
        if report is not None:
            status, details = report
            return StepResult(name, status, tuple(details))
    return command_result(name, argv, result, frozenset())


def _audit_report(text: str) -> tuple[LiteralAuditStatus, list[str]] | None:
    try:
        report = json.loads(text)
    except ValueError:
        return None
    if not isinstance(report, dict):
        return None
    error = report.get("error")
    if isinstance(error, dict):
        return "blocked", [f"npm audit: {error.get('code', '')} {error.get('summary', '')}"]
    vulnerabilities = report.get("vulnerabilities")
    if not isinstance(vulnerabilities, dict) or not vulnerabilities:
        return None
    lines = []
    for name, value in sorted(vulnerabilities.items()):
        if not isinstance(value, dict) or not isinstance(value.get("via"), list):
            return None
        titles = [
            item.get("title", "") if isinstance(item, dict) else str(item) for item in value["via"]
        ]
        lines.append(f"{name} {value.get('severity', '')}: {'; '.join(titles)}")
    return "failed", lines


class AuditStep:
    name = "audit"
    tier: Tier = "full"

    def run(self, context: CheckContext) -> StepResult:
        return _npm(context, self.name, ("npm", "audit", "--json"), 600)


class InstallStep:
    name = "install"
    tier: Tier = "fast"

    def run(self, context: CheckContext) -> StepResult:
        return _npm(context, self.name, ("npm", "ci", "--no-audit", "--no-fund"), 1200)
