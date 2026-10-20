"""Offline: how doctor --skills asks a Harness for its skills and reads the answer. Every output is
a simulated Harness result; no Harness runs."""

import json

import pytest

from devctl.harness import (
    PROBE_MODELS,
    SKILLS_PROMPT,
    HarnessName,
    SkillReport,
    error_line,
    parse_skills,
    skills_args,
)
from devctl.process import ProcessResult

HARNESSES: list[HarnessName] = ["claude", "codex", "agy"]


def result(
    stdout: str = "", stderr: str = "", code: int = 0, *, cut: str | None = None
) -> ProcessResult:
    """A finished Session's result, or one cut short: cut names the ProcessResult flag to set."""
    return ProcessResult(
        ["harness"],
        code,
        stdout,
        stderr,
        0.0,
        cut == "timed_out",
        cut == "stdout_truncated",
        cut == "stderr_truncated",
    )


def lines(*events: object) -> str:
    return "".join(f"{json.dumps(event)}\n" for event in events)


def init(skills: object) -> dict[str, object]:
    return {"type": "system", "subtype": "init", "skills": skills}


def done(text: object, *, is_error: bool = False) -> dict[str, object]:
    return {"type": "result", "subtype": "success", "is_error": is_error, "result": text}


def agent_message(text: str) -> dict[str, object]:
    return {"type": "item.completed", "item": {"id": "i", "type": "agent_message", "text": text}}


class TestSkillsArgs:
    def test_claude_prints_its_own_skill_list_in_the_init_event(self) -> None:
        assert skills_args("claude") == [
            "-p",
            SKILLS_PROMPT,
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            PROBE_MODELS["claude"],
        ]

    def test_codex_replies_in_a_read_only_ephemeral_session(self) -> None:
        assert skills_args("codex") == [
            "exec",
            "--json",
            "--model",
            PROBE_MODELS["codex"],
            "-c",
            'model_reasoning_effort="low"',
            "--sandbox",
            "read-only",
            "--ephemeral",
            SKILLS_PROMPT,
        ]

    def test_agy_asks_for_its_skills_without_an_agent_turn(self) -> None:
        assert skills_args("agy") == [
            "-p",
            "/skills",
            "--output-format",
            "json",
            "--model",
            PROBE_MODELS["agy"],
        ]

    def test_the_prompt_asks_for_names_only(self) -> None:
        assert SKILLS_PROMPT == (
            "List the name of every skill you can load, one name per line, and nothing else."
        )


class TestUnfinishedSessions:
    @pytest.mark.parametrize("harness", HARNESSES)
    @pytest.mark.parametrize("cut", ["timed_out", "stdout_truncated", "stderr_truncated"])
    def test_a_session_that_did_not_finish_gives_no_list(
        self, harness: HarnessName, cut: str
    ) -> None:
        # The output is a valid list, but a cut or timed-out Session proves nothing.
        stdout = lines(init(["rs-tdd"])) if harness == "claude" else '[{"name": "rs-tdd"}]'
        report = parse_skills(harness, result(stdout, cut=cut))
        assert report.names is None
        assert report.error == (f"{harness} did not finish within 120 s, or its output was cut")


class TestClaude:
    def test_the_init_event_lists_the_skills(self) -> None:
        stdout = lines(init(["rs-tdd", "tools:lint"]), done("ignored"))
        assert parse_skills("claude", result(stdout)) == SkillReport(
            frozenset({"rs-tdd", "tools:lint"}), None
        )

    def test_an_empty_init_list_is_a_list(self) -> None:
        assert parse_skills("claude", result(lines(init([])))) == SkillReport(frozenset(), None)

    def test_lines_that_are_not_json_objects_are_skipped(self) -> None:
        stdout = "starting\n[1, 2]\n42\n" + lines(init(["rs-tdd"])) + "\n"
        assert parse_skills("claude", result(stdout)).names == frozenset({"rs-tdd"})

    def test_without_skills_in_init_the_reply_is_the_list(self) -> None:
        stdout = lines(
            {"type": "system", "subtype": "init"}, done("- rs-tdd\n`/billing`\n$notes\n\n* extra")
        )
        assert parse_skills("claude", result(stdout)).names == frozenset(
            {"rs-tdd", "billing", "notes", "extra"}
        )

    def test_an_init_list_with_a_non_string_falls_back_to_the_reply(self) -> None:
        stdout = lines(init(["rs-tdd", 7]), done("rs-tdd\nbilling"))
        assert parse_skills("claude", result(stdout)).names == frozenset({"rs-tdd", "billing"})

    def test_the_last_result_event_is_the_reply(self) -> None:
        stdout = lines(done("first"), done("second"))
        assert parse_skills("claude", result(stdout)).names == frozenset({"second"})

    def test_an_error_result_gives_its_text_cut_to_one_line_of_300_characters(self) -> None:
        stdout = lines(done("API Error: 529 overloaded\nsecond line", is_error=True))
        assert parse_skills("claude", result(stdout, code=1)) == SkillReport(
            None, "API Error: 529 overloaded"
        )
        long = parse_skills("claude", result(lines(done("x" * 500, is_error=True))))
        assert long.error == "x" * 300

    def test_an_error_result_without_text_names_the_exit_code(self) -> None:
        for stdout in (lines(done("", is_error=True)), lines(done(None, is_error=True))):
            report = parse_skills("claude", result(stdout, code=1))
            assert report == SkillReport(None, "claude exited 1 with no skill list")

    def test_no_event_at_all_names_the_exit_code(self) -> None:
        assert parse_skills("claude", result("", code=2)) == SkillReport(
            None, "claude exited 2 with no skill list"
        )

    def test_a_result_without_is_error_is_not_a_reply(self) -> None:
        stdout = lines({"type": "result", "result": "rs-tdd"})
        assert parse_skills("claude", result(stdout)).names is None


class TestCodex:
    def test_the_last_agent_message_is_the_list(self) -> None:
        stdout = lines(
            {"type": "thread.started", "thread_id": "t"},
            agent_message("thinking"),
            {"type": "item.completed", "item": {"type": "command_execution", "text": "ls"}},
            agent_message("- rs-tdd\n* `billing-rules`\n/rs-setup\n$notes\n\n  spaced  \n"),
            {"type": "turn.completed", "usage": {}},
        )
        assert parse_skills("codex", result(stdout)) == SkillReport(
            frozenset({"rs-tdd", "billing-rules", "rs-setup", "notes", "spaced"}), None
        )

    def test_an_empty_reply_is_an_empty_list(self) -> None:
        stdout = lines(agent_message(""))
        assert parse_skills("codex", result(stdout)) == SkillReport(frozenset(), None)

    def test_a_failed_turn_gives_its_message(self) -> None:
        stdout = lines(
            {"type": "error", "message": "Reconnecting... 1/5"},
            {"type": "turn.failed", "error": {"message": "You exceeded your usage limit.\nMore"}},
        )
        assert parse_skills("codex", result(stdout, code=1)) == SkillReport(
            None, "You exceeded your usage limit."
        )

    def test_an_error_event_gives_its_message(self) -> None:
        stdout = lines({"type": "error", "message": "model not found"})
        assert parse_skills("codex", result(stdout, code=1)) == SkillReport(None, "model not found")

    def test_nothing_usable_names_the_exit_code(self) -> None:
        stdout = lines({"type": "turn.failed", "error": {}}, {"type": "error", "message": 3})
        assert parse_skills("codex", result(stdout, code=3)) == SkillReport(
            None, "codex exited 3 with no reply"
        )

    def test_a_reply_that_is_not_text_is_no_reply(self) -> None:
        stdout = lines({"type": "item.completed", "item": {"type": "agent_message", "text": 5}})
        assert parse_skills("codex", result(stdout)).names is None


class TestAgy:
    def test_a_json_array_of_named_objects_is_the_list(self) -> None:
        stdout = json.dumps(
            [{"name": "rs-tdd", "builtin": False}, {"name": "help", "builtin": True}]
        )
        assert parse_skills("agy", result(stdout)) == SkillReport(
            frozenset({"rs-tdd", "help"}), None
        )

    def test_an_empty_array_is_an_empty_list(self) -> None:
        assert parse_skills("agy", result("[]")) == SkillReport(frozenset(), None)

    @pytest.mark.parametrize(
        "stdout",
        ["", "not json", '{"name": "rs-tdd"}', '[{"name": "rs-tdd"}, {"builtin": true}]', "[1]"],
    )
    def test_anything_else_names_the_exit_code(self, stdout: str) -> None:
        assert parse_skills("agy", result(stdout, code=1)) == SkillReport(
            None, "agy printed no skill list (exit 1)"
        )

    def test_the_error_line_on_stderr_is_the_reason(self) -> None:
        stderr = "warming up\nerror: Eligibility check failed: UNAVAILABLE (code 503)\n"
        assert parse_skills("agy", result("", stderr, code=1)) == SkillReport(
            None, "error: Eligibility check failed: UNAVAILABLE (code 503)"
        )


class TestErrorLine:
    @pytest.mark.parametrize(
        ("stderr", "expected"),
        [
            ("", None),
            ("warning: not an error\n", None),
            ("  error: indented\n", None),
            ("note\nerror: first\nerror: second\n", "error: first"),
            ("AGY_ERROR: {}\nerror: later\n", "AGY_ERROR: {}"),
            ("error: " + "y" * 400, ("error: " + "y" * 400)[:300]),
        ],
    )
    def test_the_first_error_line_cut_to_300(self, stderr: str, expected: str | None) -> None:
        assert error_line(stderr) == expected
