"""doctor --skills: the skills each Harness's Session loads from a worktree at HEAD.

For each Harness the Roster names, or without a Roster each of claude, codex and agy found on
PATH, doctor adds a detached worktree at HEAD in a new temporary directory, starts one new
headless Session there and compares the skills it lists with the ones committed at HEAD. git runs
with the owner's own setup; no App token is minted. The worktree is doctor's only local write, and
it is removed again whatever the Session did. Each Session spends a little of the owner's quota.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

from devctl import process
from devctl.check.markdown import front_matter
from devctl.doctor_items import DoctorContext, Item, Status, harness_roles, run_installed
from devctl.harness import PROBE_TIMEOUT_SECONDS, HarnessName, parse_skills, skills_args
from devctl.process import ProcessResult
from devctl.repo import Repo
from devctl.settings import ProjectSettings

SUPPORTED: tuple[HarnessName, ...] = ("claude", "codex", "agy")
_GIT_TIMEOUT_SECONDS = 120.0
_NONE_ON_PATH = (
    ".rapid-ship/project.toml has no Roster, and none of claude, codex or agy is on PATH"
)


class ProbeError(Exception):
    """The probe worktree could not be added or removed."""


def _git_problem(result: ProcessResult) -> str | None:
    """Why git's answer cannot be used, or None. A timeout or cut output is never an answer."""
    if result.timed_out:
        return f"timed out after {_GIT_TIMEOUT_SECONDS:g} seconds"
    if result.stdout_truncated or result.stderr_truncated:
        return "its output was too long"
    if result.returncode != 0:
        return process.first_line(result.stderr) or f"exit code {result.returncode}"
    return None


def _git(cwd: Path, *args: str, failure: str) -> None:
    problem = _git_problem(process.run_process(["git", *args], cwd, _GIT_TIMEOUT_SECONDS))
    if problem is not None:
        raise ProbeError(f"{failure}: {problem}")


@contextmanager
def probe_worktree(repo: Repo) -> Iterator[Path]:
    """A detached worktree at HEAD in a new temporary directory, removed whatever the body did.

    The removal is forced twice, so files a Session wrote, or a lock it took, cannot keep the
    worktree. When the removal fails anyway, the worktree stays and ProbeError says how to remove
    it by hand.
    """
    scratch = Path(tempfile.mkdtemp(prefix="devctl-skills-")).resolve()
    path = scratch / "tree"
    try:
        _git(
            repo.root,
            "worktree",
            "add",
            "--detach",
            str(path),
            "HEAD",
            failure=f"could not add the probe worktree {path}",
        )
    except ProbeError:
        shutil.rmtree(scratch, ignore_errors=True)
        raise
    try:
        yield path
    finally:
        command = f"git worktree remove --force --force {path}"
        try:
            _git(
                repo.root,
                "worktree",
                "remove",
                "--force",
                "--force",
                str(path),
                failure=f"could not remove the probe worktree {path}",
            )
        except ProbeError as error:
            raise ProbeError(f"{error}; remove it with {command}") from None
        scratch.rmdir()


def _item(name: str, status: Status, detail: str) -> Item:
    return Item("skills", name, status, detail)


def _user_invoked(manifest: Path) -> bool:
    """True when the skill's front matter sets disable-model-invocation: true.

    Front matter that cannot be read leaves the skill checked; map rule 7 reports it.
    """
    try:
        data = front_matter(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError):
        return False
    return isinstance(data, dict) and data.get("disable-model-invocation") is True


def repository_skills(tree: Path) -> tuple[frozenset[str], frozenset[str]]:
    """The skills under tree/.agents/skills, by directory name: (checked, user-invoked).

    A user-invoked skill is one that a Session may leave out of its list, so it is not checked.
    """
    checked: set[str] = set()
    user_invoked: set[str] = set()
    root = tree / ".agents" / "skills"
    for entry in root.iterdir() if root.is_dir() else ():
        manifest = entry / "SKILL.md"
        if manifest.is_file():
            (user_invoked if _user_invoked(manifest) else checked).add(entry.name)
    return frozenset(checked), frozenset(user_invoked)


def _compare(name: str, listed: frozenset[str], tree: Path) -> Item:
    """Missing when the Session did not list a checked skill; outside skills are only named."""
    checked, user_invoked = repository_skills(tree)
    missing = sorted(checked - listed)
    outside = sorted(listed - checked - user_invoked)
    parts = [
        f"missing: {', '.join(missing)}" if missing else f"{len(checked)} repository skills seen"
    ]
    if outside:
        parts.append(f"outside the repository: {', '.join(outside)}")
    if user_invoked:
        parts.append(f"not checked, user-invoked: {', '.join(sorted(user_invoked))}")
    return _item(name, "missing" if missing else "ok", "; ".join(parts))


def _session(name: str, harness: HarnessName, tree: Path) -> Item:
    """Start one headless Session of harness in tree; compare what it lists with tree's skills."""
    result = run_installed(harness, *skills_args(harness), cwd=tree, timeout=PROBE_TIMEOUT_SECONDS)
    if result is None:
        return _item(name, "missing", f"{harness} is not on PATH")
    report = parse_skills(harness, result)
    if report.names is None:
        return _item(name, "unknown", report.error or f"{harness} gave no skill list")
    return _compare(name, report.names, tree)


def _harness_item(repo: Repo, harness: HarnessName, name: str) -> Item:
    """One Harness in a worktree of its own, so one Session cannot change what the next sees."""
    if shutil.which(harness) is None:
        return _item(name, "missing", f"{harness} is not on PATH")
    try:
        with probe_worktree(repo) as tree:
            return _session(name, harness, tree)
    except (ProbeError, OSError) as error:  # adding or removing the worktree
        return _item(name, "unknown", str(error))


def probed_harnesses(project: ProjectSettings) -> dict[HarnessName, str]:
    """Each Harness to probe, with its item's name: the Roster's, named for their roles, or
    without a Roster each supported Harness on PATH (Spec 1 section 6, a Proposal)."""
    if project.roster:
        return {h: f"{roles} skills ({h})" for h, roles in harness_roles(project).items()}
    return {h: f"skills ({h})" for h in SUPPORTED if shutil.which(h) is not None}


def skills_items(ctx: DoctorContext) -> list[Item]:
    """One item per probed Harness, or one missing item when there is none to probe."""
    names = probed_harnesses(ctx.project)
    if not names:
        return [_item("skills", "missing", _NONE_ON_PATH)]
    repo = Repo.discover(ctx.root)
    return [_harness_item(repo, harness, name) for harness, name in names.items()]
