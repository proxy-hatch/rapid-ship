"""load_settings reads, checks and types every setting."""

import pytest

from {{package}}.errors import UsageError
from {{package}}.settings import Settings, load_settings


def test_unset_values_take_their_defaults() -> None:
    assert load_settings({}) == Settings(log_level="info", workers=4)


@pytest.mark.parametrize("workers", ["1", "32"])
def test_values_inside_the_range_are_read(workers: str) -> None:
    settings = load_settings({"LOG_LEVEL": "debug", "WORKERS": workers})

    assert settings == Settings(log_level="debug", workers=int(workers))


@pytest.mark.parametrize("workers", ["0", "33"])
def test_an_out_of_range_value_is_rejected(workers: str) -> None:
    with pytest.raises(UsageError, match="set it to a whole number from 1 to 32"):
        load_settings({"WORKERS": workers})


def test_an_unknown_log_level_names_its_variable_and_keeps_the_cause() -> None:
    with pytest.raises(UsageError) as caught:
        load_settings({"LOG_LEVEL": "verbose"})

    assert str(caught.value).startswith("LOG_LEVEL is verbose; use one of debug, info")
    assert isinstance(caught.value.__cause__, UsageError)


def test_without_a_mapping_the_process_environment_is_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WORKERS", "8")
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    assert load_settings() == Settings(log_level="info", workers=8)
