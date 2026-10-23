"""Validate input where it enters the program, into a typed value."""

from typing import Literal, get_args

from {{package}}.errors import UsageError

Level = Literal["debug", "info", "warning", "error"]
LEVELS: tuple[Level, ...] = get_args(Level)  # the allowed values, written once in Level


def parse_level(text: str) -> Level:
    """The log level that `text` names, or a UsageError that lists every level."""
    for level in LEVELS:
        # The comparison narrows `level` to Level, so the return needs no cast.
        if text == level:
            return level
    raise UsageError(f"{text} is not a log level", f"use one of {', '.join(LEVELS)}")
