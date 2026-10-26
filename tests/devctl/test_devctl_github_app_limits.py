"""Offline: unusable keys, failed Keychain reads, odd GitHub replies and run_guarded's errors.

GitHub is simulated by github_fakes and the Keychain by a fake reader; every key is a test key.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from check_workspace import project_settings
from devctl.github.api import API_URL, GitHubError
from devctl.github.app import (
    AppError,
    GitHubAccess,
    KeychainMissing,
    MacKeychain,
    app_jwt,
    installation,
    installation_token,
    project_access,
    run_guarded,
)
from devctl.process import ProcessResult
from devctl.settings import SettingsError
from github_fakes import (
    REVIEWER_ID,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeKeychain,
)

AppKeys = dict[str, tuple[bytes, bytes]]


@pytest.mark.parametrize("which", ["public key", "cut private key"])
def test_a_key_that_cannot_sign_is_an_app_error(app_keys: AppKeys, which: str) -> None:
    private, public = app_keys["worker"]
    key = public if which == "public key" else private[:200]
    with pytest.raises(AppError) as caught:
        app_jwt(key, WORKER_ID)
    assert "BEGIN" not in str(caught.value)


@pytest.mark.parametrize(
    "result",
    [
        ProcessResult([], -9, "", "", 120.0, timed_out=True),
        ProcessResult([], 44, "", "", 120.0, timed_out=True),
        ProcessResult([], 0, "2d2d", "", 0.1, stdout_truncated=True),
        ProcessResult([], 1, "", "security: SecKeychainSearchCopyNext failed", 0.1),
    ],
    ids=["timed out", "timed out with 44", "cut output", "other exit"],
)
def test_a_failed_keychain_read_is_an_app_error_without_output(result: ProcessResult) -> None:
    with pytest.raises(AppError) as caught:
        MacKeychain(run=lambda argv: result).read("rapid-ship/worker-app/101")
    assert not isinstance(caught.value, KeychainMissing)
    assert str(caught.value) == "could not read Keychain item rapid-ship/worker-app/101"


def test_a_keychain_tool_that_cannot_start_is_an_app_error() -> None:
    def absent(argv: list[str]) -> ProcessResult:
        raise FileNotFoundError(2, "No such file or directory", argv[0])

    with pytest.raises(AppError, match="could not read Keychain item s"):
        MacKeychain(run=absent).read("s")


def test_a_jwt_signed_for_another_app_is_refused(github: FakeGitHub, app_keys: AppKeys) -> None:
    # The item named for the Reviewer App's ID holds the Worker key, which then signs as the
    # Reviewer App, so GitHub cannot verify the signature.
    keychain = FakeKeychain({f"rapid-ship/worker-app/{REVIEWER_ID}": app_keys["worker"][0]})
    with pytest.raises(GitHubError) as caught:
        installation_token("worker", "o/r", REVIEWER_ID, keychain=keychain, api_url=github.url)
    assert caught.value.status == 401
    assert github.issued_tokens == []


def test_an_installation_without_a_numeric_id_mints_nothing(
    github: FakeGitHub, keychain: FakeKeychain
) -> None:
    github.route("GET", "/repos/o/r/installation", lambda call, _: (200, {"id": "1001/x"}))
    with pytest.raises(GitHubError, match="no numeric id"):
        installation_token("worker", "o/r", WORKER_ID, keychain=keychain, api_url=github.url)
    assert [call.method for call in github.calls] == ["GET"]


def test_installation_reports_the_granted_permissions(
    github: FakeGitHub, keychain: FakeKeychain
) -> None:
    found = installation("worker", "o/r", WORKER_ID, keychain=keychain, api_url=github.url)
    assert found["id"] == WORKER_INSTALLATION
    assert found["permissions"] == WORKER_PERMISSIONS


def test_github_access_mints_once_and_reuses_the_token(
    github: FakeGitHub, keychain: FakeKeychain
) -> None:
    access = GitHubAccess("o/r", api_url=github.url, keychain=keychain)
    token = access.token("worker", WORKER_ID)
    github.route("GET", "/repos/o/r", lambda call, _: (200, {"full_name": "o/r"}))
    assert access.api(token).request("GET", "/repos/o/r") == {"full_name": "o/r"}
    assert github.calls[-1].headers["Authorization"] == f"Bearer {token}"
    assert github.issued_tokens == [token]


def test_project_access_needs_a_repository(tmp_path: Path) -> None:
    with pytest.raises(AppError, match="names no repository"):
        project_access(project_settings())
    access = project_access(project_settings(repository="o/r"))
    assert (access.api_url, access.keychain) == (API_URL, None)
    assert access.remote == "https://github.com/o/r.git"
    bare = str(tmp_path / "bare.git")
    assert GitHubAccess("o/r", remote_url=bare).remote == bare


def _raises(error: Exception) -> Callable[[], int]:
    def action() -> int:
        raise error

    return action


@pytest.mark.parametrize(
    "error",
    [
        AppError("the worker App is not installed on o/r"),
        GitHubError(500, "boom"),
        SettingsError(".rapid-ship/project.toml: missing"),
        OSError("disk gone"),
    ],
)
def test_run_guarded_reports_known_errors_with_exit_2(
    error: Exception, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_guarded(_raises(error)) == 2
    assert capsys.readouterr().err == f"devctl: {error}\n"


def test_run_guarded_passes_the_actions_exit_code_and_other_errors() -> None:
    assert run_guarded(lambda: 1) == 1
    with pytest.raises(ValueError, match="a bug"):
        run_guarded(_raises(ValueError("a bug")))


def test_missing_key_message_stays_as_raised_without_a_readable_lock(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = KeychainMissing("rapid-ship/worker-app/101", "worker")
    assert run_guarded(_raises(missing), root=tmp_path) == 2  # tmp_path has no kit.lock
    assert run_guarded(_raises(missing)) == 2
    expected = (
        "devctl: Keychain item rapid-ship/worker-app/101 not found; in the App's settings on "
        "GitHub, open Credentials, then Key pairs, and click New key to generate a private key; "
        "then run rapid-ship app --import-key worker with the key on stdin\n"
    )
    assert capsys.readouterr().err == expected * 2
