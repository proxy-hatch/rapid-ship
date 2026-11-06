"""Stack options and read-only detection of project roots."""

import os
from collections.abc import Sequence
from dataclasses import dataclass
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
