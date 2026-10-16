"""Offline: doctor's local items with recorded command output and a fake agy on PATH. No real
Harness, gh, gitleaks or GitHub is run."""

import argparse
import dataclasses
from pathlib import Path

import pytest

from devctl import doctor
from devctl.check.stacks.agnostic import GITLEAKS_VERSION
from devctl.doctor import (
    AGY_PROBE_ARGS,
    DoctorContext,
    Item,
    agy_sign_in,
    claude_item,
    codex_item,
    doctor_command,
    doctor_exit_code,
    git_item,
    local_items,
)
from devctl.harness import PROBE_MODELS
from devctl.process import ProcessResult
from github_fakes import FakeHarness, FakeRun, MakeContext, RepoFiles

# Observed on 2026-10-13 (Checked facts): Google's eligibility check failed, not the sign-in.
SERVICE_503 = (
    "error: failed to send message: send failed; already reported to the user: Eligibility check "
    "failed: failed to get load code assist response: UNAVAILABLE (code 503): The service is "
    "currently unavailable.\n"
)
SERVICE_502 = (
    "error: Eligibility check failed: failed to get load code assist response: request failed "
    '(code 502): HTML response "Error 502 (Server Error)!!1"\n'
)


def result(code: int, out: str = "", err: str = "") -> ProcessResult:
    return ProcessResult(["x"], code, out, err, 0.0)


@pytest.mark.parametrize(
    ("output", "status"),
    [
        (result(0, '{"loggedIn": true, "authMethod": "claude.ai"}'), "ok"),
        (result(1, '{"loggedIn": false}'), "missing"),
        (result(0, '{"loggedIn": true, "authMethod": "console"}'), "ok"),
        (result(0, '{"loggedIn": false}'), "unknown"),  # exit code and flag disagree
        (result(0, "not json"), "unknown"),
    ],
)
def test_claude_sign_in(output: ProcessResult, status: str) -> None:
    assert claude_item("worker", output).status == status


@pytest.mark.parametrize(
    ("output", "status"),
    [
        (result(0, err="Logged in using ChatGPT\n"), "ok"),
        (result(1, err="Not logged in\n"), "missing"),
        (result(0, err="Logged in using an API key - sk-proj-***ABCD\n"), "ok"),
        (result(0, err="Logged in using access token\n"), "ok"),
        (result(0, err="Something else\n"), "unknown"),
    ],
)
def test_codex_sign_in_never_echoes_the_cli(output: ProcessResult, status: str) -> None:
    item = codex_item("reviewer", output)
    assert item.status == status
    assert "ABCD" not in item.detail


def test_agy_reply_means_signed_in(fake_harness: FakeHarness) -> None:
    fake_harness.install("agy", stdout="Hello! How can I help?\n")
    item = agy_sign_in("worker")
    assert (item.name, item.status) == ("worker sign-in (agy)", "ok")
    assert fake_harness.calls("agy") == [list(AGY_PROBE_ARGS)]
    assert PROBE_MODELS["agy"] in AGY_PROBE_ARGS
    assert "Hello" not in item.detail


@pytest.mark.parametrize(("code", "stderr"), [(0, ""), (1, "error: example failure\n")])
def test_agy_without_a_reply_is_missing(fake_harness: FakeHarness, code: int, stderr: str) -> None:
    # Exit code 0 alone proves nothing (Checked facts).
    fake_harness.install("agy", stderr=stderr, code=code)
    assert agy_sign_in("worker").status == "missing"


@pytest.mark.parametrize("stderr", [SERVICE_503, SERVICE_502])
def test_agy_eligibility_errors_are_unknown_with_the_error(
    fake_harness: FakeHarness, stderr: str
) -> None:
    fake_harness.install("agy", stderr=stderr, code=1)
    item = agy_sign_in("worker")
    assert item.status == "unknown"
    assert "Eligibility check failed" in item.detail


def test_agy_is_probed_inside_another_coding_session(
    fake_harness: FakeHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    # doctor probes agy wherever it runs; rs-setup warns before it runs doctor inside
    # another Harness's Session (Spec 1 section 8, step 13).
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("CODEX_THREAD_ID", "t-1")
    fake_harness.install("agy", stdout="Hello!\n")
    assert agy_sign_in("worker").status == "ok"
    assert fake_harness.calls("agy") == [list(AGY_PROBE_ARGS)]


@pytest.mark.usefixtures("fake_harness")
def test_missing_agy_is_missing() -> None:
    assert agy_sign_in("reviewer").status == "missing"


def test_local_items_run_the_agy_probe(ctx: MakeContext, fake_run: FakeRun) -> None:
    fake_run.answer(["agy", *AGY_PROBE_ARGS], result(0, "Hello!\n"))
    items = {i.name: i for i in local_items(ctx(worker=("agy", "gemini-3.8-flash-high")))}
    assert items["worker sign-in (agy)"].status == "ok"


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
    assert doctor_command(argparse.Namespace(skills=False)) == 1
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
        assert doctor.doctor_command(argparse.Namespace(skills=False)) == 0
    [with_apps, without_apps] = contexts
    assert with_apps.access is not None
    assert with_apps.access.repository == "o/r"
    assert without_apps.access is None
