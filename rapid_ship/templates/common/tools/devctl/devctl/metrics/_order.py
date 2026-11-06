"""devctl metrics: helper to discover table headers in source order."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class TableHeader:
    name: str
    is_array: bool


def _is_escaped(text: str, pos: int) -> bool:
    bs_count = 0
    k = pos - 1
    while k >= 0 and text[k] == "\\":
        bs_count += 1
        k -= 1
    return bs_count % 2 == 1


def _skip_multiline_basic(text: str, i: int, n: int) -> int:
    idx = i + 3
    while idx < n:
        if text.startswith('"""', idx) and not _is_escaped(text, idx):
            return idx + 3
        idx += 1
    return n


def _skip_multiline_literal(text: str, i: int, n: int) -> int:
    end_pos = text.find("'''", i + 3)
    return n if end_pos == -1 else end_pos + 3


def _skip_basic_str(text: str, i: int, n: int) -> int:
    idx = i + 1
    while idx < n and text[idx] != "\n":
        if text[idx] == '"' and not _is_escaped(text, idx):
            return idx + 1
        idx += 1
    return idx


def _skip_literal_str(text: str, i: int, n: int) -> int:
    idx = i + 1
    while idx < n and text[idx] != "\n":
        if text[idx] == "'":
            return idx + 1
        idx += 1
    return idx


def _skip_string(text: str, i: int, n: int) -> int | None:
    if text.startswith('"""', i):
        return _skip_multiline_basic(text, i, n)
    if text.startswith("'''", i):
        return _skip_multiline_literal(text, i, n)
    if text[i] == '"':
        return _skip_basic_str(text, i, n)
    if text[i] == "'":
        return _skip_literal_str(text, i, n)
    return None


def _parse_header(line: str) -> TableHeader | None:
    try:
        parsed = tomllib.loads(line)
    except tomllib.TOMLDecodeError:
        return None
    name = next(iter(parsed.keys()), None)
    if name is None:
        return None
    return TableHeader(name=name, is_array=line.startswith("[["))


def _handle_open_bracket(
    text: str, i: int, n: int, at_line_start: bool, inline_depth: int
) -> tuple[TableHeader | None, int, bool, int]:
    if at_line_start and inline_depth == 0:
        eol = text.find("\n", i)
        line_end = n if eol == -1 else eol
        header = _parse_header(text[i:line_end].strip())
        return header, line_end, True, inline_depth
    return None, i + 1, False, inline_depth + 1


def scan_table_headers(text: str) -> list[TableHeader]:
    headers: list[TableHeader] = []
    i = 0
    n = len(text)
    at_line_start = True
    inline_depth = 0

    while i < n:
        next_i = _skip_string(text, i, n)
        if next_i is not None:
            i = next_i
            at_line_start = False
            continue

        if text[i] == "#":
            eol = text.find("\n", i)
            i = n if eol == -1 else eol
        elif text[i] == "\n":
            at_line_start = True
            i += 1
        elif text[i] in " \t\r":
            i += 1
        elif text[i] == "[":
            header, i, at_line_start, inline_depth = _handle_open_bracket(
                text, i, n, at_line_start, inline_depth
            )
            if header is not None:
                headers.append(header)
        elif text[i] in ("]", "}"):
            inline_depth = max(0, inline_depth - 1)
            at_line_start = False
            i += 1
        elif text[i] == "{":
            inline_depth += 1
            at_line_start = False
            i += 1
        else:
            at_line_start = False
            i += 1

    return headers
