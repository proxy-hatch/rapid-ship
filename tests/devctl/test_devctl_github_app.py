"""Offline: App JWTs and installation tokens against simulated GitHub and a fake Keychain."""

from pathlib import Path

import jwt
import pytest

from devctl.github.api import GitHubError
from devctl.github.app import (
    AppError,
    KeychainMissing,
    MacKeychain,
    app_jwt,
    installation_token,
    run_guarded,
)
from devctl.process import ProcessResult
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeKeychain,
)

AppKeys = dict[str, tuple[bytes, bytes]]


def test_worker_token_is_restricted_to_one_repository_and_its_permissions(
    github: FakeGitHub, keychain: FakeKeychain
) -> None:
    token = installation_token("worker", "o/r", WORKER_ID, keychain=keychain, api_url=github.url)
    assert token == github.issued_tokens[-1]
    mint = github.calls[-1]
    assert mint.path == f"/app/installations/{WORKER_INSTALLATION}/access_tokens"
    assert mint.body == {"repositories": ["r"], "permissions": WORKER_PERMISSIONS}


def test_reviewer_token_requests_only_reviewer_permissions(
    github: FakeGitHub, keychain: FakeKeychain
) -> None:
    installation_token("reviewer", "o/r", REVIEWER_ID, keychain=keychain, api_url=github.url)
    assert github.calls[-1].body["permissions"] == REVIEWER_PERMISSIONS


def test_jwt_is_short_lived_and_names_the_app_as_a_string(app_keys: AppKeys) -> None:
    private, public = app_keys["worker"]
    token = app_jwt(private, 101, now=1_000_000.0)
    claims = jwt.decode(
        token, public, algorithms=["RS256"], options={"verify_exp": False, "verify_iat": False}
    )
    assert claims == {"iat": 999_940, "exp": 1_000_540, "iss": "101"}


def test_not_installed_is_an_app_error(github: FakeGitHub, keychain: FakeKeychain) -> None:
    with pytest.raises(AppError, match="worker App is not installed on o/other"):
        installation_token("worker", "o/other", WORKER_ID, keychain=keychain, api_url=github.url)


def test_missing_keychain_item(github: FakeGitHub) -> None:
    with pytest.raises(KeychainMissing, match="rapid-ship/worker-app"):
        installation_token(
            "worker", "o/r", WORKER_ID, keychain=FakeKeychain({}), api_url=github.url
        )


def test_missing_key_message_names_the_tagged_rapid_ship_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship" / "kit.lock").write_text(
        'kit_version = "0.2.0"\nstack = "agnostic"\n'
    )

    def missing() -> int:
        raise KeychainMissing("Keychain item rapid-ship/worker-app not found")

    assert run_guarded(missing, root=tmp_path) == 2
    assert (
        "Keychain item rapid-ship/worker-app not found; run uvx --from "
        "git+https://github.com/proxy-hatch/rapid-ship@v0.2.0 rapid-ship app"
    ) in capsys.readouterr().err


def test_mint_failure_text_has_no_key_material(github: FakeGitHub, keychain: FakeKeychain) -> None:
    github.route(
        "POST",
        r"/app/installations/\d+/access_tokens",
        lambda call, _: (
            422,
            {"message": "The permissions requested are not granted to this installation."},
        ),
    )
    with pytest.raises(GitHubError) as caught:
        installation_token("worker", "o/r", WORKER_ID, keychain=keychain, api_url=github.url)
    assert "BEGIN" not in str(caught.value)


def test_mac_keychain_decodes_hex_output_and_maps_exit_44(app_keys: AppKeys) -> None:
    pem = app_keys["worker"][0]
    seen: list[list[str]] = []

    def found(argv: list[str]) -> ProcessResult:
        seen.append(argv)
        return ProcessResult(argv, 0, pem.hex() + "\n", "", 0.0)

    assert MacKeychain(run=found).read("rapid-ship/worker-app") == pem
    assert seen == [["security", "find-generic-password", "-s", "rapid-ship/worker-app", "-w"]]
    with pytest.raises(KeychainMissing):
        MacKeychain(run=lambda argv: ProcessResult(argv, 44, "", "not found", 0.0)).read("s")
    with pytest.raises(AppError) as caught:
        MacKeychain(run=lambda argv: ProcessResult(argv, 0, "not a key\n", "", 0.0)).read("s")
    assert "not a key" not in str(caught.value)


def test_rapid_ship_and_devctl_agree_on_services_and_permissions() -> None:
    from devctl.github import app
    from rapid_ship import github_app

    assert github_app.KEYCHAIN_SERVICE == app.KEYCHAIN_SERVICE
    assert github_app.APP_PERMISSIONS == app.APP_PERMISSIONS
