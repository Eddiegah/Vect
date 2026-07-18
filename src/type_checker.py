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

from typing import Any, Dict, List, Optional, Tuple
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


class MultiTypeError(Exception):
    """Multiple type errors collected in one pass."""
    def __init__(self, errors: list):
        self.errors = errors
        lines = [str(e) for e in errors]
        super().__init__('\n'.join(lines))


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
        for name, (params, ret) in BUILTINS.items():
            self.global_env.define(name, f'fn:{ret}')
        self.functions: Dict[str, Tuple[List[str], str]] = {}
        self._return_type_stack: List[str] = []
        self.symbolic_funcs: set = set()
        self._func_nodes: Dict[str, Any] = {}   # name → FuncDef AST node

    def check(self, program: Program) -> None:
        """
        Type-check a complete program.
        Collects ALL errors across all top-level statements and raises
        MultiTypeError at the end if any were found. This means you see
        every problem at once instead of fixing them one by one.
        """
        # First pass: register all top-level function signatures
        for node in program.body:
            if isinstance(node, FuncDef):
                self._register_func(node)
            elif isinstance(node, SymbolicFunc):
                self.symbolic_funcs.add(node.name)
                self.global_env.define(node.name, SYM)

        # Second pass: check all statements, collecting errors
        errors = []
        for node in program.body:
            try:
                self._check_stmt(node, self.global_env)
            except MultiTypeError as e:
                errors.extend(e.errors)
            except TypeError as e:
                errors.append(e)
            except Exception as e:
                raise

        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise MultiTypeError(errors)

    def _register_func(self, node: FuncDef):
        """
        Record a function's signature in the environment.

        If parameters have annotations, use them directly.
        If a parameter has NO annotation, mark it as 'unknown' — it will
        be resolved when we see the first call to this function.
        """
        param_types = []
        for p in node.params:
            t = p.type_annotation if p.type_annotation else 'unknown'
            param_types.append(t)
        ret = node.return_type if node.return_type else 'unknown'
        self.functions[node.name] = (param_types, ret)
        self.global_env.define(node.name, f'fn:{ret}')
        # Store the AST node for re-checking after inference
        self._func_nodes[node.name] = node

    def _resolve_func_signature(self, name: str, arg_types: List[str]):
        """
        When a function with 'unknown' param types is first called,
        substitute the actual argument types and re-record the signature.
        Also infer the return type by type-checking the body with
        the inferred parameter types.
        """
        if name not in self._func_nodes:
            return
        node = self._func_nodes[name]
        param_types, ret = self.functions[name]

        # Replace 'unknown' params with inferred types from call site
        new_param_types = []
        for i, (pt, at) in enumerate(zip(param_types, arg_types)):
            if pt == 'unknown':
                new_param_types.append(at)
            else:
                new_param_types.append(pt)

        # Infer return type by type-checking the body with resolved params
        if ret == 'unknown':
            func_env = Env(parent=self.global_env)
            for p, t in zip(node.params, new_param_types):
                func_env.define(p.name, t)
            inferred_ret = self._infer_return_type(node.body, func_env)
            ret = inferred_ret if inferred_ret else VOID

        self.functions[name] = (new_param_types, ret)
        self.global_env.define(name, f'fn:{ret}')

    def _infer_return_type(self, body: list, env: Env) -> Optional[str]:
        """
        Scan a function body for return statements and infer the return type.
        Also processes VarDecl nodes to build up a local environment first,
        so that `return local_var` correctly resolves.
        """
        from .ast_nodes import Return, VarDecl, If, While, For
        # First pass: collect local var types by scanning VarDecl
        local_env = Env(parent=env)
        for stmt in body:
            if isinstance(stmt, VarDecl):
                try:
                    t = self._infer(stmt.value, local_env)
                    local_env.define(stmt.name, t)
                except Exception:
                    local_env.define(stmt.name, FLOAT)  # safe default

        # Second pass: find return statements
        for stmt in body:
            if isinstance(stmt, Return) and stmt.value is not None:
                try:
                    return self._infer(stmt.value, local_env)
                except Exception:
                    pass
            # Recurse into blocks
            for attr in ('body', 'else_body'):
                sub = getattr(stmt, attr, None)
                if isinstance(sub, list):
                    result = self._infer_return_type(sub, local_env)
                    if result:
                        return result
        return None

    # ------------------------------------------------------------------
    # Statement checking
    # ------------------------------------------------------------------

    def _check_stmt(self, node: Node, env: Env) -> None:
        if isinstance(node, VarDecl):
            self._check_var_decl(node, env)
        elif isinstance(node, TupleUnpack):
            self._check_tuple_unpack(node, env)
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

    def _check_tuple_unpack(self, node, env: Env):
        """var (a, b) = func()  — bind each name to its tuple element type."""
        val_type = self._infer(node.value, env)
        # val_type is like "(int, float)" or a function return type
        if val_type.startswith('(') and val_type.endswith(')'):
            inner = val_type[1:-1]
            types = [t.strip() for t in inner.split(',')]
        else:
            # Unknown tuple — bind everything to float
            types = [FLOAT] * len(node.names)
        for name, t in zip(node.names, types):
            env.define(name, t if t else FLOAT)

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
            actual_t = p.type_annotation if p.type_annotation else (
                t if t != 'unknown' else FLOAT
            )
            func_env.define(p.name, actual_t)
        expected_ret = ret_type if ret_type != 'unknown' else VOID
        self._return_type_stack.append(expected_ret)

        # Collect errors across every statement in the function body
        body_errors = []
        for stmt in node.body:
            try:
                self._check_stmt(stmt, func_env)
            except TypeError as e:
                body_errors.append(e)
            except MultiTypeError as e:
                body_errors.extend(e.errors)

        self._return_type_stack.pop()

        if body_errors:
            if len(body_errors) == 1:
                raise body_errors[0]
            raise MultiTypeError(body_errors)

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
            try:
                self._check_stmt(stmt, body_env)
            except TypeError:
                raise
        if node.else_body:
            else_env = Env(parent=env)
            for stmt in node.else_body:
                try:
                    self._check_stmt(stmt, else_env)
                except TypeError:
                    raise

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
            try:
                self._check_stmt(stmt, body_env)
            except TypeError:
                raise

    def _check_for(self, node: For, env: Env):
        iter_type = self._infer(node.iterable, env)
        if iter_type not in (VEC, MAT, STRING):
            raise TypeError(
                f"'for' loop can only iterate over vec, mat, or string, "
                f"but got '{iter_type}'.",
                node.iterable.line, node.iterable.col
            )
        body_env = Env(parent=env)
        elem_type = FLOAT if iter_type in (VEC, MAT) else STRING
        body_env.define(node.var, elem_type)
        for stmt in node.body:
            try:
                self._check_stmt(stmt, body_env)
            except TypeError:
                raise

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

        if isinstance(node, TupleLiteral):
            # A tuple — return a tuple type string like "(int, float)"
            types = [self._infer(e, env) for e in node.elements]
            return '(' + ', '.join(types) + ')'

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

        # Symbolic calls — skip argument type-checking entirely
        # (args contain unbound symbolic variables like x, t)
        if name == 'integral':
            return SYM if len(node.args) == 2 else FLOAT

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

        # Vec/mat stdlib (v2)
        if name == 'norm':
            return FLOAT
        if name in ('cross', 'normalize', 'zeros', 'ones'):
            return VEC
        if name == 'det':
            return FLOAT
        if name in ('inv',):
            return MAT
        if name == 'solve':
            return VEC

        # String operations (v4)
        if name in ('str_upper', 'str_lower', 'str_trim', 'str_replace',
                    'str_repeat', 'str_concat'):
            return STRING
        if name in ('str_len',):
            return INT
        if name in ('str_contains', 'str_starts', 'str_ends'):
            return BOOL

        # Symbolic integration — first arg is a symbolic call, skip type-checking it
        if name == 'integral':
            if len(node.args) == 2:
                return SYM
            return FLOAT

        # Plot functions
        if name in ('plot', 'plot_xy'):
            return VOID

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

            # --- Type inference: resolve unknown params from call site ---
            # If ANY param is unknown, infer for THIS call (polymorphic)
            if 'unknown' in param_types or ret_type == 'unknown':
                actual_types = []
                for arg in node.args:
                    try:
                        actual_types.append(self._infer(arg, env))
                    except Exception:
                        actual_types.append(FLOAT)
                if len(actual_types) == len(param_types):
                    # Infer return type for this specific call's types
                    node_ast = self._func_nodes.get(name)
                    if node_ast:
                        func_env = Env(parent=self.global_env)
                        for p, t in zip(node_ast.params, actual_types):
                            func_env.define(p.name, t)
                        inferred_ret = self._infer_return_type(node_ast.body, func_env)
                        return inferred_ret if inferred_ret else VOID
                return ret_type if ret_type != 'unknown' else FLOAT

            if len(node.args) != len(param_types):
                raise TypeError(
                    f"Function '{name}' expects {len(param_types)} argument(s) "
                    f"but got {len(node.args)}.",
                    node.line, node.col
                )
            for i, (arg, expected_t) in enumerate(zip(node.args, param_types)):
                actual_t = self._infer(arg, env)
                if actual_t != expected_t:
                    if expected_t == FLOAT and actual_t == INT: continue
                    if expected_t in (VEC, MAT, SYM): continue
                    if expected_t == 'unknown': continue
                    raise TypeError(
                        f"Argument {i+1} of '{name}' should be '{expected_t}' "
                        f"but got '{actual_t}'.",
                        arg.line, arg.col
                    )
            return ret_type if ret_type != 'unknown' else FLOAT

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
