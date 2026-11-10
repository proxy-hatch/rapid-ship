"""Offline: local merged history and a recorded gh executable; no network access."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from check_workspace import fake_tool
from github_fakes import RecordedOwner, git


class MergedHistory:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.mkdir(parents=True, exist_ok=True)
        git(path, "init", "-q", "-b", "main")
        git(path, "config", "core.hooksPath", str(path / "empty-hooks"))
        git(path, "config", "commit.gpgsign", "false")
        self.owner = RecordedOwner({"repos/o/r": {"default_branch": "main"}})
        self.pulls: list[dict[str, object]] = []
        self.push({"initial": "root"})

    def push(self, files: Mapping[str, str]) -> str:
        for name, text in files.items():
            target = self.path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        git(self.path, "add", ".")
        git(self.path, "commit", "-q", "--allow-empty", "-m", "recorded change")
        sha = git(self.path, "rev-parse", "HEAD")
        self.owner.serve(f"repos/o/r/commits/{sha}/pulls?per_page=64&page=1", [])
        return sha

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

    def closed_pages(self) -> None:
        for offset in range(0, len(self.pulls) + 1, 64):
            self.owner.serve(
                "repos/o/r/pulls?state=closed&base=main&sort=updated&direction=desc"
                f"&per_page=64&page={offset // 64 + 1}",
                self.pulls[offset : offset + 64],
            )

    def publish(self) -> str:
        sha = git(self.path, "rev-parse", "HEAD")
        git(self.path, "update-ref", "refs/remotes/origin/main", sha)
        self.closed_pages()
        return sha


def fake_gh(directory: Path, served: Mapping[str, object]) -> Path:
    """Project the approved recorded filters before printing, as gh --jq does."""
    data = directory / "served.json"
    directory.mkdir(parents=True, exist_ok=True)
    data.write_text(json.dumps(served))
    return fake_tool(
        directory,
        "gh",
        """
import re
served = json.loads(here.with_name('served.json').read_text())
assert sys.argv[1:4] == ['api', '--method', 'GET']
value = served[sys.argv[4]]
if isinstance(value, dict) and 'error' in value:
    sys.stderr.write(value['error'])
    sys.exit(1)
if '--jq' in sys.argv:
    projection = sys.argv[sys.argv.index('--jq') + 1]
    if projection.startswith('['):
        rows = value['workflow_runs'] if '.workflow_runs[]' in projection else value
        fields = re.findall(r'\\b([a-z_]+)\\b', projection)
        projected = []
        for row in rows:
            item = {key: row.get(key) for key in fields if key in row}
            if 'has_marker' in fields:
                marker = '<!-- rapid-ship-metrics -->'
                item['has_marker'] = (row.get('body') or '').startswith(marker)
            if 'body' not in projection.split('has_marker')[0]:
                item.pop('body', None)
            projected.append(item)
        value = projected
    else:
        value = {key: value.get(key) for key in re.findall(r'[a-z_]+', projection)}
sys.stdout.write(json.dumps(value))
""",
    )
