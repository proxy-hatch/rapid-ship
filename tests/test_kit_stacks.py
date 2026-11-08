"""Offline: stack options, detection and the lock's [[stack]] in scratch git repositories."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from rapid_ship.kit.git import head_commit
from rapid_ship.kit.init import init_repository
from rapid_ship.kit.stacks import (
    ProjectStack,
    StackName,
    checked_stacks,
    detect_stacks,
    parse_stack,
    proposal,
)
from rapid_ship.kit.templates import KitError


def test_a_stack_option_names_a_stack_and_a_directory() -> None:
    for option in ("python", "python=.", "python=./"):
        assert parse_stack(option) == ProjectStack("python", ".")
    assert parse_stack("python=./backend/") == ProjectStack("python", "backend")
    for option, message in (
        ("go", "the stack is python or agnostic"),
        ("python=../x", "the directory is outside the repository"),
        ("python=/x", "the directory is outside the repository"),
    ):
        with pytest.raises(KitError, match=message):
            parse_stack(option)


def test_stacks_are_checked_and_sorted(tmp_path: Path) -> None:
    backend = ProjectStack("python", "backend")
    worker = ProjectStack("python", "worker")
    assert checked_stacks(tmp_path, [worker, backend]) == (backend, worker)
    (tmp_path / "file").touch()
    (tmp_path / "link").symlink_to(tmp_path, target_is_directory=True)
    for stacks, message in (
        ([backend, backend], "given twice"),
        ([backend, ProjectStack("agnostic", ".")], "stands alone"),
        ([ProjectStack("agnostic", "app")], "directory is the root"),
        ([ProjectStack("python", "file")], "not a directory"),
        ([ProjectStack("python", "link/app")], "symlink"),
    ):
        with pytest.raises(KitError, match=message):
            checked_stacks(tmp_path, stacks)


def test_detection_finds_nested_roots_and_skips_vendored_directories(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    for directory in (
        ".",
        "services/api",
        "node_modules/x",
        ".venv/lib",
        "build",
        "dist",
        "vendor",
        "third_party",
        "venv",
        ".hidden",
    ):
        folder = git_repo / directory
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "pyproject.toml").touch()
    run_git(git_repo, "add", ".")
    run_git(git_repo, "commit", "-qm", "markers")
    (git_repo / ".gitignore").write_text("ignored/\n")
    (git_repo / "ignored").mkdir()
    (git_repo / "ignored/pyproject.toml").touch()
    (git_repo / "linked").symlink_to(git_repo / "services/api", target_is_directory=True)
    (git_repo / "extra").mkdir()
    (git_repo / "extra/pyproject.toml").touch()
    assert detect_stacks(git_repo) == [
        (ProjectStack("python", "."), ("pyproject.toml",)),
        (ProjectStack("python", "extra"), ("extra/pyproject.toml",)),
        (ProjectStack("python", "services/api"), ("services/api/pyproject.toml",)),
    ]


def test_init_without_stack_proposes_and_writes_nothing(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    before = run_git(git_repo, "status", "--porcelain")
    with pytest.raises(KitError) as caught:
        init_repository(git_repo, stacks=(), variables={})
    assert str(caught.value) == proposal([])
    assert head_commit(git_repo) is None
    assert run_git(git_repo, "status", "--porcelain") == before
    assert not run_git(git_repo, "branch", "--list", "rapid-ship/init").strip()


def test_nested_stack_rendering_is_refused_before_writing(
    git_repo: Path, run_git: Callable[..., str]
) -> None:
    from test_kit_contents import VARIABLES

    result = init_repository(
        git_repo, stacks=[ProjectStack("python", "backend")], variables=VARIABLES
    )
    assert not result.conflicts
    assert (git_repo / "backend/pyproject.toml").is_file()


def test_tracked_roots_produce_the_exact_proposal_without_writes(
    git_repo: Path,
    commit_all: Callable[..., None],
    run_git: Callable[..., str],
) -> None:
    (git_repo / "services/api").mkdir(parents=True)
    for marker in ("pyproject.toml", "services/api/pyproject.toml"):
        (git_repo / marker).touch()
    commit_all(git_repo)
    before = head_commit(git_repo)
    with pytest.raises(KitError) as caught:
        init_repository(git_repo, stacks=(), variables={})
    assert str(caught.value) == (
        "init wrote nothing: confirm the stacks first. It found these stack roots:\n"
        "  python in . (pyproject.toml)\n"
        "  python in services/api (services/api/pyproject.toml)\n"
        "Confirm them with the owner, or ask the owner for the stacks, then run init again with:\n"
        "  --stack python --stack python=services/api"
    )
    assert head_commit(git_repo) == before
    assert run_git(git_repo, "status", "--porcelain") == ""
    assert run_git(git_repo, "branch", "--list", "rapid-ship/init") == ""


def test_structured_stacks_reject_a_name_with_cli_delimiters(tmp_path: Path) -> None:
    malformed = ProjectStack(cast("StackName", "python=backend"), ".")
    with pytest.raises(KitError, match="the stack is python or agnostic"):
        checked_stacks(tmp_path, [malformed])


def test_structured_stacks_normalize_a_directory_containing_equals(tmp_path: Path) -> None:
    assert checked_stacks(tmp_path, [ProjectStack("python", "./backend=app/")]) == (
        ProjectStack("python", "backend=app"),
    )
