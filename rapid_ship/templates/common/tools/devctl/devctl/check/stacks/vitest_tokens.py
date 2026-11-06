"""Shared lexical boundaries for the pure Vitest readers."""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = re.compile(r"[\w$]+")
_REGEX_AFTER = frozenset({"(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "return"})
_TAG = re.compile(r"<([A-Za-z][\w.:-]*)(?=[\s/>])")


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    kind: str = "code"


class Lexer:
    def __init__(self, source: str) -> None:
        self.source = source
        self.position = 0
        self.tokens: list[Token] = []

    def quoted(self, quote: str) -> Token:
        start = self.position
        self.position += 1
        dynamic = False
        while self.position < len(self.source):
            char = self.source[self.position]
            self.position += 1
            if char == "\\":
                self.position += 1
            elif char == quote:
                return Token(
                    self.source[start : self.position],
                    start,
                    self.position,
                    "dynamic" if dynamic else "string",
                )
            elif char in "\r\n" and quote != "`":
                break
            elif (
                quote == "`"
                and char == "$"
                and self.source[self.position : self.position + 1] == "{"
            ):
                dynamic = True
                self.position += 1
                previous = len(self.tokens)
                self.javascript(stop="}")
                del self.tokens[previous:]
        raise ValueError(f"unterminated string at offset {start}")

    def regex(self) -> Token:
        start = self.position
        self.position += 1
        character_class = False
        while self.position < len(self.source):
            char = self.source[self.position]
            self.position += 1
            if char == "\\":
                self.position += 1
            elif char == "[":
                character_class = True
            elif char == "]":
                character_class = False
            elif char == "/" and not character_class:
                while self.position < len(self.source) and self.source[self.position].isalpha():
                    self.position += 1
                return Token(self.source[start : self.position], start, self.position, "regex")
            elif char in "\r\n":
                break
        raise ValueError(f"unterminated regular expression at offset {start}")

    def jsx_start(self) -> bool:
        rest = self.source[self.position :]
        if rest.startswith("<>"):
            return True
        match = _TAG.match(rest)
        if match is None:
            return False
        previous = self.tokens[-1].text if self.tokens else "="
        if previous not in _REGEX_AFTER and previous not in {">", "=>"}:
            return False
        return bool(f"</{match[1]}" in rest or re.match(r"<[^<>]*?/\s*>", rest))

    def jsx_expression(self) -> None:
        start = self.position
        self.tokens.append(Token("{", start, start + 1))
        self.position += 1
        self.javascript(stop="}")
        self.tokens.append(Token("}", self.position - 1, self.position))

    def jsx_tag(self) -> bool:
        """Consume an opening or closing tag; return whether it is self-closing."""
        while self.position < len(self.source):
            char = self.source[self.position]
            if char == ">":
                closed = self.source[: self.position].rstrip().endswith("/")
                self.position += 1
                return closed
            if char in "\"'":
                # JSX attributes do not use JavaScript backslash escaping.
                end = self.source.find(char, self.position + 1)
                if end < 0:
                    raise ValueError("unterminated JSX attribute")
                self.position = end + 1
            elif char == "{":
                self.jsx_expression()
            else:
                self.position += 1
        raise ValueError("unterminated JSX tag")

    def jsx(self) -> None:
        if self.jsx_tag():
            return
        while self.position < len(self.source):
            if self.source.startswith("</", self.position):
                self.jsx_tag()
                return
            char = self.source[self.position]
            if char == "<":
                self.jsx()
            elif char == "{":
                self.jsx_expression()
            else:
                self.position += 1
        raise ValueError("unterminated JSX element")

    def comment(self) -> bool:
        if self.source.startswith("//", self.position):
            end = self.source.find("\n", self.position)
            self.position = len(self.source) if end < 0 else end
        elif self.source.startswith("/*", self.position):
            end = self.source.find("*/", self.position + 2)
            if end < 0:
                raise ValueError("unterminated comment")
            self.position = end + 2
        else:
            return False
        return True

    def javascript(self, stop: str = "") -> None:
        depth = 0
        while self.position < len(self.source):
            char = self.source[self.position]
            if char.isspace() or self.comment():
                if char.isspace():
                    self.position += 1
                continue
            if char == stop and depth == 0:
                self.position += 1
                return
            if char == "<" and self.jsx_start():
                self.jsx()
                continue
            token = self.next_token(char)
            depth += (token.text == "{") - (token.text == "}")
            self.tokens.append(token)
        if stop:
            raise ValueError("unterminated JavaScript expression")

    def next_token(self, char: str) -> Token:
        if char in "\"'`":
            return self.quoted(char)
        previous = self.tokens[-1].text if self.tokens else ";"
        if char == "/" and previous in _REGEX_AFTER:
            return self.regex()
        start = self.position
        word = _WORD.match(self.source, start)
        self.position = word.end() if word else start + 1
        return Token(self.source[start : self.position], start, self.position)


def tokens(source: str) -> tuple[list[Token], dict[int, int]]:
    lexer = Lexer(source)
    lexer.javascript()
    pairs: dict[int, int] = {}
    stack: list[int] = []
    for index, token in enumerate(lexer.tokens):
        if token.kind != "code":
            continue
        if token.text in {"(", "[", "{"}:
            stack.append(index)
        elif token.text in {")", "]", "}"}:
            if (
                not stack
                or lexer.tokens[stack[-1]].text != {")": "(", "]": "[", "}": "{"}[token.text]
            ):
                raise ValueError("unbalanced JavaScript delimiters")
            opened = stack.pop()
            pairs[opened] = index
    if stack:
        raise ValueError("unclosed JavaScript delimiter")
    return lexer.tokens, pairs


def title(token: Token) -> str | None:
    if token.kind != "string":
        return None
    value = re.sub(r"\\\r?\n", "", token.text[1:-1])
    escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "0": "\0"}
    return re.sub(
        r"\\(u[\da-fA-F]{4}|x[\da-fA-F]{2}|.)",
        lambda m: (
            chr(int(m[1][1:], 16)) if m[1][0] in "ux" and len(m[1]) > 1 else escapes.get(m[1], m[1])
        ),
        value,
    )
