"""Offline: metrics.toml in temporary directories."""

from pathlib import Path

import pytest

from devctl.metrics.settings import (
    BASIC_METRICS,
    DeploymentsSource,
    IssuesSource,
    MetricsSettingsError,
    SettingsMetric,
    gate_note,
    load_metrics,
)
from rapid_ship.kit.templates import render_files

VARIABLES = {
    "project_name": "demo-app",
    "package": "demo_app",
    "owner": "octo",
    "repository": "octo/demo-app",
}


def test_the_seed_loads_with_the_defaults(tmp_path: Path) -> None:
    templates = {t.path: t for t in render_files("python", VARIABLES, ())}
    metrics_template = templates[".rapid-ship/metrics.toml"]
    assert metrics_template.content is not None
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(metrics_template.content)

    settings = load_metrics(tmp_path)

    assert settings.window == 30
    assert settings.thresholds == {
        "revisions": 1.0,
        "reverts": 1,
        "red_merges": 1,
        "closed_unmerged": 3,
    }
    assert settings.metrics == ()


def test_every_problem_is_listed(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 0\n"
        'mode = "walk"\n'
        "[thresholds]\n"
        "alarm = 0\n"
        "reverts = -1\n\n"
        "[[metric]]\n"
        'id = "Bad-ID"\n'
        'title = "Bad"\n'
        'source = "pagerduty"\n'
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    expected = (
        "metrics.toml: window = 0: use an integer of at least 1",
        "metrics.toml: unknown key 'mode'; it accepts window, thresholds, metric",
        (
            "metrics.toml [thresholds] alarm = 0: alarm names no metric; "
            "use one of revisions, reverts, red_merges, closed_unmerged, corrections"
        ),
        "metrics.toml [thresholds] reverts = -1: use a number of at least 0",
        (
            'metrics.toml [[metric]] #1: id = "Bad-ID": '
            "use lowercase letters, digits and _, starting with a letter"
        ),
        'metrics.toml [[metric]] #1: source = "pagerduty": use "issues" or "deployments"',
    )
    assert exc_info.value.problems == expected
    assert str(exc_info.value) == "\n".join(expected)


def test_window_has_no_upper_limit(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("window = 100000\n")

    settings = load_metrics(tmp_path)

    assert settings.window == 100000


def test_a_threshold_names_a_basic_settings_or_code_metric(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n"
        "[thresholds]\n"
        "alarms = 0\n"
        "probe_failures = 0\n\n"
        "[[metric]]\n"
        'id = "alarms"\n'
        'title = "Alarms"\n'
        'source = "issues"\n'
        'label = "alarm"\n'
    )

    settings = load_metrics(tmp_path, code_metric_ids={"probe_failures"})

    assert settings.thresholds["alarms"] == 0
    assert settings.thresholds["probe_failures"] == 0
    assert len(settings.metrics) == 1
    assert settings.metrics[0] == SettingsMetric("alarms", "Alarms", IssuesSource("alarm"))


@pytest.mark.parametrize(
    ("toml_content", "expected_problem"),
    [
        (
            'window = 30\n[[metric]]\nid = "m"\ntitle = "T"\nsource = "issues"\n',
            "metrics.toml [[metric]] #1: label: required",
        ),
        (
            'window = 30\n[[metric]]\nid = "m"\ntitle = "T"\nsource = "deployments"\n',
            "metrics.toml [[metric]] #1: environment: required",
        ),
        (
            'window = 30\n[[metric]]\nid = "m"\ntitle = "T"\n'
            'source = "deployments"\nenvironment = "prod"\ncount = "both"\n',
            'metrics.toml [[metric]] #1: count = "both": use "rollbacks" or "failures"',
        ),
        (
            'window = 30\n[[metric]]\nid = "m"\ntitle = "T"\n'
            'source = "deployments"\nenvironment = "prod"\nlabel = "alarm"\n',
            'metrics.toml [[metric]] #1: label is not read by source "deployments"; '
            "it reads environment and count",
        ),
        (
            'window = 30\n[[metric]]\nid = "m"\ntitle = ""\nsource = "issues"\nlabel = "alarm"\n',
            'metrics.toml [[metric]] #1: title = "": use a non-empty string',
        ),
    ],
)
def test_each_source_needs_its_fields_and_reads_no_other(
    tmp_path: Path, toml_content: str, expected_problem: str
) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(toml_content)

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    assert expected_problem in exc_info.value.problems


def test_ids_are_new_and_well_formed(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n"
        "[thresholds]\n"
        "alarm = 0\n\n"
        "[[metric]]\n"
        'id = "valid_setting"\n'
        'title = "Valid"\n'
        'source = "issues"\n'
        'label = "valid"\n\n'
        "[[metric]]\n"
        'id = "valid_setting"\n'
        'title = "Repeated"\n'
        'source = "issues"\n'
        'label = "valid"\n\n'
        "[[metric]]\n"
        'id = "reverts"\n'
        'title = "Reverts"\n'
        'source = "issues"\n'
        'label = "reverts"\n\n'
        "[[metric]]\n"
        'id = "9x"\n'
        'title = "Nine"\n'
        'source = "issues"\n'
        'label = "nine"\n\n'
        "[[metric]]\n"
        'id = "collides"\n'
        'title = "Collides"\n'
        'source = "issues"\n'
        'label = "collides"\n'
    )

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path, code_metric_ids={"collides", "probe_metric"})

    expected_known = f"use one of {', '.join(BASIC_METRICS)}, valid_setting, collides, probe_metric"
    assert (
        f"metrics.toml [thresholds] alarm = 0: alarm names no metric; {expected_known}"
        in exc_info.value.problems
    )

    assert (
        'metrics.toml [[metric]] #2: id = "valid_setting": '
        "another metric already defines valid_setting; choose another id" in exc_info.value.problems
    )
    assert (
        'metrics.toml [[metric]] #3: id = "reverts": reverts is a basic metric; choose another id'
        in exc_info.value.problems
    )
    assert (
        'metrics.toml [[metric]] #4: id = "9x": '
        "use lowercase letters, digits and _, starting with a letter" in exc_info.value.problems
    )
    assert (
        'metrics.toml [[metric]] #5: id = "collides": '
        "devctl_project.metrics() already defines collides; choose another id"
        in exc_info.value.problems
    )


def test_count_defaults_to_rollbacks(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "window = 30\n"
        "[[metric]]\n"
        'id = "rollbacks"\n'
        'title = "Deploy rollbacks"\n'
        'source = "deployments"\n'
        'environment = "production"\n'
    )

    settings = load_metrics(tmp_path)

    assert len(settings.metrics) == 1
    assert settings.metrics[0].source == DeploymentsSource(
        environment="production", count="rollbacks"
    )


def test_a_boolean_is_not_a_number(tmp_path: Path) -> None:
    target = tmp_path / ".rapid-ship/metrics.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("window = true\n[thresholds]\nreverts = true\n")

    with pytest.raises(MetricsSettingsError) as exc_info:
        load_metrics(tmp_path)

    assert exc_info.value.problems == (
        "metrics.toml: window = True: use an integer of at least 1",
        "metrics.toml [thresholds] reverts = True: use a number of at least 0",
    )


def test_a_missing_file_names_the_fix(tmp_path: Path) -> None:
    expected = (
        r"\.rapid-ship/metrics\.toml: missing; "
        r"run rapid-ship sync to add it with the defaults"
    )
    with pytest.raises(MetricsSettingsError, match=expected):
        load_metrics(tmp_path)


def test_the_gate_note_appears_only_while_gate_toml_exists(tmp_path: Path) -> None:
    gate = tmp_path / ".rapid-ship/gate.toml"
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text('mode = "walk"\n')

    expected = (
        ".rapid-ship/gate.toml: devctl no longer reads it; delete it, "
        "and carry any threshold worth keeping into .rapid-ship/metrics.toml"
    )
    assert gate_note(tmp_path) == expected

    gate.unlink()
    assert gate_note(tmp_path) is None
