"""An immutable PR window from a resolved local default-branch tip."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import cast
from urllib.parse import quote

from devctl.metrics.github import GitHubReader
from devctl.repo import Repo, RepoError

PULLS = (
    "[.[] | {number, user: {login: .user.login}, merged_at, closed_at, updated_at, "
    "merge_commit_sha, body, html_url}]"
)
CLOSED_PULLS = (
    "[.[] | {number, user: {login: .user.login}, merged_at, closed_at, updated_at, "
    "merge_commit_sha, html_url}]"
)


class MetricsError(Exception):
    """The local metrics window could not be resolved."""


@dataclass(frozen=True)
class PullRequest:
    number: int
    author: str
    merged_at: datetime | None
    closed_at: datetime | None
    merge_commit: str | None
    body: str
    url: str


@dataclass(frozen=True)
class Window:
    branch: str
    tip: str
    size: int
    agent_login: str | None
    prs: tuple[PullRequest, ...]
    merged: tuple[PullRequest, ...]
    not_fetched: int

    @property
    def since(self) -> datetime | None:
        return self.prs[-1].merged_at if self.prs else None


def default_branch(reader: GitHubReader) -> str:
    data = cast("Mapping[str, str]", reader.get("", jq="{default_branch}"))
    return data["default_branch"]


def resolve_tip(repo: Repo, branch: str) -> str:
    try:
        return repo.git(
            "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}^{{commit}}"
        ).strip()
    except RepoError:
        raise MetricsError(f"origin/{branch} is missing: run git fetch origin") from None


def commit_exists(repo: Repo, sha: str) -> bool:
    try:
        repo.git("cat-file", "-e", f"{sha}^{{commit}}")
    except RepoError:
        return False
    return True


def is_ancestor(repo: Repo, commit: str, of: str) -> bool:
    try:
        repo.git("merge-base", "--is-ancestor", commit, of)
    except RepoError:
        return False
    return True


def _timestamp(value: object) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else None


def _pull(data: Mapping[str, object]) -> PullRequest:
    user = cast("Mapping[str, str]", data["user"])
    return PullRequest(
        number=cast("int", data["number"]),
        author=user["login"],
        merged_at=_timestamp(data.get("merged_at")),
        closed_at=_timestamp(data.get("closed_at")),
        merge_commit=cast("str | None", data.get("merge_commit_sha")),
        body=cast("str", data.get("body") or ""),
        url=cast("str", data["html_url"]),
    )


def build_window(
    repo: Repo,
    reader: GitHubReader,
    branch: str,
    tip: str,
    size: int,
    agent_login: str | None,
) -> Window:
    population: list[PullRequest] = []
    merged: list[PullRequest] = []
    for sha in repo.git("rev-list", "--first-parent", tip).splitlines():
        for data in reader.pages(f"commits/{sha}/pulls", jq=PULLS):
            if data.get("merge_commit_sha") != sha:
                continue
            pr = _pull(data)
            merged.append(pr)
            if agent_login is None or pr.author == agent_login:
                population.append(pr)
            break
        if len(population) >= size:
            break
    not_fetched = 0
    path = f"pulls?state=closed&base={quote(branch, safe='')}&sort=updated&direction=desc"
    for data in reader.pages(path, jq=CLOSED_PULLS):
        pr = _pull(data)
        if pr.merged_at is None or (agent_login is not None and pr.author != agent_login):
            continue
        if pr.merge_commit is not None and (
            not commit_exists(repo, pr.merge_commit) or not is_ancestor(repo, pr.merge_commit, tip)
        ):
            not_fetched += 1
    return Window(branch, tip, size, agent_login, tuple(population), tuple(merged), not_fetched)
