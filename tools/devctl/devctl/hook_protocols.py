"""The types devctl hook's rules share: a Harness's tool call, the hook's answer, its settings.

hook.py and merge_guard.py both use them, so they live here and neither imports the other's
types. Each Harness's own event and answer format joins them here once it has Kit wiring.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# None: no decision. The hook only denies or asks; it never allows (Spec 1 section 4).
Decision = Literal["deny", "ask"] | None


@dataclass(frozen=True)
class ToolCall:
    """One Harness's pre-tool event, normalised."""

    shell: str | None  # the command line of a shell tool
    edits: tuple[Path, ...]  # the absolute, normalised paths a file-edit tool writes
    cwd: Path  # the event's working directory


@dataclass(frozen=True)
class HookSettings:
    """What G5, G7, G8 and the merge guard read from the repository."""

    agent_identity: bool
    protected: tuple[str, ...]  # Protected-set patterns; empty without a CODEOWNERS file
    repository: str | None  # [github] repository
    reviewer_app_slug: str | None  # [github] reviewer_app_slug when Agent identity is on, else None
