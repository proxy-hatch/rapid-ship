"""Offline: the edges of doctor's local items, its output and its command line. Command output is
recorded (FakeRun); no real Harness, gh, gitleaks or GitHub is run, and no Session starts."""

import argparse
import dataclasses
import re
import shutil
from pathlib import Path
from typing import Any, cast

import pytest

from devctl import cli, doctor
from devctl.check.stacks.agnostic import GITLEAKS_VERSION
from devctl.doctor import (
    KIT_SOURCE,
    DoctorContext,
    Item,
    OwnerReadError,
    doctor_command,
    doctor_exit_code,
    gh_get,
    git_item,
    local_items,
    run_doctor,
)
from devctl.doctor_local import gitleaks_item
from devctl.process import MAX_OUTPUT_BYTES, ProcessResult
from github_fakes import FakeRun, MakeContext, RepoFiles
from rapid_ship.kit.templates import render_files

GH_GET = ["gh", "api", "--method", "GET", "repos/o/r"]


def result(
    code: int,
    out: str = "",
    err: str = "",
    *,
    timed_out: bool = False,
    stdout_truncated: bool = False,
    stderr_truncated: bool = False,
) -> ProcessResult:
    return ProcessResult(["x"], code, out, err, 0.0, timed_out, stdout_truncated, stderr_truncated)


def by_name(items: list[Item]) -> dict[str, Item]:
    return {item.name: item for item in items}


def adjusted(context: DoctorContext, **changes: object) -> DoctorContext:
    project = dataclasses.replace(context.project, **cast("dict[str, Any]", changes))
    return dataclasses.replace(context, project=project)


def seeded_pyproject_text() -> str:
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    [template] = [t for t in render_files("python", variables, ()) if t.path == "pyproject.toml"]
    assert template.content is not None
    return template.content.decode()


class TestToolchain:
    def test_a_missing_tool_is_missing_and_nothing_runs(
        self, ctx: MakeContext, fake_run: FakeRun, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)
        items = by_name(local_items(ctx()))
        assert {n: items[n].status for n in ("git", "uv", "gh", "gh sign-in", "gitleaks")} == {
            "git": "missing",
            "uv": "missing",
            "gh": "missing",
            "gh sign-in": "missing",
            "gitleaks": "missing",
        }
        assert items["gitleaks"].detail == (
            f"install gitleaks {GITLEAKS_VERSION}; devctl check blocks its secrets step without it"
        )
        assert items["core.hooksPath"].status == "missing"
        assert fake_run.argv == []

    @pytest.mark.parametrize(
        ("output", "status"),
        [
            (result(0, "git version 2.4.0\n"), "missing"),  # 4 is below 31, as numbers
            (result(0, "git version 2.100.1\n"), "ok"),
            (result(0, "git version 3.0\n"), "ok"),
            (result(0, "git version 10.0.0\n"), "ok"),
            (result(0, "git version 2.39.5\n", timed_out=True), "unknown"),
            (result(0, "git version 2.39.5\n", stdout_truncated=True), "unknown"),
            (result(0, "git version 2.39.5\n", "boom"), "ok"),
            (result(128, "git version 2.39.5\n"), "unknown"),
            (result(0, ""), "unknown"),
        ],
    )
    def test_git_version_is_compared_as_numbers(
        self, fake_run: FakeRun, output: ProcessResult, status: str
    ) -> None:
        fake_run.answer(["git", "--version"], output)
        assert git_item().status == status

    def test_git_reports_its_version_and_never_its_output(self, fake_run: FakeRun) -> None:
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5 (Apple Git-154)\n"))
        assert git_item().detail == "2.39.5"
        assert fake_run.argv == [["/usr/bin/git", "--version"]]

    @pytest.mark.parametrize(
        ("output", "status"),
        [
            (result(0, f"{GITLEAKS_VERSION}\nextra\n"), "ok"),
            (result(0, f"v{GITLEAKS_VERSION}\n"), "ok"),
            (result(0, "9.0.0\n"), "missing"),
            (result(0, "8.30.2\n"), "missing"),  # the pin is exact, not a prefix
            (result(0, "8.3.1\n"), "missing"),
            (result(0, "8.30\n"), "unknown"),
            (result(0, f"gitleaks version {GITLEAKS_VERSION}\n"), "unknown"),
            (result(0, "vv8.30.1\n"), "unknown"),
            (result(0, ""), "unknown"),
            (result(0, f"{GITLEAKS_VERSION}\n", timed_out=True), "unknown"),
            (result(0, f"{GITLEAKS_VERSION}\n", stdout_truncated=True), "unknown"),
            (result(2, f"{GITLEAKS_VERSION}\n"), "unknown"),
        ],
    )
    def test_gitleaks_output_shapes(
        self, fake_run: FakeRun, output: ProcessResult, status: str
    ) -> None:
        fake_run.answer(["gitleaks", "version"], output)
        item = gitleaks_item()
        assert (item.area, item.name, item.status) == ("toolchain", "gitleaks", status)
        assert fake_run.argv == [["/usr/bin/gitleaks", "version"]]

    @pytest.mark.parametrize(
        ("output", "status"),
        [
            (result(0), "ok"),
            (result(1, err="not logged in"), "missing"),
            (result(0, timed_out=True), "unknown"),
        ],
    )
    def test_gh_sign_in_is_the_exit_code_of_gh_auth_status(
        self, ctx: MakeContext, fake_run: FakeRun, output: ProcessResult, status: str
    ) -> None:
        fake_run.answer(["gh", "auth", "status"], output)
        assert by_name(local_items(ctx()))["gh sign-in"].status == status
        assert ["/usr/bin/gh", "auth", "status"] in fake_run.argv

    def test_uv_and_gh_are_ok_where_which_finds_them(
        self, ctx: MakeContext, fake_run: FakeRun
    ) -> None:
        items = by_name(local_items(ctx()))
        assert (items["uv"].status, items["uv"].detail) == ("ok", "/usr/bin/uv")
        assert (items["gh"].status, items["gh"].detail) == ("ok", "/usr/bin/gh")


class TestSignIns:
    def test_no_roster_means_no_sign_in_items_and_no_session(
        self, ctx: MakeContext, fake_run: FakeRun
    ) -> None:
        items = local_items(ctx())
        assert [i.name for i in items if i.name.endswith(("(claude)", "(codex)", "(agy)"))] == []
        assert not any(arg in {"-p", "exec", "--print"} for argv in fake_run.argv for arg in argv)

    @pytest.mark.parametrize(
        "changes",
        [
            {},
            {"worker_app": None, "reviewer_app": None},
            {"stack": "agnostic", "repository": None, "code_owner": None},
        ],
        ids=["agent identity on", "agent identity off", "agnostic, no repository"],
    )
    def test_the_full_report_has_no_harness_sign_in_for_any_settings(
        self,
        ctx: MakeContext,
        fake_run: FakeRun,
        capsys: pytest.CaptureFixture[str],
        changes: dict[str, object],
    ) -> None:
        # The optional rs-providers skill checks each Harness's sign-in (Spec 2). fake_run finds
        # claude, codex and agy on PATH, and doctor without --skills runs none of them.
        run_doctor(adjusted(ctx(), **changes))
        report = capsys.readouterr().out.splitlines()
        assert [line for line in report if re.search(r"\b(?:claude|codex|agy)\b", line)] == []
        assert [line for line in report if "sign-in" in line and "gh sign-in" not in line] == []
        harnesses = {"claude", "codex", "agy"}
        assert [argv for argv in fake_run.argv if Path(argv[0]).name in harnesses] == []


class TestItems:
    def test_the_items_come_in_this_order_with_these_areas(
        self, ctx: MakeContext, fake_run: FakeRun
    ) -> None:
        items = local_items(ctx())
        assert [(i.area, i.name) for i in items] == [
            ("toolchain", "git"),
            ("toolchain", "uv"),
            ("toolchain", "gh"),
            ("toolchain", "gh sign-in"),
            ("toolchain", "gitleaks"),
            ("guardrails", "core.hooksPath"),
            ("guardrails", "CI workflow"),
            ("guardrails", "Python guardrail settings"),
            ("guardrails", "tools/devctl exclusions"),
            ("kit", "Kit files"),
        ]

    def test_the_agnostic_stack_has_no_python_guardrail_item(
        self, ctx: MakeContext, fake_run: FakeRun
    ) -> None:
        names = [i.name for i in local_items(adjusted(ctx(), stack="agnostic"))]
        assert "Python guardrail settings" not in names
        assert "tools/devctl exclusions" in names

    @pytest.mark.parametrize(
        ("config", "detail"),
        [
            (result(0, "hooks\n"), "core.hooksPath is hooks;"),
            (result(1), "core.hooksPath is not set;"),
            (result(0, "\n"), "core.hooksPath is not set;"),
        ],
    )
    def test_core_hooks_path_must_be_githooks(
        self, ctx: MakeContext, fake_run: FakeRun, config: ProcessResult, detail: str
    ) -> None:
        fake_run.answer(["git", "config", "--get", "core.hooksPath"], config)
        item = by_name(local_items(ctx()))["core.hooksPath"]
        assert item.status == "missing"
        assert item.detail.startswith(detail)
        assert "git config core.hooksPath .githooks" in item.detail

    def test_core_hooks_path_that_did_not_finish_is_unknown(
        self, ctx: MakeContext, fake_run: FakeRun
    ) -> None:
        answer = result(0, ".githooks\n", timed_out=True)
        fake_run.answer(["git", "config", "--get", "core.hooksPath"], answer)
        assert by_name(local_items(ctx()))["core.hooksPath"].status == "unknown"

    def test_the_ci_workflow_must_be_tracked(self, ctx: MakeContext, fake_run: FakeRun) -> None:
        item = by_name(local_items(ctx()))["CI workflow"]
        assert item.status == "missing"
        assert "not tracked" in item.detail

    def test_a_workflow_that_git_does_not_track_does_not_count(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        workflow = repo_files.root / ".github/workflows/devctl-check.yml"
        workflow.parent.mkdir(parents=True)
        workflow.write_text("jobs:\n  check:\n    name: devctl check\n")
        item = by_name(local_items(ctx()))["CI workflow"]
        assert item.status == "missing"
        assert "not tracked" in item.detail

    def test_a_tracked_workflow_that_cannot_be_read_is_unknown(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        repo_files.workflow(job_name="devctl check")
        (repo_files.root / ".github/workflows/devctl-check.yml").unlink()
        item = by_name(local_items(ctx()))["CI workflow"]
        assert item.status == "unknown"
        assert item.detail == "cannot read .github/workflows/devctl-check.yml"

    @pytest.mark.parametrize(
        ("text", "status"),
        [
            ("jobs:\n  check:\n    name: check\n", "missing"),
            ("jobs:\n  devctl check:\n    runs-on: x\n", "missing"),  # the id is not the name
            ("jobs: [\n", "missing"),
            ("jobs: 3\n", "missing"),
            ("- a\n- b\n", "missing"),
            ("", "missing"),
            ("jobs:\n  a:\n    name: other\n  b:\n    name: devctl check\n", "ok"),
        ],
    )
    def test_the_ci_workflow_needs_a_job_named_devctl_check(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles, text: str, status: str
    ) -> None:
        repo_files.write(".github/workflows/devctl-check.yml", text)
        assert by_name(local_items(ctx()))["CI workflow"].status == status

    def test_a_missing_lock_makes_the_kit_files_item_missing_without_a_command(
        self, ctx: MakeContext, fake_run: FakeRun
    ) -> None:
        item = by_name(local_items(ctx()))["Kit files"]
        assert item.status == "missing"
        assert ".rapid-ship/kit.lock: missing" in item.detail
        assert "uvx" not in item.detail

    def test_modified_files_are_listed_and_do_not_make_the_item_missing(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        repo_files.lock(unchanged=["devctl"], missing=[], stale=["AGENTS.md"])
        repo_files.write("AGENTS.md", "ours")
        item = by_name(local_items(ctx()))["Kit files"]
        assert item.status == "ok"
        assert "1 unchanged, 1 modified, 0 excluded; modified: AGENTS.md; run uvx" in item.detail
        assert item.detail.endswith("rapid-ship status to see template updates")

    def test_python_guardrail_gaps_are_joined(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        repo_files.write("pyproject.toml", "[tool.mypy]\nstrict = true\n")
        item = by_name(local_items(ctx()))["Python guardrail settings"]
        assert item.status == "missing"
        assert "mypy: warn_unreachable is not true; mypy: enable_error_code lacks" in item.detail

    def test_the_seeded_pyproject_meets_both_pyproject_items(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        repo_files.write("pyproject.toml", seeded_pyproject_text())
        items = by_name(local_items(ctx()))
        assert items["Python guardrail settings"].status == "ok"
        assert items["tools/devctl exclusions"].status == "ok"
        assert "not checked" not in items["tools/devctl exclusions"].detail

    def test_a_missing_or_unparsable_pyproject_is_missing_for_the_python_stack(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        items = by_name(local_items(ctx()))
        assert items["Python guardrail settings"].detail == "no pyproject.toml"
        assert items["tools/devctl exclusions"].status == "missing"
        repo_files.write("pyproject.toml", "[tool\nbroken")
        items = by_name(local_items(ctx()))
        assert items["Python guardrail settings"].status == "missing"
        assert items["Python guardrail settings"].detail.startswith("pyproject.toml: ")
        assert items["tools/devctl exclusions"].status == "missing"

    def test_the_agnostic_stack_needs_no_pyproject_but_checks_the_uv_workspace(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        agnostic = adjusted(ctx(), stack="agnostic")
        item = by_name(local_items(agnostic))["tools/devctl exclusions"]
        assert (item.status, item.detail) == ("ok", "no pyproject.toml, so no uv workspace")
        repo_files.write("pyproject.toml", '[tool.uv.workspace]\nmembers = ["tools/*"]\n')
        item = by_name(local_items(agnostic))["tools/devctl exclusions"]
        assert item.status == "missing"
        assert item.detail.startswith("uv: ")
        repo_files.write("pyproject.toml", "[tool\nbroken")
        assert by_name(local_items(agnostic))["tools/devctl exclusions"].status == "missing"

    def test_the_kit_source_notes_what_it_does_not_check_even_when_nothing_is_missing(
        self, ctx: MakeContext, fake_run: FakeRun, repo_files: RepoFiles
    ) -> None:
        repo_files.write("pyproject.toml", "[project]\nname = 'kit'\n")
        repo_files.write(KIT_SOURCE, "")
        item = by_name(local_items(ctx()))["tools/devctl exclusions"]
        assert item.status == "ok"
        assert item.detail == (
            "ruff, mypy and pytest not checked: this repository holds the Kit templates"
        )


class TestOutput:
    def test_exit_code_ignores_ok_items(self) -> None:
        assert doctor_exit_code([]) == 0
        assert doctor_exit_code([Item("a", "n", "unknown", ""), Item("a", "n", "ok", "")]) == 2

    def test_every_item_is_printed_then_the_summary(
        self, ctx: MakeContext, fake_run: FakeRun, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # Unanswered commands exit 1 with no output: gh sign-in, hooks, CI and Kit files are
        # missing, and gitleaks (no version printed) is unknown. With no repository, the GitHub
        # part is one missing item, printed after the local ones.
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        context = adjusted(
            ctx(), stack="agnostic", repository=None, worker_app=None, reviewer_app=None
        )
        assert run_doctor(context) == 2
        lines = capsys.readouterr().out.splitlines()
        assert lines[0] == "ok  toolchain  git: 2.39.5"
        assert "missing  toolchain  gh sign-in: not signed in; run gh auth login" in lines
        assert "unknown  toolchain  gitleaks: gitleaks version gave no readable version" in lines
        assert (
            lines[-2]
            == "missing  github  repository: repository is not set in .rapid-ship/project.toml"
        )
        assert lines[-1] == "doctor: 4 ok, 5 missing, 1 unknown"
        assert len(lines) == 11

    def test_doctor_reads_the_project_and_reports_every_local_item_ok(
        self,
        ctx: MakeContext,
        fake_run: FakeRun,
        repo_files: RepoFiles,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        repo_files.write(".rapid-ship/project.toml", 'stack = "agnostic"\n')
        repo_files.workflow(job_name="devctl check")
        repo_files.lock(unchanged=["devctl"], missing=[])
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        fake_run.answer(["gitleaks", "version"], result(0, f"{GITLEAKS_VERSION}\n"))
        fake_run.answer(["gh", "auth", "status"], result(0))
        fake_run.answer(["git", "config", "--get", "core.hooksPath"], result(0, ".githooks\n"))
        monkeypatch.chdir(repo_files.root)
        # The project names no repository, so GitHub's part is one missing item and the exit is 1.
        assert doctor_command(argparse.Namespace(skills=False)) == 1
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == "doctor: 9 ok, 1 missing, 0 unknown"
        assert lines[-2].startswith("missing  github  repository: ")
        assert all(line.startswith("ok  ") for line in lines[:-2])

    def test_an_unreadable_project_stops_with_the_settings_error(
        self,
        ctx: MakeContext,
        fake_run: FakeRun,
        repo_files: RepoFiles,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        fake_run.answer(["git", "--version"], result(0, "git version 2.39.5\n"))
        monkeypatch.chdir(repo_files.root)
        assert cli.main(["doctor"]) == 2
        assert ".rapid-ship/project.toml: missing" in capsys.readouterr().err

    def test_git_that_cannot_be_read_stops_with_unknown(
        self,
        fake_run: FakeRun,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.chdir(tmp_path)
        fake_run.answer(["git", "--version"], result(0, "no version here\n"))
        assert doctor_command(argparse.Namespace(skills=False)) == 2
        out = capsys.readouterr().out
        assert out.splitlines() == [
            "unknown  toolchain  git: git --version gave no readable version",
            "doctor: 0 ok, 0 missing, 1 unknown",
        ]

    def test_doctor_is_a_registered_command(self) -> None:
        args = cli.build_parser().parse_args(["doctor"])
        assert args.handler is doctor.doctor_command
        with pytest.raises(SystemExit) as raised:
            cli.main(["doctor", "--help"])
        assert raised.value.code == 0


class TestGhGet:
    def test_it_runs_gh_api_as_get_and_parses_the_json(self, fake_run: FakeRun) -> None:
        fake_run.answer(GH_GET, result(0, '{"id": 2}'))
        assert gh_get("repos/o/r") == {"id": 2}
        assert fake_run.argv == [GH_GET]

    def test_a_failed_request_carries_gh_s_status_and_the_json_message(
        self, fake_run: FakeRun
    ) -> None:
        fake_run.answer(GH_GET, result(1, '{"message": "Not Found"}', "gh: Not Found (HTTP 404)\n"))
        with pytest.raises(OwnerReadError) as raised:
            gh_get("repos/o/r")
        assert (raised.value.status, raised.value.message) == (404, "Not Found")
        assert str(raised.value) == "Not Found"

    @pytest.mark.parametrize(
        ("output", "status", "message"),
        [
            (result(1, "", "gh: HTTP 500 oops\n"), None, "gh: HTTP 500 oops"),
            (result(1, "", "gh: Server Error (HTTP 502)\n"), 502, "gh: Server Error (HTTP 502)"),
            (result(1, "[]", "gh: Forbidden (HTTP 403)\n"), 403, "gh: Forbidden (HTTP 403)"),
            (result(4), None, "gh api exited 4"),
            (result(1, '{"message": 7}'), None, "gh api exited 1"),
            (result(1, "<html>", ""), None, "gh api exited 1"),
        ],
    )
    def test_the_message_falls_back_to_stderr_then_the_exit_code(
        self, fake_run: FakeRun, output: ProcessResult, status: int | None, message: str
    ) -> None:
        fake_run.answer(GH_GET, output)
        with pytest.raises(OwnerReadError) as raised:
            gh_get("repos/o/r")
        assert (raised.value.status, raised.value.message) == (status, message)

    def test_a_timeout_is_checked_before_anything_else(self, fake_run: FakeRun) -> None:
        fake_run.answer(
            GH_GET, result(1, "{}", "(HTTP 500)", timed_out=True, stdout_truncated=True)
        )
        with pytest.raises(OwnerReadError, match="gh api timed out") as raised:
            gh_get("repos/o/r")
        assert raised.value.status is None

    def test_cut_output_is_checked_before_the_exit_code(self, fake_run: FakeRun) -> None:
        fake_run.answer(GH_GET, result(1, '{"id": 9', "", stdout_truncated=True))
        with pytest.raises(
            OwnerReadError, match=f"gh api output exceeded {MAX_OUTPUT_BYTES} bytes"
        ):
            gh_get("repos/o/r")

    def test_output_that_is_not_json_is_an_error(self, fake_run: FakeRun) -> None:
        fake_run.answer(GH_GET, result(0, "not json"))
        with pytest.raises(OwnerReadError, match="gh api printed no JSON"):
            gh_get("repos/o/r")

    @pytest.mark.parametrize(
        "installed", [False, True], ids=["gh not installed", "gh not executable"]
    )
    def test_a_gh_that_cannot_start_is_an_owner_read_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, installed: bool
    ) -> None:
        # The real run_process, with PATH a directory that holds no working gh: Popen raises
        # FileNotFoundError, or PermissionError for a file that is not executable. Neither may
        # escape, because cli.main turns only RepoError and SettingsError into exit 2.
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        if installed:
            (bin_dir / "gh").write_text("#!/bin/sh\n")
            (bin_dir / "gh").chmod(0o644)
        monkeypatch.setenv("PATH", str(bin_dir))
        with pytest.raises(OwnerReadError, match="gh could not start") as raised:
            gh_get("repos/o/r")
        assert (raised.value.status, raised.value.message) == (None, "gh could not start")
