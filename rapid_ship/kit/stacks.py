"""Stack options and read-only detection of project roots."""

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import groupby
from pathlib import Path
from typing import Literal

from rapid_ship.files import UnsafePath, relative_parts, safe_path

StackName = Literal["python", "agnostic"]
STACKS: tuple[StackName, ...] = ("python", "agnostic")
SKIPPED = frozenset(
    {"node_modules", "venv", "dist", "build", "vendor", "third_party", "__pycache__"}
)


@dataclass(frozen=True)
class ProjectStack:
    name: StackName
    directory: str


def under(directory: str, path: str) -> str:
    return path if directory == "." else f"{directory}/{path}"


def parse_stack(option: str) -> ProjectStack:
    from rapid_ship.kit.templates import KitError

    name, separator, directory = option.partition("=")
    if name not in STACKS:
        raise KitError(f"--stack {option}: the stack is {' or '.join(STACKS)}")
    directory = directory if separator else "."
    try:
        directory = "." if directory in (".", "./") else "/".join(relative_parts(directory))
    except UnsafePath as error:
        raise KitError(f"--stack {option}: the directory is outside the repository") from error
    return ProjectStack(name, directory)


def checked_stacks(root: Path, stacks: Sequence[ProjectStack]) -> tuple[ProjectStack, ...]:
    from rapid_ship.kit.templates import KitError

    for stack in stacks:
        if stack.name not in STACKS:
            raise KitError(f"--stack {stack.name}: the stack is {' or '.join(STACKS)}")
    result = tuple(
        sorted(
            (parse_stack(f"{s.name}={s.directory}") for s in stacks),
            key=lambda s: (s.directory, s.name),
        )
    )
    seen: set[ProjectStack] = set()
    for stack in result:
        option = f"--stack {stack.name}={stack.directory}"
        if stack in seen:
            raise KitError(f"{option} is given twice")
        seen.add(stack)
        if stack.name == "agnostic":
            if len(result) != 1:
                raise KitError("the agnostic stack stands alone; remove the other --stack options")
            if stack.directory != ".":
                raise KitError(f"{option}: the agnostic stack's directory is the root")
        _check_directory(root, stack.directory, option)
    return result


def _check_directory(root: Path, directory: str, option: str) -> None:
    from rapid_ship.kit.templates import KitError

    try:
        path = root if directory == "." else safe_path(root, directory)
    except UnsafePath as error:
        raise KitError(str(error)) from error
    if path.exists() and not path.is_dir():
        raise KitError(f"{option}: not a directory")


def detect_stacks(root: Path) -> list[tuple[ProjectStack, tuple[str, ...]]]:
    from rapid_ship.kit.git import git

    found: set[str] = set()
    for raw in git(root, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(
        b"\0"
    ):
        path = os.fsdecode(raw)
        parts = path.split("/")
        if parts[-1] != "pyproject.toml" or any(p in SKIPPED or p.startswith(".") for p in parts):
            continue
        try:
            marker = safe_path(root, path)
        except UnsafePath:
            continue
        if marker.is_file():
            found.add(marker.parent.relative_to(root).as_posix())
    return [(ProjectStack("python", d), (under(d, "pyproject.toml"),)) for d in sorted(found)]


def proposal(found: Sequence[tuple[ProjectStack, tuple[str, ...]]]) -> str:
    if not found:
        return (
            "init wrote nothing: it found no stack root, a directory with pyproject.toml "
            "(python). Ask the owner for the stacks, then run init again with "
            "--stack NAME[=DIRECTORY] for each stack, or with --stack agnostic."
        )
    rows = [f"  {s.name} in {s.directory} ({', '.join(markers)})" for s, markers in found]
    options = [
        f"--stack {s.name}" + ("" if s.directory == "." else f"={s.directory}") for s, _ in found
    ]
    return "\n".join(
        [
            "init wrote nothing: confirm the stacks first. It found these stack roots:",
            *rows,
            "Confirm them with the owner, or ask the owner for the stacks, "
            "then run init again with:",
            "  " + " ".join(options),
        ]
    )


def describe(stacks: Sequence[ProjectStack]) -> str:
    if len(stacks) == 1 and stacks[0].directory == ".":
        return stacks[0].name
    return ", ".join(f"{s.name} ({s.directory})" for s in stacks)


@dataclass(frozen=True)
class StackKit:
    markers: tuple[str, ...]
    new_project_marker: str | None
    source_root: str
    unit_tests: tuple[str, ...]
    guide_rows: tuple[str, ...]
    guide_rules: tuple[str, ...]
    lint_rules: bool
    patterns: tuple[str, ...]
    protected: tuple[str, ...]


KITS: dict[StackName, StackKit] = {
    "python": StackKit(
        ("pyproject.toml",),
        "pyproject.toml",
        "src/{package}",
        ("tests/unit/**",),
        (
            "| Product code | [Source](src/AGENTS.md) |",
            "| Tests, and which count as unit tests | [Tests](tests/AGENTS.md) |",
        ),
        (
            (
                "- Mark a `dead-code` false positive where devctl can see it, with its `rs-"
                "exception` marker. Use `# noqa: V<code>` on the line vulture reports, and `# "
                "deptry: ignore[<code>]` on the line deptry reports. For a dependency that "
                "deptry reports as unused, add an item under `DEP002` in "
                "`[tool.deptry.per_rule_ignores]`. For one definition, prefer the comment to an "
                "`ignore_names` item, which spares every definition of the name. Never hide a "
                "finding with a vulture whitelist module, a bare reference to the name, a "
                "leading `_`, an `__all__` entry or a `getattr` string. devctl cannot detect "
                "these, so review treats each as an unmarked suppression. advisory"
            ),
        ),
        True,
        (
            "python-error-handling.md",
            "python-configuration.md",
            "python-input-validation.md",
            "python-performance.md",
        ),
        (
            "pyproject.toml",
            "**/ruff.toml",
            "**/.ruff.toml",
            "mypy.ini",
            ".mypy.ini",
            "pytest.ini",
            ".pytest.ini",
            "pytest.toml",
            ".pytest.toml",
            "setup.cfg",
            "tox.ini",
            ".importlinter",
        ),
    ),
    "agnostic": StackKit((), None, "", ("tests/unit/**",), (), (), False, (), ()),
}
DERIVED = frozenset(
    {
        "directory",
        "guide_rows",
        "lint_marker",
        "source_roots",
        "stack_patterns",
        "stack_protected",
        "stack_rows",
        "stack_rules",
        "stack_tables",
        "stack_title",
        "unit_tests",
    }
)


def guide_directories(stacks: Sequence[ProjectStack]) -> list[str]:
    return sorted(
        {
            str(parent)
            for s in stacks
            if s.directory != "."
            for parent in (Path(s.directory), *Path(s.directory).parents)
            if str(parent) != "."
        }
    )


def navigation_row(directory: str, title: str) -> str:
    return f"| {title} | [{directory}/]({directory}/AGENTS.md) |"


def stack_variables(stacks: Sequence[ProjectStack]) -> dict[str, str]:
    ordered = sorted(stacks, key=lambda s: s.name)
    names = " and ".join(s.name.title() for s in ordered)
    title = f"The {names} stack" + ("s" if len(ordered) > 1 else "")
    return {
        "directory": "" if ordered[0].directory == "." else ordered[0].directory + "/",
        "guide_rows": "\n".join(
            dict.fromkeys(row for s in ordered for row in KITS[s.name].guide_rows)
        ),
        "stack_title": title,
    }


def derived_variables(
    stacks: Sequence[ProjectStack], variables: Mapping[str, str]
) -> dict[str, str]:
    ordered = sorted(stacks, key=lambda s: (s.directory, s.name))
    names = list(dict.fromkeys(s.name for s in ordered))
    owner = variables.get("owner") or "<owner>"
    groups = {d: list(items) for d, items in groupby(ordered, key=lambda s: s.directory)}
    rows = [stack_variables(groups["."])["guide_rows"]] if "." in groups else []
    for d in guide_directories(ordered):
        title = stack_variables(groups[d])["stack_title"] if d in groups else "Directory navigation"
        rows.append(navigation_row(d, title))
    return {
        "stack_tables": "\n\n".join(
            f"[[stack]]\nname = {json.dumps(s.name)}\ndirectory = {json.dumps(s.directory)}"
            for s in ordered
        ),
        "source_roots": ", ".join(
            json.dumps(under(s.directory, KITS[s.name].source_root.format(**variables)))
            for s in ordered
            if KITS[s.name].source_root
        ),
        "unit_tests": ", ".join(
            dict.fromkeys(
                json.dumps(under(s.directory, item))
                for s in ordered
                for item in KITS[s.name].unit_tests
            )
        ),
        "stack_patterns": "\n".join(
            f"# /docs/patterns/{item} @{owner}" for name in names for item in KITS[name].patterns
        ),
        "stack_protected": "\n".join(
            f"# /{under(s.directory, item)} @{owner}"
            for s in ordered
            for item in KITS[s.name].protected
        ),
        "stack_rows": "\n".join(rows),
        "stack_rules": "\n".join(rule for name in names for rule in KITS[name].guide_rules),
        "lint_marker": "enforced by: check:lint"
        if all(KITS[s.name].lint_rules for s in ordered)
        else "advisory",
    }
