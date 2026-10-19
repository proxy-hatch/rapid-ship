"""Offline: doctor --skills with fake Harness executables on PATH and a scratch clone. No real
Harness runs, and no App token is minted."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from devctl.doctor import DoctorContext, Item, skills_items
from devctl.github.app import GitHubAccess
from devctl.harness import PROBE_MODELS
from devctl.settings import Agent, ProjectSettings, Role
from github_fakes import FakeGitHub, FakeHarness, Remote, files_containing, git
from github_fixtures import no_owner_reads


@pytest.fixture
def doctor_ctx(remote: Remote, project: ProjectSettings, access: GitHubAccess) -> DoctorContext:
    """The clone with Agent identity on, so a test can show --skills mints no token anyway."""
    return DoctorContext(remote.clone, project, no_owner_reads, access)


def commit_skills(clone: Path, *names: str, user_invoked: tuple[str, ...] = ()) -> None:
    for name in (*names, *user_invoked):
        flag = "disable-model-invocation: true\n" if name in user_invoked else ""
        skill = clone / ".agents" / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: The {name} skill.\n{flag}---\n"
        )
    git(clone, "add", ".agents")
    git(clone, "commit", "-q", "-m", "add skills")


def claude_stream(skills: list[str]) -> str:
    init = {"type": "system", "subtype": "init", "session_id": "s-1", "skills": skills}
    done = {"type": "result", "subtype": "success", "is_error": False, "result": "\n".join(skills)}
    return f"{json.dumps(init)}\n{json.dumps(done)}\n"


def agy_skills(names: list[str]) -> str:
    return json.dumps([{"name": name, "builtin": False} for name in names])


def install_script(harness: FakeHarness, name: str, body: str) -> None:
    """A Harness executable of its own: body runs in the Session's working directory."""
    script = harness.directory / name
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(0o755)


def worktrees(remote: Remote) -> list[str]:
    listing = git(remote.clone, "worktree", "list", "--porcelain")
    return [line for line in listing.splitlines() if line.startswith("worktree ")]


def by_name(items: list[Item]) -> dict[str, Item]:
    return {item.name: item for item in items}


def test_each_roster_harness_sees_the_skills_at_head(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", "billing-rules")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd", "billing-rules"]))
    fake_harness.install(
        "claude", stdout=claude_stream(["rs-tdd", "billing-rules", "my-notes", "tools:lint"])
    )
    items = by_name(skills_items(doctor_ctx))
    assert items["worker skills (agy)"].status == "ok"
    reviewer = items["reviewer skills (claude)"]
    assert reviewer.status == "ok"
    assert "outside the repository: my-notes, tools:lint" in reviewer.detail
    [args] = fake_harness.calls("claude")
    assert args[args.index("--model") + 1] == PROBE_MODELS["claude"]
    [cwd] = fake_harness.cwds("claude")
    assert not cwd.is_relative_to(remote.clone.resolve())
    assert not cwd.exists()
    assert len(worktrees(remote)) == 1


def test_an_uncommitted_skill_is_not_compared(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    draft = remote.clone / ".agents" / "skills" / "draft"
    draft.mkdir()
    (draft / "SKILL.md").write_text("---\nname: draft\ndescription: Not committed.\n---\n")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd"]))
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    for item in skills_items(doctor_ctx):
        assert (item.status, item.detail) == ("ok", "1 repository skills seen")


def test_a_skill_the_session_cannot_see_is_missing(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", "billing-rules")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd", "billing-rules"]))
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    reviewer = by_name(skills_items(doctor_ctx))["reviewer skills (claude)"]
    assert (reviewer.status, reviewer.detail) == ("missing", "missing: billing-rules")


def test_codex_lists_skills_one_name_per_line(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    events = [
        {"type": "thread.started", "thread_id": "t-1"},
        {
            "type": "item.completed",
            "item": {"id": "item_0", "type": "agent_message", "text": "- rs-tdd\nreview-notes\n"},
        },
        {"type": "turn.completed", "usage": {}},
    ]
    fake_harness.install("codex", stdout="".join(f"{json.dumps(event)}\n" for event in events))
    roster: dict[Role, Agent] = {
        "worker": Agent("codex", "gpt-6.1-sol"),
        "reviewer": Agent("codex", "gpt-6-astra"),
    }
    codex = replace(doctor_ctx, project=replace(doctor_ctx.project, roster=roster))
    [item] = skills_items(codex)
    assert (item.name, item.status) == ("worker and reviewer skills (codex)", "ok")
    assert "outside the repository: review-notes" in item.detail
    [args] = fake_harness.calls("codex")
    assert args[:2] == ["exec", "--json"]
    assert args[args.index("--model") + 1] == PROBE_MODELS["codex"]
    assert args[args.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in args


def test_user_invoked_skills_are_not_checked(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", user_invoked=("rs-setup",))
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd"]))
    # A Harness may list a user-invoked skill anyway; it is still a repository skill.
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd", "rs-setup"]))
    for item in skills_items(doctor_ctx):
        assert item.status == "ok"
        assert "not checked, user-invoked: rs-setup" in item.detail
        assert "outside the repository" not in item.detail


def test_without_a_roster_each_supported_harness_on_path_is_probed(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    fake_harness.install("agy", stdout=agy_skills(["rs-tdd"]))
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    no_roster = replace(doctor_ctx, project=replace(doctor_ctx.project, roster={}))
    items = skills_items(no_roster)
    assert [(i.name, i.status) for i in items] == [
        ("skills (claude)", "ok"),
        ("skills (agy)", "ok"),
    ]
    assert fake_harness.calls("codex") == []


def test_without_a_roster_or_a_harness_on_path_one_item_is_missing(
    doctor_ctx: DoctorContext, fake_harness: FakeHarness
) -> None:
    no_roster = replace(doctor_ctx, project=replace(doctor_ctx.project, roster={}))
    assert skills_items(no_roster) == [
        Item(
            "skills",
            "skills",
            "missing",
            ".rapid-ship/project.toml has no Roster, and none of claude, codex or agy is on PATH",
        )
    ]


def test_a_roster_harness_not_on_path_is_missing_and_gets_no_worktree(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    items = by_name(skills_items(doctor_ctx))
    assert items["worker skills (agy)"] == Item(
        "skills", "worker skills (agy)", "missing", "agy is not on PATH"
    )
    assert items["reviewer skills (claude)"].status == "ok"
    assert len(worktrees(remote)) == 1


def test_the_worktree_is_removed_when_a_session_fails(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    fake_harness.install(
        "agy",
        code=1,
        stderr="error: Eligibility check failed: UNAVAILABLE (code 503): "
        "The service is currently unavailable.\n",
    )
    fake_harness.install("claude", code=1)
    items = by_name(skills_items(doctor_ctx))
    assert items["worker skills (agy)"].status == "unknown"
    assert "code 503" in items["worker skills (agy)"].detail
    assert items["reviewer skills (claude)"].status == "unknown"
    assert len(worktrees(remote)) == 1


def test_a_session_that_writes_files_and_locks_its_worktree_still_has_it_removed(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    reply = agy_skills(["rs-tdd"])
    install_script(
        fake_harness,
        "agy",
        f"echo scratch > scratch.txt\ngit worktree lock \"$(pwd)\"\necho '{reply}'",
    )
    solo = replace(doctor_ctx.project, roster={"worker": Agent("agy", "m")})
    [item] = skills_items(replace(doctor_ctx, project=solo))
    assert item.status == "ok"
    assert len(worktrees(remote)) == 1


def test_a_session_that_never_finishes_is_unknown_and_its_worktree_is_removed(
    doctor_ctx: DoctorContext,
    remote: Remote,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("devctl.doctor_skills.PROBE_TIMEOUT_SECONDS", 0.3)
    install_script(fake_harness, "agy", "sleep 30")
    solo = replace(doctor_ctx.project, roster={"worker": Agent("agy", "m")})
    [item] = skills_items(replace(doctor_ctx, project=solo))
    assert item.status == "unknown"
    assert "did not finish" in item.detail
    assert len(worktrees(remote)) == 1


def test_a_session_gets_its_harness_sign_in_and_no_devctl_as_variable(
    doctor_ctx: DoctorContext,
    remote: Remote,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Any sign-in method is ok (Spec 1 section 6), so one the owner's shell exports reaches the
    # Session; devctl as's variables never do.
    commit_skills(remote.clone, "rs-tdd")
    monkeypatch.setenv("GEMINI_API_KEY", "example-value")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("RAPID_SHIP_GIT_TOKEN", "example-value")
    monkeypatch.setenv("GIT_ASKPASS", "/nowhere/askpass")
    record = fake_harness.directory / "agy.env"
    install_script(fake_harness, "agy", f"env > \"{record}\"\necho '{agy_skills(['rs-tdd'])}'")
    solo = replace(doctor_ctx.project, roster={"worker": Agent("agy", "m")})
    [item] = skills_items(replace(doctor_ctx, project=solo))
    assert item.status == "ok"
    environment = record.read_text().splitlines()
    assert "GEMINI_API_KEY=example-value" in environment
    assert "HTTPS_PROXY=http://proxy.invalid:3128" in environment
    passed = [
        line for line in environment if line.startswith(("RAPID_SHIP_GIT_TOKEN=", "GIT_ASKPASS="))
    ]
    assert passed == []


def test_no_token_is_minted_and_the_session_sees_none(
    doctor_ctx: DoctorContext,
    github: FakeGitHub,
    remote: Remote,
    fake_harness: FakeHarness,
    tmp_path: Path,
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    record = fake_harness.directory / "agy.env"
    install_script(fake_harness, "agy", f"env > \"{record}\"\necho '{agy_skills(['rs-tdd'])}'")
    solo = replace(doctor_ctx.project, roster={"worker": Agent("agy", "m")})
    [item] = skills_items(replace(doctor_ctx, project=solo))
    assert item.status == "ok"
    assert github.calls == []
    environment = record.read_text()
    assert "GIT_ASKPASS" not in environment
    assert "RAPID_SHIP_GIT_TOKEN" not in environment
    assert files_containing(tmp_path, "ghs_") == []
