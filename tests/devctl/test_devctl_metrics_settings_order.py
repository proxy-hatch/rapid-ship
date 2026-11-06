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


@pytest.mark.parametrize(
    "body", ["[metric]", '["metric"]', "[metric.foo]", 'metric.id = "x"', 'metric = {id = "x"}']
)
def test_metric_table_shapes_are_rejected(tmp_path: Path, body: str) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir()
    target.write_text("window = 30\n" + body + "\n")
    with pytest.raises(MetricsSettingsError) as caught:
        load_metrics(tmp_path)
    assert caught.value.problems == ("metrics.toml: metric: expected a list of tables",)


@pytest.mark.parametrize("nested", ["metric.extra", "thresholds.extra"])
def test_nested_headers_keep_identity_and_validate_once(tmp_path: Path, nested: str) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir()
    first = '[[metric]]\nid="first"\ntitle="First"\nsource="pagerduty"\n'
    threshold = "[thresholds]\nreverts=-1\n"
    extra = f"[{nested}]\nx=0\n"
    target.write_text(
        "window=30\n"
        + first
        + (extra + threshold if nested.startswith("metric") else threshold + extra)
        + '[[metric]]\nid="second"\ntitle="Second"\nsource="pagerduty"\n'
    )
    source = ': source = "pagerduty": use "issues" or "deployments"'
    threshold_error = "metrics.toml [thresholds] reverts = -1: use a number of at least 0"
    extra_error = (
        "metrics.toml [[metric]] #1: unknown key 'extra'; "
        "it accepts id, title, source, label, environment, count"
        if nested.startswith("metric")
        else "metrics.toml [thresholds] extra = {'x': 0}: extra names no metric; "
        "use one of revisions, reverts, red_merges, closed_unmerged, corrections, first, second"
    )
    middle = (
        (extra_error, threshold_error)
        if nested.startswith("metric")
        else (threshold_error, extra_error)
    )
    with pytest.raises(MetricsSettingsError) as caught:
        load_metrics(tmp_path)
    assert caught.value.problems == (
        "metrics.toml [[metric]] #1" + source,
        *middle,
        "metrics.toml [[metric]] #2" + source,
    )


def test_read_failure_uses_settings_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir()
    target.touch()

    def denied(*args: object, **kwargs: object) -> str:
        raise PermissionError("test read denied")

    monkeypatch.setattr(Path, "read_text", denied)
    with pytest.raises(MetricsSettingsError) as caught:
        load_metrics(tmp_path)
    assert caught.value.problems == ("metrics.toml: test read denied",)
    assert isinstance(caught.value.__cause__, PermissionError)


@pytest.mark.parametrize(
    "opening", ["[thresholds]", '["thresholds"]', "thresholds.reverts = -1\n[thresholds.extra]"]
)
def test_later_nested_threshold_follows_intervening_metric(tmp_path: Path, opening: str) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir()
    # A dotted assignment establishes the value before the first nested header.
    start = opening + ("\nreverts=-1" if opening.startswith("[") else "")
    nested = "[thresholds.extra]" if opening.startswith("[") else "[thresholds.other]"
    key = "extra" if opening.startswith("[") else "other"
    target.write_text(
        "window=30\n"
        + start
        + '\n[[metric]]\nid="x"\ntitle="X"\nsource="pagerduty"\n'
        + nested
        + "\nx=0\n"
    )
    with pytest.raises(MetricsSettingsError) as caught:
        load_metrics(tmp_path)
    expected = ["metrics.toml [thresholds] reverts = -1: use a number of at least 0"]
    if not opening.startswith("["):
        expected.append(
            "metrics.toml [thresholds] extra = {}: extra names no metric; use one of "
            "revisions, reverts, red_merges, closed_unmerged, corrections, x"
        )
    expected.extend(
        (
            'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
            f"metrics.toml [thresholds] {key} = {{'x': 0}}: {key} names no metric; use one of "
            "revisions, reverts, red_merges, closed_unmerged, corrections, x",
        )
    )
    assert caught.value.problems == tuple(expected)


def test_inline_missing_fields_follow_present_diagnostics(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir()
    target.write_text('window=30\nmetric=[{source="pagerduty"}]\n')
    with pytest.raises(MetricsSettingsError) as caught:
        load_metrics(tmp_path)
    assert caught.value.problems == (
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
        "metrics.toml [[metric]] #1: id: required",
        "metrics.toml [[metric]] #1: title: required",
    )
