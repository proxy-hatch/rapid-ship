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
    """The tracked `files` under `root`, sorted; `paths` adds each directory that holds one, and
    `links` holds the tracked symlinks."""

    root: Path
    files: tuple[str, ...]
    paths: frozenset[str]
    links: tuple[str, ...]

    @classmethod
    def read(cls, repo: Repo) -> TrackedFiles:
        """RepoError when git cannot list the files."""
        files = repo.tracked_files()
        links = tuple(path for path in files if (repo.root / path).is_symlink())
        return cls(repo.root, tuple(files), _with_directories(files), links)

    def holds(self, path: str) -> bool:
        """Whether `path`, relative to the root, is a tracked file or a directory that holds one.

        git records a symlink, not the paths beneath it. So three things must be tracked: the
        path as written, or a symlink above it; its last name, in the directory it resolves to;
        and the file or directory that the whole path resolves to.
        """
        relative = PurePosixPath(path)
        written = relative.as_posix() in self.paths or any(
            relative.is_relative_to(link) for link in self.links
        )
        directory = self._resolved(relative.parent.as_posix())
        last = None if directory is None else (PurePosixPath(directory) / relative.name).as_posix()
        return written and last in self.paths and self._resolved(path) in self.paths

    def why_untracked(self, path: str) -> str:
        """Why `path`, which the work tree holds, is not tracked, with the fix."""
        return "not tracked; stage it with git add"

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
