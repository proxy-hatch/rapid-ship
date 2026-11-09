"""Offline: the Corrections ledger's format in fixture repositories."""

import pytest

from check_workspace import Workspace
from devctl.check import map_ledger
from devctl.check.map import MapStep
from devctl.check.map_ledger import ledger_errors
from devctl.check.references import resolve
from devctl.check.steps import CheckContext
from devctl.check.tracked import TrackedFiles
from devctl.settings import ProjectStack
from test_devctl_ledger import FILE, VALID, entry_text


def errors(workspace: Workspace) -> list[str]:
    workspace.stage()
    return ledger_errors(workspace.context(), workspace.context().repo.tracked_files())


def implemented(*references: str) -> str:
    return entry_text(
        VALID.replace("status: open", f"status: implemented\nprevented_by: {list(references)!r}")
    )


def test_a_valid_ledger_passes(workspace: Workspace) -> None:
    workspace.root_guide("# Root\n[Docs](docs/AGENTS.md)\n")
    sha = workspace.commit()
    workspace.write(FILE, entry_text())
    workspace.write("docs/corrections/second.md", entry_text())
    workspace.write("docs/corrections/README.md", "# Format\n")
    workspace.write("docs/AGENTS.md", "# Docs\n[Corrections](corrections/README.md)\n")
    workspace.write("docs/corrections/last-pass.toml", f'through = "{sha}"\ndate = 2026-10-16\n')
    workspace.stage()
    assert errors(workspace) == []
    assert MapStep().run(workspace.context(source_roots=())).status == "passed"


def test_an_invalid_entry_fails_the_map_step(workspace: Workspace) -> None:
    workspace.root_guide()
    workspace.write(FILE, entry_text(VALID.replace("by: reviewer", "by: bot")))
    workspace.stage()
    result = MapStep().run(workspace.context())
    assert result.status == "failed"
    assert any(f"{FILE}: by:" in detail for detail in result.details)


def test_prevented_by_resolves_a_reference_or_a_path(workspace: Workspace) -> None:
    workspace.write("CODEOWNERS", "# owners\n")
    workspace.write(FILE, implemented("check:map", "CODEOWNERS"))
    assert errors(workspace) == []
    workspace.write(FILE, implemented("check:nonesuch", "docs/missing.md"))
    found = errors(workspace)
    assert len(found) == 2
    assert all("or a repository path that exists" in problem for problem in found)


def test_untracked_on_disk_path_is_missing(workspace: Workspace) -> None:
    workspace.write(FILE, implemented("mechanism.txt"))
    workspace.stage()
    workspace.write("mechanism.txt", "prevention\n")
    found = ledger_errors(workspace.context(), workspace.context().repo.tracked_files())
    assert len(found) == 1
    assert "missing tracked repository path" in found[0]
    workspace.stage()
    assert errors(workspace) == []


def test_ledger_references_use_the_entry_as_holder(workspace: Workspace) -> None:
    workspace.write("backend/pyproject.toml", '[tool.ruff.lint]\nselect = ["F"]\n')
    workspace.write(FILE, implemented("ruff:F401"))
    workspace.stage()
    context = workspace.context(
        stacks=(ProjectStack("python", "backend"), ProjectStack("agnostic", "web"))
    )
    assert ledger_errors(context, context.repo.tracked_files()) == []


def test_an_ambiguous_ledger_reference_names_stacks_and_unambiguous_forms(
    workspace: Workspace,
) -> None:
    for directory in ("backend", "other"):
        workspace.write(f"{directory}/pyproject.toml", '[tool.ruff.lint]\nselect = ["F"]\n')
    workspace.write("backend/tests/test_core.py", "def test_core() -> None:\n    pass\n")
    workspace.write(FILE, implemented("ruff:F401"))
    workspace.stage()
    context = workspace.context(
        stacks=(ProjectStack("python", "backend"), ProjectStack("python", "other"))
    )
    found = ledger_errors(context, context.repo.tracked_files())
    assert len(found) == 1
    assert all(
        part in found[0]
        for part in ("backend", "other", "test:<path>::<name>", "check:<step>", "lint (backend)")
    )
    workspace.write(
        FILE, implemented("test:backend/tests/test_core.py::test_core", "check:lint (backend)")
    )
    assert ledger_errors(context, context.repo.tracked_files()) == []


def test_through_must_name_a_commit(workspace: Workspace) -> None:
    workspace.commit()
    workspace.write(
        "docs/corrections/last-pass.toml", 'through = "' + "0" * 40 + '"\ndate = 2026-10-16'
    )
    assert "through names no commit in this repository" in errors(workspace)[0]


def test_the_readme_and_other_files_are_not_entries(workspace: Workspace) -> None:
    workspace.write("docs/corrections/README.md", "No front matter")
    workspace.write("docs/corrections/notes.txt", "No front matter")
    assert errors(workspace) == []


def test_an_entry_in_a_subdirectory_is_checked(workspace: Workspace) -> None:
    workspace.write("docs/corrections/nested/a.md", "No front matter")
    assert "docs/corrections/nested/a.md:" in errors(workspace)[0]


def test_the_resolver_receives_the_tracked_object_and_entry_holder(
    workspace: Workspace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace.write("pyproject.toml", '[tool.ruff.lint]\nselect = ["F"]\n')
    workspace.write(FILE, implemented("ruff:F401"))
    workspace.stage()
    context = workspace.context()
    files = context.repo.tracked_files()
    seen: list[tuple[TrackedFiles, str]] = []

    def recording_resolve(
        reference: str,
        context: CheckContext,
        tracked: TrackedFiles,
        holder: str,
    ) -> str | None:
        seen.append((tracked, holder))
        return resolve(reference, context, tracked, holder)

    monkeypatch.setattr(map_ledger, "resolve", recording_resolve)
    assert ledger_errors(context, files) == []
    assert len(seen) == 1
    tracked, holder = seen[0]
    assert isinstance(tracked, TrackedFiles)
    assert tracked.files == tuple(files)
    assert tracked.root == workspace.root
    assert holder == FILE
