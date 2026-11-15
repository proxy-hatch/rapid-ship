"""The metrics command and report assembly. Only --post writes to GitHub."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path

from devctl.doctor_items import gh_get
from devctl.metrics.api import IncidentMetric, Metric, MetricContext
from devctl.metrics.github import AllowanceUsedUp, GitHubError, GitHubReader
from devctl.metrics.model import NEEDS_IDENTITY, Kind, Measured, MetricReport, Population, judge
from devctl.metrics.post import PostTarget, gh_write, post, prepare_post, status_changes
from devctl.metrics.project import measure, project_metrics
from devctl.metrics.red_merges import red_merges
from devctl.metrics.report import Report, exit_code, render_json, render_text
from devctl.metrics.reverts import reverts
from devctl.metrics.revisions import revisions
from devctl.metrics.settings import (
    IssuesSource,
    MetricsSettings,
    MetricsSettingsError,
    SettingsMetric,
    gate_note,
    load_metrics,
)
from devctl.metrics.sources import count_deployments, count_issues
from devctl.metrics.window import MetricsError, Window, build_window, default_branch, resolve_tip
from devctl.repo import Repo, RepoError
from devctl.settings import ProjectSettings, SettingsError, load_project


def _measure(measure: Callable[[], Measured]) -> Measured:
    try:
        return measure()
    except AllowanceUsedUp as error:
        return Measured(None, error.reason())


def _source(
    repo: Repo, reader: GitHubReader, metric: SettingsMetric, span: MetricContext
) -> Measured:
    source = metric.source
    try:
        if isinstance(source, IssuesSource):
            return count_issues(reader, source.label, span.since, span.until)
        return count_deployments(
            repo, reader, source.environment, source.count, span.since, span.until
        )
    except AllowanceUsedUp as error:
        return Measured(None, error.reason())
    except GitHubError as error:
        return Measured(None, str(error))


def _project_reports(
    settings: MetricsSettings,
    code_metrics: Sequence[Metric],
    repo: Repo,
    reader: GitHubReader,
    window: Window | None,
    unavailable: str | None,
    until: datetime,
) -> list[MetricReport]:
    """Project-defined metrics, settings sources first, each unknown when no span is available."""
    span = None
    if unavailable is None and window is not None and window.since is not None:
        prs = tuple(pr.number for pr in window.prs)
        span = MetricContext(reader.repository, window.since, until, prs, reader.get)
    reason = unavailable or "window unavailable; rerun devctl metrics"

    def judged(metric_id: str, title: str, kind: Kind, measured: Measured) -> MetricReport:
        threshold = settings.thresholds.get(metric_id)
        return judge(metric_id, title, kind, "repository", measured, threshold)

    reports = []
    for metric in settings.metrics:
        measured = Measured(None, reason) if span is None else _source(repo, reader, metric, span)
        reports.append(judged(metric.metric_id, metric.title, "count", measured))
    for code in code_metrics:
        kind: Kind = "incident" if isinstance(code, IncidentMetric) else "count"
        measured = Measured(None, reason) if span is None else measure(code, span, reader)
        reports.append(judged(code.id, code.title, kind, measured))
    return reports


def _known(window: Window | None) -> Window:
    if window is None:
        raise MetricsError("window unavailable; rerun devctl metrics")
    return window


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
    repository = project.repository  # a local keeps its narrowed type inside the rows' lambdas
    code_metrics = project_metrics()
    settings = load_metrics(root, [metric.id for metric in code_metrics])
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
    rows: tuple[tuple[str, str, Callable[[], Measured]], ...] = (
        ("revisions", "Revisions", lambda: revisions(reader, _known(window))),
        ("reverts", "Reverts", lambda: reverts(repo, _known(window), repository)),
        ("red_merges", "Red merges", lambda: red_merges(reader, _known(window))),
    )
    for metric_id, title, measure_row in rows:
        if unavailable is not None:
            measured = Measured(None, unavailable)
        elif metric_id == "revisions" and not project.agent_identity:
            measured = Measured(None, NEEDS_IDENTITY)
        else:
            measured = _measure(measure_row)
        metrics.append(
            judge(
                metric_id, title, "count", population, measured, settings.thresholds.get(metric_id)
            )
        )
    metrics.extend(
        _project_reports(settings, code_metrics, repo, reader, window, unavailable, now())
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


def _require_actions() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true" or not os.environ.get("GH_TOKEN"):
        raise MetricsError(
            "--post runs only in GitHub Actions with GH_TOKEN set; "
            "run ./devctl metrics without it to read the report"
        )


def _publish(report: Report, target: PostTarget) -> int:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    url = post(report, target, gh_write, Path(summary) if summary else None)
    changes = status_changes(target.previous, report)
    sys.stdout.write("".join(f"{line}\n" for line in (url, *changes)))
    return 0  # a breach is the report's finding, and posting it is the whole response


def _command(args: argparse.Namespace) -> int:
    try:
        if args.post:
            _require_actions()
        repo = Repo.discover(Path.cwd())
        project = load_project(repo.root)
        if project.repository is None:
            raise MetricsError(
                '[github] repository is not set in .rapid-ship/project.toml; set it to "owner/name"'
            )
        reader = GitHubReader(project.repository, get=gh_get)
        target = prepare_post(reader) if args.post else None
        try:
            report = build_report(
                repo.root, project, args.window, reader, lambda: datetime.now(UTC)
            )
        except MetricsSettingsError as error:
            raise MetricsError(str(error)) from error
        if target is not None:
            return _publish(report, target)
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
    parser = commands.add_parser("metrics", help="Report metrics for the last merged pull requests")
    parser.add_argument("--window", type=_positive, help="number of merged PRs, at least 1")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="print the report as JSON")
    output.add_argument(
        "--post",
        action="store_true",
        help="post the report to the metrics issue; runs only in GitHub Actions",
    )
    parser.set_defaults(handler=_command)
