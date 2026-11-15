"""devctl metrics --post: the report on the one open issue that the scheduled Action keeps."""

from __future__ import annotations

import json
import re
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import get_args
from urllib.parse import quote

from devctl import process
from devctl.doctor_items import owner_environment
from devctl.metrics.github import AllowanceUsedUp, GitHubError, GitHubReader
from devctl.metrics.model import NEEDS_IDENTITY, ThresholdStatus
from devctl.metrics.report import Report, render_markdown, value_text
from devctl.metrics.window import MetricsError

ISSUE_TITLE = "rapid-ship metrics"
MARKER = "<!-- rapid-ship-metrics -->"
ACTIONS_LOGIN = "github-actions[bot]"
WRITE_TIMEOUT_SECONDS = 60.0
GitHubWrite = Callable[[str, str, Mapping[str, object]], object]  # method, path, body -> JSON

_JSON_OPENER = "<!-- rapid-ship-metrics-json"
_JSON_COMMENT = re.compile(re.escape(_JSON_OPENER) + r"\n(.*?)-->", re.DOTALL)
# gh applies this filter, so an issue's body never reaches devctl: only whether it has the marker.
_LOOKUP = (
    "[.[] | {number, user: {login: .user.login}, pull_request: (.pull_request != null), "
    f'has_marker: ((.body // "") | startswith("{MARKER}"))}}]'
)
_NOTABLE = ("breached", "unknown")
_STATUSES = (*get_args(ThresholdStatus), NEEDS_IDENTITY)
_COMMENT_NOT_POSTED = (
    ". The issue already holds this run's report, but its status-change comment was not posted, "
    "and a rerun does not post it again. The job summary holds this run's report too"
)


@dataclass(frozen=True)
class PostTarget:
    repository: str
    number: int | None  # None: create a new issue
    previous: Mapping[str, str]  # metric id -> status in the previous report


def gh_write(method: str, path: str, body: Mapping[str, object]) -> object:
    """Send body to path as method with the run's gh sign-in; return GitHub's JSON answer.

    A write that does not finish may still have happened, so nothing here retries one.
    Raises GitHubError.
    """
    argv = ["gh", "api", "--method", method, path, "--input", "-"]
    try:
        result = process.run_process(
            argv,
            Path(tempfile.gettempdir()),
            WRITE_TIMEOUT_SECONDS,
            env=owner_environment("gh"),
            input_text=json.dumps(body),
        )
    except OSError:
        raise GitHubError(None, f"gh could not start for {method} {path}; install gh") from None
    if result.timed_out:
        raise GitHubError(None, _uncertain(method, path, "gh api timed out"))
    if result.stdout_truncated:
        raise GitHubError(None, _uncertain(method, path, "gh api printed too much"))
    if result.returncode != 0:
        line = process.first_line(result.stderr) or f"gh api exited {result.returncode}"
        raise GitHubError(None, _refusal(method, path, line))
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise GitHubError(None, _uncertain(method, path, "gh api printed no JSON")) from None


def _refusal(method: str, path: str, line: str) -> str:
    """The message for a write that gh refused, with the fix that gh's first stderr line implies."""
    if "rate limit" in line.lower() or re.search(r"\bHTTP 429\b", line):
        refused = f"GitHub refused {method} {path}: {line}; the API allowance is used up"
        if path.endswith("/comments"):
            return refused + _COMMENT_NOT_POSTED
        return (
            f"{refused}, and the job summary holds this run's report: "
            "rerun the workflow after the allowance resets"
        )
    if re.search(r"\bHTTP 5\d\d\b", line):
        return _uncertain(method, path, line)
    if re.search(r"\bHTTP 422\b", line):
        refused = (
            f"GitHub refused {method} {path}: {line}; GitHub may have found the body too large"
        )
        if path.endswith("/comments"):
            return refused + _COMMENT_NOT_POSTED
        return f"{refused}, and the job summary holds this run's report"
    return (
        f"GitHub refused {method} {path}: {line}; "
        "check that the workflow grants issues: write, then rerun it"
    )


def _uncertain(method: str, path: str, cause: str) -> str:
    return (
        f"{cause} for {method} {path}, so the write may have been applied: "
        "check the issue before you rerun the workflow"
    )


def status_changes(previous: Mapping[str, str], report: Report) -> list[str]:
    """One line for each threshold whose status differs from the previous report's."""
    return [
        f"{m.metric_id}: {previous.get(m.metric_id, 'none')} -> {m.status} "
        f"({value_text(m)}, at most {m.threshold})"
        for m in report.metrics
        if m.status is not None and previous.get(m.metric_id) != m.status
    ]


def prepare_post(reader: GitHubReader) -> PostTarget:
    """Find the issue to update and its previous statuses, before any measurement starts.

    A lookup that fails fails the post: without an answer, a new issue could duplicate the old.
    """
    try:
        number = _find_issue(reader)
        previous = {} if number is None else _previous_statuses(reader, number)
    except AllowanceUsedUp as error:
        raise GitHubError(None, _lookup_failure(error.reason())) from error
    except GitHubError as error:
        raise GitHubError(error.status, _lookup_failure(str(error))) from error
    return PostTarget(reader.repository, number, previous)


def _lookup_failure(reason: str) -> str:
    return f"cannot look up the metrics issue: {reason}; nothing was posted"


def _find_issue(reader: GitHubReader) -> int | None:
    """The lowest number among the open issues that the Action opened and that carry the marker."""
    path = f"issues?state=open&creator={quote(ACTIONS_LOGIN, safe='')}"
    numbers = [
        number
        for entry in reader.pages(path, jq=_LOOKUP)
        if (number := _report_number(entry)) is not None
    ]
    return min(numbers, default=None)


def _report_number(entry: Mapping[str, object]) -> int | None:
    """The issue number of an entry that is the Action's report, else None.

    The server's creator filter is not trusted: the login, the marker and the pull request flag
    are checked here.
    """
    user, number = entry.get("user"), entry.get("number")
    if (
        isinstance(user, Mapping)
        and user.get("login") == ACTIONS_LOGIN
        and entry.get("has_marker") is True
        and not entry.get("pull_request")
        and isinstance(number, int)
    ):
        return number
    return None


def _previous_statuses(reader: GitHubReader, number: int) -> dict[str, str]:
    issue = reader.get(f"issues/{number}", jq="{body}")
    if not isinstance(issue, Mapping):
        raise GitHubError(None, f"GitHub returned invalid JSON for issues/{number}")
    return _statuses(issue.get("body"))


def _statuses(body: object) -> dict[str, str]:
    """The status of each metric in the JSON comment of a posted body; {} when it has none.

    Anyone with write access can edit the body, so an entry counts only with a known status.
    """
    match = _JSON_COMMENT.search(body) if isinstance(body, str) else None
    try:
        data = json.loads(match[1]) if match else None
    except (ValueError, RecursionError):
        return {}
    metrics = data.get("metrics") if isinstance(data, dict) else None
    if not isinstance(metrics, list):
        return {}
    return {
        entry["id"]: entry["status"]
        for entry in metrics
        if isinstance(entry, dict)
        and isinstance(entry.get("id"), str)
        and entry.get("status") in _STATUSES
    }


def post(report: Report, target: PostTarget, write: GitHubWrite, summary: Path | None) -> str:
    """Add the report to the job summary and to the issue; return the issue's URL.

    It reads nothing from GitHub. A new issue gets a comment only for a breached or unknown
    threshold, and an updated one only for a status that changed. Raises GitHubError, or
    MetricsError when the job summary cannot be written, before any GitHub write.
    """
    if summary is not None:
        try:
            with summary.open("a", encoding="utf-8") as stream:
                stream.write(render_markdown(report))
        except OSError as error:
            raise MetricsError(
                f"cannot append the report to the job summary {summary}: "
                f"{error.strerror or error}; nothing was posted"
            ) from error
    issues = f"repos/{target.repository}/issues"
    body = {"body": _body(report)}
    if target.number is None:
        number, url = _issue(write("POST", issues, {"title": ISSUE_TITLE, **body}))
        notable = replace(report, metrics=tuple(m for m in report.metrics if m.status in _NOTABLE))
        changes = status_changes({}, notable)
    else:
        number = target.number
        url = _issue(write("PATCH", f"{issues}/{number}", body))[1]
        changes = status_changes(target.previous, report)
    if changes:
        heading = "Suggested threshold status changed:"
        lines = "\n".join(f"- {change}" for change in changes)
        write("POST", f"{issues}/{number}/comments", {"body": f"{heading}\n\n{lines}"})
    return url


def _body(report: Report) -> str:
    """The marker, the Markdown report and a comment with each metric's id and status.

    The next run reads only the statuses, so the body lists no item; a line counts them.
    """
    markdown = render_markdown(report)
    items = sum(len(metric.measured.items) for metric in report.metrics)
    if items:
        noun = "item" if items == 1 else "items"
        markdown += (
            f"\nThe report holds {items} {noun} that this issue does not list; "
            "./devctl metrics --json prints the whole report.\n"
        )
    metrics = [{"id": metric.metric_id, "status": metric.status} for metric in report.metrics]
    # Every > becomes its unicode escape, so --> can appear only where the comment ends.
    data = json.dumps({"version": 1, "metrics": metrics}, indent=2).replace(">", "\\u003e")
    return f"{MARKER}\n{markdown}\n{_JSON_OPENER}\n{data}\n-->\n"


def _issue(answer: object) -> tuple[int, str]:
    number = answer.get("number") if isinstance(answer, Mapping) else None
    url = answer.get("html_url") if isinstance(answer, Mapping) else None
    if not isinstance(number, int) or not isinstance(url, str):
        raise GitHubError(
            None,
            "GitHub's answer names no issue number and URL, so the write may have been applied: "
            "check the issue before you rerun the workflow",
        )
    return number, url
