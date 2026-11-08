"""Read-only metrics command and report assembly."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

from devctl.doctor_items import gh_get
from devctl.metrics.github import AllowanceUsedUp, GitHubError, GitHubReader
from devctl.metrics.model import NEEDS_IDENTITY, Measured, Population, judge
from devctl.metrics.red_merges import red_merges
from devctl.metrics.report import Report, exit_code, render_json, render_text
from devctl.metrics.revisions import revisions
from devctl.metrics.settings import MetricsSettingsError, gate_note, load_metrics
from devctl.metrics.window import MetricsError, Window, build_window, default_branch, resolve_tip
from devctl.repo import Repo, RepoError
from devctl.settings import ProjectSettings, SettingsError, load_project


def _measure(measure: Callable[[], Measured]) -> Measured:
    try:
        return measure()
    except AllowanceUsedUp as error:
        return Measured(None, error.reason())


def build_report(
    root: Path,
    project: ProjectSettings,
    window_size: int | None,
    reader: GitHubReader,
    now: Callable[[], datetime],
) -> Report:
    if project.repository is None:
        raise MetricsError(
            '[github] repository is not set in .rapid-ship/project.toml; set it to "owner/name"'
        )
    settings = load_metrics(root)
    repo = Repo.discover(root)
    branch = tip = None
    window: Window | None = None
    unavailable = None
    try:
        branch = default_branch(reader)
        tip = resolve_tip(repo, branch)
        login = f"{project.worker_app.slug}[bot]" if project.worker_app else None
        window = build_window(repo, reader, branch, tip, window_size or settings.window, login)
    except AllowanceUsedUp as error:
        unavailable = error.reason()
    if window is not None and not window.prs:
        unavailable = "no merged agent PRs yet" if project.agent_identity else "no merged PRs yet"
    population: Population = "agent" if project.agent_identity else "all"
    metrics = []
    for metric_id, title, function in (
        ("revisions", "Revisions", revisions),
        ("red_merges", "Red merges", red_merges),
    ):
        if unavailable is not None:
            measured = Measured(None, unavailable)
        elif metric_id == "revisions" and not project.agent_identity:
            measured = Measured(None, NEEDS_IDENTITY)
        elif window is not None:
            measured = _measure(partial(function, reader, window))
        else:
            raise MetricsError("window unavailable; rerun devctl metrics")
        metrics.append(
            judge(
                metric_id, title, "count", population, measured, settings.thresholds.get(metric_id)
            )
        )
    notes = []
    if note := gate_note(root):
        notes.append(note)
    if window is not None and window.not_fetched:
        notes.append(
            f"{window.not_fetched} merged PRs are not in origin/{branch} yet: "
            "run git fetch origin and rerun"
        )
    return Report(
        project.repository,
        now(),
        branch,
        tip,
        window,
        project.agent_identity,
        tuple(metrics),
        tuple(notes),
    )


def _command(args: argparse.Namespace) -> int:
    try:
        repo = Repo.discover(Path.cwd())
        project = load_project(repo.root)
        if project.repository is None:
            raise MetricsError(
                '[github] repository is not set in .rapid-ship/project.toml; set it to "owner/name"'
            )
        reader = GitHubReader(project.repository, get=gh_get)
        try:
            report = build_report(
                repo.root, project, args.window, reader, lambda: datetime.now(UTC)
            )
        except MetricsSettingsError as error:
            raise MetricsError(str(error)) from error
    except (SettingsError, MetricsError, GitHubError, RepoError) as error:
        sys.stderr.write(f"devctl metrics: {error}\n")
        return 2
    sys.stdout.write(render_json(report) if args.json else render_text(report))
    return exit_code(report)


def _positive(value: str) -> int:
    try:
        size = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("use an integer of at least 1") from None
    if size < 1:
        raise argparse.ArgumentTypeError("use an integer of at least 1")
    return size


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("metrics", help="Report Revisions and Red merges")
    parser.add_argument("--window", type=_positive, help="number of merged PRs, at least 1")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.set_defaults(handler=_command)
