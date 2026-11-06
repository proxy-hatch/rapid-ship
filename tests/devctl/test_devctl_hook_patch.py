"""Offline simulations of Codex patches, including forms absent from recorded events."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from devctl.hook_protocols import read_event
from test_devctl_hook_agy import INVALID, PYTHON, project
from test_devctl_hook_codex import REPO, calling
from test_devctl_hook_protocol import hook


def patch(body: str) -> str:
    return f"*** Begin Patch\n{body}\n*** End Patch\n"


@pytest.mark.parametrize("wrapper", ["", "<<EOF", "<<'EOF'", '<<"EOF"'])
@pytest.mark.parametrize(
    "metadata",
    ["*** Environment ID: local", "  *** Environment ID: local  ", "*** Environment ID:local"],
)
def test_environment_metadata_does_not_hide_lock_operations(
    wrapper: str,
    metadata: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path)
    command = patch(
        metadata + "\n*** Add File: harmless\n+x\n*** Delete File: .rapid-ship/kit.lock"
    )
    if wrapper:
        command = f"{wrapper}\n{command}EOF"

    assert (
        hook(monkeypatch, calling(command, workspace.root, "apply_patch"), "codex", "pre-tool") == 0
    )
    result = capsys.readouterr()
    assert result.err == ""
    decision = json.loads(result.out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"].startswith("G4: ")


@pytest.mark.parametrize("wrapper", ["", "<<EOF", "<<'EOF'", '<<"EOF"'])
@pytest.mark.parametrize(
    "body",
    [
        "*** Delete File: .rapid-ship/kit.lock  ",
        "  *** Delete File: .rapid-ship/kit.lock",
        "*** Add File: harmless\n+x\n  *** Delete File: .rapid-ship/kit.lock  ",
        "*** Update File: harmless\n@@\n-x\n+y\n*** Delete File: .rapid-ship/kit.lock  ",
        "*** Update File: harmless\n*** Move to: .rapid-ship/kit.lock  \n@@\n-x\n+y",
        "*** Update File: .rapid-ship/kit.lock  \n@@\n-x\n+y",
        "*** Begin Patch  \n*** Update File: .rapid-ship/kit.lock\n@@\n-x\n+y\n  *** End Patch",
        "*** Update File: .rapid-ship/kit.lock\n@@\n-x\n+y\n*** End of File  \n@@\n-a\n+b",
    ],
)
def test_lock_denial_uses_the_tool_header_whitespace_and_eof_wrappers(
    wrapper: str,
    body: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path)
    command = body + "\n" if body.startswith("*** Begin Patch") else patch(body)
    if wrapper:
        command = f"{wrapper}\n{command}EOF"

    assert (
        hook(monkeypatch, calling(command, workspace.root, "apply_patch"), "codex", "pre-tool") == 0
    )
    result = capsys.readouterr()
    assert result.err == ""
    decision = json.loads(result.out)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert decision["permissionDecisionReason"].startswith("G4: ")


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_all_patch_paths_are_normalised_and_content_is_not_a_header(newline: str) -> None:
    body = (
        "*** Add File: new file.txt\n+*** Delete File: not-a-path\n"
        "*** Update File: ../old file.txt\n*** Move to: /repo/sub/../moved file.txt\n"
        "@@ heading\n *** Add File: context-only\n-*** Update File: removed-only\n"
        "+*** Move to: added-only\n*** End of File\n"
        "*** Delete File: ../deleted.txt\n*** Update File: ../last.txt\n@@\n-a\n+b"
    )
    call = read_event(
        "codex", calling(patch(body).replace("\n", newline), REPO / "sub", "apply_patch")
    )
    assert call.shell is None
    assert call.edits == tuple(
        REPO / path
        for path in (
            "sub/new file.txt",
            "old file.txt",
            "moved file.txt",
            "deleted.txt",
            "last.txt",
        )
    )


@pytest.mark.parametrize(
    "body",
    [
        "*** Add File: .rapid-ship/kit.lock\n+x",
        "*** Update File: .rapid-ship/kit.lock\n@@\n-x\n+y",
        "*** Delete File: .rapid-ship/kit.lock",
        "*** Update File: .rapid-ship/kit.lock\n*** Move to: other\n@@\n-x\n+y",
        "*** Update File: other\n*** Move to: sub/../.rapid-ship/kit.lock\n@@\n-x\n+y",
    ],
)
@pytest.mark.parametrize("settings", [PYTHON, INVALID])
def test_each_lock_operation_is_denied_after_a_harmless_operation(
    body: str,
    settings: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path, settings)
    command = patch("*** Add File: harmless\n+x\n" + body)
    assert (
        hook(monkeypatch, calling(command, workspace.root, "apply_patch"), "codex", "pre-tool") == 0
    )
    result = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert result["permissionDecision"] == "deny"
    assert result["permissionDecisionReason"].startswith("G4: ")


@pytest.mark.parametrize(
    "body",
    [
        "",
        "arbitrary text",
        "*** Move to: destination",
        "*** Add File: ",
        "*** Add File: x\nnot-prefixed",
        "*** Delete File: x\n+content",
        "*** Update File: x",
        "*** Update File: x\n*** Move to: y",
        "*** Update File: x\n@@\n???",
        "*** Update File: x\n@@",
        "*** Update File: x\n@@\n+x\n*** Move to: y",
        "*** Add File: x\n+x\n*** Bogus File: y",
        "*** Environment ID:\n*** Delete File: x",
        "*** Environment ID: local\n*** Environment ID: local\n*** Delete File: x",
        "*** Add File: x\n+x\n*** Environment ID: local\n*** Delete File: y",
    ],
)
def test_malformed_patch_is_not_an_empty_call(body: str) -> None:
    with pytest.raises(ValueError, match="patch"):
        read_event("codex", calling(patch(body), tool="apply_patch"))


@pytest.mark.parametrize(
    "command",
    [
        "hello",
        "*** Begin Patch\n*** Delete File: x",
        "*** Delete File: x\n*** End Patch",
        "*** Begin Patch\n*** Delete File: x\n*** End Patch\nignored",
    ],
)
def test_patch_boundaries_are_required(command: str) -> None:
    with pytest.raises(ValueError, match="patch"):
        read_event("codex", calling(command, tool="apply_patch"))


def test_later_paths_are_judged_in_their_own_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = project(tmp_path)
    command = patch(f"*** Add File: {tmp_path}/outside\n+x\n*** Delete File: .rapid-ship/kit.lock")
    assert (
        hook(monkeypatch, calling(command, workspace.root, "apply_patch"), "codex", "pre-tool") == 0
    )
    assert json.loads(capsys.readouterr().out)["hookSpecificOutput"]["permissionDecision"] == "deny"
