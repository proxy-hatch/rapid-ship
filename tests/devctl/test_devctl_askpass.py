"""Offline: the askpass helper and token-bearing git against local repositories and a simulated
GitHub server. No network."""

import os
import secrets
from pathlib import Path

import pytest

from devctl import process
from devctl.github import askpass
from devctl.github.app import GitError, git_environment, require_exact_remote, run_git
from github_fakes import FakeGitHub, Remote, git

pytestmark = pytest.mark.usefixtures("isolated_home")

PROMPT = "Password for 'https://git.example.invalid': "
ELSEWHERE = "https://git.example.invalid/o/r.git"


def test_askpass_answers_git_prompts_from_its_environment(tmp_path: Path) -> None:
    token = secrets.token_urlsafe(48)
    path = git_environment(token)["PATH"]

    def run(prompt: str, env: dict[str, str]) -> process.ProcessResult:
        return process.run_process([str(askpass.ASKPASS_PATH), prompt], tmp_path, 10, env=env)

    password = run(PROMPT, {"PATH": path, askpass.ASKPASS_VARIABLE: token})
    user = run(
        "Username for 'https://git.example.invalid': ",
        {"PATH": path, askpass.ASKPASS_VARIABLE: token},
    )
    without = run(PROMPT, {"PATH": path})
    assert (password.returncode, password.stdout) == (0, token + "\n")
    assert (user.returncode, user.stdout) == (0, "x-access-token\n")
    assert (without.returncode, without.stdout) == (1, "")


def test_configured_credential_helpers_are_bypassed(tmp_path: Path) -> None:
    token = secrets.token_urlsafe(48)
    owner = tmp_path / "owner.gitconfig"
    owner.write_text(
        '[credential]\n\thelper = "!f() { echo username=owner; echo password=owner-login; }; f"\n'
    )
    # GIT_CONFIG_NOSYSTEM keeps Xcode's osxkeychain helper out of the control case.
    env = {**git_environment(token), "GIT_CONFIG_GLOBAL": str(owner), "GIT_CONFIG_NOSYSTEM": "1"}
    request = "protocol=https\nhost=git.example.invalid\n\n"
    reset = process.run_process(
        ["git", *askpass.GIT_TOKEN_OPTIONS, "credential", "fill"],
        tmp_path,
        30,
        env=env,
        input_text=request,
    )
    control = process.run_process(
        ["git", "credential", "fill"], tmp_path, 30, env=env, input_text=request
    )
    assert f"password={token}" in reset.stdout
    assert "password=owner-login" in control.stdout


def test_extra_headers_from_git_config_are_not_sent(remote: Remote, github: FakeGitHub) -> None:
    url = f"{github.url}/o/r.git"
    headers = {"X-Owner-Generic", "X-Owner-Scoped"}
    git(remote.clone, "config", "http.extraHeader", "X-Owner-Generic: owner")
    # actions/checkout writes a URL-scoped header like this one; -c http.extraHeader= keeps it.
    git(remote.clone, "config", f"http.{github.url}/.extraHeader", "X-Owner-Scoped: owner")
    process.run_process(["git", "ls-remote", url], remote.clone, 30)  # control: no reset
    control = {name for call in github.calls for name in call.headers}
    github.calls.clear()
    run_git(remote.clone, ["ls-remote", url], secrets.token_urlsafe(48), url=url)
    sent = {name for call in github.calls for name in call.headers}
    assert headers <= control
    assert github.calls
    assert not headers & sent


def test_repository_hooks_do_not_run_with_the_token(remote: Remote, tmp_path: Path) -> None:
    hooks, leak = tmp_path / "hooks", tmp_path / "leak"
    hooks.mkdir()
    for name in ("pre-push", "reference-transaction"):
        (hooks / name).write_text(f'#!/bin/sh\nprintenv RAPID_SHIP_GIT_TOKEN >> "{leak}"\n')
        (hooks / name).chmod(0o755)
    git(remote.clone, "config", "core.hooksPath", str(hooks))
    url = str(remote.bare)
    result = run_git(
        remote.clone, ["push", url, "HEAD:refs/heads/hooks-1"], secrets.token_urlsafe(48), url=url
    )
    assert result.returncode == 0
    assert not leak.exists()


def test_git_tracing_from_the_callers_environment_is_dropped(
    remote: Remote, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in {"GIT_TRACE": "1", "GIT_TRACE_CURL": "1", "GIT_TRACE_REDACT": "0"}.items():
        monkeypatch.setenv(name, value)
    url = str(remote.bare)
    result = run_git(remote.clone, ["ls-remote", url], secrets.token_urlsafe(48), url=url)
    assert result.returncode == 0
    assert "trace" not in result.stderr


@pytest.mark.parametrize("rule", ["insteadOf", "pushInsteadOf"])
def test_rewritten_remote_url_is_refused(remote: Remote, rule: str) -> None:
    url = str(remote.bare)
    git(
        remote.clone,
        "config",
        f"url.https://elsewhere.invalid/.{rule}",
        "https://unrelated.invalid/",
    )
    require_exact_remote(remote.clone, url)
    git(remote.clone, "config", f"url.{url}-elsewhere.{rule}", url)
    with pytest.raises(GitError, match="rewrites"):
        require_exact_remote(remote.clone, url)
    with pytest.raises(GitError, match="rewrites"):
        run_git(
            remote.clone,
            ["push", url, "HEAD:refs/heads/rewrite-1"],
            secrets.token_urlsafe(48),
            url=url,
        )
    assert remote.branch("rewrite-1") is None


def test_token_is_never_an_argument(remote: Remote, recorded_argv: list[list[str]]) -> None:
    token = secrets.token_urlsafe(48)
    url = str(remote.bare)
    run_git(remote.clone, ["ls-remote", url], token, url=url)
    assert recorded_argv
    assert all(token not in arg for argv in recorded_argv for arg in argv)


def test_askpass_must_be_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plain = tmp_path / "askpass.py"
    plain.write_text("")
    monkeypatch.setattr(askpass, "ASKPASS_PATH", plain)
    with pytest.raises(GitError, match="not executable"):
        run_git(tmp_path, ["ls-remote", ELSEWHERE], "t", url=ELSEWHERE)
    assert os.access(Path(askpass.__file__), os.X_OK)
