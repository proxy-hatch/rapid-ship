"""Offline: knip's allowlist items in knip.jsonc."""

import json

import pytest

from devctl.check.stacks.python_dead_code import AllowlistItem
from devctl.check.stacks.typescript_suppressions import KNIP_ALLOWLIST_KEYS, knip_allowlist


@pytest.mark.parametrize("key", KNIP_ALLOWLIST_KEYS)
def test_each_allowlist_key_names_its_rule(key: str) -> None:
    value = '{"src/x.ts": ["exports"]}' if key == "ignoreIssues" else '["src/x.ts"]'
    text = '{\n"' + key + '":\n' + value + "\n}"
    assert knip_allowlist(text, "knip.jsonc") == ([AllowlistItem(3, f"knip.{key}:src/x.ts")], [])


def test_two_items_on_one_line_fail() -> None:
    items, errors = knip_allowlist('{"ignore": ["a", "a"]}', "frontend/knip.jsonc")
    assert items == [AllowlistItem(1, "knip.ignore:a")] * 2
    assert errors == [
        "frontend/knip.jsonc:1: knip.ignore holds 2 items on one line; "
        "write each alone on its own line, with its own marker"
    ]


def test_nested_allowlist_fails() -> None:
    assert knip_allowlist('{"workspaces":{"pkg":{"ignore":["x"]}}}', "knip.jsonc") == (
        [],
        [
            "knip.jsonc: workspaces.pkg.ignore sets an allowlist below the top level; "
            "devctl reads knip's allowlists only at the top level of knip.jsonc"
        ],
    )


def test_comments_escapes_and_scope_settings() -> None:
    text = """{ // "ignore": ["fake"]
      "ignoreDependencies": [
        "@types/node", /* ] "fake" */
        "a\\u002fb",
      ],
      "entry": ["x"], "project": ["y"], "ignoreWorkspaces": ["z"]
    }"""
    assert knip_allowlist(text, "knip.jsonc") == (
        [
            AllowlistItem(3, "knip.ignoreDependencies:@types/node"),
            AllowlistItem(4, "knip.ignoreDependencies:a/b"),
        ],
        [],
    )


def test_invalid_jsonc_rejects() -> None:
    with pytest.raises(json.JSONDecodeError):
        knip_allowlist('{"ignore": [,]}', "knip.jsonc")


def test_non_allowlist_scalars_do_not_hide_later_items() -> None:
    text = '{"a": false, "b": 1.5e-3, "c": null, "d": "text", "ignore": ["real"]}'
    assert knip_allowlist(text, "knip.jsonc") == ([AllowlistItem(1, "knip.ignore:real")], [])


def test_repeated_items_are_located_as_a_multiset() -> None:
    text = '{"ignore": [\n"a",\n"a",\n"b"\n]}'
    assert knip_allowlist(text, "knip.jsonc") == (
        [
            AllowlistItem(2, "knip.ignore:a"),
            AllowlistItem(3, "knip.ignore:a"),
            AllowlistItem(4, "knip.ignore:b"),
        ],
        [],
    )
