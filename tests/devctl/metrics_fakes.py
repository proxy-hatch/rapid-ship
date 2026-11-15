"""Offline: local merged history and a recorded gh executable; no network access."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, cast

import pytest

import devctl_project
from check_workspace import fake_tool
from devctl.metrics.api import IncidentMetric, Metric, MetricContext, MetricResult
from devctl.metrics.command import build_report
from devctl.metrics.github import GitHubReader
from devctl.metrics.report import render_json
from devctl.settings import load_project
from github_fakes import RecordedOwner, git

WAIT = 5.0  # the longest a test waits on an event, so a failing test cannot hang
NOW = datetime(2026, 10, 16, tzinfo=UTC)
PROJECT = '[[stack]]\nname = "python"\ndirectory = "."\n[github]\nrepository = "o/r"\n'
RESET = {"resources": {"core": {"reset": 1791007920}}}  # 2026-10-03 06:12 UTC
ALLOWANCE = "GitHub API allowance used up; it resets at 06:12 UTC"
WHEELS = ("cp312-macosx", "cp312-manylinux", "cp313-macosx", "cp313-manylinux")


def entry_text(date: str, category: str = "env-read", rungs: str = "[1]") -> str:
    """A valid Corrections ledger entry, dated date and naming the rungs in rungs."""
    return (
        f"---\ndate: {date}\nby: reviewer\nsource: session\ncategory: {category}\n"
        f"rungs: {rungs}\nprevention: Read configuration through settings.\nstatus: open\n---\n"
        "The review required settings.\n"
    )


def lock(version: int, packages: int) -> str:
    """A lock file whose packages each list four wheels, all of which every version rewrites."""

    def wheel(name: int, tag: str) -> str:
        digest = sha256(f"{name}{tag}{version}".encode()).hexdigest()
        url = f"https://files.example/pkg{name}-1.{version}-{tag}.whl"
        return f'    {{ url = "{url}", hash = "sha256:{digest}" }},\n'

    return "".join(
        f'[[package]]\nname = "pkg{name}"\nwheels = [\n'
        + "".join(wheel(name, tag) for tag in WHEELS)
        + "]\n\n"
        for name in range(packages)
    )


class MergedHistory:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir(parents=True, exist_ok=True)
        git(path, "init", "-q", "-b", "main")
        git(path, "config", "core.hooksPath", str(path / "empty-hooks"))
        git(path, "config", "commit.gpgsign", "false")
        self.owner = RecordedOwner({"repos/o/r": {"default_branch": "main"}})
        self.pulls: list[dict[str, object]] = []
        self.unmerged: list[dict[str, object]] = []
        self.push({"initial": "root"})

    def push(
        self, files: Mapping[str, str | bytes | None], message: str = "recorded change"
    ) -> str:
        """Commit files directly; None deletes one. No PR merges the commit."""
        for name, content in files.items():
            target = self.path / name
            if content is None:
                target.unlink()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                target.write_bytes(content)
            else:
                target.write_text(content)
        git(self.path, "add", ".")
        git(self.path, "commit", "-q", "--allow-empty", "-m", message)
        sha = git(self.path, "rev-parse", "HEAD")
        self.owner.serve(f"repos/o/r/commits/{sha}/pulls?per_page=64&page=1", [])
        return sha

    def revert(self, sha: str, *, merge: bool = False) -> str:
        """Undo sha with git revert, as a commit that no PR merges."""
        git(self.path, "revert", "--no-edit", *(["-m", "1"] if merge else []), sha)
        revert = git(self.path, "rev-parse", "HEAD")
        self.owner.serve(f"repos/o/r/commits/{revert}/pulls?per_page=64&page=1", [])
        return revert

    def merge(
        self,
        number: int,
        files: Mapping[str, str],
        author: str = "o-worker[bot]",
        body: str = "",
        *,
        parents: int = 1,
    ) -> str:
        if parents == 2:
            git(self.path, "checkout", "-q", "-b", f"pr-{number}")
            self.push(files)
            git(self.path, "checkout", "-q", "main")
            git(self.path, "merge", "-q", "--no-ff", "-m", "recorded merge", f"pr-{number}")
            sha = git(self.path, "rev-parse", "HEAD")
        else:
            sha = self.push(files)
        pr: dict[str, object] = {
            "number": number,
            "user": {"login": author},
            "body": body,
            "merged_at": f"2026-10-{number:02d}T06:12:00Z",
            "closed_at": f"2026-10-{number:02d}T06:12:00Z",
            "updated_at": f"2026-10-{number:02d}T06:12:00Z",
            "merge_commit_sha": sha,
            "html_url": f"https://example.invalid/pull/{number}",
        }
        self.pulls.insert(0, pr)
        self.owner.serve(f"repos/o/r/commits/{sha}/pulls?per_page=64&page=1", [pr])
        self.closed_pages()
        return sha

    def close(self, number: int, closer: str = "person", author: str = "o-worker[bot]") -> None:
        """Record a PR that closer closed without merging, on the day of October 2026 it names."""
        stamp = f"2026-10-{number:02d}T06:12:00Z"
        self.unmerged.insert(
            0,
            {
                "number": number,
                "user": {"login": author},
                "body": "",
                "merged_at": None,
                "closed_at": stamp,
                "updated_at": stamp,
                "merge_commit_sha": None,
                "html_url": f"https://example.invalid/pull/{number}",
            },
        )
        self.owner.serve(
            f"repos/o/r/issues/{number}/events?per_page=64&page=1",
            [{"event": "closed", "actor": {"login": closer}}],
        )
        self.closed_pages()

    def closed_pages(self) -> None:
        for offset in range(0, len(self.pulls) + 1, 64):
            self.owner.serve(
                "repos/o/r/pulls?state=closed&base=main&sort=updated&direction=desc"
                f"&per_page=64&page={offset // 64 + 1}",
                self.pulls[offset : offset + 64],
            )
        closed = sorted([*self.pulls, *self.unmerged], key=lambda pr: str(pr["updated_at"]))
        closed.reverse()
        for offset in range(0, len(closed) + 1, 64):
            self.owner.serve(
                "repos/o/r/pulls?state=closed&sort=updated&direction=desc"
                f"&per_page=64&page={offset // 64 + 1}",
                closed[offset : offset + 64],
            )

    def publish(self) -> str:
        sha = git(self.path, "rev-parse", "HEAD")
        git(self.path, "update-ref", "refs/remotes/origin/main", sha)
        self.closed_pages()
        return sha


def fake_gh(directory: Path, served: Mapping[str, object]) -> Path:
    """Project the approved recorded filters before printing, as gh --jq does.

    A GET is served under its path. A POST or PATCH must pass --input -: its stdin body, which must
    be JSON, is appended to stdin.log, and the answer is served under "<METHOD> <path>".
    """
    data = directory / "served.json"
    directory.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps(served))
    return fake_tool(
        directory,
        "gh",
        """
import re
served = json.loads(here.with_name('served.json').read_text())
method, key = sys.argv[3], sys.argv[4]
assert sys.argv[1:3] == ['api', '--method'] and method in ('GET', 'POST', 'PATCH')
if method != 'GET':
    assert sys.argv[5:] == ['--input', '-']
    with open(here.with_name('stdin.log'), 'a') as stdin_log:
        stdin_log.write(json.dumps(json.loads(sys.stdin.read())) + '\\n')
    key = method + ' ' + key
value = served[key]
if isinstance(value, dict) and 'error' in value:
    sys.stderr.write(value['error'])
    sys.exit(1)
if '--jq' in sys.argv:
    projection = sys.argv[sys.argv.index('--jq') + 1]
    if projection.startswith('['):
        rows = value['workflow_runs'] if '.workflow_runs[]' in projection else value
        fields = re.findall(r'\\b([a-z_]+)\\b', projection)
        # A body is output only where the filter names it outside its marker test.
        named = projection.replace('(.body // "")', '')
        selects_body = 'body' in re.findall(r'\\b([a-z_]+)\\b', named)
        projected = []
        for row in rows:
            item = {key: row.get(key) for key in fields if key in row}
            if 'has_marker' in fields:
                marker = '<!-- rapid-ship-metrics -->'
                item['has_marker'] = (row.get('body') or '').startswith(marker)
            if not selects_body:
                item.pop('body', None)
            projected.append(item)
        value = projected
    else:
        value = {key: value.get(key) for key in re.findall(r'[a-z_]+', projection)}
sys.stdout.write(json.dumps(value))
""",
    )


def block_gh(directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Put a gh that always fails first on PATH, so that a test cannot reach a real one."""
    fake_tool(directory, "gh", "sys.exit('gh is blocked in this test')")
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")


def served_project(path: Path, metrics_toml: str = "", *, prs: int = 1) -> MergedHistory:
    """A repository with merged PRs and its settings, and every read that a report of it makes."""
    h = MergedHistory(path)
    (path / ".rapid-ship").mkdir()
    (path / ".rapid-ship/project.toml").write_text(PROJECT)
    (path / ".rapid-ship/metrics.toml").write_text("window = 30\n" + metrics_toml)
    for number in range(1, prs + 1):
        sha = h.merge(number, {})
        h.owner.serve(f"repos/o/r/pulls/{number}/reviews?per_page=64&page=1", [])
        h.owner.serve(
            f"repos/o/r/actions/workflows/devctl-check.yml/runs?head_sha={sha}"
            "&event=push&per_page=64&page=1",
            [{"id": number, "run_number": 1, "run_attempt": 1, "conclusion": "success"}],
        )
    h.publish()
    return h


def report_json(h: MergedHistory) -> dict[str, Any]:
    """The report of h, as ./devctl metrics --json prints it."""
    report = build_report(
        h.path, load_project(h.path), None, GitHubReader("o/r", h.owner), lambda: NOW
    )
    return cast("dict[str, Any]", json.loads(render_json(report)))


def use_metrics(monkeypatch: pytest.MonkeyPatch, *metrics: Metric) -> None:
    """Make devctl_project.metrics() return these metrics."""
    monkeypatch.setattr(devctl_project, "metrics", lambda: list(metrics), raising=False)


class Probe(Metric):
    """A code metric that runs a function and remembers the threads it ran on."""

    def __init__(
        self, run: Callable[[MetricContext], MetricResult], metric_id: str = "probes"
    ) -> None:
        self.id = metric_id
        self.title = "Probes"
        self.run = run
        self.started = threading.Event()
        self.threads: list[threading.Thread] = []

    def measure(self, context: MetricContext) -> MetricResult:
        self.threads.append(threading.current_thread())
        self.started.set()
        return self.run(context)

    def join(self) -> None:
        """Wait until measure has begun, then for every thread: none may outlive its test."""
        assert self.started.wait(WAIT)
        for thread in self.threads:
            thread.join(WAIT)
        assert not any(thread.is_alive() for thread in self.threads)


class IncidentProbe(Probe, IncidentMetric):
    """A Probe that is an incident metric."""


class Gate:
    """A request parked inside the owner: entered says it is in flight, release lets it finish."""

    def __init__(self) -> None:
        self.entered = threading.Event()
        self.release = threading.Event()


class GatedOwner(RecordedOwner):
    """A RecordedOwner whose gated paths stay in flight until the test releases them."""

    def __init__(self, served: Mapping[str, object]) -> None:
        super().__init__(served)
        self.gates: dict[str, Gate] = {}

    def gate(self, path: str) -> Gate:
        self.gates[path] = Gate()
        return self.gates[path]

    def __call__(self, path: str, jq: str | None = None) -> object:
        gate = self.gates.get(path)
        if gate is not None:
            gate.entered.set()
            assert gate.release.wait(WAIT)
        return super().__call__(path, jq)


def gh_argv(directory: Path) -> list[list[str]]:
    """The arguments of every call the fake gh in directory received, in order."""
    lines = (directory / "gh.log").read_text().splitlines()
    return [json.loads(line)["argv"] for line in lines]


def gh_bodies(directory: Path) -> list[dict[str, object]]:
    """The JSON body of every write the fake gh in directory received, in order."""
    log = directory / "stdin.log"
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
