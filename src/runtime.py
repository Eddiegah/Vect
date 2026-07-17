"""
runtime.py — Python/ctypes runtime for Vect.

These are the C-ABI functions that the JIT-compiled Vect code calls back into.
Each function is wrapped in a ctypes CFUNCTYPE so LLVM can call it via
a raw function pointer.

Why a Python runtime instead of pure LLVM IR?
  - Vector/matrix operations are complex to implement in raw IR.
  - Symbolic differentiation requires sympy, which runs in Python.
  - String handling is much easier in Python than in LLVM IR.
  - For v1, correctness and clarity beat raw performance.
"""

import ctypes
import math
import sys
from typing import Dict, Any, Optional

# We use numpy for vector/matrix storage because it gives us contiguous
# float64 arrays that are easy to work with.
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import sympy
    HAS_SYMPY = True
except ImportError:
    HAS_SYMPY = False


# ---------------------------------------------------------------------------
# Object registry
#
# The JIT code works with raw i8* pointers (integers in ctypes terms).
# We maintain a Python-side registry that maps integer IDs to real objects.
# This avoids having to implement a full memory manager.
# ---------------------------------------------------------------------------

_registry: Dict[int, Any] = {}
_next_id = 1


def _register(obj: Any) -> int:
    """Store obj in the registry and return its integer ID (used as pointer)."""
    global _next_id
    oid = _next_id
    _next_id += 1
    _registry[oid] = obj
    return oid


def _get(ptr: int) -> Any:
    """Retrieve an object by its registry ID."""
    if ptr == 0:
        return None
    obj = _registry.get(ptr)
    if obj is None:
        raise RuntimeError(f"Invalid Vect object pointer: {ptr}")
    return obj


def _as_ptr(oid: int) -> ctypes.c_void_p:
    """Return a ctypes void pointer with value = oid."""
    return ctypes.c_void_p(oid)


def reset_registry():
    """Clear the object registry — call between program runs to avoid leaks."""
    global _registry, _next_id
    _registry = {}
    _next_id = 1


# ---------------------------------------------------------------------------
# Vect object types
# ---------------------------------------------------------------------------

class VectVec:
    """A Vect vector: a list of float64 values."""
    def __init__(self, data):
        if HAS_NUMPY:
            self.data = np.array(data, dtype=np.float64)
        else:
            self.data = list(float(x) for x in data)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, i):
        return float(self.data[i])

    def __setitem__(self, i, v):
        self.data[i] = float(v)

    def __repr__(self):
        if HAS_NUMPY:
            vals = [f'{x:.6g}' for x in self.data]
        else:
            vals = [f'{x:.6g}' for x in self.data]
        return '[' + ', '.join(vals) + ']'


class VectMat:
    """A Vect matrix: a list of VectVec rows."""
    def __init__(self, rows):
        self.rows = rows   # list of VectVec

    @property
    def nrows(self):
        return len(self.rows)

    @property
    def ncols(self):
        return len(self.rows[0]) if self.rows else 0

    def __repr__(self):
        rows = ['  ' + repr(r) for r in self.rows]
        return '[\n' + ',\n'.join(rows) + '\n]'


class VectSym:
    """A symbolic expression, stored as a sympy expression string."""
    def __init__(self, expr_str: str):
        self.expr_str = expr_str

    def __repr__(self):
        return self.expr_str


# ---------------------------------------------------------------------------
# ctypes function type factory
# ---------------------------------------------------------------------------

# Mapping from our type names to ctypes types
_C_INT    = ctypes.c_int64
_C_FLOAT  = ctypes.c_double
_C_BOOL   = ctypes.c_bool
_C_PTR    = ctypes.c_void_p
_C_VOID   = None


def _cfunc(ret, *args):
    """Shorthand for ctypes.CFUNCTYPE."""
    return ctypes.CFUNCTYPE(ret, *args)


# ---------------------------------------------------------------------------
# Runtime function implementations
# ---------------------------------------------------------------------------

# --- I/O ---

def _print_int(val: int):
    print(val)

def _print_float(val: float):
    # Print cleanly: no unnecessary trailing zeros
    if val == int(val) and abs(val) < 1e15:
        print(f'{val:.1f}')
    else:
        print(f'{val:.6g}')

def _print_bool(val: bool):
    print('true' if val else 'false')

def _print_string(ptr: int):
    # First check if this is a registered Python object (vec, mat, sym, str)
    obj = _registry.get(ptr)
    if obj is not None:
        if isinstance(obj, VectVec):
            _print_vec(ptr)
        elif isinstance(obj, VectMat):
            _print_mat(ptr)
        elif isinstance(obj, VectSym):
            print(repr(obj))
        else:
            print(str(obj))
        return
    # Otherwise it's a raw C string pointer from a string literal in IR
    if ptr and ptr > 0:
        try:
            s = ctypes.string_at(ptr).decode('utf-8')
            print(s)
            return
        except Exception:
            pass
    print('')   # fallback: empty string

def _print_vec(ptr: int):
    obj = _registry.get(ptr)
    if isinstance(obj, VectVec):
        vals = [f'{x:.6g}' for x in obj.data]
        print('[' + ', '.join(vals) + ']')
    elif isinstance(obj, VectMat):
        _print_mat(ptr)
    else:
        _print_string(ptr)

def _print_mat(ptr: int):
    obj = _registry.get(ptr)
    if isinstance(obj, VectMat):
        row_strs = []
        for row in obj.rows:
            vals = [f'{x:.6g}' for x in row.data]
            row_strs.append('  [' + ', '.join(vals) + ']')
        print('[\n' + ',\n'.join(row_strs) + '\n]')
    elif isinstance(obj, VectVec):
        _print_vec(ptr)
    else:
        _print_string(ptr)

def _input_fn() -> int:
    try:
        s = input()
    except EOFError:
        s = ''
    return _register(s)

# --- Vector operations ---

def _vec_new(length: int) -> int:
    return _register(VectVec([0.0] * length))

def _vec_set(ptr: int, i: int, val: float):
    vec = _get(ptr)
    vec[i] = val

def _vec_get(ptr: int, i: int) -> float:
    vec = _get(ptr)
    return vec[i]

def _vec_len(ptr: int) -> int:
    vec = _get(ptr)
    return len(vec)

def _vec_add(a_ptr: int, b_ptr: int) -> int:
    a, b = _get(a_ptr), _get(b_ptr)
    if isinstance(a, VectMat):
        rows = [VectVec([x + y for x, y in zip(ra.data, rb.data)])
                for ra, rb in zip(a.rows, b.rows)]
        return _register(VectMat(rows))
    result = VectVec([x + y for x, y in zip(a.data, b.data)])
    return _register(result)

def _vec_sub(a_ptr: int, b_ptr: int) -> int:
    a, b = _get(a_ptr), _get(b_ptr)
    if isinstance(a, VectMat):
        rows = [VectVec([x - y for x, y in zip(ra.data, rb.data)])
                for ra, rb in zip(a.rows, b.rows)]
        return _register(VectMat(rows))
    result = VectVec([x - y for x, y in zip(a.data, b.data)])
    return _register(result)

def _vec_mul_elem(a_ptr: int, b_ptr: int) -> int:
    a, b = _get(a_ptr), _get(b_ptr)
    result = VectVec([x * y for x, y in zip(a.data, b.data)])
    return _register(result)

def _vec_scale(ptr: int, scalar: float) -> int:
    vec = _get(ptr)
    if isinstance(vec, VectMat):
        rows = [VectVec([x * scalar for x in row.data]) for row in vec.rows]
        return _register(VectMat(rows))
    result = VectVec([x * scalar for x in vec.data])
    return _register(result)

def _vec_dot(a_ptr: int, b_ptr: int) -> float:
    a, b = _get(a_ptr), _get(b_ptr)
    return sum(x * y for x, y in zip(a.data, b.data))

# --- Matrix operations ---

def _mat_new(nrows: int, ncols: int) -> int:
    rows = [VectVec([0.0] * ncols) for _ in range(nrows)]
    return _register(VectMat(rows))

def _mat_set_row(mat_ptr: int, row_idx: int, vec_ptr: int):
    mat = _get(mat_ptr)
    vec = _get(vec_ptr)
    mat.rows[row_idx] = vec

def _mat_get_row(mat_ptr: int, row_idx: int) -> int:
    mat = _get(mat_ptr)
    return _register(mat.rows[row_idx])

def _mat_mul(a_ptr: int, b_ptr: int) -> int:
    a, b = _get(a_ptr), _get(b_ptr)
    if isinstance(a, VectMat) and isinstance(b, VectMat):
        nrows, ncols, inner = a.nrows, b.ncols, a.ncols
        result_rows = []
        for i in range(nrows):
            row = []
            for j in range(ncols):
                s = sum(a.rows[i][k] * b.rows[k][j] for k in range(inner))
                row.append(s)
            result_rows.append(VectVec(row))
        return _register(VectMat(result_rows))
    # mat @ vec (column vector case)
    if isinstance(a, VectMat) and isinstance(b, VectVec):
        result = []
        for row in a.rows:
            s = sum(row[k] * b[k] for k in range(len(b)))
            result.append(s)
        return _register(VectVec(result))
    raise RuntimeError("Matrix multiply requires mat @ mat or mat @ vec")

def _mat_add(a_ptr: int, b_ptr: int) -> int:
    return _vec_add(a_ptr, b_ptr)   # reuses vec_add which handles VectMat

def _mat_sub(a_ptr: int, b_ptr: int) -> int:
    return _vec_sub(a_ptr, b_ptr)

def _mat_transpose(ptr: int) -> int:
    mat = _get(ptr)
    if isinstance(mat, VectMat):
        nrows, ncols = mat.nrows, mat.ncols
        result_rows = []
        for j in range(ncols):
            row = VectVec([mat.rows[i][j] for i in range(nrows)])
            result_rows.append(row)
        return _register(VectMat(result_rows))
    # Transpose of a vec → single-column mat
    if isinstance(mat, VectVec):
        rows = [VectVec([mat[i]]) for i in range(len(mat))]
        return _register(VectMat(rows))
    raise RuntimeError("transpose requires a matrix or vector")

def _mat_scale(ptr: int, scalar: float) -> int:
    return _vec_scale(ptr, scalar)

# --- Symbolic math ---

def _sym_diff(expr_ptr: int, var_ptr: int) -> int:
    if not HAS_SYMPY:
        raise RuntimeError("sympy is not installed — symbolic differentiation unavailable")
    try:
        expr_str = ctypes.string_at(expr_ptr).decode('utf-8')
        var_str  = ctypes.string_at(var_ptr).decode('utf-8')
    except Exception:
        expr_str = str(_get(expr_ptr)) if expr_ptr > 1000 else ''
        var_str  = str(_get(var_ptr))  if var_ptr  > 1000 else ''

    var_sym  = sympy.Symbol(var_str)
    expr_sym = sympy.sympify(expr_str)
    deriv    = sympy.diff(expr_sym, var_sym)
    result_str = str(deriv)
    return _register(VectSym(result_str))

def _sym_eval(expr_ptr: int, var_ptr: int, val: float) -> float:
    if not HAS_SYMPY:
        raise RuntimeError("sympy is not installed")
    obj = _get(expr_ptr)
    if isinstance(obj, VectSym):
        expr_str = obj.expr_str
    else:
        try:
            expr_str = ctypes.string_at(expr_ptr).decode('utf-8')
        except Exception:
            expr_str = str(obj)

    try:
        var_str = ctypes.string_at(var_ptr).decode('utf-8')
    except Exception:
        var_str = str(_get(var_ptr))

    var_sym  = sympy.Symbol(var_str)
    expr_sym = sympy.sympify(expr_str)
    result   = expr_sym.subs(var_sym, val)
    return float(result)

# --- Math builtins ---

def _sqrt(x: float) -> float: return math.sqrt(x)
def _sin(x: float) -> float:  return math.sin(x)
def _cos(x: float) -> float:  return math.cos(x)
def _tan(x: float) -> float:  return math.tan(x)
def _abs_f(x: float) -> float: return abs(x)
def _floor(x: float) -> int:  return int(math.floor(x))
def _ceil(x: float) -> int:   return int(math.ceil(x))

# --- String operations ---

def _str_concat(a_ptr: int, b_ptr: int) -> int:
    def _deref(ptr):
        obj = _registry.get(ptr)
        if obj is not None:
            return str(obj)
        try:
            return ctypes.string_at(ptr).decode('utf-8')
        except Exception:
            return ''
    return _register(_deref(a_ptr) + _deref(b_ptr))

def _int_to_str(val: int) -> int:
    return _register(str(val))

def _float_to_str(val: float) -> int:
    if val == int(val) and abs(val) < 1e15:
        return _register(f'{val:.1f}')
    return _register(f'{val:.6g}')

# --- Range ---

def _range_fn(start: int, stop: int, step: int) -> int:
    if step == 0:
        step = 1
    data = list(float(x) for x in range(start, stop, step))
    return _register(VectVec(data))


# ---------------------------------------------------------------------------
# Wrap all functions in ctypes callbacks and build the symbol table
# ---------------------------------------------------------------------------

def build_runtime() -> Dict[str, Any]:
    """
    Return a dict mapping LLVM symbol name → ctypes function pointer.
    Call this once before executing a compiled program.
    """
    # Keep references alive to prevent GC
    _callbacks = []

    def wrap(ret, *arg_types):
        """Decorator: wrap a Python function as a ctypes C callback."""
        def decorator(fn):
            ctype = ctypes.CFUNCTYPE(ret, *arg_types)
            cb = ctype(fn)
            _callbacks.append(cb)  # prevent garbage collection
            return cb
        return decorator

    C = ctypes

    symbols = {}

    # Helper to register a wrapped function
    def reg(name, fn, ret, *args):
        ctype = ctypes.CFUNCTYPE(ret, *args)
        cb = ctype(fn)
        _callbacks.append(cb)
        symbols[name] = cb

    # I/O
    reg('vect_print_int',    _print_int,    None, C.c_int64)
    reg('vect_print_float',  _print_float,  None, C.c_double)
    reg('vect_print_bool',   _print_bool,   None, C.c_bool)
    reg('vect_print_string', _print_string, None, C.c_void_p)
    reg('vect_print_vec',    _print_vec,    None, C.c_void_p)
    reg('vect_print_mat',    _print_mat,    None, C.c_void_p)
    reg('vect_input',        _input_fn,     C.c_void_p)

    # Vectors
    reg('vect_vec_new',      _vec_new,      C.c_void_p, C.c_int64)
    reg('vect_vec_set',      _vec_set,      None, C.c_void_p, C.c_int64, C.c_double)
    reg('vect_vec_get',      _vec_get,      C.c_double, C.c_void_p, C.c_int64)
    reg('vect_vec_len',      _vec_len,      C.c_int64, C.c_void_p)
    reg('vect_vec_add',      _vec_add,      C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_vec_sub',      _vec_sub,      C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_vec_mul_elem', _vec_mul_elem, C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_vec_scale',    _vec_scale,    C.c_void_p, C.c_void_p, C.c_double)
    reg('vect_vec_dot',      _vec_dot,      C.c_double, C.c_void_p, C.c_void_p)

    # Matrices
    reg('vect_mat_new',      _mat_new,      C.c_void_p, C.c_int64, C.c_int64)
    reg('vect_mat_set_row',  _mat_set_row,  None, C.c_void_p, C.c_int64, C.c_void_p)
    reg('vect_mat_get_row',  _mat_get_row,  C.c_void_p, C.c_void_p, C.c_int64)
    reg('vect_mat_mul',      _mat_mul,      C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_mat_add',      _mat_add,      C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_mat_sub',      _mat_sub,      C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_mat_transpose',_mat_transpose,C.c_void_p, C.c_void_p)
    reg('vect_mat_scale',    _mat_scale,    C.c_void_p, C.c_void_p, C.c_double)

    # Symbolic
    reg('vect_sym_diff',     _sym_diff,     C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_sym_eval',     _sym_eval,     C.c_double, C.c_void_p, C.c_void_p, C.c_double)

    # Math
    reg('vect_sqrt',  _sqrt,  C.c_double, C.c_double)
    reg('vect_sin',   _sin,   C.c_double, C.c_double)
    reg('vect_cos',   _cos,   C.c_double, C.c_double)
    reg('vect_tan',   _tan,   C.c_double, C.c_double)
    reg('vect_abs_f', _abs_f, C.c_double, C.c_double)
    reg('vect_floor', _floor, C.c_int64,  C.c_double)
    reg('vect_ceil',  _ceil,  C.c_int64,  C.c_double)

    # Strings
    reg('vect_str_concat',   _str_concat,   C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_int_to_str',   _int_to_str,   C.c_void_p, C.c_int64)
    reg('vect_float_to_str', _float_to_str, C.c_void_p, C.c_double)

    # Range
    reg('vect_range', _range_fn, C.c_void_p, C.c_int64, C.c_int64, C.c_int64)

    # Keep callbacks alive by storing on the dict
    symbols['_keep_alive'] = _callbacks
    return symbols
