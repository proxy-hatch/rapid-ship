"""Offline: the window over a local repository and recorded GitHub responses."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from devctl.metrics.github import GitHubReader
from devctl.metrics.window import (
    MetricsError,
    Window,
    build_window,
    commit_exists,
    default_branch,
    is_ancestor,
    resolve_tip,
)
from devctl.repo import Repo
from github_fakes import git
from metrics_fakes import MergedHistory


def window(history: MergedHistory, size: int = 30, agent: str | None = None) -> Window:
    repo = Repo.discover(history.path)
    reader = GitHubReader("o/r", history.owner)
    branch = default_branch(reader)
    return build_window(repo, reader, branch, resolve_tip(repo, branch), size, agent)


def test_the_walk_follows_first_parents_and_skips_direct_pushes(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    for number in range(1, 4):
        h.merge(number, {str(number): "x"})
    h.push({"direct": "x"})
    h.merge(4, {"four": "x"}, parents=2)
    h.publish()
    result = window(h)
    assert [pr.number for pr in result.prs] == [4, 3, 2, 1]
    side = git(tmp_path, "rev-parse", "pr-4")
    assert not any(f"commits/{side}/" in path for path in h.owner.paths)
    assert result.not_fetched == 0


def test_agent_identity_selects_the_worker_apps_prs(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"a": "x"})
    h.merge(2, {"b": "x"}, author="person")
    h.publish()
    result = window(h, agent="o-worker[bot]")
    assert [pr.number for pr in result.prs] == [1]
    assert [pr.number for pr in result.merged] == [2, 1]
    assert result.agent_login == "o-worker[bot]"


def test_without_agent_identity_every_pr_counts(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {}, author="person")
    h.publish()
    assert window(h).prs[0].author == "person"


def test_a_window_that_is_not_full(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {})
    h.merge(2, {})
    h.publish()
    result = window(h)
    assert len(result.prs) == 2
    assert result.size == 30
    assert result.prs[-1].closed_at == result.since
    assert result.since == datetime(2026, 10, 1, 6, 12, tzinfo=UTC)


def test_a_merged_pr_missing_locally_counts_as_not_fetched(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    tip = h.merge(1, {})
    h.publish()
    h.merge(2, {})
    h.pulls.insert(0, {**h.pulls[0], "number": 3, "merge_commit_sha": "f" * 40})
    h.closed_pages()
    result = window(h)
    assert result.tip == tip
    assert result.not_fetched == 2
    repo = Repo.discover(tmp_path)
    assert not commit_exists(repo, "f" * 40)
    assert not is_ancestor(repo, git(tmp_path, "rev-parse", "HEAD"), tip)


def test_a_pr_merged_by_another_commit_is_skipped(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    sha = h.merge(1, {})
    h.owner.serve(
        f"repos/o/r/commits/{sha}/pulls?per_page=64&page=1",
        [
            {**h.pulls[0], "merge_commit_sha": "f" * 40},
        ],
    )
    h.publish()
    assert window(h).prs == ()


def test_a_missing_origin_branch_names_the_fetch(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    with pytest.raises(MetricsError, match="origin/main is missing: run git fetch origin"):
        resolve_tip(Repo.discover(h.path), "main")


def test_the_window_stops_at_size_without_reading_further(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {})
    tip = h.merge(2, {})
    h.publish()
    assert len(window(h, size=1).prs) == 1
    assert [p for p in h.owner.paths if "/commits/" in p] == [
        f"repos/o/r/commits/{tip}/pulls?per_page=64&page=1",
    ]


def test_a_history_without_population_prs_walks_to_the_root(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    for _ in range(105):
        h.push({})
    h.publish()
    result = window(h, agent="o-worker[bot]")
    assert result.prs == ()
    assert result.since is None
    assert len([p for p in h.owner.paths if "/commits/" in p]) == 106


def test_not_fetched_pages_to_the_end(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {})
    h.publish()
    h.pulls = [dict(h.pulls[0]) for _ in range(64)] + [
        {**h.pulls[0], "number": 2, "merge_commit_sha": "e" * 40},
    ]
    h.closed_pages()
    assert window(h).not_fetched == 1
    assert h.owner.paths[-1].endswith("per_page=64&page=2")
