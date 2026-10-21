"""Offline: the edges of devctl as: cut or endless gh output, a gh that cannot start, a missing
key, GitHub's answers it cannot use, the workflow hint and the command line. GitHub, the Keychain
and gh are simulated; git runs against a local bare repository."""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from devctl import cli, identity, process
from devctl.github.app import GitHubAccess
from devctl.repo import Repo
from devctl.settings import ProjectSettings
from github_fakes import WORKER_ID, FakeGitHub, FakeHarness, FakeKeychain, Remote, RunAs, git


def install_gh(fakes: FakeHarness, body: str) -> None:
    gh = fakes.directory / "gh"
    gh.write_text(f"#!{sys.executable}\nimport sys, time\n{body}\n")
    gh.chmod(0o755)


@pytest.fixture
def worktree(remote: Remote, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(remote.clone, "switch", "-q", "-c", "feature")
    remote.commit_in(remote.clone, "feature work")
    monkeypatch.chdir(remote.clone)
    return remote.clone


@pytest.mark.usefixtures("worktree")
def test_gh_output_that_was_cut_exits_2_and_says_so(
    run_as: RunAs,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(process, "MAX_OUTPUT_BYTES", 16)
    install_gh(fake_harness, "print('x' * 100)")
    assert run_as("worker", "gh", "api", "repos/{owner}/{repo}") == 2
    assert "gh printed more than 16 bytes, so its output was cut; it exited 0" in (
        capsys.readouterr().err
    )


@pytest.mark.usefixtures("worktree")
def test_a_gh_that_never_finishes_exits_2(
    run_as: RunAs,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(identity, "GH_TIMEOUT_SECONDS", 0.3)
    install_gh(fake_harness, "time.sleep(30)")
    assert run_as("worker", "gh", "pr", "checks", "7") == 2
    assert "devctl: gh did not finish within 0.3 seconds" in capsys.readouterr().err


@pytest.mark.usefixtures("worktree")
def test_a_gh_that_cannot_start_exits_2(
    access: GitHubAccess,
    project: ProjectSettings,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = Repo.discover(Path.cwd())
    # CI runners install a real gh in /usr/bin, so PATH holds an empty directory only.
    empty = tmp_path / "no-gh"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    monkeypatch.setattr(identity, "project_access", lambda settings: access)
    assert identity.run_as(repo, project, "worker", "gh", ["pr", "list"]) == 2
    assert capsys.readouterr().err == "devctl: gh could not start; install gh\n"


@pytest.mark.usefixtures("worktree")
def test_a_missing_key_exits_2_before_any_tool_runs(
    access: GitHubAccess,
    project: ProjectSettings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    no_keys = replace(access, keychain=FakeKeychain({}))
    monkeypatch.setattr(identity, "project_access", lambda settings: no_keys)
    assert identity.run_as(Repo.discover(Path.cwd()), project, "worker", "push", []) == 2
    assert capsys.readouterr().err == (
        f"devctl: Keychain item rapid-ship/worker-app/{WORKER_ID} not found; run rapid-ship app, "
        "which re-stores a key kept under rapid-ship/worker-app, "
        "or rapid-ship app --import-key worker\n"
    )


@pytest.mark.usefixtures("worktree")
@pytest.mark.parametrize(
    "answer", [(404, {"message": "Not Found"}), (200, {}), (200, {"default_branch": ""})]
)
def test_a_default_branch_github_cannot_name_exits_2_without_a_push(
    run_as: RunAs,
    github: FakeGitHub,
    remote: Remote,
    capsys: pytest.CaptureFixture[str],
    answer: tuple[int, dict[str, str]],
) -> None:
    github.route("GET", "/repos/o/r", lambda call, match: answer)
    assert run_as("worker", "push") == 2
    assert capsys.readouterr().err.startswith("devctl: ")
    assert remote.branch("feature") is None


def test_the_workflow_refusal_gets_a_hint_and_nothing_else_does() -> None:
    refusal = (
        "remote: refusing to allow a GitHub App to create or update workflow "
        "`.github/workflows/devctl-check.yml` without `workflows` permission"
    )
    hint = identity.push_hint(refusal)
    assert hint is not None
    assert "the owner pushes it" in hint
    assert identity.push_hint("! [rejected] feature -> feature (non-fast-forward)") is None


@pytest.mark.parametrize(
    ("argv", "arguments"),
    [
        (["as", "worker", "gh", "pr", "create", "--body", "-x"], ["pr", "create", "--body", "-x"]),
        (["as", "worker", "gh", "pr", "--help"], ["pr", "--help"]),
        (["as", "worker", "gh", "-h"], ["-h"]),
        (["as", "worker", "push", "--force"], ["--force"]),
        (["as", "reviewer", "push"], []),
    ],
)
def test_everything_after_the_action_reaches_devctl_as(
    argv: list[str], arguments: list[str]
) -> None:
    args = cli.build_parser().parse_args(argv)
    assert isinstance(args, argparse.Namespace)
    assert args.handler is identity.as_command
    assert args.arguments == arguments


def test_an_unknown_role_or_action_is_a_usage_error() -> None:
    for argv in (["as", "lead", "push"], ["as", "worker", "merge"]):
        with pytest.raises(SystemExit) as raised:
            cli.build_parser().parse_args(argv)
        assert raised.value.code == 2


def test_the_command_reads_this_repositorys_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship/project.toml").write_text('stack = "agnostic"\n')
    monkeypatch.chdir(tmp_path)
    assert cli.main(["as", "worker", "push"]) == 2
    assert "Agent identity is off" in capsys.readouterr().err
