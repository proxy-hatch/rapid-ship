"""Offline: every seed names every key its loader accepts."""

import re

import pytest

from devctl.settings import EXCEPTION_KEYS, PROJECT_KEYS
from rapid_ship.kit.templates import STACKS, Stack, render_files

VARIABLES = {
    "project_name": "demo-app",
    "package": "demo_app",
    "owner": "octo",
    "repository": "octo/demo-app",
}
TABLE = re.compile(r"\s*\[\[?([\w.-]+)\]\]?\s*(#.*)?")


def seed(stack: Stack, path: str) -> str:
    templates = {t.path: t for t in render_files(stack, VARIABLES, ())}
    content = templates[path].content
    assert content is not None, f"{path} is a symlink"
    return content.decode()


def table_keys(text: str) -> set[tuple[str, str]]:
    """Each (table, key) of a TOML text's key lines; "" is the top level, which holds the tables."""
    found: set[tuple[str, str]] = set()
    table = ""
    for line in text.splitlines():
        if header := TABLE.fullmatch(line):
            table = header[1]
            found.add(("", table))
        elif key := re.match(r"\s*([\w-]+)\s*=", line):
            found.add((table, key[1]))
    return found


@pytest.mark.parametrize("stack", STACKS)
def test_each_seed_names_every_key_its_loader_accepts(stack: Stack) -> None:
    accepted = {(table, key) for table, keys in PROJECT_KEYS.items() for key in keys}

    assert table_keys(seed(stack, ".rapid-ship/project.toml")) == accepted
    example = seed(stack, ".rapid-ship/exceptions.toml").splitlines()
    for key in EXCEPTION_KEYS:
        assert any(line.startswith(f"# {key} = ") for line in example), key
