"""devctl's view of its git repository.

Every git call goes through _git, which raises RepoError so devctl reports one message
and exits 2 instead of printing a traceback.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


class RepoError(Exception):
    """git is missing, or the directory is not in a work tree. devctl exits 2."""


def _git(
    cwd: Path, *args: str, allowed: tuple[int, ...] = (0,)
) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=False)  # noqa: S603, S607  # rs-exception: EX-3
    except OSError as error:
        raise RepoError(f"cannot run git: {error}") from error
    if result.returncode not in allowed:
        raise RepoError(f"git {args[0]}: {result.stderr.decode(errors='replace').strip()}")
    return result


def _names(output: bytes) -> set[str]:
    """The paths in git's NUL-separated output."""
    return {os.fsdecode(name) for name in output.split(b"\0") if name}


@dataclass(frozen=True)
class Repo:
    root: Path
    git_common_dir: Path

    @classmethod
    def discover(cls, start: Path) -> Repo:
        output = _git(
            start, "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-common-dir"
        ).stdout
        root, common = os.fsdecode(output).splitlines()
        return cls(Path(root), Path(common))

    def tracked_files(self) -> list[str]:
        """Tracked files, staged ones included, as POSIX paths: the files a commit would record.

        git lists an unmerged path once for each stage; it appears here once. An intent-to-add
        entry (git add -N) is left out, because a commit leaves it out.
        """
        listed = _git(self.root, "ls-files", "-z").stdout
        # Against the index, git diff shows each intent-to-add entry as added. Without
        # --no-renames, rename detection can pair one with a deleted file and hide it.
        intended = _git(
            self.root, "diff", "--no-renames", "--name-only", "--diff-filter=A", "-z"
        ).stdout
        return sorted(_names(listed) - _names(intended))

    def merge_base(self, ref: str) -> str | None:
        """The merge base of HEAD and ref; None when they share no history (git exits 1)."""
        return (
            _git(self.root, "merge-base", "HEAD", ref, allowed=(0, 1)).stdout.decode().strip()
            or None
        )

    def files(self) -> list[str]:
        """Tracked files plus untracked files that Git does not ignore, as POSIX paths."""
        output = _git(
            self.root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"
        ).stdout
        return sorted(_names(output))

    def git(self, *args: str) -> str:
        """Run git in the work tree and return its output; RepoError when it fails."""
        return os.fsdecode(_git(self.root, *args).stdout)
