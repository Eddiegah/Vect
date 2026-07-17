"""Tests for the Vect lexer."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.lexer import tokenize, LexError, Token


def tok_types(source):
    """Convenience: tokenize and return just the token types (no EOF)."""
    return [t.type for t in tokenize(source) if t.type != 'EOF']


def tok_values(source):
    return [(t.type, t.value) for t in tokenize(source) if t.type != 'EOF']


# ---------------------------------------------------------------------------
# Basic literals
# ---------------------------------------------------------------------------

class TestLiterals:
    def test_integer(self):
        tokens = tokenize('42')
        assert tokens[0].type == 'INT'
        assert tokens[0].value == '42'

    def test_float(self):
        tokens = tokenize('3.14')
        assert tokens[0].type == 'FLOAT'
        assert tokens[0].value == '3.14'

    def test_float_scientific(self):
        tokens = tokenize('1.5e10')
        assert tokens[0].type == 'FLOAT'

    def test_bool_true(self):
        tokens = tokenize('true')
        assert tokens[0].type == 'BOOL'
        assert tokens[0].value == 'true'

    def test_bool_false(self):
        tokens = tokenize('false')
        assert tokens[0].type == 'BOOL'

    def test_string(self):
        tokens = tokenize('"hello world"')
        assert tokens[0].type == 'STRING'
        assert tokens[0].value == 'hello world'

    def test_string_escape(self):
        tokens = tokenize(r'"line1\nline2"')
        assert tokens[0].value == 'line1\nline2'


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

class TestKeywords:
    def test_var(self):
        assert tok_types('var') == ['VAR']

    def test_fn(self):
        assert tok_types('fn') == ['FN']

    def test_if_else(self):
        assert tok_types('if else') == ['IF', 'ELSE']

    def test_while_for_in(self):
        assert tok_types('while for in') == ['WHILE', 'FOR', 'IN']

    def test_return(self):
        assert tok_types('return') == ['RETURN']

    def test_sym(self):
        assert tok_types('sym') == ['SYM']

    def test_print(self):
        assert tok_types('print') == ['PRINT']

    def test_and_or_not(self):
        assert tok_types('and or not') == ['AND', 'OR', 'NOT']


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class TestOperators:
    def test_arithmetic(self):
        assert tok_types('+ - * / %') == ['PLUS', 'MINUS', 'STAR', 'SLASH', 'PERCENT']

    def test_power(self):
        assert tok_types('**') == ['POW']

    def test_comparison(self):
        assert tok_types('== != < <= > >=') == ['EQ', 'NEQ', 'LT', 'LEQ', 'GT', 'GEQ']

    def test_matmul(self):
        assert tok_types('@') == ['MATMUL']

    def test_arrow(self):
        assert tok_types('->') == ['ARROW']

    def test_assign(self):
        assert tok_types('=') == ['ASSIGN']

    def test_ddiv(self):
        # d/dx should be lexed as DDIV followed by IDENT
        types = tok_types('d/dx')
        assert types[0] == 'DDIV'
        assert types[1] == 'IDENT'

    def test_dot_product(self):
        assert tok_types('·') == ['DOT_PROD']


# ---------------------------------------------------------------------------
# Delimiters
# ---------------------------------------------------------------------------

class TestDelimiters:
    def test_parens(self):
        assert tok_types('()') == ['LPAREN', 'RPAREN']

    def test_braces(self):
        assert tok_types('{}') == ['LBRACE', 'RBRACE']

    def test_brackets(self):
        assert tok_types('[]') == ['LBRACKET', 'RBRACKET']

    def test_comma_colon(self):
        assert tok_types(', :') == ['COMMA', 'COLON']


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------

class TestComments:
    def test_comment_stripped(self):
        types = tok_types('42 # this is a comment')
        assert 'COMMENT' not in types
        assert types == ['INT']

    def test_whole_line_comment(self):
        types = tok_types('# comment only\n42')
        assert types == ['INT']


# ---------------------------------------------------------------------------
# Identifiers
# ---------------------------------------------------------------------------

class TestIdentifiers:
    def test_simple(self):
        tokens = tokenize('myVar')
        assert tokens[0].type == 'IDENT'
        assert tokens[0].value == 'myVar'

    def test_underscore(self):
        tokens = tokenize('_private')
        assert tokens[0].type == 'IDENT'

    def test_alphanumeric(self):
        tokens = tokenize('var1')
        assert tokens[0].type == 'IDENT'


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrors:
    def test_bad_char(self):
        with pytest.raises(LexError) as exc_info:
            tokenize('var x = $10')
        assert exc_info.value.line == 1

    def test_unclosed_string(self):
        # Unclosed string — the regex won't match so it falls through to MISMATCH
        with pytest.raises(LexError):
            tokenize('"unclosed')


# ---------------------------------------------------------------------------
# Source positions
# ---------------------------------------------------------------------------

class TestPositions:
    def test_line_numbers(self):
        tokens = [t for t in tokenize('a\nb\nc') if t.type != 'EOF']
        idents = [t for t in tokens if t.type == 'IDENT']
        assert idents[0].line == 1
        assert idents[1].line == 2
        assert idents[2].line == 3

    def test_column_numbers(self):
        tokens = [t for t in tokenize('  hello') if t.type != 'EOF']
        assert tokens[0].col == 3


# ---------------------------------------------------------------------------
# Vector syntax
# ---------------------------------------------------------------------------

class TestVectorSyntax:
    def test_vector_brackets(self):
        types = tok_types('[1, 2, 3]')
        assert types == ['LBRACKET', 'INT', 'COMMA', 'INT', 'COMMA', 'INT', 'RBRACKET']

    def test_matrix_brackets(self):
        types = tok_types('[[1,2],[3,4]]')
        assert 'LBRACKET' in types
        assert 'RBRACKET' in types
