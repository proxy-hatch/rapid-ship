---
task: Validate input
reference: src/{{package}}/inputs.py
enforced_by:
  - type:tests/test_inputs.py
  - test:tests/test_inputs.py::test_an_unknown_value_is_rejected
---
# Validate input

Validate input where it enters the program, into typed values: an enum or a union of literals, never a plain string.

This applies to every value that comes from outside the program: a command-line argument, an environment variable, a file or a request. Parse it once, where it enters, into a type such as `Level`, and pass that type inward. An unknown value stops there with a `UsageError` that lists the allowed values.

The bypass this bans is passing the raw string inward and comparing it later. mypy checks `tests/test_inputs.py`, where `assert_type` holds `parse_level` to returning `Level`, not `str`. Once a value is a `Level`, mypy's strict mode also rejects a comparison with a value outside it, such as `level == "verbose"`.

## Lessons

- `Level` is a union of literals, and `LEVELS` comes from it through `get_args`, so the allowed values are written once, in `Level`.
- `get_args` returns `tuple[Any, ...]`, so mypy cannot check the annotation `tuple[Level, ...]` on `LEVELS`. That annotation is the one step mypy takes on trust, and it sits next to `Level`, where a reader can compare the two.
- `parse_level` returns the item of `LEVELS` that matched, which is already a `Level`, so it needs no `cast`.
- Its `UsageError` lists every allowed value, so the user can fix the input without reading the code.
- `test_inputs.py` checks both sides: `assert_type` for mypy, and a rejected value for pytest.
