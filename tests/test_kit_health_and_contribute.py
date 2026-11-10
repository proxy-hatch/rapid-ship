"""Offline: rs-health references and commands, and rs-contribute opt-in, in scratch repositories."""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

from devctl.check.map_skills import skill_errors
from devctl.check.tracked import TrackedFiles
from devctl.hook import decide
from devctl.hook_protocols import HookSettings, ToolCall
from devctl.merge_guard import LocalBranches
from devctl.repo import Repo
from devctl.settings import load_project
from rapid_ship.cli import main
from rapid_ship.kit.lock import read_lock

SKILLS = Path(__file__).resolve().parents[1] / "rapid_ship/templates/common/.agents/skills"


def test_the_shared_audit_and_proposed_task_references_resolve() -> None:
    root = SKILLS / "rs-health"
    skill = (root / "SKILL.md").read_text()
    for name in ("audit.md", "proposed-task.md"):
        assert (root / "references" / name).is_file()
        assert f"references/{name}" in skill


def test_rs_health_runs_no_command_the_guardrails_deny(tmp_path: Path) -> None:
    root = SKILLS / "rs-health"
    commands: list[str] = []
    for path in root.rglob("*.md"):
        for block in re.findall(r"```sh\n(.*?)```", path.read_text(), re.S):
            block = re.sub(r"\\\n", " ", block)
            commands.extend(
                line.strip()
                for line in block.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            )
    settings = HookSettings(True, (), "o/r")
    for command in commands:
        assert decide(
            ToolCall(command, (), tmp_path),
            tmp_path,
            settings,
            lambda: LocalBranches(frozenset({"main"}), "feature"),
        ) == (None, "")
    assert len(commands) >= 5
    assert any("./devctl as worker gh issue create" in command for command in commands)


def test_rs_health_reports_an_unread_source_as_unknown() -> None:
    text = (SKILLS / "rs-health/SKILL.md").read_text().lower()
    for phrase in (
        "failed or blocked",
        "unknown",
        "never zero",
        "each unread source",
        "no task",
        "authentication",
        "gitleaks",
        "no merged prs",
        "empty successful",
    ):
        assert phrase in text


def test_rs_contribute_installs_only_when_opted_in(
    git_repo: Path, commit_all: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(git_repo)
    assert main(["init", "--stack", "agnostic", "--owner", "octo"]) == 0
    assert not (git_repo / ".agents/skills/rs-contribute").exists()
    settings_path = git_repo / ".rapid-ship/project.toml"
    settings_path.write_text(
        settings_path.read_text().replace("optional = []", 'optional = ["rs-contribute"]')
    )
    commit_all(git_repo, "Opt in")
    assert main(["sync", "--in-place"]) == 0
    assert (git_repo / ".agents/skills/rs-contribute/SKILL.md").is_file()
    assert (git_repo / ".claude/skills/rs-contribute").readlink() == Path(
        "../../.agents/skills/rs-contribute"
    )
    lock = read_lock(git_repo)
    entries = {entry.path: entry.kind for entry in lock.entries}
    assert entries[".agents/skills/rs-contribute/SKILL.md"] == "managed"
    assert entries[".claude/skills/rs-contribute"] == "managed"
    project = load_project(git_repo)
    assert project.optional_skills == ("rs-contribute",)
    commit_all(git_repo, "Install optional skill")
    assert skill_errors(TrackedFiles.read(Repo.discover(git_repo))) == []


def test_rs_contribute_hands_the_owner_its_writes(tmp_path: Path) -> None:
    text = (SKILLS / "rs-contribute/SKILL.md").read_text()
    for phrase in (
        "gh repo fork proxy-hatch/rapid-ship --clone=false",
        "gh search issues",
        "gh search prs",
        "--repo proxy-hatch/rapid-ship --state open",
        "rapid-ship sync --revert",
        "rapid_ship/templates/AGENTS.md",
        "Owner terminal commands",
    ):
        assert phrase in text
    settings = HookSettings(True, (), "proxy-hatch/rapid-ship")
    for command in ("git push", "gh pr create --repo proxy-hatch/rapid-ship"):
        assert command in text
        assert (
            decide(
                ToolCall(command, (), tmp_path),
                tmp_path,
                settings,
                lambda: LocalBranches(frozenset({"main"}), "feature"),
            )[0]
            == "deny"
        )


def test_shared_audit_covers_golden_path_drift() -> None:
    audit = (SKILLS / "rs-health/references/audit.md").read_text().lower()
    assert "docs/golden-paths/" in audit
    assert "merged code" in audit
    assert "golden path" in audit
