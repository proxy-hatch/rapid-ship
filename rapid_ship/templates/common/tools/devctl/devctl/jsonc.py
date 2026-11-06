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
    return json.loads(_TRAILING.sub(lambda m: m[0] if m[0].startswith('"') else "", cleaned))
