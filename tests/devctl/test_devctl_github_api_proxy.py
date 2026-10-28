"""Offline and simulated: GitHubApi behind an HTTP CONNECT proxy on 127.0.0.1. No network.

Only loopback names resolve, as where a proxy is the only way out. The simulated GitHub answers
https with a certificate from a test CA, and SSL_CERT_FILE trusts that CA.
Test credentials are generated locally.
"""

from __future__ import annotations

import base64
import contextlib
import secrets
import socket
import ssl
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from http.client import HTTPSConnection
from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from devctl.github.api import GitHubApi, GitHubError
from devctl.process import NETWORK_VARIABLES
from github_fakes import FakeGitHub

LOOPBACK_NAMES = ("127.0.0.1", "localhost")


class FakeProxy:
    """An HTTP CONNECT proxy on 127.0.0.1 that tunnels every CONNECT to one local port.

    heads records the request line and headers of each CONNECT. Without an upstream port, the
    proxy answers each CONNECT with refusal instead.
    """

    def __init__(self, upstream_port: int | None = None, refusal: str = "502 Bad Gateway") -> None:
        self.heads: list[str] = []
        self.traffic = bytearray()
        self._upstream_port = upstream_port
        self._refusal = refusal
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.port: int = self._listener.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self) -> None:
        with contextlib.suppress(OSError):  # close() ends accept() with an OSError
            while True:
                client, _ = self._listener.accept()
                threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client: socket.socket) -> None:
        with client:
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = client.recv(4096)
                if not chunk:
                    return
                head += chunk
            self.heads.append(head.partition(b"\r\n\r\n")[0].decode("latin-1"))
            if self._upstream_port is None:
                client.sendall(f"HTTP/1.1 {self._refusal}\r\n\r\n".encode())
                return
            with socket.create_connection(("127.0.0.1", self._upstream_port)) as upstream:
                client.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                back = threading.Thread(target=_pipe, args=(upstream, client), daemon=True)
                back.start()
                _pipe(client, upstream, self.traffic)
                back.join(timeout=5)

    def close(self) -> None:
        self._listener.close()


def _pipe(source: socket.socket, target: socket.socket, capture: bytearray | None = None) -> None:
    with contextlib.suppress(OSError):
        while data := source.recv(65536):
            if capture is not None:
                capture.extend(data)
            target.sendall(data)
        target.shutdown(socket.SHUT_WR)


def _certificate(
    subject: str, issuer: x509.Name, public_key: ec.EllipticCurvePublicKey
) -> x509.CertificateBuilder:
    now = datetime.now(UTC)
    return (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(hours=1))
    )


def tls_server(directory: Path) -> tuple[ssl.SSLContext, Path]:
    """A server context for api.github.com and localhost, and the file of the CA that signed it.

    The extensions are those that Python's default context checks strictly since 3.13.
    """
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "devctl test CA")])
    signing_only = x509.KeyUsage(
        digital_signature=False,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=True,
        crl_sign=True,
        encipher_only=False,
        decipher_only=False,
    )
    ca = (
        _certificate("devctl test CA", ca_name, ca_key.public_key())
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(signing_only, critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), False)
        .sign(ca_key, hashes.SHA256())
    )
    key = ec.generate_private_key(ec.SECP256R1())
    names = x509.SubjectAlternativeName([x509.DNSName("api.github.com"), x509.DNSName("localhost")])
    authority = x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key())
    server = (
        _certificate("api.github.com", ca_name, key.public_key())
        .add_extension(names, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(authority, critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    ca_file = directory / "ca.pem"
    ca_file.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    chain = directory / "server.pem"
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    chain.write_bytes(server.public_bytes(serialization.Encoding.PEM) + private)
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(chain)
    return context, ca_file


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """No proxy or certificate setting from this machine, and only loopback names resolve."""
    for name in NETWORK_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    resolve = socket.getaddrinfo

    def loopback_only(
        host: bytes | str | None, port: bytes | str | int | None, *options: int
    ) -> object:
        if host not in LOOPBACK_NAMES:
            raise socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided, or not known")
        return resolve(host, port, *options)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    return monkeypatch


@pytest.fixture
def secure_github(tmp_path: Path, environment: pytest.MonkeyPatch) -> Iterator[FakeGitHub]:
    context, ca_file = tls_server(tmp_path)
    environment.setenv("SSL_CERT_FILE", str(ca_file))
    github = FakeGitHub(tls=context)
    github.route("GET", "/repos/o/r", lambda call, _: (200, {"full_name": "o/r"}))
    yield github
    github.close()


@pytest.fixture
def proxy(secure_github: FakeGitHub) -> Iterator[FakeProxy]:
    tunnel = FakeProxy(secure_github.server.server_port)
    yield tunnel
    tunnel.close()


@pytest.fixture
def refusing_proxy() -> Iterator[FakeProxy]:
    refusing = FakeProxy(refusal="403 Forbidden")
    yield refusing
    refusing.close()


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("HTTPS_PROXY", "http://127.0.0.1:{port}"),
        ("https_proxy", "http://127.0.0.1:{port}"),
        ("HTTPS_PROXY", "127.0.0.1:{port}"),
    ],
)
def test_a_request_tunnels_through_the_proxy_that_the_environment_names(
    variable: str,
    value: str,
    environment: pytest.MonkeyPatch,
    secure_github: FakeGitHub,
    proxy: FakeProxy,
) -> None:
    environment.setenv(variable, value.format(port=proxy.port))

    assert GitHubApi("t").request("GET", "/repos/o/r") == {"full_name": "o/r"}
    assert proxy.heads[0].splitlines()[0] == "CONNECT api.github.com:443 HTTP/1.1"
    assert secure_github.calls[-1].headers["Host"] == "api.github.com"


@pytest.mark.parametrize("variable", ["NO_PROXY", "no_proxy"])
def test_a_host_that_no_proxy_lists_is_reached_directly(
    variable: str, environment: pytest.MonkeyPatch, secure_github: FakeGitHub, proxy: FakeProxy
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy.port}")
    environment.setenv(variable, "example.com, localhost")

    api = GitHubApi("t", base_url=secure_github.url)

    assert api.request("GET", "/repos/o/r") == {"full_name": "o/r"}
    assert proxy.heads == []


def test_proxy_credentials_reach_the_proxy_and_never_github(
    environment: pytest.MonkeyPatch, secure_github: FakeGitHub, proxy: FakeProxy
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://pro%40xy:pa%3Ass@127.0.0.1:{proxy.port}")

    token = secrets.token_urlsafe(48)
    GitHubApi(token).request("GET", "/repos/o/r")

    assert token not in proxy.heads[0]
    assert "Authorization: Bearer" not in proxy.heads[0]
    assert proxy.traffic
    assert token.encode() not in proxy.traffic
    assert secure_github.calls[-1].headers["Authorization"] == f"Bearer {token}"
    credentials = base64.b64encode(b"pro@xy:pa:ss").decode()
    assert f"Proxy-Authorization: Basic {credentials}" in proxy.heads[0].splitlines()
    assert "Proxy-Authorization" not in secure_github.calls[-1].headers


def test_a_refused_tunnel_names_the_host_the_proxy_and_the_cause(
    environment: pytest.MonkeyPatch, refusing_proxy: FakeProxy
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://someone:hunter2@127.0.0.1:{refusing_proxy.port}")
    secret = secrets.token_urlsafe(48)

    with pytest.raises(GitHubError) as caught:
        GitHubApi(secret).request("GET", "/repos/o/r")

    message = str(caught.value)
    assert message == (
        "GitHub request failed: cannot connect to api.github.com through the proxy "
        f"127.0.0.1:{refusing_proxy.port} from HTTPS_PROXY: "
        "OSError: Tunnel connection failed: 403 Forbidden; "
        "check that the proxy runs and allows api.github.com"
    )
    assert caught.value.status is None


def test_an_unreachable_proxy_is_named_with_the_cause(environment: pytest.MonkeyPatch) -> None:
    with socket.create_server(("127.0.0.1", 0)) as closed:
        port = closed.getsockname()[1]
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{port}")

    with pytest.raises(GitHubError) as caught:
        GitHubApi(secrets.token_urlsafe(48)).request("GET", "/repos/o/r")

    assert f"api.github.com through the proxy 127.0.0.1:{port} from HTTPS_PROXY: " in str(
        caught.value
    )
    assert "ConnectionRefusedError" in str(caught.value)


@pytest.mark.parametrize(
    "url",
    [
        "socks5://someone:hunter2@127.0.0.1:1080",
        "https://someone:hunter2@127.0.0.1:3128",
        "http://someone:hunter2@127.0.0.1:port",
        "http://someone:hunter2@:3128",
    ],
)
def test_a_proxy_devctl_cannot_use_is_refused_without_its_password(
    url: str, environment: pytest.MonkeyPatch
) -> None:
    environment.setenv("HTTPS_PROXY", url)

    with pytest.raises(GitHubError) as caught:
        GitHubApi("t").request("GET", "/repos/o/r")

    assert "HTTPS_PROXY" in str(caught.value)
    assert "http://" in str(caught.value)
    assert "hunter2" not in str(caught.value)


def test_a_failed_lookup_names_the_host_the_cause_and_the_proxy_setting(
    environment: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(GitHubError) as caught:
        GitHubApi(secrets.token_urlsafe(48)).request("GET", "/repos/o/r")

    message = str(caught.value)
    assert message.startswith("GitHub request failed: cannot connect to api.github.com: gaierror: ")
    assert "DNS lookup failed; the host could not be resolved" in message
    assert message.endswith("; check the network, or set HTTPS_PROXY if traffic must use a proxy")


@pytest.mark.parametrize(
    "url",
    [
        "http://user:password@[invalid]",
        "http://user:password\udcff@localhost",
        "http://user:password@[::1",
        "password://user:password@localhost:3128",
        "http://user:password@localhost:0",
        "http://user:password@localhost:65536",
        "http://user:password@local host:3128",
        "http://user:password@localhost:3128/path",
        "http://user:password@localhost:3128?password",
        "http://user:password@localhost:3128#password",
        "http://user:password@local\nhost:3128",
    ],
)
def test_malformed_proxy_settings_fail_with_safe_guidance(
    url: str, environment: pytest.MonkeyPatch
) -> None:
    environment.setenv("https_proxy", url)
    with pytest.raises(GitHubError) as caught:
        GitHubApi(secrets.token_urlsafe(48)).request("GET", "/repos/o/r")
    message = str(caught.value)
    assert "password" not in message
    assert "api.github.com" in message
    assert "HTTPS_PROXY" in message
    assert "http://" in message


@pytest.mark.parametrize("source", ["proxy", "github"])
def test_remote_errors_cannot_echo_proxy_credentials(
    source: str, environment: pytest.MonkeyPatch, secure_github: FakeGitHub
) -> None:
    token, password = secrets.token_urlsafe(48), secrets.token_urlsafe(24)
    auth = base64.b64encode(f"user:{password}".encode()).decode()
    echo = f"{password} {auth} {token}"
    upstream = secure_github.server.server_port if source == "github" else None
    tunnel = FakeProxy(upstream, refusal=f"407 {echo}")
    environment.setenv("HTTPS_PROXY", f"http://user:{password}@127.0.0.1:{tunnel.port}")
    secure_github.route("GET", "/repos/o/r", lambda call, _: (403, {"message": echo}))
    try:
        with pytest.raises(GitHubError) as caught:
            GitHubApi(token).request("GET", "/repos/o/r")
        assert all(secret not in str(caught.value) for secret in (token, password, auth))
    finally:
        tunnel.close()


@pytest.mark.parametrize("invalid", ["ca", "hostname"])
def test_tls_rejects_an_untrusted_target_before_sending_bearer(
    invalid: str,
    tmp_path: Path,
    environment: pytest.MonkeyPatch,
    secure_github: FakeGitHub,
    proxy: FakeProxy,
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy.port}")
    url = "https://wrong.example" if invalid == "hostname" else "https://api.github.com"
    if invalid == "ca":
        other = tmp_path / "other-ca"
        other.mkdir()
        _, ca_file = tls_server(other)
        environment.setenv("SSL_CERT_FILE", str(ca_file))
    token = secrets.token_urlsafe(48)
    with pytest.raises(GitHubError, match="SSLCertVerificationError"):
        GitHubApi(token, base_url=url).request("GET", "/repos/o/r")
    assert len(proxy.heads) == 1
    assert secure_github.calls == []
    assert token not in proxy.heads[0]


@pytest.mark.parametrize("lowercase", ["proxy", "empty"])
def test_lowercase_https_proxy_overrides_uppercase(
    lowercase: str,
    environment: pytest.MonkeyPatch,
    secure_github: FakeGitHub,
    proxy: FakeProxy,
    refusing_proxy: FakeProxy,
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{refusing_proxy.port}")
    value = f"http://127.0.0.1:{proxy.port}" if lowercase == "proxy" else ""
    environment.setenv("https_proxy", value)
    url = "https://api.github.com" if lowercase == "proxy" else secure_github.url
    assert GitHubApi(secrets.token_urlsafe(48), base_url=url).request("GET", "/repos/o/r")
    assert refusing_proxy.heads == []
    assert len(proxy.heads) == (1 if lowercase == "proxy" else 0)


@pytest.mark.parametrize(
    ("bypass", "direct"),
    [
        ("*", True),
        (".LOCALHOST", True),
        ("localhost:{port}", True),
        ("localhost:1", False),
        ("host", False),
        ("", False),
    ],
)
def test_no_proxy_matches_hosts_and_ports_with_lowercase_precedence(
    bypass: str,
    direct: bool,
    environment: pytest.MonkeyPatch,
    secure_github: FakeGitHub,
    proxy: FakeProxy,
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy.port}")
    environment.setenv("NO_PROXY", "*")
    environment.setenv("no_proxy", bypass.format(port=secure_github.server.server_port))
    assert GitHubApi(secrets.token_urlsafe(48), base_url=secure_github.url).request(
        "GET", "/repos/o/r"
    )
    assert len(proxy.heads) == (0 if direct else 1)
    if not direct:
        assert f"CONNECT localhost:{secure_github.server.server_port} " in proxy.heads[0]


def test_all_proxy_alone_is_not_an_https_proxy_in_urllib_semantics(
    environment: pytest.MonkeyPatch, secure_github: FakeGitHub, refusing_proxy: FakeProxy
) -> None:
    environment.setenv("ALL_PROXY", f"http://127.0.0.1:{refusing_proxy.port}")
    assert GitHubApi(secrets.token_urlsafe(48), base_url=secure_github.url).request(
        "GET", "/repos/o/r"
    )
    assert refusing_proxy.heads == []


def test_redirects_through_a_proxy_never_send_a_second_request(
    environment: pytest.MonkeyPatch, secure_github: FakeGitHub, proxy: FakeProxy
) -> None:
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy.port}")
    secure_github.route(
        "GET", "/repos/o/r", lambda call, _: (302, None, {"Location": "https://other.example"})
    )
    with pytest.raises(GitHubError) as caught:
        GitHubApi(secrets.token_urlsafe(48)).request("GET", "/repos/o/r")
    assert caught.value.status == 302
    assert len(proxy.heads) == 1
    assert len(secure_github.calls) == 1


def test_a_proxy_without_a_port_connects_to_port_80(
    environment: pytest.MonkeyPatch, secure_github: FakeGitHub, proxy: FakeProxy
) -> None:
    resolve = socket.getaddrinfo
    ports: list[bytes | str | int | None] = []

    def local_proxy(
        host: bytes | str | None, port: bytes | str | int | None, *options: int
    ) -> object:
        if host == "127.0.0.1" and port == 80:
            ports.append(port)
            port = proxy.port
        return resolve(host, port, *options)

    environment.setattr(socket, "getaddrinfo", local_proxy)
    environment.setenv("HTTPS_PROXY", "http://127.0.0.1")
    assert GitHubApi(secrets.token_urlsafe(48)).request("GET", "/repos/o/r")
    assert ports == [80]
    assert len(secure_github.calls) == 1


@pytest.mark.parametrize(
    ("url", "bypass", "direct"),
    [
        ("https://api.github.com", ".github.com", True),
        ("https://api.github.com", "hub.com", False),
        ("https://api.github.com:443", "api.github.com:443", True),
        ("https://api.github.com", "api.github.com:443", False),
    ],
)
def test_no_proxy_domain_boundaries_and_explicit_default_ports(
    url: str,
    bypass: str,
    direct: bool,
    environment: pytest.MonkeyPatch,
    secure_github: FakeGitHub,
    proxy: FakeProxy,
) -> None:
    resolve = socket.getaddrinfo

    def local_destination(
        host: bytes | str | None, port: bytes | str | int | None, *options: int
    ) -> object:
        if host == "api.github.com":
            host, port = "127.0.0.1", secure_github.server.server_port
        return resolve(host, port, *options)

    environment.setattr(socket, "getaddrinfo", local_destination)
    environment.setenv("HTTPS_PROXY", f"http://127.0.0.1:{proxy.port}")
    environment.setenv("NO_PROXY", bypass)
    assert GitHubApi(secrets.token_urlsafe(48), base_url=url).request("GET", "/repos/o/r")
    assert len(proxy.heads) == (0 if direct else 1)


@pytest.mark.parametrize("error_number", [ssl.SSL_ERROR_SSL, ssl.SSL_ERROR_EOF])
def test_tls_protocol_failures_have_safe_tls_guidance(
    error_number: int, environment: pytest.MonkeyPatch
) -> None:
    token = secrets.token_urlsafe(48)
    remote_text = secrets.token_urlsafe(24)

    def fail_tls(connection: HTTPSConnection) -> None:
        raise ssl.SSLError(error_number, f"{remote_text} {token}")

    environment.setattr(HTTPSConnection, "connect", fail_tls)
    with pytest.raises(GitHubError) as caught:
        GitHubApi(token).request("GET", "/repos/o/r")

    message = str(caught.value)
    assert "cannot connect to api.github.com: SSLError: TLS connection failed" in message
    assert "check the proxy and TLS configuration" in message
    assert "Operation not permitted" not in message
    assert token not in message
    assert remote_text not in message
