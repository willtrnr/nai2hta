from __future__ import annotations

import typing as T

from parsec import Parser, Value, many, many1, optional, regex, sepBy, string

_P = T.TypeVar("_P")


def recognize(p: Parser) -> Parser[str]:
    @Parser
    def recognize_parser(text, index) -> Value:
        res = p(text, index)
        if res.status:
            return Value.success(res.index, text[index : res.index])
        else:
            return res

    return recognize_parser


whitespace = regex(r"\s+")
ignore = many(whitespace)


def lexeme(p):
    return p << ignore


lparen = lexeme(string("("))
rparen = lexeme(string(")"))
lbracket = lexeme(string("["))
rbracket = lexeme(string("]"))
lbrace = lexeme(string("{"))
rbrace = lexeme(string("}"))
colon = lexeme(string(":"))
comma = lexeme(string(","))
newline = lexeme(string("\n"))

number = lexeme(regex(r"-?\d+(?:\.\d+)?").parsecmap(float))
word = lexeme(regex(r"""[^\s\[\]\{\}\(\),]+"""))
sep = many1(comma | newline)

tag = recognize(word + many(word | (lparen + many(word) + optional(rparen))))

weight = colon >> number


def weighted(
    begin: Parser, p: Parser[_P], end: Parser
) -> Parser[tuple[_P, float | None]]:
    return many1(begin) >> (p + optional(weight)) << many1(end)


tags = sepBy(tag, sep) << optional(sep)

weighted_tags: Parser[tuple[list[str], float | None]] = (
    weighted(lparen, tags, rparen)
    | weighted(lbracket, tags, rbracket)
    | weighted(lbrace, tags, rbrace)
)

prompt = many(weighted_tags | tags.parsecmap(lambda v: (v, None)))


def parse(text: str) -> list[tuple[list[str], float | None]]:
    return (ignore >> prompt).parse(text)
