import pytest

from {{package}}.errors import UsageError
from {{package}}.settings import load_settings


def test_an_error_keeps_its_cause_and_names_the_next_step() -> None:
    with pytest.raises(UsageError) as caught:
        load_settings({"WORKERS": "four"})

    assert str(caught.value) == "WORKERS is four; set it to a whole number from 1 to 32"
    assert isinstance(caught.value.__cause__, ValueError)
    assert "invalid literal for int()" in str(caught.value.__cause__)
