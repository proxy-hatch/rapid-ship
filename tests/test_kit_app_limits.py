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
    OWNER_READS,
    Captured,
    FakeSecurity,
    FakeStore,
    found,
    github_browser,
    http_get,
    serve_conversions,
)

from rapid_ship import cli
from rapid_ship.app_flow import app_manifest, create_app
from rapid_ship.app_keychain import AppSetupError, MacKeychainStore, StoredApp, run_command
from rapid_ship.github_app import (
    GitHubNotFound,
    OwnerGet,
    current_repository,
    gh_owner_get,
    run_app,
)


def owner_reads(path: str) -> object:
    return OWNER_READS[path]


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
            "worker", "o", open_browser=browser, api_url=conversions.url, timeout_seconds=10
        )
    assert answers == [400, 400, 400, 400, 200]
    assert created.app == StoredApp(11, "o-rs-worker")
    assert created.private_key == conversions.pem_for("o-rs-worker")
    # The exchange carries no credential, as Probot's does.
    assert conversions.requests == [("/app-manifests/o-rs-worker/conversions", None)]
    assert "http://127.0.0.1:" in capsys.readouterr().out


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
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FakeStore()
    with serve_conversions() as conversions:
        conversions.status = status
        conversions.changes = changes
        code = run_app(
            "o/r",
            store=store,
            owner_get=owner_reads,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 2
    assert store.keys == {}
    out, err = capsys.readouterr()
    assert message in err
    assert "delete the App at https://github.com/settings/apps and run rapid-ship app again" in err
    assert "BEGIN" not in out + err
    assert "client-secret" not in out + err


def test_a_key_github_returned_but_rapid_ship_could_not_store_names_the_app_to_delete(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FullStore(FakeStore):
        def add(self, service: str, app: StoredApp, private_key: bytes) -> None:
            raise AppSetupError(f"could not write Keychain item {service}")

    with serve_conversions() as conversions:
        code = run_app(
            "o/r",
            store=FullStore(),
            owner_get=owner_reads,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 2
    err = capsys.readouterr().err
    assert "could not write Keychain item rapid-ship/worker-app/11" in err
    assert "https://github.com/settings/apps/o-rs-worker/advanced" in err


def test_a_permission_mismatch_names_the_settings_page_and_still_creates_the_reviewer(
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = FakeStore()
    with serve_conversions() as conversions:
        conversions.permissions = {"contents": "write", "metadata": "read"}
        code = run_app(
            "o/r",
            store=store,
            owner_get=owner_reads,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
    assert code == 1
    assert sorted(store.keys) == ["rapid-ship/reviewer-app/12", "rapid-ship/worker-app/11"]
    out = capsys.readouterr().out
    assert "fix the permissions at https://github.com/settings/apps/o-rs-worker/permissions" in out
    assert "https://github.com/settings/apps/o-rs-reviewer/permissions" in out


def test_only_the_missing_app_is_created(capsys: pytest.CaptureFixture[str]) -> None:
    store = FakeStore()
    store.apps["rapid-ship/worker-app/7"] = StoredApp(7, "o-old-worker")
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


def test_an_organization_is_refused_even_when_gh_could_act_for_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reads = {**OWNER_READS, "user": {"login": "org"}}  # cannot happen; shows the type rule
    assert run_refused("org/r", reads.__getitem__) == (1, [], {})
    assert "rapid-ship: refused: org/r belongs to the organization org" in capsys.readouterr().err


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
    ],
)
def test_an_unexpected_owner_read_is_an_error(
    reads: dict[str, object], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_refused("o/r", reads.__getitem__) == (2, [], {})
    assert "rapid-ship: GitHub's record of " in capsys.readouterr().err


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
