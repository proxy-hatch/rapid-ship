"""Offline: the Protected-set reader and matcher, on CODEOWNERS files written to a temporary
workspace. Nothing reads GitHub."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.codeowners import (
    FileChange,
    codeowners_match,
    ledger_entry,
    patterns_in,
    protected_changes,
    protected_patterns,
)


@pytest.mark.parametrize(
    ("pattern", "path", "matches"),
    [
        (".github/", ".github/workflows/ci.yml", True),
        (".github/", "docs/.github/x", True),
        ("/pyproject.toml", "pyproject.toml", True),
        ("/pyproject.toml", "sub/pyproject.toml", False),
        # The seeded Python set lists Ruff's settings at any depth, the way Ruff reads them.
        ("/**/ruff.toml", "ruff.toml", True),
        ("/**/ruff.toml", "src/app/ruff.toml", True),
        ("/**/ruff.toml", "src/app/ruff.toml.orig", False),
        ("docs/patterns/", "docs/patterns/settings.md", True),
        ("*.toml", "a/b.toml", True),
        ("tools/devctl/", "tools/devctl", False),
    ],
)
def test_codeowners_patterns(pattern: str, path: str, matches: bool) -> None:
    assert codeowners_match(pattern, path) is matches


def test_protected_patterns_come_from_the_file_github_reads_first(workspace: Workspace) -> None:
    workspace.write("docs/CODEOWNERS", "/docs/ @docs-owner\n")
    workspace.write(
        "CODEOWNERS",
        "# Owners: see the handbook.\n* @owner\n/api/ dev@example.com @team/api\n#/db/ @owner\n",
    )

    assert protected_patterns(workspace.root) == ["/api/", "/db/"]


def test_patterns_in_reads_owned_lines_commented_or_not() -> None:
    text = "* @o\n# /.github/ @o\n/docs/ @o @team/x\n## a heading\n# prose without an owner\n"

    assert patterns_in(text) == ["/.github/", "/docs/"]


def test_protected_changes_apply_the_ledger_rule() -> None:
    changes = [
        FileChange("docs/corrections/c1.md", "modified"),
        FileChange("docs/corrections/c2.md", "removed"),
        FileChange("docs/c3.md", "renamed", previous="docs/corrections/c3.md"),
        FileChange("docs/corrections/c4.md", "added"),
        FileChange("docs/corrections/README.md", "modified"),
        FileChange("docs/x.md", "renamed", previous=".github/x.md"),
    ]
    assert protected_changes(["/.github/"], changes) == [
        ".github/x.md",
        "docs/corrections/c1.md",
        "docs/corrections/c2.md",
        "docs/corrections/c3.md",
    ]


@pytest.mark.parametrize(
    ("path", "entry"),
    [
        ("docs/corrections/c1.md", True),
        ("docs/corrections/2026/c1.md", True),
        ("docs/corrections/sub/README.md", True),
        ("docs/corrections/README.md", False),
        ("docs/corrections/c1.txt", False),
        ("docs/corrections.md", False),
        ("sub/docs/corrections/c1.md", False),
    ],
)
def test_a_ledger_entry_is_markdown_below_the_ledger_but_its_readme(path: str, entry: bool) -> None:
    assert ledger_entry(path) is entry


def test_a_change_is_listed_once_by_each_path_a_pattern_covers() -> None:
    changes = [
        FileChange(".github/b.yml", "renamed", previous=".github/a.yml"),
        FileChange(".github/a.yml", "added"),
        FileChange("docs/corrections/c1.md", "renamed", previous="docs/corrections/c0.md"),
    ]
    assert protected_changes(["/.github/", "/docs/corrections/c1.md"], changes) == [
        ".github/a.yml",
        ".github/b.yml",
        "docs/corrections/c0.md",
        "docs/corrections/c1.md",
    ]


def test_the_ledger_readme_is_protected_through_its_codeowners_line() -> None:
    from rapid_ship.kit.stacks import ProjectStack
    from rapid_ship.kit.templates import render_files

    rendered = render_files(
        (ProjectStack("python", "."),),
        {"owner": "octo", "project_name": "demo", "package": "demo", "repository": "demo"},
        (),
    )
    content = next(item.content for item in rendered if item.path == ".github/CODEOWNERS")
    assert content is not None
    patterns = patterns_in(content.decode())
    assert protected_changes(
        patterns,
        [
            FileChange("docs/corrections/README.md", "modified"),
            FileChange("docs/corrections/2026-10-16-x-1.md", "added"),
            FileChange("docs/corrections/last-pass.toml", "modified"),
        ],
    ) == ["docs/corrections/README.md"]
