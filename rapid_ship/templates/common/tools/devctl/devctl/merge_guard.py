"""The merge guard's forms: find_merge names each way to land a change on the default branch.

Spec 1 section 4, step 1 lists them: gh pr merge, which the merge guard checks, and the forms
that G3 denies outright, gh pr merge --admin, a git push to the default branch, and gh api
writes through REST or GraphQL. A gh command run through ./devctl as <role> gh counts as the
gh command it runs. Local git is read only for a git push or a ref path.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from devctl import process
from devctl.command_line import (
    REPOSITORY_OPTIONS,
    ApiCall,
    Command,
    gh_subcommand,
    parse_api,
    parse_command,
    parse_push,
    read_arguments,
)

MergeForm = Literal["pr-merge", "admin", "push", "rest", "graphql"]

_ORIGIN = "refs/remotes/origin/"
_FALLBACK = frozenset({"main", "master"})  # the default branch without refs/remotes/origin/HEAD
_GIT_SECONDS = 30.0
_EVERY_BRANCH = frozenset({"--all", "--branches", "--mirror"})  # --branches is --all's new name
_DELETE = frozenset({"-d", "--delete"})
_HEAD = "--match-head-commit"
# gh pr merge's options that take a value, which is never the pull request.
_MERGE_VALUED = REPOSITORY_OPTIONS | {
    "-b",
    "--body",
    "-F",
    "--body-file",
    "-t",
    "--subject",
    "-A",
    "--author-email",
    _HEAD,
}
# A pull request's merge, the Merges API, and the Contents API, which commits a file.
_LANDING_PATH = re.compile(r"repos/[^/]+/[^/]+/(?:pulls/[^/]+/merge|merges|contents/.+)")
_REF_PATH = re.compile(r"repos/[^/]+/[^/]+/git/refs/heads/(?P<branch>.+)")
_MUTATIONS = re.compile(
    r"\b(?:mergePullRequest|enablePullRequestAutoMerge|enqueuePullRequest|mergeBranch"
    r"|updateRefs?|createCommitOnBranch)\b"
)


@dataclass(frozen=True)
class LocalBranches:  # read from local git only for a git push, a ref path or a bare merge
    default: frozenset[str]  # origin/HEAD's branch; {"main", "master"} when that ref is missing
    current: str | None  # None: a detached HEAD


@dataclass(frozen=True)
class Merge:  # a way to land a change on the default branch, also through devctl as
    form: MergeForm  # G3 denies all but pr-merge
    target: str | None = None  # pr-merge: the number, URL or branch; None: the branch's PR
    repository: str | None = None  # pr-merge: the -R or --repo value
    head: str | None = None  # pr-merge: the --match-head-commit value
    command: tuple[str, ...] = ()  # pr-merge: the words, without --match-head-commit


def read_branches(root: Path) -> LocalBranches:
    """The default branch from refs/remotes/origin/HEAD, and the branch HEAD names, in root."""
    default = _symbolic_ref(root, "refs/remotes/origin/HEAD")
    branch = default.removeprefix(_ORIGIN) if default and default.startswith(_ORIGIN) else ""
    current = _symbolic_ref(root, "--short", "HEAD")
    return LocalBranches(frozenset({branch}) if branch else _FALLBACK, current)


def _symbolic_ref(root: Path, *args: str) -> str | None:
    """The ref git symbolic-ref names, or None when it fails for any reason."""
    try:
        result = process.run_process(["git", "symbolic-ref", "--quiet", *args], root, _GIT_SECONDS)
    except OSError:  # git is missing, or root is gone
        return None
    if result.returncode != 0 or result.timed_out:
        return None
    return result.stdout.strip() or None


def find_merge(words: Sequence[str], branches: Callable[[], LocalBranches]) -> Merge | None:
    """The way a simple command lands a change on the default branch, or None.

    branches is called only for a git push without --all, --branches or --mirror, and for a gh
    api write to a branch's ref.
    """
    command = parse_command(words)
    if command.program == "git":
        return _push(command.args[1:], branches) if command.args[:1] == ("push",) else None
    if command.program != "gh":
        return None
    if command.args[:1] == ("pr",):
        return _pr_merge(command)
    if command.args[:1] == ("api",):
        return _api(parse_api(command.args[1:]), branches)
    return None


def _push(args: Sequence[str], branches: Callable[[], LocalBranches]) -> Merge | None:
    push = parse_push(args)
    if push.options & _EVERY_BRANCH:
        return Merge("push")
    local = branches()
    if not push.refspecs:  # git push and git push origin push the current branch
        return Merge("push") if local.current in local.default else None
    deleting = bool(push.options & _DELETE)
    if any(_destination(spec, deleting, local) in local.default for spec in push.refspecs):
        return Merge("push")
    return None


def _destination(spec: str, deleting: bool, local: LocalBranches) -> str | None:
    """The branch a refspec writes, or with --delete the branch it deletes; None for a tag."""
    name = spec.removeprefix("+")
    destination = name if deleting else name.rpartition(":")[2]
    if destination == "HEAD":
        return local.current
    if destination.startswith("refs/heads/"):
        return destination.removeprefix("refs/heads/")
    return None if destination.startswith("refs/") else destination


def _pr_merge(command: Command) -> Merge | None:
    subcommand = gh_subcommand(command.args[1:])
    if subcommand is None or subcommand.name != "merge":
        return None
    found = read_arguments(subcommand.after, _MERGE_VALUED)
    if any(item.option == "--admin" for item in found):
        return Merge("admin")
    given = [*read_arguments(subcommand.before, REPOSITORY_OPTIONS), *found]
    repositories = [item.value for item in given if item.option in REPOSITORY_OPTIONS]
    heads = [item for item in found if item.option == _HEAD]
    offset = len(command.words) - len(subcommand.after)
    dropped = {offset + at for item in heads for at in range(item.start, item.end)}
    return Merge(
        "pr-merge",
        target=next((item.value for item in found if item.option is None), None),
        repository=repositories[-1] if repositories else None,
        head=heads[-1].value if heads else None,
        command=tuple(word for at, word in enumerate(command.words) if at not in dropped),
    )


def _api(api: ApiCall, branches: Callable[[], LocalBranches]) -> Merge | None:
    if api.endpoint == "graphql":
        return Merge("graphql") if any(_names_mutation(field) for field in api.fields) else None
    if api.method == "GET":
        return None
    if _LANDING_PATH.fullmatch(api.endpoint):
        return Merge("rest")
    ref = _REF_PATH.fullmatch(api.endpoint)
    return Merge("rest") if ref and ref["branch"] in branches().default else None


def _names_mutation(field: str) -> bool:
    """Whether a query=<text> field given inline names a mutation that lands a change.

    query=@<file> reads a file, which the hook does not read.
    """
    key, _, text = field.partition("=")
    return key == "query" and not text.startswith("@") and _MUTATIONS.search(text) is not None
