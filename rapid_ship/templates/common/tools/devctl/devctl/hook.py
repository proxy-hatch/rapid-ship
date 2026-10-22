"""devctl hook's rules: G1 to G5, G7 and G8 on one normalised tool call (Spec 1 section 4).

decide applies them in the order of the simple commands, and within one command G1, G2, G3,
G7 and G8; for an edit G4, then G5. The first deny wins, and a deny beats an ask. The hook only
denies or asks: with no rule matched it gives no decision. G1 to G4 need no settings, so they
apply when the settings are unreadable; G5, G7 and G8 then give no decision.
"""

from __future__ import annotations

import functools
import shlex
import sys
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
from devctl.hook_protocols import Decision, HookSettings, ToolCall
from devctl.merge_guard import LocalBranches, MergeForm, find_merge
from devctl.settings import SettingsError, load_project

# check/kit.py names the lock too. The hook runs before every tool call, so it leaves out the
# check package, which loads every step.
KIT_LOCK = ".rapid-ship/kit.lock"
PR_READS = frozenset({"view", "list", "status", "diff", "checks", "checkout"})
ISSUE_READS = frozenset({"view", "list", "status"})
# git commit's short options that take a value: the letters after one are that value.
_COMMIT_VALUED = frozenset("mFCctSu")

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
    """The settings that G5, G7 and G8 read, or why they cannot be read.

    An unreadable project.toml or CODEOWNERS, or an invalid project.toml, switches off all three:
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
    """Why the first of G1, G2, G3, G7 and G8 that applies denies one simple command, or None."""
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
    """G1: --no-verify in any git command, or -n in git commit, in the words before "--".

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
    """G8: a gh pr or gh issue subcommand other than a read, or a gh api write."""
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
    """G4, then G5, for each path the edit writes; an edit outside root gets no decision."""
    asked: str | None = None
    for path in edits:
        if root is None or not path.is_relative_to(root):
            continue
        relative = path.relative_to(root).as_posix()
        if relative == KIT_LOCK:
            return "deny", G4
        pattern = _protecting_pattern(relative, settings)
        if asked is None and pattern is not None:
            asked = G5.format(path=relative, pattern=pattern)
    return ("ask", asked) if asked is not None else (None, "")


def _protecting_pattern(relative: str, settings: HookSettings | None) -> str | None:
    """The first Protected-set pattern that covers a path; None without settings."""
    protected = settings.protected if settings is not None else ()
    return next((pattern for pattern in protected if codeowners_match(pattern, relative)), None)
