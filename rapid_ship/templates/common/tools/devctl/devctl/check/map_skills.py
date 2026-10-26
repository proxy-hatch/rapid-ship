"""The map step's skill checks: each skill directory under .agents/skills has a tracked
SKILL.md, a regular file, with its name and a description, and a relative symlink in
.claude/skills that points to it.

They live apart from map.py, which runs them, so map.py stays under the file-size cap.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from devctl.check.markdown import front_matter_of, text_value

SKILLS = ".agents/skills"


def skill_alias_errors(root: Path, files: Sequence[str]) -> list[str]:
    """Each skill has a SKILL.md and a symlink in .claude/skills."""
    present = set(files)
    canonical = _skill_names(root, files, ".agents/skills")
    aliases = _skill_names(root, files, ".claude/skills")
    errors = [_canonical_error(root, present, name) for name in sorted(canonical)]
    errors += [_alias_error(root, present, name) for name in sorted(canonical)]
    errors += [
        f".claude/skills/{name}: no matching .agents/skills/{name} in Git; "
        "remove the alias or add the skill"
        for name in sorted(aliases - canonical)
    ]
    errors += [
        f"{path}: only skill links belong in .claude/skills; remove it"
        for path in _stray_files(root, files)
    ]
    return [error for error in errors if error]


def _skill_names(root: Path, files: Sequence[str], surface: str) -> set[str]:
    names: set[str] = set()
    for path in files:
        if path.startswith(f"{surface}/"):
            name = path[len(surface) + 1 :].split("/", 1)[0]
            entry = root / surface / name
            if entry.is_symlink() or entry.is_dir():
                names.add(name)
    return names


def _stray_files(root: Path, files: Sequence[str]) -> list[str]:
    """Files directly under .claude/skills, such as a guide; only skill links belong there."""
    names = {path.split("/")[2] for path in files if path.startswith(".claude/skills/")}
    entries = {name: root / ".claude/skills" / name for name in names}
    return sorted(
        f".claude/skills/{name}"
        for name, entry in entries.items()
        if not entry.is_symlink() and not entry.is_dir()
    )


def _canonical_error(root: Path, present: set[str], name: str) -> str | None:
    entry = root / ".agents/skills" / name
    if entry.is_symlink() and (
        entry.readlink().is_absolute() or not entry.resolve().is_relative_to(root.resolve())
    ):
        return f".agents/skills/{name}: make it a relative symlink inside the repository"
    if not (entry / "SKILL.md").is_file():
        return f".agents/skills/{name}: missing SKILL.md"
    if not _skill_md_tracked(root, present, name):
        return f".agents/skills/{name}/SKILL.md: not tracked; stage it with git add"
    return None


def _skill_md_tracked(root: Path, present: set[str], name: str) -> bool:
    """Whether `present` holds the skill's SKILL.md. A skill directory can be a symlink, as into
    a package; git records the symlink and not what it holds, so SKILL.md is looked up at the
    resolved path."""
    directory, real_root = (root / SKILLS / name).resolve(), root.resolve()
    return (
        directory.is_relative_to(real_root)
        and f"{directory.relative_to(real_root).as_posix()}/SKILL.md" in present
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


def skill_errors(root: Path, files: Sequence[str]) -> list[str]:
    """Each SKILL.md names its directory and has a description."""
    present = set(files)
    errors: list[str] = []
    for name in sorted(_skill_names(root, files, SKILLS)):
        path = f"{SKILLS}/{name}/SKILL.md"
        if not (root / path).is_file() or not _skill_md_tracked(root, present, name):
            continue  # skill_alias_errors reports a missing or untracked SKILL.md
        data = front_matter_of(root, path, "name and description")
        if isinstance(data, str):
            errors.append(data)
            continue
        if data.get("name") != name:
            errors.append(f"{path}: name must be {name}, the directory name")
        if text_value(data, "description") is None:
            errors.append(f"{path}: description is missing or empty")
    return errors


def skill_file_errors(root: Path, files: Sequence[str]) -> list[str]:
    """Each SKILL.md is a regular file, because Codex rejects a symlink.

    It judges the last path component only; a skill directory that is itself a symlink is
    skill_alias_errors' concern.
    """
    present = set(files)
    paths = (
        f"{SKILLS}/{name}/SKILL.md"
        for name in sorted(_skill_names(root, files, SKILLS))
        if _skill_md_tracked(root, present, name)
    )
    return [
        f"{path}: is a symlink; make it a regular file, because Codex rejects a symlinked SKILL.md"
        for path in paths
        if (root / path).is_symlink()
    ]
