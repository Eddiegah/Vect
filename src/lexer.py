"""
lexer.py — Tokenizer for the Vect language.

Converts a raw source string into a flat list of Token objects.
The parser then consumes those tokens.

Token types are plain strings (e.g. 'INT', 'PLUS', 'IDENT').
This keeps the code easy to read and debug — no need for an enum here.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: str        # e.g. 'INT', 'PLUS', 'IDENT', 'KEYWORD'
    value: str       # the raw text from the source
    line: int        # 1-based line number
    col: int         # 1-based column number

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, {self.line}:{self.col})"


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class LexError(Exception):
    """Raised when the lexer encounters a character it can't tokenize."""
    def __init__(self, msg: str, line: int, col: int):
        self.line = line
        self.col = col
        super().__init__(f"Syntax error at line {line}, col {col}: {msg}")


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

KEYWORDS = {
    # Control flow
    'if', 'else', 'while', 'for', 'in', 'break', 'continue', 'return',
    # Declarations
    'var', 'fn', 'sym',
    # Types
    'int', 'float', 'bool', 'string', 'vec', 'mat',
    # Literals
    'true', 'false',
    # Operators (word form)
    'and', 'or', 'not',
    # Built-ins exposed as keywords
    'print', 'input', 'eval',
    # Transpose keyword
    'T',
}

# ---------------------------------------------------------------------------
# Token specification — ordered list of (type, regex) pairs.
# The lexer tries each in order and takes the first match.
# ---------------------------------------------------------------------------

_TOKEN_SPEC = [
    # Comments — line comments starting with #
    ('COMMENT',     r'#[^\n]*'),

    # Multi-char operators (must come before single-char ones)
    ('ARROW',       r'->'),
    ('POW',         r'\*\*'),
    ('EQ',          r'=='),
    ('NEQ',         r'!='),
    ('LEQ',         r'<='),
    ('GEQ',         r'>='),
    ('MATMUL',      r'@'),          # matrix multiply
    ('DOT_PROD',    r'·'),          # U+00B7 middle dot — dot product
    ('DDIV',        r'd/d'),        # start of d/dx derivative syntax

    # Single-char operators
    ('LT',          r'<'),
    ('GT',          r'>'),
    ('PLUS',        r'\+'),
    ('MINUS',       r'-'),
    ('STAR',        r'\*'),
    ('SLASH',       r'/'),
    ('PERCENT',     r'%'),
    ('ASSIGN',      r'='),
    ('BANG',        r'!'),

    # Delimiters
    ('LPAREN',      r'\('),
    ('RPAREN',      r'\)'),
    ('LBRACE',      r'\{'),
    ('RBRACE',      r'\}'),
    ('LBRACKET',    r'\['),
    ('RBRACKET',    r'\]'),
    ('COMMA',       r','),
    ('COLON',       r':'),
    ('SEMICOLON',   r';'),
    ('NEWLINE',     r'\n'),

    # Literals
    ('FLOAT',       r'\d+\.\d*([eE][+-]?\d+)?|\.\d+([eE][+-]?\d+)?'),
    ('INT',         r'\d+'),
    ('STRING',      r'"(?:[^"\\]|\\.)*"'),   # double-quoted strings

    # Identifiers / keywords
    ('IDENT',       r'[A-Za-z_][A-Za-z0-9_]*'),

    # Whitespace (not newline — we handle newline separately above)
    ('SKIP',        r'[ \t\r]+'),

    # Anything else is an error
    ('MISMATCH',    r'.'),
]

_MASTER_RE = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in _TOKEN_SPEC),
    re.UNICODE
)


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

def tokenize(source: str) -> List[Token]:
    """
    Convert source code string into a list of tokens.
    Raises LexError on unrecognised characters.
    Strips COMMENT, SKIP, and most NEWLINE tokens — the parser works
    statement-by-statement using SEMICOLON or NEWLINE as terminators,
    but we simplify by treating NEWLINE as a soft statement separator
    and letting the parser handle consecutive newlines.
    """
    tokens: List[Token] = []
    line = 1
    line_start = 0
    last_meaningful = None   # track last real token type for NEWLINE filtering

    for mo in _MASTER_RE.finditer(source):
        kind = mo.lastgroup
        value = mo.group()
        col = mo.start() - line_start + 1

        if kind == 'NEWLINE':
            line += 1
            line_start = mo.end()
            # Emit NEWLINE only after a token that could end a statement.
            # This keeps the token stream clean for the parser.
            if last_meaningful in (
                'INT', 'FLOAT', 'STRING', 'IDENT',
                'RPAREN', 'RBRACKET', 'RBRACE',
                'BREAK', 'CONTINUE', 'RETURN',
                'TRUE', 'FALSE',
                'KEYWORD',  # covers true/false/break etc. when re-classified below
            ):
                tokens.append(Token('NEWLINE', '\n', line - 1, col))
                last_meaningful = 'NEWLINE'
            continue

        elif kind in ('COMMENT', 'SKIP'):
            continue

        elif kind == 'MISMATCH':
            raise LexError(
                f"Unexpected character {value!r}",
                line, col
            )

        elif kind == 'STRING':
            # Strip surrounding quotes and process escape sequences
            inner = value[1:-1]
            inner = inner.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
            tok = Token('STRING', inner, line, col)
            tokens.append(tok)
            last_meaningful = 'STRING'
            continue

        elif kind == 'IDENT':
            # Promote identifiers that are keywords
            if value in KEYWORDS:
                # Use the value itself as the token type for keywords,
                # uppercased, so 'if' becomes 'IF', 'fn' becomes 'FN', etc.
                # Special case: 'true'/'false' get BOOL type.
                if value in ('true', 'false'):
                    tok = Token('BOOL', value, line, col)
                else:
                    tok = Token(value.upper(), value, line, col)
            else:
                tok = Token('IDENT', value, line, col)
            tokens.append(tok)
            last_meaningful = tok.type
            continue

        elif kind == 'FLOAT':
            tok = Token('FLOAT', value, line, col)
            tokens.append(tok)
            last_meaningful = 'FLOAT'
            continue

        elif kind == 'INT':
            tok = Token('INT', value, line, col)
            tokens.append(tok)
            last_meaningful = 'INT'
            continue

        else:
            tok = Token(kind, value, line, col)
            tokens.append(tok)
            last_meaningful = kind
            continue

    tokens.append(Token('EOF', '', line, 0))
    return tokens


# ---------------------------------------------------------------------------
# Debug helper
# ---------------------------------------------------------------------------

def dump_tokens(source: str) -> None:
    """Print all tokens — useful for debugging the lexer."""
    for tok in tokenize(source):
        print(tok)


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            dump_tokens(f.read())
    else:
        dump_tokens("""
var x = 10
var y = 3.14
if x > 5 {
    print("hello")
}
fn add(a: int, b: int) -> int {
    return a + b
}
v = [1, 2, 3]
""")
