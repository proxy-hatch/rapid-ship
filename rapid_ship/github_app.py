"""rapid-ship app: create the owner's Worker and Reviewer Apps once, and print how to install them.

GitHub's manifest flow creates each App (spec section 3). A server on 127.0.0.1 serves a page
that posts the manifest to GitHub, then takes GitHub's one-time code on its callback. The code
buys the App's ID, slug and private key. The key goes to the macOS Keychain on `security`'s
stdin: it is never written to disk, put in argv or printed. devctl reads it back with the same
tool. rapid_ship may not import devctl, so the services and permissions here repeat devctl's,
and a test keeps the two equal.
"""

from __future__ import annotations

import hmac
import html
import json
import queue
import re
import secrets
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Protocol, TypeGuard
from urllib.parse import parse_qs, urlsplit

KEYCHAIN_SERVICE = {"worker": "rapid-ship/worker-app", "reviewer": "rapid-ship/reviewer-app"}
APP_PERMISSIONS = {  # the same table as devctl's, kept equal by a test
    "worker": {
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "metadata": "read",
    },
    "reviewer": {"pull_requests": "write", "contents": "read", "metadata": "read"},
}
MAX_SECURITY_LINE = 4095  # `security -i` reads each command into a 4096-byte buffer

Runner = Callable[[list[str], str | None], subprocess.CompletedProcess[str]]
OwnerGet = Callable[[str], object]

GITHUB_URL = "https://github.com"
API_URL = "https://api.github.com"
PROJECT_URL = "https://github.com/proxy-hatch/rapid-ship"
_ROLES = ("worker", "reviewer")
_TITLES = {"worker": "Worker App", "reviewer": "Reviewer App"}
_DESCRIPTIONS = {
    "worker": "rapid-ship Workers push branches, open pull requests and merge approved ones.",
    "reviewer": "rapid-ship Reviewers post their verdicts on pull requests.",
}
_MAX_APP_NAME = 34  # GitHub's limit on an App's name
_GH_TIMEOUT_SECONDS = 60.0
_CONVERSION_TIMEOUT_SECONDS = 30.0
_POLL_SECONDS = 0.05  # how soon the flow's server stops once the code has come
_MAX_REPLY_BYTES = 1024 * 1024
_MAX_MESSAGE_CHARACTERS = 300
_ITEM_NOT_FOUND = 44  # the exit code of `security find-generic-password` for a missing item
_REPOSITORY = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+")
_CODE = re.compile(r"[A-Za-z0-9_-]{1,128}")
_SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")
_HEX = re.compile(r"(?:[0-9a-f]{2})+")
# keychain_utilities.c print_keychain_item_attributes: the account holds the App ID and the
# comment the slug, so find() reads both without reading the key.
_ACCOUNT = re.compile(r'^\s*"acct"<blob>="(\d+)"$', re.MULTILINE)
_COMMENT = re.compile(r'^\s*"icmt"<blob>="([a-z0-9][a-z0-9-]*)"$', re.MULTILINE)


class AppSetupError(Exception):
    """rapid-ship app cannot go on; the command exits 2."""


class _Refused(Exception):
    """The repository cannot take the owner's Apps; the command exits 1."""


@dataclass(frozen=True)
class StoredApp:
    app_id: int
    slug: str


@dataclass(frozen=True)
class CreatedApp:
    app: StoredApp
    private_key: bytes
    permissions: dict[str, str]


def run_command(
    argv: Sequence[str], input_text: str | None = None, *, timeout_seconds: float = 120.0
) -> subprocess.CompletedProcess[str]:
    """Run security or gh with fixed arguments and no shell.

    rapid_ship cannot use devctl's runner.
    """
    try:
        return subprocess.run(  # noqa: S603  # rs-exception: EX-11
            list(argv),
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise AppSetupError(f"could not run {argv[0]}: {type(error).__name__}") from None


def _first_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = [line.strip() for line in result.stderr.splitlines() if line.strip()]
    return lines[0][:_MAX_MESSAGE_CHARACTERS] if lines else f"exit code {result.returncode}"


def _record(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _is_id(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def gh_owner_get(path: str) -> object:
    """GET path from GitHub's REST API as the owner's gh login, and parse the JSON reply."""
    result = run_command(
        ["gh", "api", "--method", "GET", path], timeout_seconds=_GH_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        raise AppSetupError(f"gh api {path} failed: {_first_line(result)}")
    try:
        return json.loads(result.stdout)
    except (ValueError, RecursionError):
        raise AppSetupError(f"gh api {path} printed no JSON") from None


def current_repository() -> str:
    """The OWNER/NAME of the GitHub repository that gh finds for the current directory."""
    result = run_command(
        ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
        timeout_seconds=_GH_TIMEOUT_SECONDS,
    )
    name = result.stdout.strip()
    if result.returncode != 0 or not name:
        raise AppSetupError(
            f"gh cannot tell this directory's GitHub repository ({_first_line(result)}); "
            "give --repository OWNER/NAME"
        )
    return name


class KeychainStore(Protocol):
    def find(self, service: str) -> StoredApp | None: ...
    def add(self, service: str, app: StoredApp, private_key: bytes) -> None: ...


def _secret(output: str) -> bytes:
    text = output.rstrip("\n")
    # `security -w` prints the item as lowercase hex when any byte is not printable, as a PEM's
    # newlines are (keychain_find.c:429-437). devctl decodes it the same way.
    return bytes.fromhex(text) if _HEX.fullmatch(text) else text.encode()


class MacKeychainStore:
    """Each App as a generic-password item: the App ID as account, the slug as comment, the key
    as secret. No message includes `security`'s output, which can hold the key."""

    def __init__(self, run: Runner = run_command) -> None:
        self.run = run

    def find(self, service: str) -> StoredApp | None:
        # Without -w, security prints the item's attributes only, never its secret.
        result = self.run(["security", "find-generic-password", "-s", service], None)
        if result.returncode == _ITEM_NOT_FOUND:
            return None
        if result.returncode != 0:
            raise AppSetupError(f"could not read Keychain item {service}")
        account = _ACCOUNT.search(result.stdout)
        comment = _COMMENT.search(result.stdout)
        if account is None or comment is None:
            raise AppSetupError(f"Keychain item {service} was not written by rapid-ship app")
        return StoredApp(int(account.group(1)), comment.group(1))

    def add(self, service: str, app: StoredApp, private_key: bytes) -> None:
        # The key travels as hex on stdin, never in argv. Without -U an existing item is never
        # replaced. Without -T the item trusts /usr/bin/security alone, so devctl reads it with
        # no dialog, and so can any process the owner runs (spec section 6).
        line = (
            f"add-generic-password -s {service} -a {app.app_id} -j {app.slug} "
            f"-X {private_key.hex()}\n"
        )
        if len(line) > MAX_SECURITY_LINE:
            raise AppSetupError(
                f"the private key is too long for security -i; it reads lines of at most "
                f"{MAX_SECURITY_LINE} characters, so nothing was stored"
            )
        if self.run(["security", "-i"], line).returncode != 0:
            raise AppSetupError(f"could not write Keychain item {service}")
        stored = self.run(["security", "find-generic-password", "-s", service, "-w"], None)
        held = stored.returncode == 0 and _secret(stored.stdout) == private_key
        if not held or self.find(service) != app:
            raise AppSetupError(
                f"Keychain item {service} does not hold the key and App just written"
            )


def app_manifest(role: str, owner_login: str, redirect_url: str) -> dict[str, object]:
    """GitHub's App manifest for the role's App: private, with no webhook and no events.

    The owner can still edit the name on GitHub's page, for one taken by another account.
    """
    suffix = f"-rs-{role}"
    login = owner_login[: _MAX_APP_NAME - len(suffix)].rstrip("-")
    return {
        "name": f"{login}{suffix}",
        "url": PROJECT_URL,
        "description": _DESCRIPTIONS[role],
        "public": False,
        "redirect_url": redirect_url,
        "default_permissions": dict(APP_PERMISSIONS[role]),
        "default_events": [],
    }


def install_url(slug: str, owner_id: int, repository_id: int) -> str:
    return (
        f"{GITHUB_URL}/apps/{slug}/installations/new/permissions"
        f"?suggested_target_id={owner_id}&repository_ids[]={repository_id}"
    )


class _FlowServer(ThreadingHTTPServer):
    """The manifest flow's local server: GET /start serves the form, GET /callback takes a code."""

    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _FlowHandler)
        self.host = f"127.0.0.1:{self.server_port}"
        self.state = secrets.token_urlsafe(32)
        self.page = b""
        self.codes: queue.Queue[str] = queue.Queue(maxsize=1)

    def answer(self, path: str, host: str | None) -> tuple[int, bytes, str]:
        # Only this Host: a page on a domain rebound to 127.0.0.1 sends its own name.
        parts = urlsplit(path)
        if host == self.host and parts.path == "/start":
            return 200, self.page, "text/html; charset=utf-8"
        if host == self.host and parts.path == "/callback" and self._take(parts.query):
            return 200, b"The App was created. Return to the terminal.\n", "text/plain"
        return 400, b"Bad request\n", "text/plain"

    def _take(self, query: str) -> bool:
        fields = parse_qs(query)
        states, codes = fields.get("state", []), fields.get("code", [])
        # Bytes, because compare_digest refuses a str that is not ASCII.
        taken = (
            len(states) == len(codes) == 1
            and hmac.compare_digest(states[0].encode(), self.state.encode())
            and _CODE.fullmatch(codes[0]) is not None
        )
        if taken:
            with suppress(queue.Full):  # an earlier callback already gave the code
                self.codes.put_nowait(codes[0])
        return taken

    def handle_error(self, request: object, client_address: object) -> None:
        """Silent: a browser that drops its connection must not print a traceback."""


class _FlowHandler(BaseHTTPRequestHandler):
    server: _FlowServer

    def do_GET(self) -> None:
        status, body, content_type = self.server.answer(self.path, self.headers.get("Host"))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        """Silent, so a one-time code never reaches the terminal."""


def _start_page(manifest: dict[str, object], state: str) -> bytes:
    action = html.escape(f"{GITHUB_URL}/settings/apps/new?state={state}", quote=True)
    value = html.escape(json.dumps(manifest), quote=True)
    return (
        '<!doctype html>\n<html><head><meta charset="utf-8"><title>rapid-ship app</title></head>'
        f'<body><form method="post" action="{action}">'
        f'<input type="hidden" name="manifest" value="{value}">'
        '<button type="submit">Create the App on GitHub</button></form>'
        "<script>document.forms[0].submit();</script></body></html>\n"
    ).encode()


def _wait_for_code(
    role: str, owner_login: str, open_browser: Callable[[str], object], timeout_seconds: float
) -> str:
    server = _FlowServer()
    manifest = app_manifest(role, owner_login, f"http://{server.host}/callback")
    server.page = _start_page(manifest, server.state)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": _POLL_SECONDS}, daemon=True
    )
    thread.start()
    minutes = f"{timeout_seconds / 60:g}"
    try:
        start = f"http://{server.host}/start"
        sys.stdout.write(
            f"Create the {_TITLES[role]} on GitHub. If no browser opens, open {start}\n"
            f"Waiting up to {minutes} minutes.\n"
        )
        open_browser(start)
        return server.codes.get(timeout=timeout_seconds)
    except queue.Empty:
        raise AppSetupError(f"no App was created within {minutes} minutes") from None
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _convert(code: str, api_url: str) -> object:
    """Exchange the one-time code for the App. The code is the credential, as in Probot."""
    parts = urlsplit(api_url)
    loopback = parts.scheme == "http" and parts.hostname == "127.0.0.1"
    if not (parts.scheme == "https" or loopback) or not parts.hostname:
        raise AppSetupError("the GitHub API URL must use https (http only on 127.0.0.1)")
    factory = HTTPSConnection if parts.scheme == "https" else HTTPConnection
    connection = factory(parts.hostname, parts.port, timeout=_CONVERSION_TIMEOUT_SECONDS)
    target = f"{parts.path.rstrip('/')}/app-manifests/{code}/conversions"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "rapid-ship"}
    try:
        connection.request("POST", target, headers=headers)
        reply = connection.getresponse()
        status, data = reply.status, reply.read(_MAX_REPLY_BYTES + 1)
    except (OSError, HTTPException, ValueError) as error:
        raise AppSetupError(f"could not reach GitHub: {type(error).__name__}") from None
    finally:
        connection.close()
    try:
        parsed = None if len(data) > _MAX_REPLY_BYTES else json.loads(data)
    except (ValueError, RecursionError):
        parsed = None  # _created_app reports what is missing
    if not 200 <= status < 300:
        message = _record(parsed).get("message") or reply.reason
        raise AppSetupError(f"GitHub returned {status}: {str(message)[:_MAX_MESSAGE_CHARACTERS]}")
    return parsed


def _orphaned(error: AppSetupError, settings_url: str) -> AppSetupError:
    """GitHub created an App whose key rapid-ship does not hold."""
    return AppSetupError(
        f"{error}. GitHub shows an App's key only once, so delete the App at {settings_url} "
        "and run rapid-ship app again"
    )


def _created_app(reply: object) -> CreatedApp:
    """The App in GitHub's reply. client_secret and webhook_secret are never read."""
    found = _record(reply)
    app_id, slug, pem = found.get("id"), found.get("slug"), found.get("pem")
    permissions = found.get("permissions")
    if not _is_id(app_id):
        raise AppSetupError("GitHub returned no App ID")
    if not isinstance(slug, str) or not _SLUG.fullmatch(slug):
        raise AppSetupError(f"GitHub returned no App slug for App {app_id}")
    if not isinstance(pem, str) or not pem.startswith("-----BEGIN "):
        raise AppSetupError(f"GitHub returned no private key for {slug}")
    if not isinstance(permissions, dict):  # compared with APP_PERMISSIONS, never trusted
        raise AppSetupError(f"GitHub returned no permissions for {slug}")
    return CreatedApp(StoredApp(app_id, slug), pem.encode(), dict(permissions))


def create_app(
    role: str,
    owner_login: str,
    *,
    open_browser: Callable[[str], object],
    api_url: str = API_URL,
    timeout_seconds: float = 900.0,
) -> CreatedApp:
    """Run GitHub's manifest flow for the role's App on the owner's personal account."""
    code = _wait_for_code(role, owner_login, open_browser, timeout_seconds)
    try:
        return _created_app(_convert(code, api_url))
    except AppSetupError as error:  # GitHub sends the code only once it created the App
        raise _orphaned(error, f"{GITHUB_URL}/settings/apps") from None


@dataclass(frozen=True)
class _Target:
    owner_id: int
    owner_login: str
    repository_id: int


def _target(repository: str, owner_get: OwnerGet) -> _Target:
    """The repository's owner and ID. Refused unless the owner's gh login owns the repository."""
    if not _REPOSITORY.fullmatch(repository) or ".." in repository:
        raise AppSetupError(f"the repository must be OWNER/NAME, not {repository!r}")
    found = _record(owner_get(f"repos/{repository}"))
    owner = _record(found.get("owner"))
    login, owner_id, repository_id = owner.get("login"), owner.get("id"), found.get("id")
    if not isinstance(login, str) or not _is_id(owner_id) or not _is_id(repository_id):
        raise AppSetupError(f"GitHub's record of {repository} has no owner login or no ID")
    # A private App installs only on the account that owns it.
    if owner.get("type") != "User":
        raise _Refused(
            f"{repository} belongs to the organization {login}. rapid-ship app creates private "
            "Apps on your personal account, and they install only on its repositories"
        )
    user = _record(owner_get("user")).get("login")
    if not isinstance(user, str):
        raise AppSetupError("GitHub's record of your account has no login")
    if login.casefold() != user.casefold():
        raise _Refused(
            f"{repository} belongs to {login}, and gh is signed in as {user}. A private App "
            "installs only on its owner's repositories; sign gh in as the owner"
        )
    return _Target(owner_id, login, repository_id)


def _ensure_app(
    role: str,
    stored: StoredApp | None,
    target: _Target,
    store: KeychainStore,
    create: Callable[[str, str], CreatedApp],
) -> tuple[StoredApp, bool]:
    """The role's App and whether its permissions are rapid-ship's. A found App is not checked."""
    if stored is not None:
        return stored, True
    created = create(role, target.owner_login)
    try:
        # Before anything else: GitHub shows the key only once.
        store.add(KEYCHAIN_SERVICE[role], created.app, created.private_key)
    except AppSetupError as error:
        raise _orphaned(error, f"{GITHUB_URL}/settings/apps/{created.app.slug}/advanced") from None
    return created.app, created.permissions == APP_PERMISSIONS[role]


def _report(role: str, app: StoredApp, repository: str, target: _Target, matches: bool) -> None:
    sys.stdout.write(
        f"{_TITLES[role]}: ID {app.app_id} ({app.slug})\n"
        f"  {role}_app_id = {app.app_id}\n"
        f'  {role}_app_slug = "{app.slug}"\n'
        f"  Install on {repository}: "
        f"{install_url(app.slug, target.owner_id, target.repository_id)}\n"
    )
    if not matches:
        wanted = ", ".join(f"{name} {level}" for name, level in APP_PERMISSIONS[role].items())
        sys.stdout.write(
            f"  Its permissions differ from rapid-ship's ({wanted}): "
            f"fix the permissions at {GITHUB_URL}/settings/apps/{app.slug}/permissions\n"
        )


def run_app(
    repository: str,
    *,
    store: KeychainStore,
    owner_get: OwnerGet,
    open_browser: Callable[[str], object],
    api_url: str = API_URL,
    timeout_seconds: float = 900.0,
) -> int:
    """Create each missing App, then print every App's ID and its install URL for repository.

    0 when both Apps are ready, 1 when the repository is refused or an App's permissions differ,
    2 when the command cannot go on.
    """
    create = partial(
        create_app, open_browser=open_browser, api_url=api_url, timeout_seconds=timeout_seconds
    )
    try:
        target = _target(repository, owner_get)
        found = {role: store.find(KEYCHAIN_SERVICE[role]) for role in _ROLES}
        exit_code = 0
        for role in _ROLES:
            app, matches = _ensure_app(role, found[role], target, store, create)
            _report(role, app, repository, target, matches)
            exit_code = exit_code if matches else 1
    except _Refused as refusal:
        sys.stderr.write(f"rapid-ship: refused: {refusal}\n")
        return 1
    except AppSetupError as error:
        sys.stderr.write(f"rapid-ship: {error}\n")
        return 2
    sys.stdout.write(
        "Record each App's ID and slug, as printed above, in .rapid-ship/project.toml under "
        "[github]; rs-setup does this. ./devctl doctor then confirms each installation.\n"
    )
    return exit_code
