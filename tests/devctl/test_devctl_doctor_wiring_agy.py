"""Offline: agy wiring, real rules through a stand-in shim, and simulated process failures."""

from __future__ import annotations

import json
import shlex
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from devctl import process
from devctl.doctor_wiring import agy_wiring_item, agy_wiring_problems
from devctl.process import ProcessResult
from rapid_ship.kit.templates import load_manifest, render_files
from test_devctl_doctor_settings import SHIM

COMMAND = "./devctl hook agy pre-tool"
HANDLER = {"type": "command", "command": COMMAND, "timeout": 600}
ALL = "run_command|write_file|edit_file"
GAP = "no PreToolUse hook runs devctl hook agy pre-tool for "
EVERY_TOOL = "run_command, write_file, edit_file"
WIRING = ".agents/hooks.json"
DENY = json.dumps({"decision": "deny", "reason": "G2: a force push rewrites published history"})


def wired(matcher: object = ALL, /, **fields: object) -> dict[str, dict[str, object]]:
    """One named hook, devctl, whose one PreToolUse entry has the matcher and one handler."""
    entry: dict[str, object] = {"hooks": [{**HANDLER, **fields}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return {"devctl": {"PreToolUse": [entry]}}


def named(**hooks: Mapping[str, object]) -> dict[str, object]:
    """Named hooks, each with one PreToolUse entry made from its matcher and fields."""
    return {name: {"PreToolUse": [{"hooks": [HANDLER], **entry}]} for name, entry in hooks.items()}


SEED = wired()


def rendered_seed() -> str:
    """The Kit's .agents/hooks.json as init renders it."""
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    [template] = [t for t in render_files("agnostic", variables, ()) if t.path == WIRING]
    assert template.content is not None
    return template.content.decode()


@pytest.mark.parametrize(
    ("hooks", "problems"),
    [
        (SEED, []),
        (wired("*"), []),
        (wired(""), []),
        (wired("run_command|write_file|edit_file|read_file"), []),
        (wired("(run_command|write_file|edit_file)"), []),
        (wired("run_command|.*_file"), []),
        (wired(timeout=360), []),
        (wired("run_command"), [GAP + "write_file, edit_file"]),
        # A part of a name counts only if agy does not anchor the matcher, which is not documented.
        (wired("command|write_file|edit_file"), [GAP + "run_command"]),
        (wired(None), [GAP + EVERY_TOOL]),
        (wired(3), [GAP + EVERY_TOOL]),
        (wired("run_command|("), [GAP + EVERY_TOOL]),
        (named(a={"matcher": "run_command"}, b={"matcher": "write_file|edit_file"}), []),
    ],
)
def test_agy_wiring_problems_for_the_matcher(hooks: object, problems: list[str]) -> None:
    assert agy_wiring_problems(hooks) == problems


@pytest.mark.parametrize(
    ("hooks", "problems"),
    [
        ({"devctl": {"enabled": True, **SEED["devctl"]}}, []),
        ({"devctl": {"enabled": False, **SEED["devctl"]}}, [GAP + EVERY_TOOL]),
        ({"devctl": {"enabled": "false", **SEED["devctl"]}}, [GAP + EVERY_TOOL]),
        (
            {"off": {"enabled": False, **SEED["devctl"]}, **named(on={"matcher": "run_command"})},
            [GAP + "write_file, edit_file"],
        ),
        # agy waits 30 seconds for a hook without a timeout; the merge guard needs 360.
        (
            named(devctl={"matcher": ALL, "hooks": [{"type": "command", "command": COMMAND}]}),
            [GAP + EVERY_TOOL],
        ),
        (wired(timeout=359), [GAP + EVERY_TOOL]),
        (wired(timeout="600"), [GAP + EVERY_TOOL]),
        (wired(timeout=True), [GAP + EVERY_TOOL]),
        (wired(type="http"), [GAP + EVERY_TOOL]),
        (wired(command='"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool'), [GAP + EVERY_TOOL]),
        (wired(command="../devctl hook agy pre-tool"), []),
        (
            wired(command="$(git rev-parse --show-toplevel)/devctl hook agy pre-tool"),
            [GAP + EVERY_TOOL],
        ),
        (
            wired(command='"$(git rev-parse --show-toplevel; true)/devctl" hook agy pre-tool'),
            [GAP + EVERY_TOOL],
        ),
        (
            wired(command='"/x$(git rev-parse --show-toplevel)/devctl" hook agy pre-tool'),
            [GAP + EVERY_TOOL],
        ),
        (wired(command=f"{COMMAND}; true"), [GAP + EVERY_TOOL]),
        (wired(command=f"{COMMAND} --verbose"), [GAP + EVERY_TOOL]),
        ({}, [GAP + EVERY_TOOL]),
        ([SEED], [GAP + EVERY_TOOL]),
        ({"devctl": [SEED["devctl"]]}, [GAP + EVERY_TOOL]),
        ({"devctl": {"PostToolUse": [{"matcher": ALL, "hooks": [HANDLER]}]}}, [GAP + EVERY_TOOL]),
        ({"devctl": {"PreToolUse": {"matcher": ALL, "hooks": [HANDLER]}}}, [GAP + EVERY_TOOL]),
        ({"devctl": {"PreToolUse": [{"matcher": ALL, "hooks": HANDLER}]}}, [GAP + EVERY_TOOL]),
    ],
)
def test_agy_wiring_problems_for_the_handler(hooks: object, problems: list[str]) -> None:
    assert agy_wiring_problems(hooks) == problems


class Probe:
    """process.run_process for the agy item: every call is recorded and gets one answer."""

    def __init__(self, result: ProcessResult | OSError) -> None:
        self.result = result
        self.calls: list[tuple[list[str], Path, str | None]] = []

    def run_process(
        self,
        argv: Sequence[str],
        cwd: Path,
        timeout_seconds: float,
        env: Mapping[str, str] | None = None,
        input_text: str | None = None,
    ) -> ProcessResult:
        self.calls.append((list(argv), cwd, input_text))
        if isinstance(self.result, OSError):
            raise self.result
        return self.result


def answering(
    monkeypatch: pytest.MonkeyPatch, stdout: str = DENY + "\n", code: int = 0, **flags: bool
) -> Probe:
    probe = Probe(ProcessResult([], code, stdout, "", 0.1, **flags))
    monkeypatch.setattr(process, "run_process", probe.run_process)
    return probe


def item_for(root: Path, text: str | None = None, *, tracked: bool = True) -> tuple[str, str]:
    if text is not None:
        (root / ".agents").mkdir(exist_ok=True)
        (root / WIRING).write_text(text)
    item = agy_wiring_item(root, [WIRING] if tracked else [])
    assert (item.area, item.name) == ("guardrails", "agy wiring")
    return item.status, item.detail


def test_the_rendered_seed_is_ok_and_its_hook_answers_a_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = answering(monkeypatch)

    assert json.loads(rendered_seed()) == SEED
    assert item_for(tmp_path, rendered_seed()) == (
        "ok",
        f".agents/hooks.json runs devctl hook agy pre-tool for {EVERY_TOOL}, and it denied a probe "
        "git push --force in deterministic direct/shell checks from root and .agents/",
    )
    assert [(argv, cwd) for argv, cwd, _ in probe.calls] == [
        (argv, cwd)
        for cwd in (tmp_path, tmp_path / ".agents")
        for argv in (shlex.split(COMMAND), ["/bin/sh", "-c", COMMAND])
    ]
    assert len({event for _, _, event in probe.calls}) == 1
    event = probe.calls[0][2]
    assert event is not None
    assert json.loads(event) == {
        "toolCall": {"name": "run_command", "args": {"CommandLine": "git push --force"}},
        "workspacePaths": [str(tmp_path)],
    }


def test_a_file_that_git_does_not_track_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = answering(monkeypatch)

    assert item_for(tmp_path, json.dumps(SEED), tracked=False) == (
        "missing",
        ".agents/hooks.json is not tracked",
    )
    assert probe.calls == []


@pytest.mark.parametrize("content", ["{\n", "", '{"devctl": {}'])
def test_a_file_that_is_not_json_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str
) -> None:
    answering(monkeypatch)

    assert item_for(tmp_path, content) == ("missing", ".agents/hooks.json is not valid JSON")


def test_a_tracked_file_that_cannot_be_read_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    answering(monkeypatch)

    assert item_for(tmp_path) == ("unknown", "cannot read .agents/hooks.json")


def test_a_gap_names_the_file_and_the_tools_and_runs_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = answering(monkeypatch)

    assert item_for(tmp_path, json.dumps(wired("run_command"))) == (
        "missing",
        f".agents/hooks.json: {GAP}write_file, edit_file",
    )
    assert probe.calls == []


@pytest.mark.parametrize(
    ("stdout", "code", "flags", "expected"),
    [
        (
            "",
            127,
            {},
            (
                "missing",
                ".agents/hooks.json: its hook exited 127 on a probe event, so agy would block "
                "every call it is wired for",
            ),
        ),
        (
            '{"decision": "allow"}\n',
            0,
            {},
            (
                "missing",
                ".agents/hooks.json: its hook did not deny a probe git push --force with G2",
            ),
        ),
        (
            '{"decision": "deny", "reason": "devctl hook: internal error: x"}\n',
            0,
            {},
            (
                "missing",
                ".agents/hooks.json: its hook did not deny a probe git push --force with G2",
            ),
        ),
        (
            "not json\n",
            0,
            {},
            (
                "missing",
                ".agents/hooks.json: its hook did not deny a probe git push --force with G2",
            ),
        ),
        (
            "",
            0,
            {"timed_out": True},
            (
                "unknown",
                ".agents/hooks.json: its hook gave no answer to a probe event within 30 seconds",
            ),
        ),
    ],
    ids=["exit-127", "allow", "devctl-failure", "not-json", "timed-out"],
)
def test_a_hook_that_does_not_deny_the_probe_does_not_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    code: int,
    flags: dict[str, bool],
    expected: tuple[str, str],
) -> None:
    answering(monkeypatch, stdout, code, **flags)

    assert item_for(tmp_path, json.dumps(SEED)) == expected


def test_every_wired_command_must_answer_the_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gone = "./gone/devctl hook agy pre-tool"
    hooks = named(
        a={"matcher": "run_command"},
        b={"matcher": "write_file|edit_file", "hooks": [{**HANDLER, "command": gone}]},
    )
    answers = {COMMAND: (DENY + "\n", 0), gone: ("", 127)}
    commands: list[str] = []

    def run_process(argv: Sequence[str], *args: object, **kwargs: object) -> ProcessResult:
        command = argv[-1] if argv[0] == "/bin/sh" else shlex.join(argv)
        commands.append(command)
        return ProcessResult([], answers[command][1], answers[command][0], "", 0.1)

    monkeypatch.setattr(process, "run_process", run_process)

    assert item_for(tmp_path, json.dumps(hooks)) == (
        "missing",
        ".agents/hooks.json: its hook exited 127 on a probe event, so agy would block every call "
        "it is wired for",
    )
    assert commands == [COMMAND] * 4 + [gone]


def test_a_hook_that_cannot_start_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(process, "run_process", Probe(OSError("no /bin/sh")).run_process)

    assert item_for(tmp_path, json.dumps(SEED)) == (
        "unknown",
        "cannot run the hook of .agents/hooks.json",
    )


@pytest.mark.parametrize(
    "command",
    [
        '"$(git rev-parse --show-toplevel)/devctl" hook agy pre-tool',
        '"$ROOT/devctl" hook agy pre-tool',
        '"${ROOT}/devctl" hook agy pre-tool',
        "~/devctl hook agy pre-tool",
        "'~/devctl' hook agy pre-tool",
        "'$(touch never)/devctl' hook agy pre-tool",
        "`pwd`/devctl hook agy pre-tool",
        "./devctl hook agy pre-tool > never",
        "./devctl hook agy pre-tool && touch never",
        "./devctl hook agy pre-tool\n touch never",
        "./devctl\nhook agy pre-tool",
        "X=1 ./devctl hook agy pre-tool",
        "./devctl hook agy pre-tool # comment",
        "./devctl hook agy pre-tool\x00",
    ],
)
def test_shell_dependent_or_extra_commands_are_rejected_without_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    probe = answering(monkeypatch)

    assert item_for(tmp_path, json.dumps(wired(command=command)))[0] == "missing"
    assert probe.calls == []


@pytest.mark.parametrize(
    "command",
    [
        "./devctl hook agy pre-tool",
        "'/project with spaces/devctl' hook agy pre-tool",
        '"/project with spaces/devctl" hook agy pre-tool',
        "/project\\ with\\ spaces/devctl hook agy pre-tool",
    ],
)
def test_static_paths_and_quoting_are_valid(command: str) -> None:
    assert agy_wiring_problems(wired(command=command)) == []


def launch_project(tmp_path: Path) -> Path:
    """Offline: real rendered agy files and rules, with a stand-in for uv's canonical shim."""
    root = tmp_path / "project with spaces"
    root.mkdir()
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    executable = load_manifest().executable
    for template in render_files("agnostic", variables, ()):
        if template.path in (WIRING, ".agents/devctl", ".rapid-ship/project.toml"):
            assert template.content is not None
            target = root / template.path
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(template.content)
            target.chmod(0o755 if template.path in executable else 0o644)
    (root / "devctl").write_text(SHIM)
    (root / "devctl").chmod(0o755)
    assert process.run_process(["git", "init", "--quiet"], root, 10).returncode == 0
    return root


@pytest.mark.parametrize("directory", [".", ".agents"])
@pytest.mark.parametrize("shell", [False, True], ids=["direct", "shell"])
@pytest.mark.parametrize("command", ["git status", "git push --force"])
def test_rendered_launch_reaches_real_allow_and_g2_rules(
    tmp_path: Path, directory: str, shell: bool, command: str
) -> None:
    root = launch_project(tmp_path)
    seed = json.loads((root / WIRING).read_text())
    launcher = seed["devctl"]["PreToolUse"][0]["hooks"][0]["command"]
    argv = ["/bin/sh", "-c", launcher] if shell else shlex.split(launcher)
    event = {
        "toolCall": {"name": "run_command", "args": {"CommandLine": command}},
        "workspacePaths": [str(root)],
    }

    result = process.run_process(argv, root / directory, 10, input_text=json.dumps(event))

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    answer = json.loads(result.stdout)
    if command == "git status":
        assert answer == {"decision": "allow"}
    else:
        assert answer["decision"] == "deny"
        assert answer["reason"].startswith("G2: ")


@pytest.mark.parametrize("path", ["devctl", ".agents/devctl"])
@pytest.mark.parametrize("defect", ["missing", "not-executable", "bad-interpreter"])
def test_doctor_detects_an_unusable_launcher(tmp_path: Path, path: str, defect: str) -> None:
    root = launch_project(tmp_path)
    launcher = root / path
    if defect == "missing":
        launcher.unlink(missing_ok=True)
    elif defect == "not-executable":
        launcher.chmod(0o644)
    else:
        launcher.write_text("#!/no/such/interpreter\n")

    assert item_for(root)[0] == "missing"


def test_doctor_accepts_the_real_rendered_launch_contract(tmp_path: Path) -> None:
    root = launch_project(tmp_path)

    assert item_for(root)[0] == "ok"
