"""
parser.py — Recursive descent parser for Vect.

Consumes a token stream (from lexer.py) and builds an AST
(nodes from ast_nodes.py).

Operator precedence (lowest to highest):
  1.  or
  2.  and
  3.  not
  4.  ==  !=  <  <=  >  >=
  5.  +  -
  6.  *  /  %  @  ·
  7.  ** (right-associative)
  8.  unary -  not
  9.  postfix: call(), index[]
  10. primary: literals, identifiers, (expr), [vec], d/dx(...)

Each precedence level has its own parse_* method.  The methods call
downward (higher precedence) to build the tree correctly.
"""

from typing import List, Optional
from .lexer import Token, tokenize, LexError
from .ast_nodes import *


# ---------------------------------------------------------------------------
# Parse error
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """A human-readable parse error with source position."""
    def __init__(self, msg: str, line: int, col: int):
        self.line = line
        self.col = col
        super().__init__(f"Parse error at line {line}, col {col}: {msg}")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: List[Token]):
        # Keep all tokens including NEWLINEs; skip_newlines() handles them contextually.
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # Token navigation helpers
    # ------------------------------------------------------------------

    def peek(self, offset: int = 0) -> Token:
        """Look at the token at pos+offset without consuming it."""
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[idx]

    def current(self) -> Token:
        return self.peek(0)

    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok

    def skip_newlines(self):
        """Skip any NEWLINE tokens (used between statements)."""
        while self.current().type == 'NEWLINE':
            self.advance()

    def expect(self, *types: str) -> Token:
        """
        Consume and return the current token if it matches one of the
        given types.  Raises a helpful ParseError if it doesn't.
        """
        tok = self.current()
        if tok.type in types:
            self.advance()
            return tok
        expected = ' or '.join(repr(t) for t in types)
        raise ParseError(
            f"Expected {expected}, but found {tok.type!r} ({tok.value!r})",
            tok.line, tok.col
        )

    def match(self, *types: str) -> bool:
        """Return True (and consume) if current token matches any type."""
        if self.current().type in types:
            self.advance()
            return True
        return False

    def check(self, *types: str) -> bool:
        """Return True if current token matches any type, without consuming."""
        return self.current().type in types

    # ------------------------------------------------------------------
    # Top-level
    # ------------------------------------------------------------------

    def parse_program(self) -> Program:
        self.skip_newlines()
        body = []
        while not self.check('EOF'):
            stmt = self.parse_statement()
            if stmt is not None:
                body.append(stmt)
            self.skip_newlines()
        tok = self.current()
        return Program(body=body, line=1, col=1)

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def parse_statement(self) -> Optional[Node]:
        self.skip_newlines()
        tok = self.current()

        if tok.type == 'EOF':
            return None

        # Variable declaration
        if tok.type == 'VAR':
            return self.parse_var_decl()

        # Function definition
        if tok.type == 'FN':
            return self.parse_func_def()

        # Symbolic function definition
        if tok.type == 'SYM':
            return self.parse_symbolic_func()

        # if statement
        if tok.type == 'IF':
            return self.parse_if()

        # while loop
        if tok.type == 'WHILE':
            return self.parse_while()

        # for loop
        if tok.type == 'FOR':
            return self.parse_for()

        # return
        if tok.type == 'RETURN':
            return self.parse_return()

        # break
        if tok.type == 'BREAK':
            self.advance()
            self._consume_stmt_end()
            return Break(line=tok.line, col=tok.col)

        # continue
        if tok.type == 'CONTINUE':
            self.advance()
            self._consume_stmt_end()
            return Continue(line=tok.line, col=tok.col)

        # print statement (built-in keyword)
        if tok.type == 'PRINT':
            return self.parse_print_call()

        # Assignment or expression statement
        return self.parse_assign_or_expr()

    def _consume_stmt_end(self):
        """Consume an optional NEWLINE or SEMICOLON at end of statement."""
        while self.check('NEWLINE', 'SEMICOLON'):
            self.advance()

    def parse_var_decl(self) -> VarDecl:
        tok = self.expect('VAR')
        name_tok = self.expect('IDENT')
        type_ann = None
        if self.match('COLON'):
            type_ann = self.expect(
                'INT', 'FLOAT', 'BOOL', 'STRING', 'VEC', 'MAT', 'IDENT'
            ).value
        self.expect('ASSIGN')
        value = self.parse_expr()
        self._consume_stmt_end()
        return VarDecl(name=name_tok.value, type_annotation=type_ann,
                       value=value, line=tok.line, col=tok.col)

    def parse_func_def(self) -> FuncDef:
        tok = self.expect('FN')
        name_tok = self.expect('IDENT')
        self.expect('LPAREN')
        params = []
        if not self.check('RPAREN'):
            params.append(self.parse_param())
            while self.match('COMMA'):
                params.append(self.parse_param())
        self.expect('RPAREN')
        ret_type = None
        if self.match('ARROW'):
            ret_type = self.expect(
                'INT', 'FLOAT', 'BOOL', 'STRING', 'VEC', 'MAT', 'IDENT'
            ).value
        self.skip_newlines()
        self.expect('LBRACE')
        body = self.parse_block()
        self.expect('RBRACE')
        self._consume_stmt_end()
        return FuncDef(name=name_tok.value, params=params,
                       return_type=ret_type, body=body,
                       line=tok.line, col=tok.col)

    def parse_param(self) -> Param:
        tok = self.expect('IDENT')
        type_ann = None
        if self.match('COLON'):
            type_ann = self.expect(
                'INT', 'FLOAT', 'BOOL', 'STRING', 'VEC', 'MAT', 'IDENT'
            ).value
        return Param(name=tok.value, type_annotation=type_ann,
                     line=tok.line, col=tok.col)

    def parse_symbolic_func(self) -> SymbolicFunc:
        """Parse: sym f(x, y) = expr"""
        tok = self.expect('SYM')
        name_tok = self.expect('IDENT')
        self.expect('LPAREN')
        params = []
        if not self.check('RPAREN'):
            params.append(self.expect('IDENT').value)
            while self.match('COMMA'):
                params.append(self.expect('IDENT').value)
        self.expect('RPAREN')
        self.expect('ASSIGN')
        expr = self.parse_expr()
        self._consume_stmt_end()
        return SymbolicFunc(name=name_tok.value, params=params,
                            expr=expr, line=tok.line, col=tok.col)

    def parse_if(self) -> If:
        tok = self.expect('IF')
        cond = self.parse_expr()
        self.skip_newlines()
        self.expect('LBRACE')
        body = self.parse_block()
        self.expect('RBRACE')
        else_body = None
        # Look ahead past newlines for 'else'
        saved = self.pos
        self.skip_newlines()
        if self.check('ELSE'):
            self.advance()
            self.skip_newlines()
            if self.check('IF'):
                # else-if chain
                else_body = [self.parse_if()]
            else:
                self.expect('LBRACE')
                else_body = self.parse_block()
                self.expect('RBRACE')
        else:
            self.pos = saved
        self._consume_stmt_end()
        return If(condition=cond, body=body, else_body=else_body,
                  line=tok.line, col=tok.col)

    def parse_while(self) -> While:
        tok = self.expect('WHILE')
        cond = self.parse_expr()
        self.skip_newlines()
        self.expect('LBRACE')
        body = self.parse_block()
        self.expect('RBRACE')
        self._consume_stmt_end()
        return While(condition=cond, body=body, line=tok.line, col=tok.col)

    def parse_for(self) -> For:
        tok = self.expect('FOR')
        var_tok = self.expect('IDENT')
        self.expect('IN')
        iterable = self.parse_expr()
        self.skip_newlines()
        self.expect('LBRACE')
        body = self.parse_block()
        self.expect('RBRACE')
        self._consume_stmt_end()
        return For(var=var_tok.value, iterable=iterable, body=body,
                   line=tok.line, col=tok.col)

    def parse_return(self) -> Return:
        tok = self.expect('RETURN')
        value = None
        if not self.check('NEWLINE', 'SEMICOLON', 'RBRACE', 'EOF'):
            value = self.parse_expr()
        self._consume_stmt_end()
        return Return(value=value, line=tok.line, col=tok.col)

    def parse_print_call(self) -> ExprStatement:
        """print(expr, ...) — sugar for the built-in print function."""
        tok = self.expect('PRINT')
        self.expect('LPAREN')
        args = []
        if not self.check('RPAREN'):
            args.append(self.parse_expr())
            while self.match('COMMA'):
                args.append(self.parse_expr())
        self.expect('RPAREN')
        self._consume_stmt_end()
        call = FuncCall(name='print', args=args, line=tok.line, col=tok.col)
        return ExprStatement(expr=call, line=tok.line, col=tok.col)

    def parse_assign_or_expr(self) -> Node:
        """
        Either an assignment  (name = expr  or  name[i] = expr)
        or a plain expression statement.
        """
        # Try to detect assignment by looking ahead
        if self.check('IDENT'):
            # name = expr
            if self.peek(1).type == 'ASSIGN':
                name_tok = self.advance()
                self.advance()  # consume '='
                value = self.parse_expr()
                self._consume_stmt_end()
                return Assign(name=name_tok.value, value=value,
                              line=name_tok.line, col=name_tok.col)
            # name[index] = expr
            if self.peek(1).type == 'LBRACKET':
                saved = self.pos
                name_tok = self.advance()
                self.advance()  # '['
                index = self.parse_expr()
                if self.check('RBRACKET') and self.peek(1).type == 'ASSIGN':
                    self.advance()  # ']'
                    self.advance()  # '='
                    value = self.parse_expr()
                    self._consume_stmt_end()
                    return IndexAssign(name=name_tok.value, index=index,
                                       value=value, line=name_tok.line,
                                       col=name_tok.col)
                else:
                    self.pos = saved

        expr = self.parse_expr()
        self._consume_stmt_end()
        return ExprStatement(expr=expr, line=expr.line, col=expr.col)

    def parse_block(self) -> List[Node]:
        """Parse a brace-delimited block of statements."""
        stmts = []
        self.skip_newlines()
        while not self.check('RBRACE', 'EOF'):
            stmt = self.parse_statement()
            if stmt is not None:
                stmts.append(stmt)
            self.skip_newlines()
        return stmts

    # ------------------------------------------------------------------
    # Expressions — precedence climbing
    # ------------------------------------------------------------------

    def parse_expr(self) -> Node:
        return self.parse_or()

    def parse_or(self) -> Node:
        left = self.parse_and()
        while self.check('OR'):
            op_tok = self.advance()
            right = self.parse_and()
            left = BinOp(op='or', left=left, right=right,
                         line=op_tok.line, col=op_tok.col)
        return left

    def parse_and(self) -> Node:
        left = self.parse_not()
        while self.check('AND'):
            op_tok = self.advance()
            right = self.parse_not()
            left = BinOp(op='and', left=left, right=right,
                         line=op_tok.line, col=op_tok.col)
        return left

    def parse_not(self) -> Node:
        if self.check('NOT'):
            op_tok = self.advance()
            operand = self.parse_not()
            return UnaryOp(op='not', operand=operand,
                           line=op_tok.line, col=op_tok.col)
        return self.parse_comparison()

    def parse_comparison(self) -> Node:
        left = self.parse_addition()
        while self.check('EQ', 'NEQ', 'LT', 'LEQ', 'GT', 'GEQ'):
            op_tok = self.advance()
            right = self.parse_addition()
            left = BinOp(op=op_tok.value, left=left, right=right,
                         line=op_tok.line, col=op_tok.col)
        return left

    def parse_addition(self) -> Node:
        left = self.parse_multiplication()
        while self.check('PLUS', 'MINUS'):
            op_tok = self.advance()
            right = self.parse_multiplication()
            left = BinOp(op=op_tok.value, left=left, right=right,
                         line=op_tok.line, col=op_tok.col)
        return left

    def parse_multiplication(self) -> Node:
        left = self.parse_power()
        while self.check('STAR', 'SLASH', 'PERCENT', 'MATMUL', 'DOT_PROD'):
            op_tok = self.advance()
            right = self.parse_power()
            left = BinOp(op=op_tok.value, left=left, right=right,
                         line=op_tok.line, col=op_tok.col)
        return left

    def parse_power(self) -> Node:
        """** is right-associative: 2**3**2 == 2**(3**2)."""
        base = self.parse_unary()
        if self.check('POW'):
            op_tok = self.advance()
            exp = self.parse_power()  # right-recursive for right-associativity
            return BinOp(op='**', left=base, right=exp,
                         line=op_tok.line, col=op_tok.col)
        return base

    def parse_unary(self) -> Node:
        if self.check('MINUS'):
            op_tok = self.advance()
            operand = self.parse_unary()
            return UnaryOp(op='-', operand=operand,
                           line=op_tok.line, col=op_tok.col)
        if self.check('NOT'):
            op_tok = self.advance()
            operand = self.parse_unary()
            return UnaryOp(op='not', operand=operand,
                           line=op_tok.line, col=op_tok.col)
        return self.parse_postfix()

    def parse_postfix(self) -> Node:
        """Handle function calls and subscript access."""
        expr = self.parse_primary()
        while True:
            if self.check('LBRACKET'):
                lbracket = self.advance()
                index = self.parse_expr()
                self.expect('RBRACKET')
                expr = IndexAccess(obj=expr, index=index,
                                   line=lbracket.line, col=lbracket.col)
            elif self.check('LPAREN') and isinstance(expr, Identifier):
                # function call on identifier
                lp = self.advance()
                args = []
                if not self.check('RPAREN'):
                    args.append(self.parse_expr())
                    while self.match('COMMA'):
                        args.append(self.parse_expr())
                self.expect('RPAREN')
                expr = FuncCall(name=expr.name, args=args,
                                line=expr.line, col=expr.col)
            else:
                break
        return expr

    def parse_primary(self) -> Node:
        tok = self.current()

        # Integer literal
        if tok.type == 'INT':
            self.advance()
            return IntLiteral(value=int(tok.value), line=tok.line, col=tok.col)

        # Float literal
        if tok.type == 'FLOAT':
            self.advance()
            return FloatLiteral(value=float(tok.value), line=tok.line, col=tok.col)

        # Bool literal
        if tok.type == 'BOOL':
            self.advance()
            return BoolLiteral(value=(tok.value == 'true'), line=tok.line, col=tok.col)

        # String literal
        if tok.type == 'STRING':
            self.advance()
            return StringLiteral(value=tok.value, line=tok.line, col=tok.col)

        # Identifier or function call
        if tok.type == 'IDENT':
            self.advance()
            return Identifier(name=tok.value, line=tok.line, col=tok.col)

        # Transpose — postfix .T accessed as keyword T (handled after primary)
        if tok.type == 'T':
            # This shouldn't appear as a standalone primary.
            # It's handled as a built-in function call: T(matrix)
            self.advance()
            self.expect('LPAREN')
            arg = self.parse_expr()
            self.expect('RPAREN')
            return FuncCall(name='transpose', args=[arg],
                            line=tok.line, col=tok.col)

        # Grouped expression
        if tok.type == 'LPAREN':
            self.advance()
            expr = self.parse_expr()
            self.expect('RPAREN')
            return expr

        # Vector or matrix literal: [...]
        if tok.type == 'LBRACKET':
            return self.parse_vector_or_matrix()

        # Derivative syntax: d/dx(expr)
        if tok.type == 'DDIV':
            return self.parse_derivative()

        # eval(expr, x=val, ...)  — evaluate a symbolic expression
        if tok.type == 'EVAL':
            return self.parse_eval()

        # print as expression (shouldn't normally happen but be defensive)
        if tok.type == 'PRINT':
            return self.parse_print_expr()

        raise ParseError(
            f"Unexpected token {tok.type!r} ({tok.value!r}) — "
            f"expected a value or expression",
            tok.line, tok.col
        )

    # ------------------------------------------------------------------
    # Vector / matrix literals
    # ------------------------------------------------------------------

    def parse_vector_or_matrix(self) -> Node:
        """
        Parse [elem, elem, ...].
        If the first element is itself a [...], treat the whole thing as
        a matrix literal (list of row vectors).
        """
        tok = self.expect('LBRACKET')

        if self.check('RBRACKET'):
            # Empty vector
            self.advance()
            return VectorLiteral(elements=[], line=tok.line, col=tok.col)

        # Peek: is the first element itself a vector?
        first = self.parse_expr()

        if isinstance(first, VectorLiteral) and not self.check('RBRACKET'):
            # It's a matrix
            rows = [first]
            while self.match('COMMA'):
                row = self.parse_expr()
                if not isinstance(row, VectorLiteral):
                    raise ParseError(
                        "In a matrix literal, every row must be a vector like [1, 2, 3]",
                        row.line, row.col
                    )
                rows.append(row)
            self.expect('RBRACKET')
            return MatrixLiteral(rows=rows, line=tok.line, col=tok.col)

        if isinstance(first, VectorLiteral):
            # Single-row matrix — treat as matrix
            self.expect('RBRACKET')
            return MatrixLiteral(rows=[first], line=tok.line, col=tok.col)

        # It's a flat vector
        elements = [first]
        while self.match('COMMA'):
            elements.append(self.parse_expr())
        self.expect('RBRACKET')
        return VectorLiteral(elements=elements, line=tok.line, col=tok.col)

    # ------------------------------------------------------------------
    # Symbolic differentiation
    # ------------------------------------------------------------------

    def parse_derivative(self) -> Derivative:
        """
        Parse: d/dx(expr)

        The lexer emits 'd/d' as a single DDIV token, then the variable
        name follows as IDENT, then (expr).
        """
        tok = self.expect('DDIV')
        var_tok = self.expect('IDENT')
        self.expect('LPAREN')
        expr = self.parse_expr()
        self.expect('RPAREN')
        return Derivative(variable=var_tok.value, expr=expr,
                          line=tok.line, col=tok.col)

    def parse_eval(self) -> SymbolicEval:
        """
        Parse: eval(expr, x=val, y=val2, ...)
        """
        tok = self.expect('EVAL')
        self.expect('LPAREN')
        expr = self.parse_expr()
        bindings = []
        while self.match('COMMA'):
            name_tok = self.expect('IDENT')
            self.expect('ASSIGN')
            val = self.parse_expr()
            bindings.append((name_tok.value, val))
        self.expect('RPAREN')
        return SymbolicEval(expr=expr, bindings=bindings,
                            line=tok.line, col=tok.col)

    def parse_print_expr(self) -> FuncCall:
        tok = self.expect('PRINT')
        self.expect('LPAREN')
        args = []
        if not self.check('RPAREN'):
            args.append(self.parse_expr())
            while self.match('COMMA'):
                args.append(self.parse_expr())
        self.expect('RPAREN')
        return FuncCall(name='print', args=args, line=tok.line, col=tok.col)


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

def parse(source: str, filename: str = '<input>') -> Program:
    """
    Lex and parse a Vect source string, returning the AST root.
    Raises LexError or ParseError with clear messages on failure.
    """
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse_program()


# ---------------------------------------------------------------------------
# Debug helper — pretty-print an AST
# ---------------------------------------------------------------------------

def _indent(level: int) -> str:
    return '  ' * level


def dump_ast(node, level: int = 0) -> str:
    """Return a human-readable tree representation of the AST."""
    if node is None:
        return _indent(level) + 'None'
    if isinstance(node, list):
        return '\n'.join(dump_ast(n, level) for n in node)
    if not isinstance(node, Node):
        return _indent(level) + repr(node)

    cls = node.__class__.__name__
    fields = {k: v for k, v in node.__dict__.items()
              if k not in ('line', 'col')}

    if not fields:
        return _indent(level) + cls

    lines = [_indent(level) + cls]
    for name, val in fields.items():
        if isinstance(val, list):
            lines.append(_indent(level + 1) + f'{name}:')
            for item in val:
                lines.append(dump_ast(item, level + 2))
        elif isinstance(val, Node):
            lines.append(_indent(level + 1) + f'{name}:')
            lines.append(dump_ast(val, level + 2))
        else:
            lines.append(_indent(level + 1) + f'{name}: {val!r}')
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    src = sys.stdin.read() if len(sys.argv) == 1 else open(sys.argv[1]).read()
    try:
        tree = parse(src)
        print(dump_ast(tree))
    except (LexError, ParseError) as e:
        print(f"Error: {e}")
        sys.exit(1)
