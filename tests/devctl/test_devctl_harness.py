"""Offline: how doctor --skills asks Claude Code for its skills and reads the answer. Every output
is a simulated Claude Code result; no Harness runs."""

import json

import pytest

from devctl.harness import PROBE_MODEL, SKILLS_PROMPT, SkillReport, parse_skills, skills_args
from devctl.process import ProcessResult


def result(
    stdout: str = "", stderr: str = "", code: int = 0, *, cut: str | None = None
) -> ProcessResult:
    """A finished Session's result, or one cut short: cut names the ProcessResult flag to set."""
    return ProcessResult(
        ["claude"],
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


class TestSkillsArgs:
    def test_claude_prints_its_own_skill_list_in_the_init_event(self) -> None:
        assert skills_args() == [
            "-p",
            SKILLS_PROMPT,
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            PROBE_MODEL,
        ]

    def test_the_prompt_asks_for_names_only(self) -> None:
        assert SKILLS_PROMPT == (
            "List the name of every skill you can load, one name per line, and nothing else."
        )


class TestUnfinishedSessions:
    @pytest.mark.parametrize("cut", ["timed_out", "stdout_truncated", "stderr_truncated"])
    def test_a_session_that_did_not_finish_gives_no_list(self, cut: str) -> None:
        # The output is a valid list, but a cut or timed-out Session proves nothing.
        report = parse_skills(result(lines(init(["rs-tdd"])), cut=cut))
        assert report.names is None
        assert report.error == "claude did not finish within 120 s, or its output was cut"


class TestClaude:
    def test_the_init_event_lists_the_skills(self) -> None:
        stdout = lines(init(["rs-tdd", "tools:lint"]), done("ignored"))
        assert parse_skills(result(stdout)) == SkillReport(
            frozenset({"rs-tdd", "tools:lint"}), None
        )

    def test_an_empty_init_list_is_a_list(self) -> None:
        assert parse_skills(result(lines(init([])))) == SkillReport(frozenset(), None)

    def test_lines_that_are_not_json_objects_are_skipped(self) -> None:
        stdout = "starting\n[1, 2]\n42\n" + lines(init(["rs-tdd"])) + "\n"
        assert parse_skills(result(stdout)).names == frozenset({"rs-tdd"})

    def test_without_skills_in_init_the_reply_is_the_list(self) -> None:
        stdout = lines(
            {"type": "system", "subtype": "init"}, done("- rs-tdd\n`/billing`\n$notes\n\n* extra")
        )
        assert parse_skills(result(stdout)).names == frozenset(
            {"rs-tdd", "billing", "notes", "extra"}
        )

    def test_an_init_list_with_a_non_string_falls_back_to_the_reply(self) -> None:
        stdout = lines(init(["rs-tdd", 7]), done("rs-tdd\nbilling"))
        assert parse_skills(result(stdout)).names == frozenset({"rs-tdd", "billing"})

    def test_the_last_result_event_is_the_reply(self) -> None:
        stdout = lines(done("first"), done("second"))
        assert parse_skills(result(stdout)).names == frozenset({"second"})

    def test_an_error_result_gives_its_text_cut_to_one_line_of_300_characters(self) -> None:
        stdout = lines(done("API Error: 529 overloaded\nsecond line", is_error=True))
        assert parse_skills(result(stdout, code=1)) == SkillReport(
            None, "API Error: 529 overloaded"
        )
        long = parse_skills(result(lines(done("x" * 500, is_error=True))))
        assert long.error == "x" * 300

    def test_an_error_result_without_text_names_the_exit_code(self) -> None:
        for stdout in (lines(done("", is_error=True)), lines(done(None, is_error=True))):
            report = parse_skills(result(stdout, code=1))
            assert report == SkillReport(None, "claude exited 1 with no skill list")

    def test_no_event_at_all_names_the_exit_code(self) -> None:
        assert parse_skills(result("", code=2)) == SkillReport(
            None, "claude exited 2 with no skill list"
        )

    def test_a_result_without_is_error_is_not_a_reply(self) -> None:
        stdout = lines({"type": "result", "result": "rs-tdd"})
        assert parse_skills(result(stdout)).names is None
