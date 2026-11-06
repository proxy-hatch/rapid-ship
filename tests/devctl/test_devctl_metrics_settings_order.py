"""Offline: diagnostic order across interleaved TOML tables."""

from pathlib import Path

import pytest

from devctl.metrics.settings import MetricsSettingsError, load_metrics


def test_interleaved_metric_and_threshold_tables_preserve_file_order(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n\n"
        "[[metric]]\n"
        'id = "first"\n'
        'title = "First"\n'
        'source = "pagerduty"\n\n'
        "[thresholds]\n"
        "reverts = -1\n\n"
        "[[metric]]\n"
        'id = "second"\n'
        'title = "Second"\n'
        'source = "pagerduty"\n'
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    expected = (
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
        "metrics.toml [thresholds] reverts = -1: use a number of at least 0",
        'metrics.toml [[metric]] #2: source = "pagerduty": use "issues" or "deployments"',
    )
    assert exc_info.value.problems == expected


def test_apparent_headers_in_comments_and_multiline_strings_are_ignored(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n"
        "# [thresholds]\n"
        "# [[metric]]\n\n"
        "[[metric]]\n"
        'id = "first"\n'
        'title = """\n'
        "[thresholds]\n"
        "reverts = 10\n"
        '"""\n'
        'source = "pagerduty"\n\n'
        "[thresholds]\n"
        "reverts = -1\n\n"
        "[[metric]]\n"
        'id = "second"\n'
        "title = '''\n"
        "[[metric]]\n"
        "id = 'sub'\n"
        "'''\n"
        'source = "pagerduty"\n'
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    expected = (
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
        "metrics.toml [thresholds] reverts = -1: use a number of at least 0",
        'metrics.toml [[metric]] #2: source = "pagerduty": use "issues" or "deployments"',
    )
    assert exc_info.value.problems == expected


def test_apparent_headers_in_multiline_inline_arrays_are_ignored(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n"
        "extra_list = [\n"
        "  [1, 2],\n"
        "  [3, 4]\n"
        "]\n\n"
        "[[metric]]\n"
        'id = "first"\n'
        'title = "First"\n'
        'source = "pagerduty"\n\n'
        "[thresholds]\n"
        "reverts = -1\n"
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    expected = (
        "metrics.toml: unknown key 'extra_list'; it accepts window, thresholds, metric",
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
        "metrics.toml [thresholds] reverts = -1: use a number of at least 0",
    )
    assert exc_info.value.problems == expected


def test_quoted_table_headers_and_whitespace(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n\n"
        '  [[ "metric" ]]  # first metric\n'
        'id = "first"\n'
        'title = "First"\n'
        'source = "pagerduty"\n\n'
        "  [ 'thresholds' ]  # thresholds section\n"
        "reverts = -1\n\n"
        '[["metric"]]\n'
        'id = "second"\n'
        'title = "Second"\n'
        'source = "pagerduty"\n'
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    expected = (
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
        "metrics.toml [thresholds] reverts = -1: use a number of at least 0",
        'metrics.toml [[metric]] #2: source = "pagerduty": use "issues" or "deployments"',
    )
    assert exc_info.value.problems == expected


def test_unknown_table_headers_interleaved(
    tmp_path: Path,
) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n\n"
        "[[metric]]\n"
        'id = "first"\n'
        'title = "First"\n'
        'source = "pagerduty"\n\n'
        "[unknown_table]\n"
        "foo = 1\n\n"
        "[[metric]]\n"
        'id = "second"\n'
        'title = "Second"\n'
        'source = "pagerduty"\n'
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    expected = (
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
        "metrics.toml: unknown key 'unknown_table'; it accepts window, thresholds, metric",
        'metrics.toml [[metric]] #2: source = "pagerduty": use "issues" or "deployments"',
    )
    assert exc_info.value.problems == expected
