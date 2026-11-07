"""Tracked TypeScript reference inputs and computed settings, cached per tracked snapshot."""

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from weakref import ref

from devctl import node, process
from devctl.check.tracked import TrackedFiles
from devctl.settings import ProjectStack, under

_CACHE: dict[int, tuple[ref[TrackedFiles], dict[tuple[str, str], object]]] = {}


def _cache(tracked: TrackedFiles) -> dict[tuple[str, str], object]:
    key = id(tracked)
    if key not in _CACHE:
        _CACHE[key] = (ref(tracked, lambda _: _CACHE.pop(key, None)), {})
    return _CACHE[key][1]


def _inputs(reference: str, tracked: TrackedFiles, paths: list[str]) -> str | None:
    for path in paths:
        if not tracked.holds(path):
            return f"{reference}: {path} is {tracked.why_untracked(path)}"
        if not (tracked.root / path).is_file():
            return f"{reference}: {path} is not a file"
    return None


def resolve_eslint(
    reference: str, rule: str, tracked: TrackedFiles, stack: ProjectStack
) -> str | None:
    directory = tracked.root / stack.directory
    # ESLint 10 starts beside the probe, then searches its ancestors. Keep lookup within
    # this stack so an ancestor stack's config cannot satisfy a missing local config.
    config = next(
        (
            path.relative_to(tracked.root).as_posix()
            for parent in ((directory / node.ESLINT_PROBE).parent, directory)
            for extension in ("js", "mjs", "cjs", "ts", "mts", "cts")
            if (path := parent / f"eslint.config.{extension}").is_file() or path.is_symlink()
        ),
        under(stack.directory, "eslint.config.js"),
    )
    if error := _inputs(
        reference,
        tracked,
        [under(stack.directory, name) for name in ("package.json", "tsconfig.json")] + [config],
    ):
        return error
    cache = _cache(tracked)
    key = ("eslint", stack.directory)
    if key not in cache:
        cache[key] = node.eslint_config(directory)
    data = cache[key]
    if isinstance(data, str):
        return f"{reference}: {node.cannot_run('eslint', stack.directory, data, directory)}"
    rules = data.get("rules", {}) if isinstance(data, Mapping) else {}
    if isinstance(rules, Mapping) and node.is_error(rules.get(rule)):
        return None
    return f"{reference}: ESLint does not report {rule} as an error in {stack.directory}"


def _tsc(directory: Path) -> set[str] | str:
    tool = node.node_tool(directory, "tsc")
    if tool is None:
        return "tsc is not installed"
    result = process.run_process(
        [str(tool), "--listFilesOnly", "-p", "tsconfig.json"], directory, 120
    )
    if result.timed_out:
        return "tsc timed out after 120 seconds"
    if result.returncode:
        return f"tsc exited {result.returncode}: {result.stderr.strip()}"
    return {
        str((directory / line).resolve()) for line in result.stdout.splitlines() if line.strip()
    }


def resolve_type(
    reference: str, path: str, tracked: TrackedFiles, stack: ProjectStack
) -> str | None:
    if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts or "\\" in path:
        return f"{reference}: {path} is not a file"
    if error := _inputs(reference, tracked, [under(stack.directory, "tsconfig.json"), path]):
        return error
    directory = tracked.root / stack.directory
    cache = _cache(tracked)
    key = ("tsc", stack.directory)
    if key not in cache:
        cache[key] = _tsc(directory)
    files = cache[key]
    if isinstance(files, str):
        return f"{reference}: {node.cannot_run('tsc', stack.directory, files, directory)}"
    if isinstance(files, set) and str((tracked.root / path).resolve()) in files:
        return None
    return f"{reference}: tsc does not check {path}"
