"""The one module that reads configuration. Every other module takes a Settings.

Ruff bans os.environ and os.getenv in every other file (TID251), and pyproject.toml
exempts this one. See docs/patterns/python-configuration.md.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass

from {{package}}.errors import UsageError
from {{package}}.inputs import Level, parse_level


@dataclass(frozen=True)
class Settings:
    """Every setting, checked. Each comment names its variable, values and default."""

    log_level: Level  # LOG_LEVEL: debug, info, warning or error; default info
    workers: int  # WORKERS: how many tasks run at once, 1 to 32; default 4


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    """Read and check every setting. The first bad value stops with a UsageError.

    `environ` is the process environment unless the caller, such as a test, passes one.
    """
    source = os.environ if environ is None else environ
    return Settings(
        log_level=_log_level(source.get("LOG_LEVEL", "info")),
        workers=_workers(source.get("WORKERS", "4")),
    )


def _log_level(text: str) -> Level:
    try:
        return parse_level(text)
    except UsageError as error:
        # Add the variable's name on top of parse_level's error, never in its place.
        raise UsageError(f"LOG_LEVEL is {text}", error.next_step) from error


def _workers(text: str) -> int:
    next_step = "set it to a whole number from 1 to 32"
    try:
        workers = int(text)
    except ValueError as error:
        raise UsageError(f"WORKERS is {text}", next_step) from error
    if not 1 <= workers <= 32:
        raise UsageError(f"WORKERS is {text}", next_step)
    return workers
