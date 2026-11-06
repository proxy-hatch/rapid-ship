"""devctl metrics: source identities and diagnostic ordering."""

from __future__ import annotations

import tomllib

type SourcePath = tuple[str | int, ...]


class Problems(list[str]):
    """Collect each diagnostic once, then order by its value's source identity."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.positions = source_positions(text)
        self.ranks: list[float] = []
        self.rank = 0.0

    def at(self, path: SourcePath, *, missing: bool = False) -> None:
        descendants = [v for k, v in self.positions.items() if k[: len(path)] == path]
        if missing and descendants:
            self.rank = max(descendants) + 0.5
            return
        while path not in self.positions and path:
            path = path[:-1]
        self.rank = self.positions.get(path, 0)

    def append(self, problem: str) -> None:
        super().append(problem)
        self.ranks.append(self.rank)

    def ordered(self) -> tuple[str, ...]:
        return tuple(
            p for _, p in sorted(zip(self.ranks, self, strict=True), key=lambda pair: pair[0])
        )


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
    if text.startswith(('"""', "'" * 3), i):
        end = (_skip_multiline_basic if text[i] == '"' else _skip_multiline_literal)(text, i, n)
        # TOML permits one or two quote characters before a multiline ending.
        while end < n and text[end] == text[i]:
            end += 1
        return end
    if text[i] == '"':
        return _skip_basic_str(text, i, n)
    if text[i] == "'":
        return _skip_literal_str(text, i, n)
    return None


def _key_path(text: str) -> tuple[str, ...]:
    value = tomllib.loads(text)
    path: list[str] = []
    while isinstance(value, dict) and value:
        key = next(iter(value))
        path.append(key)
        value = value[key]
        if isinstance(value, list):
            value = value[0]
    return tuple(path)


def _statement(
    text: str,
    i: int,
    context: SourcePath,
    positions: dict[SourcePath, int],
    arrays: dict[SourcePath, int],
) -> tuple[SourcePath, int]:
    start = i
    n = len(text)
    char = text[i]
    if char == "[":
        end = text.find("\n", i)
        end = n if end == -1 else end
        keys = _key_path(text[i:end])
        path: SourcePath = ()
        for index, key in enumerate(keys):
            path += (key,)
            positions.setdefault(path, start)
            if index == len(keys) - 1 and text.startswith("[[", i):
                arrays[path] = arrays.get(path, -1) + 1
            if path in arrays:
                path += (arrays[path],)
                positions.setdefault(path, start)
        context = path
        i = end
    else:
        end = i
        while text[end] != "=":
            end = _skip_string(text, end, n) or end + 1
        path = context + _key_path(text[i:end] + "=0")
        i = end + 1
        for size in range(1, len(path) + 1):
            positions.setdefault(path[:size], start)
    return context, i


def source_positions(text: str) -> dict[SourcePath, int]:
    positions: dict[SourcePath, int] = {}
    arrays: dict[SourcePath, int] = {}
    context: SourcePath = ()
    i, n, depth = 0, len(text), 0
    at_start = True
    while i < n:
        char = text[i]
        if at_start and depth == 0 and char not in " \t\r\n#":
            context, i = _statement(text, i, context, positions, arrays)
            at_start = False
            continue
        next_i = _skip_string(text, i, n)
        if next_i is not None:
            i = next_i
        elif char == "#":
            end = text.find("\n", i)
            i = n if end == -1 else end
        else:
            if char == "\n":
                at_start = True
            elif char in "[{":
                depth += 1
            elif char in "]}":
                depth -= 1
            if char not in " \t\r\n":
                at_start = False
            i += 1
    return positions
