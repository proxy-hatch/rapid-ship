"""Pure line suppression readers and located JSONC allowlist items."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import PurePosixPath

from devctl import jsonc
from devctl.check.stacks.python_dead_code import AllowlistItem

SCRIPT_EXTENSIONS = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
KNIP_ALLOWLIST_KEYS = (
    "ignore",
    "ignoreFiles",
    "ignoreBinaries",
    "ignoreDependencies",
    "ignoreMembers",
    "ignoreUnresolved",
    "ignoreIssues",
    "tags",
)
KNIP_SETTINGS = "knip.jsonc"
OTHER_KNIP_SETTINGS = (
    "knip.json",
    ".knip.json",
    ".knip.jsonc",
    "knip.ts",
    "knip.config.ts",
    "knip.js",
    "knip.config.js",
)
_DISABLE = re.compile(r"\beslint-disable(?:-next-line|-line)?\b([^\r\n]*?)(?:\*/|$)")
_INLINE = re.compile(r"/\*\s*eslint\s+(.+?)\*/")
_RULE = re.compile(r"""(?:^|,)\s*["']?([@\w/-]+)["']?\s*:""")
_CALL = re.compile(r"\b(?:test|it|describe|suite|bench)((?:\.\w+)*)\s*\(")
_JSON_TOKEN = re.compile(
    r'"(?:[^"\\]|\\.)*"|//[^\r\n]*|/\*[\s\S]*?\*/|true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[^\s]'
)


def _inline_names(configuration: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    for token in re.finditer(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[{}\[\],]', configuration):
        text = token[0]
        if text in {"{", "["}:
            depth += 1
        elif text in {"}", "]"}:
            depth -= 1
        elif text == "," and depth == 0:
            parts.append(configuration[start : token.start()])
            start = token.end()
    parts.append(configuration[start:])
    return sorted({match[1] for part in parts if (match := _RULE.match(part))})


def line_rules(path: str, line: str) -> list[str]:
    rules = ["prettier-ignore"] if "prettier-ignore" in line else []
    if PurePosixPath(path).suffix not in SCRIPT_EXTENSIONS:
        return rules
    for match in _DISABLE.finditer(line):
        names = match[1].split(" -- ", 1)[0].strip()
        rules.append(
            "eslint:" + ",".join(sorted(set(re.split(r"[\s,]+", names)))) if names else "eslint"
        )
    for match in _INLINE.finditer(line):
        names = _inline_names(match[1])
        if names:
            rules.append("eslint:" + ",".join(names))
    if "@ts-expect-error" in line:
        rules.append("ts-expect-error")
    if any(m[1] != "stop" for m in re.finditer(r"\b(?:istanbul|c8|v8) ignore (\w+)", line)):
        rules.append("no-cover")
    for call in _CALL.finditer(line):
        rules.extend(
            word
            for word in call[1].split(".")
            if word in {"skip", "skipIf", "runIf", "todo", "fails"}
        )
        rules.extend(
            m[1]
            for m in re.finditer(r"\b(skip|todo|fails)\s*:\s*(?!false\b)\S", line[call.end() :])
        )
    rules.extend(f"knip:{m[0]}" for m in re.finditer(r"@(public|beta)\b", line))
    return list(dict.fromkeys(rules))


def _expected(data: object) -> list[tuple[str, str]]:
    if not isinstance(data, dict):
        return []
    items: list[tuple[str, str]] = []
    for key in KNIP_ALLOWLIST_KEYS:
        value = data.get(key)
        if (key == "ignoreIssues" and isinstance(value, dict)) or isinstance(value, list):
            items.extend((key, item) for item in value if isinstance(item, str))
    return items


def _nested(data: object, path: tuple[str, ...] = ()) -> list[str]:
    errors: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if path and key in KNIP_ALLOWLIST_KEYS:
                errors.append(".".join((*path, key)))
            errors.extend(_nested(value, (*path, key)))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            errors.extend(_nested(value, (*path, str(index))))
    return errors


def _located(text: str) -> list[tuple[int, str, str]]:
    """Locate JSON strings by container path, excluding strings inside comments."""
    tokens = [
        (m[0], text.count("\n", 0, m.start()) + 1)
        for m in _JSON_TOKEN.finditer(text)
        if not m[0].startswith(("//", "/*"))
    ]
    found: list[tuple[int, str, str]] = []
    position = 0

    def value(path: tuple[str, ...]) -> None:
        nonlocal position
        lexeme, line = tokens[position]
        position += 1
        if lexeme == "{":
            while tokens[position][0] != "}":
                if tokens[position][0] == ",":
                    position += 1
                    continue
                name, number = tokens[position]
                key = str(json.loads(name))
                position += 2  # key and colon
                if path == ("ignoreIssues",):
                    found.append((number, path[0], key))
                value((*path, key))
            position += 1
        elif lexeme == "[":
            while tokens[position][0] != "]":
                if tokens[position][0] == ",":
                    position += 1
                else:
                    value((*path, "[]"))
            position += 1
        elif lexeme.startswith('"') and path in {(key, "[]") for key in KNIP_ALLOWLIST_KEYS}:
            found.append((line, path[0], str(json.loads(lexeme))))

    value(())
    return found


def knip_allowlist(text: str, path: str) -> tuple[list[AllowlistItem], list[str]]:
    """Return located items and policy errors; invalid JSONC raises JSONDecodeError."""
    data = jsonc.loads(text)
    expected = Counter(_expected(data))
    found = _located(text)
    items = [AllowlistItem(line, f"knip.{key}:{item}") for line, key, item in found]
    errors = [
        f"{path}: {key} sets an allowlist below the top level; devctl reads knip's "
        "allowlists only at the top level of knip.jsonc"
        for key in _nested(data)
    ]
    for (line, key), count in Counter((line, key) for line, key, _ in found).items():
        if count > 1:
            errors.append(
                f"{path}:{line}: knip.{key} holds {count} items on one line; write each "
                "alone on its own line, with its own marker"
            )
    expected.subtract((key, item) for _, key, item in found)
    for (key, item), count in expected.items():
        errors.extend(
            f"{path}: knip.{key} lists '{item}' on no line devctl can read; write it "
            "alone on its own line"
            for _ in range(max(0, count))
        )
    return items, errors
