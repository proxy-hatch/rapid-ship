"""Offline: kit_summary against scratch directories and hand-written locks. No git, no network."""

import hashlib
import json
from pathlib import Path

import pytest

from devctl.check.kit import KitLockError, kit_summary


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def write_lock(root: Path, *entries: dict[str, str], version: str = "0.3.1") -> None:
    lines = [f'kit_version = "{version}"', 'stack = "python"', ""]
    for entry in entries:
        lines.append("[[file]]")
        lines += [f"{key} = {json.dumps(value)}" for key, value in entry.items()]
        lines.append("")
    (root / ".rapid-ship").mkdir()
    (root / ".rapid-ship/kit.lock").write_text("\n".join(lines))


def managed(path: str, text: str) -> dict[str, str]:
    return {"path": path, "kind": "managed", "sha256": sha(text)}


def test_each_managed_file_is_unchanged_modified_or_missing(tmp_path: Path) -> None:
    (tmp_path / "same.txt").write_text("same")
    (tmp_path / "edited.txt").write_text("edited by the project")
    write_lock(
        tmp_path,
        managed("gone.txt", "gone"),
        managed("same.txt", "same"),
        managed("edited.txt", "the template's text"),
    )
    summary = kit_summary(tmp_path, ())
    assert summary.kit_version == "0.3.1"
    assert summary.unchanged == ("same.txt",)
    assert summary.modified == ("edited.txt",)
    assert summary.missing == ("gone.txt",)
    assert summary.excluded == ()


def test_a_symlink_or_a_directory_in_place_of_a_file_is_missing(tmp_path: Path) -> None:
    (tmp_path / "real.txt").write_text("text")
    (tmp_path / "alias.txt").symlink_to("real.txt")
    (tmp_path / "folder.txt").mkdir()
    write_lock(tmp_path, managed("alias.txt", "text"), managed("folder.txt", "text"))
    assert kit_summary(tmp_path, ()).missing == ("alias.txt", "folder.txt")


def test_a_file_that_cannot_be_read_differs_from_the_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "locked.txt").write_text("text")
    write_lock(tmp_path, managed("locked.txt", "text"))

    def refuse(self: Path) -> bytes:
        raise PermissionError(13, "Permission denied", str(self))

    monkeypatch.setattr(Path, "read_bytes", refuse)
    assert kit_summary(tmp_path, ()).modified == ("locked.txt",)


def test_a_managed_link_is_unchanged_only_when_it_points_where_the_lock_says(
    tmp_path: Path,
) -> None:
    (tmp_path / "links").mkdir()
    (tmp_path / "links/right").symlink_to("../target")
    (tmp_path / "links/wrong").symlink_to("../elsewhere")
    (tmp_path / "links/plain").write_text("a file where a link belongs")
    link = {"kind": "managed", "link": "../target"}
    write_lock(
        tmp_path,
        {"path": "links/right", **link},
        {"path": "links/wrong", **link},
        {"path": "links/plain", **link},
        {"path": "links/absent", **link},
    )
    summary = kit_summary(tmp_path, ())
    assert summary.unchanged == ("links/right",)
    assert summary.modified == ("links/wrong",)
    assert summary.missing == ("links/plain", "links/absent")


def test_seeded_entries_and_the_locks_own_entry_are_not_compared(tmp_path: Path) -> None:
    write_lock(
        tmp_path,
        {"path": "AGENTS.md", "kind": "seeded", "template_sha256": sha("template")},
        managed(".rapid-ship/kit.lock", "lock"),
        managed("kept.txt", "kept"),
    )
    (tmp_path / "kept.txt").write_text("kept")
    summary = kit_summary(tmp_path, ())
    assert (summary.unchanged, summary.modified, summary.missing) == (("kept.txt",), (), ())


def test_excluded_paths_are_counted_without_a_look_at_the_disk(tmp_path: Path) -> None:
    (tmp_path / ".agents/skills/rs-tdd").mkdir(parents=True)
    (tmp_path / ".agents/skills/rs-tdd/SKILL.md").write_text("ours")
    write_lock(
        tmp_path,
        managed(".agents/skills/rs-tdd/SKILL.md", "theirs"),
        managed(".agents/skills/rs-tdd/extra.md", "absent"),
        {"path": ".claude/skills/rs-tdd", "kind": "managed", "link": "../../.agents/skills/rs-tdd"},
        managed(".agents/skills/rs-tdd-old/SKILL.md", "other skill"),
    )
    summary = kit_summary(tmp_path, (".agents/skills/rs-tdd",))
    assert summary.excluded == (
        ".agents/skills/rs-tdd/SKILL.md",
        ".agents/skills/rs-tdd/extra.md",
        ".claude/skills/rs-tdd",
    )
    assert summary.missing == (".agents/skills/rs-tdd-old/SKILL.md",)  # not below the directory


@pytest.mark.parametrize("content", [None, "not toml [", 'kit_version = 1\nstack = "python"\n'])
def test_an_unreadable_lock_raises_the_kit_lock_error(tmp_path: Path, content: str | None) -> None:
    if content is not None:
        (tmp_path / ".rapid-ship").mkdir()
        (tmp_path / ".rapid-ship/kit.lock").write_text(content)
    with pytest.raises(KitLockError, match=r"\.rapid-ship/kit\.lock"):
        kit_summary(tmp_path, ())
