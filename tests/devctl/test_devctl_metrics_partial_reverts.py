"""Offline: the content check over local repositories."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path

import pytest

from devctl.metrics import partial_reverts
from devctl.metrics.partial_reverts import Undoing, undoing
from devctl.metrics.window import MetricsError
from devctl.repo import Repo
from github_fakes import git
from metrics_fakes import MergedHistory, lock

BINARY = b"\x00\x01" * 20
NAMES = tuple(
    f"{verb}_{noun}"
    for verb in ("get", "set", "load", "save")
    for noun in ("user", "item", "path", "token", "state", "file")
)
ORIGINAL = [
    "total = price * quantity + shipping",
    "tax = round(total * rate, 2) + fees",
    "return total + tax - discount",
]
BUDGET = 1_000_000


def code(count: int, call: str = "compute") -> list[str]:
    """Varied lines of code that each call one function named `call_<word>`."""
    return [
        f"{NAMES[(n * 5 + 3) % 24]}_{n} = {call}_{NAMES[(n * 11 + 7) % 24]}"
        f"({NAMES[(n * 13 + 1) % 24]}, limit={n % 17})"
        for n in range(count)
    ]


def bits(seed: str, count: int, width: int = 59) -> list[str]:
    """`count` rows of 0 and 1 that look random and are the same on every run."""
    stream = "".join(
        f"{int(sha256(f'{seed}{n}'.encode()).hexdigest(), 16):0256b}"
        for n in range(count * width // 256 + 1)
    )
    return [stream[row * width : (row + 1) * width] for row in range(count)]


def damaged(lines: Sequence[str], count: int) -> list[str]:
    """The lines with `count` evenly spread letters replaced by #."""
    chars = list("\n".join(lines))
    letters = [i for i, char in enumerate(chars) if char.isalpha()]
    for i in letters[:: len(letters) // count][:count]:
        chars[i] = "#"
    return "".join(chars).split("\n")


@dataclass(frozen=True)
class GarbledRepo(Repo):
    damage: Callable[[str], str]

    def git(self, *args: str) -> str:
        output = super().git(*args)
        return self.damage(output) if "--raw" in args else output


def rows(first: int, last: int, word: str = "line") -> list[str]:
    return [f"{word} {n}" for n in range(first, last + 1)]


def text(*parts: Sequence[str]) -> str:
    return "".join(f"{row}\n" for part in parts for row in part)


def doc_rows(a: Sequence[str], b: Sequence[str], skip: int = 4) -> list[str]:
    """Thirty lines, but `a` replaces the `skip` lines from line 5 and `b` lines 20-23."""
    return [*rows(1, 4), *a, *rows(5 + skip, 19), *b, *rows(24, 30)]


def doc(a: Sequence[str], b: Sequence[str], skip: int = 4) -> str:
    return text(doc_rows(a, b, skip))


def check(h: MergedHistory, merge: str) -> Undoing | None:
    return undoing(Repo.discover(h.path), merge, git(h.path, "rev-parse", "HEAD"))


def record_checks(monkeypatch: pytest.MonkeyPatch) -> tuple[list[tuple[int, int]], list[int]]:
    """Record what the checks pay and compare.

    The first list has one entry for each check that builds a matcher: the characters of its two
    texts, and the charge that came just before it. The second holds every charge a check asked
    for, the one the budget refused last.
    """
    checks: list[tuple[int, int]] = []
    attempts: list[int] = []
    spend = partial_reverts.Budget.spend

    def spying(self: partial_reverts.Budget, cost: int) -> None:
        attempts.append(cost)
        spend(self, cost)

    class Recording(partial_reverts._Metered):
        def __init__(self, a: str, b: str, budget: partial_reverts.Budget) -> None:
            checks.append((len(a) + len(b), attempts[-1]))
            super().__init__(a, b, budget)

    monkeypatch.setattr(partial_reverts.Budget, "spend", spying)
    monkeypatch.setattr(partial_reverts, "_Metered", Recording)
    return checks, attempts


def test_a_restored_file(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n", "b.txt": "old\n"})
    pr = h.push({"a.txt": "new\n", "b.txt": "new\n"})
    undo = h.push({"a.txt": "old\n"})
    assert check(h, pr) == Undoing(undo, False, ("a.txt",), ())


def test_an_added_file_deleted(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"keep.txt": "old\n"})
    pr = h.push({"keep.txt": "new\n", "added.txt": "fresh\n"})
    undo = h.push({"added.txt": None})
    assert check(h, pr) == Undoing(undo, False, ("added.txt",), ())


def test_a_deleted_file_brought_back(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"keep.txt": "old\n", "gone.txt": "was here\n"})
    pr = h.push({"keep.txt": "new\n", "gone.txt": None})
    undo = h.push({"gone.txt": "was here\n"})
    assert check(h, pr) == Undoing(undo, False, ("gone.txt",), ())


def test_an_undone_section(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    undo = h.push({"f.txt": doc(rows(5, 8), rows(20, 23, "beta"))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


def test_the_users_git_settings_do_not_change_what_is_found(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    git(h.path, "config", "color.ui", "always")
    git(h.path, "config", "diff.interHunkContext", "20")
    git(h.path, "config", "diff.algorithm", "histogram")
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    undo = h.push({"f.txt": doc(rows(5, 8), rows(20, 23, "beta"))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


def test_log_follow_does_not_hide_a_section_brought_back_by_a_rename(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    git(h.path, "config", "log.follow", "true")
    h.push({"gone.txt": text(rows(1, 6)), "keep.txt": "old\n"})
    pr = h.push({"gone.txt": None, "keep.txt": "new\n"})
    # The lines return under the old name by renaming another file, with one word changed.
    h.push({"other.txt": text(rows(1, 5), ["line six"])})
    undo = h.push({"other.txt": None, "gone.txt": text(rows(1, 5), ["line six"])})
    assert check(h, pr) == Undoing(undo, False, (), ("gone.txt:1-1",))


def test_files_are_listed_in_path_order_whatever_git_orders_its_diffs_by(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path / "repo")
    order = tmp_path / "order"
    order.write_text("c.txt\nb.txt\na.txt\n")
    git(h.path, "config", "diff.orderFile", str(order))
    h.push({"a.txt": "old\n", "b.txt": "old\n", "c.txt": "old\n"})
    pr = h.push({"a.txt": "new\n", "b.txt": "new\n", "c.txt": "new\n"})
    undo = h.push({"a.txt": "old\n", "b.txt": "old\n", "c.txt": "old\n"})
    assert check(h, pr) == Undoing(undo, True, ("a.txt", "b.txt", "c.txt"), ())


def test_a_section_undone_after_other_commits_moved_it(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    header = rows(1, 10, "header")
    h.push({"f.txt": text(header, doc_rows(rows(5, 8, "alpha"), rows(20, 23, "beta")))})
    undo = h.push({"f.txt": text(header, doc_rows(rows(5, 8), rows(20, 23, "beta")))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


def test_a_section_undone_with_small_edits_above_the_threshold(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    # One word of four lines differs from the original: 26 of 27 and 31 characters match, 0.90.
    restored = ["line 5", "line 6", "line seven", "line 8"]
    undo = h.push({"f.txt": doc(restored, rows(20, 23, "beta"))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


@pytest.mark.parametrize(("first", "named"), [(10, "f.txt:9-9"), (1, "f.txt:1-1")])
def test_a_deleted_section_brought_back_is_named_by_the_line_before_it(
    tmp_path: Path, first: int, named: str
) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": text(rows(1, 30))})
    pr = h.push({"f.txt": text(rows(1, first - 1), rows(first + 3, 30))})
    # The three lines return with one word changed.
    back = [f"line {first}", f"line {first + 1}", f"line {first + 2}!"]
    undo = h.push({"f.txt": text(rows(1, first - 1), back, rows(first + 3, 30))})
    assert check(h, pr) == Undoing(undo, False, (), (named,))


def test_lines_are_compared_without_their_surrounding_whitespace(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    # One commit indents the PR's lines and the next replaces them with the old lines, also
    # indented. The indentation alone would keep both below the threshold.
    indent = "            "
    h.push({"f.txt": doc([indent + row for row in rows(5, 8, "alpha")], rows(20, 23, "beta"))})
    undo = h.push({"f.txt": doc([indent + row for row in rows(5, 8)], rows(20, 23, "beta"))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


def test_a_section_below_the_threshold_does_not_count(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    # Every line is reworded: only the 23 characters of "line " and the line breaks match the
    # original's 27 and the new text's 40, 0.69.
    reworded = ["line five", "line six", "line seven", "line eight"]
    h.push({"f.txt": doc(reworded, rows(20, 23, "beta"))})
    assert check(h, pr) is None


@pytest.mark.parametrize(
    ("removed", "added", "counts"),
    [
        (1, ["alpha 5"], False),
        (1, ["alpha 5", ""], False),
        (1, ["alpha 5", "alpha 6"], True),
        (2, ["alpha 5"], True),
    ],
)
def test_a_hunk_under_3_non_blank_lines_is_ignored(
    tmp_path: Path, removed: int, added: list[str], counts: bool
) -> None:
    h = MergedHistory(tmp_path)
    original = rows(5, 4 + removed)
    h.push({"f.txt": doc(original, rows(20, 23), removed)})
    pr = h.push({"f.txt": doc(added, rows(20, 23, "beta"), removed)})
    undo = h.push({"f.txt": doc(original, rows(20, 23, "beta"), removed)})
    expected = Undoing(undo, False, (), (f"f.txt:5-{4 + len(added)}",)) if counts else None
    assert check(h, pr) == expected


def test_a_pure_addition_removed_later_does_not_count(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": text(rows(1, 30))})
    pr = h.push({"f.txt": text(rows(1, 10), rows(1, 4, "extra"), rows(11, 30))})
    # The block goes, but line 1 also changes, so the file is not back to what it was.
    h.push({"f.txt": text(["edited"], rows(2, 30))})
    assert check(h, pr) is None


def test_a_rename_undone_is_a_whole_revert(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"old.txt": text(rows(1, 5))})
    pr = h.push({"old.txt": None, "new.txt": text(rows(1, 5))})
    undo = h.push({"new.txt": None, "old.txt": text(rows(1, 5))})
    assert check(h, pr) == Undoing(undo, True, ("new.txt", "old.txt"), ())


def test_a_binary_file_counts_only_when_restored(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"logo.bin": BINARY, "keep.txt": "old\n"})
    pr = h.push({"logo.bin": b"\x00\x02" * 20, "keep.txt": "new\n"})
    h.push({"logo.bin": b"\x00\x03" * 20})
    assert check(h, pr) is None
    undo = h.push({"logo.bin": BINARY})
    assert check(h, pr) == Undoing(undo, False, ("logo.bin",), ())


def test_a_refactor_that_rewrites_the_prs_lines_is_not_a_revert(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    changed = [
        "total = price * quantity",
        "tax = round(total * rate, 2)",
        "total = total + tax",
        "return total",
    ]
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(changed, rows(20, 23, "beta"))})
    # The refactor removes exactly the PR's lines, but what it writes is not what they replaced.
    h.push({"f.txt": doc(["return Invoice(price, quantity, rate).total()"], rows(20, 23, "beta"))})
    assert check(h, pr) is None


def test_old_lines_written_over_other_lines_are_not_an_undone_section(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    red, blue = rows(5, 8, "red"), rows(20, 23, "blue")
    h.push({"f.txt": doc(red, blue)})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    # The red lines come back, but over lines 20-23 and not over what the PR wrote at 5-8, and the
    # PR's lines at 20-23 go without the blue lines coming back.
    h.push({"f.txt": doc(rows(5, 8, "alpha"), red)})
    assert check(h, pr) is None


def test_a_later_move_of_an_added_file_counts_as_restored(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"keep.txt": "old\n"})
    pr = h.push({"keep.txt": "new\n", "tool.py": "print('x')\n"})
    moved = h.push({"tool.py": None, "pkg/tool.py": "print('x')\n"})
    assert check(h, pr) == Undoing(moved, False, ("tool.py",), ())


def test_a_restored_file_lists_no_sections(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    undo = h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    assert check(h, pr) == Undoing(undo, True, ("f.txt",), ())


def test_sections_are_listed_in_file_order_and_the_earliest_commit_is_named(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    first = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23))})
    # Lines 5-8 come back last, with one word changed, so the file never equals the original.
    h.push({"f.txt": doc(["line 5", "line 6", "line seven", "line 8"], rows(20, 23))})
    assert check(h, pr) == Undoing(first, False, (), ("f.txt:5-8", "f.txt:20-23"))


def test_a_file_restored_twice_names_the_first_restoration(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n", "b.txt": "old\n"})
    pr = h.push({"a.txt": "new\n", "b.txt": "new\n"})
    first = h.push({"a.txt": "old\n"})
    h.push({"a.txt": "newer\n"})
    h.push({"a.txt": "old\n"})
    assert check(h, pr) == Undoing(first, False, ("a.txt",), ())


def test_the_earliest_undoing_commit_is_named(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n", "b.txt": "old\n", "c.txt": "old\n"})
    pr = h.push({"a.txt": "new\n", "b.txt": "new\n", "c.txt": "new\n"})
    first = h.push({"b.txt": "old\n"})
    h.push({"a.txt": "old\n"})
    assert check(h, pr) == Undoing(first, False, ("a.txt", "b.txt"), ())


def test_a_path_with_glob_characters_is_matched_literally(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    original = doc(rows(5, 8), rows(20, 23))
    h.push({"[id].txt": original, "d.txt": original})
    changed = doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))
    pr = h.push({"[id].txt": changed, "d.txt": changed})
    # d.txt gets its lines 5-8 back, and [id].txt, which that glob also matches, an unrelated edit.
    undo = h.push({"d.txt": doc(rows(5, 8), rows(20, 23, "beta")), "[id].txt": changed + "more\n"})
    assert check(h, pr) == Undoing(undo, False, (), ("d.txt:5-8",))


def test_a_two_parent_merge_is_compared_with_its_first_parent(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n", "b.txt": "old\n"})
    merge = h.merge(1, {"a.txt": "new\n", "b.txt": "new\n"}, parents=2)
    undo = h.push({"a.txt": "old\n"})
    assert check(h, merge) == Undoing(undo, False, ("a.txt",), ())


def test_a_later_merge_commit_is_compared_with_its_first_parent(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n", "b.txt": "old\n"})
    pr = h.push({"a.txt": "new\n", "b.txt": "new\n"})
    merge = h.merge(2, {"a.txt": "old\n"}, parents=2)
    assert check(h, pr) == Undoing(merge, False, ("a.txt",), ())


def test_a_pr_with_no_later_commit_has_no_undoing(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    pr = h.push({"a.txt": "new\n"})
    assert check(h, pr) is None


def test_a_pr_that_changed_no_files_has_no_undoing(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n"})
    pr = h.push({})
    h.push({"a.txt": "new\n"})
    assert check(h, pr) is None


@pytest.mark.parametrize("count", [3, 10, 30, 100])
def test_a_word_renamed_on_every_line_is_similar_at_any_section_size(
    tmp_path: Path, count: int
) -> None:
    original, restored = code(count), code(count, "derive")
    a, b = "\n".join(original), "\n".join(restored)
    assert SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.8
    # From 200 characters on, difflib's default skips every character that is over 1% of the text.
    assert count == 3 or SequenceMatcher(None, a, b).ratio() < 0.8
    h = MergedHistory(tmp_path)
    h.push({"f.txt": text(rows(1, 4), original, rows(5, 8))})
    pr = h.push({"f.txt": text(rows(1, 4), rows(1, count, "alpha"), rows(5, 8))})
    undo = h.push({"f.txt": text(rows(1, 4), restored, rows(5, 8))})
    assert check(h, pr) == Undoing(undo, False, (), (f"f.txt:5-{4 + count}",))


@pytest.mark.parametrize(("count", "ratio", "counts"), [(21, 0.79, False), (19, 0.81, True)])
def test_a_ratio_of_0_81_counts_and_one_of_0_79_does_not(
    tmp_path: Path, count: int, ratio: float, counts: bool
) -> None:
    restored = damaged(ORIGINAL, count)
    measured = SequenceMatcher(None, "\n".join(ORIGINAL), "\n".join(restored)).ratio()
    assert measured == pytest.approx(ratio, abs=0.005)
    h = MergedHistory(tmp_path)
    h.push({"f.txt": doc(ORIGINAL, rows(20, 23), 3)})
    pr = h.push({"f.txt": doc(rows(5, 7, "alpha"), rows(20, 23, "beta"), 3)})
    undo = h.push({"f.txt": doc(restored, rows(20, 23, "beta"), 3)})
    expected = Undoing(undo, False, (), ("f.txt:5-7",)) if counts else None
    assert check(h, pr) == expected


def regenerated_lock(h: MergedHistory) -> str:
    """A PR that rewrites a lock file with 12 packages, which three later commits rewrite again."""
    h.push({"uv.lock": lock(0, 12)})
    pr = h.push({"uv.lock": lock(1, 12)})
    for version in range(2, 5):
        h.push({"uv.lock": lock(version, 12)})
    return pr


def test_the_comparisons_of_a_regenerated_file_stop_at_the_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pr = regenerated_lock(MergedHistory(tmp_path))
    monkeypatch.setattr(partial_reverts, "COMPARISON_BUDGET", BUDGET)
    checks, attempts = record_checks(monkeypatch)
    with pytest.raises(partial_reverts.Unfinished) as stopped:
        undoing(Repo.discover(tmp_path), pr, git(tmp_path, "rev-parse", "HEAD"))
    assert str(stopped.value) == (
        "the content check was cut short in uv.lock, where its comparison budget ran out: "
        "the PR is neither counted nor cleared"
    )
    # The run stops at the first charge that no longer fits, and each check paid its base cost and
    # 10 units for each character of its two texts before it built its matcher.
    spent = sum(attempts[:-1])
    assert spent <= BUDGET < spent + attempts[-1]
    assert all(paid == partial_reverts.CHECK_COST + 10 * size for size, paid in checks)
    # The 36 hunks of the later commits against each of the PR's 12, and some check was made.
    assert 0 < len(checks) < 12 * 36


def test_a_ratio_spends_four_units_for_each_character_it_passes_and_one_for_each_position() -> None:
    budget = partial_reverts.Budget(1_000)
    assert partial_reverts._Metered("abcd", "abxd", budget).ratio() == 0.75
    # Its three searches: all of `abcd` against `abxd`, where `a`, `b` and `d` each have one
    # position, then `cd` against `xd`, where only `d` has one, then `c` against `x`, with none.
    # A search pays four units for each character it passes and one for each position it scans.
    assert budget.left == 1_000 - (4 * 4 + 3) - (4 * 2 + 1) - (4 * 1 + 0)


def test_a_pair_that_is_short_but_costly_to_search_runs_out_the_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = MergedHistory(tmp_path)
    h.push({"f.txt": text(rows(1, 4), bits("old", 16), rows(5, 8))})
    pr = h.push({"f.txt": text(rows(1, 4), rows(1, 3, "alpha"), rows(5, 8))})
    h.push({"f.txt": text(rows(1, 4), bits("new", 16), rows(5, 8))})
    # The two texts have 959 characters each, so the product of their lengths is 0.92 million. A
    # ratio between them scans about twice that many positions, which is where its time goes.
    monkeypatch.setattr(partial_reverts, "COMPARISON_BUDGET", 1_300_000)
    with pytest.raises(partial_reverts.Unfinished, match=r"cut short in f\.txt"):
        check(h, pr)


def test_every_check_costs_its_base_cost_even_between_empty_texts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = MergedHistory(tmp_path)
    base = rows(1, 60)
    h.push({"f.txt": text(base)})
    kept = [*base[:1], *base[4:11], *base[14:21], *base[24:31], *base[34:]]  # four blocks of 3 go
    pr = h.push({"f.txt": text(kept)})
    # 30 separate one-line additions: 4 x 30 pairs of hunks, and the first check of each pair
    # compares two empty texts.
    h.push({"f.txt": text(*([row, f"extra {n}"] for n, row in enumerate(kept[:30])), kept[30:])})
    monkeypatch.setattr(partial_reverts, "COMPARISON_BUDGET", 50 * partial_reverts.CHECK_COST)
    built, _ = record_checks(monkeypatch)
    with pytest.raises(partial_reverts.Unfinished, match=r"cut short in f\.txt"):
        check(h, pr)
    assert 0 < len(built) <= 50


@pytest.mark.parametrize(("restored", "regenerated"), [("a.txt", "z.lock"), ("z.txt", "a.lock")])
def test_a_restored_file_counts_when_the_budget_runs_out_in_another_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restored: str, regenerated: str
) -> None:
    h = MergedHistory(tmp_path)
    h.push({restored: "old\n", regenerated: lock(0, 12)})
    pr = h.push({restored: "new\n", regenerated: lock(1, 12)})
    undo = h.push({restored: "old\n"})
    for version in range(2, 5):
        h.push({regenerated: lock(version, 12)})
    monkeypatch.setattr(partial_reverts, "COMPARISON_BUDGET", BUDGET)
    assert check(h, pr) == Undoing(undo, False, (restored,), ())


def test_a_section_found_before_the_budget_runs_out_still_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": doc(rows(5, 8), rows(20, 23)), "z.lock": lock(0, 12)})
    pr = h.push({"a.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta")), "z.lock": lock(1, 12)})
    undo = h.push({"a.txt": doc(rows(5, 8), rows(20, 23, "beta"))})
    for version in range(2, 5):
        h.push({"z.lock": lock(version, 12)})
    monkeypatch.setattr(partial_reverts, "COMPARISON_BUDGET", BUDGET)
    assert check(h, pr) == Undoing(undo, False, (), ("a.txt:5-8",))


@pytest.mark.parametrize(
    "change",
    [
        (),
        ("--add", "remote.origin.promisor", "false"),
        ("--unset-all", "remote.origin.promisor"),
        ("remote.origin.promisor", "false"),
    ],
    ids=[
        "the clone's promisor key",
        "a false value added after it",
        "no promisor key, the filter key kept",
        "a false promisor key, the filter key kept",
    ],
)
def test_a_partial_clone_is_not_read_for_file_contents(
    tmp_path: Path, change: tuple[str, ...]
) -> None:
    source = MergedHistory(tmp_path / "source")
    git(source.path, "config", "uploadpack.allowFilter", "true")
    source.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = source.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    tip = source.push({"f.txt": doc(rows(5, 8), rows(20, 23, "beta"))})
    clone = tmp_path / "clone"
    git(
        tmp_path,
        "clone",
        "-q",
        "--no-local",
        "--filter=blob:none",
        f"file://{source.path}",
        str(clone),
    )
    if change:
        # git treats a remote as a promisor when any value of its promisor key is true, and also
        # when it has a partial clone filter, whatever its promisor key says.
        git(clone, "config", *change)
    objects = git(clone, "count-objects", "-v")
    with pytest.raises(partial_reverts.Unfinished) as stopped:
        undoing(Repo.discover(clone), pr, tip)
    assert str(stopped.value) == (
        "this clone is partial, and reading file contents would fetch them: "
        "clone again without --filter and rerun"
    )
    assert git(clone, "count-objects", "-v") == objects


@pytest.mark.parametrize(
    "damage",
    [lambda out: out.replace(" M\0", " M x\0"), lambda out: out.replace("\0a.txt\0", "\0")],
    ids=["an extra column", "a path missing"],
)
def test_a_change_list_that_git_garbles_is_a_guided_error(
    tmp_path: Path, damage: Callable[[str], str]
) -> None:
    h = MergedHistory(tmp_path)
    h.push({"a.txt": "old\n"})
    pr = h.push({"a.txt": "new\n"})
    h.push({"a.txt": "old\n"})
    repo = Repo.discover(h.path)
    with pytest.raises(MetricsError, match="cannot read the files that git log --raw lists"):
        undoing(
            GarbledRepo(repo.root, repo.git_common_dir, damage),
            pr,
            git(h.path, "rev-parse", "HEAD"),
        )


def test_a_textconv_driver_does_not_hide_a_section(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path / "repo")
    hide = tmp_path / "hide"
    hide.write_text("#!/bin/sh\necho hidden\n")
    hide.chmod(0o755)
    attributes = tmp_path / "attributes"
    attributes.write_text("*.txt diff=hide\n")
    git(h.path, "config", "diff.hide.textconv", str(hide))
    git(h.path, "config", "core.attributesFile", str(attributes))
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    undo = h.push({"f.txt": doc(rows(5, 8), rows(20, 23, "beta"))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


@pytest.mark.parametrize(
    ("name", "value"), [("core.attributesFile", "{attributes}"), ("core.bigFileThreshold", "100")]
)
def test_a_setting_that_makes_git_read_a_file_as_binary_does_not_hide_a_section(
    tmp_path: Path, name: str, value: str
) -> None:
    h = MergedHistory(tmp_path / "repo")
    (tmp_path / "attributes").write_text("*.txt -diff\n")
    git(h.path, "config", name, value.format(attributes=tmp_path / "attributes"))
    h.push({"f.txt": doc(rows(5, 8), rows(20, 23))})
    pr = h.push({"f.txt": doc(rows(5, 8, "alpha"), rows(20, 23, "beta"))})
    undo = h.push({"f.txt": doc(rows(5, 8), rows(20, 23, "beta"))})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:5-8",))


def test_the_diff_algorithm_does_not_change_how_a_later_commit_is_read(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    git(h.path, "config", "diff.algorithm", "patience")
    original = ["z", "b", "a", "y", "}", "x", ""]
    h.push({"f.txt": text(original)})
    pr = h.push({"f.txt": text(["}", "x", "", "", "z", "a"])})
    # Myers reads the later commit as one block that brings back `z b a y`; patience reads it as
    # three insertions, none of which the PR's deletion matches.
    undo = h.push({"f.txt": text(original, ["tail"])})
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:1-1",))


def test_the_indent_heuristic_setting_does_not_move_a_section(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    git(h.path, "config", "diff.indentHeuristic", "false")
    original = ["    {", "    }", "if x:", "    c()", "  e", "{", "if x:", "}"]
    h.push({"f.txt": text(original)})
    pr = h.push({"f.txt": text(["    }", "if x:", "}"])})
    undo = h.push({"f.txt": text(original, ["tail"])})
    # `if x:` borders the deleted lines on both sides, so git may place the deletion one line
    # lower; its indent heuristic puts it first.
    assert check(h, pr) == Undoing(undo, False, (), ("f.txt:1-1",))


def test_a_submodule_pointer_restored_is_found_whatever_ignoresubmodules_says(
    tmp_path: Path,
) -> None:
    h = MergedHistory(tmp_path)

    def point_at(sha: str) -> str:
        git(h.path, "update-index", "--add", "--cacheinfo", f"160000,{sha},vendor/lib")
        git(h.path, "commit", "-q", "-m", "move the pointer")
        return git(h.path, "rev-parse", "HEAD")

    point_at("1" * 40)
    pr = point_at("2" * 40)
    undo = point_at("1" * 40)
    git(h.path, "config", "diff.ignoreSubmodules", "all")  # also hides a staged pointer from commit
    assert check(h, pr) == Undoing(undo, True, ("vendor/lib",), ())


def test_a_mode_change_is_not_restored_when_only_the_content_returns(tmp_path: Path) -> None:
    h = MergedHistory(tmp_path)
    h.push({"run.sh": "echo one\n", "keep.txt": "old\n"})
    (h.path / "run.sh").chmod(0o755)
    pr = h.push({"keep.txt": "new\n"})
    h.push({"run.sh": "echo two\n"})
    h.push({"run.sh": "echo one\n"})
    assert check(h, pr) is None
