"""rapid-ship app's manifest flow, through which GitHub creates one App and hands over its key.

A server on 127.0.0.1 serves a page that posts the manifest to GitHub, then takes GitHub's
one-time code on its callback. The code buys the App's ID, slug and private key (Spec 1 section
3). The page posts to the settings of the account that will own the App: a user's own, or an
organisation's, which only its admins open. rapid_ship may not import devctl, so the permissions
here repeat devctl's, and a test keeps the two equal.
"""

from __future__ import annotations

import hmac
import html
import json
import queue
import re
import secrets
import sys
import threading
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Literal, TypeGuard
from urllib.parse import parse_qs, urlsplit

from rapid_ship.app_keychain import SLUG, AppSetupError, StoredApp

APP_PERMISSIONS = {  # the same table as devctl's, kept equal by a test
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
    "worker": "rapid-ship Workers push branches, open pull requests and merge approved ones.",
    "reviewer": "rapid-ship Reviewers post their verdicts on pull requests.",
}
_MAX_APP_NAME = 34  # GitHub's limit on an App's name
_CONVERSION_TIMEOUT_SECONDS = 30.0
_POLL_SECONDS = 0.05  # how soon the flow's server stops once the code has come
_MAX_REPLY_BYTES = 1024 * 1024
_CODE = re.compile(r"[A-Za-z0-9_-]{1,128}")


@dataclass(frozen=True)
class CreatedApp:
    app: StoredApp
    private_key: bytes
    permissions: dict[str, str]


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
    """value when it is a JSON object, else an empty one."""
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
        message = as_record(parsed).get("message") or reply.reason
        raise AppSetupError(f"GitHub returned {status}: {str(message)[:MAX_MESSAGE_CHARACTERS]}")
    return parsed


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
