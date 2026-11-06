"""JSON with comments and trailing commas, without changing string contents."""

import json
import re

_STRING = r'"(?:[^"\\]|\\.)*"'
_COMMENTS = re.compile(rf"{_STRING}|//[^\r\n]*|/\*[\s\S]*?\*/")
_TRAILING = re.compile(rf"{_STRING}|,(?=\s*[}}\]])")


def loads(text: str) -> object:
    cleaned = _COMMENTS.sub(
        lambda m: m[0] if m[0].startswith('"') else re.sub(r"[^\r\n]", " ", m[0]), text
    )

    def trailing_comma(match: re.Match[str]) -> str:
        if match[0].startswith('"'):
            return match[0]
        preceding = cleaned[: match.start()].rstrip()
        # Keep commas without a preceding value so JSON validation rejects them.
        return "" if preceding and preceding[-1] not in "[{,:" else match[0]

    return json.loads(_TRAILING.sub(trailing_comma, cleaned))
