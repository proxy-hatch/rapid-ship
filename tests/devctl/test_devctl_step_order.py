"""The core steps, and their order, for each stack."""

from __future__ import annotations

from check_workspace import project_settings
from devctl.check import core_steps
from devctl.settings import ProjectStack

PYTHON = [
    "format",
    "lint",
    "map",
    "exceptions",
    "file-size",
    "kit",
    "types",
    "contracts",
    "dead-code",
    "tests",
    "audit",
    "secrets",
    "workflows",
    "diff",
    "evidence",
]


def test_each_stack_has_its_core_steps_in_order() -> None:
    python = core_steps(project_settings(stacks=(ProjectStack("python", "."),)))
    agnostic = core_steps(project_settings(stacks=(ProjectStack("agnostic", "."),)))

    assert [step.name for step in python] == PYTHON
    assert [step.name for step in agnostic] == [
        "map",
        "exceptions",
        "file-size",
        "kit",
        "secrets",
        "workflows",
        "diff",
        "evidence",
    ]
    assert [step.name for step in python if step.tier == "fast"] == PYTHON[:6]
