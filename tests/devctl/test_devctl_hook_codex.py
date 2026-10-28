"""Offline: recorded Codex events and simulated CLI calls; no Codex Session runs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devctl.hook_protocols import ToolCall, read_event
from test_devctl_hook_agy import IDENTITY, INVALID, PYTHON, project, raise_inside_the_rules
from test_devctl_hook_protocol import hook

FIXTURES = Path(__file__).parent / "fixtures/hooks/codex"
REPO = Path("/repo")


def recorded(name: str = "bash.json", **changes: object) -> bytes:
    event = json.loads((FIXTURES / name).read_text())
    event.update(changes)
    return json.dumps(event).encode()


def calling(command: str, cwd: Path = REPO, tool: str = "Bash") -> bytes:
    return recorded(cwd=str(cwd), tool_name=tool, tool_input={"command": command})


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("bash.json", ToolCall("git status", (), REPO)),
        ("bash-subagent.json", ToolCall("git status", (), REPO)),
        (
            "bash-headless.json",
            ToolCall(
                "git status --short --branch && rg --files -g 'spike.ipynb' "
                "-g 'spike.txt' -g 'AGENTS.md'",
                (),
                REPO,
            ),
        ),
        ("apply-patch.json", ToolCall(None, (REPO / "spike.ipynb",), REPO)),
    ],
)
def test_recorded_events(name: str, expected: ToolCall) -> None:
    assert read_event("codex", (FIXTURES / name).read_bytes()) == expected


def test_fixtures_equal_the_appended_record() -> None:
    record = (Path(__file__).parents[2] / "docs/trials/2026-10-21-hook-spike.md").read_text()
    for fixture in FIXTURES.glob("*.json"):
        section = record.split(f"### `codex/{fixture.name}`\n", 1)[1]
        assert section.split("```json\n", 1)[1].split("```", 1)[0] == fixture.read_text()


@pytest.mark.parametrize("tool", ["Read", "unknown"])
def test_unwired_tools_have_no_action(tool: str) -> None:
    assert read_event("codex", calling("git push --force", tool=tool)) == ToolCall(None, (), REPO)


@pytest.mark.parametrize(
    ("command", "settings", "reason"),
    [
        ("git commit -n -m x", PYTHON, "G1: "),
        ("git push --force", PYTHON, "G2: "),
        ("git push origin HEAD:main", PYTHON, "G3: "),
        ("git push origin task", IDENTITY, "G7: "),
        ("gh pr create --fill", IDENTITY, "G8: "),
        ("gh pr merge 1", PYTHON, "merge denied: "),
        ("git commit -n -m x", INVALID, "G1: "),
        ("git push --force", INVALID, "G2: "),
        ("gh pr merge 1 --admin", INVALID, "G3: "),
        ("gh pr merge 1", INVALID, "merge denied: "),
        ("gh pr merge '", PYTHON, "merge denied: "),
    ],
)
def test_shell_denials(
    command: str,
    settings: str,
    reason: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path, settings)
    assert hook(monkeypatch, calling(command, workspace.root), "codex", "pre-tool") == 0
    out, err = capsys.readouterr()
    output = json.loads(out)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert output["permissionDecision"] == "deny"
    assert output["permissionDecisionReason"].startswith(reason)
    assert bool(err) == (settings == INVALID)


@pytest.mark.parametrize("settings", [PYTHON, INVALID])
def test_harmless_calls_have_no_decision(
    settings: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        hook(
            monkeypatch,
            calling("git status", project(tmp_path, settings).root),
            "codex",
            "pre-tool",
        )
        == 0
    )
    out, err = capsys.readouterr()
    assert out == ""
    assert bool(err) == (settings == INVALID)


def test_protected_patch_does_not_ask_but_claude_still_does(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path)
    workspace.write(".github/CODEOWNERS", "* @o\n# /**/AGENTS.md @o\n")
    patch = "*** Begin Patch\n*** Add File: AGENTS.md\n+x\n*** End Patch"
    assert (
        hook(monkeypatch, calling(patch, workspace.root, "apply_patch"), "codex", "pre-tool") == 0
    )
    assert capsys.readouterr() == ("", "")
    event = recorded(
        cwd=str(workspace.root), tool_name="Write", tool_input={"file_path": "AGENTS.md"}
    )
    assert hook(monkeypatch, event, "claude", "pre-tool") == 0
    answer = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert answer["permissionDecision"] == "ask"
    assert answer["permissionDecisionReason"].startswith("G5: ")


@pytest.mark.parametrize(
    "payload",
    [
        b"\xff",
        b"[]",
        b"{}",
        recorded(cwd="relative"),
        recorded(cwd=None),
        recorded(hook_event_name="PostToolUse"),
        recorded(tool_name=None),
        recorded(tool_input=None),
        recorded(tool_input={}),
        calling("arbitrary text", tool="apply_patch"),
    ],
)
def test_malformed_calls_exit_one_with_only_stderr(
    payload: bytes,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert hook(monkeypatch, payload, "codex", "pre-tool") == 1
    out, err = capsys.readouterr()
    assert out == ""
    assert len(err.splitlines()) == 1
    assert err.startswith("devctl hook: internal error: ")
    assert err.endswith("; the tool call goes through\n")


@pytest.mark.parametrize("args", [("codex",), ("codex", "post-tool")])
def test_usage_failure_has_no_stdout(
    args: tuple[str, ...],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert hook(monkeypatch, recorded(), *args) == 1
    assert capsys.readouterr() == ("", "devctl hook: usage: devctl hook codex pre-tool\n")


def test_internal_failure_has_no_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raise_inside_the_rules(monkeypatch)
    assert (
        hook(monkeypatch, calling("git status", project(tmp_path).root), "codex", "pre-tool") == 1
    )
    assert capsys.readouterr() == (
        "",
        "devctl hook: internal error: boom; the tool call goes through\n",
    )


def test_recognized_merge_check_failure_denies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def broken_read(path: str, jq: str | None = None) -> object:
        raise RuntimeError("read failed")

    workspace = project(tmp_path, PYTHON + '\n[github]\nrepository = "o/r"\n')
    monkeypatch.setattr("devctl.hook.gh_get", broken_read)
    assert hook(monkeypatch, calling("gh pr merge 1", workspace.root), "codex", "pre-tool") == 0
    out, err = capsys.readouterr()
    answer = json.loads(out)["hookSpecificOutput"]
    assert answer["permissionDecision"] == "deny"
    assert "the guard failed: RuntimeError: read failed" in answer["permissionDecisionReason"]
    assert err == ""
