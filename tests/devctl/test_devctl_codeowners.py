"""Offline: the Protected-set reader and matcher, on CODEOWNERS files written to a temporary
workspace. Nothing reads GitHub."""

from __future__ import annotations

import pytest

from check_workspace import Workspace
from devctl.codeowners import codeowners_match, patterns_in, protected_patterns


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
