"""Offline: TypeScript suppression forms read from lines of text."""

import pytest

from devctl.check.stacks.typescript_suppressions import SCRIPT_EXTENSIONS, line_rules


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "// eslint-disable-next-line no-console, complexity -- reason",
            ["eslint:complexity,no-console"],
        ),
        ("{/* eslint-disable-next-line */}", ["eslint"]),
        ('/* eslint no-console: "off" */', ["eslint:no-console"]),
        (
            '/* eslint complexity: ["error", 50], no-console: "off" */',
            ["eslint:complexity,no-console"],
        ),
        ("// @ts-expect-error", ["ts-expect-error"]),
        ("/* prettier-ignore */", ["prettier-ignore"]),
        ("/* v8 ignore start */", ["no-cover"]),
        ("/* v8 ignore stop */", []),
        ("/* c8 ignore next */", ["no-cover"]),
        ("/* istanbul ignore if */", ["no-cover"]),
        ("test.concurrent.skip(", ["skip"]),
        ("it.skipIf(ci)(", ["skipIf"]),
        ("describe.runIf(x)(", ["runIf"]),
        ("suite.todo(", ["todo"]),
        ("bench.fails(", ["fails"]),
        ('test("x", { skip: true }, () => {})', ["skip"]),
        ('describe("x", { todo: true }, () => {})', ["todo"]),
        ('test("x", { fails: condition }, () => {})', ["fails"]),
        ('test("x", { skip: false }, () => {})', []),
        ("/** @public */", ["knip:@public"]),
        (" * @beta rs-exception: EX-1", ["knip:@beta"]),
        ("/* eslint-enable */", []),
        ("/* eslint-env node */", []),
        ("test.only(", []),
        ("// @ts-ignore", []),
        ("const skip = true;", []),
    ],
)
def test_each_form_names_its_rule(line: str, expected: list[str]) -> None:
    assert line_rules("src/a.ts", line) == expected


@pytest.mark.parametrize("extension", SCRIPT_EXTENSIONS)
def test_script_extensions(extension: str) -> None:
    assert line_rules(f"a{extension}", "// @ts-expect-error") == ["ts-expect-error"]


def test_other_files_only_have_prettier() -> None:
    assert line_rules("a.md", "@public @ts-expect-error prettier-ignore") == ["prettier-ignore"]


@pytest.mark.parametrize(
    "options",
    [
        '["error", {"paths": [], "patterns": []}]',
        '["error", {"paths": [{"name": "x", "message": "bad, fake: off"}], "patterns": []}]',
        '["error", "text, fake: off", "escaped \\"quote, phantom: off"]',
        "['error', {paths: [], patterns: ['x, fake: off']}]",
    ],
)
def test_inline_eslint_options_do_not_add_rule_names(options: str) -> None:
    source = f'/* eslint no-restricted-imports: {options}, no-console: "off" */'
    assert line_rules("a.ts", source) == ["eslint:no-console,no-restricted-imports"]
