"""Offline: rapid-ship app --import-key with a simulated GitHub API and a fake `security`.

Where the Apps exist, such as an organisation's, a developer generates their own private key for
an App that .rapid-ship/project.toml records, and gives it on stdin. GET /app, under a token that
the key signs, must show that App before the key is stored. No test reads the real Keychain or
contacts GitHub.
"""

import io
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
)
from test_kit_app import FakeConversions, FakeSecurity, rsa_key, serve_conversions

from rapid_ship import cli
from rapid_ship.app_import import MAX_KEY_BYTES, import_key
from rapid_ship.app_keychain import MacKeychainStore, StoredApp, keychain_service

ROLES = ("worker", "reviewer")
TITLES = {"worker": "Worker App", "reviewer": "Reviewer App"}
# The organisation's Apps, as the repository's .rapid-ship/project.toml records them.
APPS = {"worker": StoredApp(11, "org-rs-worker"), "reviewer": StoredApp(12, "org-rs-reviewer")}
ORGANISATION = {"login": "org", "id": 4, "type": "Organization"}
SETTINGS = """[github]
repository = "org/r"
worker_app_id = 11
worker_app_slug = "org-rs-worker"
reviewer_app_id = 12
reviewer_app_slug = "org-rs-reviewer"
"""


# The refusal of input that does not start as a PEM key, which devctl would not read back.
NO_PEM = "stdin holds no PEM private key: it must start with a -----BEGIN line"
UNREADABLE = "the key is not a readable, unencrypted PEM private key"


class Terminal(io.BytesIO):
    """stdin that is a terminal, where the developer would paste the key."""

    def isatty(self) -> bool:
        return True

    def read(self, size: int | None = -1, /) -> bytes:  # noqa: V107  # rs-exception: EX-23
        raise AssertionError("a terminal on stdin is never read")


@dataclass
class Developer:
    """A developer's machine: the repository's work tree, `security` and GitHub's API."""

    root: Path
    security: FakeSecurity
    api: FakeConversions
    monkeypatch: pytest.MonkeyPatch

    def run(self, role: str, stdin: bytes | io.BytesIO) -> int:
        """rapid-ship app --import-key role, with stdin as its standard input."""
        stream = stdin if isinstance(stdin, io.BytesIO) else io.BytesIO(stdin)
        self.monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(stream))
        return cli.main(["app", "--repository", "org/r", "--import-key", role])

    def stored_nothing(self) -> bool:
        return self.security.inputs == [] and self.security.items == {}


@pytest.fixture
def developer(git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Developer]:
    (git_repo / ".rapid-ship").mkdir()
    (git_repo / ".rapid-ship" / "project.toml").write_text(SETTINGS)
    monkeypatch.chdir(git_repo)
    security = FakeSecurity()
    monkeypatch.setattr(cli, "MacKeychainStore", lambda: MacKeychainStore(run=security))

    def never(*args: object, **kwargs: object) -> int:
        raise AssertionError("--import-key creates no App and reads nothing as the owner's gh")

    monkeypatch.setattr(cli, "run_app", never)
    monkeypatch.setattr(cli, "current_repository", never)
    with serve_conversions() as api:
        monkeypatch.setattr(cli, "import_key", partial(import_key, api_url=api.url))
        yield Developer(git_repo, security, api, monkeypatch)


def leaks(developer: Developer, key: bytes, text: str) -> list[str]:
    """Each place where the key shows: an argument to `security`, or the command's output."""
    body = key.splitlines()[1].decode()  # the first line of the key's base64
    places = [
        f"argv {argv}"
        for argv in developer.security.argvs
        if any(key.hex() in arg or "BEGIN" in arg or body in arg for arg in argv)
    ]
    return places + [f"output {needle}" for needle in ("BEGIN", body) if needle in text]


@pytest.mark.parametrize("role", ROLES)
def test_a_key_github_accepts_for_the_recorded_app_is_stored(
    role: str, developer: Developer, capsys: pytest.CaptureFixture[str]
) -> None:
    app, key = APPS[role], rsa_key(f"developer/{role}")
    developer.api.register(key, app, ORGANISATION)
    assert developer.run(role, key) == 0
    service = keychain_service(role, app.app_id)
    assert developer.security.items == {
        service: {"-a": str(app.app_id), "-j": app.slug, "-X": key.hex()}
    }
    # devctl reads the item back as it was given.
    assert MacKeychainStore(run=developer.security).read_key(service) == key
    [(path, authorization)] = developer.api.requests
    assert path == "/app"
    assert authorization is not None
    token = authorization.removeprefix("Bearer ")
    assert jwt.decode(token, options={"verify_signature": False})["iss"] == str(app.app_id)
    out, err = capsys.readouterr()
    assert err == ""
    assert out == (
        f"Stored your key for the {TITLES[role]} {app.app_id} ({app.slug}) in Keychain item "
        f"{service}. rapid-ship wrote it nowhere else: delete the key file that GitHub "
        "downloaded. ./devctl doctor then checks the App's installation.\n"
    )
    assert leaks(developer, key, out + err) == []


def test_the_key_is_stored_without_the_blank_lines_around_it(developer: Developer) -> None:
    """devctl reads an item only when it starts with the PEM's BEGIN line."""
    key = rsa_key("developer/worker")
    developer.api.register(key, APPS["worker"], ORGANISATION)
    assert developer.run("worker", b"\n \r\n" + key.rstrip() + b"\n\n ") == 0
    [item] = developer.security.items.values()
    assert item["-X"] == key.hex()


@pytest.mark.parametrize(
    "settings",
    [
        SETTINGS.replace("reviewer_app_id = 12", "reviewer_app_id = 0").replace(
            '"org-rs-reviewer"', '""'
        ),
        SETTINGS.replace('repository = "org/r"', 'repository = "org/other"'),
        None,
    ],
    ids=["role not recorded", "another repository", "outside a work tree"],
)
def test_an_app_that_project_toml_does_not_record_gets_no_key(
    settings: str | None,
    developer: Developer,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if settings is None:
        (tmp_path / "elsewhere").mkdir()
        developer.monkeypatch.chdir(tmp_path / "elsewhere")
    else:
        (developer.root / ".rapid-ship" / "project.toml").write_text(settings)
    key = rsa_key("developer/reviewer")
    stdin = io.BytesIO(key)
    assert developer.run("reviewer", stdin) == 1
    assert developer.stored_nothing()
    assert (developer.api.requests, stdin.tell()) == ([], 0)
    out, err = capsys.readouterr()
    assert out == ""
    assert err == (
        "rapid-ship: .rapid-ship/project.toml records no Reviewer App for org/r, so no key can be "
        "checked against it. Run rapid-ship app --import-key reviewer in the repository's work "
        "tree once [github] records the App's ID and slug. Nothing was stored.\n"
    )


# The refusal when the Worker App 11's item exists, whoever wrote it.
EXISTS = (
    "rapid-ship: Keychain item rapid-ship/worker-app/11 already exists, and rapid-ship never "
    "replaces one; ./devctl doctor checks the key it holds. To replace a key that no longer "
    "works, delete the item with: security delete-generic-password -s "
    "rapid-ship/worker-app/11, then run this again. Nothing was stored.\n"
)


def test_an_existing_item_is_left_in_place(
    developer: Developer, capsys: pytest.CaptureFixture[str]
) -> None:
    held = {"-a": "11", "-j": "org-rs-worker", "-X": rsa_key("held/worker").hex()}
    developer.security.items["rapid-ship/worker-app/11"] = dict(held)
    key = rsa_key("developer/worker")
    developer.api.register(key, APPS["worker"], ORGANISATION)
    stdin = io.BytesIO(key)
    assert developer.run("worker", stdin) == 1
    assert developer.security.items == {"rapid-ship/worker-app/11": held}
    assert (developer.security.inputs, developer.api.requests, stdin.tell()) == ([], [], 0)
    assert capsys.readouterr() == ("", EXISTS)


def test_an_item_rapid_ship_did_not_write_is_left_in_place(
    developer: Developer, capsys: pytest.CaptureFixture[str]
) -> None:
    """An item added by hand has no App ID or slug, and devctl reads its key by name alone."""
    held = {"-X": rsa_key("held/worker").hex()}
    developer.security.items["rapid-ship/worker-app/11"] = dict(held)
    key = rsa_key("developer/worker")
    developer.api.register(key, APPS["worker"], ORGANISATION)
    stdin = io.BytesIO(key)
    assert developer.run("worker", stdin) == 1
    assert developer.security.items == {"rapid-ship/worker-app/11": held}
    assert (developer.security.inputs, developer.api.requests, stdin.tell()) == ([], [], 0)
    assert capsys.readouterr() == ("", EXISTS)


@pytest.mark.parametrize(
    ("stdin", "message", "consumed"),
    [
        (b"", "stdin holds no key", 0),
        (b"\n \n", "stdin holds no key", 3),
        (b"A" * (MAX_KEY_BYTES + 1), "stdin holds more than 64 KiB, more than any App key", None),
        (b"A" * (MAX_KEY_BYTES * 16), "stdin holds more than 64 KiB, more than any App key", None),
        (b"A" * MAX_KEY_BYTES, NO_PEM, MAX_KEY_BYTES),
    ],
    ids=["empty", "blank", "one byte over 64 KiB", "1 MiB", "64 KiB"],
)
def test_stdin_that_holds_no_key_stores_nothing(
    stdin: bytes,
    message: str,
    consumed: int | None,
    developer: Developer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    stream = io.BytesIO(stdin)
    assert developer.run("worker", stream) == 1
    assert developer.stored_nothing()
    assert developer.api.requests == []
    # At most one byte over the limit is read.
    assert stream.tell() == (MAX_KEY_BYTES + 1 if consumed is None else consumed)
    assert capsys.readouterr() == ("", f"rapid-ship: {message}. Nothing was stored.\n")


def test_a_terminal_on_stdin_is_refused_before_it_is_read(
    developer: Developer, capsys: pytest.CaptureFixture[str]
) -> None:
    """A key pasted into a terminal would show on the screen, and a terminal waits for input."""
    assert developer.run("worker", Terminal()) == 1
    assert developer.stored_nothing()
    assert developer.api.requests == []
    assert capsys.readouterr() == (
        "",
        "rapid-ship: give the key on stdin, as in: rapid-ship app --import-key worker "
        "< the-downloaded.private-key.pem. Nothing was stored.\n",
    )


def test_a_closed_stdin_stores_nothing(
    developer: Developer, capsys: pytest.CaptureFixture[str]
) -> None:
    """With file descriptor 0 closed, as after <&-, Python sets sys.stdin to None."""
    developer.monkeypatch.setattr(sys, "stdin", None)
    assert cli.main(["app", "--repository", "org/r", "--import-key", "worker"]) == 1
    assert developer.stored_nothing()
    assert developer.api.requests == []
    assert capsys.readouterr() == ("", "rapid-ship: stdin holds no key. Nothing was stored.\n")


def _public_key() -> bytes:
    loaded = load_pem_private_key(rsa_key("developer/worker"), password=None)
    return loaded.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)


def _encrypted_key() -> bytes:
    loaded = load_pem_private_key(rsa_key("developer/worker"), password=None)
    return loaded.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(b"passphrase")
    )


def _ec_key() -> bytes:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())


@pytest.mark.parametrize(
    ("make", "message"),
    [
        (_public_key, UNREADABLE),
        (_encrypted_key, UNREADABLE),
        (_ec_key, "the key is not an RSA private key"),
        (lambda: b"hunter2 " + rsa_key("developer/worker"), NO_PEM),
        (lambda: b"hunter2\n", NO_PEM),
    ],
    ids=["public key", "encrypted key", "EC key", "text before the key", "not a key"],
)
def test_input_that_is_no_unencrypted_rsa_private_key_stores_nothing(
    make: Callable[[], bytes],
    message: str,
    developer: Developer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert developer.run("worker", make()) == 1
    assert developer.stored_nothing()
    assert developer.api.requests == []  # refused before any call to GitHub
    out, err = capsys.readouterr()
    assert out == ""
    assert err == f"rapid-ship: {message}. Nothing was stored.\n"
    assert "hunter2" not in err


@pytest.mark.parametrize(
    ("signs_for", "changes", "message"),
    [
        (
            StoredApp(12, "org-rs-reviewer"),
            {},
            "GitHub refused a token that the key on stdin signs for the Worker App 11 "
            "(org-rs-worker): GitHub returned 401: A JSON web token could not be decoded",
        ),
        (
            APPS["worker"],
            {"id": 99},
            "GitHub shows the key's App as 99 (org-rs-worker), not the Worker App 11 "
            "(org-rs-worker) that .rapid-ship/project.toml records",
        ),
        (
            APPS["worker"],
            {"slug": "org-renamed"},
            "GitHub shows the key's App as 11 (org-renamed), not the Worker App 11 "
            "(org-rs-worker) that .rapid-ship/project.toml records",
        ),
    ],
    ids=["another App's key", "another App's ID", "another slug"],
)
def test_a_key_github_does_not_show_as_the_recorded_apps_stores_nothing(
    signs_for: StoredApp,
    changes: dict[str, object],
    message: str,
    developer: Developer,
    capsys: pytest.CaptureFixture[str],
) -> None:
    key = rsa_key("developer/other")
    developer.api.register(key, signs_for, ORGANISATION)
    developer.api.app_changes = changes
    assert developer.run("worker", key) == 1
    assert developer.stored_nothing()
    assert [path for path, _ in developer.api.requests] == ["/app"]
    out, err = capsys.readouterr()
    assert (out, err) == ("", f"rapid-ship: {message}. Nothing was stored.\n")
    assert leaks(developer, key, out + err) == []


def test_a_redirect_from_github_is_not_followed(
    developer: Developer, capsys: pytest.CaptureFixture[str]
) -> None:
    """The App token goes to GET /app and nowhere else."""
    key = rsa_key("developer/worker")
    developer.api.register(key, APPS["worker"], ORGANISATION)
    developer.api.app_status = 307
    developer.api.app_headers = {"Location": f"{developer.api.url}/elsewhere"}
    assert developer.run("worker", key) == 2
    assert developer.stored_nothing()
    assert [path for path, _ in developer.api.requests] == ["/app"]
    assert capsys.readouterr() == ("", "rapid-ship: GitHub returned 307: Temporary Redirect\n")


def test_cli_import_key_takes_a_role(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["app", "--import-key", "admin"])
    assert caught.value.code == 2
    assert "invalid choice: 'admin'" in capsys.readouterr().err
    with pytest.raises(SystemExit) as caught:
        cli.main(["app", "--help"])
    assert caught.value.code == 0
    assert "--import-key {worker,reviewer}" in capsys.readouterr().out
