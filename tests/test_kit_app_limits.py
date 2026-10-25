"""Offline: rapid-ship app's refusals and failures, with a simulated browser, GitHub and Keychain.

gh is a fake executable on PATH.
"""

import html
import json
import os
import subprocess
from http.client import HTTPConnection
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from test_kit_app import (
    ORG_ADMIN,
    OWNER_READS,
    Captured,
    FakeSecurity,
    FakeStore,
    found,
    github_browser,
    http_get,
    reads,
    rsa_key,
    serve_conversions,
)

from rapid_ship import cli
from rapid_ship.app_flow import AppOwner, app_manifest, create_app
from rapid_ship.app_keychain import AppSetupError, MacKeychainStore, StoredApp, run_command
from rapid_ship.github_app import (
    GitHubNotFound,
    OwnerGet,
    current_repository,
    gh_owner_get,
    run_app,
)

# A repository of each kind of owner, and the GitHub page that lists that owner's Apps. gh's
# login owns o/r and is an admin of the organisation org.
APP_PAGES = [
    ("o/r", "https://github.com/settings/apps"),
    ("org/r", "https://github.com/organizations/org/settings/apps"),
]
ADMIN_READS = reads({**OWNER_READS, **ORG_ADMIN})
NOT_ADMIN = (
    "rapid-ship: refused: org/r belongs to the organisation org, and gh's login is not an admin "
    "of org: an organisation admin creates its Apps once; ask one to run rapid-ship app, or, if "
    "the Apps exist, record their IDs and run rapid-ship app --import-key <role>\n"
)


def get_as_host(url: str, host: str) -> int:
    """GET url with another Host header, as a page on a rebound domain would."""
    parts = urlsplit(url)
    connection = HTTPConnection(parts.netloc, timeout=5)
    connection.putrequest("GET", f"{parts.path}?{parts.query}", skip_host=True)
    connection.putheader("Host", host)
    connection.endheaders()
    response = connection.getresponse()
    response.read()
    return response.status


def test_the_callback_takes_only_its_state_a_plain_code_and_its_own_host(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers: list[int] = []

    def browser(start_url: str) -> None:
        _, page = http_get(start_url)
        manifest = json.loads(html.unescape(found(r'name="manifest" value="([^"]+)"', page)))
        callback = manifest["redirect_url"]
        state = html.unescape(found(r'action="([^"]+)"', page)).split("state=", 1)[1]
        assert get_as_host(start_url, "rebound.example") == 400
        answers.append(http_get(f"{callback}?code=a/b&state={state}")[0])
        answers.append(http_get(f"{callback}?code=c0de")[0])
        answers.append(http_get(f"{callback}?code=c0de&state=")[0])
        answers.append(get_as_host(f"{callback}?code=c0de&state={state}", "rebound.example"))
        answers.append(http_get(f"{callback}?code={manifest['name']}&state={state}")[0])

    with serve_conversions() as conversions:
        created = create_app(
            "worker",
            AppOwner("o", "user"),
            open_browser=browser,
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert answers == [400, 400, 400, 400, 200]
    assert created.app == StoredApp(11, "o-rs-worker")
    assert created.private_key == conversions.pem_for("o-rs-worker")
    # The exchange carries no credential, as Probot's does.
    assert conversions.requests == [("/app-manifests/o-rs-worker/conversions", None)]
    assert "http://127.0.0.1:" in capsys.readouterr().out


@pytest.mark.parametrize(("repository", "apps_page"), APP_PAGES)
@pytest.mark.parametrize(
    ("status", "changes", "message"),
    [
        (201, {"pem": "not a key"}, "returned no private key"),
        (201, {"permissions": ["contents"]}, "returned no permissions"),
        (201, {"id": "11"}, "returned no App ID"),
        (201, {"slug": "-x"}, "returned no App slug"),
        (422, {"message": "The code has expired"}, "GitHub returned 422: The code has expired"),
    ],
)
def test_a_conversion_reply_that_rapid_ship_cannot_use_stores_nothing(
    status: int,
    changes: dict[str, object],
    message: str,
    repository: str,
    apps_page: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FakeStore()
    with serve_conversions() as conversions:
        conversions.status = status
        conversions.changes = changes
        code = run_app(
            repository,
            store=store,
            owner_get=ADMIN_READS,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 2
    assert store.keys == {}
    out, err = capsys.readouterr()
    assert message in err
    assert f"delete the App at {apps_page} and run rapid-ship app again" in err
    assert "BEGIN" not in out + err
    assert "client-secret" not in out + err


@pytest.mark.parametrize(("repository", "apps_page"), APP_PAGES)
def test_a_key_github_returned_but_rapid_ship_could_not_store_names_the_app_to_delete(
    repository: str, apps_page: str, capsys: pytest.CaptureFixture[str]
) -> None:
    class FullStore(FakeStore):
        def add(self, service: str, app: StoredApp, private_key: bytes) -> None:
            raise AppSetupError(f"could not write Keychain item {service}")

    with serve_conversions() as conversions:
        code = run_app(
            repository,
            store=FullStore(),
            owner_get=ADMIN_READS,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 2
    err = capsys.readouterr().err
    assert "could not write Keychain item rapid-ship/worker-app/11" in err
    owner = repository.split("/")[0]
    assert f"delete the App at {apps_page}/{owner}-rs-worker/advanced" in err


@pytest.mark.parametrize(("repository", "apps_page"), APP_PAGES)
def test_a_permission_mismatch_names_the_settings_page_and_still_creates_the_reviewer(
    repository: str, apps_page: str, capsys: pytest.CaptureFixture[str]
) -> None:
    store = FakeStore()
    with serve_conversions() as conversions:
        conversions.permissions = {"contents": "write", "metadata": "read"}
        code = run_app(
            repository,
            store=store,
            owner_get=ADMIN_READS,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 1
    assert sorted(store.keys) == ["rapid-ship/reviewer-app/12", "rapid-ship/worker-app/11"]
    out = capsys.readouterr().out
    owner = repository.split("/")[0]
    assert f"fix the permissions at {apps_page}/{owner}-rs-worker/permissions" in out
    assert f"{apps_page}/{owner}-rs-reviewer/permissions" in out


def test_only_the_missing_app_is_created(capsys: pytest.CaptureFixture[str]) -> None:
    store = FakeStore()
    store.apps["rapid-ship/worker-app/7"] = StoredApp(7, "o-old-worker")
    # A public App, which GitHub shows to gh.
    answers = {**OWNER_READS, "apps/o-old-worker": {"id": 7, "owner": {"login": "o", "id": 1}}}
    captured: Captured = []
    with serve_conversions() as conversions:
        code = run_app(
            "o/r",
            store=store,
            owner_get=answers.__getitem__,
            open_browser=github_browser(captured),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 0
    assert [manifest["name"] for _, manifest in captured] == ["o-rs-reviewer"]
    assert list(store.keys) == ["rapid-ship/reviewer-app/12"]
    out = capsys.readouterr().out
    assert "Worker App: ID 7 (o-old-worker)" in out
    assert "Reviewer App: ID 12 (o-rs-reviewer)" in out
    assert "Record each App's ID and slug, as printed above, in .rapid-ship/project.toml" in out
    assert 'worker_app_slug = "o-old-worker"' in out


@pytest.mark.parametrize(
    ("status", "changes", "message"),
    [
        (500, {"message": "Server Error"}, "GitHub returned 500: Server Error"),
        (200, {"owner": None}, "GitHub's record of App 11 has no App ID, slug or owner ID"),
    ],
    ids=["server error", "no owner"],
)
def test_a_get_app_reply_that_rapid_ship_cannot_use_changes_nothing(
    status: int, changes: dict[str, object], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """GET /app under the key of an item whose App GitHub does not show to gh fails, or answers
    without the App's owner."""
    store = FakeStore()
    app, name = StoredApp(11, "o-rs-worker"), "rapid-ship/worker-app/11"
    store.apps[name], store.keys[name] = app, rsa_key("o/worker")
    before = dict(store.apps)
    opened: list[str] = []
    with serve_conversions() as api:
        api.register(store.keys[name], app, {"login": "o", "id": 1, "type": "User"})
        api.app_status, api.app_changes = status, changes
        code = run_app(
            "o/r",
            store=store,
            owner_get=reads(OWNER_READS),
            open_browser=opened.append,
            api_url=api.url,
            timeout_seconds=0.1,
        )
    assert code == 2
    assert (store.apps, opened) == (before, [])
    out, err = capsys.readouterr()
    assert (out, err) == ("", f"rapid-ship: {message}\n")


def run_refused(repository: str, owner_get: OwnerGet) -> tuple[int, list[str], dict[str, bytes]]:
    """Run app with a browser that never calls back, so a run that should stop ends in 0.1 s."""
    opened: list[str] = []
    store = FakeStore()
    code = run_app(
        repository,
        store=store,
        owner_get=owner_get,
        open_browser=opened.append,
        timeout_seconds=0.1,
    )
    return code, opened, store.keys


def test_a_repository_of_another_user_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    reads = {
        **OWNER_READS,
        "repos/u/r": {"id": 5, "owner": {"login": "u", "id": 6, "type": "User"}},
    }
    assert run_refused("u/r", reads.__getitem__) == (1, [], {})
    err = capsys.readouterr().err
    assert "rapid-ship: refused: u/r belongs to u, and gh is signed in as o" in err


@pytest.mark.parametrize(
    "membership",
    [
        None,
        {"state": "active", "role": "member"},
        {"state": "pending", "role": "admin"},
        {"state": "active", "role": "billing_manager"},
        ["admin"],
    ],
    ids=["not a member", "member", "pending admin", "billing manager", "not a record"],
)
def test_an_organisation_member_who_is_not_an_admin_creates_no_app(
    membership: object, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub answers 404 when the login is not a member of the organisation."""
    answers = dict(OWNER_READS)
    if membership is not None:
        answers["user/memberships/orgs/org"] = membership
    log: list[str] = []
    assert run_refused("org/r", reads(answers, log)) == (1, [], {})
    assert log == ["repos/org/r", "user/memberships/orgs/org"]
    out, err = capsys.readouterr()
    assert (out, err) == ("", NOT_ADMIN)


def test_a_member_who_is_not_an_admin_is_refused_before_any_key_is_re_stored(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """GitHub shows the organisation's Worker App, whose key is in the old Keychain item named
    without the App ID, and the Reviewer App must be created."""
    store = FakeStore()
    old = "rapid-ship/worker-app"
    store.apps[old] = StoredApp(11, "org-rs-worker")
    store.keys[old] = b"-----BEGIN TEST KEY-----\nnot a real key\n-----END TEST KEY-----\n"
    answers = {**OWNER_READS, "apps/org-rs-worker": {"id": 11, "owner": {"login": "org", "id": 4}}}
    opened: list[str] = []
    code = run_app(
        "org/r",
        store=store,
        owner_get=reads(answers),
        open_browser=opened.append,
        timeout_seconds=0.1,
    )
    assert (code, opened, list(store.apps)) == (1, [], [old])
    assert capsys.readouterr().err == NOT_ADMIN


def test_a_membership_read_that_fails_otherwise_is_an_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def forbidden(path: str) -> object:
        if path == "user/memberships/orgs/org":
            raise AppSetupError(f"gh api {path} failed: gh: Forbidden (HTTP 403)")
        return OWNER_READS[path]

    assert run_refused("org/r", forbidden) == (2, [], {})
    assert capsys.readouterr().err == (
        "rapid-ship: gh api user/memberships/orgs/org failed: gh: Forbidden (HTTP 403)\n"
    )


def test_an_organisation_developer_with_recorded_apps_and_no_key_is_told_to_import_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    recorded = {
        "worker": StoredApp(11, "org-rs-worker"),
        "reviewer": StoredApp(12, "org-rs-reviewer"),
    }
    log: list[str] = []
    opened: list[str] = []
    store = FakeStore()
    code = run_app(
        "org/r",
        store=store,
        owner_get=reads(OWNER_READS, log),
        open_browser=opened.append,
        recorded=recorded,
        timeout_seconds=0.1,
    )
    assert (code, log, opened, store.apps) == (1, ["repos/org/r"], [], {})
    err = capsys.readouterr().err
    assert "then run rapid-ship app --import-key worker with the key on stdin\n" in err
    assert "then run rapid-ship app --import-key reviewer with the key on stdin\n" in err


@pytest.mark.parametrize("repository", ["o", "o/r/x", "o/../r", "o/r?per_page=1", "/r"])
def test_a_repository_that_is_not_owner_slash_name_reads_nothing(
    repository: str, capsys: pytest.CaptureFixture[str]
) -> None:
    reads: list[str] = []

    def record(path: str) -> object:
        reads.append(path)
        return OWNER_READS[path]

    assert run_refused(repository, record) == (2, [], {})
    assert reads == []
    assert "OWNER/NAME" in capsys.readouterr().err


@pytest.mark.parametrize(
    "reads",
    [
        {"repos/o/r": {"id": 2, "owner": "o"}, "user": {"login": "o"}},
        {"repos/o/r": {"id": True, "owner": {"login": "o", "id": 1, "type": "User"}}},
        {"repos/o/r": OWNER_READS["repos/o/r"], "user": ["o"]},
        {"repos/o/r": {"id": 2, "owner": {"login": "o", "id": 1, "type": "Enterprise"}}},
        # The organisation's login goes into GitHub paths and URLs.
        {"repos/o/r": {"id": 2, "owner": {"login": "o/../x", "id": 1, "type": "Organization"}}},
    ],
)
def test_an_unexpected_owner_read_is_an_error(
    reads: dict[str, object], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_refused("o/r", reads.__getitem__) == (2, [], {})
    assert "rapid-ship: GitHub's record of " in capsys.readouterr().err


def test_exists_reads_no_secret_and_counts_an_item_rapid_ship_did_not_write() -> None:
    security = FakeSecurity()
    store = MacKeychainStore(run=security)
    assert store.exists("rapid-ship/worker-app/11") is False
    security.items["rapid-ship/worker-app/11"] = {"-X": "2d2d"}  # added by hand: no -a or -j
    assert store.exists("rapid-ship/worker-app/11") is True
    looked_up = ["security", "find-generic-password", "-s", "rapid-ship/worker-app/11"]
    assert security.argvs == [looked_up, looked_up]

    def locked(argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv, 51, "", "security: User interaction is not allowed."
        )

    with pytest.raises(
        AppSetupError, match="could not read Keychain item rapid-ship/worker-app/11"
    ):
        MacKeychainStore(run=locked).exists("rapid-ship/worker-app/11")


def test_find_reads_no_secret_and_refuses_an_item_rapid_ship_did_not_write() -> None:
    security = FakeSecurity()
    store = MacKeychainStore(run=security)
    assert store.find("rapid-ship/worker-app") is None
    assert security.argvs == [["security", "find-generic-password", "-s", "rapid-ship/worker-app"]]

    def foreign(argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, 'attributes:\n    "acct"<blob>="me"\n', "")

    with pytest.raises(AppSetupError, match="was not written by rapid-ship app"):
        MacKeychainStore(run=foreign).find("rapid-ship/worker-app")

    def locked(argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            argv, 51, "", "security: User interaction is not allowed."
        )

    with pytest.raises(AppSetupError, match="could not read Keychain item rapid-ship/worker-app"):
        MacKeychainStore(run=locked).find("rapid-ship/worker-app")


def test_add_checks_the_item_it_wrote_and_never_reports_the_key() -> None:
    class Ignoring(FakeSecurity):
        """security -i exits 0 without storing the item."""

        def __call__(
            self, argv: list[str], input_text: str | None
        ) -> subprocess.CompletedProcess[str]:
            if argv == ["security", "-i"]:
                self.argvs.append(argv)
                return subprocess.CompletedProcess(argv, 0, "", "")
            return super().__call__(argv, input_text)

    pem = b"-----BEGIN TEST KEY-----\nnot a real key\n-----END TEST KEY-----\n"
    with pytest.raises(AppSetupError) as caught:
        MacKeychainStore(run=Ignoring()).add("rapid-ship/worker-app", StoredApp(11, "s"), pem)
    assert "rapid-ship/worker-app" in str(caught.value)
    assert pem.hex() not in str(caught.value)

    class Other(FakeSecurity):
        """The item holds another key."""

        def __call__(
            self, argv: list[str], input_text: str | None
        ) -> subprocess.CompletedProcess[str]:
            result = super().__call__(argv, input_text)
            if argv[4:] == ["-w"]:
                return subprocess.CompletedProcess(argv, 0, b"other".hex() + "\n", "")
            return result

    with pytest.raises(AppSetupError, match="does not hold the key and App just written"):
        MacKeychainStore(run=Other()).add("rapid-ship/worker-app", StoredApp(11, "s"), pem)

    calls: list[list[str]] = []

    def failing(argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", f"echo {input_text}")

    with pytest.raises(AppSetupError) as caught:
        MacKeychainStore(run=failing).add("rapid-ship/worker-app", StoredApp(11, "s"), pem)
    assert str(caught.value) == "could not write Keychain item rapid-ship/worker-app"
    assert calls == [["security", "-i"]]


def test_add_never_updates_an_existing_item() -> None:
    """GitHub shows an App's key once, so a key already stored must survive another add."""
    security = FakeSecurity()
    old = b"-----BEGIN TEST KEY-----\nthe key already stored\n-----END TEST KEY-----\n"
    held = {"-a": "11", "-j": "s", "-X": old.hex()}
    security.items["rapid-ship/worker-app"] = dict(held)
    new = b"-----BEGIN TEST KEY-----\nnot a real key\n-----END TEST KEY-----\n"
    with pytest.raises(AppSetupError) as caught:
        MacKeychainStore(run=security).add("rapid-ship/worker-app", StoredApp(12, "t"), new)
    assert str(caught.value) == "could not write Keychain item rapid-ship/worker-app"
    assert security.items == {"rapid-ship/worker-app": held}
    [line] = security.inputs
    assert "-U" not in line.split()


def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str) -> Path:
    """Put a gh on PATH that records its arguments, one a line, then runs body."""
    directory = tmp_path / "bin"
    directory.mkdir()
    gh = directory / "gh"
    record = tmp_path / "gh-args"
    gh.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\n{body}\n")
    gh.chmod(0o755)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return record


def test_gh_owner_get_reads_with_get_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record = fake_gh(tmp_path, monkeypatch, """echo '{"login": "o"}'""")
    assert gh_owner_get("user") == {"login": "o"}
    assert record.read_text().splitlines() == ["api", "--method", "GET", "user"]


def test_gh_owner_get_reports_gh_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_gh(tmp_path, monkeypatch, "echo 'gh: Not Found (HTTP 404)' >&2\nexit 1")
    with pytest.raises(AppSetupError, match=r"gh: Not Found \(HTTP 404\)"):
        gh_owner_get("repos/o/missing")


def test_gh_owner_get_refuses_output_that_is_not_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_gh(tmp_path, monkeypatch, "echo 'Welcome to GitHub'")
    with pytest.raises(AppSetupError, match="JSON"):
        gh_owner_get("user")


def test_current_repository_asks_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    record = fake_gh(tmp_path, monkeypatch, "echo o/r")
    assert current_repository() == "o/r"
    assert record.read_text().splitlines() == [
        "repo",
        "view",
        "--json",
        "nameWithOwner",
        "--jq",
        ".nameWithOwner",
    ]


def test_current_repository_names_the_option_when_gh_cannot_tell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_gh(tmp_path, monkeypatch, "echo 'no git remotes found' >&2\nexit 1")
    with pytest.raises(AppSetupError, match=r"no git remotes found.*--repository"):
        current_repository()


def test_run_command_reports_a_program_that_cannot_start(tmp_path: Path) -> None:
    with pytest.raises(AppSetupError, match=r"could not run .*FileNotFoundError"):
        run_command([str(tmp_path / "missing")])


def test_cli_app_without_repository_uses_the_current_repository(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[str] = []

    def record(repository: str, **kwargs: object) -> int:
        calls.append(repository)
        return 1

    monkeypatch.setattr(cli, "run_app", record)
    monkeypatch.setattr(cli, "current_repository", lambda: "o/r")
    monkeypatch.chdir(tmp_path)
    assert cli.main(["app"]) == 1
    assert calls == ["o/r"]

    def unknown() -> str:
        raise AppSetupError("gh repo view failed")

    monkeypatch.setattr(cli, "current_repository", unknown)
    assert cli.main(["app"]) == 2
    assert calls == ["o/r"]
    assert capsys.readouterr().err == "rapid-ship: gh repo view failed\n"


def test_cli_app_help_names_the_repository_option(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["app", "--help"])
    assert caught.value.code == 0
    assert "--repository OWNER/NAME" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("login", "name"),
    [
        ("o", "o-rs-reviewer"),
        ("a" * 39, "a" * 22 + "-rs-reviewer"),
        ("abcdefghijklmnopqrstu-vw", "abcdefghijklmnopqrstu-rs-reviewer"),
    ],
)
def test_the_app_name_fits_github_34_characters(login: str, name: str) -> None:
    manifest = app_manifest("reviewer", login, "http://127.0.0.1:1/callback")
    assert manifest["name"] == name
    assert len(name) <= 34
    assert manifest["url"] == "https://github.com/proxy-hatch/rapid-ship"


@pytest.mark.parametrize(
    ("stderr", "not_found"),
    [("gh: Not Found (HTTP 404)", True), ("gh: Bad credentials (HTTP 401)", False)],
)
def test_gh_owner_get_tells_a_404_from_other_errors(
    stderr: str, not_found: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_gh(tmp_path, monkeypatch, f"echo '{stderr}' >&2\nexit 1")
    with pytest.raises(AppSetupError) as caught:
        gh_owner_get("apps/gone")
    assert isinstance(caught.value, GitHubNotFound) is not_found
    assert str(caught.value) == f"gh api apps/gone failed: {stderr}"
