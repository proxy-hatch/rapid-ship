"""Offline: Codex wiring and simulated probe replies; real shim resolution in scratch git."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from check_workspace import new_workspace
from devctl import process
from devctl.doctor_items import Item
from devctl.doctor_wiring import codex_wiring_item, codex_wiring_problems
from devctl.hook_protocols import WIRED_TOOLS
from devctl.process import run_process
from test_devctl_doctor_settings import SHIM
from test_devctl_doctor_wiring_agy import Probe, answering

COMMAND = '"$(git rev-parse --show-toplevel)/devctl" hook codex pre-tool'
WIRING = ".codex/hooks.json"
DENY = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "G2: force",
        }
    }
)


def wired(matcher: object = "Bash|apply_patch", **fields: object) -> dict[str, object]:
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": matcher,
                    "hooks": [
                        {"type": "command", "command": COMMAND, **fields},
                    ],
                }
            ]
        }
    }


SEED = wired()


@pytest.mark.parametrize("matcher", ["Bash|apply_patch", "^(Bash|apply_patch)$", ".*", "*", ""])
def test_complete_matchers(matcher: str) -> None:
    assert codex_wiring_problems(wired(matcher)) == []


@pytest.mark.parametrize("matcher", ["Bash", "apply_patch", "ash|apply_patch", "[", 3, None])
def test_incomplete_matchers(matcher: object) -> None:
    assert codex_wiring_problems(wired(matcher))


@pytest.mark.parametrize(
    "fields",
    [
        {"timeout": 359},
        {"timeout": True},
        {"timeout": "600"},
        {"timeout": None},
        {"timeout": float("inf")},
        {"timeout": float("nan")},
        {"type": "prompt"},
        {"async": True},
        {"asyncRewake": True},
        {"if": "true"},
        {"enabled": False},
        {"disabled": True},
        {"args": ["hook", "codex", "pre-tool"]},
        {"command": COMMAND.replace("codex", "agy")},
        {"command": COMMAND + "; true"},
        {"command": COMMAND + "\ntrue"},
        {"command": COMMAND.replace(" hook", "\nhook")},
        {"command": COMMAND.replace(" codex", "\ncodex")},
        {"command": COMMAND.replace(" pre-tool", "\npre-tool")},
        {"command": COMMAND.replace(" pre-tool", "\r\npre-tool")},
        {"command": COMMAND + " > result"},
        {"command": COMMAND + " --verbose"},
        {"command": "false&&" + COMMAND},
        {"command": "X=1 " + COMMAND},
        {
            "command": COMMAND.replace(
                "git rev-parse --show-toplevel", "git rev-parse --show-toplevel; true"
            )
        },
        {"command": "$(git rev-parse --show-toplevel)/devctl hook codex pre-tool"},
        {"command": "'$(git rev-parse --show-toplevel)/devctl' hook codex pre-tool"},
        {"command": '"$CLAUDE_PROJECT_DIR/devctl" hook codex pre-tool'},
        {"command": "/owner-checkout/devctl hook codex pre-tool"},
        {"command": "./devctl hook codex pre-tool"},
    ],
)
def test_invalid_handlers_are_not_probed(
    fields: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = answering(monkeypatch, DENY)
    settings = wired(**fields)
    assert codex_wiring_problems(settings)
    item = item_for(tmp_path, json.dumps(settings))
    assert item.status == "missing"
    assert probe.calls == []


@pytest.mark.parametrize(
    "settings",
    [
        [],
        {},
        {"hooks": []},
        {"hooks": {"PreToolUse": {}}},
        {**SEED, "disableAllHooks": True},
        {**SEED, "enabled": False},
        {
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": ".*",
                        "enabled": False,
                        "hooks": [
                            {"type": "command", "command": COMMAND},
                        ],
                    }
                ]
            }
        },
    ],
)
def test_invalid_or_disabled_shapes(settings: object) -> None:
    assert codex_wiring_problems(settings)


@pytest.mark.parametrize("timeout", [360, 600, 601])
def test_sufficient_timeout(timeout: int) -> None:
    assert codex_wiring_problems(wired(timeout=timeout)) == []


def item_for(root: Path, text: str | None, *, tracked: bool = True) -> Item:
    if text is not None:
        (root / ".codex").mkdir(exist_ok=True)
        (root / WIRING).write_text(text)
    return codex_wiring_item(root, [WIRING] if tracked else [])


def test_probe_command_cwd_event_and_trust_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = answering(monkeypatch, DENY)
    item = item_for(tmp_path, json.dumps(SEED))
    assert (item.area, item.name, item.status) == ("guardrails", "Codex wiring", "ok")
    assert "/hooks" in item.detail
    assert "trust" in item.detail
    assert "user" in item.detail
    [(argv, cwd, event)] = probe.calls
    assert (argv, cwd) == (["/bin/sh", "-c", COMMAND], tmp_path)
    assert event is not None
    assert json.loads(event) == {
        "hook_event_name": "PreToolUse",
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_input": {"command": "git push --force"},
    }
    assert set(WIRED_TOOLS["codex"]) == {"Bash", "apply_patch"}


@pytest.mark.parametrize(
    ("text", "tracked", "status"),
    [
        (json.dumps(SEED), False, "missing"),
        (None, True, "unknown"),
        ("{", True, "missing"),
        ('"text"', True, "missing"),
    ],
)
def test_file_status(
    text: str | None,
    tracked: bool,
    status: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = answering(monkeypatch, DENY)
    assert item_for(tmp_path, text, tracked=tracked).status == status
    assert probe.calls == []


@pytest.mark.parametrize(
    ("stdout", "code", "flags", "status"),
    [
        (DENY, 0, {}, "ok"),
        (DENY, 1, {}, "missing"),
        ("", 127, {}, "missing"),
        ("", 0, {}, "missing"),
        ("not JSON", 0, {}, "missing"),
        (DENY.replace("deny", "ask"), 0, {}, "missing"),
        (DENY.replace("G2:", "G1:"), 0, {}, "missing"),
        (DENY.replace("PreToolUse", "PostToolUse"), 0, {}, "missing"),
        ('{"decision":"deny","reason":"G2: force"}', 0, {}, "missing"),
        ("", 0, {"timed_out": True}, "unknown"),
        (DENY, 0, {"stdout_truncated": True}, "unknown"),
    ],
)
def test_probe_status(
    stdout: str,
    code: int,
    flags: dict[str, bool],
    status: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answering(monkeypatch, stdout, code, **flags)
    assert item_for(tmp_path, json.dumps(SEED)).status == status


def test_probe_cannot_start(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(process, "run_process", Probe(OSError("no shell")).run_process)
    assert item_for(tmp_path, json.dumps(SEED)).status == "unknown"


def test_command_resolves_the_linked_worktree_from_a_subdirectory(tmp_path: Path) -> None:
    workspace = new_workspace(tmp_path / "main")
    workspace.write("devctl", SHIM).chmod(0o755)
    workspace.write(".rapid-ship/project.toml", 'stack = "python"\n')
    workspace.commit()
    workspace.git("worktree", "add", "-q", "-b", "child", str(tmp_path / "child"))
    child = tmp_path / "child"
    (child / "sub").mkdir()
    # If the command selects the owner's checkout, it cannot produce a denial.
    workspace.write("devctl", "#!/bin/sh\nexit 99\n").chmod(0o755)
    event = json.dumps(
        {
            "hook_event_name": "PreToolUse",
            "cwd": str(child / "sub"),
            "tool_name": "Bash",
            "tool_input": {"command": "git push --force"},
        }
    )
    result = run_process(["/bin/sh", "-c", COMMAND], child / "sub", 30, input_text=event)
    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert item_for(child, json.dumps(SEED)).status == "ok"
