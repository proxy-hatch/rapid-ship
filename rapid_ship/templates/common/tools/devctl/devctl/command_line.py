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
# The scanner puts _MARK where a substitution was, and the words then carry SUBSTITUTED there:
# the hook cannot know what the substitution prints.
_MARK = "\x00"
SUBSTITUTED = "$(...)"
# The scanner puts _QUOTED before quoted or escaped text, so that shlex never gives it as a token
# of punctuation alone, which _split would read as an operator: ';' and \; are words.
_QUOTED = "\x01"
_NO_QUOTE = "No closing quotation"
# A backslash in double quotes before one of these: the shell removes a newline, and keeps $ and
# ` without the backslash. shlex reads \" and \\ itself and keeps any other backslash, as the
# shell does.
_IN_DOUBLE_QUOTES = {"\n": "", "$": "$", "`": "`"}
# $'...' escapes that name one character; any other escape stays as written.
_ANSI_C = {"n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b"}
_ANSI_C.update({"f": "\f", "v": "\v", "\\": "\\", "'": "'", '"': '"', "?": "?"})


def simple_commands(line: str) -> list[tuple[str, ...]]:
    """Each simple command of a command line, as the words the shell passes it.

    Heredoc bodies, comments, redirections and arithmetic commands, (( ... )), are left out, and
    so is a reserved word such as if or then before a command. A subshell gives its contents as
    commands of their own. So do $( ... ), backticks, <( ... ) and >( ... ), inside double quotes
    too, and so does each of them inside arithmetic: (( ... )), $(( ... )) or $[ ... ]. These
    commands come ahead of the line's other commands. The command that holds a substitution or
    an arithmetic expansion keeps its other words, and SUBSTITUTED stands where it was, joined to
    the text around it. Raises ValueError when shell rules cannot split the line, such as for an
    unclosed quote or $(: the shell rejects it too.
    """
    scanner = _Scanner(line)
    scanned = scanner.scan(close="")
    return [*scanner.commands, *_words(scanned)]


def _words(scanned: str) -> list[tuple[str, ...]]:
    """The simple commands of text the scanner has read, split by shlex."""
    lexer = shlex.shlex(_DESCRIPTOR.sub("", scanned), posix=True, punctuation_chars=_PUNCTUATION)
    lexer.whitespace = lexer.whitespace.replace("\n", "")  # a newline separates commands
    # shlex reads both attributes. whitespace_split keeps HEAD:refs/heads/main, +task and {owner}
    # whole, and commenters is empty because the scanner removed the comments.
    lexer.whitespace_split = True  # noqa: V101  # rs-exception: EX-17
    lexer.commenters = ""  # noqa: V101  # rs-exception: EX-18
    return [
        tuple(word.replace(_QUOTED, "").replace(_MARK, SUBSTITUTED) for word in words)
        for words in _split(lexer)
    ]


class _Scanner:
    """One pass over a command line as the shell reads it, before shlex splits the words.

    It removes comments, heredoc bodies, arithmetic commands and each backslash-newline outside
    single quotes. It puts _QUOTED before quoted or escaped text, and _MARK where each
    substitution or arithmetic expansion was, after it has added the commands inside it to
    commands, innermost first. It turns $'...' into a quoted word that shlex reads.
    """

    def __init__(self, text: str) -> None:
        self.text = text
        self.at = 0
        self.commands: list[tuple[str, ...]] = []
        self.heredocs: list[tuple[str, bool]] = []  # the line's heredocs: WORD, and <<- or not

    def scan(self, close: str) -> str:
        """The text from here up to close, ")" for a substitution or "" for the end."""
        kept: list[str] = []
        depth = 0  # the subshells open inside this substitution
        word_start = True  # a # here starts a comment
        while self.at < len(self.text):
            char = self.text[self.at]
            if close and char == ")" and depth == 0:
                self.at += 1
                return "".join(kept)
            if char == "#" and word_start:
                end = self.text.find("\n", self.at)
                self.at = len(self.text) if end < 0 else end
                continue
            start = self.at
            # (( ... )) is an arithmetic command; ((a) ) falls back to a subshell in a subshell.
            if self.text.startswith("((", start) and self._arithmetic(start + 2):
                kept.append(" ")
                word_start = True
                continue
            self.at = start
            piece, word_start = self._piece(word_start)
            depth += {"(": 1, ")": -1}.get(piece, 0)
            kept.append(piece)
        if close:
            raise ValueError(f"no closing {close}")
        return "".join(kept)

    def _piece(self, word_start: bool) -> tuple[str, bool]:
        """Read what starts here outside quotes: the text to keep, and whether a word can start
        after it."""
        text, at = self.text, self.at
        if self._substitution(process=True):
            return _MARK, False
        if text[at] == "\\":
            escaped = text[at : at + 2]
            self.at += 2
            # A backslash-newline goes and the word goes on; shlex needs a final \ escaped.
            if escaped == "\\\n":
                return "", word_start
            return _QUOTED + escaped.ljust(2, "\\"), False
        if text[at] == "'":
            end = text.find("'", at + 1)
            if end < 0:
                raise ValueError(_NO_QUOTE)
            self.at = end + 1
            return _QUOTED + text[at : end + 1], False
        if text.startswith("$'", at):
            return _QUOTED + self._ansi_c(), False
        if text.startswith(('"', '$"'), at):  # $"..." is a translated "..."
            return _QUOTED + self._double_quoted(), False
        if text.startswith("<<", at):
            return self._here(), True
        self.at += 1
        if text[at] == "\n":
            self._skip_heredoc_bodies()
        return text[at], text[at] in _WORD_BREAKS

    def _substitution(self, process: bool) -> bool:
        """Read a substitution that starts here and add the commands inside it; False when none
        starts here. process: <( ... ) and >( ... ) count, which they do outside double quotes."""
        text, at = self.text, self.at
        if text.startswith("$((", at) and self._arithmetic(at + 3):
            return True
        if text.startswith("$[", at):  # the older form of $(( ... ))
            if not self._arithmetic(at + 2, close="]"):
                raise ValueError("no closing ]")
            return True
        if text.startswith("$(", at) or (process and text.startswith(("<(", ">("), at)):
            self.at = at + 2
            scanned = self.scan(close=")")
            self.commands += _words(scanned)
            return True
        if text.startswith("`", at):
            self.at = at + 1
            inner = _Scanner(self._backquoted())
            scanned = inner.scan(close="")
            self.commands += [*inner.commands, *_words(scanned)]
            return True
        return False

    def _arithmetic(self, start: int, close: str = "))") -> bool:
        """Read arithmetic from start, after its $((, (( or $[, up to close, "))" or "]", with each
        substitution inside it. False, with no command added, when the text ends first or a lone )
        ends it: the shell then reads $((a) ) and ((a) ) as a subshell inside $( ... ) or ( ... ).
        """
        found, self.at, depth = len(self.commands), start, 0
        nesting = {"(": 1, ")": -1} if close == "))" else {"[": 1, "]": -1}
        while self.at < len(self.text):
            char = self.text[self.at]
            if char == close[0] and depth == 0:
                if self.text.startswith(close, self.at):
                    self.at += len(close)
                    return True
                break
            if not self._substitution(process=False):
                depth += nesting.get(char, 0)
                self.at += 1
        del self.commands[found:]
        return False

    def _backquoted(self) -> str:
        """The command between backquotes, from after the first: \\`, \\$ and \\\\ unescaped."""
        inner: list[str] = []
        while self.at < len(self.text):
            char, after = self.text[self.at], self.text[self.at + 1 : self.at + 2]
            if char == "`":
                self.at += 1
                return "".join(inner)
            escaped = char == "\\" and after in ("`", "$", "\\")
            inner.append(after if escaped else char)
            self.at += 2 if escaped else 1
        raise ValueError("no closing `")

    def _double_quoted(self) -> str:
        """A double-quoted string, with _MARK for each substitution in it."""
        self.at += 2 if self.text[self.at] == "$" else 1
        kept = ['"']
        while self.at < len(self.text):
            char = self.text[self.at]
            if char == '"':
                self.at += 1
                return "".join([*kept, '"'])
            if self._substitution(process=False):
                kept.append(_MARK)
                continue
            escaped = self.text[self.at + 1 : self.at + 2] if char == "\\" else ""
            self.at += 1 + len(escaped)
            kept.append(_IN_DOUBLE_QUOTES.get(escaped, char + escaped))
        raise ValueError(_NO_QUOTE)

    def _ansi_c(self) -> str:
        """$'...' as one single-quoted word that shlex reads."""
        decoded: list[str] = []
        self.at += 2
        while self.at < len(self.text):
            char = self.text[self.at]
            if char == "'":
                self.at += 1
                return shlex.quote("".join(decoded))
            escaped = self.text[self.at + 1 : self.at + 2] if char == "\\" else ""
            decoded.append(_ANSI_C.get(escaped, char + escaped) if escaped else char)
            self.at += 1 + len(escaped)
        raise ValueError(_NO_QUOTE)

    def _here(self) -> str:
        """<<< as written, or a heredoc's << and WORD, whose body the next newline skips."""
        if self.text.startswith("<<<", self.at):
            self.at += 3
            return "<<<"
        self.at += 2
        strip_tabs = self.text.startswith("-", self.at)
        self.at += int(strip_tabs)
        while self.text[self.at : self.at + 1] in (" ", "\t"):
            self.at += 1
        word = self._delimiter()
        self.heredocs.append((word, strip_tabs))
        return f"<< {shlex.quote(word)} "

    def _delimiter(self) -> str:
        """A heredoc's WORD without its quotes and backslashes; the shell needs one."""
        start, word = self.at, []
        while self.at < len(self.text) and self.text[self.at] not in _WORD_BREAKS:
            char = self.text[self.at]
            if char in "'\"":
                end = self.text.find(char, self.at + 1)
                if end < 0:
                    raise ValueError(_NO_QUOTE)
                word.append(self.text[self.at + 1 : end])
                self.at = end + 1
            else:
                skip = int(char == "\\")  # a backslash quotes the character after it
                word.append(self.text[self.at + skip : self.at + 1 + skip])
                self.at += 1 + skip
        if self.at == start:
            raise ValueError("a heredoc has no WORD")
        return "".join(word)

    def _skip_heredoc_bodies(self) -> None:
        """After a newline, skip the body of each heredoc opened before it, up to its WORD line;
        a body without that line runs to the end of the text, as the shell reads it."""
        for word, strip_tabs in self.heredocs:
            while self.at < len(self.text):
                end = self.text.find("\n", self.at)
                line = self.text[self.at : len(self.text) if end < 0 else end]
                self.at = len(self.text) if end < 0 else end + 1
                if (line.lstrip("\t") if strip_tabs else line) == word:
                    break
        self.heredocs.clear()


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
    before it still ends the command. Every other run, such as ;, &&, |, &, ( or a newline, ends
    the command. The scanner has already replaced each <( and >( with _MARK.
    """
    positions = [at for at in (token.find("<"), token.find(">")) if at >= 0]
    if not positions:
        return True, False
    before = token[: min(positions)]
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
