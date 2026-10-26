"""Simulated GitHub, Keychain and repositories for offline devctl tests.

Nothing here contacts GitHub: a remote is a local bare repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import jwt

from devctl.doctor_items import DoctorContext, OwnerReadError
from devctl.github.app import KeychainMissing

# run_process is imported directly, so recorded_argv and fake_run never see test setup.
from devctl.process import ProcessResult, run_process

WORKER_ID = 101
REVIEWER_ID = 202
WORKER_INSTALLATION = 1001
REVIEWER_INSTALLATION = 2002
# Each App's permissions, written out so tests do not compare the code with itself.
WORKER_PERMISSIONS = {
    "contents": "write",
    "pull_requests": "write",
    "issues": "write",
    "metadata": "read",
}
REVIEWER_PERMISSIONS = {"pull_requests": "write", "contents": "read", "metadata": "read"}
MAX_JWT_SECONDS = 600  # GitHub refuses an App JWT that lives longer than 10 minutes
_UNAUTHORIZED = (401, {"message": "A JSON web token could not be decoded"})
_NOT_FOUND = (404, {"message": "Not Found"})


@dataclass(frozen=True)
class Call:
    method: str
    path: str
    query: dict[str, list[str]]
    headers: dict[str, str]
    body: Any


Reply = tuple[Any, ...]  # (status, body) or (status, body, headers)
Handler = Callable[[Call, re.Match[str]], Reply]
MakeContext = Callable[..., DoctorContext]
RunAs = Callable[..., int]  # the run_as fixture: (role, action, *arguments, settings=...)


@dataclass(frozen=True)
class FakeApp:
    slug: str
    public_key_pem: bytes


@dataclass(frozen=True)
class FakeInstallation:
    installation_id: int
    permissions: dict[str, str]


class FakeGitHub:
    """GitHub's REST API, simulated on 127.0.0.1.

    Routes match the path with re.fullmatch; the most recently added route wins. Two generic
    routes answer for the Apps that add_app registers and install installs: a repository's
    installation, and installation token mints. Each needs a valid App JWT. A test adds any other
    route it needs with route().
    """

    def __init__(self) -> None:
        self.calls: list[Call] = []
        self.routes: list[tuple[str, re.Pattern[str], Handler]] = []
        self.apps: dict[int, FakeApp] = {}
        self.installations: dict[tuple[int, str], FakeInstallation] = {}
        self.issued_tokens: list[str] = []
        fake = self

        class _Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                parts = urlsplit(self.path)
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                call = Call(
                    self.command,
                    parts.path,
                    parse_qs(parts.query),
                    dict(self.headers.items()),
                    json.loads(raw) if raw else None,
                )
                fake.calls.append(call)
                status, body, headers = fake.reply(call)
                data = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PATCH = do_PUT = do_DELETE = _serve

            def log_message(self, *args: object) -> None:
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        # A short poll interval makes close() return at once; the default 0.5 s costs every test.
        serve = self.server.serve_forever
        threading.Thread(target=serve, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.route("GET", r"/repos/([^/]+/[^/]+)/installation", self._installation)
        self.route("POST", r"/app/installations/(\d+)/access_tokens", self._access_token)

    def add_app(self, app_id: int, slug: str, public_key_pem: bytes) -> None:
        self.apps[app_id] = FakeApp(slug, public_key_pem)

    def install(
        self, app_id: int, repository: str, permissions: dict[str, str], installation_id: int
    ) -> None:
        self.installations[(app_id, repository)] = FakeInstallation(
            installation_id, dict(permissions)
        )

    def uninstall(self, app_id: int, repository: str) -> None:
        del self.installations[(app_id, repository)]

    def jwt_app_id(self, call: Call) -> int | None:
        """The App whose JWT authorises call, or None when the JWT is missing or invalid.

        The issuer is read unverified only to pick the App's public key; the signature, iat, exp
        and iss are then verified with it, and the JWT may live at most 10 minutes.
        """
        scheme, _, token = call.headers.get("Authorization", "").partition(" ")
        if scheme != "Bearer" or not token:
            return None
        try:
            app_id = int(jwt.decode(token, options={"verify_signature": False})["iss"])
            claims = jwt.decode(
                token,
                self.apps[app_id].public_key_pem,
                algorithms=["RS256"],
                options={"require": ["iat", "exp", "iss"]},
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            return None
        return app_id if claims["exp"] - claims["iat"] <= MAX_JWT_SECONDS else None

    def _installation(self, call: Call, match: re.Match[str]) -> Reply:
        app_id = self.jwt_app_id(call)
        if app_id is None:
            return _UNAUTHORIZED
        found = self.installations.get((app_id, match[1]))
        if found is None:
            return _NOT_FOUND
        return 200, {
            "id": found.installation_id,
            "app_id": app_id,
            "app_slug": self.apps[app_id].slug,
            "permissions": found.permissions,
            "repository_selection": "selected",
        }

    def _access_token(self, call: Call, match: re.Match[str]) -> Reply:
        app_id = self.jwt_app_id(call)
        if app_id is None:
            return _UNAUTHORIZED
        owned = {
            found.installation_id
            for (owner, _), found in self.installations.items()
            if owner == app_id
        }
        if int(match[1]) not in owned:
            return _NOT_FOUND
        # Longer than 40 characters, like GitHub's stateless token format.
        token = "ghs_" + secrets.token_urlsafe(64)
        self.issued_tokens.append(token)
        expires = datetime.now(UTC) + timedelta(hours=1)
        return 201, {
            "token": token,
            "expires_at": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "permissions": (call.body or {}).get("permissions"),
        }

    def route(self, method: str, pattern: str, handler: Handler) -> None:
        self.routes.append((method, re.compile(pattern), handler))

    def reply(self, call: Call) -> tuple[int, Any, dict[str, str]]:
        for method, pattern, handler in reversed(self.routes):
            match = pattern.fullmatch(call.path)
            if method == call.method and match:
                answer = handler(call, match)
                headers: dict[str, str] = answer[2] if len(answer) > 2 else {}
                return answer[0], answer[1], headers
        return 404, {"message": "Not Found"}, {}

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


class FakeKeychain:
    """The macOS Keychain, simulated: generic-password items by service name."""

    def __init__(self, items: dict[str, bytes]) -> None:
        self.items = dict(items)

    def read(self, service: str) -> bytes:
        try:
            return self.items[service]
        except KeyError:
            raise KeychainMissing(service) from None


GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def git(cwd: Path, *args: str) -> str:
    """Run git for test setup with a fixed identity; assert it succeeds and return its output."""
    result = run_process(["git", *args], cwd, 60, env=GIT_IDENTITY)
    assert result.returncode == 0, f"git {' '.join(args)} failed: {result.stderr}"
    return result.stdout.strip()


def files_containing(root: Path, needle: str) -> list[Path]:
    """Every regular, non-symlink file under root whose bytes contain needle, sorted.

    Used to prove a secret reached no file: root is a test's tmp_path, which holds the isolated
    HOME, the bare repository, the clone and every .git directory.
    """
    data = needle.encode()
    found: list[Path] = []
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory, name)
            if path.is_symlink() or not path.is_file():
                continue
            if data in path.read_bytes():
                found.append(path)
    return sorted(found)


@dataclass(frozen=True)
class Remote:
    """A local bare repository in GitHub's place, and a clone of it with main pushed.

    branch and commit_on run git outside the clone, so rules a test writes into the clone's git
    config, such as insteadOf, never apply to them. commit_in runs git in the worktree it is given.
    """

    bare: Path
    clone: Path
    git_common_dir: Path  # the clone's resolved .git, as Repo.discover(clone) reports it

    def branch(self, name: str) -> str | None:
        """The branch's head on the bare repository, or None when it has no such branch."""
        listed = git(self.bare, "ls-remote", "--heads", str(self.bare))
        for line in listed.splitlines():
            sha, _, ref = line.partition("\t")
            if ref == f"refs/heads/{name}":
                return sha
        return None

    def commit_on(self, branch: str, message: str) -> str:
        """Commit a new file on the bare repository's branch from a temporary clone; return it."""
        with tempfile.TemporaryDirectory(dir=self.bare.parent) as scratch:
            work = Path(scratch) / "c"
            git(self.bare.parent, "clone", "-q", "--branch", branch, str(self.bare), str(work))
            # A new file makes each commit distinct, even with its parent, message and second
            # shared with another.
            (work / f"{secrets.token_hex(4)}.txt").write_text(message + "\n")
            git(work, "add", "--all")
            git(work, "commit", "-q", "-m", message)
            git(work, "push", "-q", "origin", f"HEAD:refs/heads/{branch}")
            return git(work, "rev-parse", "HEAD")

    def commit_in(self, worktree: Path, message: str) -> str:
        """Commit a new file in the worktree and return the new HEAD."""
        (worktree / f"{secrets.token_hex(4)}.txt").write_text(message)
        git(worktree, "add", "--all")
        git(worktree, "commit", "-q", "-m", message)
        return git(worktree, "rev-parse", "HEAD")


class RecordedOwner:
    """The owner's gh GET, recorded: an owner_get that serves responses by exact path.

    A path that nobody served is GitHub's 404. paths keeps every path asked for, in order, and
    filters the jq filter of each path read with one; the response is served whole either way.
    """

    def __init__(self, served: Mapping[str, object]) -> None:
        self._served: dict[str, object] = dict(served)
        self.paths: list[str] = []
        self.filters: dict[str, str] = {}

    def __call__(self, path: str, jq: str | None = None) -> object:
        self.paths.append(path)
        if jq is not None:
            self.filters[path] = jq
        found = self._served.get(path, OwnerReadError(404, "Not Found"))
        if isinstance(found, OwnerReadError):
            raise found
        return found

    def serve(self, path: str, value: object) -> None:
        """Answer path with value from now on."""
        self._served[path] = value

    def fail(self, path: str, error: OwnerReadError) -> None:
        """Make a read of path raise error from now on."""
        self._served[path] = error


class FakeRun:
    """devctl.process.run_process and shutil.which, simulated for doctor's tests.

    Every argv is recorded in argv. A command answers with the result set for its executable's base
    name and arguments by answer(), or with exit 1 and no output; shutil.which finds every name
    under /usr/bin. Test setup never goes through the patch: github_fakes.git imports run_process
    directly, and Repo runs git through its own _git.
    """

    def __init__(self) -> None:
        self.argv: list[list[str]] = []
        self._answers: dict[tuple[str, ...], ProcessResult] = {}

    @staticmethod
    def _key(argv: Sequence[str]) -> tuple[str, ...]:
        return (Path(argv[0]).name, *argv[1:])

    def answer(self, argv: list[str], result: ProcessResult) -> None:
        self._answers[self._key(argv)] = result

    def run_process(
        self,
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        self.argv.append(list(argv))
        return self._answers.get(self._key(argv)) or ProcessResult(list(argv), 1, "", "", 0.0)

    @staticmethod
    def which(cmd: str, mode: int = os.F_OK | os.X_OK, path: str | None = None) -> str | None:
        return f"/usr/bin/{cmd}"


class FakeHarness:
    """Harness executables on a PATH of their own: a /bin/sh script per installed name.

    Each run appends its working directory to <name>.cwd and its arguments, one per line and then a
    line --end--, to <name>.args; it prints <name>.stdout and <name>.stderr and exits with the
    installed code. A name that was not installed is not on PATH.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def install(self, name: str, *, stdout: str = "", stderr: str = "", code: int = 0) -> None:
        (self.directory / f"{name}.stdout").write_text(stdout)
        (self.directory / f"{name}.stderr").write_text(stderr)
        script = self.directory / name
        script.write_text(
            "#!/bin/sh\n"
            'here="${0%/*}"\n'
            f'pwd >> "$here/{name}.cwd"\n'
            f'for argument in "$@"; do printf \'%s\\n\' "$argument" >> "$here/{name}.args"; done\n'
            f"printf '%s\\n' --end-- >> \"$here/{name}.args\"\n"
            f'cat "$here/{name}.stdout"\n'
            f'cat "$here/{name}.stderr" >&2\n'
            f"exit {code}\n"
        )
        script.chmod(0o755)

    def calls(self, name: str) -> list[list[str]]:
        """The arguments of each run of name, in order; empty when the script never ran."""
        record = self.directory / f"{name}.args"
        if not record.exists():
            return []
        runs: list[list[str]] = [[]]
        for line in record.read_text().splitlines():
            if line == "--end--":
                runs.append([])
            else:
                runs[-1].append(line)
        return runs[:-1]

    def cwds(self, name: str) -> list[Path]:
        record = self.directory / f"{name}.cwd"
        if not record.exists():
            return []
        return [Path(line) for line in record.read_text().splitlines()]


@dataclass(frozen=True)
class RepoFiles:
    """Writes tracked files into the temporary repository that the ctx fixture made."""

    root: Path
    stack: str

    def write(self, path: str, text: str) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        git(self.root, "add", "--", path)

    def workflow(self, job_name: str) -> None:
        """.github/workflows/devctl-check.yml with one job of that name."""
        self.write(
            ".github/workflows/devctl-check.yml",
            "name: devctl check\n"
            "on:\n  pull_request:\n"
            f"jobs:\n  check:\n    name: {job_name}\n    runs-on: ubuntu-24.04\n"
            "    steps:\n      - run: ./devctl check --tier full\n",
        )

    def lock(
        self, unchanged: Sequence[str], missing: Sequence[str], stale: Sequence[str] = ()
    ) -> None:
        """A lock at kit_version 0.2.0 that records no exclusion.

        Each unchanged file is written with its real sha256. A missing file is not written. A stale
        entry records a sha256 that no file matches: its file is modified, or missing when absent.
        """
        lines = [f'kit_version = "0.2.0"\nstack = "{self.stack}"\n']
        written = [(path, self._write_unchanged(path)) for path in unchanged]
        entries = [(path, hashlib.sha256(content).hexdigest()) for path, content in written]
        entries += [(path, hashlib.sha256(b"missing").hexdigest()) for path in missing]
        entries += [(path, "0" * 64) for path in stale]
        for path, sha256 in entries:
            lines.append(
                f'[[file]]\npath = {json.dumps(path)}\nkind = "managed"\nsha256 = "{sha256}"\n'
            )
        self.write(".rapid-ship/kit.lock", "\n".join(lines))

    def _write_unchanged(self, path: str) -> bytes:
        content = f"{path}, as the lock records it\n"
        self.write(path, content)
        return content.encode()
