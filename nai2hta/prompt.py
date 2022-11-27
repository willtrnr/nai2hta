from __future__ import annotations

import typing as T

from parsec import (
    Parser,
    Value,
    eof,
    lookahead,
    many,
    many1,
    optional,
    regex,
    sepBy1,
    sepEndBy,
    string,
)

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


def multi_delimited(begin: Parser, inner: Parser[_P], end: Parser) -> Parser[_P]:
    return many1(begin) >> inner << many1(end)


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
pipe = lexeme(string("|"))
comma = lexeme(string(","))
newline = lexeme(string("\n"))

number = lexeme(regex(r"-?\d+(?:\.\d+)?").parsecmap(float))
word = lexeme(regex(r"[^\s\[\]\{\}\(\),:|]+"))
sep = lexeme(many1(comma | newline))


def tags(end: Parser) -> Parser[list[tuple[list[str], float | None]]]:
    end = pipe | end

    tag = recognize(many1(word | (colon / (number < end))))
    tag = recognize(tag + many(tag | (lparen + tag + (rparen | lookahead(end)))))

    return sepBy1(sepEndBy(tag, sep) + optional(colon >> number), pipe)


weighted_tags = (
    multi_delimited(lparen, tags(rparen), rparen)
    | multi_delimited(lbracket, tags(rbracket), rbracket)
    | multi_delimited(lbrace, tags(rbrace), rbrace)
)

prompt = many((weighted_tags | tags(eof())) << optional(sep)).parsecmap(
    lambda v: sum(v, start=[])
)


def parse(text: str) -> list[tuple[list[str], float | None]]:
    return (ignore >> prompt).parse_strict(text)
