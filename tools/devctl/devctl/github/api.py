"""Minimal GitHub REST client.

It never follows a redirect, which could carry the token elsewhere. Like urllib, it sends
an https request through the proxy that HTTPS_PROXY or https_proxy names, unless NO_PROXY or
no_proxy lists the host.
"""

from __future__ import annotations

import base64
import json
import os
import re
import socket
import ssl
from dataclasses import dataclass, field
from http import HTTPStatus
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from urllib.parse import unquote, urlsplit
from urllib.request import getproxies_environment, proxy_bypass

API_URL = "https://api.github.com"
API_VERSION = "2026-03-10"
MAX_RESPONSE_BYTES = 20 * 1024 * 1024
TIMEOUT_SECONDS = 30.0
MAX_MESSAGE_CHARACTERS = 300
_LOOPBACK = {"127.0.0.1", "localhost"}
_DEFAULT_PORTS = {"https": 443, "http": 80}


class GitHubError(Exception):
    def __init__(self, status: int | None, message: str) -> None:
        prefix = f"GitHub returned {status}" if status else "GitHub request failed"
        super().__init__(f"{prefix}: {message}")
        self.status = status


def json_object(value: object, what: str) -> dict[str, object]:
    """Narrow a parsed JSON value to an object, or raise GitHubError with no status."""
    if isinstance(value, dict):
        return value
    raise GitHubError(None, f"{what} is not a JSON object")


def json_list(value: object, what: str) -> list[object]:
    """Narrow a parsed JSON value to a list, or raise GitHubError with no status."""
    if isinstance(value, list):
        return value
    raise GitHubError(None, f"{what} is not a JSON list")


@dataclass(frozen=True)
class _Response:
    status: int
    reason: str
    data: bytes


@dataclass(frozen=True)
class _Proxy:
    host: str
    port: int
    tunnel_headers: dict[str, str] = field(repr=False)
    redactions: tuple[str, ...] = field(repr=False)

    @property
    def address(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{host}:{self.port}"


def _https_proxy(netloc: str) -> _Proxy | None:
    """Use urllib's environment precedence and bypass rules, without system proxy settings."""
    proxies = getproxies_environment()
    url = proxies.get("https")
    # With an HTTPS proxy in the environment, urllib bypasses only from NO_PROXY/no_proxy.
    if not url or proxy_bypass(netloc):
        return None
    # Validate before urlsplit, which silently strips some control characters.
    try:
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
            raise ValueError
        parts = urlsplit(url if "://" in url else f"http://{url}")
        port = 80 if parts.port is None else parts.port
        if (
            parts.scheme != "http"
            or not parts.hostname
            or not port
            or parts.path not in ("", "/")
            or parts.query
            or parts.fragment
        ):
            raise ValueError
    except ValueError:
        # Even a scheme or a parser error can contain credentials from malformed input.
        raise GitHubError(
            None,
            f"cannot connect to {netloc}: HTTPS_PROXY/https_proxy must name an HTTP "
            "CONNECT proxy such as http://proxy.example:3128; other schemes are unsupported",
        ) from None
    headers = {}
    redactions: tuple[str, ...] = ()
    if parts.username is not None:
        username, password = unquote(parts.username), unquote(parts.password or "")
        credentials = f"{username}:{password}"
        try:
            encoded = base64.b64encode(credentials.encode()).decode()
        except UnicodeError:
            raise GitHubError(
                None,
                f"cannot connect to {netloc}: HTTPS_PROXY/https_proxy credentials must "
                "be UTF-8 text in an http:// proxy URL",
            ) from None
        headers["Proxy-Authorization"] = "Basic " + encoded
        redactions = (
            url,
            parts.username,
            parts.password or "",
            username,
            password,
            credentials,
            encoded,
        )
    return _Proxy(parts.hostname, port, headers, redactions)


def _cause(failure: OSError | HTTPException | ValueError) -> str:
    """Describe transport failures without echoing remote replies or settings."""
    name = type(failure).__name__
    if isinstance(failure, ssl.SSLCertVerificationError):
        return f"{name}: TLS certificate verification failed; check the trusted CA and hostname"
    if isinstance(failure, socket.gaierror):
        return f"{name}: DNS lookup failed; the host could not be resolved"
    if isinstance(failure, OSError):
        if failure.errno is not None:
            return f"{name}: {os.strerror(failure.errno)}"
        # http.client includes the proxy's untrusted reason phrase after the CONNECT status.
        match = re.match(r"Tunnel connection failed: ([0-9]{3})(?: |$)", str(failure))
        if match:
            code = int(match[1])
            reason = HTTPStatus(code).phrase if code in HTTPStatus else "unknown status"
            return f"{name}: Tunnel connection failed: {code} {reason}"
    return name


class GitHubApi:
    def __init__(self, token: str, *, base_url: str = API_URL) -> None:
        try:
            if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in base_url):
                raise ValueError
            parts = urlsplit(base_url)
            loopback = parts.scheme == "http" and parts.hostname in _LOOPBACK
            if (
                not (parts.scheme == "https" or loopback)
                or not parts.hostname
                or parts.username is not None
                or parts.query
                or parts.fragment
            ):
                raise ValueError
            port = _DEFAULT_PORTS[parts.scheme] if parts.port is None else parts.port
            if not port:
                raise ValueError
        except ValueError:
            raise ValueError(
                "the GitHub API URL must use https (http only on 127.0.0.1), "
                "with a valid host and port and no credentials, query or fragment"
            ) from None
        self._token = token
        self._scheme = parts.scheme
        self._netloc = parts.netloc
        self._host = parts.hostname
        self._port = port
        self._prefix = parts.path.rstrip("/")

    def __repr__(self) -> str:
        return f"GitHubApi({self._host})"

    def request(self, method: str, path: str, body: object | None = None) -> object:
        """Send one request and return its parsed JSON (None for an empty body)."""
        proxy = _https_proxy(self._netloc) if self._scheme == "https" else None
        return self._parse(self._send(method, self._prefix + path, body, proxy), proxy)

    def _send(
        self, method: str, target: str, body: object | None, proxy: _Proxy | None
    ) -> _Response:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "devctl",
        }
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        connection = None
        try:
            connection = self._connection(proxy)
            connection.request(method, target, payload, headers)
            reply = connection.getresponse()
            data = reply.read(MAX_RESPONSE_BYTES + 1)
            return _Response(reply.status, reply.reason, data)
        except (OSError, HTTPException, ValueError) as failure:
            raise GitHubError(None, self._unreachable(failure, proxy)) from None
        finally:
            if connection is not None:
                connection.close()

    def _connection(self, proxy: _Proxy | None) -> HTTPConnection:
        if self._scheme == "http":
            return HTTPConnection(self._host, self._port, timeout=TIMEOUT_SECONDS)
        if proxy is None:
            return HTTPSConnection(self._host, self._port, timeout=TIMEOUT_SECONDS)
        connection = HTTPSConnection(proxy.host, proxy.port, timeout=TIMEOUT_SECONDS)
        connection.set_tunnel(self._host, self._port, proxy.tunnel_headers)
        return connection

    def _unreachable(
        self, failure: OSError | HTTPException | ValueError, proxy: _Proxy | None
    ) -> str:
        cause = self._clean(_cause(failure), proxy)
        if proxy is None:
            return (
                f"cannot connect to {self._netloc}: {cause}; "
                "check the network, or set HTTPS_PROXY if traffic must use a proxy"
            )
        return (
            f"cannot connect to {self._netloc} through the proxy {proxy.address} from HTTPS_PROXY: "
            f"{cause}; check that the proxy runs and allows {self._host}"
        )

    def _parse(self, response: _Response, proxy: _Proxy | None) -> object:
        if len(response.data) > MAX_RESPONSE_BYTES:
            raise GitHubError(response.status, f"response is over {MAX_RESPONSE_BYTES} bytes")
        if not 200 <= response.status < 300:
            raise GitHubError(response.status, self._clean(_message(response), proxy))
        if not response.data:
            return None
        try:
            return json.loads(response.data)
        except (ValueError, RecursionError):
            raise GitHubError(response.status, "response is not JSON") from None

    def _clean(self, text: str, proxy: _Proxy | None) -> str:
        """Redact before truncating, so a cut cannot leave part of a credential behind."""
        secrets = (self._token, *(proxy.redactions if proxy else ()))
        for secret in sorted(set(secrets), key=len, reverse=True):
            if secret:
                text = text.replace(secret, "[token]" if secret == self._token else "[credential]")
        return text[:MAX_MESSAGE_CHARACTERS]


def _message(response: _Response) -> str:
    """GitHub's own message for an error reply, else the HTTP reason."""
    try:
        parsed = json.loads(response.data)
    except (ValueError, RecursionError):
        return response.reason
    message = parsed.get("message") if isinstance(parsed, dict) else None
    return message if isinstance(message, str) and message else response.reason
