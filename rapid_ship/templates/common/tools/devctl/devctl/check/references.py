"""Resolve references: the names of the checks that enforce a Rule or a Pattern.

A reference is `<kind>:<value>`. `check` and `test` work for every stack. `ruff`, `banned`,
`contract` and Python `type` read pyproject.toml. TypeScript uses ESLint and tsc;
`test` selects Python identities, Vitest title chains or word search by file path. A file that a
reference reads or names counts only when git tracks it.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Callable, Iterable
from pathlib import PurePosixPath

from devctl.check.stacks import typescript_references, vitest
from devctl.check.stacks.python import test_identities
from devctl.check.steps import CheckContext
from devctl.check.tracked import TrackedFiles
from devctl.settings import under

# Ruff selects these when `select` is not set.
_RUFF_DEFAULT_SELECT = ["E4", "E7", "E9", "F"]
_PYTHON_KINDS = frozenset({"ruff", "banned", "contract", "type"})


class _Unreadable(Exception):
    """pyproject.toml is missing or invalid. The message names what is wrong."""


def _inside(path: str) -> bool:
    """Whether `path` is relative and cannot leave the repository."""
    parts = PurePosixPath(path).parts
    return bool(parts) and not (PurePosixPath(path).is_absolute() or ".." in parts or "\\" in path)


def path_problem(path: str, tracked: TrackedFiles) -> str | None:
    """None when `path` names a tracked file, or a directory that holds one, inside the
    repository; else why not, as a phrase: "does not exist" or "is not tracked; ..."."""
    if not _inside(path) or not (tracked.root / path).exists():
        return "does not exist"
    return None if tracked.holds(path) else f"is {tracked.why_untracked(path)}"


def _file_problem(path: str, tracked: TrackedFiles) -> str | None:
    """None when `path` is a tracked file inside the repository; else why not, as a phrase."""
    if not _inside(path) or not (tracked.root / path).is_file():
        return "is not a file"
    return None if tracked.holds(path) else f"is {tracked.why_untracked(path)}"


def resolve(
    reference: str, context: CheckContext, tracked: TrackedFiles, holder: str
) -> str | None:
    """None when the reference resolves, else why it does not."""
    kind, _, value = reference.partition(":")
    if not kind or not value:
        return f"{reference}: write <kind>:<value>"
    if kind == "check":
        return _check(reference, value, context, holder)
    if kind == "test":
        return _test(reference, value, context, tracked)
    if kind not in _PYTHON_KINDS | {"eslint"}:
        return f"{reference}: unknown reference kind {kind}"
    owners = context.project.owners(holder)
    stack_name = _stack_name(kind, value)
    candidates = [stack for stack in (owners or context.project.stacks) if stack.name == stack_name]
    if not candidates:
        return f"{reference}: unknown reference kind {kind} for {holder}"
    if len(candidates) > 1:
        choices = ", ".join(f"{stack.name} ({stack.directory})" for stack in candidates)
        return (
            f"{reference}: ambiguous for {holder}: {choices}; use test:<path>::<name> or "
            "check:<step> with a directory-qualified name, such as lint (backend)"
        )
    if stack_name == "typescript":
        resolver = (
            typescript_references.resolve_eslint
            if kind == "eslint"
            else typescript_references.resolve_type
        )
        return resolver(reference, value, tracked, candidates[0])
    path = under(candidates[0].directory, "pyproject.toml")
    try:
        data = _pyproject(tracked, path)
    except _Unreadable as error:
        return f"{reference}: {error}"
    try:
        return _PYTHON_RESOLVERS[kind](reference, value, tracked, data, path)
    except _Unreadable as error:
        return f"{reference}: {path}: {error}"


def _stack_name(kind: str, value: str) -> str:
    if kind != "type":
        return "typescript" if kind == "eslint" else "python"
    suffix = PurePosixPath(value).suffix
    if suffix in (".ts", ".tsx", ".mts", ".cts"):
        return "typescript"
    return "python" if suffix in (".py", ".pyi") else ""


def _check(reference: str, step: str, context: CheckContext, holder: str) -> str | None:
    from devctl.check import (
        StackStep,
        all_steps,
        base_name,
    )  # Imported late: devctl.check imports this module.

    owners = context.project.owners(holder)
    if any(
        (candidate.name == step or base_name(candidate.name) == step)
        and (not isinstance(candidate, StackStep) or not owners or candidate.stack in owners)
        for candidate in all_steps(context.project)
    ):
        return None
    return f"{reference}: no devctl check step is named {step}"


def _test(reference: str, value: str, context: CheckContext, tracked: TrackedFiles) -> str | None:
    path, separator, name = value.partition("::")
    if not path or not separator or not name:
        return f"{reference}: write test:<path>::<name>"
    if problem := _file_problem(path, tracked):
        return f"{reference}: {path} {problem}"
    try:
        text = (tracked.root / path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return f"{reference}: cannot read {path}: {error}"
    try:
        if PurePosixPath(path).suffix == ".py":
            found = name in test_identities(text)
        elif vitest.is_test_file(path):
            found = name in vitest.test_identities(text)[0]
        else:
            found = re.search(rf"(?<!\w){re.escape(name)}(?!\w)", text) is not None
    except SyntaxError as error:
        return f"{reference}: {path} does not parse: {error.msg} (line {error.lineno})"
    except ValueError as error:
        return f"{reference}: {path} does not parse: {error}"
    return None if found else f"{reference}: {path} has no test named {name}"


def _pyproject(tracked: TrackedFiles, relative: str) -> dict[str, object]:
    path = tracked.root / relative
    if path.is_file() and not tracked.holds(relative):
        raise _Unreadable(f"{relative} is {tracked.why_untracked(relative)}")
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise _Unreadable(f"{relative} is missing") from None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise _Unreadable(f"{relative}: {error}") from error


def _table(data: dict[str, object], *path: str) -> dict[str, object]:
    """The table at `path` in pyproject.toml; empty when absent."""
    node: object = data
    for key in path:
        if not isinstance(node, dict):
            break
        node = node.get(key, {})
    if not isinstance(node, dict):
        raise _Unreadable(f"[{'.'.join(path)}] must be a table")
    return node


def _strings(
    table: dict[str, object], key: str, where: str, *, split_commas: bool = False
) -> list[str] | None:
    """A list of strings, or a lone string; None when absent. A string is one item, or with
    split_commas a comma-separated list, as mypy reads `files`."""
    if key not in table:
        return None
    value = table[key]
    if isinstance(value, str):
        items = value.split(",") if split_commas else [value]
        return [item.strip() for item in items if item.strip()]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return list(value)
    raise _Unreadable(f"{where} {key} must be a list of strings")


def _longest(prefixes: Iterable[str], code: str) -> int:
    """The length of the longest prefix that begins `code`, or -1. ALL matches with length 0."""
    return max(
        (
            0 if prefix == "ALL" else len(prefix)
            for prefix in prefixes
            if prefix == "ALL" or code.startswith(prefix)
        ),
        default=-1,
    )


def _ruff_setting(data: dict[str, object], key: str) -> list[str] | None:
    # `[tool.ruff.lint]` wins; the deprecated top-level `[tool.ruff]` setting fills the gaps.
    lint = _strings(_table(data, "tool", "ruff", "lint"), key, "[tool.ruff.lint]")
    return lint if lint is not None else _strings(_table(data, "tool", "ruff"), key, "[tool.ruff]")


def _ruff(
    reference: str, code: str, _tracked: TrackedFiles, data: dict[str, object], settings: str
) -> str | None:
    select = _ruff_setting(data, "select")
    selected = _RUFF_DEFAULT_SELECT if select is None else select
    selected = [*selected, *(_ruff_setting(data, "extend-select") or [])]
    ignored = [
        *(_ruff_setting(data, "ignore") or []),
        *(_ruff_setting(data, "extend-ignore") or []),
    ]
    if _longest(selected, code) > _longest(ignored, code):
        return None
    return f"{reference}: Ruff does not select {code} in {settings}"


def _banned(
    reference: str, member: str, _tracked: TrackedFiles, data: dict[str, object], settings: str
) -> str | None:
    banned = _table(data, "tool", "ruff", "lint", "flake8-tidy-imports", "banned-api")
    if member in banned:
        return None
    return (
        f"{reference}: {member} is not in "
        f"[tool.ruff.lint.flake8-tidy-imports.banned-api] in {settings}"
    )


def _contract(
    reference: str, name: str, _tracked: TrackedFiles, data: dict[str, object], settings: str
) -> str | None:
    contracts = _table(data, "tool", "importlinter").get("contracts", [])
    if isinstance(contracts, list) and any(
        isinstance(entry, dict) and entry.get("name") == name for entry in contracts
    ):
        return None
    return f"{reference}: no [[tool.importlinter.contracts]] entry is named {name} in {settings}"


def _type(
    reference: str, path: str, tracked: TrackedFiles, data: dict[str, object], settings: str
) -> str | None:
    if problem := _file_problem(path, tracked):
        return f"{reference}: {path} {problem}"
    if not PurePosixPath(path).is_relative_to(PurePosixPath(settings).parent):
        return f"{reference}: [tool.mypy] files does not cover {path} in {settings}"
    relative = str(PurePosixPath(path).relative_to(PurePosixPath(settings).parent))
    mypy = _table(data, "tool", "mypy")
    covered = _strings(mypy, "files", "[tool.mypy]", split_commas=True) or []
    if not any(_is_under(relative, entry) for entry in covered):
        return f"{reference}: [tool.mypy] files does not cover {path} in {settings}"
    for pattern in _strings(mypy, "exclude", "[tool.mypy]") or []:
        try:
            if re.search(pattern, relative):
                return f"{reference}: [tool.mypy] exclude matches {path} in {settings}"
        except re.error as error:
            raise _Unreadable(
                f"[tool.mypy] exclude {pattern!r} is not a regular expression"
            ) from error
    return None


def _is_under(path: str, entry: str) -> bool:
    entry = entry.removeprefix("./").rstrip("/")
    return entry in ("", ".") or path == entry or path.startswith(f"{entry}/")


_PYTHON_RESOLVERS: dict[
    str, Callable[[str, str, TrackedFiles, dict[str, object], str], str | None]
] = {
    "ruff": _ruff,
    "banned": _banned,
    "contract": _contract,
    "type": _type,
}
