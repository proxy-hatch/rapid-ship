"""devctl hook: the deny and ask rules, then the merge guard, on one normalised tool call.

The first deny wins, and a deny beats an ask; the merge guard runs only when no rule decided.
The rules on skipped hooks, force pushes, merges outside the guard and kit.lock need no settings,
so they apply when the settings are unreadable; the Protected-set and Agent identity rules then
give no decision, and the merge guard denies every merge.
"""

from __future__ import annotations

import argparse
import functools
import re
import shlex
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from devctl.codeowners import codeowners_match, protected_patterns
from devctl.command_line import (
    Command,
    gh_subcommand,
    parse_api,
    parse_command,
    parse_push,
    simple_commands,
)
from devctl.doctor_items import OwnerGet, gh_get
from devctl.hook_protocols import HOOK_COMMAND, Decision, HookSettings, ToolCall, answer, read_event
from devctl.merge_guard import (
    LocalBranches,
    MergeForm,
    cannot_check,
    find_merge,
    guard,
    read_branches,
)
from devctl.repo import RepoError
from devctl.settings import SettingsError, load_project

KIT_LOCK = ".rapid-ship/kit.lock"  # check/kit.py's LOCK_PATH names the same file
PR_READS = frozenset({"view", "list", "status", "diff", "checks", "checkout"})
ISSUE_READS = frozenset({"view", "list", "status"})
# git commit's short options that take a value: the letters after one are that value.
_COMMIT_VALUED = frozenset("mFCctSu")
# A command line that may hold gh pr merge, read as plain text when shell rules cannot split it.
_MERGE_TEXT = re.compile(r"\bgh\b.*\bpr\b.*\bmerge\b", re.DOTALL)

G1 = (
    "G1: --no-verify and git commit -n skip the pre-commit hook; run the command without them, "
    "and fix what the hook reports"
)
G2 = (
    "G2: a force push rewrites published history; push without --force, -f, --force-with-lease, "
    "--force-if-includes or a + refspec, and merge the base branch instead"
)
G3 = (
    "G3: {form} lands a change on the default branch outside the merge guard; open a pull "
    "request and merge it with gh pr merge <number>, without --admin"
)
G4 = "G4: rapid-ship writes .rapid-ship/kit.lock; change Kit files with rapid-ship sync instead"
G5 = (
    "G5: {path} is in the Protected set (CODEOWNERS pattern {pattern}); the owner approves this "
    "edit"
)
G7 = "G7: Agent identity is on, so the Worker App pushes; run ./devctl as worker push"
G8 = "G8: Agent identity is on, so an App makes gh writes; run ./devctl as <role> gh {arguments}"
_G3_FORMS: dict[MergeForm, str] = {
    "admin": "gh pr merge --admin",
    "push": "a git push to the default branch",
    "rest": "a gh api write to a merge, ref or contents endpoint",
    "graphql": "a GraphQL merge or ref mutation",
}


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser(
        "hook",
        help="Answer a Harness's hook event with the Kit's guardrails",
        description=f"{HOOK_COMMAND} reads Claude Code's PreToolUse event on stdin and answers "
        "with a deny, an ask or no decision, with exit 0. It never exits 2, which Claude Code "
        "reads as block: an internal error exits 1, and the tool call goes through.",
    )
    # Optional strings, not choices: argparse exits 2 on a missing or unknown choice, and
    # Claude Code would then block every wired call.
    parser.add_argument("harness", nargs="?", help="the Harness: claude")
    parser.add_argument("event", nargs="?", help="the hook event: pre-tool")
    parser.set_defaults(handler=hook_command)


def hook_command(args: argparse.Namespace) -> int:
    """Answer one event on stdin. Exit 0 with an answer, else 1 with one stderr line; never 2."""
    if args.harness is not None and args.harness != "claude":
        return _fail(f"unknown Harness '{args.harness}'; this devctl wires claude only")
    if args.harness is None or args.event != "pre-tool":
        return _fail(f"usage: {HOOK_COMMAND}")
    try:
        call = read_event("claude", sys.stdin.buffer.read())
        decision, reason = run_hook(call, gh_get)
    except (ValueError, OSError, RepoError, SettingsError) as error:
        return _fail(f"internal error: {error}; the tool call goes through")
    stdout, code = answer("claude", decision, reason)
    sys.stdout.write(stdout)
    return code


def _fail(message: str) -> int:
    sys.stderr.write(f"devctl hook: {' '.join(message.splitlines())}\n")
    return 1


def run_hook(
    call: ToolCall, owner_get: OwnerGet, clock: Callable[[], float] = time.monotonic
) -> tuple[Decision, str]:
    """The answer to one tool call, judged in the repository that holds it.

    An edit belongs to the repository that holds its path, a linked worktree included, and a
    shell command to the one that holds cwd; each Claude Code edit writes one path. Outside every
    repository no settings are read. owner_get is the merge guard's only way to read GitHub, and
    clock times the hook run, whose budget every merge on the line shares.
    Raises ValueError when shell rules cannot split the command line, unless its text holds gh,
    pr and merge in that order: the guard then denies the merge it cannot check.
    """
    started = clock()
    root = work_tree_root(call.edits[0] if call.edits else call.cwd)
    read = read_settings(root) if root is not None else None
    settings = read if isinstance(read, HookSettings) else None
    branches = functools.cache(functools.partial(read_branches, root or call.cwd))
    try:
        decision, reason = decide(call, root, settings, branches)
    except ValueError as error:
        if call.shell is None or not _MERGE_TEXT.search(call.shell):
            raise
        return "deny", cannot_check(f"shell rules cannot split the command line: {error}")
    if decision is not None or call.shell is None:
        return decision, reason
    denial = _guard_merges(call.shell, read, owner_get, branches, lambda: clock() - started)
    return ("deny", denial) if denial is not None else (None, "")


def _guard_merges(
    shell: str,
    read: HookSettings | str | None,
    owner_get: OwnerGet,
    branches: Callable[[], LocalBranches],
    elapsed: Callable[[], float],
) -> str | None:
    """The first merge guard denial among the line's gh pr merge commands, in order, or None.

    read is what read_settings gave: when it gave a reason, the first merge is denied with it, so
    the agent sees the file and the key to fix; None means no repository holds the call.
    """
    for words in simple_commands(shell):
        merge = find_merge(words, branches)
        if merge is None or merge.form != "pr-merge":
            continue
        if isinstance(read, str):
            return cannot_check(read)
        denial = guard(merge, read, owner_get, branches, elapsed)
        if denial is not None:
            return denial
    return None


def work_tree_root(path: Path) -> Path | None:
    """The nearest of path and its ancestors that holds .git, a file or a directory.

    A linked worktree holds a .git file, so an edit there belongs to that worktree, with its
    own lock and CODEOWNERS, while Claude Code's $CLAUDE_PROJECT_DIR names the main checkout.
    """
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists(follow_symlinks=False):
            return candidate
    return None


def read_settings(root: Path) -> HookSettings | str:
    """The settings the Protected-set and Agent identity rules read, or why they cannot be read.

    An unreadable project.toml or CODEOWNERS, or an invalid project.toml, switches those rules off:
    this writes one stderr line and returns the reason, which the merge guard's denial carries.
    A missing CODEOWNERS is an empty Protected set, since nothing is unreadable; doctor reports it.
    """
    try:
        project = load_project(root)
        patterns = protected_patterns(root)
    except (SettingsError, OSError) as error:
        reason = " ".join(str(error).splitlines())
        sys.stderr.write(f"devctl hook: {reason}; G5, G7 and G8 give no decision\n")
        return reason
    reviewer = project.reviewer_app if project.agent_identity else None
    return HookSettings(
        agent_identity=project.agent_identity,
        protected=tuple(patterns or ()),
        repository=project.repository,
        reviewer_app_slug=reviewer.slug if reviewer else None,
    )


def decide(
    call: ToolCall,
    root: Path | None,
    settings: HookSettings | None,
    branches: Callable[[], LocalBranches],
) -> tuple[Decision, str]:
    """The answer to one tool call: a deny or an ask with its reason, or (None, "").

    root is the repository that holds the call, and settings None means they are unreadable.
    branches reads local git, at most once, and only for a git push or a ref path. Raises
    ValueError when shell rules cannot split the command line.
    """
    read_once = functools.cache(branches)
    for words in simple_commands(call.shell) if call.shell is not None else []:
        reason = _shell_rule(parse_command(words), settings, read_once)
        if reason is not None:
            return "deny", reason
    return _edit_rules(call.edits, root, settings)


def _shell_rule(
    command: Command, settings: HookSettings | None, branches: Callable[[], LocalBranches]
) -> str | None:
    """Why the first rule that applies denies one simple command, or None."""
    pushing = command.program == "git" and command.args[:1] == ("push",)
    if command.program == "git" and _skips_hooks(command.args):
        return G1
    if pushing and parse_push(command.args[1:]).force:
        return G2
    merge = find_merge(command.words, branches)
    if merge is not None and merge.form != "pr-merge":
        return G3.format(form=_G3_FORMS[merge.form])
    if settings is None or not settings.agent_identity:
        return None
    if pushing:
        return G7
    if command.program == "gh" and not command.through_devctl and _gh_writes(command.args):
        return G8.format(arguments=shlex.join(command.args))
    return None


def _skips_hooks(args: tuple[str, ...]) -> bool:
    """--no-verify in any git command, or -n in git commit, in the words before "--".

    Every word counts, an option's value too, so a message that is literally --no-verify is
    denied as well; the agent rewords it.
    """
    words = args[: args.index("--")] if "--" in args else args
    if "--no-verify" in words:
        return True
    return words[:1] == ("commit",) and any(_holds_n(word) for word in words[1:])


def _holds_n(word: str) -> bool:
    """Whether a short-option word holds -n before any letter that takes a value."""
    if not word.startswith("-") or word.startswith("--"):
        return False
    for letter in word[1:]:
        if letter in _COMMIT_VALUED:
            return False
        if letter == "n":
            return True
    return False


def _gh_writes(args: tuple[str, ...]) -> bool:
    """A gh pr or gh issue subcommand other than a read, or a gh api write."""
    if args[:1] == ("api",):
        api = parse_api(args[1:])
        return api.method != "GET" or api.body
    reads = {"pr": PR_READS, "issue": ISSUE_READS}.get(args[0]) if args else None
    if reads is None:
        return False
    subcommand = gh_subcommand(args[1:])
    return subcommand is not None and subcommand.name not in reads


def _edit_rules(
    edits: Sequence[Path], root: Path | None, settings: HookSettings | None
) -> tuple[Decision, str]:
    """The kit.lock rule, then the Protected-set rule, for each path the edit writes; an edit
    outside root gets no decision.

    Both compare paths in any case: macOS's default file system ignores case, so agents.md writes
    AGENTS.md. On a file system that keeps case, the Protected-set rule also asks before such a
    new file.
    """
    asked: str | None = None
    for path in edits:
        if root is None or not path.is_relative_to(root):
            continue
        relative = path.relative_to(root).as_posix()
        if relative.casefold() == KIT_LOCK:
            return "deny", G4
        pattern = _protecting_pattern(relative, settings)
        if asked is None and pattern is not None:
            asked = G5.format(path=relative, pattern=pattern)
    return ("ask", asked) if asked is not None else (None, "")


def _protecting_pattern(relative: str, settings: HookSettings | None) -> str | None:
    """The first Protected-set pattern that covers a path in any case; None without settings."""
    protected = settings.protected if settings is not None else ()
    folded = relative.casefold()
    return next((one for one in protected if codeowners_match(one.casefold(), folded)), None)
