"""Offline: doctor --settings on fixture repositories; gh_get is replaced by a reader that fails the
test. agy and Codex probes run this checkout's devctl hook through a stand-in shim."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

from check_workspace import Workspace
from devctl import doctor
from devctl.cli import main
from devctl.doctor import DoctorContext
from rapid_ship.kit.templates import load_manifest, render_files

VARIABLES = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
DEVCTL = Path(__file__).resolve().parents[2] / "tools/devctl"
# The Kit's shim runs devctl through uv; this one runs the vendored devctl with this Python.
SHIM = (
    "#!/bin/sh\n"
    f"PYTHONPATH={shlex.quote(str(DEVCTL))} exec {shlex.quote(sys.executable)} "
    "-c 'import sys; from devctl.cli import main; sys.exit(main())' \"$@\"\n"
)
INVALID_KEY = 'stack = "python"\n[escalation]\nrevision_rounds = 0\n'


def commit_seeds(workspace: Workspace, *, codeowners: bool = True) -> None:
    wanted = {
        ".claude/settings.json",
        ".agents/hooks.json",
        ".codex/hooks.json",
        ".agents/devctl",
        *([".github/CODEOWNERS"] if codeowners else []),
    }
    for template in render_files("python", VARIABLES, ()):
        if template.path.startswith(".rapid-ship/") or template.path in wanted:
            assert template.content is not None
            target = workspace.write(template.path, template.content.decode())
            if template.path in load_manifest().executable:
                target.chmod(0o755)
    workspace.write("devctl", SHIM).chmod(0o755)
    workspace.commit("Add the Kit's settings")


@pytest.fixture
def in_workspace(workspace: Workspace, monkeypatch: pytest.MonkeyPatch) -> Workspace:
    def no_github(path: str, jq: str | None = None) -> object:
        pytest.fail(f"doctor --settings read GitHub: {path}")

    def no_full_doctor(ctx: DoctorContext, *, skills: bool = False) -> int:
        pytest.fail("doctor --settings ran the full doctor")

    monkeypatch.setattr(doctor, "gh_get", no_github)
    monkeypatch.setattr(doctor, "run_doctor", no_full_doctor)
    monkeypatch.chdir(workspace.root)
    return workspace


def test_settings_reads_only_the_settings_and_asks_github_nothing(
    in_workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_seeds(in_workspace)

    assert main(["doctor", "--settings"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert [line.split(": ")[0] for line in lines[:-1]] == [
        "ok  toolchain  git",
        "ok  guardrails  settings",
        "ok  guardrails  Claude Code wiring",
        "ok  guardrails  agy wiring",
        "ok  guardrails  Codex wiring",
    ]
    assert lines[1].startswith("ok  guardrails  settings: ")
    assert lines[2].startswith("ok  guardrails  Claude Code wiring: ")
    # The deterministic checks run the real hook through the stand-in and managed forwarder.
    assert lines[3].endswith("in deterministic direct/shell checks from root and .agents/")
    assert "denied a probe git push --force" in lines[4]
    assert "/hooks" in lines[4]
    assert lines[-1] == "doctor: 5 ok, 0 missing, 0 unknown"


def test_an_invalid_key_exits_2_and_names_the_file_and_the_key(
    in_workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_seeds(in_workspace)
    in_workspace.write(".rapid-ship/project.toml", INVALID_KEY)

    assert main(["doctor", "--settings"]) == 2

    assert (
        "unknown  guardrails  settings: .rapid-ship/project.toml [escalation] revision_rounds: "
        "expected an integer of at least 1"
    ) in capsys.readouterr().out.splitlines()


def test_invalid_exceptions_exit_2_and_name_the_file(
    in_workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_seeds(in_workspace)
    in_workspace.write(".rapid-ship/exceptions.toml", 'exception = "none"\n')

    assert main(["doctor", "--settings"]) == 2

    assert capsys.readouterr().out.splitlines()[1] == (
        "unknown  guardrails  settings: .rapid-ship/exceptions.toml exception: "
        "expected a list of tables"
    )


def test_a_codeowners_that_is_not_utf8_exits_2_and_names_the_file(
    in_workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_seeds(in_workspace)
    (in_workspace.root / ".github/CODEOWNERS").write_bytes(b"/api/ @owner \xff\n")

    assert main(["doctor", "--settings"]) == 2

    assert capsys.readouterr().out.splitlines()[1] == (
        "unknown  guardrails  settings: .github/CODEOWNERS is not UTF-8: 'utf-8' codec can't "
        "decode byte 0xff in position 13: invalid start byte"
    )


def test_a_missing_codeowners_is_missing(
    in_workspace: Workspace, capsys: pytest.CaptureFixture[str]
) -> None:
    commit_seeds(in_workspace, codeowners=False)

    assert main(["doctor", "--settings"]) == 1

    assert capsys.readouterr().out.splitlines()[1] == (
        "missing  guardrails  settings: no CODEOWNERS file; restore .github/CODEOWNERS from git "
        "or write a new one (rapid-ship sync seeds it only while the Kit lock does not list it)"
    )


def test_settings_and_skills_exclude_each_other(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["doctor", "--settings", "--skills"])

    assert raised.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err
