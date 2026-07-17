"""Tests for the Vect parser."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.parser import parse, ParseError, dump_ast
from src.ast_nodes import *


def first(source):
    """Parse source and return the first statement in the program body."""
    prog = parse(source)
    return prog.body[0]


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

class TestLiteralParsing:
    def test_int_literal(self):
        node = first('42')
        assert isinstance(node, ExprStatement)
        assert isinstance(node.expr, IntLiteral)
        assert node.expr.value == 42

    def test_float_literal(self):
        node = first('3.14')
        assert isinstance(node.expr, FloatLiteral)
        assert abs(node.expr.value - 3.14) < 1e-9

    def test_bool_true(self):
        node = first('true')
        assert isinstance(node.expr, BoolLiteral)
        assert node.expr.value is True

    def test_bool_false(self):
        node = first('false')
        assert isinstance(node.expr, BoolLiteral)
        assert node.expr.value is False

    def test_string_literal(self):
        node = first('"hello"')
        assert isinstance(node.expr, StringLiteral)
        assert node.expr.value == 'hello'


# ---------------------------------------------------------------------------
# Variable declarations
# ---------------------------------------------------------------------------

class TestVarDecl:
    def test_simple(self):
        node = first('var x = 10')
        assert isinstance(node, VarDecl)
        assert node.name == 'x'
        assert isinstance(node.value, IntLiteral)
        assert node.value.value == 10

    def test_with_type(self):
        node = first('var x: int = 10')
        assert isinstance(node, VarDecl)
        assert node.type_annotation == 'int'

    def test_float_decl(self):
        node = first('var pi = 3.14')
        assert isinstance(node, VarDecl)
        assert isinstance(node.value, FloatLiteral)


# ---------------------------------------------------------------------------
# Arithmetic and precedence
# ---------------------------------------------------------------------------

class TestArithmetic:
    def test_addition(self):
        node = first('1 + 2').expr
        assert isinstance(node, BinOp)
        assert node.op == '+'

    def test_precedence_mul_over_add(self):
        # 1 + 2 * 3 should parse as 1 + (2 * 3)
        node = first('1 + 2 * 3').expr
        assert isinstance(node, BinOp)
        assert node.op == '+'
        assert isinstance(node.right, BinOp)
        assert node.right.op == '*'

    def test_power_right_assoc(self):
        # 2**3**2 == 2**(3**2)
        node = first('2**3**2').expr
        assert isinstance(node, BinOp)
        assert node.op == '**'
        assert isinstance(node.right, BinOp)
        assert node.right.op == '**'

    def test_unary_minus(self):
        node = first('-5').expr
        assert isinstance(node, UnaryOp)
        assert node.op == '-'

    def test_parentheses(self):
        # (1 + 2) * 3
        node = first('(1 + 2) * 3').expr
        assert node.op == '*'
        assert isinstance(node.left, BinOp)
        assert node.left.op == '+'


# ---------------------------------------------------------------------------
# Comparison and logical
# ---------------------------------------------------------------------------

class TestLogical:
    def test_comparison(self):
        node = first('x > 5').expr
        assert isinstance(node, BinOp)
        assert node.op == '>'

    def test_and(self):
        node = first('a and b').expr
        assert isinstance(node, BinOp)
        assert node.op == 'and'

    def test_or(self):
        node = first('a or b').expr
        assert node.op == 'or'

    def test_not(self):
        node = first('not x').expr
        assert isinstance(node, UnaryOp)
        assert node.op == 'not'


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------

class TestControlFlow:
    def test_if(self):
        node = first('if x > 0 { var y = 1 }')
        assert isinstance(node, If)
        assert isinstance(node.condition, BinOp)
        assert len(node.body) == 1

    def test_if_else(self):
        src = 'if x > 0 { var y = 1 } else { var y = 0 }'
        node = first(src)
        assert isinstance(node, If)
        assert node.else_body is not None

    def test_while(self):
        node = first('while i < 10 { i = i + 1 }')
        assert isinstance(node, While)

    def test_for(self):
        node = first('for x in [1, 2, 3] { print(x) }')
        assert isinstance(node, For)
        assert node.var == 'x'
        assert isinstance(node.iterable, VectorLiteral)

    def test_break(self):
        prog = parse('while true { break }')
        while_node = prog.body[0]
        assert isinstance(while_node.body[0], Break)

    def test_continue(self):
        prog = parse('while true { continue }')
        assert isinstance(prog.body[0].body[0], Continue)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

class TestFunctions:
    def test_func_def(self):
        src = 'fn add(a: int, b: int) -> int { return a + b }'
        node = first(src)
        assert isinstance(node, FuncDef)
        assert node.name == 'add'
        assert len(node.params) == 2
        assert node.return_type == 'int'

    def test_func_call(self):
        node = first('add(1, 2)').expr
        assert isinstance(node, FuncCall)
        assert node.name == 'add'
        assert len(node.args) == 2

    def test_return_stmt(self):
        prog = parse('fn f() -> int { return 42 }')
        func = prog.body[0]
        ret = func.body[0]
        assert isinstance(ret, Return)
        assert isinstance(ret.value, IntLiteral)

    def test_recursive_call(self):
        src = 'fn fib(n: int) -> int { return fib(n - 1) + fib(n - 2) }'
        node = first(src)
        assert isinstance(node, FuncDef)


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class TestAssignment:
    def test_simple_assign(self):
        node = first('x = 42')
        assert isinstance(node, Assign)
        assert node.name == 'x'

    def test_index_assign(self):
        node = first('v[0] = 99')
        assert isinstance(node, IndexAssign)
        assert node.name == 'v'


# ---------------------------------------------------------------------------
# Vectors and matrices
# ---------------------------------------------------------------------------

class TestVectors:
    def test_empty_vector(self):
        node = first('[]').expr
        assert isinstance(node, VectorLiteral)
        assert len(node.elements) == 0

    def test_int_vector(self):
        node = first('[1, 2, 3]').expr
        assert isinstance(node, VectorLiteral)
        assert len(node.elements) == 3

    def test_matrix(self):
        node = first('[[1, 2], [3, 4]]').expr
        assert isinstance(node, MatrixLiteral)
        assert len(node.rows) == 2

    def test_vector_add(self):
        node = first('v1 + v2').expr
        assert isinstance(node, BinOp)
        assert node.op == '+'

    def test_matmul(self):
        node = first('A @ B').expr
        assert isinstance(node, BinOp)
        assert node.op == '@'

    def test_transpose(self):
        node = first('T(A)').expr
        assert isinstance(node, FuncCall)
        assert node.name == 'transpose'

    def test_index_access(self):
        node = first('v[0]').expr
        assert isinstance(node, IndexAccess)


# ---------------------------------------------------------------------------
# Symbolic differentiation
# ---------------------------------------------------------------------------

class TestSymbolic:
    def test_sym_func(self):
        node = first('sym f(x) = x**2 + 1')
        assert isinstance(node, SymbolicFunc)
        assert node.name == 'f'
        assert node.params == ['x']

    def test_derivative(self):
        node = first('d/dx(x**2)').expr
        assert isinstance(node, Derivative)
        assert node.variable == 'x'

    def test_eval_expr(self):
        node = first('eval(df, x=2.0)').expr
        assert isinstance(node, SymbolicEval)
        assert len(node.bindings) == 1
        assert node.bindings[0][0] == 'x'


# ---------------------------------------------------------------------------
# Print statement
# ---------------------------------------------------------------------------

class TestPrint:
    def test_print_stmt(self):
        node = first('print("hello")')
        assert isinstance(node, ExprStatement)
        assert isinstance(node.expr, FuncCall)
        assert node.expr.name == 'print'


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestParseErrors:
    def test_missing_rbrace(self):
        with pytest.raises(ParseError):
            parse('if x > 0 { var y = 1')

    def test_missing_rparen(self):
        with pytest.raises(ParseError):
            parse('fn f(x { return x }')

    def test_unexpected_token(self):
        with pytest.raises(ParseError):
            parse('var = 10')   # missing identifier


# ---------------------------------------------------------------------------
# Example files round-trip (parse without crashing)
# ---------------------------------------------------------------------------

class TestExampleFiles:
    def _parse_file(self, name):
        path = os.path.join(os.path.dirname(__file__), '..', 'examples', name)
        with open(path, encoding='utf-8') as f:
            return parse(f.read())

    def test_fibonacci_parses(self):
        prog = self._parse_file('fibonacci.vect')
        assert len(prog.body) > 0

    def test_control_flow_parses(self):
        prog = self._parse_file('control_flow.vect')
        assert len(prog.body) > 0

    def test_linear_system_parses(self):
        prog = self._parse_file('linear_system.vect')
        assert len(prog.body) > 0

    def test_symbolic_derivative_parses(self):
        prog = self._parse_file('symbolic_derivative.vect')
        assert len(prog.body) > 0

    def test_showcase_parses(self):
        prog = self._parse_file('showcase.vect')
        assert len(prog.body) > 0
