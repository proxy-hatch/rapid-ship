"""Offline: Claude Code's hook protocol, from recorded Claude Code events; no Session runs."""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from check_workspace import Workspace, new_workspace
from devctl import cli
from devctl.hook import run_hook
from devctl.hook_protocols import WIRED_TOOLS, Decision, ToolCall, answer, read_event

FIXTURES = Path(__file__).parent / "fixtures" / "hooks" / "claude"
REPO = Path("/repo")
FORCE_PUSH = "git push --force origin task"


def recorded(name: str = "bash.json", **changes: object) -> bytes:
    """A recorded event with top-level keys replaced; a value of None removes the key."""
    event = json.loads((FIXTURES / name).read_text())
    for key, value in changes.items():
        if value is None:
            event.pop(key)
        else:
            event[key] = value
    return json.dumps(event).encode()


def with_command(name: str, cwd: Path, command: str) -> bytes:
    tool_input = json.loads((FIXTURES / name).read_text())["tool_input"]
    return recorded(name, cwd=str(cwd), tool_input={**tool_input, "command": command})


def project(tmp_path: Path) -> Workspace:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n')
    return workspace


def hook(monkeypatch: pytest.MonkeyPatch, payload: bytes, *argv: str) -> int:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload)))
    return cli.main(["hook", *argv])


def unread_github(path: str, jq: str | None = None) -> object:
    raise AssertionError(f"GitHub was read: {path}")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("bash.json", ToolCall("git status", (), REPO)),
        ("bash-subagent.json", ToolCall("git status", (), REPO)),
        ("write.json", ToolCall(None, (REPO / "spike.txt",), REPO)),
        ("edit.json", ToolCall(None, (REPO / "spike.txt",), REPO)),
        ("notebook-edit.json", ToolCall(None, (REPO / "spike.ipynb",), REPO)),
        ("monitor.json", ToolCall("git status", (), REPO)),
    ],
)
def test_read_event_normalises_each_recorded_event(name: str, expected: ToolCall) -> None:
    assert read_event("claude", (FIXTURES / name).read_bytes()) == expected


def test_an_unwired_tool_gives_an_empty_call() -> None:
    event = json.loads((FIXTURES / "bash.json").read_text())
    event["tool_name"] = "Read"
    assert read_event("claude", json.dumps(event).encode()) == ToolCall(None, (), REPO)


def test_multi_edit_is_read_by_its_file_path() -> None:
    payload = recorded("edit.json", tool_name="MultiEdit")
    assert read_event("claude", payload) == ToolCall(None, (REPO / "spike.txt",), REPO)


def test_a_path_is_resolved_against_cwd_and_normalised_lexically() -> None:
    relative = recorded("write.json", cwd="/repo/sub/", tool_input={"file_path": "../a/./b.txt"})
    dotted = recorded("write.json", tool_input={"file_path": "/repo/x/../.rapid-ship/kit.lock"})

    assert read_event("claude", relative) == ToolCall(None, (REPO / "a/b.txt",), REPO / "sub")
    assert read_event("claude", dotted).edits == (REPO / ".rapid-ship/kit.lock",)


def test_a_path_through_a_symlink_keeps_the_link(tmp_path: Path) -> None:
    cwd = tmp_path / "repo"
    elsewhere = tmp_path / "elsewhere"
    cwd.mkdir()
    elsewhere.mkdir()
    (cwd / "link").symlink_to(elsewhere, target_is_directory=True)
    payload = recorded("write.json", cwd=str(cwd), tool_input={"file_path": "link/x.txt"})

    assert read_event("claude", payload).edits == (cwd / "link/x.txt",)


@pytest.mark.parametrize("tool", WIRED_TOOLS)
def test_every_wired_tool_is_read_into_a_call_a_rule_can_match(tool: str) -> None:
    tool_input = {
        "command": "git status",
        "file_path": "/repo/x.txt",
        "notebook_path": "/repo/x.ipynb",
    }

    call = read_event("claude", recorded(tool_name=tool, tool_input=tool_input))

    assert call.shell is not None or call.edits


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"\xffnot json", id="not-json"),
        pytest.param(b"[]", id="not-an-object"),
        pytest.param(recorded(hook_event_name="PostToolUse"), id="post-tool-use"),
        pytest.param(recorded(hook_event_name=None), id="no-hook-event-name"),
        pytest.param(recorded(cwd=None), id="no-cwd"),
        pytest.param(recorded(cwd="repo"), id="relative-cwd"),
        pytest.param(recorded(tool_name=None), id="no-tool-name"),
        pytest.param(recorded(tool_input=None), id="no-tool-input"),
        pytest.param(recorded(tool_input="git status"), id="tool-input-not-an-object"),
        pytest.param(recorded(tool_input={"description": "x"}), id="bash-without-command"),
        pytest.param(recorded("write.json", tool_input={"content": "x"}), id="write-no-path"),
    ],
)
def test_a_malformed_event_is_a_value_error(payload: bytes) -> None:
    with pytest.raises(ValueError, match=r"."):
        read_event("claude", payload)


@pytest.mark.parametrize("decision", ["deny", "ask"])
def test_a_decision_is_one_json_line_with_exit_0(decision: Decision) -> None:
    stdout, code = answer("claude", decision, "G1: why")
    assert code == 0
    assert stdout.count("\n") == 1
    assert stdout.endswith("\n")
    assert json.loads(stdout) == {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": "G1: why",
        }
    }


def test_no_decision_is_empty_with_exit_0() -> None:
    assert answer("claude", None, "") == ("", 0)


def test_a_recorded_bash_event_with_a_force_push_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = project(tmp_path)

    payload = with_command("bash.json", workspace.root, FORCE_PUSH)
    code = hook(monkeypatch, payload, "claude", "pre-tool")

    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert code == 0
    assert output["permissionDecision"] == "deny"
    assert output["permissionDecisionReason"].startswith("G2: ")


def test_a_recorded_monitor_event_with_a_force_push_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = project(tmp_path)

    payload = with_command("monitor.json", workspace.root, FORCE_PUSH)
    code = hook(monkeypatch, payload, "claude", "pre-tool")

    output = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert code == 0
    assert output["permissionDecision"] == "deny"
    assert output["permissionDecisionReason"].startswith("G2: ")


def test_a_harmless_event_gets_no_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = project(tmp_path)

    code = hook(monkeypatch, recorded(cwd=str(workspace.root)), "claude", "pre-tool")

    assert code == 0
    assert capsys.readouterr() == ("", "")


def invalid_settings(tmp_path: Path) -> bytes:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n\n[linear]\nteam = "x"\n')
    return recorded(cwd=str(workspace.root))


PRE_TOOL = ("claude", "pre-tool")
UNEXPECTED: list[tuple[tuple[str, ...], Callable[[Path], bytes], int]] = [
    (PRE_TOOL, lambda _: b"\xffnot json", 1),
    (PRE_TOOL, lambda _: b"{}", 1),
    (PRE_TOOL, lambda _: recorded(hook_event_name="PostToolUse"), 1),
    (PRE_TOOL, lambda _: recorded(tool_input=None), 1),
    (("codex", "pre-tool"), lambda _: recorded(), 1),
    (("claude", "post-tool"), lambda _: recorded(), 1),
    ((), lambda _: recorded(), 1),
    (("claude",), lambda _: recorded(), 1),
    (PRE_TOOL, invalid_settings, 0),
]


@pytest.mark.parametrize(
    ("argv", "payload", "code"),
    UNEXPECTED,
    ids=[
        "not-json",
        "empty-object",
        "post-tool-use",
        "no-tool-input",
        "harness-codex",
        "event-post-tool",
        "no-harness",
        "no-event",
        "invalid-project-toml",
    ],
)
def test_the_hook_never_exits_2(
    argv: tuple[str, ...],
    payload: Callable[[Path], bytes],
    code: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert hook(monkeypatch, payload(tmp_path), *argv) == code

    out, err = capsys.readouterr()
    [line] = err.splitlines()
    assert out == ""
    assert line.startswith("devctl hook: ")


def test_an_unknown_harness_and_a_bad_usage_name_the_way_through(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    hook(monkeypatch, recorded(), "codex", "pre-tool")
    assert capsys.readouterr().err == (
        "devctl hook: unknown Harness 'codex'; this devctl wires claude only\n"
    )

    hook(monkeypatch, recorded(), "claude")
    assert capsys.readouterr().err == "devctl hook: usage: devctl hook claude pre-tool\n"

    hook(monkeypatch, b"{}", "claude", "pre-tool")
    err = capsys.readouterr().err
    assert err.startswith("devctl hook: internal error: ")
    assert err.endswith("; the tool call goes through\n")


def test_an_unreadable_directory_is_an_internal_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unreadable(path: Path) -> Path | None:
        raise PermissionError(f"[Errno 13] Permission denied: '{path}'")

    monkeypatch.setattr("devctl.hook.work_tree_root", unreadable)

    assert hook(monkeypatch, recorded(cwd=str(tmp_path)), "claude", "pre-tool") == 1
    err = capsys.readouterr().err
    assert err.startswith("devctl hook: internal error: [Errno 13] Permission denied: ")
    assert err.endswith("; the tool call goes through\n")


def test_run_hook_judges_an_edit_by_its_linked_worktree(tmp_path: Path) -> None:
    main = new_workspace(tmp_path / "main")
    main.write(".rapid-ship/project.toml", 'stack = "python"\n')
    main.write(".github/CODEOWNERS", "* @o\n")
    main.commit()
    main.git("worktree", "add", "-q", "-b", "wt", ".worktrees/wt")
    worktree = main.root / ".worktrees/wt"
    (worktree / ".github/CODEOWNERS").write_text("* @o\n# /**/AGENTS.md @o\n")

    def edit(path: Path) -> tuple[Decision, str]:
        return run_hook(ToolCall(None, (path,), main.root), unread_github)

    lock_decision, lock_reason = edit(worktree / ".rapid-ship/kit.lock")
    guide_decision, guide_reason = edit(worktree / "AGENTS.md")

    assert (lock_decision, lock_reason[:4]) == ("deny", "G4: ")
    assert (guide_decision, guide_reason[:4]) == ("ask", "G5: ")
    assert edit(main.root / "AGENTS.md") == (None, "")
