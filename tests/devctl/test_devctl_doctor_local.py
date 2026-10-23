"""Offline: doctor's local items with recorded command output. No real Harness, gh, gitleaks or
GitHub is run."""

import argparse
import dataclasses
from pathlib import Path

import pytest

from devctl import doctor
from devctl.check.stacks.agnostic import GITLEAKS_VERSION
from devctl.doctor import (
    DoctorContext,
    Item,
    doctor_command,
    doctor_exit_code,
    git_item,
    local_items,
)
from devctl.process import ProcessResult
from github_fakes import FakeRun, MakeContext, RepoFiles


def result(code: int, out: str = "", err: str = "") -> ProcessResult:
    return ProcessResult(["x"], code, out, err, 0.0)


def test_hooks_ci_workflow_and_kit(
    ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
) -> None:
    repo_files.workflow(job_name="devctl check")
    repo_files.lock(unchanged=["devctl"], missing=["tools/devctl/devctl/cli.py"])
    fake_run.answer(["git", "config", "--get", "core.hooksPath"], result(0, ".githooks\n"))
    items = {i.name: i for i in local_items(ctx())}
    assert items["core.hooksPath"].status == "ok"
    assert items["CI workflow"].status == "ok"
    assert items["Kit files"].status == "missing"
    assert "tools/devctl/devctl/cli.py" in items["Kit files"].detail
    assert (
        "uvx --from git+https://github.com/proxy-hatch/rapid-ship@v0.2.0 rapid-ship status"
        in items["Kit files"].detail
    )
    assert "Linear team and project IDs" not in items  # devctl never talks to the tracker


@pytest.mark.usefixtures("fake_run")
def test_excluded_kit_files_are_counted_not_missing(
    ctx: MakeContext, repo_files: RepoFiles
) -> None:
    # The lock records no exclusion; [kit] exclude in project.toml does. Excluding the rs-tdd skill
    # directory covers its edited SKILL.md and its absent .claude/skills link.
    repo_files.write(
        ".agents/skills/rs-tdd/SKILL.md", "---\nname: rs-tdd\ndescription: ours\n---\n"
    )
    repo_files.lock(
        unchanged=["devctl"],
        missing=[],
        stale=[".agents/skills/rs-tdd/SKILL.md", ".claude/skills/rs-tdd"],
    )
    included = {i.name: i for i in local_items(ctx())}["Kit files"]
    assert included.status == "missing"
    assert ".claude/skills/rs-tdd" in included.detail
    kit = {i.name: i for i in local_items(ctx(excluded=(".agents/skills/rs-tdd",)))}["Kit files"]
    assert kit.status == "ok"
    assert "Kit 0.2.0: 1 unchanged, 0 modified, 2 excluded" in kit.detail


def test_gitleaks_must_be_the_pinned_version(ctx: MakeContext, fake_run: FakeRun) -> None:
    fake_run.answer(["gitleaks", "version"], result(0, f"{GITLEAKS_VERSION}\n"))
    assert {i.name: i for i in local_items(ctx())}["gitleaks"].status == "ok"
    fake_run.answer(["gitleaks", "version"], result(0, "v8.18.4\n"))
    older = {i.name: i for i in local_items(ctx())}["gitleaks"]
    assert older.status == "missing"
    assert GITLEAKS_VERSION in older.detail
    fake_run.answer(["gitleaks", "version"], result(1))
    assert {i.name: i for i in local_items(ctx())}["gitleaks"].status == "unknown"


@pytest.mark.parametrize(
    ("output", "status"),
    [
        (result(0, "git version 2.39.5 (Apple Git-154)\n"), "ok"),
        (result(0, "git version 2.31.0\n"), "ok"),
        (result(0, "git version 2.30.9\n"), "missing"),
        (result(0, "not git\n"), "unknown"),
        (result(1), "unknown"),
    ],
)
def test_git_must_be_2_31_or_later(fake_run: FakeRun, output: ProcessResult, status: str) -> None:
    fake_run.answer(["git", "--version"], output)
    item = git_item()
    assert (item.area, item.name, item.status) == ("toolchain", "git", status)
    if status == "missing":
        assert "older than 2.31" in item.detail


def test_old_git_stops_doctor_before_it_reads_the_repository(
    fake_run: FakeRun,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)  # not a work tree: reading it would raise RepoError
    fake_run.answer(["git", "--version"], result(0, "git version 2.30.9\n"))
    assert doctor_command(argparse.Namespace(skills=False, settings=False)) == 1
    out = capsys.readouterr().out
    assert "missing  toolchain  git: git 2.30.9 is older than 2.31" in out


@pytest.mark.usefixtures("fake_run")
def test_tools_devctl_exclusions(ctx: MakeContext, repo_files: RepoFiles) -> None:
    pyproject = '[tool.mypy]\nfiles = ["."]\n\n[tool.uv.workspace]\nmembers = ["tools/*"]\n'
    repo_files.write("pyproject.toml", pyproject)
    item = {i.name: i for i in local_items(ctx())}["tools/devctl exclusions"]
    assert item.status == "missing"
    assert all(f"{tool}:" in item.detail for tool in ("ruff", "mypy", "pytest", "uv"))
    repo_files.write(
        "rapid_ship/templates/kit.toml", ""
    )  # the Kit's own source checks tools/devctl
    item = {i.name: i for i in local_items(ctx())}["tools/devctl exclusions"]
    assert item.status == "missing"
    assert "uv:" in item.detail
    assert "ruff:" not in item.detail


def test_exit_code_prefers_unknown_then_missing() -> None:
    ok, missing, unknown = (
        Item("a", "n", "ok", ""),
        Item("a", "n", "missing", ""),
        Item("a", "n", "unknown", ""),
    )
    assert doctor_exit_code([ok]) == 0
    assert doctor_exit_code([ok, missing]) == 1
    assert doctor_exit_code([missing, unknown]) == 2


def test_doctor_reads_the_apps_only_with_agent_identity_on(
    ctx: MakeContext, fake_run: FakeRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    contexts: list[DoctorContext] = []

    def record(context: DoctorContext, *, skills: bool = False) -> int:
        contexts.append(context)
        return 0

    on = ctx().project
    off = dataclasses.replace(on, worker_app=None, reviewer_app=None)
    fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
    monkeypatch.chdir(ctx().root)
    monkeypatch.setattr(doctor, "run_doctor", record)
    for settings in (on, off):
        monkeypatch.setattr(doctor, "load_project", lambda root, found=settings: found)
        assert doctor.doctor_command(argparse.Namespace(skills=False, settings=False)) == 0
    [with_apps, without_apps] = contexts
    assert with_apps.access is not None
    assert with_apps.access.repository == "o/r"
    assert without_apps.access is None
