"""
type_checker.py — Static type checker for Vect.

Walks the AST and enforces type rules before code generation runs.
The goal is clear, actionable error messages — every TypeError points
at the exact line/col and explains what went wrong in plain English.

Type system (v1):
  int    — 64-bit integer
  float  — 64-bit float
  bool   — boolean
  string — text string
  vec    — numeric vector (any length)
  mat    — numeric matrix (any shape)
  void   — no return value
  sym    — symbolic expression (not runtime-compiled, handled separately)

Promotion rule: int op float → float  (e.g. 1 + 2.0 is legal, yields float)
"""

from typing import Dict, List, Optional, Tuple
from .ast_nodes import *


# ---------------------------------------------------------------------------
# Type error
# ---------------------------------------------------------------------------

class TypeError(Exception):
    """A type error with source position and a plain-English message."""
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
        super().__init__(f"Type error at line {line}, col {col}: {msg}")


# ---------------------------------------------------------------------------
# Type constants
# ---------------------------------------------------------------------------

INT    = 'int'
FLOAT  = 'float'
BOOL   = 'bool'
STRING = 'string'
VEC    = 'vec'
MAT    = 'mat'
VOID   = 'void'
SYM    = 'sym'

NUMERIC = {INT, FLOAT}


def is_numeric(t: str) -> bool:
    return t in NUMERIC

def promote(a: str, b: str) -> str:
    """Return the result type when combining two numeric types.
    int + int → int,  int + float → float,  float + float → float.
    """
    if a == FLOAT or b == FLOAT:
        return FLOAT
    return INT


# ---------------------------------------------------------------------------
# Environment (symbol table)
# ---------------------------------------------------------------------------

class Env:
    """
    A scoped symbol table.  Each scope is a dict mapping name → type.
    The outer chain is accessed by following self.parent.
    """
    def __init__(self, parent: Optional['Env'] = None):
        self.parent = parent
        self.vars: Dict[str, str] = {}

    def define(self, name: str, typ: str):
        self.vars[name] = typ

    def lookup(self, name: str) -> Optional[str]:
        if name in self.vars:
            return self.vars[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def assign(self, name: str, typ: str) -> bool:
        """Update an existing variable's type.  Returns False if not found."""
        if name in self.vars:
            self.vars[name] = typ
            return True
        if self.parent:
            return self.parent.assign(name, typ)
        return False


# ---------------------------------------------------------------------------
# Built-in functions
# ---------------------------------------------------------------------------

# Maps function name → (param_types, return_type)
# param_types = None means "variadic / any args"
BUILTINS: Dict[str, Tuple] = {
    'print':     (None, VOID),
    'input':     ([], STRING),
    'len':       (None, INT),
    'sqrt':      ([FLOAT], FLOAT),
    'sin':       ([FLOAT], FLOAT),
    'cos':       ([FLOAT], FLOAT),
    'tan':       ([FLOAT], FLOAT),
    'abs':       (None, FLOAT),
    'floor':     ([FLOAT], INT),
    'ceil':      ([FLOAT], INT),
    'int':       (None, INT),
    'float':     (None, FLOAT),
    'str':       (None, STRING),
    'range':     (None, VEC),
    'transpose': ([MAT], MAT),
    'dot':       ([VEC, VEC], FLOAT),
    'zeros':     (None, VEC),
    'ones':      (None, VEC),
}


# ---------------------------------------------------------------------------
# Type checker
# ---------------------------------------------------------------------------

class TypeChecker:
    def __init__(self):
        self.global_env = Env()
        # Register built-in functions
        for name, (params, ret) in BUILTINS.items():
            self.global_env.define(name, f'fn:{ret}')
        # Map of user-defined function signatures: name → (param_types, return_type)
        self.functions: Dict[str, Tuple[List[str], str]] = {}
        # Track expected return type when inside a function
        self._return_type_stack: List[str] = []
        # Symbolic function names (for special handling in codegen)
        self.symbolic_funcs: set = set()

    def check(self, program: Program) -> None:
        """
        Type-check a complete program.
        Raises TypeError on the first violation found.
        """
        # First pass: register all top-level function signatures
        # so functions can call each other regardless of definition order.
        for node in program.body:
            if isinstance(node, FuncDef):
                self._register_func(node)
            elif isinstance(node, SymbolicFunc):
                self.symbolic_funcs.add(node.name)
                self.global_env.define(node.name, SYM)

        # Second pass: check all statements
        for node in program.body:
            self._check_stmt(node, self.global_env)

    def _register_func(self, node: FuncDef):
        """Record a function's signature in the environment."""
        param_types = []
        for p in node.params:
            t = p.type_annotation or FLOAT  # default to float if unannotated
            param_types.append(t)
        ret = node.return_type or VOID
        self.functions[node.name] = (param_types, ret)
        self.global_env.define(node.name, f'fn:{ret}')

    # ------------------------------------------------------------------
    # Statement checking
    # ------------------------------------------------------------------

    def _check_stmt(self, node: Node, env: Env) -> None:
        if isinstance(node, VarDecl):
            self._check_var_decl(node, env)
        elif isinstance(node, Assign):
            self._check_assign(node, env)
        elif isinstance(node, IndexAssign):
            self._check_index_assign(node, env)
        elif isinstance(node, FuncDef):
            self._check_func_def(node, env)
        elif isinstance(node, SymbolicFunc):
            # Symbolic functions are handled at runtime by sympy; just record them.
            self.symbolic_funcs.add(node.name)
            env.define(node.name, SYM)
        elif isinstance(node, If):
            self._check_if(node, env)
        elif isinstance(node, While):
            self._check_while(node, env)
        elif isinstance(node, For):
            self._check_for(node, env)
        elif isinstance(node, Return):
            self._check_return(node, env)
        elif isinstance(node, ExprStatement):
            self._infer(node.expr, env)
        elif isinstance(node, (Break, Continue)):
            pass  # always valid (parser ensures they're inside loops)
        else:
            raise TypeError(
                f"Unknown statement type: {type(node).__name__}",
                getattr(node, 'line', 0), getattr(node, 'col', 0)
            )

    def _check_var_decl(self, node: VarDecl, env: Env):
        val_type = self._infer(node.value, env)
        ann = node.type_annotation

        if ann:
            # Normalize annotation
            ann = ann.lower() if ann not in (VEC, MAT, SYM) else ann
            # Allow int literal assigned to float variable (widening)
            if ann == FLOAT and val_type == INT:
                val_type = FLOAT
            elif ann == INT and val_type == FLOAT:
                raise TypeError(
                    f"Variable '{node.name}' is declared as 'int' but "
                    f"the value is a float. Use 'int(...)' to convert explicitly, "
                    f"or declare it as 'float'.",
                    node.line, node.col
                )
            elif ann not in (val_type, SYM) and not (ann == VEC and val_type == VEC) \
                    and not (ann == MAT and val_type == MAT):
                if val_type not in (VEC, MAT, SYM):  # be lenient with container types
                    raise TypeError(
                        f"Variable '{node.name}' declared as '{ann}' "
                        f"but assigned a '{val_type}' value.",
                        node.line, node.col
                    )
            val_type = ann

        env.define(node.name, val_type)

    def _check_assign(self, node: Assign, env: Env):
        existing = env.lookup(node.name)
        if existing is None:
            raise TypeError(
                f"'{node.name}' is not defined. "
                f"Did you mean to declare it with 'var {node.name} = ...'?",
                node.line, node.col
            )
        val_type = self._infer(node.value, env)
        # Allow int→float promotion on reassignment
        if existing == FLOAT and val_type == INT:
            val_type = FLOAT
        if existing != val_type and existing not in (VEC, MAT, SYM) \
                and val_type not in (VEC, MAT, SYM):
            raise TypeError(
                f"Cannot assign a '{val_type}' value to '{node.name}' "
                f"which has type '{existing}'.",
                node.line, node.col
            )
        env.assign(node.name, val_type)

    def _check_index_assign(self, node: IndexAssign, env: Env):
        obj_type = env.lookup(node.name)
        if obj_type is None:
            raise TypeError(f"'{node.name}' is not defined.", node.line, node.col)
        idx_type = self._infer(node.index, env)
        if idx_type != INT:
            raise TypeError(
                f"Vector/matrix index must be an int, but got '{idx_type}'.",
                node.index.line, node.index.col
            )

    def _check_func_def(self, node: FuncDef, env: Env):
        param_types, ret_type = self.functions.get(node.name, ([], VOID))
        func_env = Env(parent=env)
        for p, t in zip(node.params, param_types):
            func_env.define(p.name, t)
        self._return_type_stack.append(ret_type)
        for stmt in node.body:
            self._check_stmt(stmt, func_env)
        self._return_type_stack.pop()

    def _check_if(self, node: If, env: Env):
        cond_type = self._infer(node.condition, env)
        if cond_type != BOOL and cond_type not in NUMERIC:
            raise TypeError(
                f"'if' condition must be a bool or numeric expression, "
                f"but got '{cond_type}'.",
                node.condition.line, node.condition.col
            )
        body_env = Env(parent=env)
        for stmt in node.body:
            self._check_stmt(stmt, body_env)
        if node.else_body:
            else_env = Env(parent=env)
            for stmt in node.else_body:
                self._check_stmt(stmt, else_env)

    def _check_while(self, node: While, env: Env):
        cond_type = self._infer(node.condition, env)
        if cond_type != BOOL and cond_type not in NUMERIC:
            raise TypeError(
                f"'while' condition must be a bool or numeric expression, "
                f"but got '{cond_type}'.",
                node.condition.line, node.condition.col
            )
        body_env = Env(parent=env)
        for stmt in node.body:
            self._check_stmt(stmt, body_env)

    def _check_for(self, node: For, env: Env):
        iter_type = self._infer(node.iterable, env)
        if iter_type not in (VEC, MAT, STRING):
            raise TypeError(
                f"'for' loop can only iterate over vec, mat, or string, "
                f"but got '{iter_type}'.",
                node.iterable.line, node.iterable.col
            )
        body_env = Env(parent=env)
        # The loop variable type depends on what we're iterating over
        elem_type = FLOAT if iter_type in (VEC, MAT) else STRING
        body_env.define(node.var, elem_type)
        for stmt in node.body:
            self._check_stmt(stmt, body_env)

    def _check_return(self, node: Return, env: Env):
        if not self._return_type_stack:
            raise TypeError(
                "'return' used outside of a function.",
                node.line, node.col
            )
        expected = self._return_type_stack[-1]
        if node.value is None:
            if expected != VOID:
                raise TypeError(
                    f"Function expects to return '{expected}' but has an empty return.",
                    node.line, node.col
                )
            return
        actual = self._infer(node.value, env)
        if expected == VOID:
            raise TypeError(
                f"Function has no return type but is returning a '{actual}' value.",
                node.line, node.col
            )
        # Allow int→float promotion
        if expected == FLOAT and actual == INT:
            return
        if actual != expected and expected not in (VEC, MAT, SYM) \
                and actual not in (VEC, MAT, SYM):
            raise TypeError(
                f"Function should return '{expected}' but this return "
                f"statement returns '{actual}'.",
                node.line, node.col
            )

    # ------------------------------------------------------------------
    # Expression type inference
    # ------------------------------------------------------------------

    def _infer(self, node: Node, env: Env) -> str:
        """Return the type of an expression, or raise TypeError."""

        if isinstance(node, IntLiteral):
            return INT

        if isinstance(node, FloatLiteral):
            return FLOAT

        if isinstance(node, BoolLiteral):
            return BOOL

        if isinstance(node, StringLiteral):
            return STRING

        if isinstance(node, Identifier):
            t = env.lookup(node.name)
            if t is None:
                raise TypeError(
                    f"'{node.name}' is not defined. "
                    f"Check the spelling or make sure you declared it with 'var'.",
                    node.line, node.col
                )
            return t

        if isinstance(node, VectorLiteral):
            for elem in node.elements:
                et = self._infer(elem, env)
                if et not in NUMERIC and et != VEC:
                    raise TypeError(
                        f"Vector elements must be numeric (int or float), "
                        f"but found a '{et}' element.",
                        elem.line, elem.col
                    )
            return VEC

        if isinstance(node, MatrixLiteral):
            for row in node.rows:
                rt = self._infer(row, env)
                if rt != VEC:
                    raise TypeError(
                        f"Matrix rows must be vectors, but found '{rt}'.",
                        row.line, row.col
                    )
            return MAT

        if isinstance(node, BinOp):
            return self._infer_binop(node, env)

        if isinstance(node, UnaryOp):
            return self._infer_unaryop(node, env)

        if isinstance(node, FuncCall):
            return self._infer_call(node, env)

        if isinstance(node, IndexAccess):
            return self._infer_index(node, env)

        if isinstance(node, Derivative):
            return SYM

        if isinstance(node, SymbolicEval):
            return FLOAT

        # Symbolic functions return SYM when called in symbolic context
        if isinstance(node, SymbolicFunc):
            return SYM

        raise TypeError(
            f"Cannot determine the type of '{type(node).__name__}'. "
            f"This might be a compiler bug.",
            getattr(node, 'line', 0), getattr(node, 'col', 0)
        )

    def _infer_binop(self, node: BinOp, env: Env) -> str:
        left_t  = self._infer(node.left, env)
        right_t = self._infer(node.right, env)
        op = node.op

        # --- Vector/matrix ops ---
        if op in ('+', '-', '*'):
            if left_t == VEC and right_t == VEC:
                return VEC
            if left_t == MAT and right_t == MAT:
                return MAT
            if left_t == VEC and right_t in NUMERIC:
                return VEC
            if left_t in NUMERIC and right_t == VEC:
                return VEC
            if left_t == MAT and right_t in NUMERIC:
                return MAT
            if left_t in NUMERIC and right_t == MAT:
                return MAT

        if op == '@':   # matrix multiply
            if left_t == MAT and right_t == MAT:
                return MAT
            if left_t == MAT and right_t == VEC:
                return VEC
            raise TypeError(
                f"'@' (matrix multiply) requires matrix operands, "
                f"but got '{left_t}' and '{right_t}'.",
                node.line, node.col
            )

        if op == '·':   # dot product
            if left_t == VEC and right_t == VEC:
                return FLOAT
            raise TypeError(
                f"'·' (dot product) requires two vectors, "
                f"but got '{left_t}' and '{right_t}'.",
                node.line, node.col
            )

        # --- Numeric ops ---
        if op in ('+', '-', '*', '/', '%', '**'):
            if left_t == STRING and right_t == STRING and op == '+':
                return STRING   # string concatenation
            if left_t not in NUMERIC or right_t not in NUMERIC:
                # Give a specific message for common mistakes
                if left_t == STRING or right_t == STRING:
                    non_str = right_t if left_t == STRING else left_t
                    raise TypeError(
                        f"Cannot use '{op}' between a string and a '{non_str}'. "
                        f"To concatenate, convert to string first with str(...).",
                        node.line, node.col
                    )
                raise TypeError(
                    f"Operator '{op}' cannot be used with '{left_t}' and '{right_t}'.",
                    node.line, node.col
                )
            return promote(left_t, right_t)

        # --- Comparison ops → bool ---
        if op in ('==', '!='):
            # equality works for all comparable types
            return BOOL

        if op in ('<', '<=', '>', '>='):
            if left_t not in NUMERIC or right_t not in NUMERIC:
                raise TypeError(
                    f"Comparison '{op}' requires numeric operands, "
                    f"but got '{left_t}' and '{right_t}'.",
                    node.line, node.col
                )
            return BOOL

        # --- Logical ops ---
        if op == 'and':
            if left_t != BOOL or right_t != BOOL:
                # Be lenient — numeric values are truthy in most languages
                pass
            return BOOL

        if op == 'or':
            return BOOL

        raise TypeError(
            f"Unknown binary operator '{op}'.",
            node.line, node.col
        )

    def _infer_unaryop(self, node: UnaryOp, env: Env) -> str:
        t = self._infer(node.operand, env)
        if node.op == '-':
            if t not in NUMERIC and t not in (VEC, MAT):
                raise TypeError(
                    f"Unary '-' requires a numeric value, but got '{t}'.",
                    node.line, node.col
                )
            return t
        if node.op == 'not':
            return BOOL
        raise TypeError(f"Unknown unary operator '{node.op}'.", node.line, node.col)

    def _infer_call(self, node: FuncCall, env: Env) -> str:
        name = node.name

        # Built-in: print is variadic, always void
        if name == 'print':
            for arg in node.args:
                self._infer(arg, env)
            return VOID

        # Built-in: input
        if name == 'input':
            return STRING

        # Built-in: range
        if name == 'range':
            return VEC

        # Built-in: transpose
        if name == 'transpose':
            if len(node.args) != 1:
                raise TypeError(
                    f"'transpose' takes exactly 1 argument, got {len(node.args)}.",
                    node.line, node.col
                )
            arg_t = self._infer(node.args[0], env)
            if arg_t not in (MAT, VEC):
                raise TypeError(
                    f"'transpose' requires a matrix or vector, but got '{arg_t}'.",
                    node.args[0].line, node.args[0].col
                )
            return MAT

        # Built-in math functions
        if name in ('sqrt', 'sin', 'cos', 'tan', 'abs', 'floor', 'ceil'):
            if len(node.args) != 1:
                raise TypeError(
                    f"'{name}' takes exactly 1 argument.", node.line, node.col
                )
            arg_t = self._infer(node.args[0], env)
            if arg_t not in NUMERIC:
                raise TypeError(
                    f"'{name}' requires a numeric argument, but got '{arg_t}'.",
                    node.args[0].line, node.args[0].col
                )
            return FLOAT if name not in ('floor', 'ceil') else INT

        # Type conversion builtins
        if name == 'int':
            if node.args:
                self._infer(node.args[0], env)
            return INT
        if name in ('float', 'str'):
            if node.args:
                self._infer(node.args[0], env)
            return FLOAT if name == 'float' else STRING

        # User-defined function
        if name in self.functions:
            param_types, ret_type = self.functions[name]
            if len(node.args) != len(param_types):
                raise TypeError(
                    f"Function '{name}' expects {len(param_types)} argument(s) "
                    f"but got {len(node.args)}.",
                    node.line, node.col
                )
            for i, (arg, expected_t) in enumerate(zip(node.args, param_types)):
                actual_t = self._infer(arg, env)
                if actual_t != expected_t:
                    # Allow int→float promotion
                    if expected_t == FLOAT and actual_t == INT:
                        continue
                    if expected_t in (VEC, MAT, SYM):
                        continue  # be lenient with container types
                    raise TypeError(
                        f"Argument {i+1} of '{name}' should be '{expected_t}' "
                        f"but got '{actual_t}'.",
                        arg.line, arg.col
                    )
            return ret_type

        # Symbolic function (calling sym f(x) as f(x) in a derivative context)
        if name in self.symbolic_funcs:
            return SYM

        # Unknown function
        t = env.lookup(name)
        if t and t.startswith('fn:'):
            return t[3:]

        raise TypeError(
            f"'{name}' is not defined. "
            f"Check the spelling or make sure you declared it with 'fn'.",
            node.line, node.col
        )

    def _infer_index(self, node: IndexAccess, env: Env) -> str:
        obj_t = self._infer(node.obj, env)
        idx_t = self._infer(node.index, env)
        if idx_t != INT:
            raise TypeError(
                f"Index must be an int, but got '{idx_t}'.",
                node.index.line, node.index.col
            )
        if obj_t == VEC:
            return FLOAT
        if obj_t == MAT:
            return VEC
        if obj_t == STRING:
            return STRING
        raise TypeError(
            f"Cannot index into a '{obj_t}'. Only vec, mat, and string support indexing.",
            node.obj.line, node.obj.col
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def type_check(program: Program) -> TypeChecker:
    """
    Run the type checker on a parsed program.
    Returns the TypeChecker (which has the function table etc.) on success,
    or raises TypeError with a clear message on failure.
    """
    checker = TypeChecker()
    checker.check(program)
    return checker
