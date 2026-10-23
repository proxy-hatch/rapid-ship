"""The profiling entry point runs; py-spy, not a test, shows how long it takes."""

from {{package}}.profiling import main


def test_the_profiling_entry_point_runs_on_a_small_input() -> None:
    assert main(["--rounds", "3"]) == 0
