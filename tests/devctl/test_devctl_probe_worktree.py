"""Offline: the temporary worktree that doctor --skills starts a Session in. Real git runs in a
scratch clone; one test simulates a failed removal. No network, no Harness."""

import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from devctl import process
from devctl.doctor_skills import ProbeError, probe_worktree
from devctl.process import ProcessResult
from devctl.repo import Repo
from github_fakes import Remote, git

pytestmark = pytest.mark.usefixtures("isolated_home")


class Boom(Exception):
    """What a failing body raises."""


def worktree_paths(clone: Path) -> list[str]:
    listing = git(clone, "worktree", "list", "--porcelain")
    return [line for line in listing.splitlines() if line.startswith("worktree ")]


@pytest.fixture
def scratch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The directory tempfile.mkdtemp uses for this test, so a test can see what is left."""
    directory = tmp_path / "tmp"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


def test_it_yields_a_detached_worktree_at_head_and_removes_it(
    remote: Remote, scratch: Path
) -> None:
    head = git(remote.clone, "rev-parse", "HEAD")
    with probe_worktree(Repo.discover(remote.clone)) as path:
        assert path.is_relative_to(scratch.resolve())
        assert git(path, "rev-parse", "HEAD") == head
        assert git(path, "rev-parse", "--abbrev-ref", "HEAD") == "HEAD"  # detached
        assert len(worktree_paths(remote.clone)) == 2
    assert list(scratch.iterdir()) == []
    assert len(worktree_paths(remote.clone)) == 1
    assert git(remote.clone, "branch", "--list") == "* main"


def test_head_is_the_current_commit_not_the_default_branch(remote: Remote) -> None:
    git(remote.clone, "switch", "-q", "-c", "feature")
    head = remote.commit_in(remote.clone, "a commit only on feature")
    with probe_worktree(Repo.discover(remote.clone)) as path:
        assert git(path, "rev-parse", "HEAD") == head


def test_it_removes_files_and_a_lock_a_session_left(remote: Remote, scratch: Path) -> None:
    with probe_worktree(Repo.discover(remote.clone)) as path:
        (path / "scratch.txt").write_text("a Session wrote this\n")
        (path / "nested").mkdir()
        (path / "nested" / "more.txt").write_text("and this\n")
        git(path, "worktree", "lock", str(path))  # one --force alone cannot remove a lock
    assert list(scratch.iterdir()) == []
    assert len(worktree_paths(remote.clone)) == 1


def test_it_removes_the_worktree_when_the_body_raises(remote: Remote, scratch: Path) -> None:
    repo = Repo.discover(remote.clone)

    def body() -> None:
        with probe_worktree(repo):
            raise Boom

    with pytest.raises(Boom):
        body()
    assert list(scratch.iterdir()) == []
    assert len(worktree_paths(remote.clone)) == 1


def test_two_open_probes_do_not_share_a_path(remote: Remote) -> None:
    repo = Repo.discover(remote.clone)
    with probe_worktree(repo) as first, probe_worktree(repo) as second:
        assert first != second
        assert first.exists()
        assert second.exists()
    assert len(worktree_paths(remote.clone)) == 1


def test_a_repository_without_a_commit_leaves_nothing(tmp_path: Path, scratch: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    git(empty, "init", "-q", "-b", "main")
    with pytest.raises(ProbeError) as raised, probe_worktree(Repo.discover(empty)):
        pytest.fail("the body must not run")
    assert str(raised.value).startswith("could not add the probe worktree ")
    assert list(scratch.iterdir()) == []


def test_a_failed_removal_says_how_to_remove_it_by_hand(
    remote: Remote, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Simulated: git refuses the removal.
    real = process.run_process

    def refuse_removal(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        if list(argv[1:3]) == ["worktree", "remove"]:
            return ProcessResult(list(argv), 128, "", "fatal: simulated refusal\n", 0.0)
        return real(argv, cwd, timeout_seconds, env=env, input_text=input_text)

    monkeypatch.setattr(process, "run_process", refuse_removal)
    with pytest.raises(ProbeError) as raised, probe_worktree(Repo.discover(remote.clone)) as path:
        pass
    assert str(raised.value) == (
        f"could not remove the probe worktree {path}: fatal: simulated refusal; "
        f"remove it with git worktree remove --force --force {path}"
    )
    assert path.exists()
    git(remote.clone, "worktree", "remove", "--force", str(path))


def test_git_runs_in_the_repository_root(remote: Remote, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, Path]] = []
    real = process.run_process

    def record(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        seen.append((" ".join(argv[1:3]), cwd))
        return real(argv, cwd, timeout_seconds, env=env, input_text=input_text)

    monkeypatch.setattr(process, "run_process", record)
    nested = remote.clone / "nested"
    nested.mkdir()
    with probe_worktree(Repo.discover(nested)):
        pass
    root = remote.clone.resolve()
    assert seen == [("worktree add", root), ("worktree remove", root)]
