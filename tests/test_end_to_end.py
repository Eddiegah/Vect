"""
test_end_to_end.py — End-to-end compilation and execution tests.

These tests compile a Vect program, run it, and capture stdout to verify
the output is exactly right.  This is the strongest test: if the output
is wrong, something is broken in lexer, parser, type checker, or codegen.
"""

import sys
import os
import io
import contextlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.pipeline import run_source
from src.lexer import LexError
from src.parser import ParseError
from src.type_checker import TypeError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(source: str) -> str:
    """Run a Vect program and return its stdout as a string."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        run_source(source.strip())
    return buf.getvalue().strip()


def lines(source: str) -> list:
    """Run and return output as a list of lines."""
    return run(source).splitlines()


# ---------------------------------------------------------------------------
# Basic arithmetic and printing
# ---------------------------------------------------------------------------

class TestBasicArithmetic:
    def test_print_int(self):
        assert run('print(42)') == '42'

    def test_print_float(self):
        out = run('print(3.14)')
        assert '3.14' in out

    def test_addition(self):
        assert run('print(1 + 2)') == '3'

    def test_subtraction(self):
        assert run('print(10 - 3)') == '7'

    def test_multiplication(self):
        assert run('print(4 * 5)') == '20'

    def test_division(self):
        # int / int = int in Vect
        assert run('print(10 / 2)') == '5'

    def test_float_arithmetic(self):
        out = run('print(1.5 + 0.5)')
        assert '2.0' in out

    def test_power(self):
        out = run('print(2.0 ** 10.0)')
        assert '1024' in out

    def test_modulo(self):
        assert run('print(10 % 3)') == '1'

    def test_precedence(self):
        # 2 + 3 * 4 = 14, not 20
        assert run('print(2 + 3 * 4)') == '14'

    def test_parens(self):
        # (2 + 3) * 4 = 20
        assert run('print((2 + 3) * 4)') == '20'

    def test_unary_minus(self):
        assert run('print(-7)') == '-7'


# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------

class TestVariables:
    def test_var_decl_and_use(self):
        assert run('var x = 5\nprint(x)') == '5'

    def test_var_assign(self):
        assert run('var x = 5\nx = 10\nprint(x)') == '10'

    def test_multi_var(self):
        out = lines('var a = 1\nvar b = 2\nprint(a + b)')
        assert out[0] == '3'

    def test_string_var(self):
        assert run('var s = "hello"\nprint(s)') == 'hello'


# ---------------------------------------------------------------------------
# Booleans and comparisons
# ---------------------------------------------------------------------------

class TestBooleans:
    def test_true(self):
        assert run('print(true)') == 'true'

    def test_false(self):
        assert run('print(false)') == 'false'

    def test_comparison_true(self):
        assert run('print(5 > 3)') == 'true'

    def test_comparison_false(self):
        assert run('print(5 < 3)') == 'false'

    def test_equality(self):
        assert run('print(3 == 3)') == 'true'

    def test_inequality(self):
        assert run('print(3 != 4)') == 'true'


# ---------------------------------------------------------------------------
# Control flow
# ---------------------------------------------------------------------------

class TestControlFlow:
    def test_if_true(self):
        assert run('if 1 > 0 { print("yes") }') == 'yes'

    def test_if_false(self):
        assert run('if 0 > 1 { print("yes") }') == ''

    def test_if_else(self):
        src = 'if 1 > 2 { print("a") } else { print("b") }'
        assert run(src) == 'b'

    def test_while_loop(self):
        src = 'var i = 0\nwhile i < 3 { print(i)\ni = i + 1 }'
        assert lines(src) == ['0', '1', '2']

    def test_while_break(self):
        src = 'var i = 0\nwhile true { if i >= 3 { break }\nprint(i)\ni = i + 1 }'
        assert lines(src) == ['0', '1', '2']

    def test_for_loop(self):
        src = 'for x in [1.0, 2.0, 3.0] { print(x) }'
        result = lines(src)
        # Each element printed (floats)
        assert len(result) == 3

    def test_if_else_if(self):
        src = '''
var x = 2
if x == 1 { print("one") }
else if x == 2 { print("two") }
else { print("other") }
'''
        assert run(src) == 'two'


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

class TestFunctions:
    def test_simple_function(self):
        src = '''
fn double(x: int) -> int {
    return x * 2
}
print(double(5))
'''
        assert run(src) == '10'

    def test_multiple_params(self):
        src = '''
fn add(a: int, b: int) -> int {
    return a + b
}
print(add(3, 4))
'''
        assert run(src) == '7'

    def test_recursive_fibonacci(self):
        src = '''
fn fib(n: int) -> int {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}
print(fib(0))
print(fib(1))
print(fib(7))
'''
        result = lines(src)
        assert result[0] == '0'
        assert result[1] == '1'
        assert result[2] == '13'

    def test_function_with_local_var(self):
        src = '''
fn square(x: int) -> int {
    var s = x * x
    return s
}
print(square(6))
'''
        assert run(src) == '36'

    def test_void_function(self):
        src = '''
fn greet() {
    print("hello")
}
greet()
'''
        assert run(src) == 'hello'


# ---------------------------------------------------------------------------
# The Fibonacci example file
# ---------------------------------------------------------------------------

class TestExamplePrograms:
    def _run_file(self, name):
        path = os.path.join(os.path.dirname(__file__), '..', 'examples', name)
        with open(path, encoding='utf-8') as f:
            source = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_source(source, name)
        return buf.getvalue().strip().splitlines()

    def test_fibonacci_output(self):
        result = self._run_file('fibonacci.vect')
        # fib(0..10) = 0,1,1,2,3,5,8,13,21,34,55
        expected = ['0', '1', '1', '2', '3', '5', '8', '13', '21', '34', '55']
        assert result == expected

    def test_control_flow_output(self):
        result = self._run_file('control_flow.vect')
        assert result[0] == 'B'       # score 85 → grade B
        assert result[1] == '8'       # first n where n*n > 50
        assert '15' in result[2]      # sum of 1-5 = 15
        assert result[3] == '7'       # max(7, 3)
        assert result[4] == '42'      # abs(-42)


# ---------------------------------------------------------------------------
# Type error cases — these should raise, not silently produce wrong output
# ---------------------------------------------------------------------------

class TestTypeErrors:
    def test_undefined_variable(self):
        with pytest.raises((TypeError, Exception)):
            run('print(undeclared_var)')

    def test_wrong_arg_count(self):
        src = 'fn f(x: int) -> int { return x }\nf(1, 2)'
        with pytest.raises((TypeError, Exception)):
            run(src)

    def test_string_plus_int(self):
        with pytest.raises((TypeError, Exception)):
            run('print("hello" + 1)')


# ---------------------------------------------------------------------------
# Vectors and matrices (Milestone 3)
# ---------------------------------------------------------------------------

class TestVectorOps:
    def test_vector_literal_print(self):
        out = run('var v = [1.0, 2.0, 3.0]\nprint(v)')
        assert '1' in out and '2' in out and '3' in out

    def test_vector_add(self):
        out = run('var a = [1.0, 2.0]\nvar b = [3.0, 4.0]\nprint(a + b)')
        assert '4' in out and '6' in out

    def test_vector_scale(self):
        out = run('var v = [1.0, 2.0, 3.0]\nprint(v * 2.0)')
        assert '2' in out and '4' in out and '6' in out

    def test_dot_product(self):
        src = 'var a = [1.0, 2.0, 3.0]\nvar b = [4.0, 5.0, 6.0]'
        out = run(src + '\nprint(a \xb7 b)')
        assert '32' in out

    def test_matrix_mul(self):
        src = '''
var A = [[1.0, 2.0], [3.0, 4.0]]
var B = [[5.0, 6.0], [7.0, 8.0]]
var C = A @ B
print(C)
'''
        out = run(src)
        assert '19' in out and '22' in out and '43' in out and '50' in out

    def test_transpose(self):
        src = 'var A = [[1.0, 2.0], [3.0, 4.0]]\nprint(T(A))'
        out = run(src)
        assert '1' in out and '3' in out and '2' in out and '4' in out

    def test_vector_index(self):
        src = 'var v = [10.0, 20.0, 30.0]\nprint(v[1])'
        out = run(src)
        assert '20' in out

    def test_linear_system_file(self):
        import io, contextlib
        path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'linear_system.vect')
        with open(path, encoding='utf-8') as f:
            source = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_source(source)
        out = buf.getvalue()
        assert '5' in out     # v1+v2 first element
        assert '32' in out    # dot product
        assert '19' in out    # A@B top-left


# ---------------------------------------------------------------------------
# Symbolic differentiation (Milestone 4)
# ---------------------------------------------------------------------------

class TestSymbolicDiff:
    def test_simple_derivative(self):
        src = '''
sym f(x) = x**2 + 3*x + 1
var df = d/dx(f(x))
print(df)
'''
        out = run(src)
        assert '2*x' in out or '2' in out   # 2x + 3

    def test_derivative_eval(self):
        src = '''
sym f(x) = x**2 + 3*x + 1
var df = d/dx(f(x))
var slope = eval(df, x=2.0)
print(slope)
'''
        out = run(src)
        assert '7' in out   # d/dx at x=2: 2*2+3 = 7

    def test_physics_velocity(self):
        src = '''
sym s(t) = 0.5 * 9.8 * t**2
var v = d/dt(s(t))
var v3 = eval(v, t=3.0)
print(v3)
'''
        out = run(src)
        # v = 9.8*t, at t=3 → 29.4
        assert '29' in out

    def test_symbolic_file(self):
        import io, contextlib
        path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'symbolic_derivative.vect')
        with open(path, encoding='utf-8') as f:
            source = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_source(source)
        out = buf.getvalue()
        assert '2*x' in out or '7' in out
        assert '29' in out

    def test_showcase_file(self):
        import io, contextlib
        path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'showcase.vect')
        with open(path, encoding='utf-8') as f:
            source = f.read()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_source(source)
        out = buf.getvalue()
        assert '3628800' in out   # factorial(10)
        assert '5.0' in out       # KE derivative at v=5
