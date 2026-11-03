"""rapid-ship app's calls to GitHub as an App: the manifest flow, and GET /app under a key."""

from __future__ import annotations

import hmac
import html
import json
import queue
import re
import secrets
import sys
import threading
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal, TypeGuard
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from rapid_ship.app_keychain import SLUG, AppSetupError, StoredApp

APP_PERMISSIONS = {  # devctl's table: rapid_ship may not import it; a test keeps them equal
    "worker": {
        "contents": "write",
        "pull_requests": "write",
        "issues": "write",
        "metadata": "read",
    },
    "reviewer": {"pull_requests": "write", "contents": "read", "metadata": "read"},
}
GITHUB_URL = "https://github.com"
API_URL = "https://api.github.com"
PROJECT_URL = "https://github.com/proxy-hatch/rapid-ship"
TITLES = {"worker": "Worker App", "reviewer": "Reviewer App"}
MAX_MESSAGE_CHARACTERS = 300

_DESCRIPTIONS = {
    "worker": (
        "Agents acting through rapid-ship's devctl push branches, open pull requests and merge "
        "approved ones."
    ),
    "reviewer": "Agents acting through rapid-ship's devctl post pull request reviews.",
}
_MAX_APP_NAME = 34  # GitHub's limit on an App's name
_API_TIMEOUT_SECONDS = 30.0
_POLL_SECONDS = 0.05  # how soon the flow's server stops once the code has come
_MAX_REPLY_BYTES = 1024 * 1024
_CODE = re.compile(r"[A-Za-z0-9_-]{1,128}")


class KeyRefused(AppSetupError):
    """A key cannot sign a token that GitHub accepts: GitHub refused it, or it cannot sign one."""


class KeyUnusable(KeyRefused):
    """A key cannot sign a token: it is no readable, unencrypted RSA PEM private key."""


@dataclass(frozen=True)
class CreatedApp:
    app: StoredApp
    private_key: bytes
    permissions: dict[str, str]


@dataclass(frozen=True)
class OwnedApp:
    """An App and the ID of the account that owns it, as GET /app shows them."""

    app: StoredApp
    owner_id: int


@dataclass(frozen=True)
class AppOwner:
    """The account that owns a repository and its Apps: a user or an organisation."""

    login: str
    kind: Literal["user", "organisation"]

    @property
    def apps_settings_url(self) -> str:
        """The GitHub page that lists the account's Apps; an App's own page adds its slug."""
        if self.kind == "organisation":
            return f"{GITHUB_URL}/organizations/{self.login}/settings/apps"
        return f"{GITHUB_URL}/settings/apps"


def as_record(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def is_id(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


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


class _FlowServer(ThreadingHTTPServer):
    """The manifest flow's local server: GET /start serves the form, GET /callback takes a code."""

    daemon_threads = True  # noqa: V107  # rs-exception: EX-13

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

    def handle_error(self, request: object, client_address: object) -> None:  # noqa: V105, V107  # rs-exception: EX-14
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


def _start_page(manifest: dict[str, object], state: str, owner: AppOwner) -> bytes:
    action = html.escape(f"{owner.apps_settings_url}/new?state={state}", quote=True)
    value = html.escape(json.dumps(manifest), quote=True)
    return (
        '<!doctype html>\n<html><head><meta charset="utf-8"><title>rapid-ship app</title></head>'
        f'<body><form method="post" action="{action}">'
        f'<input type="hidden" name="manifest" value="{value}">'
        '<button type="submit">Create the App on GitHub</button></form>'
        "<script>document.forms[0].submit();</script></body></html>\n"
    ).encode()


def _wait_for_code(
    role: str, owner: AppOwner, open_browser: Callable[[str], object], timeout_seconds: float
) -> str:
    server = _FlowServer()
    manifest = app_manifest(role, owner.login, f"http://{server.host}/callback")
    server.page = _start_page(manifest, server.state, owner)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": _POLL_SECONDS}, daemon=True
    )
    thread.start()
    minutes = f"{timeout_seconds / 60:g}"
    try:
        start = f"http://{server.host}/start"
        sys.stdout.write(
            f"Create the {TITLES[role]} on GitHub. If no browser opens, open {start}\n"
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


@dataclass(frozen=True)
class _Reply:
    status: int
    reason: str
    parsed: object  # the JSON reply, or None when it is too long or not JSON

    @property
    def failure(self) -> str:
        message = as_record(self.parsed).get("message") or self.reason
        return f"GitHub returned {self.status}: {str(message)[:MAX_MESSAGE_CHARACTERS]}"


def _call(method: str, path: str, api_url: str, authorization: str | None = None) -> _Reply:
    """Send one request to GitHub's REST API. No message includes the authorization."""
    parts = urlsplit(api_url)
    loopback = parts.scheme == "http" and parts.hostname == "127.0.0.1"
    if not (parts.scheme == "https" or loopback) or not parts.hostname:
        raise AppSetupError("the GitHub API URL must use https (http only on 127.0.0.1)")
    factory = HTTPSConnection if parts.scheme == "https" else HTTPConnection
    connection = factory(parts.hostname, parts.port, timeout=_API_TIMEOUT_SECONDS)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "rapid-ship"}
    if authorization is not None:
        headers["Authorization"] = authorization
    try:
        connection.request(method, f"{parts.path.rstrip('/')}{path}", headers=headers)
        reply = connection.getresponse()
        status, reason, data = reply.status, reply.reason, reply.read(_MAX_REPLY_BYTES + 1)
    except (OSError, HTTPException, ValueError) as error:
        raise AppSetupError(f"could not reach GitHub: {type(error).__name__}") from None
    finally:
        connection.close()
    try:
        parsed = None if len(data) > _MAX_REPLY_BYTES else json.loads(data)
    except (ValueError, RecursionError):
        parsed = None  # each caller reports what is missing
    return _Reply(status, reason, parsed)


def _convert(code: str, api_url: str) -> object:
    """Exchange the one-time code for the App. The code is the credential, as in Probot."""
    reply = _call("POST", f"/app-manifests/{code}/conversions", api_url)
    if not 200 <= reply.status < 300:
        raise AppSetupError(reply.failure)
    return reply.parsed


def _app_jwt(private_key: bytes, app_id: int) -> str:
    """A token for GitHub's App API, with the claims of devctl's app_jwt."""
    # Loaded here, as devctl does: PyJWT raises AttributeError for a public key.
    try:
        key = load_pem_private_key(private_key, password=None)
    except (ValueError, TypeError, UnsupportedAlgorithm):
        raise KeyUnusable("the key is not a readable, unencrypted PEM private key") from None
    if not isinstance(key, RSAPrivateKey):
        raise KeyUnusable("the key is not an RSA private key")
    issued = int(time.time())
    # 60 s back for clock drift; 9 minutes ahead stays under GitHub's 10-minute limit.
    claims = {"iat": issued - 60, "exp": issued + 540, "iss": str(app_id)}
    return jwt.encode(claims, key, algorithm="RS256")


def app_of_key(private_key: bytes, app_id: int, *, api_url: str = API_URL) -> OwnedApp:
    """The App with app_id and its owner, as GitHub shows them to a token that the key signs.

    GitHub shows its owner's gh no private App, but answers GET /app for an App's own token. It
    refuses the token when the App or that key no longer exists, or when the key is another App's.
    The token goes only into the request's Authorization header.
    """
    reply = _call("GET", "/app", api_url, f"Bearer {_app_jwt(private_key, app_id)}")
    if reply.status in (401, 404):
        raise KeyRefused(reply.failure)
    if not 200 <= reply.status < 300:
        raise AppSetupError(reply.failure)
    found = as_record(reply.parsed)
    found_id, slug = found.get("id"), found.get("slug")
    owner_id = as_record(found.get("owner")).get("id")
    if (
        not is_id(found_id)
        or not isinstance(slug, str)
        or not SLUG.fullmatch(slug)
        or not is_id(owner_id)
    ):
        raise AppSetupError(f"GitHub's record of App {app_id} has no App ID, slug or owner ID")
    return OwnedApp(StoredApp(found_id, slug), owner_id)


def orphaned(error: AppSetupError, settings_url: str) -> AppSetupError:
    """GitHub created an App whose key rapid-ship does not hold."""
    return AppSetupError(
        f"{error}. GitHub shows an App's key only once, so delete the App at {settings_url} "
        "and run rapid-ship app again"
    )


def _created_app(reply: object) -> CreatedApp:
    """The App in GitHub's reply. client_secret and webhook_secret are never read."""
    found = as_record(reply)
    app_id, slug, pem = found.get("id"), found.get("slug"), found.get("pem")
    permissions = found.get("permissions")
    if not is_id(app_id):
        raise AppSetupError("GitHub returned no App ID")
    if not isinstance(slug, str) or not SLUG.fullmatch(slug):
        raise AppSetupError(f"GitHub returned no App slug for App {app_id}")
    if not isinstance(pem, str) or not pem.startswith("-----BEGIN "):
        raise AppSetupError(f"GitHub returned no private key for {slug}")
    if not isinstance(permissions, dict):  # compared with APP_PERMISSIONS, never trusted
        raise AppSetupError(f"GitHub returned no permissions for {slug}")
    return CreatedApp(StoredApp(app_id, slug), pem.encode(), dict(permissions))


def create_app(
    role: str,
    owner: AppOwner,
    *,
    open_browser: Callable[[str], object],
    api_url: str = API_URL,
    timeout_seconds: float = 900.0,
) -> CreatedApp:
    """Run GitHub's manifest flow for the role's App on the owner's account."""
    code = _wait_for_code(role, owner, open_browser, timeout_seconds)
    try:
        return _created_app(_convert(code, api_url))
    except AppSetupError as error:  # GitHub sends the code only once it created the App
        raise orphaned(error, owner.apps_settings_url) from None
