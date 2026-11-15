"""rapid-ship init: vendor the Kit into a repository and commit it on its own branch.

It creates files and never replaces one.
"""

from __future__ import annotations

import keyword
import os
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from rapid_ship.files import UnsafePath, create_file, safe_path
from rapid_ship.kit.existing_checks import find_existing_checks
from rapid_ship.kit.git import (
    changed_paths,
    commit_paths,
    git,
    head_branch,
    head_commit,
    leave_branch,
    work_tree_root,
)
from rapid_ship.kit.lock import LOCK_PATH, Lock, entry_for, write_lock
from rapid_ship.kit.stacks import KITS, ProjectStack, checked_stacks, detect_stacks, proposal, under
from rapid_ship.kit.status import locate
from rapid_ship.kit.templates import (
    KitError,
    KitRefusal,
    Template,
    installed_version,
    load_manifest,
    render_files,
)
from rapid_ship.kit.writes import Undo

INIT_BRANCH = "rapid-ship/init"
FIRST_COMMIT_MESSAGE = "chore: start the repository"
_LISTED = 20  # dirty paths a refusal lists before it counts the rest
_PROJECT_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?")  # PEP 508 name
_LOGIN = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*")  # GitHub login, at most 39
_SEPARATORS = re.compile(r"[-_.]+")
# devctl's settings.py keeps a copy of this pattern; tests/devctl checks that the two agree.
_REPOSITORY = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*/(?!\.{1,2}$)[A-Za-z0-9._-]+")
_MAX_LOGIN = 39
# A github.com remote: https://, http:// or ssh:// with an optional user (or user:token), or the
# scp form git@github.com:owner/name. The path is checked against _REPOSITORY afterwards.
_GITHUB_REMOTE = re.compile(
    r"(?:(?:https?|ssh)://(?:[^/@]+@)?github\.com/|(?:[^/@:]+@)?github\.com:)(.+?)(?:\.git)?/?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class InitResult:
    stacks: tuple[ProjectStack, ...]
    created: tuple[str, ...]  # includes .rapid-ship/kit.lock; empty when there are conflicts
    skipped: tuple[str, ...]  # seeded files that already existed; rs-setup merges them
    conflicts: tuple[str, ...]  # "path: reason"; when present, init wrote nothing
    branch: str = ""  # the branch that holds the Kit commit; "" when there are conflicts
    commit: str = ""  # the Kit commit; "" when there are conflicts
    base: str = ""  # starting branch, or starting commit for a detached HEAD
    first_commit: str = ""  # empty commit created on the initially unborn branch
    # Tool settings, hooks and workflows the repository already had, for rs-setup to combine with
    # devctl's checks. Listed only when init succeeded.
    existing_checks: tuple[str, ...] = ()


def resolve_variables(
    root: Path,
    *,
    name: str | None = None,
    package: str | None = None,
    owner: str | None = None,
    repository: str | None = None,
) -> dict[str, str]:
    """The four template variables the lock records. These values are substituted into TOML
    strings and CODEOWNERS, so each is validated. An absent owner is "".
    Rendering derives the fifth, code_owner, from the owner.

    Without package, it is the root pyproject.toml's [project] name as an import name, else
    it comes from the project name.
    """
    if repository is not None and not _REPOSITORY.fullmatch(repository):
        raise KitError(f"repository {repository!r} is not owner/name; check --repository")
    if repository is None:
        repository = _origin_repository(root)
    project_name = _default_project_name(root, repository) if name is None else name
    if not _PROJECT_NAME.fullmatch(project_name):
        raise KitError(f"project name {project_name!r} is not a valid project name; check --name")
    if package is None:
        declared = _project_name(
            root, ".", "Fix it, or pass --package to name the package without it."
        )
        package = (
            _import_name(declared)
            if declared
            else re.sub(r"[^a-z0-9]+", "_", project_name.lower()).strip("_")
        )
    if not package.isidentifier() or keyword.iskeyword(package):
        raise KitError(f"package {package!r} is not a Python package name; check --package")
    if owner is not None and (len(owner) > _MAX_LOGIN or not _LOGIN.fullmatch(owner)):
        raise KitError(f"owner {owner!r} is not a GitHub login; check --owner")
    return {
        "project_name": project_name,
        "package": package,
        "owner": owner or "",
        "repository": repository or "",
    }


def _default_project_name(root: Path, repository: str | None) -> str:
    """Use the resolved repository name, else the main checkout's directory name.

    A linked worktree shares the main checkout's name. Outside a work tree, or when git
    cannot run, use root's own directory name.
    """
    if repository is not None:
        return repository.partition("/")[2]
    try:
        common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    except (KitError, KitRefusal, OSError):
        return root.resolve().name
    git_dir = Path(os.fsdecode(common.rstrip(b"\n")))
    # Another layout, such as a bare repository or a submodule, has no main checkout to name.
    return git_dir.parent.name if git_dir.name == ".git" else root.resolve().name


def _origin_repository(root: Path) -> str | None:
    """Read only the validated owner/name; the remote URL may contain credentials."""
    try:
        url = git(root, "remote", "get-url", "origin", allowed=(0, 2))
    except (KitError, KitRefusal, OSError):
        return None
    return _github_repository(os.fsdecode(url).strip())


def _github_repository(url: str) -> str | None:
    """The owner/name in a github.com remote URL, else None for any other host or shape."""
    match = _GITHUB_REMOTE.fullmatch(url)
    if match is None or not _REPOSITORY.fullmatch(match[1]):
        return None
    return match[1]


def _import_name(distribution: str) -> str:
    """The import name of a distribution name: lowercase, each run of - _ . replaced by _."""
    return _SEPARATORS.sub("_", distribution.lower())


def _project_name(root: Path, directory: str, fix: str) -> str | None:
    """The [project] name in directory's pyproject.toml, or None when it has none.

    A file that cannot be read or parsed raises a KitError that ends with fix.
    """
    relative = under(directory, "pyproject.toml")
    try:
        document = tomllib.loads(safe_path(root, relative).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (
        OSError,
        UnicodeDecodeError,
        tomllib.TOMLDecodeError,
        RecursionError,
        UnsafePath,
    ) as error:
        raise KitError(f"init wrote nothing: cannot read {relative} ({error}). {fix}") from error
    project = document.get("project")
    name = project.get("name") if isinstance(project, dict) else None
    return name if isinstance(name, str) and name else None


def _fix(stack: ProjectStack) -> str:
    """The next step when an existing Python stack's package directory cannot be found."""
    if stack.directory == ".":
        return "Pass --package naming the package directory, then run init again."
    return (
        f"Fix {under(stack.directory, 'pyproject.toml')} so that it has a [project] name whose "
        f"package directory exists, or run init without --stack python={stack.directory}."
    )


def _own_package(root: Path, stack: ProjectStack) -> str:
    """The import name of the [project] name in a stack's own pyproject.toml."""
    declared = _project_name(root, stack.directory, _fix(stack))
    if not declared:
        raise KitError(
            f"init wrote nothing: the python stack in {stack.directory} has no package directory: "
            f"{under(stack.directory, 'pyproject.toml')} has no [project] name, so init could "
            f"not tell where to look. {_fix(stack)}"
        )
    return _import_name(declared)


def _package_root(tracked: Sequence[str], stack: ProjectStack, package: str) -> str:
    """src/<package>, else <package> for a flat layout: the first that holds a tracked file,
    relative to the stack's directory."""
    candidates = [f"src/{package}", package]
    for candidate in candidates:
        if any(path.startswith(f"{under(stack.directory, candidate)}/") for path in tracked):
            return candidate
    looked = " or ".join(under(stack.directory, candidate) for candidate in candidates)
    raise KitError(
        f"init wrote nothing: the python stack in {stack.directory} has no package directory: "
        f"init looked in {looked} and found no tracked file. {_fix(stack)}"
    )


def _existing_source_roots(
    root: Path,
    stacks: Sequence[ProjectStack],
    new_projects: Sequence[ProjectStack],
    variables: Mapping[str, str],
) -> dict[str, str]:
    """The source root of each existing Python stack, keyed source_root:<directory> as the lock
    records it. A new stack's seeds create its own, src/<package>.

    The root stack's package is the project's, so an explicit --package wins. Another stack's is
    its own [project] name. A stack without a package directory raises a KitError, which stops
    init before it writes anything.
    """
    existing = [s for s in stacks if s.name == "python" and s not in new_projects]
    if not existing:
        return {}
    tracked = [os.fsdecode(path) for path in git(root, "ls-files", "-z", "--cached").split(b"\0")]
    return {
        f"source_root:{stack.directory}": _package_root(
            tracked,
            stack,
            variables["package"] if stack.directory == "." else _own_package(root, stack),
        )
        for stack in existing
    }


def init_repository(
    root: Path,
    *,
    stacks: Sequence[ProjectStack],
    variables: Mapping[str, str],
    templates_root: Path | None = None,
) -> InitResult:
    root = root.resolve()
    start = _check_init_start(root)
    if not stacks:
        raise KitError(proposal(detect_stacks(root)))
    stacks = checked_stacks(root, stacks)
    manifest = load_manifest(templates_root)
    new_projects = [
        s
        for s in stacks
        if (marker := KITS[s.name].new_project_marker)
        and not os.path.lexists(root / under(s.directory, marker))
    ]
    variables = {**variables, **_existing_source_roots(root, stacks, new_projects, variables)}
    templates = render_files(stacks, variables, (), new_projects=new_projects, root=templates_root)
    writes, skipped, conflicts = _plan(root, templates)
    if conflicts:
        return InitResult(stacks, (), tuple(skipped), tuple(conflicts))
    existing_checks = find_existing_checks(
        root, [s.directory for s in stacks]
    )  # before the branch and the writes: as it was
    version = installed_version()
    lock = Lock(version, stacks, dict(variables), tuple(entry_for(t) for t in templates))
    current = head_branch(root)
    base = current or start or ""
    first_commit = ""
    if start is None:
        try:
            git(root, "commit", "--allow-empty", "--quiet", "--message", FIRST_COMMIT_MESSAGE)
        except KitError as error:
            raise KitError(f"init stopped ({error})") from error
        first_commit = git(root, "rev-parse", "HEAD").decode().strip()
    undo = Undo(root)
    branch_created = False
    try:
        git(root, "branch", "--quiet", INIT_BRANCH)
        branch_created = True
        # git can fail after it has switched, so the switch is undone like a write.
        git(root, "switch", "--quiet", INIT_BRANCH)
        created = _write(root, writes, manifest.executable, lock, undo)
        commit_paths(root, created, f"chore: vendor the rapid-ship Kit {version}")
    except (OSError, KitError) as error:
        raise _stopped(
            root,
            error,
            undo,
            base,
            detached=current is None,
            first_commit=first_commit,
            branch_created=branch_created,
        ) from error
    commit = git(root, "rev-parse", "HEAD").decode().strip()
    return InitResult(
        stacks,
        tuple(created),
        tuple(skipped),
        (),
        INIT_BRANCH,
        commit,
        base,
        first_commit,
        existing_checks,
    )


def _check_init_start(root: Path) -> str | None:
    top = work_tree_root(root)
    if top != root:
        raise KitRefusal(f"run init from the top of the work tree, {top}")
    dirty = changed_paths(root)
    if dirty:
        raise KitRefusal(_dirty(dirty))
    if os.path.lexists(root / LOCK_PATH):
        raise KitRefusal(f"{LOCK_PATH} exists; use rapid-ship status or rapid-ship sync")
    start = head_commit(root)
    if git(root, "branch", "--list", INIT_BRANCH).strip():
        raise KitRefusal(
            f"branch {INIT_BRANCH} exists; a previous init may have committed the Kit there. "
            f"Open its pull request, or delete it with git branch -D {INIT_BRANCH}"
        )
    return start


def _dirty(paths: Sequence[str]) -> str:
    listed = [f"  {path}" for path in paths[:_LISTED]]
    if len(paths) > _LISTED:
        listed.append(f"  and {len(paths) - _LISTED} more")
    return "\n".join(
        [
            "the work tree has changes, so init wrote nothing. Uncommitted and untracked paths:",
            *listed,
            "Your coding agent can help commit or stash them; then run rapid-ship init again.",
        ]
    )


def _stopped(
    root: Path,
    error: Exception,
    undo: Undo,
    base: str,
    *,
    detached: bool,
    first_commit: str,
    branch_created: bool,
) -> KitError:
    """Remove what init created, return to where it started, and say what is left to do."""
    try:
        undo.restore()
    except OSError as failure:
        return KitError(
            f"init stopped ({error}) and could not remove every file it created ({failure}); "
            "check git status"
        )
    done = f"init stopped ({error}) and removed the files it had created"
    try:
        if branch_created:
            leave_branch(root, base, INIT_BRANCH, detached=detached)
        if first_commit:
            git(root, "update-ref", "-d", f"refs/heads/{base}", first_commit)
    except KitError as failure:
        return KitError(
            f"{done}, but could not go back ({failure}); "
            f"run git reset, git switch {base} and git branch -D {INIT_BRANCH}"
        )
    deleted = " and the empty first commit" if first_commit else ""
    return KitError(f"{done}; back on {base}, {INIT_BRANCH}{deleted} deleted")


def _plan(
    root: Path, templates: Sequence[Template]
) -> tuple[list[tuple[Template, Path]], list[str], list[str]]:
    """Sort the templates into writes, skipped seeded files and conflicts. Nothing is written."""
    writes: list[tuple[Template, Path]] = []
    skipped: list[str] = []
    conflicts: list[str] = []
    checked: set[str] = set()
    seeded = {template.path for template in templates if template.kind == "seeded"}
    for path in [*(template.path for template in templates), LOCK_PATH]:
        try:
            safe_path(root, path)
        except UnsafePath as error:
            # init never writes over a seeded file, so a seeded file that is itself a link, such
            # as CLAUDE.md -> AGENTS.md, is skipped below. A link above it is still a conflict.
            if path not in seeded or not _directories_are_real(root, path):
                conflicts.append(str(error))
                continue
        checked.add(path)
    for template in templates:
        if template.path not in checked:
            continue
        target = locate(root, template.path)
        blocker = next(
            (
                p
                for p in reversed(target.parents)
                if p.is_relative_to(root) and p != root and p.exists() and not p.is_dir()
            ),
            None,
        )
        if blocker is not None:
            conflicts.append(f"{template.path}: {blocker.relative_to(root)} is not a directory")
        elif os.path.lexists(target):
            if template.kind == "managed":
                conflicts.append(f"{template.path}: exists")
            else:
                skipped.append(template.path)
        else:
            writes.append((template, target))
    candidates = [template.path for template, _ in writes]
    if LOCK_PATH in checked:
        candidates.append(LOCK_PATH)
    conflicts += _ignored_by_git(root, candidates)
    return writes, skipped, conflicts


def _ignored_by_git(root: Path, candidates: Sequence[str]) -> list[str]:
    """A conflict for each candidate that git ignores."""
    # A Kit file that git ignores could never be committed, so CI would run without it.
    if not candidates:
        return []
    output = git(
        root,
        "check-ignore",
        "-z",
        "--stdin",
        stdin=b"\0".join(map(os.fsencode, candidates)),
        allowed=(0, 1),
        literal=False,  # check-ignore refuses pathspec flags; stdin paths are literal
    )
    return [
        f"{os.fsdecode(path)}: ignored by git, so it could not be committed"
        for path in output.split(b"\0")
        if path
    ]


def _directories_are_real(root: Path, path: str) -> bool:
    """True when no directory on the way to path is a symlink. path itself may be one."""
    try:
        locate(root, path)
    except UnsafePath:
        return False
    return True


def _write(
    root: Path,
    writes: Sequence[tuple[Template, Path]],
    executable: frozenset[str],
    lock: Lock,
    undo: Undo,
) -> list[str]:
    """Create every file, then the lock, noting each in undo. Returns the created paths."""
    for template, target in writes:
        undo.make_parents(target)
        if template.link is not None:
            target.symlink_to(template.link)
        else:
            create_file(target, template.content or b"", executable=template.path in executable)
        undo.created.append(target)  # only after it exists, so a failed create removes nothing
    undo.make_parents(root / LOCK_PATH)
    undo.created.append(root / LOCK_PATH)  # removed with missing_ok if write_lock fails
    write_lock(root, lock)
    return [*(template.path for template, _ in writes), LOCK_PATH]
