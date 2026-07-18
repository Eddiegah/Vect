"""
ast_nodes.py — AST node definitions for the Vect language.

Every construct in a Vect program is represented as one of these dataclasses.
The parser builds a tree of these nodes; the type checker and code generator
then walk that tree.

Each node carries a (line, col) position so error messages can point at the
right place in the source file.

Design note: Python dataclasses require that fields WITH defaults come after
fields WITHOUT defaults.  Our Node base class has line/col with defaults (0),
which means ALL subclass fields must also have defaults, OR we restructure.

We use a simple approach: every node dataclass declares its own line/col
fields explicitly (with default=0) rather than inheriting them, so Python's
MRO ordering never causes a conflict.  A NodeMixin provides the type identity.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


# Shared sentinel — nothing fancy, just lets isinstance checks work.
class Node:
    """Marker base class for all AST nodes."""
    pass


# Helper that adds line/col with defaults to any node dataclass.
# We define these on each class explicitly below to keep things readable.

def _node(cls):
    """Decorator that ensures a Node subclass has line and col fields."""
    return cls


# ---------------------------------------------------------------------------
# Literals
# ---------------------------------------------------------------------------

@dataclass
class IntLiteral(Node):
    value: int
    line: int = 0
    col: int = 0


@dataclass
class FloatLiteral(Node):
    value: float
    line: int = 0
    col: int = 0


@dataclass
class BoolLiteral(Node):
    value: bool
    line: int = 0
    col: int = 0


@dataclass
class StringLiteral(Node):
    value: str
    line: int = 0
    col: int = 0


@dataclass
class VectorLiteral(Node):
    """A flat vector literal like [1, 2, 3]."""
    elements: List[Any]
    line: int = 0
    col: int = 0


@dataclass
class MatrixLiteral(Node):
    """A matrix literal like [[1,2],[3,4]] — a list of row vectors."""
    rows: List[Any]
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Identifiers and access
# ---------------------------------------------------------------------------

@dataclass
class Identifier(Node):
    name: str
    line: int = 0
    col: int = 0


@dataclass
class IndexAccess(Node):
    """Subscript access: expr[index]"""
    obj: Any
    index: Any
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

@dataclass
class BinOp(Node):
    """Binary operation: left op right.
    op is a string like '+', '-', '*', '/', '%', '**',
    '==', '!=', '<', '<=', '>', '>=', 'and', 'or',
    '@' (matrix multiply), '·' (dot product).
    """
    op: str
    left: Any
    right: Any
    line: int = 0
    col: int = 0


@dataclass
class UnaryOp(Node):
    """Unary operation: op expr.
    op is '-' (negation) or 'not'.
    """
    op: str
    operand: Any
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Symbolic differentiation (the signature feature)
# ---------------------------------------------------------------------------

@dataclass
class Derivative(Node):
    """
    Symbolic derivative expression.

    Syntax: d/dx(expr)   or   d/dt(expr)  etc.

    variable: the differentiation variable name (e.g. 'x')
    expr:     the expression to differentiate
    """
    variable: str
    expr: Any
    line: int = 0
    col: int = 0


@dataclass
class SymbolicEval(Node):
    """
    Evaluate a symbolic expression at a concrete value.

    Syntax: eval(expr, x=2.0)
    This lets users take a symbolic result and compute a number from it.
    """
    expr: Any
    bindings: List[tuple]   # list of (name: str, value_expr: Node)
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Statements
# ---------------------------------------------------------------------------

@dataclass
class VarDecl(Node):
    """Variable declaration: var name = expr  or  var name: type = expr"""
    name: str
    type_annotation: Optional[str]
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class Assign(Node):
    """Assignment to an existing variable: name = expr"""
    name: str
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class IndexAssign(Node):
    """Subscript assignment: name[index] = expr"""
    name: str
    index: Any
    value: Any
    line: int = 0
    col: int = 0


@dataclass
class If(Node):
    """if condition { body } else { else_body }"""
    condition: Any
    body: List[Any]
    else_body: Optional[List[Any]]
    line: int = 0
    col: int = 0


@dataclass
class While(Node):
    """while condition { body }"""
    condition: Any
    body: List[Any]
    line: int = 0
    col: int = 0


@dataclass
class For(Node):
    """for var in iterable { body }"""
    var: str
    iterable: Any
    body: List[Any]
    line: int = 0
    col: int = 0


@dataclass
class Return(Node):
    """return expr"""
    value: Optional[Any]
    line: int = 0
    col: int = 0


@dataclass
class Break(Node):
    line: int = 0
    col: int = 0


@dataclass
class Continue(Node):
    line: int = 0
    col: int = 0


@dataclass
class ExprStatement(Node):
    """A statement that is just an expression (e.g. a function call)."""
    expr: Any
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------

@dataclass
class Param(Node):
    """A single function parameter: name or name: type"""
    name: str
    type_annotation: Optional[str]
    line: int = 0
    col: int = 0


@dataclass
class FuncDef(Node):
    """
    Function definition.

    fn name(params) -> return_type { body }
    or
    fn name(params) { body }   (void return)
    """
    name: str
    params: List[Any]
    return_type: Optional[str]
    body: List[Any]
    line: int = 0
    col: int = 0


@dataclass
class FuncCall(Node):
    """Function call: name(args)"""
    name: str
    args: List[Any]
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Symbolic function definition
# ---------------------------------------------------------------------------

@dataclass
class SymbolicFunc(Node):
    """
    A symbolic math function definition.

    Syntax:  sym f(x) = x**2 + 3*x

    This tells Vect that f is a symbolic expression, not a compiled function.
    Under the hood it uses sympy, but the user never sees that.
    """
    name: str
    params: List[str]        # symbolic variable names
    expr: Any                # the symbolic expression (AST, not compiled)
    line: int = 0
    col: int = 0


# ---------------------------------------------------------------------------
# Top-level program
# ---------------------------------------------------------------------------

@dataclass
class Program(Node):
    """The root node: a list of top-level statements/definitions."""
    body: List[Any]
    line: int = 0
    col: int = 0


@dataclass
class Import(Node):
    """
    Import declaration: import "path/to/file.vect"

    At compile time, the pipeline reads the imported file, parses it,
    and injects its fn/sym definitions into the current program.
    Only fn and sym declarations are exported — variables stay local.
    """
    path: str       # the string literal path
    line: int = 0
    col: int = 0
