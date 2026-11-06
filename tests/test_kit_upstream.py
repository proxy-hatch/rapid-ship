"""Offline: the Kit's forked skills against pristine upstream fixtures."""

import difflib
import hashlib
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

REPOSITORY = Path(__file__).resolve().parents[1]
BEGIN_MARKER = "<!-- rapid-ship: begin -->"
END_MARKER = "<!-- rapid-ship: end -->"


def blob_sha(data: bytes) -> str:
    """Git's SHA-1 of b"blob <len>\\0" + data."""
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def restore_name(text: str, upstream_name: str) -> str:
    """Swap the front matter's name: rs-<upstream_name> back."""
    expected = f"name: rs-{upstream_name}"
    if expected not in text:
        raise ValueError(f"expected {expected!r}")
    return text.replace(expected, f"name: {upstream_name}", 1)


def _marked_sections(fork_lines: list[str]) -> tuple[list[tuple[int, int]], list[int]]:
    sections: list[tuple[int, int]] = []
    marker_errors: list[int] = []
    open_begin: int | None = None

    for line_idx, line in enumerate(fork_lines, start=1):
        stripped = line.strip()
        if stripped == BEGIN_MARKER:
            if open_begin is not None:
                marker_errors.append(line_idx)
            else:
                open_begin = line_idx
        elif stripped == END_MARKER:
            if open_begin is None:
                marker_errors.append(line_idx)
            else:
                sections.append((open_begin, line_idx))
                open_begin = None

    if open_begin is not None:
        marker_errors.append(open_begin)

    return sections, marker_errors


def unmarked_changes(upstream: str, fork: str) -> list[int]:
    """1-based fork lines of changes outside marked sections and unpaired markers."""
    upstream_lines = upstream.splitlines(keepends=True)
    fork_lines = fork.splitlines(keepends=True)
    sections, marker_errors = _marked_sections(fork_lines)
    changes = list(marker_errors)

    matcher = difflib.SequenceMatcher(None, upstream_lines, fork_lines, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            if not any(start <= j1 and (j1 + 1) <= end for start, end in sections):
                changes.append(j1 if j1 > 0 else 1)
        else:
            for fork_line_idx in range(j1 + 1, j2 + 1):
                if not any(start <= fork_line_idx <= end for start, end in sections):
                    changes.append(fork_line_idx)

    return sorted(set(changes))


def load_upstream_lock() -> dict[str, Any]:
    path = REPOSITORY / "rapid_ship/upstream.lock"
    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_the_lock_names_one_upstream_commit() -> None:
    lock = load_upstream_lock()
    files = lock.get("file", [])
    assert files, "expected at least one [[file]] entry in upstream.lock"
    for entry in files:
        assert entry["repository"] == "mattpocock/skills"
        assert entry["commit"] == "49dd158d1076134a641b33efb035946536778336"
        assert entry["status"] in ("verbatim", "patched")


def test_each_fixture_is_the_pristine_upstream_file() -> None:
    lock = load_upstream_lock()
    fixtures = REPOSITORY / "tests/fixtures/upstream"
    for entry in lock["file"]:
        fixture_path = fixtures / entry["repository"] / entry["commit"] / entry["upstream"]
        assert fixture_path.is_file(), f"missing fixture: {fixture_path}"
        assert blob_sha(fixture_path.read_bytes()) == entry["blob"]


def test_verbatim_files_equal_their_upstream_file() -> None:
    lock = load_upstream_lock()
    common = REPOSITORY / "rapid_ship/templates/common"
    for entry in lock["file"]:
        if entry["status"] != "verbatim":
            continue
        fork_path = common / entry["path"]
        if fork_path.name == "SKILL.md":
            upstream_name = PurePosixPath(entry["upstream"]).parent.name
            fork_text = fork_path.read_text(encoding="utf-8")
            restored = restore_name(fork_text, upstream_name).encode("utf-8")
            assert blob_sha(restored) == entry["blob"]
        else:
            assert blob_sha(fork_path.read_bytes()) == entry["blob"]


def test_patched_files_differ_only_inside_marked_sections() -> None:
    lock = load_upstream_lock()
    common = REPOSITORY / "rapid_ship/templates/common"
    fixtures = REPOSITORY / "tests/fixtures/upstream"
    for entry in lock["file"]:
        if entry["status"] != "patched":
            continue
        fork_path = common / entry["path"]
        fixture_path = fixtures / entry["repository"] / entry["commit"] / entry["upstream"]
        fork_text = fork_path.read_text(encoding="utf-8")
        fixture_text = fixture_path.read_text(encoding="utf-8")
        upstream_name = PurePosixPath(entry["upstream"]).parent.name
        restored = (
            restore_name(fork_text, upstream_name) if fork_path.name == "SKILL.md" else fork_text
        )
        assert unmarked_changes(fixture_text, restored) == []
        assert BEGIN_MARKER in fork_text
        assert blob_sha(fork_path.read_bytes()) != entry["blob"]


def test_every_file_of_a_forked_skill_is_in_the_lock() -> None:
    lock = load_upstream_lock()
    common = REPOSITORY / "rapid_ship/templates/common"
    skill_dirs: set[str] = set()
    for entry in lock["file"]:
        parts = PurePosixPath(entry["path"]).parts
        if len(parts) >= 3 and parts[:2] == (".agents", "skills"):
            skill_dirs.add(f"{parts[0]}/{parts[1]}/{parts[2]}")

    for skill_rel in sorted(skill_dirs):
        dir_path = common / skill_rel
        assert dir_path.is_dir(), f"missing template skill directory: {dir_path}"
        template_files = {
            p.relative_to(common).as_posix() for p in dir_path.rglob("*") if p.is_file()
        }
        lock_files = {
            entry["path"] for entry in lock["file"] if entry["path"].startswith(f"{skill_rel}/")
        }
        assert template_files == lock_files


@pytest.mark.parametrize(
    ("upstream", "fork", "expected"),
    [
        (
            "line 1\n<!-- rapid-ship: begin -->\np\n<!-- rapid-ship: end -->\ntail\n",
            "line 1 edited\n<!-- rapid-ship: begin -->\np\n<!-- rapid-ship: end -->\ntail\n",
            [1],
        ),
        (
            "line 1\n<!-- rapid-ship: begin -->\noriginal\n<!-- rapid-ship: end -->\ntail\n",
            "line 1\n<!-- rapid-ship: begin -->\nedited\n<!-- rapid-ship: end -->\ntail\n",
            [],
        ),
        (
            "line 1\n<!-- rapid-ship: begin -->\nkeep\nremove\n<!-- rapid-ship: end -->\ntail\n",
            "line 1\n<!-- rapid-ship: begin -->\nkeep\n<!-- rapid-ship: end -->\ntail\n",
            [],
        ),
        (
            "line 1\nremove\n<!-- rapid-ship: begin -->\np\n<!-- rapid-ship: end -->\ntail\n",
            "line 1\n<!-- rapid-ship: begin -->\np\n<!-- rapid-ship: end -->\ntail\n",
            [1],
        ),
        (
            "line 1\nline 2\n",
            "line 1\n<!-- rapid-ship: begin -->\nline 2\n",
            [2],
        ),
        (
            "line 1\nline 2\n",
            "line 1\n<!-- rapid-ship: end -->\nline 2\n",
            [2],
        ),
    ],
)
def test_unmarked_changes_reports_only_changes_outside_a_section(
    upstream: str, fork: str, expected: list[int]
) -> None:
    assert unmarked_changes(upstream, fork) == expected


def test_restore_name_rejects_a_name_without_the_rs_prefix() -> None:
    with pytest.raises(ValueError, match="rs-tdd"):
        restore_name("---\nname: tdd\n---\n", "tdd")
