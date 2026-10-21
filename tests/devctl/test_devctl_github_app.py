"""Offline: App JWTs and installation tokens against simulated GitHub and a fake Keychain."""

from pathlib import Path

import jwt
import pytest

from devctl.github.api import GitHubError
from devctl.github.app import (
    AppError,
    GitHubAccess,
    KeychainMissing,
    MacKeychain,
    app_jwt,
    installation_token,
    keychain_private_key,
    keychain_service,
    run_guarded,
)
from devctl.process import ProcessResult
from devctl.settings import ROLES, Role, load_project
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


def test_each_key_lives_in_an_item_named_by_its_role_and_app_id() -> None:
    assert keychain_service("worker", 5376519) == "rapid-ship/worker-app/5376519"
    assert keychain_service("reviewer", 5376520) == "rapid-ship/reviewer-app/5376520"


def test_the_key_is_read_from_the_item_of_the_app_that_github_records(
    tmp_path: Path, github: FakeGitHub, app_keys: AppKeys
) -> None:
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship" / "project.toml").write_text(
        'stack = "agnostic"\n[github]\nrepository = "o/r"\n'
        'worker_app_id = 5376519\nworker_app_slug = "o-rs-worker"\n'
        'reviewer_app_id = 5376520\nreviewer_app_slug = "o-rs-reviewer"\n'
    )
    worker = load_project(tmp_path).worker_app
    assert worker is not None
    github.add_app(worker.id, worker.slug, app_keys["worker"][1])
    github.install(worker.id, "o/r", WORKER_PERMISSIONS, 3003)
    seen: list[list[str]] = []

    def security(argv: list[str]) -> ProcessResult:
        seen.append(argv)
        return ProcessResult(argv, 0, app_keys["worker"][0].hex() + "\n", "", 0.0)

    access = GitHubAccess("o/r", api_url=github.url, keychain=MacKeychain(run=security))
    assert access.token("worker", worker.id) == github.issued_tokens[-1]
    assert seen == [
        ["security", "find-generic-password", "-s", "rapid-ship/worker-app/5376519", "-w"]
    ]


@pytest.mark.parametrize(("role", "app_id"), [("worker", WORKER_ID), ("reviewer", REVIEWER_ID)])
def test_a_key_kept_only_under_the_old_name_is_missing(
    github: FakeGitHub, app_keys: AppKeys, role: Role, app_id: int
) -> None:
    # Plan 4 stored each key as rapid-ship/<role>-app; devctl reads only the name with the ID.
    old = FakeKeychain({f"rapid-ship/{role}-app": app_keys[role][0]})
    with pytest.raises(KeychainMissing) as caught:
        installation_token(role, "o/r", app_id, keychain=old, api_url=github.url)
    assert str(caught.value) == (
        f"Keychain item rapid-ship/{role}-app/{app_id} not found; run rapid-ship app, "
        f"which re-stores a key kept under rapid-ship/{role}-app, "
        f"or rapid-ship app --import-key {role}"
    )
    assert github.calls == []


def test_missing_key_message_names_the_tagged_rapid_ship_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".rapid-ship").mkdir()
    (tmp_path / ".rapid-ship" / "kit.lock").write_text(
        'kit_version = "0.2.0"\nstack = "agnostic"\n'
    )

    def read_key() -> int:
        keychain_private_key("worker", 5376519, FakeKeychain({}))
        return 0

    assert run_guarded(read_key, root=tmp_path) == 2
    tagged = "uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.2.0 rapid-ship app"
    assert capsys.readouterr().err == (
        f"devctl: Keychain item rapid-ship/worker-app/5376519 not found; run {tagged}, "
        f"which re-stores a key kept under rapid-ship/worker-app, "
        f"or {tagged} --import-key worker\n"
    )


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

    assert MacKeychain(run=found).read("rapid-ship/worker-app/101") == pem
    assert seen == [["security", "find-generic-password", "-s", "rapid-ship/worker-app/101", "-w"]]
    with pytest.raises(KeychainMissing) as missing:
        MacKeychain(run=lambda argv: ProcessResult(argv, 44, "", "not found", 0.0)).read("s")
    assert str(missing.value) == "Keychain item s not found"  # a bare read knows no role
    with pytest.raises(AppError) as caught:
        MacKeychain(run=lambda argv: ProcessResult(argv, 0, "not a key\n", "", 0.0)).read("s")
    assert "not a key" not in str(caught.value)


def test_rapid_ship_and_devctl_agree_on_services_and_permissions() -> None:
    from devctl.github import app
    from rapid_ship import app_flow, app_keychain

    for role in ROLES:
        assert app_keychain.keychain_service(role, 7) == app.keychain_service(role, 7)
    assert app_flow.APP_PERMISSIONS == app.APP_PERMISSIONS
