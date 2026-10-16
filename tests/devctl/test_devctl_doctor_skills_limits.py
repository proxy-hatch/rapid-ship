"""Offline: the edges of doctor --skills: how a repository's skills are read, how the items are
worded, and how the flag reaches run_doctor. Fake Harness executables and stubbed items only; no
real Harness runs."""

import argparse
import json
from dataclasses import replace
from pathlib import Path

import pytest

from devctl import cli, doctor
from devctl.doctor import (
    DoctorContext,
    Item,
    probed_harnesses,
    repository_skills,
    run_doctor,
    skills_items,
)
from devctl.settings import Agent, ProjectSettings
from github_fakes import FakeHarness, Remote, git
from github_fixtures import no_owner_reads


@pytest.fixture
def doctor_ctx(remote: Remote, project: ProjectSettings) -> DoctorContext:
    return DoctorContext(remote.clone, project, no_owner_reads, None)


def write_skill(tree: Path, name: str, text: str | bytes | None) -> None:
    """A skill directory under tree; text None leaves it without a SKILL.md."""
    skill = tree / ".agents" / "skills" / name
    skill.mkdir(parents=True)
    if isinstance(text, str):
        (skill / "SKILL.md").write_text(text)
    elif text is not None:
        (skill / "SKILL.md").write_bytes(text)


class TestRepositorySkills:
    def test_a_tree_without_skills_has_none(self, tmp_path: Path) -> None:
        assert repository_skills(tmp_path) == (frozenset(), frozenset())

    def test_only_directories_with_a_skill_manifest_count(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "rs-tdd", "---\nname: rs-tdd\n---\n")
        write_skill(tmp_path, "no-manifest", None)
        (tmp_path / ".agents" / "skills" / "README.md").write_text("not a skill\n")
        assert repository_skills(tmp_path) == (frozenset({"rs-tdd"}), frozenset())

    def test_the_directory_name_is_the_skill_name(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "dir-name", "---\nname: another-name\n---\n")
        assert repository_skills(tmp_path) == (frozenset({"dir-name"}), frozenset())

    def test_a_skill_that_only_the_owner_invokes_is_not_checked(self, tmp_path: Path) -> None:
        write_skill(tmp_path, "rs-tdd", "---\nname: rs-tdd\n---\n")
        write_skill(
            tmp_path, "rs-setup", "---\nname: rs-setup\ndisable-model-invocation: true\n---\n"
        )
        assert repository_skills(tmp_path) == (frozenset({"rs-tdd"}), frozenset({"rs-setup"}))

    @pytest.mark.parametrize(
        "text",
        [
            "---\nname: x\ndisable-model-invocation: false\n---\n",
            '---\nname: x\ndisable-model-invocation: "true"\n---\n',
            "---\nname: x\n---\n",
            "no front matter\n",
            "---\nname: x\n",  # never closed
            "---\n: : :\n  - [\n---\n",  # not YAML
            "---\n- a\n- b\n---\n",  # not a mapping
            b"---\nname: \xff\xfe\n---\n",  # not UTF-8
        ],
    )
    def test_front_matter_that_does_not_say_true_leaves_the_skill_checked(
        self, tmp_path: Path, text: str | bytes
    ) -> None:
        write_skill(tmp_path, "x", text)
        assert repository_skills(tmp_path) == (frozenset({"x"}), frozenset())


class TestNames:
    def test_roster_harnesses_are_named_for_their_roles_in_role_order(
        self, project: ProjectSettings, fake_harness: FakeHarness
    ) -> None:
        shared = replace(
            project, roster={"reviewer": Agent("codex", "m2"), "worker": Agent("codex", "m1")}
        )
        assert probed_harnesses(shared) == {"codex": "worker and reviewer skills (codex)"}
        assert probed_harnesses(project) == {
            "agy": "worker skills (agy)",
            "claude": "reviewer skills (claude)",
        }

    def test_without_a_roster_only_supported_harnesses_on_path_are_named(
        self, project: ProjectSettings, fake_harness: FakeHarness
    ) -> None:
        fake_harness.install("codex")
        fake_harness.install("pi")
        assert probed_harnesses(replace(project, roster={})) == {"codex": "skills (codex)"}

    def test_the_item_lists_missing_outside_and_user_invoked_skills(
        self, doctor_ctx: DoctorContext, remote: Remote, fake_harness: FakeHarness
    ) -> None:
        for name in ("b-skill", "a-skill", "c-skill"):
            write_skill(remote.clone, name, f"---\nname: {name}\ndescription: d\n---\n")
        write_skill(
            remote.clone,
            "u-skill",
            "---\nname: u-skill\ndescription: d\ndisable-model-invocation: true\n---\n",
        )
        git(remote.clone, "add", ".agents")
        git(remote.clone, "commit", "-q", "-m", "skills")
        listed = [{"name": n} for n in ("c-skill", "z-out", "m-out", "u-skill")]
        fake_harness.install("agy", stdout=json.dumps(listed))
        solo = replace(doctor_ctx.project, roster={"worker": Agent("agy", "m")})
        assert skills_items(replace(doctor_ctx, project=solo)) == [
            Item(
                "skills",
                "worker skills (agy)",
                "missing",
                "missing: a-skill, b-skill; outside the repository: m-out, z-out; "
                "not checked, user-invoked: u-skill",
            )
        ]


class TestRunDoctor:
    @pytest.fixture
    def stubbed(self, monkeypatch: pytest.MonkeyPatch) -> list[str]:
        """The other items stubbed out; the list records each skills_items call."""
        calls: list[str] = []

        def skills(ctx: DoctorContext) -> list[Item]:
            calls.append("skills")
            return [Item("skills", "worker skills (agy)", "missing", "missing: rs-tdd")]

        monkeypatch.setattr(
            doctor, "local_items", lambda ctx: [Item("toolchain", "git", "ok", "2")]
        )
        monkeypatch.setattr(
            doctor, "github_items", lambda ctx: [Item("github", "ruleset", "ok", "")]
        )
        monkeypatch.setattr(doctor, "skills_items", skills)
        return calls

    def test_without_the_flag_no_skills_item_is_built(
        self,
        doctor_ctx: DoctorContext,
        stubbed: list[str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert run_doctor(doctor_ctx) == 0
        assert stubbed == []
        assert capsys.readouterr().out.splitlines()[-1] == "doctor: 2 ok, 0 missing, 0 unknown"

    def test_with_the_flag_the_skills_items_follow_the_others(
        self,
        doctor_ctx: DoctorContext,
        stubbed: list[str],
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert run_doctor(doctor_ctx, skills=True) == 1
        assert stubbed == ["skills"]
        assert capsys.readouterr().out.splitlines() == [
            "ok  toolchain  git: 2",
            "ok  github  ruleset: ",
            "missing  skills  worker skills (agy): missing: rs-tdd",
            "doctor: 2 ok, 1 missing, 0 unknown",
        ]


class TestCommand:
    def test_the_flag_defaults_to_off_and_reaches_run_doctor(
        self, remote: Remote, project: ProjectSettings, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        passed: list[bool] = []

        def record(ctx: DoctorContext, *, skills: bool = False) -> int:
            passed.append(skills)
            return 0

        monkeypatch.chdir(remote.clone)
        monkeypatch.setattr(doctor, "git_item", lambda: Item("toolchain", "git", "ok", "2.39"))
        monkeypatch.setattr(doctor, "load_project", lambda root: project)
        monkeypatch.setattr(doctor, "run_doctor", record)
        parser = cli.build_parser()
        for argv in (["doctor"], ["doctor", "--skills"]):
            args = parser.parse_args(argv)
            assert args.handler(args) == 0
        assert passed == [False, True]

    def test_help_lists_the_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        with pytest.raises(SystemExit) as raised:
            cli.main(["doctor", "--help"])
        assert raised.value.code == 0
        out = " ".join(capsys.readouterr().out.split())
        assert "--skills" in out
        assert "spends a little quota" in out

    def test_a_namespace_from_the_parser_has_the_flag(self) -> None:
        args = cli.build_parser().parse_args(["doctor", "--skills"])
        assert isinstance(args, argparse.Namespace)
        assert args.skills is True
