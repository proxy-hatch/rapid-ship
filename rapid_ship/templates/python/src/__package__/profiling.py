r"""Find slow code: a workload for py-spy, a sampling profiler. No check times it.

Run it from the project root, after `uv sync`:

    uvx py-spy record -o profile.svg -- \
        .venv/bin/python -m {{package}}.profiling

Open profile.svg in a browser. docs/patterns/python-performance.md says how to read it.
"""

import argparse
from collections.abc import Sequence

from {{package}}.settings import load_settings


def workload(rounds: int) -> int:
    """The code to measure, run `rounds` times.

    Replace its body with the path to speed up, such as a call into the program's entry
    point with a typical input.
    """
    environ = {"LOG_LEVEL": "warning", "WORKERS": "8"}
    return sum(load_settings(environ).workers for _ in range(rounds))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a workload for py-spy.")
    parser.add_argument(
        "--rounds",
        type=int,
        default=5_000_000,
        help="how many times to run the workload (default: %(default)s)",
    )
    args = parser.parse_args(argv)
    workload(args.rounds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
