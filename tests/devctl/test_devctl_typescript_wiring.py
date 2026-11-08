"""Offline: Vitest diff and reference wiring in scratch git repositories."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.check.diff import DiffStep
from devctl.check.references import resolve
from devctl.check.tracked import TrackedFiles
from devctl.settings import ProjectStack

PATH = "frontend/src/a.test.tsx"
BEFORE = 'describe("a", () => { test("b", () => { render(<p>Don\'t</p>); }); });\n'
STACKS = (ProjectStack("typescript", "frontend"),)


@pytest.mark.parametrize("unit", [False, True])
def test_a_removed_vitest_test_fails_unless_declared(workspace: Workspace, unit: bool) -> None:
    workspace.write(PATH, BEFORE)
    base = workspace.commit()
    workspace.write(PATH, "")
    unit_tests = ("frontend/**",) if unit else ()
    context = workspace.context(base=base, stacks=STACKS, unit_tests=unit_tests)
    result = DiffStep().run(context)
    kind = "unit" if unit else "behavioural"
    assert result.status == "failed"
    assert any(f"removed {kind} test {PATH}::a > b: declare it" in d for d in result.details)
    body = f"## Evidence\n\nRemoved tests:\n- `{PATH}::a > b`: gone\n"
    declared = DiffStep().run(
        workspace.context(base=base, stacks=STACKS, pr_body=body, unit_tests=unit_tests)
    )
    assert declared.status == "passed"
    assert f"removed {kind} test {PATH}::a > b: declared (gone)" in declared.details
    workspace.write("frontend/src/b.spec.ts", BEFORE)
    assert DiffStep().run(context).status == "passed"


@pytest.mark.parametrize("after", ["test('unterminated", "\xff"])
def test_an_unreadable_vitest_head_keeps_base_tests(workspace: Workspace, after: str) -> None:
    workspace.write(PATH, BEFORE)
    base = workspace.commit()
    workspace.write(PATH, after)
    if after == "\xff":
        (workspace.root / PATH).write_bytes(b"\xff")
    result = DiffStep().run(workspace.context(base=base, stacks=STACKS))
    assert result.status == "failed"
    assert any(f"{PATH}: cannot read the tests at head (" in d for d in result.details)
    assert not any("removed" in d for d in result.details)


def test_dynamic_titles_produce_notes_without_removals(workspace: Workspace) -> None:
    workspace.write(
        PATH,
        'test(name, () => {});\ntest(`x ${y}`, () => {});\ntest.each(rows)("x %s", () => {});\n',
    )
    base = workspace.commit()
    workspace.write(PATH, "")
    result = DiffStep().run(workspace.context(base=base, stacks=STACKS))
    assert result.status == "passed"
    for line in (1, 2, 3):
        assert f"{PATH}:{line}: test title is not a plain string; not checked" in result.details


@pytest.mark.parametrize(
    "assertion", ["expect(x).toBe(x)", "expect( a ).toEqual(a)", "expect(true).toBeTruthy()"]
)
def test_an_added_vitest_tautology_fails(workspace: Workspace, assertion: str) -> None:
    workspace.write(PATH, 'test("a", () => { expect(x).toBe(y); });\n')
    base = workspace.commit()
    workspace.write(PATH, f'test("a", () => {{ {assertion}; }});\n')
    result = DiffStep().run(workspace.context(base=base, stacks=STACKS))
    assert result.status == "failed"
    assert any(
        f"{assertion} is always true; assert on the behaviour instead" in d for d in result.details
    )


def test_existing_vitest_tautology_and_outside_stack_files_are_not_reported(
    workspace: Workspace,
) -> None:
    source = 'test("a", () => { expect(x).toBe(x); });\n'
    workspace.write(PATH, source)
    base = workspace.commit()
    workspace.write(PATH, source + "\n")
    workspace.write("outside/a.test.ts", source)
    assert DiffStep().run(workspace.context(base=base, stacks=STACKS)).status == "passed"


@pytest.mark.parametrize("path", [PATH, "frontend/a.spec.mts", "frontend/a.test.cjs"])
def test_a_test_reference_reads_vitest_titles(workspace: Workspace, path: str) -> None:
    workspace.write(path, BEFORE)
    workspace.stage()
    context = workspace.context(stacks=STACKS)
    tracked = TrackedFiles.read(context.repo)
    assert resolve(f"test:{path}::a > b", context, tracked, "AGENTS.md") is None
    assert "has no test named" in (
        resolve(f"test:{path}::describe", context, tracked, "AGENTS.md") or ""
    )


def test_test_references_keep_python_and_word_search_readers(workspace: Workspace) -> None:
    workspace.write("tests/test_a.py", "class TestA:\n    def test_b(self): pass\n")
    workspace.write("tests/custom.txt", "named_case")
    workspace.stage()
    context = workspace.context(stacks=STACKS)
    tracked = TrackedFiles.read(context.repo)
    for value in ("tests/test_a.py::TestA::test_b", "tests/custom.txt::named_case"):
        assert resolve(f"test:{value}", context, tracked, "AGENTS.md") is None
