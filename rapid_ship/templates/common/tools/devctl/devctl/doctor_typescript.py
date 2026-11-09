"""Node toolchain and TypeScript guardrail floor inspection."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from devctl import jsonc, node
from devctl.doctor_items import Item, finished, run_installed
from devctl.settings import ProjectStack, under

TSCONFIG_FLOOR = (
    "strict",
    "noUncheckedIndexedAccess",
    "exactOptionalPropertyTypes",
    "noImplicitOverride",
    "noImplicitReturns",
    "noFallthroughCasesInSwitch",
    "verbatimModuleSyntax",
    "isolatedModules",
    "noEmit",
)
ESLINT_ERRORS = (
    "no-empty",
    "no-console",
    "@typescript-eslint/no-floating-promises",
    "@typescript-eslint/switch-exhaustiveness-check",
    "react-hooks/rules-of-hooks",
)
DEV_PACKAGES = (
    "@eslint/js",
    "@testing-library/react",
    "eslint",
    "eslint-plugin-react-hooks",
    "jsdom",
    "knip",
    "prettier",
    "typescript",
    "typescript-eslint",
    "vitest",
)


KNIP_FLOOR_KEYS: tuple[str, ...] = ("rules", "ignoreExportsUsedInFile")


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _options(value: object) -> Mapping[str, object]:
    return _mapping(value[1]) if isinstance(value, list) and len(value) > 1 else {}


def _complexity(value: object) -> bool:
    if not node.is_error(value) or not isinstance(value, list) or len(value) < 2:
        return False
    maximum = value[1]
    if isinstance(maximum, Mapping):
        maximum = maximum.get("max")
    return isinstance(maximum, (int, float)) and not isinstance(maximum, bool) and maximum <= 10


def floor_gaps(
    tsconfig: Mapping[str, object],
    eslint_config: Mapping[str, object],
    package: Mapping[str, object],
    knip: Mapping[str, object],
    has_lock: bool,
) -> list[str]:
    suffix = (
        f" (it extends {tsconfig['extends']}, which doctor does not read)"
        if "extends" in tsconfig
        else ""
    )
    compiler = _mapping(tsconfig.get("compilerOptions"))
    gaps = [
        f"tsconfig.json: compilerOptions.{key} is not true{suffix}"
        for key in TSCONFIG_FLOOR
        if compiler.get(key) is not True
    ]
    rules = _mapping(eslint_config.get("rules"))
    gaps.extend(
        f"eslint: {rule} is not an error"
        for rule in ESLINT_ERRORS
        if not node.is_error(rules.get(rule))
    )
    if not _complexity(rules.get("complexity")):
        gaps.append("eslint: complexity is not an error with a maximum of 10 or less")
    ban = rules.get("@typescript-eslint/ban-ts-comment")
    options = _options(ban)
    if not (
        node.is_error(ban)
        and options.get("ts-ignore") is True
        and options.get("ts-nocheck") is True
        and options.get("ts-expect-error") == "allow-with-description"
    ):
        gaps.append(
            "eslint: @typescript-eslint/ban-ts-comment does not ban @ts-ignore and @ts-nocheck "
            "and require a description on @ts-expect-error"
        )
    if not node.is_error(
        _mapping(eslint_config.get("linterOptions")).get("reportUnusedDisableDirectives")
    ):
        gaps.append("eslint: linterOptions.reportUnusedDisableDirectives is not error")
    missing = [
        name for name in DEV_PACKAGES if name not in _mapping(package.get("devDependencies"))
    ]
    if missing:
        gaps.append(f"npm: devDependencies lack {', '.join(missing)}")
    if not _mapping(package.get("engines")).get("node"):
        gaps.append("npm: engines.node is not set")
    if not has_lock:
        gaps.append("npm: package-lock.json is missing; run npm install and commit it")
    gaps.extend(
        f"knip: knip.jsonc sets {key}, which can switch a kind off"
        for key in KNIP_FLOOR_KEYS
        if key in knip
    )
    return gaps


def _read(path: Path) -> Mapping[str, object]:
    value = jsonc.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not an object")
    return value


def floor_item(root: Path, stack: ProjectStack, several: bool) -> Item:
    name = "TypeScript guardrail settings" + (f" ({stack.directory})" if several else "")
    directory = root / stack.directory
    values = []
    for filename in ("tsconfig.json", "package.json", "knip.jsonc"):
        try:
            values.append(_read(directory / filename))
        except (OSError, ValueError) as error:
            return Item(
                "guardrails", name, "unknown", f"{under(stack.directory, filename)}: {error}"
            )
    eslint = node.eslint_config(directory)
    if isinstance(eslint, str):
        return Item(
            "guardrails",
            name,
            "unknown",
            node.cannot_run("eslint", stack.directory, eslint, directory),
        )
    gaps = floor_gaps(
        values[0], eslint, values[1], values[2], (directory / "package-lock.json").is_file()
    )
    return Item(
        "guardrails",
        name,
        "missing" if gaps else "ok",
        "; ".join(gaps) or "meets the TypeScript guardrail floor",
    )


def _engine(root: Path, stack: ProjectStack) -> str:
    try:
        value = _mapping(_read(root / stack.directory / "package.json").get("engines")).get("node")
    except (OSError, ValueError):
        return ""
    return value if isinstance(value, str) else ""


def _version(text: str) -> tuple[int, int, int] | None:
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    return (int(match[1]), int(match[2] or 0), int(match[3] or 0)) if match else None


def _node_item(root: Path, stacks: Sequence[ProjectStack]) -> Item:
    result = run_installed("node", "--version")
    version = (
        _version(result.stdout) if result and finished(result) and result.returncode == 0 else None
    )
    details = []
    for stack in stacks:
        engine = _engine(root, stack)
        minimum = _version(engine)
        path = under(stack.directory, "package.json")
        if minimum is None:
            return Item("toolchain", "node", "missing", f"{path} sets no engines.node")
        if result is None:
            return Item(
                "toolchain", "node", "missing", f"node is not on PATH; install Node.js {minimum[0]}"
            )
        if version is None:
            return Item("toolchain", "node", "unknown", "node --version gave no readable version")
        found = ".".join(map(str, version))
        if version[0] != minimum[0] or version < minimum:
            needed = ".".join(map(str, minimum))
            return Item(
                "toolchain",
                "node",
                "missing",
                f"node v{found}, but {path} names {engine}; "
                f"install Node.js {minimum[0]}, {needed} or later",
            )
        details.append(f"node v{found}, which {path} names ({engine})")
    return Item("toolchain", "node", "ok", "; ".join(details))


def node_items(root: Path, stacks: Sequence[ProjectStack]) -> list[Item]:
    typescript = [stack for stack in stacks if stack.name == "typescript"]
    if not typescript:
        return []
    result = run_installed("npm", "--version")
    if result is None:
        npm = Item("toolchain", "npm", "missing", "npm is not on PATH; it comes with Node.js")
    elif not finished(result) or result.returncode or not _version(result.stdout):
        npm = Item("toolchain", "npm", "unknown", "npm --version gave no readable version")
    else:
        npm = Item("toolchain", "npm", "ok", result.stdout.strip())
    return [_node_item(root, typescript), npm]
