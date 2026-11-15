"""The settings sources: issues that carry a label, and deployments to an environment."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast
from urllib.parse import quote

from devctl.metrics.github import GitHubError, GitHubReader
from devctl.metrics.model import Measured
from devctl.metrics.window import commit_exists, is_ancestor
from devctl.repo import Repo

ISSUES = (
    "[.[] | {number, user: {login: .user.login}, state, created_at, updated_at, "
    "html_url, pull_request}]"
)
DEPLOYMENTS = "[.[] | {id, sha, created_at, environment, statuses_url}]"
STATUSES = "[.[] | {id, state, created_at, target_url}]"
_FAILED = ("failure", "error")


@dataclass(frozen=True)
class _Deployment:
    id: int
    sha: str
    at: str  # created_at as GitHub wrote it
    created: datetime


def _time(row: Mapping[str, object], key: str) -> datetime:
    try:
        value: datetime | None = datetime.fromisoformat(cast("str", row[key]))
    except (KeyError, TypeError, ValueError):
        value = None
    if value is None or value.tzinfo is None:
        raise GitHubError(None, f"GitHub returned a {key} that is not a time; inspect the response")
    return value


def _record(
    label: str, url: str | None, time: object, state: str, detail: str | None = None
) -> dict[str, object]:
    record: dict[str, object] = {"label": label, "url": url, "time": time, "state": state}
    if detail is not None:
        record["detail"] = detail
    return record


def count_issues(reader: GitHubReader, label: str, since: datetime, until: datetime) -> Measured:
    """Issues with label that were opened from since to until. A pull request is not an issue."""
    path = f"issues?labels={quote(label, safe='')}&state=all&sort=created&direction=desc"
    found = []
    for row in reader.pages(path, jq=ISSUES, until=lambda row: _time(row, "created_at") < since):
        if row.get("pull_request") is None and _time(row, "created_at") <= until:
            url, opened = cast("str", row["html_url"]), row["created_at"]
            found.append(_record(f"#{row['number']}", url, opened, "counted"))
    return Measured(len(found), items=tuple(found))


def _deployments(reader: GitHubReader, environment: str) -> Iterator[_Deployment]:
    for row in reader.pages(
        f"deployments?environment={quote(environment, safe='')}", jq=DEPLOYMENTS
    ):
        at = cast("str", row["created_at"])
        yield _Deployment(
            cast("int", row["id"]), cast("str", row["sha"]), at, _time(row, "created_at")
        )


def _states(reader: GitHubReader, deployment: _Deployment) -> list[str]:
    """The state of each of the deployment's statuses, newest first."""
    rows = reader.pages(f"deployments/{deployment.id}/statuses", jq=STATUSES)
    newest_first = sorted(rows, key=lambda row: _time(row, "created_at"), reverse=True)
    return [cast("str", row["state"]) for row in newest_first]


def _deployment_record(deployment: _Deployment, state: str, detail: str) -> dict[str, object]:
    label = f"deployment {deployment.id}: {deployment.sha[:7]}"
    return _record(label, None, deployment.at, state, detail)


def _failures(reader: GitHubReader, in_span: list[_Deployment]) -> Measured:
    found = []
    for deployment in in_span:
        states = _states(reader, deployment)
        if states and states[0] in _FAILED:
            found.append(_deployment_record(deployment, "counted", f"last status {states[0]}"))
    return Measured(len(found), items=tuple(found))


def _rollbacks(
    repo: Repo, reader: GitHubReader, in_span: list[_Deployment], earlier: _Deployment | None
) -> Measured:
    successes = [d for d in in_span if "success" in _states(reader, d)]
    items: list[dict[str, object]] = []
    for deployment, previous in zip(successes, [*successes[1:], earlier], strict=False):
        if previous is None or previous.sha == deployment.sha:
            continue
        absent = next(
            (d.sha for d in (deployment, previous) if not commit_exists(repo, d.sha)), None
        )
        if absent is not None:
            detail = f"commit {absent[:7]} is not in the local history: run git fetch origin"
            items.append(_deployment_record(deployment, "unknown", detail))
        elif is_ancestor(repo, deployment.sha, previous.sha):
            detail = f"older than {previous.sha[:7]} (deployment {previous.id})"
            items.append(_deployment_record(deployment, "counted", detail))
    counted = sum(item["state"] == "counted" for item in items)
    return Measured(counted, unknown=len(items) - counted, items=tuple(items))


def count_deployments(
    repo: Repo,
    reader: GitHubReader,
    environment: str,
    count: Literal["rollbacks", "failures"],
    since: datetime,
    until: datetime,
) -> Measured:
    """Deployments to environment from since to until that rolled back or failed.

    A rollback reached success with a commit older than the commit of the previous deployment that
    reached success, which may predate since. A failure has failure or error as its newest status.
    The list is read, newest first, up to that previous deployment, or up to since for failures.
    """
    in_span: list[_Deployment] = []
    earlier: _Deployment | None = None
    for deployment in _deployments(reader, environment):
        if deployment.created > until:
            continue
        if deployment.created >= since:
            in_span.append(deployment)
        elif count == "failures":
            break
        elif "success" in _states(reader, deployment):
            earlier = deployment
            break
    if count == "failures":
        return _failures(reader, in_span)
    return _rollbacks(repo, reader, in_span, earlier)
