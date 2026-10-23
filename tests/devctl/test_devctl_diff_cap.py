"""Offline: the diff cap in fixture repositories."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.check.diff import DiffStep
from devctl.check.steps import StepResult

NO_CODEOWNERS = "no CODEOWNERS file; Protected paths are not listed"
NO_BODY = " (pass --pr-body <file> to check a body locally)"
OVER = (
    "the change adds and removes 1501 counted lines, over the 1,500-line diff cap; split it, or, "
    "once the owner accepts the overage, add 'Over the diff cap: <reason>' to the PR's Evidence "
    "section"
)
EVIDENCE = "## Evidence\n\n- `uv run pytest`: 12 passed\n\n{line}\n\nNot covered: Windows.\n"
MANAGED = "tools/devctl/devctl/vendored.py"
LOCK = (
    'kit_version = "0.2.0"\nstack = "python"\n\n[[file]]\n'
    f'path = "{MANAGED}"\nkind = "managed"\nsha256 = "{"a" * 64}"\n'
)
# 2,000 bytes with a NUL in the first 8,000, which Git reads as binary, and 1,600 newlines.
BINARY = b"\0" + b"\n" * 1600 + b"x" * 399


def lines(count: int) -> str:
    return "".join(f"value_{index} = {index}\n" for index in range(count))


def note(count: int) -> str:
    return f"diff cap: {count} of 1,500 counted lines"


def big_change(
    workspace: Workspace, count: int, *, body: str | None = None, stack: str = "python"
) -> StepResult:
    base = workspace.commit()
    workspace.write("src/app/big.py", lines(count))
    return DiffStep().run(workspace.context(base=base, pr_body=body, stack=stack))


def test_exactly_1500_counted_lines_pass(workspace: Workspace) -> None:
    assert big_change(workspace, 1500) == StepResult("diff", "passed", (NO_CODEOWNERS, note(1500)))


def test_1501_counted_lines_fail_and_name_the_declaration(workspace: Workspace) -> None:
    assert big_change(workspace, 1501) == StepResult(
        "diff", "failed", (OVER + NO_BODY, NO_CODEOWNERS, note(1501))
    )


def test_a_declared_overage_passes_with_a_note(workspace: Workspace) -> None:
    body = EVIDENCE.format(line="Over the diff cap: a generated parser")

    assert big_change(workspace, 1501, body=body) == StepResult(
        "diff",
        "passed",
        (NO_CODEOWNERS, "diff cap: 1501 counted lines, over 1,500, declared: a generated parser"),
    )


@pytest.mark.parametrize(
    "body",
    [
        EVIDENCE.format(line="") + "## Notes\n\nOver the diff cap: a generated parser\n",
        EVIDENCE.format(line="Over the diff cap:"),
    ],
    ids=["under-notes", "no-reason"],
)
def test_a_declaration_outside_evidence_or_without_a_reason_does_not_count(
    workspace: Workspace, body: str
) -> None:
    assert big_change(workspace, 1501, body=body) == StepResult(
        "diff", "failed", (OVER, NO_CODEOWNERS, note(1501))
    )


@pytest.mark.parametrize(
    "path",
    [
        "docs/a.md",
        "notes.txt",
        "run.log",
        "assets/logo.bin",
        MANAGED,
        ".rapid-ship/kit.lock",
        "uv.lock",
        "frontend/package-lock.json",
    ],
)
@pytest.mark.parametrize("tracked", [True, False], ids=["changed", "untracked"])
def test_excluded_files_do_not_count(workspace: Workspace, path: str, tracked: bool) -> None:
    if tracked:
        workspace.write(path, "seed\n")
    base = workspace.commit()
    # An untracked lock records MANAGED; for the lock's own case the next write replaces it.
    workspace.write(".rapid-ship/kit.lock", LOCK)
    target = workspace.root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(BINARY if path.endswith(".bin") else lines(1600).encode())

    assert DiffStep().run(workspace.context(base=base)) == StepResult(
        "diff", "passed", (NO_CODEOWNERS, note(0))
    )


def test_without_a_readable_lock_kit_files_count(workspace: Workspace) -> None:
    base = workspace.commit()
    workspace.write(MANAGED, lines(1501))

    assert DiffStep().run(workspace.context(base=base)).details[0] == OVER + NO_BODY


def test_untracked_files_count(workspace: Workspace) -> None:
    workspace.write(".gitignore", "build/\n")
    workspace.write("src/app/edited.py", "")
    base = workspace.commit()
    workspace.write("src/app/edited.py", lines(1000))
    workspace.write("src/app/new.py", lines(501))
    workspace.write("build/generated.py", lines(5000))  # ignored, so not counted

    result = DiffStep().run(workspace.context(base=base))

    assert (result.status, result.details[-1]) == ("failed", note(1501))


def test_added_and_removed_lines_both_count(workspace: Workspace) -> None:
    workspace.write("src/app/old.py", lines(1499))
    workspace.write("src/app/edited.py", "a = 1\n")
    base = workspace.commit()
    (workspace.root / "src/app/old.py").unlink()
    workspace.write("src/app/edited.py", "a = 2\n")

    result = DiffStep().run(workspace.context(base=base))

    assert (result.status, result.details[-1]) == ("failed", note(1501))


def test_the_cap_applies_to_the_agnostic_stack(workspace: Workspace) -> None:
    assert big_change(workspace, 1501, stack="agnostic") == StepResult(
        "diff", "failed", (OVER + NO_BODY, NO_CODEOWNERS, note(1501))
    )
