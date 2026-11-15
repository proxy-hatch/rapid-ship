"""devctl hook: the deny and ask rules, then the merge guard, on one normalised tool call.

The first deny wins, and a deny beats an ask; the merge guard runs only when no rule decided.
The rules on skipped hooks, force pushes, merges outside the guard and kit.lock need no settings,
so they apply when the settings are unreadable; the Protected-set and Agent identity rules then
give no decision, and the merge guard denies every merge. The Protected-set rule asks, so it runs
only for the Harnesses in PROTECTED_ASK, and only while the repository's settings do not switch it
off with protected_edits false.
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
    GIT_ABBREVIATIONS,
    SUBSTITUTED,
    ApiCall,
    gh_subcommand,
    long_option,
    parse_api,
    parse_push,
    simple_commands,
)
from devctl.doctor_items import OwnerGet, gh_get
from devctl.hook_protocols import (
    FAILURE_OUTCOMES,
    HOOK_COMMANDS,
    PROTECTED_ASK,
    WIRED_HARNESSES,
    Decision,
    HookSettings,
    ToolCall,
    WiredHarness,
    answer,
    failure,
    read_event,
)
from devctl.merge_guard import (
    LocalBranches,
    MergeForm,
    cannot_check,
    find_merge,
    guard,
    read_branches,
)
from devctl.program import Command, parse_command
from devctl.settings import SettingsError, load_project

KIT_LOCK = ".rapid-ship/kit.lock"  # check/kit.py's LOCK_PATH names the same file
# ls and co are gh's own aliases of list and checkout.
PR_READS = frozenset({"view", "list", "ls", "status", "diff", "checks", "checkout", "co"})
ISSUE_READS = frozenset({"view", "list", "ls", "status"})
_HOOKS_PATH = "core.hookspath"  # git reads config names in any case
_ALIAS = "alias."
# git commit's short options that take a value: the letters after one are that value.
_COMMIT_VALUED = frozenset("mFCctSu")
# A command line that may hold gh pr merge, read as plain text when shell rules cannot split it.
_MERGE_TEXT = re.compile(r"\bgh\b.*\bpr\b.*\bmerge\b", re.DOTALL)
# A GraphQL endpoint that parse_api leaves as a URL: a host's /graphql or, on GitHub Enterprise
# Server, its /api/graphql, in any case.
_GRAPHQL_URL = re.compile(r"[a-z][a-z0-9+.-]*://[^/]+/(?:api/)?graphql", re.IGNORECASE)
# What gh's -F fills in a value from the repository, GH_REPO or the current branch.
_GH_PLACEHOLDER = re.compile(r":(?:owner|repo|branch)\b|\{(?:owner|repo|branch)\}")
# One GraphQL token, or one run of what GraphQL ignores. A block string comes before a string,
# which never starts at a triple quote, and each alternative inside a string takes a character in
# one way only, so that backtracking cannot end a string early.
_GRAPHQL_TOKEN = re.compile(
    r"(?P<ignored>[ \t\r\n,]+|#[^\r\n]*)"
    r"|[_A-Za-z][_0-9A-Za-z]*"
    r"|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?"
    r'|"""(?:[^"\\]|\\"""|\\(?!""")|"(?!""))*"""'
    r'|"(?!"")(?:[^"\\\r\n]|\\["\\/bfnrt]|\\u[0-9A-Fa-f]{4})*"'
    r"|\.\.\.|[!$&():=@\[\]{|}]"
)
_GRAPHQL_PAIRS = {")": "(", "]": "[", "}": "{"}  # each closing delimiter and its opening one
_GRAPHQL_NAME = "[_A-Za-z][_0-9A-Za-z]*"
_GRAPHQL_DIRECTIVES = rf"(?:@ {_GRAPHQL_NAME} (?:\( )?)*"
# One top-level definition, in the text that _graphql_operations builds: each token and each
# pair of delimiters, as its opening one, followed by a space.
_GRAPHQL_DEFINITION = re.compile(
    rf"\{{ |(?:(?:query|mutation|subscription) (?:{_GRAPHQL_NAME} )?(?:\( )?"
    rf"|fragment (?!on ){_GRAPHQL_NAME} on {_GRAPHQL_NAME} ){_GRAPHQL_DIRECTIVES}\{{ "
)

G1 = (
    "G1: --no-verify, git commit -n and a core.hooksPath set on the command line skip the "
    "pre-commit hook, and an alias set there hides its command from devctl hook; run the "
    "command without them, and fix what the pre-commit hook reports"
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
        description="devctl hook <harness> pre-tool reads the Harness's pre-tool event on stdin "
        "and answers in its hook protocol with a deny, an ask or no decision. It never exits 2, "
        "which Claude Code and Codex read as block. When devctl itself fails, it writes one "
        "stderr line: for claude and codex it exits 1, so the tool call goes through, and for "
        "agy, which blocks the call on any other exit code, it answers deny with that line as "
        "the reason and exit 0.",
    )
    # Optional strings, not choices: argparse exits 2 on a missing or unknown choice, and the
    # Harness would then block every wired call.
    parser.add_argument("harness", nargs="?", help="the Harness: claude, agy or codex")
    parser.add_argument("event", nargs="?", help="the hook event: pre-tool")
    parser.set_defaults(handler=hook_command)


def hook_command(args: argparse.Namespace) -> int:
    """Answer one event on stdin in the Harness's protocol; never exit 2.

    A failure of devctl's own writes one stderr line and gives the protocol's failure answer.
    """
    harness = next((wired for wired in WIRED_HARNESSES if wired == args.harness), None)
    if harness is None:
        if args.harness is None:
            return _fail(None, f"usage: devctl hook <{'|'.join(WIRED_HARNESSES)}> pre-tool")
        *others, last = WIRED_HARNESSES
        known = f"{', '.join(others)} and {last}"
        return _fail(None, f"unknown Harness '{args.harness}'; this devctl wires {known}")
    if args.event != "pre-tool":
        return _fail(harness, f"usage: {HOOK_COMMANDS[harness]}")
    try:
        call = read_event(harness, sys.stdin.buffer.read())
        decision, reason = run_hook(call, gh_get, protected_ask=harness in PROTECTED_ASK)
    except Exception as error:  # noqa: BLE001  # rs-exception: EX-30
        return _fail(harness, f"internal error: {error}; {FAILURE_OUTCOMES[harness]}")
    stdout, code = answer(harness, decision, reason)
    sys.stdout.write(stdout)
    return code


def _fail(harness: WiredHarness | None, message: str) -> int:
    """Write one stderr line and the Harness's failure answer; exit 1 without a Harness."""
    line = f"devctl hook: {' '.join(message.splitlines())}"
    sys.stderr.write(line + "\n")
    if harness is None:
        return 1
    stdout, code = failure(harness, line)
    sys.stdout.write(stdout)
    return code


def run_hook(
    call: ToolCall,
    owner_get: OwnerGet,
    clock: Callable[[], float] = time.monotonic,
    *,
    protected_ask: bool = True,
) -> tuple[Decision, str]:
    """The answer to one tool call, judged in the repository that holds it.

    An edit belongs to the repository that holds its path, a linked worktree included, and a
    shell command to the one that holds cwd; a patch can write paths in several repositories.
    Outside every repository no settings are read. owner_get is the merge guard's only way to
    read GitHub. clock times the hook run, whose budget every merge on the line shares.
    protected_ask False skips the Protected-set rule, and so does protected_edits false in the
    settings of the repository that holds the call.
    Raises ValueError when shell rules cannot split the command line, unless its text holds gh,
    pr and merge in that order: the guard then denies the merge it cannot check.
    """
    started = clock()
    if len(call.edits) > 1:
        # Each path belongs to its own repository. An outside first path cannot hide a later
        # lock edit, and a deny in a later repository still outranks an earlier ask.
        asked: tuple[Decision, str] = (None, "")
        for path in call.edits:
            result = run_hook(
                ToolCall(None, (path,), call.cwd), owner_get, clock, protected_ask=protected_ask
            )
            if result[0] == "deny":
                return result
            if result[0] == "ask" and asked[0] is None:
                asked = result
        return asked
    root = work_tree_root(call.edits[0] if call.edits else call.cwd)
    read = read_settings(root) if root is not None else None
    settings = read if isinstance(read, HookSettings) else None
    branches = functools.cache(functools.partial(read_branches, root or call.cwd))
    try:
        decision, reason = decide(call, root, settings, branches, protected_ask=protected_ask)
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
    """The work tree's settings that the Protected-set and Agent identity rules read, with the
    repository the merge guard falls back on, or why they cannot be read.

    An unreadable project.toml or CODEOWNERS, or an invalid project.toml, switches the
    Protected-set and Agent identity rules off: this writes one stderr line and returns the
    reason, and the merge guard denies every merge with that reason.
    A missing CODEOWNERS is an empty Protected set, since nothing is unreadable; doctor reports it.
    The Protected set is read whatever protected_edits says.
    """
    try:
        project = load_project(root)
        patterns = protected_patterns(root)
    except (SettingsError, OSError) as error:
        reason = " ".join(str(error).splitlines())
        sys.stderr.write(f"devctl hook: {reason}; G5, G7 and G8 give no decision\n")
        return reason
    return HookSettings(
        agent_identity=project.agent_identity,
        protected=tuple(patterns or ()),
        repository=project.repository,
        protected_edits=project.escalation.protected_edits,
    )


def decide(
    call: ToolCall,
    root: Path | None,
    settings: HookSettings | None,
    branches: Callable[[], LocalBranches],
    *,
    protected_ask: bool = True,
) -> tuple[Decision, str]:
    """The answer to one tool call: a deny or an ask with its reason, or (None, "").

    root is the repository that holds the call, and settings None means they are unreadable.
    branches reads local git, at most once, and only for a git push or a ref path. The
    Protected-set rule runs only when protected_ask is True and settings.protected_edits is true.
    Raises ValueError when shell rules cannot split the command line.
    """
    read_once = functools.cache(branches)
    for words in simple_commands(call.shell) if call.shell is not None else []:
        reason = _shell_rule(parse_command(words), settings, read_once)
        if reason is not None:
            return "deny", reason
    protected = (
        settings.protected
        if settings is not None and protected_ask and settings.protected_edits
        else ()
    )
    return _edit_rules(call.edits, root, protected)


def _shell_rule(
    command: Command, settings: HookSettings | None, branches: Callable[[], LocalBranches]
) -> str | None:
    """Why the first rule that applies denies one simple command, or None."""
    pushing = command.program == "git" and command.args[:1] == ("push",)
    if command.program == "git" and (_skips_hooks(command.args) or _sets_hooks_or_alias(command)):
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
    """--no-verify, or a prefix that git reads as it, in any git command, or -n in git commit.

    Every word counts, an option's value and the words after "--" too: "--" can be an option's
    value, as in git commit -m -- --no-verify, and then the options go on. So a message or a path
    that is literally --no-verify is denied as well; the agent rewords or renames it.
    """
    if any(long_option(word, GIT_ABBREVIATIONS) == "--no-verify" for word in args):
        return True
    return args[:1] == ("commit",) and any(_holds_n(word) for word in args[1:])


def _sets_hooks_or_alias(command: Command) -> bool:
    """Whether git's -c or --config-env sets core.hooksPath or an alias, or a variable set before
    git whose name starts with GIT_CONFIG, such as GIT_CONFIG_KEY_0, names one.

    The rules read the words on the line, not the command an alias stands for, and agents need no
    alias set on the command line.
    """
    keys = [value.partition("=")[0].casefold() for value in command.config]
    variables = (word.partition("=") for word in command.assignments)
    named = [value.casefold() for name, _, value in variables if name.startswith("GIT_CONFIG")]
    return any(key == _HOOKS_PATH or key.startswith(_ALIAS) for key in keys) or any(
        _HOOKS_PATH in value or _ALIAS in value for value in named
    )


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
        return _api_writes(parse_api(args[1:]))
    reads = {"pr": PR_READS, "issue": ISSUE_READS}.get(args[0]) if args else None
    if reads is None:
        return False
    subcommand = gh_subcommand(args[1:])
    return subcommand is not None and subcommand.name not in reads


def _api_writes(api: ApiCall) -> bool:
    """Whether a gh api call is not a read. A GraphQL call reads, whatever its method, only when it
    has no --input and exactly one query field, whose inline document defines queries alone. A
    document from a file or stdin, a placeholder for a substitution or one that gh fills, a
    mutation, a subscription or text that _graphql_operations cannot read makes it a write. Any
    other call reads exactly when its method is GET, which sends its fields as query parameters.
    """
    if api.endpoint != "graphql" and _GRAPHQL_URL.fullmatch(api.endpoint) is None:
        return api.method != "GET"
    documents = [
        value for key, _, value in (field.partition("=") for field in api.fields) if key == "query"
    ]
    if api.has_input or len(documents) != 1:
        return True
    document = documents[0]
    return (
        document.startswith("@")
        or SUBSTITUTED in document
        or _GH_PLACEHOLDER.search(document) is not None
        or _graphql_operations(document) != {"query"}
    )


def _graphql_operations(document: str) -> set[str] | None:
    """The kinds of operation that a GraphQL document defines, or None when it cannot be read.

    A kind is query, mutation or subscription, and a selection set alone is a query. The document
    is unreadable when it holds text that is no token or ignored run of GraphQL, an unterminated
    string, delimiters that do not nest and match, a $ outside every pair of parentheses, as a
    token or inside a string or comment, a top-level definition of another shape, or no operation.
    Inside a selection set only the tokens and their nesting count.
    """
    tokens = _graphql_tokens(document.removeprefix("\ufeff"))
    outer = None if tokens is None else _outer_tokens(tokens)
    if outer is None:
        return None
    text = "".join(f"{token} " for token in outer)
    kinds: set[str] = set()
    at = 0
    while at < len(text):
        definition = _GRAPHQL_DEFINITION.match(text, at)
        if definition is None:
            return None
        keyword = definition.group().partition(" ")[0]
        kinds.add("query" if keyword == "{" else keyword)
        at = definition.end()
    kinds.discard("fragment")
    return kinds or None


def _graphql_tokens(text: str) -> list[str] | None:
    """The tokens of a GraphQL text, or None where no token or ignored run starts. A comment that
    holds a $ stays a token, so that its $ makes the document unreadable outside parentheses.
    """
    tokens: list[str] = []
    at = 0
    while at < len(text):
        found = _GRAPHQL_TOKEN.match(text, at)
        if found is None:
            return None
        at = found.end()
        if found["ignored"] is None or "$" in found.group():
            tokens.append(found.group())
    return tokens


def _outer_tokens(tokens: Sequence[str]) -> list[str] | None:
    """The tokens outside every pair of delimiters, each pair as its opening delimiter.

    None when the delimiters do not nest and match, or a $ stands outside every pair of
    parentheses, as a token or inside a string or comment, where GraphQL has no variable and a
    shell expansion could stand.
    """
    outer: list[str] = []
    open_pairs: list[str] = []
    parentheses = 0  # how many ( are open
    for item in tokens:
        if "$" in item and not parentheses:
            return None
        if item in _GRAPHQL_PAIRS:
            if not open_pairs or open_pairs.pop() != _GRAPHQL_PAIRS[item]:
                return None
            parentheses -= item == ")"
        elif not open_pairs:
            outer.append(item)
        if item in _GRAPHQL_PAIRS.values():
            open_pairs.append(item)
            parentheses += item == "("
    return None if open_pairs else outer


def _edit_rules(
    edits: Sequence[Path], root: Path | None, protected: Sequence[str]
) -> tuple[Decision, str]:
    """The kit.lock rule, then the Protected-set rule with the protected patterns, for each path
    the edit writes; an edit outside root gets no decision.

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
        pattern = _protecting_pattern(relative, protected)
        if asked is None and pattern is not None:
            asked = G5.format(path=relative, pattern=pattern)
    return ("ask", asked) if asked is not None else (None, "")


def _protecting_pattern(relative: str, protected: Sequence[str]) -> str | None:
    """The first Protected-set pattern that covers a path in any case."""
    folded = relative.casefold()
    return next((one for one in protected if codeowners_match(one.casefold(), folded)), None)
