"""Offline: rs-setup's ruleset.json against doctor's ruleset rules and a ruleset that GitHub
returned, and the commands rs-setup states."""

import json
from pathlib import Path

import pytest

from devctl.doctor import devctl_exclusion_gaps
from devctl.doctor_rules import ruleset_problems

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "rapid_ship/templates/common/.agents/skills/rs-setup"
# uv prints backticks around `tool.uv.workspace`, so the code span needs double backticks.
UV_NESTED_WORKSPACE = (
    "``error: Nested workspaces are not supported, but workspace member has a "
    "`tool.uv.workspace` table: .../tools/devctl``"
)


def doctors_uv_message() -> str:
    # A members glob that covers tools/devctl and no exclude: the one gap doctor's uv row reports.
    workspace = {"tool": {"uv": {"workspace": {"members": ["tools/*"]}}}}
    (message,) = devctl_exclusion_gaps(workspace, python=False)
    return message


def guardrails_section() -> str:
    text = (SKILL / "SKILL.md").read_text()
    return text.split("## 5. Harness guardrails", 1)[1].split("## 6. Sandbox", 1)[0]


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


def test_known_failures_distinguishes_app_refusals() -> None:
    text = (SKILL / "references/known-failures.md").read_text()
    for condition in (
        "personal repository belongs to another account",
        "organisation admin",
        "recorded App has no key",
        "stored key cannot confirm",
        "App permissions differ",
        "no App is recorded for the role",
        "Keychain item already exists",
        "stdin is a terminal",
        "stdin holds no key",
        "stdin exceeds 64 KiB",
        "key is not an unencrypted RSA PEM private key",
        "GitHub refuses the token",
        "GitHub shows another App",
    ):
        assert condition in text


def test_known_failures_give_doctors_fix_for_uvs_nested_workspace_error() -> None:
    lines = (SKILL / "references/known-failures.md").read_text().splitlines()
    doctor_row = f"| `{doctors_uv_message()}` |"
    doctor = [line for line in lines if line.startswith(doctor_row)]
    uv = [line for line in lines if UV_NESTED_WORKSPACE in line]
    assert len(doctor) == len(uv) == 1
    assert uv[0].rpartition(" | ")[2] == doctor[0].rpartition(" | ")[2]


def test_known_failures_say_that_uvs_nested_workspace_error_blocks_each_check_step() -> None:
    lines = (SKILL / "references/known-failures.md").read_text().splitlines()
    (uv,) = [line for line in lines if UV_NESTED_WORKSPACE in line]
    assert uv.split(" | ")[1] == (
        "A members glob such as `tools/*` covers `tools/devctl`, which is its own uv workspace. "
        "Each `uv run --locked` check step exits 2, which devctl reports as blocked."
    )


def test_setup_conditions_future_stack_settings() -> None:
    text = (SKILL / "SKILL.md").read_text()
    assert "Read each `[[stack]]` table" in text
    assert "Until multi-stack support ships" not in text
    assert "Once TypeScript support ships, for TypeScript" not in text
    assert "Once TypeScript support ships, for each TypeScript knip" not in text
    assert "once TypeScript starter Patterns ship" in text
    assert "Offer `rs-contribute` once" in text
    assert "Until `rs-contribute` ships" not in text


def test_setup_states_that_the_kit_seeds_the_agy_wiring_and_its_trial_status() -> None:
    guardrails = guardrails_section()
    assert "merged and trialed" not in guardrails
    assert (
        "The Kit seeds the agy wiring in `.agents/hooks.json`, without G5; "
        "its live trial is incomplete."
    ) in guardrails
    assert "ACP" not in guardrails


def test_setup_states_that_the_kit_seeds_the_codex_wiring_and_that_it_is_untrialed() -> None:
    assert (
        "The Kit seeds the Codex wiring in `.codex/hooks.json`, without G5; "
        "that wiring has not been trialed."
    ) in guardrails_section()


def test_known_failures_list_the_codex_wiring_item_and_its_trust_row() -> None:
    lines = (SKILL / "references/known-failures.md").read_text().splitlines()
    wiring_row = "| `Claude Code wiring`, `agy wiring` or `Codex wiring` reports missing hooks |"
    wiring = [line for line in lines if line.startswith(wiring_row)]
    trust = [line for line in lines if line.startswith("| Codex skips the hook |")]
    assert len(wiring) == len(trust) == 1
    assert "the Codex wiring has not been trialed" in trust[0]
    assert trust[0].rpartition(" | ")[2] == (
        "Ask the owner to trust the project and review the hook in `/hooks`. |"
    )


def test_setup_does_not_call_the_codex_wiring_unavailable() -> None:
    for name in ("SKILL.md", "references/known-failures.md"):
        text = (SKILL / name).read_text()
        for stale in ("once available", "may not be available yet", "Codex wiring absent"):
            assert stale not in text


def test_sandbox_contract_requires_approved_access_and_evidence() -> None:
    text = (SKILL / "SKILL.md").read_text()
    sandbox = text.split("## 6. Sandbox", 1)[1].split("## 7. GitHub", 1)[0]
    for value in (
        "shell calls and their children",
        "file tools, MCP servers and hooks",
        "each domain, write path and command exclusion",
        "`uv cache dir`",
        "tools directory read-only",
        "full filesystem and network access",
        "stored credentials",
        "whole shell call",
        "`--body-file`",
        "`./devctl doctor --settings`",
        "`./devctl check`",
        "Harness version",
        "effective settings",
        "sandboxed or excluded",
        "`npm config get cache`",
        "restart",
    ):
        assert value in sandbox
    assert "`~/.local/share/uv/tools`;" not in sandbox
    failures = (SKILL / "references/known-failures.md").read_text()
    assert "Allow that directory" not in failures
    assert "repeat all three checks" not in failures


def test_setup_stages_written_files_before_each_check() -> None:
    text = (SKILL / "SKILL.md").read_text()
    checks = text.split("## 4. Checks", 1)[1].split("## 5. Harness", 1)[0]
    assert checks.index("Before each `./devctl check`") < checks.index("then `./devctl check`")
    assert "stage the files" in checks
    assert "`git add`" in checks
