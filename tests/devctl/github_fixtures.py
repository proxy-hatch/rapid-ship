"""Fixtures for the offline GitHub, doctor and devctl as tests. Loaded by tests/conftest.py."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from devctl import process
from devctl.github.app import GitHubAccess
from devctl.process import ProcessResult
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_INSTALLATION,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeKeychain,
    Remote,
    git,
)


@pytest.fixture(scope="session")
def app_keys() -> dict[str, tuple[bytes, bytes]]:
    """Throwaway RSA test keys, made in memory for this test session: {role: (private, public)}.

    No real App uses them, and nothing writes them to disk.
    """
    keys: dict[str, tuple[bytes, bytes]] = {}
    for role in ("worker", "reviewer"):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(Encoding.PEM, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
        keys[role] = (private, public)
    return keys


@pytest.fixture
def keychain(app_keys: dict[str, tuple[bytes, bytes]]) -> FakeKeychain:
    """Both test keys under the Keychain items that rapid-ship app writes, named by App ID."""
    return FakeKeychain(
        {
            f"rapid-ship/worker-app/{WORKER_ID}": app_keys["worker"][0],
            f"rapid-ship/reviewer-app/{REVIEWER_ID}": app_keys["reviewer"][0],
        }
    )


@pytest.fixture
def keychain_without_reviewer(app_keys: dict[str, tuple[bytes, bytes]]) -> FakeKeychain:
    """A Keychain that holds only the Worker App's key."""
    return FakeKeychain({f"rapid-ship/worker-app/{WORKER_ID}": app_keys["worker"][0]})


@pytest.fixture
def github(app_keys: dict[str, tuple[bytes, bytes]]) -> Iterator[FakeGitHub]:
    """Simulated GitHub with the Worker App and the Reviewer App, both installed on o/r."""
    fake = FakeGitHub()
    fake.add_app(WORKER_ID, "rs-worker", app_keys["worker"][1])
    fake.add_app(REVIEWER_ID, "rs-reviewer", app_keys["reviewer"][1])
    fake.install(WORKER_ID, "o/r", WORKER_PERMISSIONS, WORKER_INSTALLATION)
    fake.install(REVIEWER_ID, "o/r", REVIEWER_PERMISSIONS, REVIEWER_INSTALLATION)
    yield fake
    fake.close()


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """HOME in tmp_path, so git never reads the owner's ~/.gitconfig.

    Not autouse: integration tests that run uv need the real HOME for its cache.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture
def remote(tmp_path: Path, isolated_home: Path) -> Remote:
    """A bare repository at tmp_path/remote.git and its clone at tmp_path/work/r.

    The clone has one commit on main, pushed.
    """
    bare = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "--initial-branch=main", str(bare))
    clone = tmp_path / "work" / "r"
    clone.parent.mkdir()
    git(clone.parent, "clone", "-q", str(bare), str(clone))
    git(clone, "symbolic-ref", "HEAD", "refs/heads/main")
    git(clone, "commit", "-q", "--allow-empty", "-m", "Initial commit")
    git(clone, "push", "-q", "-u", "origin", "main")
    return Remote(bare, clone, (clone / ".git").resolve())


@pytest.fixture
def access(github: FakeGitHub, remote: Remote, keychain: FakeKeychain) -> GitHubAccess:
    """o/r on the simulated GitHub, its git remote the bare repository, its keys the test keys."""
    return GitHubAccess("o/r", api_url=github.url, remote_url=str(remote.bare), keychain=keychain)


@pytest.fixture
def recorded_argv(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Every argv passed to devctl.process.run_process, in order. Each process still runs."""
    seen: list[list[str]] = []
    real = process.run_process

    def record(
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        seen.append(list(argv))
        return real(argv, cwd, timeout_seconds, env=env, input_text=input_text)

    monkeypatch.setattr(process, "run_process", record)
    return seen
