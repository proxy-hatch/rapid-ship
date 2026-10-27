"""The files that the map rules read: the files that git tracks, staged ones included.

CI checks out only what a commit records. A map rule that read an untracked file could pass in
the pre-commit hook and then fail in CI.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from devctl.repo import Repo


@dataclass(frozen=True)
class TrackedFiles:
    """The tracked `files` under `root`, sorted; `paths` adds each directory that holds one,
    `links` holds the tracked symlinks, and `untracked` the files that git neither tracks nor
    ignores."""

    root: Path
    files: tuple[str, ...]
    paths: frozenset[str]
    links: tuple[str, ...]
    untracked: frozenset[str]

    @classmethod
    def read(cls, repo: Repo) -> TrackedFiles:
        """RepoError when git cannot list the files."""
        files = repo.tracked_files()
        links = tuple(path for path in files if (repo.root / path).is_symlink())
        untracked = frozenset(repo.files()).difference(files)
        return cls(repo.root, tuple(files), _with_directories(files), links, untracked)

    def holds(self, path: str) -> bool:
        """Whether `path`, relative to the root, is a tracked file or a directory that holds one."""
        needed = self._needed(path)
        return needed is not None and all(name in self.paths for name in needed)

    def why_untracked(self, path: str) -> str:
        """Why `path`, which the work tree holds, does not count, with a fix that clears it."""
        needed = self._needed(path)
        if needed is None:
            return "not tracked, because it resolves outside the repository"
        missing = [name for name in needed if name not in self.paths]
        written = PurePosixPath(path).as_posix()
        for name in missing:
            if (part := self._untracked_part(name)) is not None:
                return f"not tracked; stage {'it' if part == written else part} with git add"
        for name in missing:
            folded = name.casefold()
            others = sorted(known for known in self.paths if known.casefold() == folded)
            if others:
                return (
                    f"not tracked in that case; git tracks {others[0]}, "
                    "so make the two names' case match"
                )
        named = missing[0] if missing else written
        return (
            f"not tracked, and git add cannot stage it; if git check-ignore -v {named} names a "
            ".gitignore rule, narrow or remove that rule, then stage it"
        )

    def _needed(self, path: str) -> list[str] | None:
        """The paths that git must track for `path` to count; None when `path` resolves outside
        the root.

        git records a symlink, not the paths beneath it. So three must be tracked: the path as
        written, unless a tracked symlink holds it; its last name, in the directory it resolves
        to; and the file or directory that the whole path resolves to.
        """
        relative = PurePosixPath(path)
        directory, resolved = self._resolved(relative.parent.as_posix()), self._resolved(path)
        if directory is None or resolved is None:
            return None
        behind_link = any(relative.is_relative_to(link) for link in self.links)
        written = [] if behind_link else [relative.as_posix()]
        last = (PurePosixPath(directory) / relative.name).as_posix()
        return list(dict.fromkeys([*written, last, resolved]))

    def _untracked_part(self, name: str) -> str | None:
        """What `git add` must stage for `name` to be tracked: `name` itself, when it is an
        untracked file or a directory that holds one, or an untracked symlink above it."""
        relative = PurePosixPath(name)
        for part in (relative, *relative.parents):
            if part.as_posix() in self.untracked:
                return part.as_posix()
        return name if any(path.startswith(f"{name}/") for path in self.untracked) else None

    def _resolved(self, path: str) -> str | None:
        """`path` with its symlinks resolved, relative to the root; None when it leaves it."""
        resolved, real_root = (self.root / path).resolve(), self.root.resolve()
        if not resolved.is_relative_to(real_root):
            return None
        return resolved.relative_to(real_root).as_posix()


def _with_directories(paths: Iterable[str]) -> frozenset[str]:
    """`paths` and each directory that holds one, the root `.` included."""
    found: set[str] = set()
    for path in map(PurePosixPath, paths):
        found.add(path.as_posix())
        found.update(parent.as_posix() for parent in path.parents)
    return frozenset(found)
