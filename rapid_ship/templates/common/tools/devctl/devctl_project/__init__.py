"""Project verbs and extra check steps for this repository's devctl.

rapid-ship writes this package once; the project owns it afterwards.
"""

from __future__ import annotations

import argparse

from devctl.check.steps import Step
from devctl.metrics.api import Metric


def register(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Add project verbs. Each verb sets a handler that returns the exit code:

    verb = commands.add_parser("seed-demo", help="Load demo data")
    verb.set_defaults(handler=seed_demo)
    """


def check_steps() -> list[Step]:
    """Return extra steps for ./devctl check."""
    return []


def metrics() -> list[Metric]:
    """Return project-defined metrics for ./devctl metrics.

    Each metric must be deterministic and must not run a model; devctl cannot check either. A
    metric that needs a credential other than the GitHub token reads it from the environment.
    """
    return []
