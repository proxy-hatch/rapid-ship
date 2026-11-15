"""Offline: ./devctl metrics through main() with a fake gh on PATH; simulated."""

import json
import os
import shutil
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

import pytest

from devctl.cli import main
from devctl.doctor_items import OwnerReadError
from devctl.ledger import LAST_PASS
from devctl.metrics.api import MetricContext, MetricResult
from devctl.metrics.command import build_report
from devctl.metrics.github import GitHubReader
from devctl.settings import load_project
from metrics_fakes import (
    ALLOWANCE,
    RESET,
    MergedHistory,
    Probe,
    block_gh,
    entry_text,
    fake_gh,
    report_json,
    served_project,
    use_metrics,
)

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
        '[[stack]]\nname = "python"\ndirectory = "."\n[github]\nrepository = "o/r"\n' + apps
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
        "repos/o/r",
        "rate_limit",
        "repos/o/r/pulls?state=closed&base=main&sort=updated&direction=desc&per_page=64&page=1",
        "repos/o/r/pulls?state=closed&sort=updated&direction=desc&per_page=64&page=1",
    ]
    paths.extend(
        f"repos/o/r/commits/{sha}/pulls?per_page=64&page=1"
        for sha in git(h.path, "rev-list", "HEAD").splitlines()
    )
    paths.extend(f"repos/o/r/issues/{pr['number']}/events?per_page=64&page=1" for pr in h.unmerged)
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
    assert [m["value"] for m in result["metrics"]] == [0, 0, 0, 0, 0]
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
    assert json.loads(capsys.readouterr().out)["metrics"][2]["status"] == "unknown"


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
        h.owner.serve("repos/o/r", {"error": "gh: Bad credentials (HTTP 401)"})
    elif failure == "origin":
        from github_fakes import git

        git(h.path, "update-ref", "-d", "refs/remotes/origin/main")
    elif failure == "repository":
        (h.path / ".rapid-ship/project.toml").write_text(
            '[[stack]]\nname = "python"\ndirectory = "."\n'
        )
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
        path = "repos/o/r"
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
    affected = result["metrics"] if phase != "metric" else result["metrics"][2:4]
    assert all(m["value"] is None and "it resets at 06:12 UTC" in m["reason"] for m in affected)
    if phase != "metric":
        assert result["window"] is None
        assert (result["default_branch"]["name"] is None) == (phase == "before")
        assert (result["default_branch"]["commit"] is None) == (phase == "before")
    else:
        assert result["metrics"][0]["value"] == 0
        assert result["metrics"][1]["value"] == 0
        assert [m["id"] for m in affected] == ["red_merges", "closed_unmerged"]
        assert result["metrics"][4]["id"] == "corrections"
        assert result["metrics"][4]["value"] == 0
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


def test_post_and_json_exclude_each_other(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["metrics", "--post", "--json"])
    assert caught.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err


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
    assert result["metrics"][2]["value"] is None
    assert result["metrics"][2]["items"] == []
    assert result["metrics"][2]["status"] == "unknown"


ALARMS = (
    "[thresholds]\nalarms = 0\nprobes = 5\n"
    '[[metric]]\nid = "alarms"\ntitle = "Alarms"\nsource = "issues"\nlabel = "alarm"\n'
)
ISSUES = "repos/o/r/issues?labels=alarm&state=all&sort=created&direction=desc&per_page=64&page=1"


def test_project_defined_metrics_follow_the_basic_ones_settings_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = served_project(tmp_path, ALARMS)
    opened = {
        "number": 4,
        "created_at": "2026-10-05T00:00:00Z",
        "html_url": "https://example.invalid/issues/4",
        "pull_request": None,
    }
    h.owner.serve(ISSUES, [opened])
    use_metrics(monkeypatch, Probe(lambda _: MetricResult(2)))
    metrics = report_json(h)["metrics"]
    assert [
        (m["id"], m["kind"], m["population"], m["value"], m["status"]) for m in metrics[5:]
    ] == [
        ("alarms", "count", "repository", 1, "breached"),
        ("probes", "count", "repository", 2, "ok"),
    ]
    assert metrics[5]["items"] == [
        {
            "label": "#4",
            "url": "https://example.invalid/issues/4",
            "time": "2026-10-05T00:00:00Z",
            "state": "counted",
        }
    ]


def test_a_breached_code_metric_exits_1_and_prints_its_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path)
    (h.path / ".rapid-ship/metrics.toml").write_text("window = 30\n[thresholds]\nprobes = 1\n")
    use_metrics(monkeypatch, Probe(lambda _: MetricResult(2)))
    assert cli(h, monkeypatch) == 1
    rows = [line.split() for line in capsys.readouterr().out.splitlines()]
    assert ["probes", "repository", "2", "<=", "1", "breached"] in rows


def test_a_settings_metric_may_not_reuse_a_code_metric_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    clash = '[[metric]]\nid = "probes"\ntitle = "Probes"\nsource = "issues"\nlabel = "x"\n'
    monkeypatch.chdir(served_project(tmp_path, clash).path)
    block_gh(tmp_path / "bin", monkeypatch)
    use_metrics(monkeypatch, Probe(lambda _: MetricResult(1)))
    assert main(["metrics"]) == 2
    assert 'id = "probes": devctl_project.metrics() already defines probes' in (
        capsys.readouterr().err
    )


def test_the_allowance_used_up_before_project_metrics_leaves_them_unknown_and_uninvoked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = served_project(tmp_path, ALARMS)
    runs = (
        f"repos/o/r/actions/workflows/devctl-check.yml/runs?head_sha={h.pulls[0]['merge_commit_sha']}"
        "&event=push&per_page=64&page=1"
    )
    h.owner.fail(runs, OwnerReadError(403, "API rate limit exceeded"))
    h.owner.serve("rate_limit", RESET)
    probe = Probe(lambda _: MetricResult(1))
    use_metrics(monkeypatch, probe)
    metrics = {m["id"]: m for m in report_json(h)["metrics"]}
    assert [(metrics[i]["value"], metrics[i]["reason"]) for i in ("alarms", "probes")] == [
        (None, ALLOWANCE)
    ] * 2
    assert probe.threads == []
    assert h.owner.paths[-2:] == [runs, "rate_limit"]


def test_an_empty_window_makes_project_metrics_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = served_project(tmp_path, ALARMS, prs=0)
    probe = Probe(lambda _: MetricResult(1))
    use_metrics(monkeypatch, probe)
    metrics = report_json(h)["metrics"]
    assert [(m["id"], m["value"], m["reason"]) for m in metrics[5:]] == [
        ("alarms", None, "no merged PRs yet"),
        ("probes", None, "no merged PRs yet"),
    ]
    assert probe.threads == []
    assert ISSUES not in h.owner.paths


def test_a_code_metric_gets_the_repository_the_span_and_the_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[MetricContext] = []

    def record(context: MetricContext) -> MetricResult:
        seen.append(context)
        return MetricResult(0)

    use_metrics(monkeypatch, Probe(record))
    report_json(served_project(tmp_path, prs=2))
    assert [(c.repository, c.since, c.until, c.prs) for c in seen] == [
        ("o/r", datetime(2026, 10, 1, 6, 12, tzinfo=UTC), NOW, (2, 1))
    ]


def back_out_the_first_pr(h: MergedHistory) -> str:
    """Add a commit that names the first PR's merge commit as git revert does, and publish it."""
    first = str(h.pulls[-1]["merge_commit_sha"])
    undo = h.push({"note.txt": "x\n"}, f"Back out PR 1\n\nThis reverts commit {first}.\n")
    h.publish()
    return undo


def test_reverts_run_between_revisions_and_red_merges_and_count_a_reverted_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, count=2)
    undo = back_out_the_first_pr(h)
    assert cli(h, monkeypatch, "--json") == 0
    result = json.loads(capsys.readouterr().out)
    assert [m["id"] for m in result["metrics"]] == [
        "revisions",
        "reverts",
        "red_merges",
        "closed_unmerged",
        "corrections",
    ]
    reverts = result["metrics"][1]
    assert (reverts["title"], reverts["population"], reverts["kind"]) == (
        "Reverts",
        "agent",
        "count",
    )
    assert reverts["value"] == 1
    assert reverts["items"] == [{"pr": 1, "state": "counted", "revert": "whole", "commit": undo}]


def test_a_reverted_pr_can_breach_its_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, count=2)
    (h.path / ".rapid-ship/metrics.toml").write_text("window = 30\n[thresholds]\nreverts = 0\n")
    back_out_the_first_pr(h)
    assert cli(h, monkeypatch) == 1
    lines = capsys.readouterr().out.splitlines()
    row = next(line for line in lines if line.startswith("reverts"))
    assert row.split() == ["reverts", "agent", "PRs", "1", "(#1)", "<=", "0", "breached"]


def test_without_agent_identity_reverts_count_every_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, identity=False, count=2)
    back_out_the_first_pr(h)
    assert cli(h, monkeypatch, "--json") == 0
    reverts = json.loads(capsys.readouterr().out)["metrics"][1]
    assert (reverts["population"], reverts["reason"], reverts["value"]) == ("all", None, 1)


def test_closed_unmerged_and_corrections_follow_red_merges_and_precede_project_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path)
    assert cli(h, monkeypatch, "--json") == 0
    metrics = json.loads(capsys.readouterr().out)["metrics"]
    assert [(m["id"], m["title"], m["kind"], m["population"]) for m in metrics] == [
        ("revisions", "Revisions", "count", "agent"),
        ("reverts", "Reverts", "count", "agent"),
        ("red_merges", "Red merges", "count", "agent"),
        ("closed_unmerged", "Closed unmerged", "count", "agent"),
        ("corrections", "Corrections", "count", "ledger"),
    ]
    assert cli(h, monkeypatch) == 0
    rows = capsys.readouterr().out.splitlines()[4:9]
    assert [row.split()[0] for row in rows] == [
        "revisions",
        "reverts",
        "red_merges",
        "closed_unmerged",
        "corrections",
    ]


def test_a_pr_a_person_closed_counts_and_one_an_app_closed_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, count=2)
    (h.path / ".rapid-ship/metrics.toml").write_text(
        "window = 30\n[thresholds]\nclosed_unmerged = 0\n"
    )
    h.close(7, closer="person")
    h.close(8, closer="o-reviewer[bot]")
    h.close(9, closer="o-worker[bot]")
    assert cli(h, monkeypatch, "--json") == 1
    closed = json.loads(capsys.readouterr().out)["metrics"][3]
    assert closed["value"] == 1
    assert closed["items"] == [{"pr": 7, "state": "counted"}]
    assert (closed["threshold"], closed["status"]) == (0, "breached")
    assert cli(h, monkeypatch) == 1
    row = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("closed_"))
    assert row.split() == ["closed_unmerged", "agent", "PRs", "1", "(#7)", "<=", "0", "breached"]


def test_without_agent_identity_closed_unmerged_counts_every_closed_pr_and_reads_no_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, identity=False, count=2)
    h.close(7, closer="person", author="someone")
    h.close(8, closer="o-worker[bot]")
    assert cli(h, monkeypatch, "--json") == 0
    closed = json.loads(capsys.readouterr().out)["metrics"][3]
    assert (closed["population"], closed["reason"], closed["value"]) == ("all", None, 2)
    log = [
        json.loads(line)["argv"][3]
        for line in (h.path.parent / "bin/gh.log").read_text().splitlines()
    ]
    assert not any("/events" in path for path in log)


def test_corrections_counts_the_ledger_at_the_tip_and_reads_no_github_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    h = setup(tmp_path, count=2)
    h.push(
        {
            "docs/corrections/2026-10-05-env-read-1.md": entry_text("2026-10-05", rungs="[1, 2]"),
            "docs/corrections/2026-10-06-env-read-2.md": entry_text("2026-10-06", rungs="[2]"),
        }
    )
    h.publish()
    assert cli(h, monkeypatch, "--json") == 0
    corrections = json.loads(capsys.readouterr().out)["metrics"][4]
    assert corrections["value"] == 2
    assert corrections["by_rung"] == {"1": 1, "2": 2, "3": 0, "4": 0}
    assert corrections["repeats"] == ["docs/corrections/2026-10-06-env-read-2.md"]
    assert corrections["not_gardened"] == [2, 1]
    log = [
        json.loads(line)["argv"][3]
        for line in (h.path.parent / "bin/gh.log").read_text().splitlines()
    ]
    assert not any("corrections" in path for path in log)
    assert cli(h, monkeypatch) == 0
    row = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("corr"))
    assert "2 (rung 1: 1, rung 2: 2), 1 repeat, 2 PRs not gardened" in row


@pytest.mark.parametrize(
    ("entries", "gardened", "status"),
    [(2, True, "ok"), (2, False, "unknown"), (3, False, "breached"), (3, True, "breached")],
)
def test_corrections_status_follows_the_ledger_rule(
    tmp_path: Path, entries: int, gardened: bool, status: str
) -> None:
    h = served_project(tmp_path, "[thresholds]\ncorrections = 2\n", prs=2)
    through = h.push(
        {
            f"docs/corrections/2026-10-05-cause-{n}-1.md": entry_text("2026-10-05", f"cause-{n}")
            for n in range(1, entries + 1)
        }
    )
    if gardened:
        h.push({LAST_PASS: f'through = "{through}"\ndate = 2026-10-16\n'})
    h.publish()
    corrections = {m["id"]: m for m in report_json(h)["metrics"]}["corrections"]
    assert (corrections["value"], corrections["threshold"], corrections["status"]) == (
        entries,
        2,
        status,
    )
    assert (corrections["not_gardened"] == []) == gardened
