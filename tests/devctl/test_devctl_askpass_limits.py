"""Offline: the edges of token-bearing git, against local repositories and a simulated GitHub
server. No network."""

import base64
import re
import secrets
import sys
from pathlib import Path

import pytest

from devctl import process
from devctl.github import askpass
from devctl.github.app import GitError, git_environment, require_exact_remote, run_git
from devctl.process import ProcessResult
from github_fakes import Call, FakeGitHub, Remote, Reply, git

pytestmark = pytest.mark.usefixtures("isolated_home")


def test_git_authenticates_with_the_token_from_askpass(remote: Remote, github: FakeGitHub) -> None:
    token = secrets.token_urlsafe(48)
    url = f"{github.url}/o/r.git"

    def refs(call: Call, _: re.Match[str]) -> Reply:
        if "Authorization" not in call.headers:
            return 401, None, {"WWW-Authenticate": 'Basic realm="GitHub"'}
        return 404, {"message": "Not Found"}

    github.route("GET", r"/o/r\.git/info/refs", refs)
    run_git(remote.clone, ["ls-remote", url], token, url=url)
    expected = "Basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
    assert [call.headers.get("Authorization") for call in github.calls] == [None, expected]


@pytest.mark.parametrize("rule", ["insteadOf", "pushInsteadOf"])
def test_an_empty_rewrite_rule_is_refused(remote: Remote, rule: str) -> None:
    # git matches the value as a prefix, so an empty one rewrites every URL to the base.
    url = str(remote.bare)
    git(remote.clone, "config", f"url.{url}-elsewhere.{rule}", "")
    with pytest.raises(GitError, match="rewrites"):
        require_exact_remote(remote.clone, url)
    with pytest.raises(GitError, match="rewrites"):
        run_git(remote.clone, ["push", url, "HEAD:refs/heads/empty-1"], "t", url=url)
    assert remote.branch("empty-1") is None


def test_unreadable_git_config_is_a_git_error(remote: Remote) -> None:
    url = str(remote.bare)
    with (remote.git_common_dir / "config").open("a") as config:
        config.write("[broken\n")
    with pytest.raises(GitError, match=r"could not read git config: .*bad config"):
        run_git(remote.clone, ["push", url, "HEAD:refs/heads/broken-1"], "t", url=url)
    assert remote.branch("broken-1") is None


@pytest.mark.parametrize(
    "cut",
    [{"returncode": 1, "timed_out": True}, {"returncode": 0, "stdout_truncated": True}],
    ids=["timed out", "cut output"],
)
def test_a_cut_config_read_is_a_git_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cut: dict[str, int | bool]
) -> None:
    def answer(argv: list[str], *_: object, **__: object) -> ProcessResult:
        returncode = int(cut["returncode"])
        timed_out = bool(cut.get("timed_out", False))
        truncated = bool(cut.get("stdout_truncated", False))
        return ProcessResult(argv, returncode, "", "", 0.0, timed_out, truncated)

    monkeypatch.setattr(process, "run_process", answer)
    with pytest.raises(GitError, match="could not read git config"):
        require_exact_remote(tmp_path, "https://git.example.invalid/o/r.git")


def test_run_git_needs_the_url_among_its_arguments(
    remote: Remote, recorded_argv: list[list[str]]
) -> None:
    with pytest.raises(ValueError, match="remote URL"):
        run_git(remote.clone, ["ls-remote", "origin"], "t", url=str(remote.bare))
    assert recorded_argv == []


def test_askpass_answers_only_username_and_password_prompts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    token = secrets.token_urlsafe(48)
    environ = {askpass.ASKPASS_VARIABLE: token}
    assert askpass.answer("Enter passphrase for key '/k': ", environ) is None
    assert askpass.answer("Password for 'https://h': ", {askpass.ASKPASS_VARIABLE: ""}) is None
    monkeypatch.setenv(askpass.ASKPASS_VARIABLE, token)
    assert askpass.main(["askpass.py"]) == 1
    assert askpass.main(["askpass.py", "Username for 'https://h': "]) == 0
    assert capsys.readouterr().out == "x-access-token\n"


def test_git_environment_passes_the_network_settings_and_no_other_caller_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("SSL_CERT_FILE", "/etc/ssl/example.pem")
    monkeypatch.setenv("GH_TOKEN", "example-value")
    monkeypatch.setenv("GIT_TRACE", "1")
    monkeypatch.setenv("GIT_ASKPASS", "/nowhere/askpass")
    monkeypatch.setenv(askpass.ASKPASS_VARIABLE, "example-value")
    env = git_environment("t")
    assert env["HTTPS_PROXY"] == "http://proxy.invalid:3128"
    assert env["SSL_CERT_FILE"] == "/etc/ssl/example.pem"
    assert env["GIT_ASKPASS"] == str(askpass.ASKPASS_PATH)
    assert env[askpass.ASKPASS_VARIABLE] == "t"
    assert "GH_TOKEN" not in env
    assert "GIT_TRACE" not in env


def test_git_environment_puts_this_interpreter_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert git_environment("t")["PATH"] == f"{Path(sys.executable).parent}:/usr/bin:/bin"
    # Path("").parent is ".", which would put git's working directory on PATH.
    monkeypatch.setattr(sys, "executable", "")
    assert git_environment("t")["PATH"] == "/usr/bin:/bin"
