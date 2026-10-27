"""Offline: agy's hook protocol, from events agy 1.4.7 sent; no Session runs."""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from check_workspace import Workspace, new_workspace
from devctl import cli
from devctl.hook import decide
from devctl.hook_protocols import WIRED_TOOLS, ToolCall, answer, read_event
from devctl.merge_guard import LocalBranches

FIXTURES = Path(__file__).parent / "fixtures" / "hooks" / "agy"
CLAUDE_FIXTURES = Path(__file__).parent / "fixtures" / "hooks" / "claude"
REPO = Path("/repo")
PYTHON = 'stack = "python"\n'
INVALID = 'stack = "python"\n\n[linear]\nteam = "x"\n'
IDENTITY = (
    'stack = "python"\n\n[github]\nrepository = "o/r"\n'
    'worker_app_id = 1\nworker_app_slug = "o-worker"\n'
    'reviewer_app_id = 2\nreviewer_app_slug = "o-reviewer"\n'
)


def recorded(name: str = "run-command.json", **changes: object) -> bytes:
    """A recorded event with top-level keys replaced; a value of None removes the key."""
    event = json.loads((FIXTURES / name).read_text())
    for key, value in changes.items():
        if value is None:
            event.pop(key)
        else:
            event[key] = value
    return json.dumps(event).encode()


def calling(tool: str, workspace: Path = REPO, **args: object) -> bytes:
    """A recorded event whose toolCall is tool with args, in workspace."""
    return recorded(toolCall={"args": args, "name": tool}, workspacePaths=[str(workspace)])


def project(tmp_path: Path, settings: str = PYTHON) -> Workspace:
    workspace = new_workspace(tmp_path / "main")
    workspace.write(".rapid-ship/project.toml", settings)
    return workspace


def hook(monkeypatch: pytest.MonkeyPatch, payload: bytes, *argv: str) -> int:
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(payload)))
    return cli.main(["hook", *argv])


def one_answer(out: str) -> dict[str, object]:
    assert out.count("\n") == 1
    assert out.endswith("\n")
    parsed = json.loads(out)
    assert isinstance(parsed, dict)
    return parsed


def unread() -> LocalBranches:
    raise AssertionError("local git was read")


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("run-command.json", ToolCall("git status", (), REPO)),
        ("run-command-subagent.json", ToolCall("git status", (), REPO)),
        ("write-file.json", ToolCall(None, (REPO / "spike.txt",), REPO)),
        ("edit-file.json", ToolCall(None, (REPO / "spike.txt",), REPO)),
        ("invoke-subagent.json", ToolCall(None, (), REPO)),
    ],
)
def test_read_event_normalises_each_recorded_agy_event(name: str, expected: ToolCall) -> None:
    assert read_event("agy", (FIXTURES / name).read_bytes()) == expected


@pytest.mark.parametrize("tool", ["read_file", "send_message"])
def test_a_tool_the_hook_does_not_wire_gives_an_empty_call(tool: str) -> None:
    payload = calling(tool, Path="/repo/spike.txt")
    assert read_event("agy", payload) == ToolCall(None, (), REPO)


def test_a_relative_path_is_resolved_against_the_first_workspace_path() -> None:
    event = json.loads(calling("write_file", Path="sub/../a.txt", Content="x"))
    event["workspacePaths"] = ["/repo/", "/other"]

    assert read_event("agy", json.dumps(event).encode()) == ToolCall(None, (REPO / "a.txt",), REPO)


@pytest.mark.parametrize(
    ("cwd", "expected"),
    [("sub/../other", REPO / "other"), ("/elsewhere", Path("/elsewhere")), ("", REPO)],
    ids=["relative", "absolute", "empty"],
)
def test_a_cwd_argument_resolves_against_the_first_workspace_path(cwd: str, expected: Path) -> None:
    call = read_event("agy", calling("run_command", CommandLine="git status", Cwd=cwd))

    assert call == ToolCall("git status", (), expected)


@pytest.mark.parametrize("tool", WIRED_TOOLS["agy"])
def test_every_wired_agy_tool_is_read_into_a_call_a_rule_can_match(tool: str) -> None:
    call = read_event("agy", calling(tool, CommandLine="git status", Path="/repo/x.txt"))

    assert call.shell is not None or call.edits


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"\xffnot json", id="not-json"),
        pytest.param(b"[]", id="not-an-object"),
        pytest.param(recorded(toolCall=None), id="no-tool-call"),
        pytest.param(recorded(toolCall="run_command"), id="tool-call-not-an-object"),
        pytest.param(recorded(toolCall={"args": {}}), id="no-name"),
        pytest.param(recorded(toolCall={"name": "run_command", "args": []}), id="args-not-object"),
        pytest.param(calling("run_command", toolSummary="x"), id="run-command-no-command-line"),
        pytest.param(calling("write_file", Content="x"), id="write-file-no-path"),
        pytest.param(calling("edit_file", Path=3), id="edit-file-path-not-a-string"),
        pytest.param(
            calling("run_command", CommandLine="git status", Cwd=3), id="cwd-not-a-string"
        ),
        pytest.param(recorded(workspacePaths=None), id="no-workspace-paths"),
        pytest.param(recorded(workspacePaths=[]), id="empty-workspace-paths"),
        pytest.param(recorded(workspacePaths=["repo"]), id="relative-workspace-path"),
    ],
)
def test_a_malformed_agy_event_is_a_value_error(payload: bytes) -> None:
    with pytest.raises(ValueError, match=r"."):
        read_event("agy", payload)


def test_an_agy_answer_is_one_json_line_with_exit_0() -> None:
    assert answer("agy", "deny", "G1: why") == ('{"decision": "deny", "reason": "G1: why"}\n', 0)
    assert answer("agy", None, "") == ('{"decision": "allow"}\n', 0)


# The tool, its arguments, project.toml, and the answer's decision and reason prefix. A relative
# Path resolves against the workspace.
RULES = [
    pytest.param("run_command", {"CommandLine": "git commit -n -m x"}, PYTHON, "G1: ", id="G1"),
    pytest.param(
        "run_command", {"CommandLine": "git push --force origin t"}, PYTHON, "G2: ", id="G2"
    ),
    pytest.param(
        "run_command", {"CommandLine": "git push origin HEAD:main"}, PYTHON, "G3: ", id="G3"
    ),
    pytest.param("write_file", {"Path": ".rapid-ship/kit.lock"}, PYTHON, "G4: ", id="G4-write"),
    pytest.param("edit_file", {"Path": ".rapid-ship/kit.lock"}, PYTHON, "G4: ", id="G4-edit"),
    pytest.param("run_command", {"CommandLine": "git push origin t"}, IDENTITY, "G7: ", id="G7"),
    pytest.param("run_command", {"CommandLine": "gh pr create --fill"}, IDENTITY, "G8: ", id="G8"),
    pytest.param(
        "run_command",
        {"CommandLine": "gh pr merge 1 --squash"},
        INVALID,
        "merge denied: the merge guard cannot check this merge: ",
        id="merge-guard",
    ),
]


@pytest.mark.parametrize(("tool", "args", "settings", "prefix"), RULES)
def test_each_rule_decides_through_the_agy_protocol(
    tool: str,
    args: dict[str, object],
    settings: str,
    prefix: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path, settings)

    code = hook(monkeypatch, calling(tool, workspace.root, **args), "agy", "pre-tool")

    output = one_answer(capsys.readouterr().out)
    assert code == 0
    assert output["decision"] == "deny"
    assert str(output["reason"]).startswith(prefix)


def test_a_command_is_judged_in_the_repository_that_holds_its_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    other = new_workspace(tmp_path / "other")
    other.write(".rapid-ship/project.toml", IDENTITY)
    payload = calling(
        "run_command", project(tmp_path).root, CommandLine="git push origin t", Cwd=str(other.root)
    )

    assert hook(monkeypatch, payload, "agy", "pre-tool") == 0
    assert str(one_answer(capsys.readouterr().out)["reason"]).startswith("G7: ")


def test_a_harmless_agy_call_gets_allow_and_no_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = project(tmp_path)

    payload = calling("run_command", workspace.root, CommandLine="git status")
    code = hook(monkeypatch, payload, "agy", "pre-tool")

    assert code == 0
    assert capsys.readouterr() == ('{"decision": "allow"}\n', "")


def test_g5_does_not_run_for_agy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = project(tmp_path)
    workspace.write(".github/CODEOWNERS", "* @o\n# /**/AGENTS.md @o\n")
    claude = json.loads((CLAUDE_FIXTURES / "write.json").read_text())
    claude.update(cwd=str(workspace.root), tool_input={"file_path": "AGENTS.md", "content": "x"})

    agy_code = hook(
        monkeypatch, calling("write_file", workspace.root, Path="AGENTS.md"), "agy", "pre-tool"
    )
    agy_out = capsys.readouterr().out
    claude_code = hook(monkeypatch, json.dumps(claude).encode(), "claude", "pre-tool")
    claude_out = json.loads(capsys.readouterr().out)["hookSpecificOutput"]

    assert (agy_code, agy_out) == (0, '{"decision": "allow"}\n')
    assert (claude_code, claude_out["permissionDecision"]) == (0, "ask")
    assert claude_out["permissionDecisionReason"].startswith("G5: ")


def test_without_the_protected_ask_g4_still_denies() -> None:
    def edit(path: str) -> tuple[object, str]:
        call = ToolCall(None, (REPO / path,), REPO)
        return decide(call, REPO, None, unread, protected_ask=False)

    decision, reason = edit(".rapid-ship/kit.lock")

    assert (decision, reason[:4]) == ("deny", "G4: ")
    assert edit("AGENTS.md") == (None, "")


def raise_inside_the_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: object, **kwargs: object) -> tuple[None, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr("devctl.hook.decide", broken)


def invalid_settings_call(tmp_path: Path) -> bytes:
    return calling("run_command", project(tmp_path, INVALID).root, CommandLine="git status")


# argv after hook, the payload, and whether devctl failed, so that the answer is a deny whose reason
# is the stderr line.
FAILURES: list[tuple[tuple[str, ...], Callable[[Path], bytes], bool]] = [
    (("agy", "pre-tool"), lambda _: b"\xffnot json", True),
    (("agy", "pre-tool"), lambda _: b"[]", True),
    (("agy", "pre-tool"), lambda _: recorded(toolCall=None), True),
    (("agy", "pre-tool"), lambda _: recorded(workspacePaths=None), True),
    (("agy", "pre-tool"), lambda _: calling("run_command", toolSummary="x"), True),
    (("agy",), lambda _: recorded(), True),
    (("agy", "post-tool"), lambda _: recorded(), True),
    # Invalid settings switch G5, G7 and G8 off; the call itself still gets an answer.
    (("agy", "pre-tool"), lambda tmp: invalid_settings_call(tmp), False),
]


@pytest.mark.parametrize(
    ("argv", "payload", "failed"),
    FAILURES,
    ids=[
        "not-json",
        "not-an-object",
        "no-tool-call",
        "no-workspace-paths",
        "no-command-line",
        "no-event",
        "event-post-tool",
        "invalid-project-toml",
    ],
)
def test_the_agy_hook_always_exits_0_with_a_decision(
    argv: tuple[str, ...],
    payload: Callable[[Path], bytes],
    failed: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert hook(monkeypatch, payload(tmp_path), *argv) == 0

    out, err = capsys.readouterr()
    [line] = err.splitlines()
    assert line.startswith("devctl hook: ")
    denied = {"decision": "deny", "reason": line}
    assert one_answer(out) == (denied if failed else {"decision": "allow"})


def test_an_exception_inside_the_rules_denies_the_agy_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raise_inside_the_rules(monkeypatch)

    payload = calling("run_command", project(tmp_path).root, CommandLine="git status")
    assert hook(monkeypatch, payload, "agy", "pre-tool") == 0

    reason = "devctl hook: internal error: boom; devctl hook denies the call until this is fixed"
    assert capsys.readouterr() == (
        json.dumps({"decision": "deny", "reason": reason}) + "\n",
        reason + "\n",
    )


def test_a_usage_error_names_the_agy_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert hook(monkeypatch, recorded(), "agy") == 0

    reason = "devctl hook: usage: devctl hook agy pre-tool"
    assert capsys.readouterr() == (
        json.dumps({"decision": "deny", "reason": reason}) + "\n",
        reason + "\n",
    )
