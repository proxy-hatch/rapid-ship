"""Offline: what doctor passes each tool from the owner's environment. Each tool is a fake
executable on PATH (FakeHarness) that answers from its own environment; no real gh, gitleaks,
Harness or GitHub is run, and no Session starts."""

import json
import sys
from pathlib import Path

import pytest

from devctl.doctor import Item, OwnerReadError, gh_get, local_items
from github_fakes import FakeHarness, MakeContext

Answer = tuple[str, str, int]  # stdout, stderr, exit code
# Per tool: the item that reports its sign-in, and what the fake answers signed in and signed out.
SIGN_IN_ANSWERS: dict[str, tuple[str, Answer, Answer]] = {
    "gh": ("gh sign-in", ("", "", 0), ("", "You are not logged into any GitHub hosts.\n", 1)),
}
# One sign-in per tool, set together, to show that no tool receives another's.
OWNER_SIGN_INS = {
    "GH_TOKEN": "gh",
    "ANTHROPIC_API_KEY": "claude",
    "OPENAI_API_KEY": "codex",
    "GEMINI_API_KEY": "agy",
}
# devctl as's own variables, git tracing, and gh's other hosts: no doctor tool receives these.
NEVER_PASSED = (
    "RAPID_SHIP_GIT_TOKEN",
    "GIT_ASKPASS",
    "GIT_TRACE",
    "GH_HOST",
    "GH_ENTERPRISE_TOKEN",
)
NETWORK = {
    "HTTPS_PROXY": "http://proxy.invalid:3128",
    "NO_PROXY": "localhost",
    "SSL_CERT_FILE": "/etc/ssl/example.pem",
}


def install_signed_in_when(
    harness: FakeHarness, tool: str, variable: str, signed_in: Answer, signed_out: Answer
) -> None:
    """A tool that answers signed in only while variable is in its environment."""
    script = harness.directory / tool
    script.write_text(
        f"#!{sys.executable}\n"
        "import os, sys\n"
        f"out, err, code = {signed_in!r} if {variable!r} in os.environ else {signed_out!r}\n"
        "sys.stdout.write(out)\n"
        "sys.stderr.write(err)\n"
        "sys.exit(code)\n"
    )
    script.chmod(0o755)


def install_recorder(harness: FakeHarness, tool: str) -> Path:
    """A tool that writes its environment, as JSON, to the path returned, and exits 1."""
    record = harness.directory / f"{tool}.env.json"
    script = harness.directory / tool
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        f"with open({str(record)!r}, 'w') as f:\n"
        "    json.dump(dict(os.environ), f)\n"
        "sys.exit(1)\n"
    )
    script.chmod(0o755)
    return record


def by_name(items: list[Item]) -> dict[str, Item]:
    return {item.name: item for item in items}


@pytest.mark.parametrize(
    ("tool", "variable"),
    [
        ("gh", "GH_TOKEN"),
        ("gh", "GITHUB_TOKEN"),
        ("gh", "GH_CONFIG_DIR"),
    ],
)
def test_a_sign_in_held_only_in_the_environment_is_ok(
    ctx: MakeContext,
    fake_harness: FakeHarness,
    monkeypatch: pytest.MonkeyPatch,
    tool: str,
    variable: str,
) -> None:
    # Spec 1 section 6: any sign-in method is ok, including one that the owner's shell exports.
    name, signed_in, signed_out = SIGN_IN_ANSWERS[tool]
    install_signed_in_when(fake_harness, tool, variable, signed_in, signed_out)
    context = ctx()
    monkeypatch.delenv(variable, raising=False)
    assert by_name(local_items(context))[name].status == "missing"
    monkeypatch.setenv(variable, "example-value")
    assert by_name(local_items(context))[name].status == "ok"


def test_each_tool_gets_its_own_sign_in_and_the_network_settings_only(
    ctx: MakeContext, fake_harness: FakeHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    for variable in (*OWNER_SIGN_INS, *NEVER_PASSED):
        monkeypatch.setenv(variable, "0")  # "0" keeps the test's own git from tracing
    for variable, value in NETWORK.items():
        monkeypatch.setenv(variable, value)
    tools = ("gh", "gitleaks")
    records = {tool: install_recorder(fake_harness, tool) for tool in tools}
    local_items(ctx())
    for tool, record in records.items():
        seen = json.loads(record.read_text())
        own = {variable for variable, owner in OWNER_SIGN_INS.items() if owner == tool}
        assert set(OWNER_SIGN_INS) & seen.keys() == own, tool
        assert not set(NEVER_PASSED) & seen.keys(), tool
        assert {variable: seen.get(variable) for variable in NETWORK} == NETWORK, tool


def test_owner_reads_use_a_gh_sign_in_held_in_the_environment(
    fake_harness: FakeHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_signed_in_when(
        fake_harness,
        "gh",
        "GH_TOKEN",
        ('{"full_name": "o/r"}', "", 0),
        ('{"message": "Requires authentication"}', "gh: Requires authentication (HTTP 401)\n", 1),
    )
    monkeypatch.delenv("GH_TOKEN", raising=False)
    with pytest.raises(OwnerReadError) as refused:
        gh_get("repos/o/r")
    assert refused.value.status == 401
    monkeypatch.setenv("GH_TOKEN", "example-value")
    assert gh_get("repos/o/r") == {"full_name": "o/r"}
