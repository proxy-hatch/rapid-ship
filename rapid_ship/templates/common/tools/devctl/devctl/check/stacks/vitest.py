"""Pure Vitest test identities and tautological assertion readers."""

from __future__ import annotations

import re

from devctl.check.stacks.vitest_tokens import Token, title, tokens

TEST_FILE = re.compile(r".*\.(test|spec)\.(ts|tsx|mts|cts|js|jsx|mjs|cjs)$")
SEPARATOR = " > "


def is_test_file(path: str) -> bool:
    return TEST_FILE.fullmatch(path) is not None


def _call(stream: list[Token], pairs: dict[int, int], index: int) -> tuple[int, int, bool] | None:
    position = index + 1
    each = False
    while position + 1 < len(stream) and stream[position].text == ".":
        each |= stream[position + 1].text == "each"
        position += 2
    if each and position < len(stream) and stream[position].text.startswith("`"):
        position += 1
    elif each and position in pairs and stream[position].text == "(":
        position = pairs[position] + 1
    if position not in pairs or stream[position].text != "(":
        return None
    return position, pairs[position], each


def test_identities(source: str) -> tuple[list[str], list[int]]:
    stream, pairs = tokens(source)
    names: list[str] = []
    unchecked: list[int] = []
    scopes: list[tuple[int, str | None]] = []
    for index, token in enumerate(stream):
        scopes = [(end, name) for end, name in scopes if end > index]
        if token.kind != "code" or token.text not in {"describe", "suite", "it", "test"}:
            continue
        if index and stream[index - 1].text == ".":
            continue
        call = _call(stream, pairs, index)
        if call is None:
            continue
        opened, end, each = call
        first = opened + 1
        name = title(stream[first]) if first < end and not each else None
        if first + 1 < end and stream[first + 1].text != ",":
            name = None
        if token.text in {"describe", "suite"}:
            scopes.append((end, name))
        elif name is None or any(parent is None for _, parent in scopes):
            unchecked.append(source.count("\n", 0, token.start) + 1)
        else:
            names.append(
                SEPARATOR.join([*(parent for _, parent in scopes if parent is not None), name])
            )
    return names, unchecked


def tautologies(source: str) -> list[tuple[int, str]]:
    stream, pairs = tokens(source)
    found: list[tuple[int, str]] = []
    for index, token in enumerate(stream):
        if (
            token.kind != "code"
            or token.text != "expect"
            or (index and stream[index - 1].text == ".")
        ):
            continue
        call = _call(stream, pairs, index)
        if call is None:
            continue
        opened, end, _ = call
        if end + 3 >= len(stream) or stream[end + 1].text != ".":
            continue
        matcher = stream[end + 2].text
        other = end + 3
        if stream[other].text != "(" or other not in pairs:
            continue
        close = pairs[other]
        left = source[stream[opened].end : stream[end].start]
        right = source[stream[other].end : stream[close].start]
        same = (
            matcher in {"toBe", "toEqual", "toStrictEqual"}
            and bool(left.strip())
            and re.sub(r"\s", "", left) == re.sub(r"\s", "", right)
        )
        truthy = matcher == "toBeTruthy" and left.strip() == "true" and not right.strip()
        if same or truthy:
            found.append(
                (source.count("\n", 0, token.start) + 1, source[token.start : stream[close].end])
            )
    return found
