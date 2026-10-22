"""Offline: doctor's Harness wiring item on written settings files."""

import json

import pytest

from devctl.doctor import Item, local_items
from devctl.doctor_wiring import wiring_problems
from github_fakes import MakeContext, RepoFiles
from rapid_ship.kit.templates import render_files

HOOK = {"type": "command", "command": '"$CLAUDE_PROJECT_DIR"/devctl hook claude pre-tool'}
ALL = "Bash|Edit|Write|MultiEdit|NotebookEdit|Monitor"
GAP = "no PreToolUse hook runs devctl hook claude pre-tool for "
EVERY_TOOL = "Bash, Edit, Write, MultiEdit, NotebookEdit, Monitor"
PRE_TOOL: list[object] = ["hook", "claude", "pre-tool"]
WIRING = ".claude/settings.json"


def wired(matcher: str | None = ALL, /, **fields: object) -> dict[str, object]:
    entry: dict[str, object] = {"hooks": [{**HOOK, **fields}]}
    if matcher is not None:
        entry["matcher"] = matcher
    return {"hooks": {"PreToolUse": [entry]}}


SEED = wired()


def args_form(command: str, args: list[object]) -> dict[str, object]:
    """A command hook that names its program in command and its words in args."""
    hook = {"type": "command", "command": command, "args": args}
    return {"hooks": {"PreToolUse": [{"hooks": [hook]}]}}


def rendered_seed() -> str:
    """The Kit's .claude/settings.json as init renders it."""
    variables = {"project_name": "demo", "package": "demo", "owner": "o", "repository": "o/r"}
    [template] = [t for t in render_files("agnostic", variables, ()) if t.path == WIRING]
    assert template.content is not None
    return template.content.decode()


def harness_wiring_item(ctx: MakeContext) -> Item:
    [item] = [i for i in local_items(ctx()) if i.name == "Harness wiring"]
    assert item.area == "guardrails"
    return item


@pytest.mark.parametrize(
    ("settings", "problems"),
    [
        (SEED, []),
        (wired("*"), []),
        (wired(None), []),
        (wired("Bash,Edit,Write,MultiEdit,NotebookEdit,Monitor"), []),
        (wired("Bash|Monitor|.*Edit|Write"), []),
        (wired("Bash"), [GAP + "Edit, Write, MultiEdit, NotebookEdit, Monitor"]),
        (wired("Bash,Edit"), [GAP + "Write, MultiEdit, NotebookEdit, Monitor"]),
        (wired("Edit"), [GAP + "Bash, Write, MultiEdit, NotebookEdit, Monitor"]),
        (wired("Bash|Edit|Write|NotebookEdit|Monitor"), [GAP + "MultiEdit"]),
        (wired("Bash|Edit|Write|MultiEdit|NotebookEdit"), [GAP + "Monitor"]),
        (wired(**{"async": True}), [GAP + EVERY_TOOL]),
        (wired(**{"if": "Bash(git *)"}), [GAP + EVERY_TOOL]),
        ({**SEED, "disableAllHooks": True}, ["disableAllHooks is true, so no hook runs"]),
        ({}, [GAP + EVERY_TOOL]),
    ],
)
def test_wiring_problems(settings: object, problems: list[str]) -> None:
    assert wiring_problems(settings) == problems


@pytest.mark.parametrize(
    ("settings", "problems"),
    [
        (wired(""), []),
        (wired("Bash, Edit, Write, MultiEdit, NotebookEdit, Monitor"), []),
        (wired(**{"async": False}), []),
        (wired(**{"asyncRewake": True}), [GAP + EVERY_TOOL]),  # runs in the background
        (wired(**{"asyncRewake": False}), []),
        (args_form("${CLAUDE_PROJECT_DIR}/devctl", PRE_TOOL), []),
        # Exec form starts command with no shell: quotes and a "$" outside ${...} stay literal.
        (args_form('"$CLAUDE_PROJECT_DIR"/devctl', PRE_TOOL), [GAP + EVERY_TOOL]),
        (args_form("'$CLAUDE_PROJECT_DIR/devctl'", PRE_TOOL), [GAP + EVERY_TOOL]),
        (args_form("$CLAUDE_PROJECT_DIR/devctl", PRE_TOOL), [GAP + EVERY_TOOL]),
        (args_form("${CLAUDE_PROJECT_DIR/devctl", PRE_TOOL), [GAP + EVERY_TOOL]),
        (args_form("devctl", ["hook", "claude", "'pre-tool'"]), [GAP + EVERY_TOOL]),
        (args_form("devctl", ["hook", "claude"]), [GAP + EVERY_TOOL]),
        (args_form("devctl", ["hook", "claude", 3]), [GAP + EVERY_TOOL]),
        (
            {
                "hooks": {
                    "PreToolUse": [
                        {"matcher": "Bash|Monitor", "hooks": [HOOK]},
                        {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "x"}]},
                        {"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": ["x", HOOK]},
                    ]
                }
            },
            [],
        ),
        (wired("Bash|("), [GAP + EVERY_TOOL]),  # not a valid regular expression: matches nothing
        (wired("bash|edit|write|multiedit|notebookedit|monitor"), [GAP + EVERY_TOOL]),
        (wired(**{"type": "http"}), [GAP + EVERY_TOOL]),
        (wired(**{"command": "devctl hook claude"}), [GAP + EVERY_TOOL]),
        ({**SEED, "disableAllHooks": False}, []),
        ({"disableAllHooks": True}, ["disableAllHooks is true, so no hook runs", GAP + EVERY_TOOL]),
        ({"hooks": {"PostToolUse": [{"matcher": ALL, "hooks": [HOOK]}]}}, [GAP + EVERY_TOOL]),
        ({"hooks": [{"PreToolUse": [{"matcher": ALL, "hooks": [HOOK]}]}]}, [GAP + EVERY_TOOL]),
        ({"hooks": {"PreToolUse": {"matcher": ALL, "hooks": [HOOK]}}}, [GAP + EVERY_TOOL]),
        ({"hooks": {"PreToolUse": [{"matcher": ALL, "hooks": HOOK}]}}, [GAP + EVERY_TOOL]),
        ({"hooks": {"PreToolUse": [{"matcher": 3, "hooks": [HOOK]}]}}, [GAP + EVERY_TOOL]),
        ([SEED], [GAP + EVERY_TOOL]),
        ("hooks", [GAP + EVERY_TOOL]),
    ],
)
def test_wiring_problems_in_other_shapes(settings: object, problems: list[str]) -> None:
    assert wiring_problems(settings) == problems


@pytest.mark.usefixtures("fake_run")
class TestItem:
    def test_the_rendered_seed_is_ok(self, ctx: MakeContext, repo_files: RepoFiles) -> None:
        assert json.loads(rendered_seed()) == SEED
        repo_files.write(WIRING, rendered_seed())
        item = harness_wiring_item(ctx)
        assert (item.status, item.detail) == (
            "ok",
            f".claude/settings.json runs devctl hook claude pre-tool for {EVERY_TOOL}",
        )

    def test_a_missing_file_is_missing(self, ctx: MakeContext) -> None:
        item = harness_wiring_item(ctx)
        assert (item.status, item.detail) == ("missing", ".claude/settings.json is not tracked")

    def test_a_file_that_git_does_not_track_does_not_count(
        self, ctx: MakeContext, repo_files: RepoFiles
    ) -> None:
        settings = repo_files.root / WIRING
        settings.parent.mkdir()
        settings.write_text(rendered_seed())
        item = harness_wiring_item(ctx)
        assert (item.status, item.detail) == ("missing", ".claude/settings.json is not tracked")

    @pytest.mark.parametrize("content", [b"{\n", b"", b'{"hooks": {}', b"\xff\xfe{}"])
    def test_a_file_that_is_not_json_is_missing(
        self, ctx: MakeContext, repo_files: RepoFiles, content: bytes
    ) -> None:
        repo_files.write(WIRING, "tracked")
        (repo_files.root / WIRING).write_bytes(content)
        item = harness_wiring_item(ctx)
        assert (item.status, item.detail) == ("missing", ".claude/settings.json is not valid JSON")

    def test_a_gap_names_the_file_and_the_tools(
        self, ctx: MakeContext, repo_files: RepoFiles
    ) -> None:
        repo_files.write(WIRING, json.dumps({**wired("Bash"), "disableAllHooks": True}))
        item = harness_wiring_item(ctx)
        assert (item.status, item.detail) == (
            "missing",
            ".claude/settings.json: disableAllHooks is true, so no hook runs; "
            f"{GAP}Edit, Write, MultiEdit, NotebookEdit, Monitor",
        )

    def test_a_tracked_file_that_cannot_be_read_is_unknown(
        self, ctx: MakeContext, repo_files: RepoFiles
    ) -> None:
        repo_files.write(WIRING, rendered_seed())
        (repo_files.root / WIRING).unlink()
        item = harness_wiring_item(ctx)
        assert (item.status, item.detail) == ("unknown", "cannot read .claude/settings.json")
