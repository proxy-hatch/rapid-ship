"""The map step's skill checks: each skill directory under .agents/skills has a tracked
SKILL.md, a regular file, with its name and a description, and a relative symlink in
.claude/skills that points to it.

They live apart from map.py, which runs them, so map.py stays under the file-size cap.
"""

from __future__ import annotations

from pathlib import Path

from devctl.check.markdown import front_matter_of, text_value
from devctl.check.tracked import TrackedFiles

SKILLS = ".agents/skills"


def skill_alias_errors(tracked: TrackedFiles) -> list[str]:
    """Each skill has a SKILL.md and a symlink in .claude/skills."""
    present = set(tracked.files)
    canonical = _skill_names(tracked, ".agents/skills")
    aliases = _skill_names(tracked, ".claude/skills")
    errors = [_canonical_error(tracked, name) for name in sorted(canonical)]
    errors += [_alias_error(tracked.root, present, name) for name in sorted(canonical)]
    errors += [
        f".claude/skills/{name}: no matching .agents/skills/{name} in Git; "
        "remove the alias or add the skill"
        for name in sorted(aliases - canonical)
    ]
    errors += [
        f"{path}: only skill links belong in .claude/skills; remove it"
        for path in _stray_files(tracked)
    ]
    return [error for error in errors if error]


def _skill_names(tracked: TrackedFiles, surface: str) -> set[str]:
    names: set[str] = set()
    for path in tracked.files:
        if path.startswith(f"{surface}/"):
            name = path[len(surface) + 1 :].split("/", 1)[0]
            entry = tracked.root / surface / name
            if entry.is_symlink() or entry.is_dir():
                names.add(name)
    return names


def _stray_files(tracked: TrackedFiles) -> list[str]:
    """Files directly under .claude/skills, such as a guide; only skill links belong there."""
    names = {path.split("/")[2] for path in tracked.files if path.startswith(".claude/skills/")}
    entries = {name: tracked.root / ".claude/skills" / name for name in names}
    return sorted(
        f".claude/skills/{name}"
        for name, entry in entries.items()
        if not entry.is_symlink() and not entry.is_dir()
    )


def _canonical_error(tracked: TrackedFiles, name: str) -> str | None:
    root = tracked.root
    entry = root / SKILLS / name
    if entry.is_symlink() and (
        entry.readlink().is_absolute() or not entry.resolve().is_relative_to(root.resolve())
    ):
        return f"{SKILLS}/{name}: make it a relative symlink inside the repository"
    skill_md = f"{SKILLS}/{name}/SKILL.md"
    if (root / skill_md).is_symlink() and _skill_md_tracked(tracked, name):
        return None
    if not (root / skill_md).is_file():
        return f"{SKILLS}/{name}: missing SKILL.md"
    if not tracked.holds(skill_md):
        return f"{skill_md}: {tracked.why_untracked(skill_md)}"
    return None


def _skill_md_tracked(tracked: TrackedFiles, name: str) -> bool:
    """Whether git tracks SKILL.md itself, resolving its directory but not its last component."""
    directory, real_root = (tracked.root / SKILLS / name).resolve(), tracked.root.resolve()
    return (
        directory.is_relative_to(real_root)
        and (directory.relative_to(real_root) / "SKILL.md").as_posix() in tracked.files
    )


def _alias_error(root: Path, present: set[str], name: str) -> str | None:
    relative = f".claude/skills/{name}"
    alias, canonical = root / relative, root / ".agents/skills" / name
    expected = f"../../.agents/skills/{name}"
    if relative in present and alias.is_symlink():
        resolved = alias.resolve()
        inside = resolved.is_relative_to(root.resolve())
        if not alias.readlink().is_absolute() and inside and resolved == canonical.resolve():
            return None
        return f"{relative}: make it a relative symlink to {expected}"
    if (
        alias.is_dir()
        and not alias.is_symlink()
        and any(p.startswith(f"{relative}/") for p in present)
    ):
        return (
            f"{relative}: a copy is not an alias; replace it with a relative symlink to {expected}"
        )
    return f"{relative}: add a relative symlink to {expected} and track it in Git"


def skill_errors(tracked: TrackedFiles) -> list[str]:
    """Each SKILL.md names its directory and has a description."""
    errors: list[str] = []
    for name in sorted(_skill_names(tracked, SKILLS)):
        path = f"{SKILLS}/{name}/SKILL.md"
        if not (tracked.root / path).is_file() or not tracked.holds(path):
            continue  # skill_alias_errors reports a missing or untracked SKILL.md
        data = front_matter_of(tracked.root, path, "name and description")
        if isinstance(data, str):
            errors.append(data)
            continue
        if data.get("name") != name:
            errors.append(f"{path}: name must be {name}, the directory name")
        if text_value(data, "description") is None:
            errors.append(f"{path}: description is missing or empty")
    return errors


def skill_file_errors(tracked: TrackedFiles) -> list[str]:
    """Each SKILL.md is a regular file, because Codex rejects a symlink.

    It judges the last path component only; a skill directory that is itself a symlink is
    skill_alias_errors' concern.
    """
    paths = (
        f"{SKILLS}/{name}/SKILL.md"
        for name in sorted(_skill_names(tracked, SKILLS))
        if _skill_md_tracked(tracked, name)
    )
    return [
        f"{path}: is a symlink; make it a regular file, because Codex rejects a symlinked SKILL.md"
        for path in paths
        if (tracked.root / path).is_symlink()
    ]
