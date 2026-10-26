"""Offline: the root documents in fixture repositories: README.md and ARCHITECTURE.md exist at
the repository root, their local links resolve, and the root guide links both."""

from __future__ import annotations

from check_workspace import Workspace
from devctl.check.map import MapStep, root_document_errors, root_link_errors
from devctl.check.steps import StepResult

LINKS = "[README](README.md) [Architecture](ARCHITECTURE.md)\n"
BACK = "Start at [AGENTS.md](AGENTS.md).\n"
BROKEN = "ARCHITECTURE.md:1: missing target 'gone.md'; update the navigation link"
UNLINKED = "AGENTS.md: does not link README.md; add it to the Find the change table"
MISSING = (
    "README.md: missing at the repository root; restore it from git or write a new one "
    "(rapid-ship sync seeds it only while the Kit lock does not list it)"
)


def run_map(workspace: Workspace) -> StepResult:
    return MapStep().run(workspace.context(source_roots=()))


def root_document_and_link_errors(workspace: Workspace) -> tuple[list[str], list[str]]:
    context = workspace.context(source_roots=())
    root, files = context.repo.root, context.repo.files()
    return root_document_errors(root, files), root_link_errors(root, files)


def test_both_documents_linked_from_the_root_guide_pass_the_map_step(
    workspace: Workspace,
) -> None:
    workspace.write("AGENTS.md", f"# Root\n\n{LINKS}")
    workspace.write("README.md", f"# Demo\n\n{BACK}")
    workspace.write("ARCHITECTURE.md", f"# Architecture\n\n{BACK}")

    result = run_map(workspace)

    assert (result.status, result.details) == ("passed", ())


def test_a_missing_document_and_a_broken_link_are_both_reported(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", LINKS)
    workspace.write("ARCHITECTURE.md", "[Gone](gone.md)\n")

    assert root_document_and_link_errors(workspace) == (
        [MISSING],
        [BROKEN],
    )


def test_a_broken_link_in_architecture_md_fails_the_map_step(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", LINKS)
    workspace.write("README.md", BACK)
    workspace.write("ARCHITECTURE.md", "[Gone](gone.md)\n")

    result = run_map(workspace)

    assert (result.status, result.details) == ("failed", (BROKEN,))


def test_a_root_guide_without_the_links_fails_the_map_step(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", "[Architecture](ARCHITECTURE.md)\n")
    workspace.write("README.md", BACK)
    workspace.write("ARCHITECTURE.md", BACK)

    result = run_map(workspace)

    assert (result.status, result.details) == ("failed", (UNLINKED,))


def test_a_missing_document_fails_the_map_step(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", "[Architecture](ARCHITECTURE.md)\n")
    workspace.write("ARCHITECTURE.md", BACK)

    result = run_map(workspace)

    assert (result.status, result.details) == ("failed", (MISSING, UNLINKED))


def test_the_root_guide_may_link_a_document_by_any_local_form(workspace: Workspace) -> None:
    workspace.write(
        "AGENTS.md",
        "[README](./README.md#run) and [the design][design]\n\n[design]: ARCHITECTURE.md\n",
    )
    workspace.write("README.md", BACK)
    workspace.write("ARCHITECTURE.md", BACK)

    assert root_document_and_link_errors(workspace) == ([], [])


def test_a_link_that_starts_with_a_slash_resolves_against_the_repository_root(
    workspace: Workspace,
) -> None:
    workspace.write("AGENTS.md", "[README](/README.md) [Architecture](/ARCHITECTURE.md)\n")
    workspace.write("README.md", "[Guide](/AGENTS.md) ![Logo](/docs/logo.png)\n")
    workspace.write("docs/logo.png", "png\n")
    workspace.write("ARCHITECTURE.md", "[Gone](/gone.md)\n")

    assert root_document_and_link_errors(workspace) == (
        [],
        ["ARCHITECTURE.md:1: missing target '/gone.md'; update the navigation link"],
    )


def test_a_missing_root_guide_is_left_to_the_reachability_check(workspace: Workspace) -> None:
    workspace.write("README.md", "# Demo\n")
    workspace.write("ARCHITECTURE.md", "# Architecture\n")

    assert root_document_and_link_errors(workspace) == ([], [])
