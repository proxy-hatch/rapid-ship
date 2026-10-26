"""Offline: rapid-ship app with a simulated browser, GitHub conversion endpoint and Keychain."""

import html
import json
import re
import subprocess
import threading
import tomllib
import webbrowser
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from functools import cache
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    load_pem_private_key,
)

from rapid_ship import cli
from rapid_ship.app_keychain import AppSetupError, MacKeychainStore, StoredApp, keychain_service
from rapid_ship.github_app import GitHubNotFound, OwnerGet, gh_owner_get, run_app

Captured = list[tuple[str, dict[str, Any]]]

# The App ID and requested permissions of each App, by the end of the App's name.
REQUESTED: dict[str, tuple[int, dict[str, str]]] = {
    "-rs-worker": (
        11,
        {"contents": "write", "pull_requests": "write", "issues": "write", "metadata": "read"},
    ),
    "-rs-reviewer": (12, {"pull_requests": "write", "contents": "read", "metadata": "read"}),
}
# What the owner's gh login reads: o owns o/r, and org/r belongs to an organisation. o also owns
# the private Apps o-rs-worker (11) and o-rs-reviewer (12). GitHub shows gh no private App, even
# its owner's, so apps/o-rs-worker is a 404, as every path missing here is. So is the login's
# membership of org: the login is not a member of it.
OWNER_READS: dict[str, object] = {
    "repos/o/r": {"id": 2, "owner": {"login": "o", "id": 1, "type": "User"}},
    "repos/org/r": {"id": 3, "owner": {"login": "org", "id": 4, "type": "Organization"}},
    "user": {"login": "o", "id": 1},
}
# The owner's Apps after the owner made them public: GitHub then shows them to gh.
PUBLIC_APPS: dict[str, object] = {
    "apps/o-rs-worker": {"id": 11, "slug": "o-rs-worker", "owner": {"login": "o", "id": 1}},
    "apps/o-rs-reviewer": {"id": 12, "slug": "o-rs-reviewer", "owner": {"login": "o", "id": 1}},
}
# GitHub's GET /user/memberships/orgs/org when gh's login is an admin of org.
ORG_ADMIN: dict[str, object] = {
    "user/memberships/orgs/org": {
        "state": "active",
        "role": "admin",
        "organization": {"login": "org", "id": 4},
    }
}


def reads(answers: Mapping[str, object], log: list[str] | None = None) -> OwnerGet:
    """The owner's gh over answers: a path it does not hold is GitHub's 404."""

    def get(path: str) -> object:
        if log is not None:
            log.append(path)
        if path not in answers:
            raise GitHubNotFound(f"gh api {path} failed: gh: Not Found (HTTP 404)")
        return answers[path]

    return get


class FakeStore:
    """A Keychain that keeps each App's record and key in two dicts, by service.

    As the Keychain does, add never replaces an existing item.
    """

    def __init__(self) -> None:
        self.apps: dict[str, StoredApp] = {}
        self.keys: dict[str, bytes] = {}

    def exists(self, service: str) -> bool:
        return service in self.apps

    def add(self, service: str, app: StoredApp, private_key: bytes) -> None:
        if service in self.apps:
            raise AppSetupError(f"could not write Keychain item {service}")
        self.apps[service] = app
        self.keys[service] = private_key

    def read_key(self, service: str) -> bytes:
        if service not in self.keys:
            raise AppSetupError(f"Keychain item {service} not found")
        return self.keys[service]

    def listed(self, role: str) -> list[StoredApp]:
        named = [
            app for name, app in self.apps.items() if name == keychain_service(role, app.app_id)
        ]
        return sorted(named, key=lambda app: app.app_id)


def attributes(service: str, account: str | None, comment: str | None) -> str:
    """One generic-password item as keychain_utilities.c print_keychain_item_attributes prints
    it for find-generic-password and dump-keychain. None is an attribute the item lacks."""

    def blob(value: str | None) -> str:
        return "<NULL>" if value is None else f'"{value}"'

    return (
        'keychain: "/Users/o/Library/Keychains/login.keychain-db"\n'
        'class: "genp"\n'
        "attributes:\n"
        f'    "acct"<blob>={blob(account)}\n'
        f'    "icmt"<blob>={blob(comment)}\n'
        f'    "svce"<blob>="{service}"\n'
    )


class FakeSecurity:
    """`security` over a dict of generic-password items: service -> its -a, -j and -X values.
    An item added by hand can lack -a and -j.

    As security does, an add without -U leaves an existing item as it was and fails.
    """

    def __init__(self) -> None:
        self.argvs: list[list[str]] = []
        self.inputs: list[str] = []  # each line that security -i read on stdin
        self.items: dict[str, dict[str, str]] = {}

    def __call__(self, argv: list[str], input_text: str | None) -> subprocess.CompletedProcess[str]:
        self.argvs.append(argv)
        if argv == ["security", "-i"]:
            assert input_text is not None
            self.inputs.append(input_text)
            command, *words = input_text.split()
            assert command == "add-generic-password"
            update = "-U" in words
            words = [word for word in words if word != "-U"]
            options = dict(zip(words[::2], words[1::2], strict=True))
            if options["-s"] in self.items and not update:
                # errSecDuplicateItem (-25299). security -i exits with the failed command's status.
                duplicate = (
                    "security: SecKeychainItemCreateFromContent (<default>): "
                    "The specified item already exists in the keychain.\n"
                    "add-generic-password: returned -25299\n"
                )
                return subprocess.CompletedProcess(argv, 45, "", duplicate)
            self.items[options["-s"]] = {flag: options[flag] for flag in ("-a", "-j", "-X")}
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv == ["security", "dump-keychain"]:
            dump = [
                attributes(name, item.get("-a"), item.get("-j"))
                for name, item in self.items.items()
            ]
            return subprocess.CompletedProcess(argv, 0, "".join(dump), "")
        assert argv[:3] == ["security", "find-generic-password", "-s"]
        item = self.items.get(argv[3])
        if item is None:
            missing = "security: The specified item could not be found in the keychain.\n"
            return subprocess.CompletedProcess(argv, 44, "", missing)
        if argv[4:] == ["-w"]:
            return subprocess.CompletedProcess(argv, 0, item["-X"] + "\n", "")
        assert argv[4:] == []
        found = attributes(argv[3], item.get("-a"), item.get("-j"))
        return subprocess.CompletedProcess(argv, 0, found, "")


@cache
def rsa_key(name: str) -> bytes:
    """A real RSA private key in PEM, made once for each name, for a key that must sign a token."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())


class FakeConversions:
    """GitHub's POST /app-manifests/<code>/conversions, whose code is the name of the App it
    creates, and GET /app, which answers for the App whose key signed the bearer token.

    rapid-ship never parses a created App's key, so a PEM-shaped test text stands in for it. A key
    that signs a token must be real, as rsa_key makes one.
    """

    def __init__(self) -> None:
        self.url = ""
        self.permissions: dict[str, str] | None = None  # granted instead of the requested ones
        self.status = 201
        self.changes: dict[str, object] = {}  # reply fields that replace the usual ones
        self.requests: list[tuple[str, str | None]] = []  # each path and Authorization header
        # GET /app's record of each registered App, and the public key that checks its tokens.
        self.keyed: dict[int, tuple[rsa.RSAPublicKey, dict[str, object]]] = {}
        self.app_status = 200  # GET /app's status for a token it accepts
        self.app_changes: dict[str, object] = {}  # GET /app's reply fields that replace the usual
        self.app_headers: dict[str, str] = {}  # GET /app's extra reply headers, such as Location

    def register(self, private_key: bytes, app: StoredApp, owner: Mapping[str, object]) -> None:
        """Let GET /app answer as app, which owner owns, for a token that private_key signed."""
        loaded = load_pem_private_key(private_key, password=None)
        assert isinstance(loaded, rsa.RSAPrivateKey)
        record = {"id": app.app_id, "slug": app.slug, "owner": dict(owner)}
        self.keyed[app.app_id] = (loaded.public_key(), record)

    def app_reply(self, authorization: str | None) -> tuple[int, dict[str, object]]:
        """GET /app: 401 unless a registered App's key signed a current token for that App."""
        token = (authorization or "").removeprefix("Bearer ")
        try:
            issuer = jwt.decode(token, options={"verify_signature": False})["iss"]
            public_key, record = self.keyed[int(issuer)]
            claims = jwt.decode(
                token, public_key, algorithms=["RS256"], options={"require": ["iat", "exp"]}
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            return 401, {"message": "A JSON web token could not be decoded"}
        if claims["exp"] - claims["iat"] > 600:  # GitHub's limit on a token's lifetime
            return 401, {"message": "'Expiration time' claim ('exp') is too far in the future"}
        return self.app_status, {**record, **self.app_changes}

    def pem_for(self, name: str) -> bytes:
        return f"-----BEGIN RSA PRIVATE KEY-----\n{name}\n-----END RSA PRIVATE KEY-----\n".encode()

    def reply(self, path: str) -> dict[str, object]:
        name = path.removeprefix("/app-manifests/").removesuffix("/conversions")
        [(app_id, requested)] = [app for end, app in REQUESTED.items() if name.endswith(end)]
        return {
            "id": app_id,
            "slug": name,
            "pem": self.pem_for(name).decode(),
            "client_secret": "client-secret",
            "webhook_secret": None,
            "permissions": requested if self.permissions is None else self.permissions,
            "html_url": f"https://github.com/apps/{name}",
            **self.changes,
        }


def _conversion_handler(fake: FakeConversions) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            fake.requests.append((self.path, self.headers.get("Authorization")))
            self._send(fake.status, fake.reply(self.path))

        def do_GET(self) -> None:
            authorization = self.headers.get("Authorization")
            fake.requests.append((self.path, authorization))
            if self.path == "/app":
                self._send(*fake.app_reply(authorization), fake.app_headers)
            else:
                self._send(404, {"message": "Not Found"})

        def _send(
            self, status: int, reply: dict[str, object], headers: Mapping[str, str] | None = None
        ) -> None:
            body = json.dumps(reply).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            """Silent."""

    return Handler


@contextmanager
def serve_conversions() -> Iterator[FakeConversions]:
    fake = FakeConversions()
    server = ThreadingHTTPServer(("127.0.0.1", 0), _conversion_handler(fake))
    # A short poll, so that shutdown returns soon after each test.
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    fake.url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def conversions() -> Iterator[FakeConversions]:
    with serve_conversions() as fake:
        yield fake


@pytest.fixture
def store() -> FakeStore:
    return FakeStore()


@pytest.fixture
def owner_get() -> OwnerGet:
    return reads(OWNER_READS)


def http_get(url: str) -> tuple[int, str]:
    parts = urlsplit(url)
    connection = HTTPConnection(parts.netloc, timeout=5)
    connection.request("GET", f"{parts.path}?{parts.query}" if parts.query else parts.path)
    response = connection.getresponse()
    return response.status, response.read().decode()


def found(pattern: str, text: str) -> str:
    match = re.search(pattern, text)
    assert match is not None, pattern
    return match.group(1)


def github_browser(captured: Captured) -> Callable[[str], None]:
    """Act as the owner's browser and GitHub: read the form, reject a forged callback,
    then call back."""

    def open_browser(start_url: str) -> None:
        _, page = http_get(start_url)
        action = found(r'action="([^"]+)"', page)
        manifest: dict[str, Any] = json.loads(
            html.unescape(found(r'name="manifest" value="([^"]+)"', page))
        )
        captured.append((action, manifest))
        callback = manifest["redirect_url"]
        state = html.unescape(action).split("state=", 1)[1]
        assert http_get(f"{callback}?code=c0de&state=wrong")[0] == 400
        assert http_get(f"{callback}?code={manifest['name']}&state={state}")[0] == 200

    return open_browser


def test_cli_app_calls_run_app_with_the_real_dependencies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    def record(repository: str, **kwargs: object) -> int:
        calls.append((repository, kwargs))
        return 0

    monkeypatch.setattr(cli, "run_app", record)
    monkeypatch.chdir(tmp_path)  # app runs outside a work tree too
    assert cli.main(["app", "--repository", "o/r"]) == 0
    [(repository, kwargs)] = calls
    assert repository == "o/r"
    assert isinstance(kwargs["store"], MacKeychainStore)
    assert kwargs["owner_get"] is gh_owner_get
    assert kwargs["open_browser"] is webbrowser.open
    assert kwargs["recorded"] == {}  # outside a work tree, no project.toml records an App


def test_creates_both_apps_and_prints_install_urls(
    conversions: FakeConversions,
    store: FakeStore,
    owner_get: OwnerGet,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    captured: Captured = []
    assert (
        run_app(
            "o/r",
            store=store,
            owner_get=owner_get,
            open_browser=github_browser(captured),
            api_url=conversions.url,
            timeout_seconds=10,
        )
        == 0
    )
    (action, worker), (_, reviewer) = captured
    assert action.startswith("https://github.com/settings/apps/new?state=")
    assert (worker["public"], worker["default_events"], "hook_attributes" in worker) == (
        False,
        [],
        False,
    )
    assert worker["default_permissions"] == {
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "metadata": "read",
    }
    assert reviewer["default_permissions"] == {
        "pull_requests": "write",
        "contents": "read",
        "metadata": "read",
    }
    assert worker["redirect_url"].startswith("http://127.0.0.1:")
    assert len(worker["name"]) <= 34
    assert store.keys["rapid-ship/worker-app/11"] == conversions.pem_for(worker["name"])
    out = capsys.readouterr().out
    assert "Worker App: ID 11" in out
    assert "Reviewer App: ID 12" in out
    assert "/installations/new/permissions?suggested_target_id=1&repository_ids[]=2" in out
    assert "BEGIN" not in out
    assert "client-secret" not in out
    assert not [p for p in tmp_path.rglob("*") if p.is_file() and b"BEGIN" in p.read_bytes()]


def test_existing_apps_are_only_printed(
    store: FakeStore, capsys: pytest.CaptureFixture[str]
) -> None:
    store.apps = {
        "rapid-ship/worker-app/11": StoredApp(11, "o-rs-worker"),
        "rapid-ship/reviewer-app/12": StoredApp(12, "o-rs-reviewer"),
    }
    opened: list[str] = []
    owner_get = reads({**OWNER_READS, **PUBLIC_APPS})
    assert run_app("o/r", store=store, owner_get=owner_get, open_browser=opened.append) == 0
    assert opened == []
    assert (
        "https://github.com/apps/o-rs-worker/installations/new/permissions"
        in capsys.readouterr().out
    )


def test_an_organisation_admin_creates_its_apps_through_the_organisation_flow(
    conversions: FakeConversions, store: FakeStore, capsys: pytest.CaptureFixture[str]
) -> None:
    """A private App installs only on its owner's repositories, so an organisation's repository
    gets Apps that the organisation owns. An admin of the organisation creates them."""
    log: list[str] = []
    captured: Captured = []
    code = run_app(
        "org/r",
        store=store,
        owner_get=reads({**OWNER_READS, **ORG_ADMIN}, log),
        open_browser=github_browser(captured),
        api_url=conversions.url,
        timeout_seconds=10,
    )
    assert code == 0
    assert log == ["repos/org/r", "user/memberships/orgs/org"]
    pages = [html.unescape(action).split("?state=", 1)[0] for action, _ in captured]
    assert pages == ["https://github.com/organizations/org/settings/apps/new"] * 2
    assert [manifest["name"] for _, manifest in captured] == ["org-rs-worker", "org-rs-reviewer"]
    assert sorted(store.keys) == ["rapid-ship/reviewer-app/12", "rapid-ship/worker-app/11"]
    out = capsys.readouterr().out
    assert (
        "https://github.com/apps/org-rs-worker/installations/new/permissions"
        "?suggested_target_id=4&repository_ids[]=3"
    ) in out


def test_an_organisations_recorded_apps_need_no_admin(
    store: FakeStore, capsys: pytest.CaptureFixture[str]
) -> None:
    """A member who is not an admin uses the Apps that the repository records, whose keys this
    machine holds. Only creating an App needs an admin."""
    apps = {"worker": StoredApp(11, "org-rs-worker"), "reviewer": StoredApp(12, "org-rs-reviewer")}
    store.apps = {keychain_service(role, app.app_id): app for role, app in apps.items()}
    log: list[str] = []
    opened: list[str] = []
    code = run_app(
        "org/r",
        store=store,
        owner_get=reads(OWNER_READS, log),
        open_browser=opened.append,
        recorded=apps,
    )
    assert (code, log, opened) == (0, ["repos/org/r"], [])
    assert (
        "https://github.com/apps/org-rs-reviewer/installations/new/permissions"
        "?suggested_target_id=4&repository_ids[]=3"
    ) in capsys.readouterr().out


def test_permission_mismatch_keeps_the_key_and_exits_1(
    conversions: FakeConversions, store: FakeStore, owner_get: OwnerGet
) -> None:
    conversions.permissions = {"contents": "write", "metadata": "read"}
    assert (
        run_app(
            "o/r",
            store=store,
            owner_get=owner_get,
            open_browser=github_browser([]),
            api_url=conversions.url,
            timeout_seconds=10,
        )
        == 1
    )
    assert "rapid-ship/worker-app/11" in store.keys


def test_no_callback_times_out_with_exit_2(store: FakeStore, owner_get: OwnerGet) -> None:
    assert (
        run_app(
            "o/r",
            store=store,
            owner_get=owner_get,
            open_browser=lambda url: None,
            timeout_seconds=0.2,
        )
        == 2
    )


def test_keychain_add_passes_the_key_on_stdin_only() -> None:
    security = FakeSecurity()
    pem = b"-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----\n"
    MacKeychainStore(run=security).add(
        "rapid-ship/worker-app/11", StoredApp(11, "o-rs-worker"), pem
    )
    assert ["security", "-i"] in security.argvs
    assert all(pem.hex() not in arg for argv in security.argvs for arg in argv)
    assert MacKeychainStore(run=security).find("rapid-ship/worker-app/11") == StoredApp(
        11, "o-rs-worker"
    )


def test_keychain_add_refuses_a_line_security_would_cut() -> None:
    security = FakeSecurity()
    with pytest.raises(AppSetupError, match="too long"):
        MacKeychainStore(run=security).add(
            "rapid-ship/worker-app/11", StoredApp(11, "s"), b"-----BEGIN " + b"A" * 2100
        )
    assert security.argvs == []


def test_the_printed_settings_lines_are_the_github_table(
    store: FakeStore, capsys: pytest.CaptureFixture[str]
) -> None:
    store.apps = {
        "rapid-ship/worker-app/11": StoredApp(11, "o-rs-worker"),
        "rapid-ship/reviewer-app/12": StoredApp(12, "o-rs-reviewer"),
    }
    owner_get = reads({**OWNER_READS, **PUBLIC_APPS})
    assert run_app("o/r", store=store, owner_get=owner_get, open_browser=lambda url: None) == 0
    lines = [line.strip() for line in capsys.readouterr().out.splitlines() if "_app_" in line]
    assert tomllib.loads("\n".join(lines)) == {
        "worker_app_id": 11,
        "worker_app_slug": "o-rs-worker",
        "reviewer_app_id": 12,
        "reviewer_app_slug": "o-rs-reviewer",
    }
