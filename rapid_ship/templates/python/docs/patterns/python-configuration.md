---
task: Read configuration
reference: src/{{package}}/settings.py
enforced_by:
  - banned:os.environ
  - banned:os.getenv
  - test:tests/test_settings.py::test_an_out_of_range_value_is_rejected
---
# Read configuration

One typed settings module reads configuration. It validates every value, with numeric ranges and allowed values, and documents each one in a short inline comment.

This applies to every value the program takes from its environment. To add a setting, add a field to `Settings` in `{{package}}.settings`, with a comment that names its variable, its allowed values and its default. Then read and check the value in `load_settings`. Code that needs a setting takes the `Settings`, or the one value it uses, as an argument.

The bypass this bans is reading the environment anywhere else. Ruff's banned-api rule (TID251) flags `os.environ` and `os.getenv` in every file except `settings.py`, which a per-file entry in `pyproject.toml` exempts. That entry is the owner's setting, like the rest of `pyproject.toml`.

## Lessons

- One frozen dataclass holds every setting. A reader finds them all in one place, and no code changes one after loading.
- `load_settings` checks each value as it reads it: `WORKERS` must be a whole number from 1 to 32, and `LOG_LEVEL` one of four levels. The first bad value stops the program with a `UsageError` that names the variable, its value and what to set instead.
- `load_settings` takes the environment as an argument and reads `os.environ` only when it gets none. Tests pass a plain `dict`, and only the test of that default sets a variable, through pytest's `monkeypatch`.
- `LOG_LEVEL` goes through `parse_level` from `inputs.py`, so the allowed levels are written once.
- Each field's comment names its variable, allowed values and default, beside the field it documents.
