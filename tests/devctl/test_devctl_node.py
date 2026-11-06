"""Offline: the Node.js helpers against fake tools in a fake node_modules/.bin."""

import json
from pathlib import Path

import pytest

from check_workspace import node_tools
from devctl import process
from devctl.node import cannot_run, eslint_config, is_error, node_tool
from devctl.process import ProcessResult


def test_the_install_advice_follows_the_lock(tmp_path: Path) -> None:
    assert cannot_run("eslint", "frontend", "eslint is not installed", tmp_path) == (
        "cannot run eslint in frontend: eslint is not installed; "
        "run npm install there and commit package-lock.json"
    )
    (tmp_path / "package-lock.json").touch()
    assert cannot_run("eslint", "frontend", "eslint is not installed", tmp_path).endswith(
        "run npm ci there"
    )


def test_eslint_config_reads_print_config(tmp_path: Path) -> None:
    assert node_tool(tmp_path, "eslint") is None
    assert eslint_config(tmp_path) == "eslint is not installed"
    node_tools(tmp_path, eslint='print(\'{"rules": {"no-console": ["error"]}}\')')
    assert eslint_config(tmp_path) == {"rules": {"no-console": ["error"]}}
    logged = json.loads((tmp_path / "node_modules/.bin/eslint.log").read_text())
    assert logged["argv"] == ["--print-config", "src/index.ts"]
    assert logged["cwd"] == str(tmp_path)
    node_tools(tmp_path, eslint='print("earlier\\nboom", file=sys.stderr); sys.exit(2)')
    assert eslint_config(tmp_path) == "eslint exited 2: boom"
    for output in ("x", "[]"):
        node_tools(tmp_path, eslint=f"print({output!r})")
        assert eslint_config(tmp_path) == "eslint printed no JSON object"


def test_eslint_config_reports_a_simulated_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    node_tools(tmp_path, eslint="sys.exit(0)")
    calls: list[tuple[list[str], Path, float]] = []

    def timed_out(argv: list[str], cwd: Path, timeout: float) -> ProcessResult:
        calls.append((argv, cwd, timeout))
        return ProcessResult(argv, 0, "{}", "", 0, timed_out=True)

    monkeypatch.setattr(process, "run_process", timed_out)
    assert eslint_config(tmp_path) == "eslint timed out after 120 seconds"
    assert calls == [
        (
            [str(tmp_path / "node_modules/.bin/eslint"), "--print-config", "src/index.ts"],
            tmp_path,
            120,
        )
    ]


@pytest.mark.parametrize("severity", [2, "error", [2], ["error", {}]])
def test_a_severity_is_an_error_when_it_is_2_or_error(severity: object) -> None:
    assert is_error(severity)


@pytest.mark.parametrize("severity", [1, "warn", 0, "off", [], None])
def test_other_severities_are_not_errors(severity: object) -> None:
    assert not is_error(severity)
