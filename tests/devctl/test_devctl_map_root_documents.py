"""Offline: map rule 8 in fixture repositories."""

from __future__ import annotations

import pytest

import devctl
from check_workspace import Workspace
from devctl.check.map import MapStep, root_document_errors, root_link_errors
from devctl.check.steps import StepResult

LINKS = "[README](README.md) [Architecture](ARCHITECTURE.md)\n"
BACK = "Start at [AGENTS.md](AGENTS.md).\n"
BROKEN = "ARCHITECTURE.md:1: missing target 'gone.md'; update the navigation link"
UNLINKED = "AGENTS.md: does not link README.md; add it to the Find the change table"
GRACE = "; this fails from the next Kit version"
MISSING = (
    "README.md: missing at the repository root; restore it from git or write a new one "
    "(rapid-ship sync seeds it only while the Kit lock does not list it)"
)


def run_map(workspace: Workspace, monkeypatch: pytest.MonkeyPatch, version: str) -> StepResult:
    """The map step as devctl `version` runs it."""
    monkeypatch.setattr(devctl, "__version__", version)
    return MapStep().run(workspace.context(source_roots=()))


def rule_8(workspace: Workspace) -> tuple[list[str], list[str]]:
    context = workspace.context(source_roots=())
    root, files = context.repo.root, context.repo.files()
    return root_document_errors(root, files), root_link_errors(root, files)


def test_rule_8_passes_with_both_documents_linked_from_the_root_guide(
    workspace: Workspace,
) -> None:
    workspace.write("AGENTS.md", f"# Root\n\n{LINKS}")
    workspace.write("README.md", f"# Demo\n\n{BACK}")
    workspace.write("ARCHITECTURE.md", f"# Architecture\n\n{BACK}")

    result = MapStep().run(workspace.context(source_roots=()))

    assert (result.status, result.details) == ("passed", ())


def test_rule_8_reports_a_missing_document_and_a_broken_link(workspace: Workspace) -> None:
    workspace.write("AGENTS.md", LINKS)
    workspace.write("ARCHITECTURE.md", "[Gone](gone.md)\n")

    assert rule_8(workspace) == (
        [MISSING],
        [BROKEN],
    )


def test_a_broken_link_in_architecture_md_warns_in_kit_0_2_0_and_fails_after(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace.write("AGENTS.md", LINKS)
    workspace.write("README.md", BACK)
    workspace.write("ARCHITECTURE.md", "[Gone](gone.md)\n")

    warned = run_map(workspace, monkeypatch, "0.2.0")
    failed = run_map(workspace, monkeypatch, "0.3.0")

    assert (warned.status, warned.details) == ("passed", (f"warning: {BROKEN}{GRACE}",))
    assert (failed.status, failed.details) == ("failed", (BROKEN,))


def test_a_root_guide_without_the_links_warns_in_kit_0_2_0_and_fails_after(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace.write("AGENTS.md", "[Architecture](ARCHITECTURE.md)\n")
    workspace.write("README.md", BACK)
    workspace.write("ARCHITECTURE.md", BACK)

    warned = run_map(workspace, monkeypatch, "0.2.0")
    failed = run_map(workspace, monkeypatch, "0.3.0")

    assert (warned.status, warned.details) == ("passed", (f"warning: {UNLINKED}{GRACE}",))
    assert (failed.status, failed.details) == ("failed", (UNLINKED,))


def test_a_missing_document_fails_at_once_in_kit_0_2_0(
    workspace: Workspace, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace.write("AGENTS.md", "[Architecture](ARCHITECTURE.md)\n")
    workspace.write("ARCHITECTURE.md", BACK)

    result = run_map(workspace, monkeypatch, "0.2.0")

    assert (result.status, result.details) == (
        "failed",
        (MISSING, f"warning: {UNLINKED}{GRACE}"),
    )


def test_the_root_guide_may_link_a_document_by_any_local_form(workspace: Workspace) -> None:
    workspace.write(
        "AGENTS.md",
        "[README](./README.md#run) and [the design][design]\n\n[design]: ARCHITECTURE.md\n",
    )
    workspace.write("README.md", BACK)
    workspace.write("ARCHITECTURE.md", BACK)

    assert rule_8(workspace) == ([], [])


def test_a_link_that_starts_with_a_slash_resolves_against_the_repository_root(
    workspace: Workspace,
) -> None:
    workspace.write("AGENTS.md", "[README](/README.md) [Architecture](/ARCHITECTURE.md)\n")
    workspace.write("README.md", "[Guide](/AGENTS.md) ![Logo](/docs/logo.png)\n")
    workspace.write("docs/logo.png", "png\n")
    workspace.write("ARCHITECTURE.md", "[Gone](/gone.md)\n")

    assert rule_8(workspace) == (
        [],
        ["ARCHITECTURE.md:1: missing target '/gone.md'; update the navigation link"],
    )


def test_without_a_root_guide_rule_8_leaves_the_report_to_rule_3(workspace: Workspace) -> None:
    workspace.write("README.md", "# Demo\n")
    workspace.write("ARCHITECTURE.md", "# Architecture\n")

    assert rule_8(workspace) == ([], [])
