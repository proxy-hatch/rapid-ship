"""Validate input where it enters the program, into a typed value."""

from typing import Literal, get_args

from {{package}}.errors import UsageError

Level = Literal["debug", "info", "warning", "error"]
# The allowed values, taken from Level so they are written once. get_args returns
# tuple[Any, ...], so mypy cannot check this annotation: it is the one unchecked step.
LEVELS: tuple[Level, ...] = get_args(Level)


def parse_level(text: str) -> Level:
    """The log level that `text` names, or a UsageError that lists every level."""
    for level in LEVELS:
        if text == level:
            return level  # already a Level, by the annotation on LEVELS, so no cast
    raise UsageError(f"{text} is not a log level", f"use one of {', '.join(LEVELS)}")
