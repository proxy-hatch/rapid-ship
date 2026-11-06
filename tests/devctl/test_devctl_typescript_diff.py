"""Offline: pure Vitest identities and tautologies; no live diff integration."""

import pytest

from devctl.check.stacks import vitest


def test_identities_are_title_chains() -> None:
    source = """describe("a", () => { it("b", () => { const r = /\\)/; const s = "describe("; });
    describe('c', () => { test(`d`, () => {}) }) }); test("e", () => {})"""
    assert vitest.test_identities(source) == (["a > b", "a > c > d", "e"], [])


def test_dynamic_and_each_titles_are_unchecked() -> None:
    source = """test(name, () => {});
    test(`x ${y}`, () => {});
    test.each(rows)("x %s", () => {});
    describe(name, () => { it("child", () => {}) });
    suite.each(rows)("s", () => { test("nested", () => {}) });"""
    assert vitest.test_identities(source) == ([], [1, 2, 3, 4, 5])


@pytest.mark.parametrize(
    "jsx",
    [
        "<p>Don't</p>",
        """<><div title='test("fake", () => {})'><p>Don't</p>
    test("fake", () => {}) expect(true).toBeTruthy()</div><X title="don't" /></>""",
        """<X value={"}"} other={/}/}><span>Don't</span>{expect(true).toBeTruthy()}</X>""",
    ],
)
def test_jsx_preserves_real_calls(jsx: str) -> None:
    source = (
        f'describe("d", () => {{ test("a", () => {{ render({jsx}); }}); }}); '
        'test("e", () => { render(<p>Don\'t</p>); });'
    )
    assert vitest.test_identities(source) == (["d > a", "e"], [])
    assert len(vitest.tautologies(source)) == (1 if "{expect" in jsx else 0)


def test_comparison_and_generics_remain_javascript() -> None:
    source = 'const x = a < b; f<T>(x); const fn = <T,>(x: T) => x; test("real", () => {});'
    assert vitest.test_identities(source) == (["real"], [])


def test_strings_comments_regex_and_templates_are_opaque() -> None:
    source = """// test("fake", () => {})
    const s = 'expect(true).toBeTruthy()';
    const t = `test("fake", () => {}) ${"}"}`;
    const r = /test("fake")/;
    test("real", () => {});"""
    assert vitest.test_identities(source) == (["real"], [])
    assert vitest.tautologies(source) == []


def test_escaped_and_continued_strings_preserve_boundaries() -> None:
    source = "test('it\\'s', () => {}); const x = 'a\\\nb'; test(\"next\", () => {});"
    assert vitest.test_identities(source) == (["it's", "next"], [])


@pytest.mark.parametrize(
    "source", ["const s = 'bad\ntest('x', () => {});", "test('x', () => {", "/* unclosed"]
)
def test_malformed_source_rejects(source: str) -> None:
    with pytest.raises(ValueError, match=r"unterminated|unclosed|unbalanced"):
        vitest.test_identities(source)


def test_tautologies_and_genuine_assertions() -> None:
    source = """expect( x . y ).toBe(x.y); expect(true).toBeTruthy();
    expect(f(a)).toStrictEqual(f(a)); expect(a).toEqual(b); expect(false).toBeTruthy();"""
    assert vitest.tautologies(source) == [
        (1, "expect( x . y ).toBe(x.y)"),
        (1, "expect(true).toBeTruthy()"),
        (2, "expect(f(a)).toStrictEqual(f(a))"),
    ]


@pytest.mark.parametrize(
    ("path", "expected"),
    [("a.test.tsx", True), ("a.spec.mjs", True), ("test.ts", False), ("a.test.ts.bak", False)],
)
def test_test_file_paths(path: str, expected: bool) -> None:
    assert vitest.is_test_file(path) is expected


def test_generic_arrow_before_jsx_is_not_an_element() -> None:
    source = 'const f = <T>(x: T) => x; const el = <X />; test("real", () => {});'
    assert vitest.test_identities(source) == (["real"], [])


def test_jsx_expressions_start_with_javascript_boundaries() -> None:
    source = "const el = <X a={'value'} b={/}/} c={expect(true).toBeTruthy()} />;"
    assert vitest.tautologies(source) == [(1, "expect(true).toBeTruthy()")]


@pytest.mark.parametrize(
    "prefix", ["(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "return", ""]
)
def test_regex_start_contexts(prefix: str) -> None:
    from devctl.check.stacks.vitest_tokens import Lexer

    lexer = Lexer(prefix + '/test("fake")/; test("real", () => {});')
    lexer.javascript()
    assert sum(item.kind == "regex" for item in lexer.tokens) == 1


@pytest.mark.parametrize("expression", ["a < b", "/</.test(value)"])
def test_self_closing_jsx_attribute_expressions_preserve_both_readers(expression: str) -> None:
    source = (
        f"const el = <X value={{{expression}}} />; "
        'describe("outer", () => { test("real", () => { expect(true).toBeTruthy(); }); });'
    )
    assert vitest.test_identities(source) == (["outer > real"], [])
    assert vitest.tautologies(source) == [(1, "expect(true).toBeTruthy()")]


@pytest.mark.parametrize("callee", ["test", "it.concurrent", "describe", "suite"])
def test_tagged_each_calls_are_unchecked_and_later_chains_survive(callee: str) -> None:
    source = (
        f'{callee}.each`a | b\n1 | 2`("case", () => {{ test("child", () => {{}}); }});\n'
        'describe("later", () => { test("real", () => {}); });'
    )
    expected_lines = [1]
    expected_names = ["later > real"]
    if callee not in {"describe", "suite"}:
        expected_names.insert(0, "child")
    else:
        expected_lines = [2]
    assert vitest.test_identities(source) == (expected_names, expected_lines)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_line_continuations_preserve_titles_and_later_assertions(newline: str) -> None:
    source = (
        "const s = 'a\\"
        + newline
        + "b'; test('re\\"
        + newline
        + "al', () => { expect(true).toBeTruthy(); });"
    )
    assert vitest.test_identities(source) == (["real"], [])
    assert vitest.tautologies(source) == [(3, "expect(true).toBeTruthy()")]


@pytest.mark.parametrize("ending", ["\\", "\\\n", "\\\r\n", "\r\n", "\n"])
def test_unterminated_strings_still_reject(ending: str) -> None:
    with pytest.raises(ValueError, match="unterminated string"):
        vitest.test_identities("const s = 'bad" + ending)


@pytest.mark.parametrize(
    "prefix",
    [
        'const f = <T>(x: T) => x; const text = "</T>";',
        'const f = <T /* type */>(x: T) /* body */ => x; const text = "</T>";',
        'const f = <T extends Item>(x: T) => x; const text = "</T>";',
    ],
)
def test_generic_arrow_ignores_later_closing_tag_literals(prefix: str) -> None:
    source = prefix + ' test("real", () => {}); expect(true).toBeTruthy();'
    assert vitest.test_identities(source) == (["real"], [])
    assert vitest.tautologies(source) == [(1, "expect(true).toBeTruthy()")]


@pytest.mark.parametrize(
    "prefix",
    [
        "const el = <T>(text){expect(x).toBe(x)}</T>;",
        "const el = <T>(Don't){expect(x).toBe(x)}</T>;",
        'const el = <T title="</T>">test("fake", () => {})</T>;',
        'const text = "<T>(x: T) => x; </T>"; const value = a < b;',
        'f<T>(x); const text = "</T>";',
    ],
)
def test_generic_and_jsx_controls_preserve_opaque_text(prefix: str) -> None:
    source = prefix + ' test("real", () => {});'
    assert vitest.test_identities(source) == (["real"], [])
    assert vitest.tautologies(source) == ([(1, "expect(x).toBe(x)")] if "{expect" in prefix else [])


@pytest.mark.parametrize(
    "chain",
    [
        "skipIf(ci)",
        "runIf(ci)",
        "concurrent.skipIf(ci)",
        "skipIf(ci).runIf(other).concurrent",
        "runIf(check(a, b)).sequential.skipIf(ci)",
    ],
)
def test_conditional_configuration_preserves_titles_and_suite_scopes(chain: str) -> None:
    source = (
        f'describe.{chain}("outer", () => {{\n'
        f'  suite.{chain}("inner", () => {{\n'
        f'    test.{chain}("real", () => {{}});\n'
        "  });\n"
        '  it("sibling", () => {});\n'
        "});\n"
        f'test.{chain}("standalone", () => {{}});\n'
        'describe("later", () => { test("ordinary", () => {}); });'
    )
    assert vitest.test_identities(source) == (
        ["outer > inner > real", "outer > sibling", "standalone", "later > ordinary"],
        [],
    )


@pytest.mark.parametrize(
    "chain", ["skipIf(ci).each(rows)", "each(rows).runIf(ci)", "runIf(ci).each`a | b`"]
)
def test_conditional_each_and_dynamic_titles_stay_unchecked(chain: str) -> None:
    source = (
        f'describe.{chain}("outer", () => {{\n'
        '  test("real", () => {});\n'
        "});\n"
        f'test.{chain}("case", () => {{}});\n'
        "test.runIf(ci)(name, () => {});\n"
        'describe.skipIf(ci)(name, () => { test("child", () => {}); });\n'
        'test("later", () => {});'
    )
    assert vitest.test_identities(source) == (["later"], [2, 4, 5, 6])


def test_generic_closing_tag_string_preserves_tautology_reader() -> None:
    source = 'const f = <T>(x: T) => x; const text = "</T>"; test("real", () => {});'
    assert vitest.tautologies(source) == []
