"""Offline: doctor --skills with fake Harness executables on PATH and a scratch clone. No real
Harness runs, and no App token is minted."""

import json
from pathlib import Path

import pytest

from devctl.doctor import DoctorContext, Item, skills_items
from devctl.github.app import GitHubAccess
from devctl.harness import PROBE_MODEL, skills_args
from devctl.settings import ProjectSettings
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


def install_script(harness: FakeHarness, name: str, body: str) -> None:
    """A Harness executable of its own: body runs in the Session's working directory."""
    script = harness.directory / name
    script.write_text(f"#!/bin/sh\n{body}\n")
    script.chmod(0o755)


def worktrees(remote: Remote) -> list[str]:
    listing = git(remote.clone, "worktree", "list", "--porcelain")
    return [line for line in listing.splitlines() if line.startswith("worktree ")]


def test_claude_on_path_sees_the_skills_at_head(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", "billing-rules")
    fake_harness.install(
        "claude", stdout=claude_stream(["rs-tdd", "billing-rules", "my-notes", "tools:lint"])
    )
    [claude] = skills_items(doctor_ctx)
    assert (claude.name, claude.status) == ("skills (claude)", "ok")
    assert "outside the repository: my-notes, tools:lint" in claude.detail
    [args] = fake_harness.calls("claude")
    assert args == skills_args()
    assert args[args.index("--model") + 1] == PROBE_MODEL
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
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    [item] = skills_items(doctor_ctx)
    assert (item.status, item.detail) == ("ok", "1 repository skills seen")


def test_a_skill_the_session_cannot_see_is_missing(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", "billing-rules")
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    [claude] = skills_items(doctor_ctx)
    assert (claude.status, claude.detail) == ("missing", "missing: billing-rules")


def test_user_invoked_skills_are_not_checked(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd", user_invoked=("rs-setup",))
    # Claude Code may list a user-invoked skill anyway; it is still a repository skill.
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd", "rs-setup"]))
    [item] = skills_items(doctor_ctx)
    assert item.status == "ok"
    assert "not checked, user-invoked: rs-setup" in item.detail
    assert "outside the repository" not in item.detail


def test_codex_and_agy_on_path_are_not_probed(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    # doctor probes Claude Code alone until the Kit integrates another Harness (Spec 1 section 6).
    commit_skills(remote.clone, "rs-tdd")
    fake_harness.install("codex")
    fake_harness.install("agy")
    fake_harness.install("claude", stdout=claude_stream(["rs-tdd"]))
    assert [(i.name, i.status) for i in skills_items(doctor_ctx)] == [("skills (claude)", "ok")]
    assert fake_harness.calls("codex") == []
    assert fake_harness.calls("agy") == []


def test_with_no_harness_on_path_one_item_is_missing(
    doctor_ctx: DoctorContext, fake_harness: FakeHarness
) -> None:
    assert skills_items(doctor_ctx) == [
        Item("skills", "skills", "missing", "claude is not on PATH")
    ]


def test_without_claude_on_path_no_other_harness_is_probed(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    fake_harness.install("codex")
    fake_harness.install("agy")
    assert skills_items(doctor_ctx) == [
        Item("skills", "skills", "missing", "claude is not on PATH")
    ]
    assert fake_harness.calls("codex") == []
    assert fake_harness.calls("agy") == []
    assert len(worktrees(remote)) == 1


def test_a_harness_that_leaves_path_after_probing_is_missing_and_its_worktree_is_removed(
    doctor_ctx: DoctorContext,
    remote: Remote,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # probed_harnesses found claude on PATH, and it was gone when its Session was to start.
    monkeypatch.setattr(
        "devctl.doctor_skills.probed_harnesses", lambda project: {"claude": "skills (claude)"}
    )
    assert skills_items(doctor_ctx) == [
        Item("skills", "skills (claude)", "missing", "claude is not on PATH")
    ]
    assert len(worktrees(remote)) == 1


def test_the_worktree_is_removed_when_a_session_fails(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    fake_harness.install("claude", code=1)
    [item] = skills_items(doctor_ctx)
    assert (item.status, item.detail) == ("unknown", "claude exited 1 with no skill list")
    assert len(worktrees(remote)) == 1


def test_a_session_that_writes_files_and_locks_its_worktree_still_has_it_removed(
    doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
) -> None:
    commit_skills(remote.clone, "rs-tdd")
    reply = claude_stream(["rs-tdd"])
    install_script(
        fake_harness,
        "claude",
        f"echo scratch > scratch.txt\ngit worktree lock \"$(pwd)\"\nprintf '%s' '{reply}'",
    )
    [item] = skills_items(doctor_ctx)
    assert item.status == "ok"
    assert len(worktrees(remote)) == 1


def test_a_session_that_never_finishes_is_unknown_and_its_worktree_is_removed(
    doctor_ctx: DoctorContext,
    remote: Remote,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("devctl.doctor_skills.PROBE_TIMEOUT_SECONDS", 0.3)
    install_script(fake_harness, "claude", "sleep 30")
    [item] = skills_items(doctor_ctx)
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
    monkeypatch.setenv("ANTHROPIC_API_KEY", "example-value")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid:3128")
    monkeypatch.setenv("RAPID_SHIP_GIT_TOKEN", "example-value")
    monkeypatch.setenv("GIT_ASKPASS", "/nowhere/askpass")
    record = fake_harness.directory / "claude.env"
    reply = claude_stream(["rs-tdd"])
    install_script(fake_harness, "claude", f"env > \"{record}\"\nprintf '%s' '{reply}'")
    [item] = skills_items(doctor_ctx)
    assert item.status == "ok"
    environment = record.read_text().splitlines()
    assert "ANTHROPIC_API_KEY=example-value" in environment
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
    record = fake_harness.directory / "claude.env"
    reply = claude_stream(["rs-tdd"])
    install_script(fake_harness, "claude", f"env > \"{record}\"\nprintf '%s' '{reply}'")
    [item] = skills_items(doctor_ctx)
    assert item.status == "ok"
    assert github.calls == []
    environment = record.read_text()
    assert "GIT_ASKPASS" not in environment
    assert "RAPID_SHIP_GIT_TOKEN" not in environment
    assert files_containing(tmp_path, "ghs_") == []
