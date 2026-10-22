"""Shell splitting, and the git and gh forms that devctl hook's rules read.

simple_commands splits a command line into simple commands as the shell does. parse_command
names the program of one, and parse_push, parse_api and gh_subcommand read the arguments of
git push, gh api, and gh pr or gh issue. hook.py and merge_guard.py share them. The hook
follows no script, alias, sh -c string or wrapper other than devctl as (Spec 1 section 4).
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Collection, Iterable, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

_PUNCTUATION = "();<>|&`\n"
# <<WORD, <<-WORD, <<'WORD' or <<"WORD" opens a heredoc; the here-string <<< does not.
_HEREDOC = re.compile(
    r"""(?<!<)<<(?!<)(-?)[ \t]*(?:'([^'\n]*)'|"([^"\n]*)"|\\?([^\s;&|()<>'"`]+))"""
)
# A file-descriptor number written directly before a redirection, as the 2 of 2>&1.
_DESCRIPTOR = re.compile(r"(?<![^\s;&|()<>`])\d+(?=[<>])")
_WORD_BREAKS = frozenset(" \t\n;&|()<>`")  # an unescaped one of these ends a word
# Reserved words that stand before a command, as in "if git push; then git log; fi".
_RESERVED = frozenset({"!", "{", "do", "elif", "else", "if", "then", "time", "until", "while"})
_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# git's global options that take the next word as their value.
_GIT_VALUED = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"})
_PUSH_VALUED = frozenset({"-o", "--push-option", "--repo", "--receive-pack", "--exec"})
_FORCE = frozenset({"--force", "-f", "--force-with-lease", "--force-if-includes"})
_API_FIELDS = frozenset({"-f", "--raw-field", "-F", "--field"})
_API_VALUED = _API_FIELDS | {
    "-X",
    "--method",
    "-H",
    "--header",
    "--input",
    "-q",
    "--jq",
    "-t",
    "--template",
    "--hostname",
    "-p",
    "--preview",
    "--cache",
}
_API_URL = "https://api.github.com/"
REPOSITORY_OPTIONS = frozenset({"-R", "--repo"})  # gh's options that name another repository


def simple_commands(line: str) -> list[tuple[str, ...]]:
    """Each simple command of a command line, as the words the shell passes it.

    Heredoc bodies, comments and redirections are left out, and so is a reserved word such as
    if or then before a command. A subshell, $( ... ), backticks and <( ... ) give their contents
    as commands of their own. Raises ValueError when shell rules cannot split the line, such as
    for an unclosed quote outside a heredoc: the shell rejects it too.
    """
    text = _DESCRIPTOR.sub("", _joined_without_comments(_without_heredoc_bodies(line)))
    lexer = shlex.shlex(text, posix=True, punctuation_chars=_PUNCTUATION)
    lexer.whitespace = lexer.whitespace.replace("\n", "")  # a newline separates commands
    lexer.whitespace_split = True  # keeps HEAD:refs/heads/main, +task and {owner} whole
    lexer.commenters = ""  # comments are gone; shlex's would also swallow the newline after one
    return _split(lexer)


def _without_heredoc_bodies(text: str) -> str:
    """text without each heredoc's body: the lines after a <<WORD line, up to the line WORD.

    This reads the raw text, quotes and comments included, so a <<WORD inside quotes hides the
    lines after it, a bypass that Spec 1 section 4's limits accept.
    """
    kept: list[str] = []
    ends: list[tuple[str, bool]] = []  # each open heredoc's WORD, and whether <<- strips tabs
    for line in text.split("\n"):
        if ends:
            word, tabs = ends[0]
            if (line.lstrip("\t") if tabs else line) == word:
                ends.pop(0)
            continue
        kept.append(line)
        ends = [(m[2] or m[3] or m[4] or "", m[1] == "-") for m in _HEREDOC.finditer(line)]
    return "\n".join(kept)


def _joined_without_comments(text: str) -> str:
    """text with each line that a backslash continues joined, and without its comments.

    A comment runs from a # that starts an unquoted word to the end of its line; one such as
    "# don't" would otherwise open a quote that never closes. A # after an escaped space, as in
    a\\ #b, or after a backslash-newline inside a word, is part of that word. A backslash-newline
    outside single quotes is removed, as the shell removes it, so the next line stays in the
    same command.
    """
    kept: list[str] = []
    quote = ""
    word_start = True  # a # here starts a comment
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and quote != "'":
            escape = text[index : index + 2]
            if escape != "\\\n":  # a removed backslash-newline leaves word_start as it was
                kept.append(escape)
                word_start = False
            index += 2
            continue
        if quote:
            quote = "" if char == quote else quote
        elif char in "'\"":
            quote = char
        elif char == "#" and word_start:
            end = text.find("\n", index)
            index = len(text) if end < 0 else end
            continue
        kept.append(char)
        word_start = not quote and char in _WORD_BREAKS
        index += 1
    return "".join(kept)


def _split(tokens: Iterable[str]) -> list[tuple[str, ...]]:
    commands: list[list[str]] = [[]]
    target = False  # the next word is a redirection's target
    for token in tokens:
        if token and all(char in _PUNCTUATION for char in token):
            separates, target = _operator(token)
            if separates and commands[-1]:
                commands.append([])
        elif target:
            target = False
        else:
            commands[-1].append(token)
    found = (_past_reserved_words(words) for words in commands)
    return [words for words in found if words]


def _operator(token: str) -> tuple[bool, bool]:
    """Whether a run of punctuation ends the simple command, and whether a target follows it.

    A run that holds < or > is a redirection, such as >, the >& of 2>&1, &> or <<; a ) or ;
    before it still ends the command. <( and >( start process substitution, whose contents are
    a command of their own. Every other run, such as ;, &&, |, & or a newline, ends the command.
    """
    positions = [at for at in (token.find("<"), token.find(">")) if at >= 0]
    if not positions:
        return True, False
    before, redirection = token[: min(positions)], token[min(positions) :]
    if redirection.endswith("("):
        return True, False
    return bool(before.removesuffix("&")), True  # the & of &> belongs to the redirection


def _past_reserved_words(words: list[str]) -> tuple[str, ...]:
    start = 0
    while start < len(words) and words[start] in _RESERVED:
        start += 1
    return tuple(words[start:])


@dataclass(frozen=True)
class Command:
    words: tuple[str, ...]  # the simple command as written
    program: Literal["git", "gh", "other"]
    args: tuple[str, ...]  # after the program; for git, after its global options
    through_devctl: bool  # gh run as ./devctl as <role> gh


def parse_command(words: Sequence[str]) -> Command:
    """Name the program of a simple command, after any leading NAME=value words.

    The program matches by basename, so /usr/bin/git is git. ./devctl as <role> gh <args>
    counts as gh <args>; no other wrapper is followed.
    """
    written = tuple(words)
    start = next((at for at, word in enumerate(written) if not _ASSIGNMENT.match(word)), None)
    if start is None:
        return Command(written, "other", (), False)
    name, rest = PurePosixPath(written[start]).name, written[start + 1 :]
    if name == "git":
        return Command(written, "git", _past_git_options(rest), False)
    if name == "gh":
        return Command(written, "gh", rest, False)
    if name == "devctl" and len(rest) >= 3 and rest[0] == "as" and rest[2] == "gh":
        return Command(written, "gh", rest[3:], True)
    return Command(written, "other", rest, False)


def _past_git_options(rest: tuple[str, ...]) -> tuple[str, ...]:
    index = 0
    while index < len(rest) and rest[index].startswith("-"):
        index += 2 if rest[index] in _GIT_VALUED else 1
    return rest[index:]


@dataclass(frozen=True)
class Argument:
    """One option, or one positional word, of a command's arguments."""

    option: str | None  # "--body" or "-b", without its value; None: a positional word
    value: str | None  # the option's value, or the positional word
    start: int  # the index of its first word
    end: int  # the index after its last word


def read_arguments(args: Sequence[str], valued: Collection[str]) -> list[Argument]:
    """Each option and positional word of args, read as git and gh read them.

    An option in valued takes the next word as its value, unless it is given after "=" or, for
    a short option, attached; in a cluster such as -uf, each letter is an option up to one that
    takes a value. "--" ends the options.
    """
    found: list[Argument] = []
    index = 0
    while index < len(args):
        word = args[index]
        if word == "--":
            found += (
                Argument(None, rest, at, at + 1) for at, rest in enumerate(args) if at > index
            )
            break
        if word.startswith("--"):
            found.append(_long_option(args, index, valued))
        elif word.startswith("-") and word != "-":
            found += _short_options(args, index, valued)
        else:
            found.append(Argument(None, word, index, index + 1))
        index = found[-1].end
    return found


def _long_option(args: Sequence[str], index: int, valued: Collection[str]) -> Argument:
    name, equals, value = args[index].partition("=")
    if equals:
        return Argument(name, value, index, index + 1)
    if name in valued and index + 1 < len(args):
        return Argument(name, args[index + 1], index, index + 2)
    return Argument(name, None, index, index + 1)


def _short_options(args: Sequence[str], index: int, valued: Collection[str]) -> list[Argument]:
    word = args[index]
    found: list[Argument] = []
    for at in range(1, len(word)):
        name = f"-{word[at]}"
        if name not in valued:
            found.append(Argument(name, None, index, index + 1))
        elif attached := word[at + 1 :]:
            return [*found, Argument(name, attached.removeprefix("="), index, index + 1)]
        elif index + 1 < len(args):
            return [*found, Argument(name, args[index + 1], index, index + 2)]
        else:
            return [*found, Argument(name, None, index, index + 1)]
    return found


@dataclass(frozen=True)
class Push:
    """The arguments of git push."""

    options: frozenset[str]  # each option given, such as "--force" or "-f", without its value
    remote: str | None  # the first positional word
    refspecs: tuple[str, ...]  # the positional words after the remote

    @property
    def force(self) -> bool:
        """--force, -f, --force-with-lease, --force-if-includes, or a refspec that starts +."""
        return bool(self.options & _FORCE) or any(spec.startswith("+") for spec in self.refspecs)


def parse_push(args: Sequence[str]) -> Push:
    """git push's arguments, from the words after push."""
    found = read_arguments(args, _PUSH_VALUED)
    words = [item.value for item in found if item.option is None and item.value is not None]
    options = frozenset(item.option for item in found if item.option is not None)
    return Push(options, words[0] if words else None, tuple(words[1:]))


@dataclass(frozen=True)
class ApiCall:
    """The arguments of gh api."""

    method: str  # upper case: -X or --method; else POST with a field or --input, else GET
    endpoint: str  # without https://api.github.com/, the slashes around it and the query
    fields: tuple[str, ...]  # the key=value of each -f, -F, --field and --raw-field
    body: bool  # a field or --input sends a request body


def parse_api(args: Sequence[str]) -> ApiCall:
    """gh api's arguments, from the words after api."""
    found = read_arguments(args, _API_VALUED)
    methods = [item.value for item in found if item.option in ("-X", "--method") and item.value]
    fields = tuple(item.value or "" for item in found if item.option in _API_FIELDS)
    body = bool(fields) or any(item.option == "--input" for item in found)
    words = [item.value for item in found if item.option is None and item.value is not None]
    method = methods[-1].upper() if methods else "POST" if body else "GET"
    endpoint = words[0].removeprefix(_API_URL).partition("?")[0].strip("/") if words else ""
    return ApiCall(method, endpoint, fields, body)


@dataclass(frozen=True)
class Subcommand:
    """The subcommand of gh pr or gh issue, and the words on each side of it."""

    name: str
    before: tuple[str, ...]  # the options before it, such as -R OWNER/NAME
    after: tuple[str, ...]  # its own arguments


def gh_subcommand(args: Sequence[str]) -> Subcommand | None:
    """The first word after gh pr or gh issue that is not an option; None without one.

    args are the words after pr or issue. The value of -R or --repo is not the subcommand.
    """
    for found in read_arguments(args, REPOSITORY_OPTIONS):
        if found.option is None and found.value is not None:
            return Subcommand(found.value, tuple(args[: found.start]), tuple(args[found.end :]))
    return None
