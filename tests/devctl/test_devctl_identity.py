"""Offline: devctl as, with simulated GitHub (FakeGitHub), the test Keychain, a local bare
repository in GitHub's place and a fake gh on PATH. No live GitHub, gh sign-in or Keychain."""

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from devctl.settings import ProjectSettings, Role
from github_fakes import (
    REVIEWER_INSTALLATION,
    WORKER_INSTALLATION,
    FakeGitHub,
    FakeHarness,
    Remote,
    RunAs,
    files_containing,
    git,
)


def install_gh(fakes: FakeHarness, *, code: int = 0, extra: str = "") -> None:
    """A gh that prints its arguments, GH_REPO, whether prompts are off, the sha256 of GH_TOKEN
    and whether the git askpass variable reached it, as one JSON line; then runs extra."""
    gh = fakes.directory / "gh"
    gh.write_text(
        f"#!{sys.executable}\n"
        "import hashlib, json, os, sys\n"
        "token = os.environ.get('GH_TOKEN', '')\n"
        "print(json.dumps({'argv': sys.argv[1:], 'repo': os.environ.get('GH_REPO'),"
        " 'prompt': os.environ.get('GH_PROMPT_DISABLED'),"
        " 'token_sha256': hashlib.sha256(token.encode()).hexdigest(),"
        " 'askpass': 'RAPID_SHIP_GIT_TOKEN' in os.environ}))\n"
        f"{extra}\n"
        f"sys.exit({code})\n"
    )
    gh.chmod(0o755)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture
def feature(remote: Remote, monkeypatch: pytest.MonkeyPatch) -> str:
    """The clone on branch feature with one new commit, as the working directory; its head."""
    git(remote.clone, "switch", "-q", "-c", "feature")
    head = remote.commit_in(remote.clone, "feature work")
    monkeypatch.chdir(remote.clone)
    return head


@pytest.fixture
def default_branch(github: FakeGitHub) -> None:
    """GitHub names main as o/r's default branch, to a token of either App."""
    github.route("GET", "/repos/o/r", lambda call, match: (200, {"default_branch": "main"}))


@pytest.mark.usefixtures("default_branch")
def test_push_sends_the_branch_to_the_branch_of_the_same_name(
    run_as: RunAs,
    feature: str,
    remote: Remote,
    github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_as("worker", "push") == 0
    assert remote.branch("feature") == feature
    assert remote.branch("main") != feature
    mints = [call.path for call in github.calls if call.method == "POST"]
    assert mints == [f"/app/installations/{WORKER_INSTALLATION}/access_tokens"]
    assert "feature -> feature" in capsys.readouterr().err


@pytest.mark.usefixtures("default_branch")
def test_push_never_forces(
    run_as: RunAs, feature: str, remote: Remote, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_as("worker", "push") == 0
    elsewhere = remote.commit_on("feature", "pushed from another clone")
    remote.commit_in(remote.clone, "local work on the old head")
    assert run_as("worker", "push") == 1  # git's own exit code
    assert remote.branch("feature") == elsewhere
    assert "rejected" in capsys.readouterr().err


@pytest.mark.usefixtures("default_branch")
def test_push_refuses_the_default_branch(
    run_as: RunAs,
    remote: Remote,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = remote.branch("main")
    remote.commit_in(remote.clone, "a commit on main")
    monkeypatch.chdir(remote.clone)
    assert run_as("worker", "push") == 1
    assert "main is the default branch" in capsys.readouterr().err
    assert remote.branch("main") == before


@pytest.mark.parametrize(
    ("role", "arguments", "reason"),
    [
        ("reviewer", (), "only the Worker App pushes"),
        ("worker", ("--force",), "push takes no arguments and never forces"),
        ("worker", ("origin", "+feature"), "push takes no arguments and never forces"),
    ],
)
def test_push_refusals_mint_no_token(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
    role: Role,
    arguments: tuple[str, ...],
    reason: str,
) -> None:
    assert run_as(role, "push", *arguments) == 1
    assert f"devctl as: refused: {reason}" in capsys.readouterr().err
    assert github.issued_tokens == []


def test_a_detached_head_is_refused_before_a_token_is_minted(
    run_as: RunAs, feature: str, remote: Remote, github: FakeGitHub
) -> None:
    git(remote.clone, "switch", "-q", "--detach")
    assert run_as("worker", "push") == 1
    assert github.issued_tokens == []


@pytest.mark.usefixtures("default_branch")
def test_the_push_token_is_never_an_argument_or_in_a_file(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    recorded_argv: list[list[str]],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    assert run_as("worker", "push") == 0
    out, err = capsys.readouterr()
    [token] = github.issued_tokens
    [push] = [argv for argv in recorded_argv if "push" in argv]
    assert push[:5] == ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]
    assert all(token not in arg for argv in recorded_argv for arg in argv)
    assert token not in out + err
    assert files_containing(tmp_path, token) == []


def test_gh_runs_as_the_worker_app_with_the_token_only_in_its_environment(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    recorded_argv: list[list[str]],
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    install_gh(fake_harness)
    assert run_as("worker", "gh", "pr", "create", "--title", "Add the feature") == 0
    out, err = capsys.readouterr()
    [token] = github.issued_tokens
    assert json.loads(out) == {
        "argv": ["pr", "create", "--title", "Add the feature"],
        "repo": "o/r",
        "prompt": "1",
        "token_sha256": sha256(token),
        "askpass": False,
    }
    assert token not in out + err
    assert all(token not in arg for argv in recorded_argv for arg in argv)
    assert files_containing(tmp_path, token) == []
    mints = [call.path for call in github.calls if call.method == "POST"]
    assert mints == [f"/app/installations/{WORKER_INSTALLATION}/access_tokens"]


def test_gh_as_the_reviewer_uses_the_reviewer_app(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_gh(fake_harness)
    assert run_as("reviewer", "gh", "pr", "review", "7", "--approve") == 0
    mints = [call.path for call in github.calls if call.method == "POST"]
    assert mints == [f"/app/installations/{REVIEWER_INSTALLATION}/access_tokens"]
    assert json.loads(capsys.readouterr().out)["argv"] == ["pr", "review", "7", "--approve"]


def test_a_token_the_tool_prints_is_hidden(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # gh and git push share one relay, so a gh that prints its token proves the relay hides it.
    install_gh(fake_harness, extra="print(token)\nprint(token, file=sys.stderr)")
    assert run_as("worker", "gh", "api", "user") == 0
    out, err = capsys.readouterr()
    [token] = github.issued_tokens
    assert token not in out + err
    assert out.splitlines()[-1] == "[token]"
    assert err.splitlines()[-1] == "[token]"


def test_gh_exit_code_is_passed_through(
    run_as: RunAs, feature: str, fake_harness: FakeHarness
) -> None:
    install_gh(fake_harness, code=3)
    assert run_as("worker", "gh", "issue", "list") == 3


@pytest.mark.parametrize(
    "arguments",
    [
        (),
        ("auth", "token"),
        ("alias", "set", "x", "y"),
        ("extension", "install", "x"),
        ("repo", "delete", "o/r"),
        ("-R", "o/r", "pr", "list"),
        ("pr", "merge", "7", "--admin"),
        ("pr", "merge", "--admin=true", "7"),
    ],
)
def test_gh_refusals_mint_no_token_and_start_no_gh(
    run_as: RunAs,
    feature: str,
    github: FakeGitHub,
    fake_harness: FakeHarness,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    install_gh(fake_harness)
    assert run_as("worker", "gh", *arguments) == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert "devctl as: refused: " in err
    assert github.issued_tokens == []


def test_agent_identity_off_exits_2_and_says_how_to_turn_it_on(
    run_as: RunAs,
    feature: str,
    project: ProjectSettings,
    github: FakeGitHub,
    capsys: pytest.CaptureFixture[str],
) -> None:
    off = replace(project, worker_app=None, reviewer_app=None)
    assert run_as("worker", "push", settings=off) == 2
    assert run_as("worker", "gh", "pr", "list", settings=off) == 2
    err = capsys.readouterr().err
    assert err.count("devctl: Agent identity is off") == 2
    assert "rapid-ship app" in err
    assert github.calls == []
