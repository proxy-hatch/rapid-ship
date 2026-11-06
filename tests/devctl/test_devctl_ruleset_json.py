"""Offline: rs-setup's ruleset.json against doctor's ruleset rules and a ruleset that GitHub
returned, and the commands rs-setup states."""

import json
from pathlib import Path

import pytest

from devctl.doctor_rules import ruleset_problems

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "rapid_ship/templates/common/.agents/skills/rs-setup"


@pytest.mark.parametrize("every_pr", [True, False])
@pytest.mark.parametrize("agent_identity", [True, False])
def test_rs_setups_ruleset_passes_doctor_in_every_mode(
    every_pr: bool, agent_identity: bool
) -> None:
    ruleset = json.loads((SKILL / "ruleset.json").read_text())
    assert (
        ruleset_problems([ruleset], "main", every_pr=every_pr, agent_identity=agent_identity) == []
    )


def test_the_ruleset_is_the_body_github_accepted() -> None:
    fixture = json.loads((ROOT / "tests/devctl/fixtures/github/ruleset.json").read_text())
    for key in ("id", "source", "source_type"):
        del fixture[key]
    parameters = next(
        rule["parameters"] for rule in fixture["rules"] if rule["type"] == "pull_request"
    )
    del parameters["require_extra_approval_for_unattributed_changes"]
    del parameters["required_reviewers"]
    assert json.loads((SKILL / "ruleset.json").read_text()) == fixture


def test_rs_setup_applies_the_settings_doctor_checks() -> None:
    text = (SKILL / "SKILL.md").read_text()
    for value in (
        "--input .agents/skills/rs-setup/ruleset.json",
        "-F delete_branch_on_merge=true",
        "-f approval_policy=all_external_contributors",
    ):
        assert value in text


def test_rs_setup_states_each_guard() -> None:
    text = "\n".join(path.read_text() for path in SKILL.rglob("*.md"))
    for value in (
        "rulesets?targets=branch",
        "--method PUT repos/<owner>/<name>/rulesets/<id>",
        "git check-ignore -q .claude/settings.local.json",
        "git rev-parse --git-path info/exclude",
        "gh auth status",
        'exclude = ["tools/devctl"]',
        ".agents/hooks.json",
        ".codex/hooks.json",
        "/hooks",
        "sandbox_mode",
        "./devctl as",
        "new sandbox Session",
        "github.com",
        "api.github.com",
        "codeload.github.com",
        "objects.githubusercontent.com",
        "pypi.org",
        "files.pythonhosted.org",
        "~/.cache/uv",
        "~/.local/share/uv/tools",
    ):
        assert value in text


def test_known_failures_quote_what_the_kit_prints() -> None:
    import inspect

    from devctl import merge_guard
    from devctl.hook import G7, G8

    text = (SKILL / "references/known-failures.md").read_text()
    source = inspect.getsource(merge_guard)
    assert G7 in text
    assert G8.partition("{arguments}")[0] in text
    for fragment in (
        "merge denied: in Walk the owner merges every pull request; ask the owner to merge PR #",
        ", so the owner merges it",
    ):
        assert fragment in source
        assert fragment in text
