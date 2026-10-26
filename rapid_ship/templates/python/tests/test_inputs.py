"""mypy checks this file, so the assert_type call below holds parse_level to returning a
Level, not a str (docs/patterns/python-input-validation.md).
"""

from typing import assert_type

import pytest

from {{package}}.errors import UsageError
from {{package}}.inputs import Level, parse_level


def test_a_known_value_becomes_a_level() -> None:
    level = assert_type(parse_level("info"), Level)

    assert level == "info"


def test_an_unknown_value_is_rejected() -> None:
    with pytest.raises(UsageError, match="use one of debug, info, warning, error"):
        parse_level("verbose")
