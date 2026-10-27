"""The map step: checks the guides, feature files, Patterns, Rules, skills and root documents.

Every rule reads only the files that git tracks, staged ones included (`TrackedFiles`), and
reads their text from the work tree. A path that a guide, feature file, Pattern or reference
names resolves only when git tracks it.
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import shlex
from collections import deque
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from devctl.check.map_skills import skill_alias_errors, skill_errors, skill_file_errors
from devctl.check.markdown import (
    ListItem,
    front_matter_of,
    navigation_links,
    rules_items,
    section,
    text_value,
)
from devctl.check.references import path_problem, resolve
from devctl.check.steps import CheckContext, StepResult, Tier, blocked, failed, passed
from devctl.check.tracked import TrackedFiles
from devctl.repo import RepoError
from devctl.settings import ProjectSettings

ROOT_GUIDE = "AGENTS.md"
ROOT_DOCUMENTS = ("README.md", "ARCHITECTURE.md")
FEATURES = "docs/features"
PATTERNS = "docs/patterns"
# The reference may be wrapped in backticks, as in "enforced by: `check:map`".
_RULE_END = re.compile(r"(?:^|\s)(?:enforced by: `?(?P<reference>[^\s`]+)`?|advisory)$")


class MapStep:
    name = "map"
    tier: Tier = "fast"

    def run(self, context: CheckContext) -> StepResult:
        try:
            tracked = TrackedFiles.read(context.repo)
        except RepoError as error:
            return blocked(self.name, str(error))
        found = guides(tracked, context.project)
        errors = [
            *link_errors(tracked, found),
            *coverage_errors(tracked, context.project),
            *reachability_errors(tracked, found),
            *feature_errors(context, tracked),
            *pattern_errors(context, tracked),
            *pattern_lesson_errors(context, tracked),
            *rule_errors(context, tracked, found),
            *skill_alias_errors(tracked),
            *skill_errors(tracked),
            *skill_file_errors(tracked),
            *root_document_errors(tracked),
            *root_link_errors(tracked),
        ]
        return failed(self.name, *errors) if errors else passed(self.name)


def guides(tracked: TrackedFiles, project: ProjectSettings) -> list[str]:
    """The tracked AGENTS.md files that exist as files, less those under [map] exclude."""
    return [
        path
        for path in tracked.files
        if PurePosixPath(path).name == "AGENTS.md"
        and (tracked.root / path).is_file()
        and not _map_excluded(path, project)
    ]


def _map_excluded(path: str, project: ProjectSettings) -> bool:
    """Whether `path` is an entry of [map] exclude or lies under one."""
    return any(path == entry or path.startswith(f"{entry}/") for entry in project.map_exclude)


def link_errors(tracked: TrackedFiles, found: Sequence[str]) -> list[str]:
    """Each local link in each guide reaches a tracked file or a directory that holds one."""
    errors: list[str] = []
    for guide in found:
        try:
            links = _links(tracked.root, guide)
        except (OSError, ValueError) as error:
            errors.append(f"{guide}:{error}")
            continue
        for line, target in links:
            if problem := _link_error(tracked, guide, line, target):
                errors.append(problem)
    return errors


def _links(root: Path, guide: str) -> list[tuple[int, str]]:
    """The (line, target) of each link in `guide`. OSError or ValueError when it cannot be read."""
    return navigation_links((root / guide).read_text(encoding="utf-8"))


def _local_path(target: str) -> str | None:
    """The unescaped, unquoted path of a link to a local file or directory, else None."""
    target = re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", target)
    url = urlsplit(target)
    if url.scheme or url.netloc or not url.path:
        return None
    return unquote(url.path)


def _from_root(guide: str, path: str) -> str:
    """`path`, a local link in `guide`, relative to the repository root.

    GitHub resolves a link that starts with / against the repository root, as in a README.
    """
    directory = "" if path.startswith("/") else posixpath.dirname(guide)
    return posixpath.normpath(posixpath.join(directory, path.lstrip("/")))


def _link_error(tracked: TrackedFiles, guide: str, line: int, target: str) -> str | None:
    path = _local_path(target)
    if path is None:
        return None
    root = tracked.root
    dependency = Path(os.path.normpath(root / _from_root(guide, path)))
    if not dependency.exists():
        return f"{guide}:{line}: missing target {target!r}; update the navigation link"
    if dependency.is_relative_to(root) and tracked.holds(dependency.relative_to(root).as_posix()):
        return None
    return (
        f"{guide}:{line}: target {target!r} is not maintained in this checkout; "
        "track its source or update the navigation link"
    )


def coverage_errors(tracked: TrackedFiles, project: ProjectSettings) -> list[str]:
    """Each top-level directory and source-root child has a tracked guide or is unguided."""
    files, present = tracked.files, set(tracked.files)
    errors = [
        f"{source_root}: source root has no files; fix [map] source_roots"
        for source_root in project.source_roots
        if not any(path.startswith(f"{source_root}/") for path in files)
    ]
    needing = {path.split("/", 1)[0] for path in files if "/" in path}
    for source_root in project.source_roots:
        needing.update(_children(files, source_root))
    hint = "add an AGENTS.md guide, or list the directory under [map] unguided"
    for directory in sorted(needing):
        guide = f"{directory}/AGENTS.md"
        if _needs_guide(directory, project) and guide not in present:
            errors.append(_required(tracked, guide, f"{directory}/: {hint}"))
    return errors


def _required(tracked: TrackedFiles, path: str, missing: str) -> str:
    """The error for a required file that git does not track; `missing` when the work tree
    lacks it too."""
    if (tracked.root / path).is_file():
        return f"{path}: {tracked.why_untracked(path)}"
    return missing


def _children(files: Sequence[str], root: str) -> set[str]:
    """`<root>/<child>` for each child directory of `root` that holds a file."""
    prefix = f"{root}/"
    return {
        prefix + path[len(prefix) :].split("/", 1)[0]
        for path in files
        if path.startswith(prefix) and "/" in path[len(prefix) :]
    }


def _needs_guide(directory: str, project: ProjectSettings) -> bool:
    name = PurePosixPath(directory).name
    # Python writes bytecode into __pycache__ on import; hidden directories hold tool state.
    if name.startswith(".") or name == "__pycache__":
        return False
    return directory not in project.unguided and not _map_excluded(directory, project)


def reachability_errors(tracked: TrackedFiles, found: Sequence[str]) -> list[str]:
    """Every guide is reached from the root guide by links, directly or by directory."""
    if ROOT_GUIDE not in found:
        missing = f"{ROOT_GUIDE}: add a root guide that links every other guide"
        return [_required(tracked, ROOT_GUIDE, missing)]
    reached = {ROOT_GUIDE}
    pending = deque([ROOT_GUIDE])
    while pending:
        guide = pending.popleft()
        targets = set(_guide_targets(tracked.root, guide))
        for other in found:
            holder = posixpath.dirname(other) or "."
            if other not in reached and (other in targets or holder in targets):
                reached.add(other)
                pending.append(other)
    return [
        f"{guide}: not reachable by links from {ROOT_GUIDE}; link it from its parent guide"
        for guide in sorted(set(found) - reached)
    ]


def _guide_targets(root: Path, guide: str) -> list[str]:
    """Where `guide`'s local links point, as repository-relative paths. An unreadable guide has
    none; `link_errors` reports it."""
    try:
        links = _links(root, guide)
    except (OSError, ValueError):
        return []
    paths = (_local_path(target) for _, target in links)
    return [_from_root(guide, path) for path in paths if path]


def registered_verbs() -> frozenset[str]:
    """The devctl verbs, including the project's own from devctl_project.register."""
    from devctl.cli import build_parser  # Imported late: devctl.cli imports devctl.check.

    for action in build_parser()._actions:
        if isinstance(action, argparse._SubParsersAction):
            return frozenset(action.choices)
    return frozenset()


def _string_list(data: dict[str, object], key: str, *, allow_empty: bool) -> list[str] | None:
    """The list under `key`, or None when it is missing, not a list of text or not allowed empty."""
    value = data.get(key)
    if not isinstance(value, list) or (not value and not allow_empty):
        return None
    if not all(isinstance(item, str) and item.strip() for item in value):
        return None
    return value


def _documents(tracked: TrackedFiles, directory: str) -> list[str]:
    """The tracked Markdown files under `directory`, other than its README, that exist as
    files."""
    return [
        path
        for path in tracked.files
        if path.startswith(f"{directory}/")
        and path.endswith(".md")
        and path != f"{directory}/README.md"
        and (tracked.root / path).is_file()
    ]


_Problems = Callable[[CheckContext, TrackedFiles, str, dict[str, object], str], list[str]]


def _document_errors(
    context: CheckContext,
    tracked: TrackedFiles,
    directory: str,
    keys: str | None,
    problems: _Problems,
) -> list[str]:
    """`problems(context, tracked, path, front matter, text)` for each document under
    `directory`.

    A document whose front matter is unusable is reported as one error; when it has none, the
    message names `keys`. With `keys` None it is skipped, because another rule already reports
    it.
    """
    root = tracked.root
    errors: list[str] = []
    for path in _documents(tracked, directory):
        data = front_matter_of(root, path, keys or "")
        if isinstance(data, dict):
            text = (root / path).read_text(encoding="utf-8")
            errors += problems(context, tracked, path, data, text)
        elif keys is not None:
            errors.append(data)
    return errors


def feature_errors(context: CheckContext, tracked: TrackedFiles) -> list[str]:
    """Each feature file has front matter, and git tracks what it names."""
    keys = "purpose, entry_points, data, observe and reproduce"
    return _document_errors(context, tracked, FEATURES, keys, _feature_problems)


def _feature_problems(
    _context: CheckContext,
    tracked: TrackedFiles,
    path: str,
    data: dict[str, object],
    _text: str,
) -> list[str]:
    problems: list[str] = []
    if text_value(data, "purpose") is None:
        problems.append(f"{path}: purpose is missing or empty")
    for key, allow_empty in (("entry_points", False), ("data", True)):
        items = _string_list(data, key, allow_empty=allow_empty)
        if items is None:
            problems.append(f"{path}: {key} is missing or empty")
            continue
        problems += [
            f"{path}: {key} names {item}, which {problem}"
            for item in items
            if (problem := path_problem(item, tracked))
        ]
    if text_value(data, "observe") is None:
        problems.append(f"{path}: observe is missing or empty")
    if problem := _reproduce_problem(path, data):
        problems.append(problem)
    return problems


def _reproduce_problem(path: str, data: dict[str, object]) -> str | None:
    command = text_value(data, "reproduce")
    if command is None:
        return f"{path}: reproduce is missing or empty"
    try:
        words = shlex.split(command)
    except ValueError:
        words = []
    if words[:1] != ["./devctl"]:
        return f"{path}: reproduce must be a ./devctl command"
    if len(words) < 2:
        return f"{path}: reproduce names no verb after ./devctl"
    if words[1] not in registered_verbs():
        return f"{path}: reproduce runs {command}; {words[1]} is not a devctl verb"
    return None


def pattern_errors(context: CheckContext, tracked: TrackedFiles) -> list[str]:
    """Each Pattern file has a tracked reference and enforcement that resolves."""
    return _document_errors(
        context, tracked, PATTERNS, "task, reference and enforced_by", _pattern_problems
    )


def _pattern_problems(
    context: CheckContext,
    tracked: TrackedFiles,
    path: str,
    data: dict[str, object],
    _text: str,
) -> list[str]:
    problems: list[str] = []
    reference = text_value(data, "reference")
    if reference is None:
        problems.append(f"{path}: reference is missing or empty")
    elif problem := path_problem(reference, tracked):
        problems.append(f"{path}: reference names {reference}, which {problem}")
    enforced = _string_list(data, "enforced_by", allow_empty=False)
    if enforced is None:
        problems.append(f"{path}: enforced_by is missing or empty")
        return problems
    reasons = (resolve(item, context, tracked) for item in enforced)
    return problems + [f"{path}: {reason}" for reason in reasons if reason is not None]


def pattern_lesson_errors(context: CheckContext, tracked: TrackedFiles) -> list[str]:
    """Each Pattern file has a task and a non-empty ## Lessons.

    A file whose front matter is unusable is left to `pattern_errors`, which reports it.
    """
    return _document_errors(context, tracked, PATTERNS, None, _lesson_problems)


def _lesson_problems(
    _context: CheckContext,
    _tracked: TrackedFiles,
    path: str,
    data: dict[str, object],
    text: str,
) -> list[str]:
    problems: list[str] = []
    if text_value(data, "task") is None:
        problems.append(f"{path}: task is missing or empty")
    lessons = section(text, "Lessons", 2)
    if lessons is None or not lessons.strip():
        problems.append(f"{path}: ## Lessons is missing or empty")
    return problems


def rule_errors(context: CheckContext, tracked: TrackedFiles, found: Sequence[str]) -> list[str]:
    """Each rule under a Rules heading ends with a marker whose reference resolves."""
    errors: list[str] = []
    for guide in found:
        try:
            items = rules_items((tracked.root / guide).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # link_errors reports a guide that cannot be read
        errors += [
            problem for item in items if (problem := _rule_problem(context, tracked, guide, item))
        ]
    return errors


def _rule_problem(
    context: CheckContext, tracked: TrackedFiles, guide: str, item: ListItem
) -> str | None:
    ending = _RULE_END.search(item.text)
    if ending is None:
        return f"{guide}:{item.line}: end the rule with 'enforced by: <reference>' or 'advisory'"
    reference = ending.group("reference")
    reason = resolve(reference, context, tracked) if reference else None
    return f"{guide}:{item.line}: {reason}" if reason else None


def _root_documents(tracked: TrackedFiles) -> list[str]:
    """The ROOT_DOCUMENTS that git tracks and that exist as files."""
    return [
        name for name in ROOT_DOCUMENTS if name in tracked.files and (tracked.root / name).is_file()
    ]


def root_document_errors(tracked: TrackedFiles) -> list[str]:
    """README.md and ARCHITECTURE.md are tracked at the repository root.

    rapid-ship sync seeds a missing document when it upgrades a project from a Kit without the
    seed. Once the lock lists a document, sync never writes it again, so the message names git.
    """
    found = _root_documents(tracked)
    return [
        _required(
            tracked,
            name,
            f"{name}: missing at the repository root; restore it from git or write a new one "
            "(rapid-ship sync seeds it only while the Kit lock does not list it)",
        )
        for name in ROOT_DOCUMENTS
        if name not in found
    ]


def root_link_errors(tracked: TrackedFiles) -> list[str]:
    """Each local link in the root documents resolves as link_errors checks it, and the root
    guide links both. A missing or untracked document is root_document_errors' report, and a
    missing or untracked root guide reachability_errors'."""
    root = tracked.root
    errors = link_errors(tracked, _root_documents(tracked))
    if ROOT_GUIDE in tracked.files and (root / ROOT_GUIDE).is_file():
        targets = set(_guide_targets(root, ROOT_GUIDE))
        errors += [
            f"{ROOT_GUIDE}: does not link {name}; add it to the Find the change table"
            for name in ROOT_DOCUMENTS
            if name not in targets
        ]
    return errors
