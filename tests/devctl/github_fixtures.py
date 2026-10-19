"""Fixtures for the offline GitHub, doctor and devctl as tests. Loaded by tests/conftest.py."""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
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

from check_workspace import project_settings
from devctl import process
from devctl.doctor_items import DoctorContext, OwnerReadError
from devctl.github.app import GitHubAccess
from devctl.process import ProcessResult
from devctl.settings import Agent, App, Harness, ProjectSettings
from github_fakes import (
    REVIEWER_ID,
    REVIEWER_INSTALLATION,
    REVIEWER_PERMISSIONS,
    WORKER_ID,
    WORKER_INSTALLATION,
    WORKER_PERMISSIONS,
    FakeGitHub,
    FakeHarness,
    FakeKeychain,
    FakeRun,
    MakeContext,
    RecordedOwner,
    Remote,
    RepoFiles,
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


@pytest.fixture
def project() -> ProjectSettings:
    """o/r with a Roster of two Harnesses and both Apps recorded, so Agent identity is on."""
    return project_settings(
        repository="o/r",
        worker_app=App(WORKER_ID, "rs-worker"),
        reviewer_app=App(REVIEWER_ID, "rs-reviewer"),
        roster={
            "worker": Agent("agy", "gemini-3.8-flash-high"),
            "reviewer": Agent("claude", "claude-opus-5-5"),
        },
    )


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    """Patch process.run_process and shutil.which. Nothing a test starts through devctl runs."""
    fake = FakeRun()
    monkeypatch.setattr(process, "run_process", fake.run_process)
    monkeypatch.setattr(shutil, "which", fake.which)
    return fake


@pytest.fixture
def fake_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeHarness:
    """PATH holds only a directory of fake executables, /usr/bin and /bin, so no real Harness or
    gh is found."""
    directory = tmp_path / "harness-bin"
    directory.mkdir()
    monkeypatch.setenv("PATH", os.pathsep.join([str(directory), "/usr/bin", "/bin"]))
    return FakeHarness(directory)


def no_owner_reads(path: str) -> object:
    raise OwnerReadError(None, "no owner reads in this test")


@pytest.fixture
def ctx(tmp_path: Path, isolated_home: Path, project: ProjectSettings) -> MakeContext:
    """Make DoctorContexts for a temporary repository on main, with no access and no owner reads.

    worker=(harness, model) replaces the Roster's Worker. excluded replaces project.excluded, as
    load_project would from [kit] exclude.
    """
    root = tmp_path / "doctor-repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")

    def make(
        *, worker: tuple[Harness, str] | None = None, excluded: Sequence[str] = ()
    ) -> DoctorContext:
        settings = dataclasses.replace(project, excluded=tuple(excluded))
        if worker is not None:
            roster = {**settings.roster, "worker": Agent(*worker)}
            settings = dataclasses.replace(settings, roster=roster)
        return DoctorContext(root, settings, no_owner_reads, None)

    return make


@pytest.fixture
def repo_files(ctx: MakeContext) -> RepoFiles:
    """Writes into ctx's repository, and git adds what it writes."""
    context = ctx()
    return RepoFiles(context.root, context.project.stack)


FIXTURES = Path(__file__).parent / "fixtures" / "github"


@pytest.fixture
def recorded() -> RecordedOwner:
    """The owner's gh reads of o/r, as GitHub answered on 2026-10-14. Other paths are a 404."""

    def fixture(name: str) -> object:
        return json.loads((FIXTURES / name).read_text())

    return RecordedOwner(
        {
            "repos/o/r": fixture("repository.json"),
            "repos/o/r/rulesets?targets=branch": fixture("ruleset-list.json"),
            "repos/o/r/rulesets/9": fixture("ruleset.json"),
            "repos/o/r/actions/permissions/fork-pr-contributor-approval": fixture(
                "fork-approval.json"
            ),
            "repos/o/r/contents/.github/CODEOWNERS?ref=main": fixture("codeowners.json"),
        }
    )


@pytest.fixture
def ctx_github(
    isolated_home: Path,
    project: ProjectSettings,
    github: FakeGitHub,
    keychain: FakeKeychain,
    recorded: RecordedOwner,
    repo_files: RepoFiles,
) -> MakeContext:
    """Make DoctorContexts for the temporary repository in Walk with Agent identity on, and o/r on
    the simulated GitHub. The owner reads are the recorded ones. keychain replaces the Keychain
    that holds both keys."""
    repo_files.lock(unchanged=[], missing=[])  # so a missing key can name rapid-ship app

    def make(*, keychain: FakeKeychain = keychain) -> DoctorContext:
        access = GitHubAccess("o/r", api_url=github.url, keychain=keychain)
        return DoctorContext(repo_files.root, project, recorded, access)

    return make
