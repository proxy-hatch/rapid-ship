"""Offline: ./devctl metrics through main() with a fake gh on PATH; simulated."""

import json
import os
import shutil
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import pytest

from devctl.cli import main
from devctl.metrics.command import build_report
from devctl.metrics.github import GitHubReader
from devctl.settings import load_project
from metrics_fakes import MergedHistory, fake_gh

NOW = datetime(2026, 10, 16, tzinfo=UTC)


def setup(tmp_path: Path, *, identity: bool = True, count: int = 1) -> MergedHistory:
    h = MergedHistory(tmp_path / "repo")
    settings = h.path / ".rapid-ship"
    settings.mkdir()
    apps = (
        (
            'worker_app_id = 1\nworker_app_slug = "o-worker"\n'
            'reviewer_app_id = 2\nreviewer_app_slug = "o-reviewer"\n'
        )
        if identity
        else ""
    )
    (settings / "project.toml").write_text(
        'stack = "python"\n[github]\nrepository = "o/r"\n' + apps
    )
    (settings / "metrics.toml").write_text(
        "window = 30\n[thresholds]\nrevisions = 1.0\nred_merges = 0\n"
    )
    for n in range(1, count + 1):
        sha = h.merge(n, {})
        h.owner.serve(f"repos/o/r/pulls/{n}/reviews?per_page=64&page=1", [])
        h.owner.serve(
            f"repos/o/r/actions/workflows/devctl-check.yml/runs?head_sha={sha}&event=push&per_page=64&page=1",
            {
                "workflow_runs": [
                    {"id": n, "run_number": n, "run_attempt": 1, "conclusion": "success"}
                ]
            },
        )
    h.publish()
    return h


def responses(h: MergedHistory) -> dict[str, object]:
    from github_fakes import git

    paths = [
        "repos/o/r/",
        "rate_limit",
        "repos/o/r/pulls?state=closed&base=main&sort=updated&direction=desc&per_page=64&page=1",
    ]
    paths.extend(
        f"repos/o/r/commits/{sha}/pulls?per_page=64&page=1"
        for sha in git(h.path, "rev-list", "HEAD").splitlines()
    )
    for pr in h.pulls:
        paths.extend(
            [
                f"repos/o/r/pulls/{pr['number']}/reviews?per_page=64&page=1",
                f"repos/o/r/actions/workflows/devctl-check.yml/runs?head_sha={pr['merge_commit_sha']}"
                "&event=push&per_page=64&page=1",
            ]
        )
    from devctl.doctor_items import OwnerReadError

    result = {}
    for path in paths:
        with suppress(OwnerReadError):
            result[path] = h.owner(path)
    return result


def cli(h: MergedHistory, monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    fake_gh(h.path.parent / "bin", responses(h))
    monkeypatch.setenv("PATH", str(h.path.parent / "bin") + os.pathsep + os.environ["PATH"])
    monkeypatch.chdir(h.path)
    return main(["metrics", *args])


def test_no_breach_exits_0_and_a_breach_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path)
    assert cli(h, monkeypatch, "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert [m["value"] for m in result["metrics"]] == [0, 0]
    h.owner.serve(
        "repos/o/r/pulls/1/reviews?per_page=64&page=1",
        [
            {
                "state": "CHANGES_REQUESTED",
                "commit_id": "A",
                "submitted_at": "2026-10-01T00:00:00Z",
            },
            {
                "state": "CHANGES_REQUESTED",
                "commit_id": "B",
                "submitted_at": "2026-10-01T00:00:00Z",
            },
        ],
    )
    assert cli(h, monkeypatch) == 1
    assert "breached" in capsys.readouterr().out


def test_an_unknown_status_never_changes_the_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path)
    h.owner.serve(next(p for p in responses(h) if "/runs?" in p), {"workflow_runs": []})
    assert cli(h, monkeypatch, "--json") == 0
    assert json.loads(capsys.readouterr().out)["metrics"][1]["status"] == "unknown"


@pytest.mark.parametrize(
    ("failure", "fix"),
    [
        ("settings", "integer of at least 1"),
        ("missing_gh", "install gh"),
        ("401", "gh auth status"),
        ("origin", "git fetch origin"),
        ("repository", "owner/name"),
    ],
)
def test_each_failure_exits_2_and_names_its_fix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
    fix: str,
) -> None:
    h = setup(tmp_path, identity=False)
    if failure == "settings":
        (h.path / ".rapid-ship/metrics.toml").write_text("window = 0\nwrong = 1\n")
    elif failure == "401":
        h.owner.serve("repos/o/r/", {"error": "gh: Bad credentials (HTTP 401)"})
    elif failure == "origin":
        from github_fakes import git

        git(h.path, "update-ref", "-d", "refs/remotes/origin/main")
    elif failure == "repository":
        (h.path / ".rapid-ship/project.toml").write_text('stack = "python"\n')
    if failure == "missing_gh":
        bin_path = h.path.parent / "bin"
        bin_path.mkdir()
        git_path = shutil.which("git")
        assert git_path is not None
        (bin_path / "git").symlink_to(git_path)
        monkeypatch.chdir(h.path)
        monkeypatch.setenv("PATH", str(bin_path))
        code = main(["metrics"])
    else:
        code = cli(h, monkeypatch)
    assert code == 2
    error = capsys.readouterr().err
    assert error.startswith("devctl metrics: ")
    assert fix in error
    if failure == "settings":
        assert "wrong" in error


@pytest.mark.parametrize("phase", ["before", "walk", "metric"])
def test_allowance_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], phase: str
) -> None:
    h = setup(tmp_path)
    if phase == "before":
        path = "repos/o/r/"
    elif phase == "walk":
        for _ in range(8):
            h.push({})
        h.publish()
        paths = [p for p in responses(h) if "/commits/" in p]
        path = paths[5]
    else:
        path = next(p for p in responses(h) if "/runs?" in p)
    h.owner.serve(path, {"error": "gh: API rate limit exceeded for 192.0.2.1. (HTTP 403)"})
    h.owner.serve("rate_limit", {"resources": {"core": {"reset": 1791007920}}})
    assert cli(h, monkeypatch, "--json") == 0
    result = json.loads(capsys.readouterr().out)
    affected = result["metrics"] if phase != "metric" else result["metrics"][1:]
    assert all(m["value"] is None and "it resets at 06:12 UTC" in m["reason"] for m in affected)
    if phase != "metric":
        assert result["window"] is None
        assert (result["default_branch"]["name"] is None) == (phase == "before")
        assert (result["default_branch"]["commit"] is None) == (phase == "before")
    else:
        assert result["metrics"][0]["value"] == 0
    log = [
        json.loads(line)["argv"][3]
        for line in (h.path.parent / "bin/gh.log").read_text().splitlines()
    ]
    assert log[-2:] == [path, "rate_limit"]


@pytest.mark.parametrize("identity", [True, False])
def test_an_empty_window_makes_every_metric_unknown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    identity: bool,
) -> None:
    h = setup(tmp_path, identity=identity, count=0)
    assert cli(h, monkeypatch, "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["window"]["prs"] == 0
    assert result["window"]["since"] is None
    reason = "no merged agent PRs yet" if identity else "no merged PRs yet"
    assert all(m["value"] is None and m["reason"] == reason for m in result["metrics"])


def test_without_agent_identity_revisions_needs_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, identity=False)
    assert cli(h, monkeypatch, "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["window"]["population"] == "all"
    assert result["metrics"][0]["reason"] == "needs Agent identity"
    assert result["metrics"][0]["status"] == "needs Agent identity"


def test_window_overrides_the_setting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, count=2)
    assert cli(h, monkeypatch, "--window", "1", "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["window"]["size"] == result["window"]["prs"] == 1


@pytest.mark.parametrize("value", ["0", "-1", "x"])
def test_window_below_1_is_a_usage_error(value: str) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["metrics", "--window", value])
    assert caught.value.code == 2


def test_the_gate_note_and_the_not_fetched_note_are_printed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path)
    (h.path / ".rapid-ship/gate.toml").write_text("")
    h.merge(2, {})
    assert cli(h, monkeypatch) == 0
    text = capsys.readouterr().out
    assert "devctl no longer reads it" in text
    assert "1 merged PRs are not in origin/main yet: run git fetch origin and rerun" in text


def test_every_gh_call_is_a_get(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    h = setup(tmp_path)
    assert cli(h, monkeypatch) == 0
    calls = [
        json.loads(line)["argv"] for line in (h.path.parent / "bin/gh.log").read_text().splitlines()
    ]
    assert calls
    assert all(call[:3] == ["api", "--method", "GET"] for call in calls)


def test_builder_uses_the_supplied_project_and_reader(tmp_path: Path) -> None:
    h = setup(tmp_path)
    # RecordedOwner supplies projected lists, while the CLI fake projects workflow objects.
    key = next(p for p in responses(h) if "/runs?" in p)
    h.owner.serve(key, [])
    result = build_report(
        h.path, load_project(h.path), 1, GitHubReader("o/r", h.owner), lambda: NOW
    )
    assert result.generated_at == NOW
    assert result.repository == "o/r"
    assert result.window is not None
    assert result.window.size == 1


def test_window_has_no_upper_limit_and_absent_thresholds_have_no_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path)
    (h.path / ".rapid-ship/metrics.toml").write_text("window = 1\n")
    assert cli(h, monkeypatch, "--window", "1000000", "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["window"]["size"] == 1000000
    assert all(m["status"] is None and m["threshold"] is None for m in result["metrics"])


def test_a_partial_red_count_is_unknown_and_a_finished_breach_still_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, count=2)
    h.owner.serve(
        "repos/o/r/pulls/1/reviews?per_page=64&page=1",
        [
            {
                "state": "CHANGES_REQUESTED",
                "commit_id": head,
                "submitted_at": "2026-10-01T00:00:00Z",
            }
            for head in ("A", "B", "C")
        ],
    )
    runs = [p for p in responses(h) if "/runs?" in p]
    h.owner.serve(
        runs[0],
        {"workflow_runs": [{"id": 2, "run_number": 2, "run_attempt": 1, "conclusion": "failure"}]},
    )
    h.owner.serve(runs[1], {"error": "gh: API rate limit exceeded (HTTP 403)"})
    h.owner.serve("rate_limit", {"resources": {"core": {"reset": 1791007920}}})
    assert cli(h, monkeypatch, "--json") == 1
    result = json.loads(capsys.readouterr().out)
    assert result["metrics"][0]["value"] == 1.5
    assert result["metrics"][0]["status"] == "breached"
    assert result["metrics"][1]["value"] is None
    assert result["metrics"][1]["items"] == []
    assert result["metrics"][1]["status"] == "unknown"
