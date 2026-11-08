"""Offline: [[stack]] tables in fixture repositories."""

import json
from pathlib import Path

import pytest

from devctl.settings import PROJECT, ProjectSettings, ProjectStack, SettingsError, load_project


def table(name: str, directory: str = ".") -> str:
    return f'[[stack]]\nname = "{name}"\ndirectory = {json.dumps(directory)}\n'


def read(root: Path, text: str) -> ProjectSettings:
    (root / ".rapid-ship").mkdir(exist_ok=True)
    (root / PROJECT).write_text(text)
    return load_project(root)


def test_stacks_load_sorted_and_normalised(tmp_path: Path) -> None:
    for directory in ("backend", "frontend"):
        (tmp_path / directory).mkdir()
    project = read(tmp_path, table("typescript", "./frontend/") + table("python", "backend"))
    assert project.stacks == (
        ProjectStack("python", "backend"),
        ProjectStack("typescript", "frontend"),
    )
    assert read(tmp_path, table("python", "./")).stacks == (ProjectStack("python", "."),)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            'stack = "python"',
            'stack = "python" is no longer read; rewrite it as one [[stack]] '
            'table with name = "python" and directory = "."',
        ),
        ("", "[[stack]]: required; add one table for each stack, with its name and directory"),
        (
            "stack = []",
            "[[stack]]: required; add one table for each stack, with its name and directory",
        ),
        (table("go"), "#1 name: expected python or typescript or agnostic"),
        (table("python") + 'path = "x"', "#1: unknown key 'path'; it accepts directory, name"),
        ('[[stack]]\nname = "python"', "#1 directory: required"),
        *[
            (
                table("python", d),
                "#1 directory: expected a directory inside the repository that is not a symlink",
            )
            for d in ("../x", "/x", "a\\b", "missing", "link", "link/sub")
        ],
        (table("python", "backend") * 2, "two [[stack]] tables name python in backend"),
        (table("agnostic") + table("python"), "the agnostic stack cannot sit beside another stack"),
        (table("agnostic", "docs"), 'directory: the agnostic stack\'s directory is "."'),
    ],
)
def test_invalid_stacks_raise_settings_error(tmp_path: Path, text: str, message: str) -> None:
    for directory in ("backend", "docs", "real/sub"):
        (tmp_path / directory).mkdir(parents=True)
    (tmp_path / "link").symlink_to("real", target_is_directory=True)
    with pytest.raises(SettingsError) as error:
        read(tmp_path, text)
    assert message in str(error.value)


def test_owners_are_the_stacks_of_the_innermost_directory(tmp_path: Path) -> None:
    (tmp_path / "frontend").mkdir()
    (tmp_path / "backend").mkdir()
    project = read(
        tmp_path, table("python") + table("python", "frontend") + table("typescript", "frontend")
    )
    assert project.owners("frontend/src/a.ts") == (
        ProjectStack("python", "frontend"),
        ProjectStack("typescript", "frontend"),
    )
    assert project.owners("src/app/a.py") == (ProjectStack("python", "."),)
    assert project.owners("frontendish/a.py") == (ProjectStack("python", "."),)
    assert read(tmp_path, table("python", "backend")).owners("README.md") == ()
    assert read(tmp_path, table("python") + table("typescript", "frontend")).owners(
        "frontend/src/a.ts"
    ) == (ProjectStack("typescript", "frontend"),)
