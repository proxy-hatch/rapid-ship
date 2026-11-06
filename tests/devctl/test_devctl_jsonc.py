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


@pytest.mark.parametrize("text", ['{"a": }', '{"a": 1 /* unfinished', '{"a": 1 2}'])
def test_invalid_jsonc_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError, match="Expecting"):
        loads(text)
