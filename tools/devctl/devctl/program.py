"""The program that a simple command runs, as devctl hook's rules read it: git, gh or another.

parse_command looks past NAME=value words, each wrapper in WRAPPERS and ./devctl as <role> gh.
It splits the string of env -S by the shell's quoting rules, which lack env's own escapes and
its ${NAME} expansions. It does not read the string that sh -c runs, or the words that xargs
reads on stdin.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# git's global options that take the next word as their value. git reads no prefix of a global
# option, and -c takes no attached value.
_GIT_VALUED = frozenset(
    {
        "-C",
        "-c",
        "--git-dir",
        "--work-tree",
        "--namespace",
        "--config-env",
        "--shallow-file",
        "--super-prefix",
        "--attr-source",
    }
)
_GIT_CONFIG = frozenset({"-c", "--config-env"})
_GH_HELP = frozenset({"-h", "--help"})


@dataclass(frozen=True)
class Wrapper:
    """A program that runs the command written after its own options."""

    valued: frozenset[str]  # its options that take the next word as their value
    operands: int = 0  # the words between its options and the command: timeout's DURATION
    splits: frozenset[str] = frozenset()  # valued options whose value it splits into arguments

    def command_at(self, words: tuple[str, ...], start: int) -> tuple[tuple[str, ...], int]:
        """words, with the value of each option in splits replaced by the words it splits into,
        and the index there of the wrapped command: past this wrapper's options, which begin at
        start, and its operands. The wrapper reads the split words as its own arguments, options
        included. A value that does not split, such as one with an unclosed quote, gives
        len(words): the wrapper rejects it and runs nothing.
        """
        at = start
        while at < len(words) and words[at].startswith("-"):
            if words[at] == "--":
                at += 1
                break
            cluster, option, value, end = self._option(words, at)
            if option not in self.splits or value is None:
                at = end
                continue
            try:
                split = shlex.split(value)
            except ValueError:
                return words, len(words)
            words = (*words[:at], *cluster, *split, *words[end:])
            at += len(cluster)
        return words, at + self.operands

    def _option(
        self, words: tuple[str, ...], at: int
    ) -> tuple[tuple[str, ...], str, str | None, int]:
        """The option word at `at`: the options of its cluster before a valued one, that option or
        the word itself, the option's value, and the index after them.

        A long option without "=" takes the next word when it is a prefix of a valued one: GNU
        getopt reads a unique prefix as that option and rejects an ambiguous one. In a cluster of
        short options, the first valued letter takes the rest of the word, or the next word when
        the word ends with it.
        """
        word, following = words[at], words[at + 1] if at + 1 < len(words) else None
        if word.startswith("--"):
            name, equals, value = word.partition("=")
            named = sorted(one for one in self.valued if one.startswith(name))
            option = named[0] if named else name
            if equals:
                return (), option, value, at + 1
            return ((), option, following, at + 2) if named else ((), option, None, at + 1)
        for index in range(1, len(word)):
            option = f"-{word[index]}"
            if option in self.valued:
                cluster = (word[:index],) if index > 1 else ()
                if attached := word[index + 1 :]:
                    return cluster, option, attached, at + 1
                return cluster, option, following, at + 2
        return (), word, None, at + 1


# The options of GNU's and macOS's versions together. The shell's time keyword, with its -p and
# --, is skipped as a reserved word; this entry reads the time program, such as /usr/bin/time.
# The shell's builtin runs a builtin such as command or exec, and zsh's noglob and nocorrect run
# any command.
WRAPPERS = {
    "builtin": Wrapper(frozenset()),
    "caffeinate": Wrapper(frozenset({"-t", "-w"})),
    "command": Wrapper(frozenset()),
    "env": Wrapper(
        frozenset({"-a", "--argv0", "-u", "--unset", "-C", "--chdir", "-S", "--split-string"})
        | {"--env0-from", "--quoting-style", "-P", "-L", "-U"},
        splits=frozenset({"-S", "--split-string"}),
    ),
    "exec": Wrapper(frozenset({"-a"})),
    "nice": Wrapper(frozenset({"-n", "--adjustment"})),
    "nocorrect": Wrapper(frozenset()),
    "noglob": Wrapper(frozenset()),
    "nohup": Wrapper(frozenset()),
    "setsid": Wrapper(frozenset()),
    "stdbuf": Wrapper(frozenset({"-i", "--input", "-o", "--output", "-e", "--error"})),
    "time": Wrapper(frozenset({"-f", "--format", "-o", "--output"})),
    "timeout": Wrapper(frozenset({"-s", "--signal", "-k", "--kill-after"}), operands=1),
    "xargs": Wrapper(
        frozenset(
            {"-a", "--arg-file", "-d", "--delimiter", "-E", "-I", "-J", "-L", "-n", "--max-args"}
            | {"-P", "--max-procs", "-R", "-S", "-s", "--max-chars", "--process-slot-var"}
        )
    ),
}
# Homebrew installs GNU's versions with a g before the name, such as gtimeout and gxargs.
WRAPPERS.update(
    {
        f"g{name}": WRAPPERS[name]
        for name in ("env", "nice", "nohup", "stdbuf", "time", "timeout", "xargs")
    }
)


@dataclass(frozen=True)
class Command:
    words: tuple[str, ...]  # the simple command, each env -S string split into its words
    program: Literal["git", "gh", "other"]
    args: tuple[str, ...]  # after the program; for git, after its global options
    through_devctl: bool  # gh run as ./devctl as <role> gh
    assignments: tuple[str, ...] = ()  # the NAME=value words before the program, env's too
    config: tuple[str, ...] = ()  # git: the key=value of each -c and --config-env


def parse_command(words: Sequence[str]) -> Command:
    """Name the program of a simple command, past NAME=value words and the wrappers.

    The program and each wrapper match by basename, so /usr/bin/git is git. ./devctl as <role>
    gh <args> counts as gh <args>, and env -S <string> as the words that env splits it into. A gh
    command that asks for help is another program: gh then runs nothing else.
    """
    found = tuple(words)
    at = 0
    assignments: list[str] = []
    while at < len(found):
        wrapper = WRAPPERS.get(PurePosixPath(found[at]).name)
        if _ASSIGNMENT.match(found[at]):
            assignments.append(found[at])
            at += 1
        elif wrapper is not None:
            found, at = wrapper.command_at(found, at + 1)
        else:
            break
    if at >= len(found):
        return Command(found, "other", (), False, tuple(assignments))
    name, rest = PurePosixPath(found[at]).name, found[at + 1 :]
    if name == "git":
        config, args = _git_options(rest)
        return Command(found, "git", args, False, tuple(assignments), config)
    if name == "gh" and not _asks_help(rest):
        return Command(found, "gh", rest, False, tuple(assignments))
    devctl_gh = name == "devctl" and len(rest) >= 3 and rest[0] == "as" and rest[2] == "gh"
    if devctl_gh and not _asks_help(rest[3:]):
        return Command(found, "gh", rest[3:], True, tuple(assignments))
    return Command(found, "other", rest, False, tuple(assignments))


def _asks_help(args: Sequence[str]) -> bool:
    """Whether gh's arguments hold -h or --help before any "--", where it is not the value of the
    option written before it.

    gh takes an option's value from the next word, so -b --help sends the body --help. The hook
    does not know which of gh's options take a value, so -h or --help after an option written
    without "=" counts as that option's value. An unresolved expansion before a help token can
    supply such an option, so a word holding "$" or "`" keeps the command classified as gh.
    """
    for at, word in enumerate(args):
        if word == "--" or "$" in word or "`" in word:
            return False
        before = args[at - 1] if at else ""
        if word in _GH_HELP and (not before.startswith("-") or "=" in before):
            return True
    return False


def _git_options(rest: tuple[str, ...]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The values of git's -c and --config-env, and the words after its global options."""
    config: list[str] = []
    at = 0
    while at < len(rest) and rest[at].startswith("-"):
        word = rest[at]
        if word.startswith("--config-env="):
            config.append(word.removeprefix("--config-env="))
        elif word in _GIT_CONFIG and at + 1 < len(rest):
            config.append(rest[at + 1])
        at += 2 if word in _GIT_VALUED else 1
    return tuple(config), rest[at:]
