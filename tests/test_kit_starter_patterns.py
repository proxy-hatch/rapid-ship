"""Offline: a new Python project from init, checked with devctl's Pattern file checks and with
the skeleton's own check commands."""

import sys
from collections.abc import Callable
from pathlib import Path

from devctl.check.map import pattern_errors, pattern_lesson_errors
from devctl.check.stacks.python import CONTRACTS, FORMAT, LINT, TESTS, TYPES
from devctl.check.steps import CheckContext
from devctl.process import run_process
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
UV_RUN = ("uv", "run", "--locked")
# This repository's environment, which holds the tools the seed's dev group pins.
TOOLS = Path(sys.executable).parent


def test_the_python_starter_patterns_pass_the_pattern_file_checks(
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


def test_the_python_skeleton_passes_its_own_checks(
    git_repo: Path, kit_variables: dict[str, str]
) -> None:
    """devctl's format, lint, types, contracts and tests commands, with the seed's pyproject.toml
    as their settings. This repository's tools stand in for `uv run --locked`, which would sync
    the seed's environment from the network, and PYTHONPATH=src for the install it makes."""
    init_repository(git_repo, stack="python", variables=kit_variables)

    failures: list[str] = []
    for step in (FORMAT, LINT, TYPES, CONTRACTS, TESTS):
        assert step.argv[: len(UV_RUN)] == UV_RUN
        tool, *args = step.argv[len(UV_RUN) :]
        result = run_process([str(TOOLS / tool), *args], git_repo, 300, {"PYTHONPATH": "src"})
        if result.returncode != 0:
            failures.append(f"{step.name}: {result.stdout}{result.stderr}")

    assert failures == []
