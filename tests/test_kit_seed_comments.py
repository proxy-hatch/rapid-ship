"""Offline: every seed documents each key, and names every key its loader accepts."""

import re
from collections.abc import Sequence
from pathlib import Path

import pytest

from devctl.codeowners import patterns_in
from devctl.settings import EXCEPTION_KEYS, PROJECT_KEYS
from rapid_ship.kit.templates import STACKS, Stack, render_files

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "rapid_ship/templates/common/.github/workflows/devctl-check.yml"
VARIABLES = {
    "project_name": "demo-app",
    "package": "demo_app",
    "owner": "octo",
    "repository": "octo/demo-app",
}
TOML_KEY = re.compile(r'^\s*[\w."-]+\s*=')
YAML_KEY = re.compile(r"^\s*(- )?[\w-]+:")
TABLE = re.compile(r"\s*\[\[?([\w.-]+)\]\]?\s*(#.*)?")
QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'')
RUN_BLOCK = re.compile(r"^(\s*)(- )?run: [|>]")
FLIGHT_NOTE = "# Lines that start with ## stay comments in Flight."


def seed(stack: Stack, path: str) -> str:
    templates = {t.path: t for t in render_files(stack, VARIABLES, ())}
    content = templates[path].content
    assert content is not None, f"{path} is a symlink"
    return content.decode()


def has_comment(line: str) -> bool:
    """Whether a '#' outside the line's quoted strings starts a comment."""
    return re.search(r"(^|\s)#", QUOTED.sub('""', line)) is not None


def undocumented(lines: Sequence[str | None], key: re.Pattern[str]) -> list[str]:
    """Key lines with no comment on them or above the run of key lines they belong to.

    None stands for a line the rule skips, such as one inside a `run: |` block; it ends a run.
    """

    def is_key(line: str | None) -> bool:
        return line is not None and key.match(line) is not None

    missing = []
    for number, line in enumerate(lines):
        if line is None or not is_key(line) or has_comment(line):
            continue
        above = number - 1
        while above >= 0 and is_key(lines[above]):
            above -= 1
        previous = lines[above] if above >= 0 else None
        if previous is None or not previous.lstrip().startswith("#"):
            missing.append(line)
    return missing


def outside_run_blocks(text: str) -> list[str | None]:
    """The workflow's lines, with None for each line inside a `run: |` or `run: >` block."""
    lines: list[str | None] = []
    block: int | None = None  # a line deeper than this stays in the block
    for line in text.splitlines():
        depth = len(line) - len(line.lstrip())
        if block is not None and (not line.strip() or depth > block):
            lines.append(None)
            continue
        block = None
        lines.append(line)
        if started := RUN_BLOCK.match(line):
            block = len(started[1]) + len(started[2] or "")
    return lines


@pytest.mark.parametrize(
    ("stack", "path"),
    [
        ("python", ".rapid-ship/project.toml"),
        ("agnostic", ".rapid-ship/project.toml"),
        ("python", "pyproject.toml"),
    ],
)
def test_each_seeded_toml_key_has_a_comment(stack: Stack, path: str) -> None:
    lines = seed(stack, path).splitlines()

    assert any(TOML_KEY.match(line) for line in lines)
    assert undocumented(lines, TOML_KEY) == []


def test_each_ci_workflow_key_has_a_comment() -> None:
    lines = outside_run_blocks(WORKFLOW.read_text())

    assert None in lines  # the gitleaks step's run block is skipped
    assert undocumented(lines, YAML_KEY) == []


def test_the_comment_rule_finds_an_undocumented_key() -> None:
    # The rule itself: a blank line or a table header ends a run, and a quoted '#' is no comment.
    lines = ["# about a and b", "a = 1", "b = '#'", "", "c = 2", "[t]", "d = 3  # about d"]
    assert undocumented(lines, TOML_KEY) == ["c = 2"]
    block = outside_run_blocks("# about run\nrun: |\n  echo a: b\nname: x\n")
    assert block == ["# about run", "run: |", None, "name: x"]
    assert undocumented(block, YAML_KEY) == ["name: x"]


@pytest.mark.parametrize("stack", STACKS)
def test_each_protected_group_is_under_a_heading(stack: Stack) -> None:
    lines = seed(stack, ".github/CODEOWNERS").splitlines()
    owned = [number for number, line in enumerate(lines) if patterns_in(line)]

    assert owned
    for number in owned:
        above = lines[number - 1]
        assert patterns_in(above) or above.startswith("## "), lines[number]
    assert FLIGHT_NOTE in lines[: owned[0]]


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
