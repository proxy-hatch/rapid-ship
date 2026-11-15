"""Offline: Reverts over local repositories and the recorded GitHub responses of their window."""

from pathlib import Path

import pytest

from devctl.metrics import partial_reverts
from devctl.metrics.model import Measured
from devctl.metrics.reverts import reverts
from devctl.process import run_process
from devctl.repo import Repo
from github_fakes import git
from metrics_fakes import MergedHistory, lock
from test_devctl_metrics_window import window as local_window


def measure(h: MergedHistory, agent: str | None = None) -> Measured:
    h.publish()
    return reverts(Repo.discover(h.path), local_window(h, agent=agent), "o/r")


def whole(pr: int, commit: str) -> dict[str, object]:
    return {"pr": pr, "state": "counted", "revert": "whole", "commit": commit}


def lines(first: int, last: int, word: str = "line") -> str:
    return "".join(f"{word} {n}\n" for n in range(first, last + 1))


def test_a_git_revert_line_counts(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"})
    h.merge(2, {"other.txt": "two\n"})
    undo = h.push({"note.txt": "x\n"}, f"Back out the feature\n\nThis reverts commit {first}.\n")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, undo),)


def test_a_reverted_merge_commit_counts(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"}, parents=2)
    undo = h.revert(first, merge=True)
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, undo),)


def test_the_revert_buttons_body_line_counts(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"feature.txt": "one\n"})
    button = h.merge(2, {"revert.txt": "x\n"}, body="Reverts o/r#1\n")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, button),)


@pytest.mark.parametrize(
    ("body", "counts"),
    [
        ("## Summary\n\nreverts O/R#1\r\n\nbecause it broke", True),
        ("Reverts o/r#12", False),
        ("Reverts o/r#1abc", False),
        ("Reverts other/repo#1", False),
        ("This pull request reverts o/r#1", False),
    ],
)
def test_the_body_line_is_compared_without_case_and_by_whole_number(
    tmp_path: Path, body: str, counts: bool
) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"feature.txt": "one\n"})
    button = h.merge(2, {"revert.txt": "x\n"}, body=body)
    result = measure(h)
    assert result.items == ((whole(1, button),) if counts else ())


def test_both_signals_count_once(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"})
    line = h.push({"note.txt": "x\n"}, f"Back out\n\nThis reverts commit {first}.\n")
    h.merge(2, {"revert.txt": "x\n"}, body="Reverts o/r#1")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, line),)


def test_a_pr_reverted_twice_counts_once_and_names_the_earliest_commit(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"})
    earliest = h.push({"note.txt": "x\n"}, f"Back out\n\nThis reverts commit {first}.\n")
    h.push({"note.txt": "y\n"}, f"Back out again\n\nThis reverts commit {first}.\n")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, earliest),)


def test_a_pr_named_by_two_revert_buttons_names_the_earlier_pr_merge(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"feature.txt": "one\n"})
    earlier = h.merge(2, {"revert.txt": "x\n"}, body="Reverts o/r#1")
    h.merge(3, {"revert-again.txt": "x\n"}, body="Reverts o/r#1")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, earlier),)


def test_an_abbreviated_sha_does_not_count(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"})
    h.push({"note.txt": "x\n"}, f"Back out\n\nThis reverts commit {first[:7]}.\n")
    assert measure(h) == Measured(0)


@pytest.mark.parametrize(
    "line", ["Note: This reverts commit {sha}.", "This reverts commit {sha}0."]
)
def test_a_mention_that_is_not_a_revert_line_does_not_count(tmp_path: Path, line: str) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"})
    h.push({"note.txt": "x\n"}, f"Back out\n\n{line.format(sha=first)}\n")
    assert measure(h) == Measured(0)


def test_a_revert_by_hand_that_restores_every_file_is_whole(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n"})
    h.merge(1, {"a.txt": "new\n", "b.txt": "added\n"})
    undo = h.push({"a.txt": "old\n", "b.txt": None}, "Back out the feature")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, undo),)


def test_a_partial_revert_names_its_files_and_sections(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    base = lines(1, 30)
    changed = lines(1, 4) + lines(5, 8, "alpha") + lines(9, 19) + lines(20, 23, "beta")
    changed += lines(24, 30)
    h.push({"a.txt": "old\n", "f.txt": base})
    h.merge(1, {"a.txt": "new\n", "f.txt": changed})
    half = lines(1, 4) + lines(5, 8) + lines(9, 19) + lines(20, 23, "beta") + lines(24, 30)
    undo = h.push({"a.txt": "old\n", "f.txt": half}, "Back out most of the change")
    result = measure(h)
    assert result.value == 1
    assert result.items == (
        {
            "pr": 1,
            "state": "counted",
            "revert": "partial",
            "commit": undo,
            "files": ["a.txt"],
            "sections": ["f.txt:5-8"],
        },
    )


def test_a_whole_revert_outranks_a_partial_one(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n", "b.txt": "old\n"})
    first = h.merge(1, {"a.txt": "new\n", "b.txt": "new\n"})
    h.push({"a.txt": "old\n"}, "Back out the change to a")
    undo = h.push({"note.txt": "x\n"}, f"Back out the rest\n\nThis reverts commit {first}.\n")
    result = measure(h)
    assert result.value == 1
    assert result.items == (whole(1, undo),)


def test_any_pr_may_revert_an_agent_pr_but_only_agent_prs_count(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"agent.txt": "x\n"})
    h.merge(2, {"person.txt": "x\n"}, author="person")
    button = h.merge(3, {"revert.txt": "x\n"}, author="person", body="Reverts o/r#1")
    h.merge(4, {"revert-too.txt": "x\n"}, body="Reverts o/r#2")
    result = measure(h, agent="o-worker[bot]")
    assert result.value == 1
    assert result.items == (whole(1, button),)


def test_a_pr_with_no_parent_here_is_unknown_unless_a_revert_names_it(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    first = h.merge(1, {"feature.txt": "one\n"})
    h.merge(2, {"other.txt": "two\n"})
    git(h.path, "replace", "--graft", first)  # a shallow clone ends at a commit like this
    result = measure(h)
    assert (result.value, result.unknown) == (0, 1)
    assert result.items == (
        {
            "pr": 1,
            "state": "unknown",
            "detail": (
                "its merge commit has no parent in this clone: run git fetch --unshallow and rerun"
            ),
        },
    )
    undo = h.push({"note.txt": "x\n"}, f"Back out\n\nThis reverts commit {first}.\n")
    assert measure(h).items == (whole(1, undo),)


def test_a_body_that_names_a_later_pr_does_not_count(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"one.txt": "x\n"}, body="Reverts o/r#2")
    h.merge(2, {"two.txt": "x\n"})
    assert measure(h) == Measured(0)


def test_a_body_that_names_its_own_pr_does_not_count(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.merge(1, {"one.txt": "x\n"}, body="Reverts o/r#1")
    assert measure(h) == Measured(0)


def test_a_pr_whose_comparisons_outgrow_the_budget_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = MergedHistory(tmp_path)
    h.push({"uv.lock": lock(0, 12)})
    h.merge(1, {"uv.lock": lock(1, 12)})
    for version in range(2, 5):
        h.push({"uv.lock": lock(version, 12)})
    monkeypatch.setattr(partial_reverts, "COMPARISON_BUDGET", 1_000_000)
    result = measure(h)
    assert (result.value, result.unknown) == (0, 1)
    assert result.items == (
        {
            "pr": 1,
            "state": "unknown",
            "detail": (
                "the content check was cut short in uv.lock, where its comparison budget ran out: "
                "the PR is neither counted nor cleared"
            ),
        },
    )


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("remote.origin.promisor", "true"),
        ("remote.origin.promisor", "1"),
        ("remote.origin.promisor", "yes"),
        ("remote.origin.promisor", "on"),
        ("remote.origin.promisor", None),  # a key without a value, which git reads as true
        ("extensions.partialclone", "origin"),
    ],
)
def test_a_partial_clone_makes_the_pr_unknown_unless_a_revert_names_it(
    tmp_path: Path, setting: str, value: str | None
) -> None:
    h = MergedHistory(tmp_path)
    base = lines(1, 4) + lines(5, 8) + lines(9, 30)
    h.push({"f.txt": base})
    first = h.merge(1, {"f.txt": lines(1, 4) + lines(5, 8, "alpha") + lines(9, 30)})
    h.push({"f.txt": base + "tail\n"})
    if value is None:
        config = h.path / ".git/config"
        config.write_text(config.read_text() + '[remote "origin"]\n\tpromisor\n')
    else:
        git(h.path, "config", setting, value)
    result = measure(h)
    assert (result.value, result.unknown) == (0, 1)
    assert result.items == (
        {
            "pr": 1,
            "state": "unknown",
            "detail": (
                "this clone is partial, and reading file contents would fetch them: "
                "clone again without --filter and rerun"
            ),
        },
    )
    undo = h.push({"note.txt": "x\n"}, f"Back out\n\nThis reverts commit {first}.\n")
    assert measure(h).items == (whole(1, undo),)


def test_log_show_signature_does_not_change_what_is_read(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path / "repo")
    key = tmp_path / "key"
    made = run_process(
        ["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)], tmp_path, 60
    )
    assert made.returncode == 0, made.stderr
    for name, value in (
        ("gpg.format", "ssh"),
        ("user.signingkey", str(key)),
        ("commit.gpgsign", "true"),
        ("log.showSignature", "true"),
    ):
        git(h.path, "config", name, value)
    base = lines(1, 4) + lines(5, 8) + lines(9, 30)
    h.push({"f.txt": base})
    h.merge(1, {"f.txt": lines(1, 4) + lines(5, 8, "alpha") + lines(9, 30)})
    undo = h.push({"f.txt": base + "tail\n"}, "Back out most of the change")
    first = h.merge(2, {"feature.txt": "one\n"})
    revert = h.push({"note.txt": "x\n"}, f"Back out\n\nThis reverts commit {first}.\n")
    assert "gpgsig" in git(h.path, "cat-file", "-p", "HEAD")
    partial = {"pr": 1, "state": "counted", "revert": "partial", "commit": undo}
    assert measure(h).items == (
        whole(2, revert),
        {**partial, "files": [], "sections": ["f.txt:5-8"]},
    )
