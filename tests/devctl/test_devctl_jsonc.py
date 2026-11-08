"""Offline: the JSONC reader."""

import pytest

from devctl.jsonc import loads


def test_jsonc_reads_comments_and_trailing_commas() -> None:
    assert loads('{\n // c\n "a": [1, 2,], /* b */ "s": "// kept",\n}') == {
        "a": [1, 2],
        "s": "// kept",
    }
    assert loads(r'{"s": "escaped \\\" // /* ,]", "x": [1, /*c*/ ],}') == {
        "s": 'escaped \\" // /* ,]',
        "x": [1],
    }


@pytest.mark.parametrize(
    "text",
    [
        '{"a": }',
        '{"a": 1 /* unfinished',
        '{"a": 1 2}',
        "[,]",
        "{,}",
        "[/* before */ , /* after */]",
        "{// before\n, // after\n}",
        '{"a": [,]}',
        "[{,}]",
        "[1,,]",
        "[1, /* gap */ ,]",
        '{"a":,}',
        '{"a": 1,,}',
    ],
)
def test_invalid_jsonc_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError, match=r".+"):
        loads(text)


@pytest.mark.parametrize(
    "text",
    [
        '[{}, [], "[,]", "{,}", true, null, -1.2e3,]',
        '[{}, [], "[,]", "{,}", true, null, -1.2e3, /* end */]',
        '[{}, [], "[,]", "{,}", true, null, -1.2e3, // end\n]',
    ],
)
def test_trailing_commas_preserve_values_and_empty_containers(text: str) -> None:
    assert loads(text) == [{}, [], "[,]", "{,}", True, None, -1200.0]
