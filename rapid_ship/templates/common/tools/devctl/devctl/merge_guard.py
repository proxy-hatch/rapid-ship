"""The merge guard, G9 (Spec 1 section 4), and find_merge, which names each way to land a change
on the default branch.

Step 1 lists those ways: gh pr merge, which guard checks, and the forms that G3 denies outright,
gh pr merge --admin, a git push to the default branch, and gh api writes through REST or GraphQL.
A gh command run through ./devctl as <role> gh counts as the gh command it runs. Local git is read
only for a git push, a ref path, or a gh pr merge that names no pull request.

guard reads GitHub only through OwnerGet, doctor's GET with the owner's gh sign-in, and only for
gh pr merge. Once it has recognised a merge it denies every merge it cannot check, its own errors
included, so a merge that the running guard cannot check does not pass.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from devctl import process
from devctl.codeowners import protected_changes
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
from devctl.doctor_items import OWNER_GET_TIMEOUT_SECONDS, OwnerGet, OwnerReadError
from devctl.hook_protocols import GUARD_BUDGET_SECONDS, HookSettings
from devctl.merge_guard_github import (
    Unchecked,
    base_patterns,
    changed_files,
    check_state,
    find_pull,
    reviewer_approved,
)

MergeForm = Literal["pr-merge", "admin", "push", "rest", "graphql"]

_ORIGIN = "refs/remotes/origin/"
_FALLBACK = frozenset({"main", "master"})  # the default branch without refs/remotes/origin/HEAD
_GIT_SECONDS = 30.0
_EVERY_BRANCH = frozenset({"--all", "--branches", "--mirror"})  # --branches is --all's new name
_HEADS = "refs/heads/"
_EXPANSION = re.compile(r"[$`]")  # a parameter expansion, or a substitution's $(...)
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

# The guard's four denials, exactly as Spec 1 section 4, step 5 words them.
_CHECK_DENIED = (
    "merge denied: devctl check on PR #{number} at {head} is {state}; wait for it to pass or fix "
    "what it reports, then merge again"
)
_PROTECTED_DENIED = (
    "merge denied: PR #{number} touches the Protected set ({paths}); the owner merges it in "
    "GitHub's web interface"
)
_REVIEW_DENIED = (
    "merge denied: PR #{number} has no Reviewer App approval of its head {head}; have the "
    "Reviewer review that commit, then merge again"
)
_HEAD_DENIED = (
    "merge denied: PR #{number} merges only at the checked head {head}; run {command} "
    "--match-head-commit {head}"
)
# Every other denial, with why the guard cannot check the merge.
_UNCHECKED = (
    "merge denied: the merge guard cannot check this merge: {reason}; fix that, then merge again"
)
_NO_SETTINGS = "the hook cannot read .rapid-ship/project.toml or .github/CODEOWNERS"
_OVER_BUDGET = f"its GitHub reads would pass the {GUARD_BUDGET_SECONDS:.0f}-second budget"


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
    return Merge("push") if any(_lands(spec, deleting, local) for spec in push.refspecs) else None


def _lands(spec: str, deleting: bool, local: LocalBranches) -> bool:
    """Whether a refspec writes a default branch, or with --delete deletes one.

    Its destination is the part after its last ":", or with --delete the whole refspec. ":" alone
    pushes each branch that both sides have. HEAD and @ name the current branch. A * matches any
    text, as in a refspec pattern. The hook cannot read a $ or ` expansion, so a destination that
    holds one names the current branch, when the text before it could start that branch's ref.
    """
    name = spec.removeprefix("+")
    if name == ":" and not deleting:
        return True
    destination = name if deleting else name.rpartition(":")[2]
    if destination in ("HEAD", "@"):
        return local.current in local.default
    ref = _remote_ref(destination)
    expansion = _EXPANSION.search(ref)
    if expansion:
        current = f"{_HEADS}{local.current}"
        return local.current in local.default and current.startswith(ref[: expansion.start()])
    pattern = re.escape(ref).replace(r"\*", ".*")
    return any(re.fullmatch(pattern, f"{_HEADS}{branch}") for branch in local.default)


def _remote_ref(destination: str) -> str:
    """The ref a destination names on the remote: git reads heads/<branch> as
    refs/heads/<branch>, and a name outside refs/ as a branch."""
    if destination.startswith("refs/"):
        return destination
    return f"refs/{destination}" if destination.startswith("heads/") else _HEADS + destination


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


def cannot_check(reason: str) -> str:
    """The denial of a merge that the guard cannot check, with the reason."""
    return _UNCHECKED.format(reason=reason)


def guard(
    merge: Merge,
    settings: HookSettings | None,
    owner_get: OwnerGet,
    branches: Callable[[], LocalBranches],
    elapsed: Callable[[], float],
) -> str | None:
    """The merge guard's denial of a pr-merge, or None: no decision.

    settings None means none were read, so the guard cannot tell whether Agent identity is on and
    denies before any read. branches is called only for a merge that names no pull request, and
    elapsed, the seconds since the hook run started, before each read.
    """
    if settings is None:
        return cannot_check(_NO_SETTINGS)
    try:
        return _checked(merge, settings, _budgeted(owner_get, elapsed), branches)
    except Unchecked as unchecked:
        return cannot_check(str(unchecked))
    except OwnerReadError as error:
        return cannot_check(error.message)
    except Exception as error:  # noqa: BLE001  # rs-exception: EX-12
        message = " ".join(str(error).splitlines())
        return cannot_check(f"the guard failed: {type(error).__name__}: {message}")


def _budgeted(owner_get: OwnerGet, elapsed: Callable[[], float]) -> OwnerGet:
    """owner_get, refused before a read that could end past GUARD_BUDGET_SECONDS."""

    def read(path: str) -> object:
        if elapsed() + OWNER_GET_TIMEOUT_SECONDS > GUARD_BUDGET_SECONDS:
            raise Unchecked(_OVER_BUDGET)
        return owner_get(path)

    return read


def _checked(
    merge: Merge, settings: HookSettings, read: OwnerGet, branches: Callable[[], LocalBranches]
) -> str | None:
    """Read the PR, CODEOWNERS on its base, its files, its reviews with Agent identity on, and its
    check runs, in that order, and deny with the first message that applies.

    The Protected set comes first, because waiting on a check cannot fix a PR only the owner can
    merge, so a Protected PR is denied before its reviews and check runs are read. The review
    comes after the check, because fixing a failed check pushes a new head that needs a new
    review, and before the head, because the retry that message names would be denied without it.
    """
    repository = merge.repository or settings.repository
    pull = find_pull(read, merge.target, repository, lambda: branches().current)
    patterns = base_patterns(read, pull)
    protected = protected_changes(patterns, changed_files(read, pull))
    if protected:
        return _PROTECTED_DENIED.format(number=pull.number, paths=", ".join(protected))
    slug = settings.reviewer_app_slug
    approved = not settings.agent_identity or reviewer_approved(read, pull, slug)
    state = check_state(read, pull)
    if state != "success":
        return _CHECK_DENIED.format(number=pull.number, head=pull.head, state=state)
    if not approved:
        return _REVIEW_DENIED.format(number=pull.number, head=pull.head)
    if merge.head != pull.head:
        command = shlex.join(merge.command)
        return _HEAD_DENIED.format(number=pull.number, head=pull.head, command=command)
    return None
