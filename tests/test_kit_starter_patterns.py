"""Offline: a new Python project from init, checked with map rule 5; no network."""

from collections.abc import Callable
from pathlib import Path

from devctl.check.map import pattern_errors, pattern_lesson_errors
from devctl.check.steps import CheckContext
from devctl.repo import Repo
from devctl.settings import load_project
from rapid_ship.kit.init import init_repository

PATTERNS = (
    "python-configuration.md",
    "python-error-handling.md",
    "python-input-validation.md",
    "python-performance.md",
)
MODULES = ("errors", "inputs", "settings", "profiling")
STARTER_FILES = (
    *(f"docs/patterns/{name}" for name in PATTERNS),
    *(f"src/demo_app/{name}.py" for name in MODULES),
    *(f"tests/test_{name}.py" for name in MODULES),
)


def test_the_python_starter_patterns_pass_map_rule_5(
    git_repo: Path, kit_variables: dict[str, str], commit_all: Callable[..., None]
) -> None:
    init_repository(git_repo, stack="python", variables=kit_variables)
    commit_all(git_repo)
    context = CheckContext(Repo.discover(git_repo), load_project(git_repo), None, None)
    files = context.repo.tracked_files()

    patterns = [path for path in files if path.startswith("docs/patterns/python-")]
    assert sorted(patterns) == [f"docs/patterns/{name}" for name in PATTERNS]
    assert pattern_errors(context, files) == []
    assert pattern_lesson_errors(context, files) == []


def test_the_starter_patterns_are_new_project_seeds_only(
    git_repo: Path, kit_variables: dict[str, str], commit_all: Callable[..., None]
) -> None:
    (git_repo / "pyproject.toml").write_text('[project]\nname = "ours"\n')
    commit_all(git_repo)

    init_repository(git_repo, stack=None, variables=kit_variables)

    assert [path for path in STARTER_FILES if (git_repo / path).exists()] == []
    assert (git_repo / "docs/patterns/README.md").is_file()
