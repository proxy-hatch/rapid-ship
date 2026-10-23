---
task: Find slow code
reference: src/{{package}}/profiling.py
enforced_by:
  - test:tests/test_profiling.py::test_the_profiling_entry_point_runs_on_a_small_input
---
# Find slow code

Measure before you speed code up. Profile the slow path with py-spy, a sampling profiler, and change the code that the profile points to, not the code that looks slow.

This applies whenever code is too slow. Put the slow path in `workload` in `{{package}}.profiling`, such as a call into the program's entry point with a typical input, and run it under py-spy. Profile again after the change to confirm the gain.

The bypass this bans is speeding code up by guesswork, and judging speed in a test. `./devctl check` never runs a profiler, because timings are not deterministic: `tests/test_profiling.py` checks only that the entry point runs on a small input.

## Run py-spy

Nothing installs py-spy into the project; `uvx` fetches it for each run. From the project root:

1. Run `uv sync`, so that `.venv` holds the project.
2. Record a profile of the profiling module:

   ```sh
   uvx py-spy record -o profile.svg -- .venv/bin/python -m {{package}}.profiling
   ```

   The command names `.venv/bin/python` because `uvx` puts its own environment first on `PATH`, and the `python` there cannot import `{{package}}`. On macOS, py-spy can read another process only as root, so put `sudo` before the command.
3. Open `profile.svg` in a browser.

## Read the flame graph

- Each bar is a function. The bars in the next row out from it, away from the row that spans the whole graph, are the functions it called.
- A bar's width is its share of the samples: how often the function was running, or waiting for a function it called. Left to right is not time order.
- Look for wide bars far from the root. Where a bar is wider than all the bars it called together, the difference is time spent in that function's own code.
- Hover over a bar to see its file, line and sample count. Click a bar to zoom in, and use Search to highlight a function by name.
- py-spy samples about 100 times a second, so a run must last a few seconds for the graph to rest on hundreds of samples. The default of 5,000,000 rounds suits the seed's workload. After you replace the workload, change `--rounds` until a run lasts a few seconds.

## Lessons

- `profiling.py` is a module with `main(argv)`, so the test calls it in the same process with `--rounds 3`, and py-spy runs the same code with the default of 5,000,000 rounds.
- `--rounds` scales the run without a code change.
- It starts no process and reads no environment, so each run profiles the same code in one process.
- Its test checks that the entry point runs and returns 0, never how long it takes.
