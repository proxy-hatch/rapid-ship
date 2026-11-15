"""Offline: the metrics workflow template."""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from rapid_ship.cli import main
from rapid_ship.kit.lock import read_lock

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / "rapid_ship/templates/common/.github/workflows"
TEMPLATE = WORKFLOWS / "rapid-ship-metrics.yml"
CI = WORKFLOWS / "devctl-check.yml"
INSTALLED = ".github/workflows/rapid-ship-metrics.yml"
PIN = re.compile(r"uses: (?P<action>[\w./-]+)@(?P<sha>[0-9a-f]{40}) # (?P<version>v\d+\.\d+\.\d+)$")


def workflow() -> dict[Any, Any]:
    data = yaml.safe_load(TEMPLATE.read_text())
    assert isinstance(data, dict)
    return data


def pins(path: Path) -> dict[str, tuple[str, str]]:
    found = (PIN.search(line.strip()) for line in path.read_text().splitlines() if "uses:" in line)
    return {match["action"]: (match["sha"], match["version"]) for match in found if match}


def test_triggers_permissions_and_concurrency() -> None:
    data = workflow()
    job = data["jobs"]["metrics"]

    assert data["name"] == "rapid-ship metrics"
    assert data[True] == {"schedule": [{"cron": "41 5 * * *"}], "workflow_dispatch": None}
    assert data["permissions"] == {}
    assert job["name"] == "rapid-ship metrics"
    assert job["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
        "actions": "read",
        "deployments": "read",
        "issues": "write",
    }
    assert data["concurrency"] == {"group": "rapid-ship-metrics", "cancel-in-progress": False}
    assert list(data["jobs"]) == ["metrics"]


def test_checkout_has_full_history_without_credentials() -> None:
    steps = workflow()["jobs"]["metrics"]["steps"]

    assert steps[0]["with"] == {"persist-credentials": False, "fetch-depth": 0}
    assert steps[0]["uses"].startswith("actions/checkout@")
    assert steps[1] == {"uses": steps[1]["uses"]}
    assert steps[1]["uses"].startswith("astral-sh/setup-uv@")
    assert len(steps) == 3


def test_actions_are_pinned_like_the_ci_workflow() -> None:
    metrics, ci = pins(TEMPLATE), pins(CI)

    assert set(metrics) == {"actions/checkout", "astral-sh/setup-uv"}
    assert {action: ci[action] for action in metrics} == metrics
    assert len(metrics) == TEMPLATE.read_text().count("uses:")  # no action is pinned by tag alone


def test_it_runs_post_with_the_github_token_only() -> None:
    text = TEMPLATE.read_text()
    last = workflow()["jobs"]["metrics"]["steps"][-1]

    assert last == {
        "name": "Post the metrics report",
        "env": {"GH_TOKEN": "${{ github.token }}"},
        "run": "./devctl metrics --post",
    }
    assert text.count("${{") == 1
    assert "secrets" not in text


def test_the_vendored_copy_matches_its_template(
    git_repo: Path, commit_all: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(git_repo)
    assert main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0
    assert not (git_repo / INSTALLED).exists()
    assert INSTALLED not in {entry.path for entry in read_lock(git_repo).entries}

    settings = git_repo / ".rapid-ship/project.toml"
    settings.write_text(
        settings.read_text().replace("optional = []", f'optional = ["{INSTALLED}"]')
    )
    commit_all(git_repo, "Opt in")
    assert main(["sync", "--in-place"]) == 0

    assert (git_repo / INSTALLED).read_bytes() == TEMPLATE.read_bytes()
    assert {entry.path: entry.kind for entry in read_lock(git_repo).entries}[INSTALLED] == "managed"
