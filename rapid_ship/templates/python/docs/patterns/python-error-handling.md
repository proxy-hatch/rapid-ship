---
task: Report an error
reference: src/{{package}}/errors.py
enforced_by:
  - ruff:BLE001
  - ruff:S110
  - test:tests/test_errors.py::test_an_error_keeps_its_cause_and_names_the_next_step
---
# Report an error

Fail fast and gracefully: stop at the first error, report it with its cause and what to do next, and never hide, swallow or reword it.

This applies wherever code finds a problem or catches an exception. When the user can fix the problem, such as a bad setting or an unknown input value, raise `UsageError(problem, next_step)` from `{{package}}.errors`. When an exception found the problem, raise it from that exception: `raise UsageError(...) from error`. Let every other exception propagate unchanged, because it is a bug and its traceback is the report. Catch `UsageError` only in the entry point, which writes its text to stderr and exits 1.

The bypass this bans is catching an error and carrying on. Ruff flags `except Exception:` and `except BaseException:` unless the handler re-raises or logs the traceback (BLE001), and a catch-all `except` whose body is only `pass` (S110). A narrow `except ValueError: pass`, a fallback value that masks a failure and an error raised without `from` are the same bypass, which review catches.

## Lessons

- `UsageError` takes the problem and the next step as two arguments, so no caller can leave out what to do. Its text joins them: `WORKERS is four; set it to a whole number from 1 to 32`.
- `settings.py` raises it `from` the `ValueError` that `int` raised. The traceback prints that cause first, so the message for the user adds to the original error and loses nothing.
- `settings.py` stops at the first bad value instead of falling back to a default, so the program never runs with a setting the user did not choose.
- To name `LOG_LEVEL`, `settings.py` raises a new `UsageError` from the one that `parse_level` raised. Context goes on top of an error, never in its place.
- `test_errors.py` checks the exact text and the cause, so a change that drops either one fails.
