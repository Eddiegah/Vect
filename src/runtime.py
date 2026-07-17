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
    obj = _get(ptr)
    if isinstance(obj, VectMat):
        # Indexing a matrix returns a row — but codegen expects float here.
        # For row access use _mat_get_row. If we get here it's a scalar fetch
        # from a flat representation — return 0 safely.
        row = obj.rows[i] if i < len(obj.rows) else VectVec([0.0])
        return float(row[0]) if len(row) > 0 else 0.0
    return obj[i]

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


def _sym_integrate(expr_ptr: int, var_ptr: int) -> int:
    """Indefinite symbolic integration: integral(expr, var)"""
    if not HAS_SYMPY:
        raise RuntimeError("sympy is not installed")
    # expr_ptr may be a C string pointer OR a registry ID
    obj = _registry.get(expr_ptr)
    if isinstance(obj, VectSym):
        expr_str = obj.expr_str
    else:
        try:
            expr_str = ctypes.string_at(expr_ptr).decode('utf-8')
        except Exception:
            expr_str = str(obj) if obj else '0'
    try:
        var_str = ctypes.string_at(var_ptr).decode('utf-8')
    except Exception:
        var_str = 'x'
    var_sym  = sympy.Symbol(var_str)
    expr_sym = sympy.sympify(expr_str)
    result   = sympy.integrate(expr_sym, var_sym)
    return _register(VectSym(str(result)))


def _sym_integrate_definite(expr_ptr: int, var_ptr: int,
                             lo: float, hi: float) -> float:
    """Definite symbolic integration: integral(expr, var, lo, hi) → float"""
    if not HAS_SYMPY:
        raise RuntimeError("sympy is not installed")
    obj = _registry.get(expr_ptr)
    if isinstance(obj, VectSym):
        expr_str = obj.expr_str
    else:
        try:
            expr_str = ctypes.string_at(expr_ptr).decode('utf-8')
        except Exception:
            expr_str = str(obj) if obj else '0'
    try:
        var_str = ctypes.string_at(var_ptr).decode('utf-8')
    except Exception:
        var_str = 'x'
    var_sym  = sympy.Symbol(var_str)
    expr_sym = sympy.sympify(expr_str)
    result   = sympy.integrate(expr_sym, (var_sym, lo, hi))
    return float(result)

# --- Math builtins ---

def _sqrt(x: float) -> float: return math.sqrt(x)
def _sin(x: float) -> float:  return math.sin(x)
def _cos(x: float) -> float:  return math.cos(x)
def _tan(x: float) -> float:  return math.tan(x)
def _abs_f(x: float) -> float: return abs(x)
def _floor(x: float) -> int:  return int(math.floor(x))
def _ceil(x: float) -> int:   return int(math.ceil(x))

# ---------------------------------------------------------------------------
# Vec/Mat stdlib — new in v2
# ---------------------------------------------------------------------------

def _vec_norm(ptr: int) -> float:
    """Euclidean norm (magnitude) of a vector: sqrt(sum(x²))"""
    vec = _get(ptr)
    return math.sqrt(sum(x*x for x in vec.data))

def _vec_cross(a_ptr: int, b_ptr: int) -> int:
    """3D cross product. Vectors must have length 3."""
    a, b = _get(a_ptr), _get(b_ptr)
    if len(a) != 3 or len(b) != 3:
        raise RuntimeError("cross product requires two 3D vectors")
    cx = a[1]*b[2] - a[2]*b[1]
    cy = a[2]*b[0] - a[0]*b[2]
    cz = a[0]*b[1] - a[1]*b[0]
    return _register(VectVec([cx, cy, cz]))

def _vec_normalize(ptr: int) -> int:
    """Return a unit vector (magnitude = 1)."""
    vec = _get(ptr)
    mag = math.sqrt(sum(x*x for x in vec.data))
    if mag == 0:
        raise RuntimeError("Cannot normalize a zero vector")
    return _register(VectVec([x / mag for x in vec.data]))

def _mat_det(ptr: int) -> float:
    """Determinant of a square matrix (uses Gaussian elimination)."""
    mat = _get(ptr)
    n = mat.nrows
    if n != mat.ncols:
        raise RuntimeError(f"det requires a square matrix, got {n}x{mat.ncols}")
    # Build a mutable copy as list-of-lists
    M = [[mat.rows[i][j] for j in range(n)] for i in range(n)]
    sign = 1.0
    for col in range(n):
        # Find pivot
        pivot_row = None
        for row in range(col, n):
            if abs(M[row][col]) > 1e-12:
                pivot_row = row
                break
        if pivot_row is None:
            return 0.0
        if pivot_row != col:
            M[col], M[pivot_row] = M[pivot_row], M[col]
            sign *= -1
        for row in range(col + 1, n):
            factor = M[row][col] / M[col][col]
            for k in range(col, n):
                M[row][k] -= factor * M[col][k]
    result = sign
    for i in range(n):
        result *= M[i][i]
    return result

def _mat_inv(ptr: int) -> int:
    """Inverse of a square matrix using Gauss-Jordan elimination."""
    mat = _get(ptr)
    n = mat.nrows
    if n != mat.ncols:
        raise RuntimeError("inv requires a square matrix")
    # Augmented matrix [M | I]
    M = [[mat.rows[i][j] for j in range(n)] for i in range(n)]
    I = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        # Pivot
        pivot = None
        for row in range(col, n):
            if abs(M[row][col]) > 1e-12:
                pivot = row
                break
        if pivot is None:
            raise RuntimeError("Matrix is singular — inverse does not exist")
        M[col], M[pivot] = M[pivot], M[col]
        I[col], I[pivot] = I[pivot], I[col]
        scale = M[col][col]
        M[col] = [v / scale for v in M[col]]
        I[col] = [v / scale for v in I[col]]
        for row in range(n):
            if row != col:
                factor = M[row][col]
                M[row] = [M[row][k] - factor * M[col][k] for k in range(n)]
                I[row] = [I[row][k] - factor * I[col][k] for k in range(n)]
    result_rows = [VectVec(I[i]) for i in range(n)]
    return _register(VectMat(result_rows))

def _mat_solve(mat_ptr: int, vec_ptr: int) -> int:
    """
    Solve the linear system Ax = b.
    mat_ptr → A (n×n matrix), vec_ptr → b (vec of length n).
    Returns x as a vec.
    """
    A_mat = _get(mat_ptr)
    b_vec = _get(vec_ptr)
    n = A_mat.nrows
    # Augmented [A | b]
    M = [[A_mat.rows[i][j] for j in range(n)] + [b_vec[i]] for i in range(n)]
    for col in range(n):
        pivot = None
        for row in range(col, n):
            if abs(M[row][col]) > 1e-12:
                pivot = row
                break
        if pivot is None:
            raise RuntimeError("System has no unique solution")
        M[col], M[pivot] = M[pivot], M[col]
        scale = M[col][col]
        M[col] = [v / scale for v in M[col]]
        for row in range(n):
            if row != col:
                factor = M[row][col]
                M[row] = [M[row][k] - factor * M[col][k] for k in range(n + 1)]
    x = VectVec([M[i][n] for i in range(n)])
    return _register(x)

def _vec_zeros(n: int) -> int:
    """Create a zero vector of length n."""
    return _register(VectVec([0.0] * n))

def _vec_ones(n: int) -> int:
    """Create a vector of ones of length n."""
    return _register(VectVec([1.0] * n))


# ---------------------------------------------------------------------------
# Plot — v2 feature
# ---------------------------------------------------------------------------

def _plot_sym(expr_ptr: int, var_ptr: int, lo: float, hi: float,
              title_ptr: int) -> int:
    """
    Plot a symbolic expression over [lo, hi].
    expr_ptr  → C string with the sympy-parseable expression
    var_ptr   → C string with the variable name
    lo, hi    → range
    title_ptr → C string with plot title (may be 0/empty)
    """
    try:
        import matplotlib
        matplotlib.use('Agg')   # non-interactive backend — saves to file
        import matplotlib.pyplot as plt
        import numpy as np_plot

        # Decode strings
        obj = _registry.get(expr_ptr)
        if isinstance(obj, VectSym):
            expr_str = obj.expr_str
        else:
            try:
                expr_str = ctypes.string_at(expr_ptr).decode('utf-8')
            except Exception:
                expr_str = '0'

        try:
            var_str = ctypes.string_at(var_ptr).decode('utf-8')
        except Exception:
            var_str = 'x'

        title_str = ''
        if title_ptr and title_ptr > 0:
            try:
                title_str = ctypes.string_at(title_ptr).decode('utf-8')
            except Exception:
                title_obj = _registry.get(title_ptr)
                if isinstance(title_obj, str):
                    title_str = title_obj

        # Evaluate numerically
        if HAS_SYMPY:
            var_sym  = sympy.Symbol(var_str)
            expr_sym = sympy.sympify(expr_str)
            xs = np_plot.linspace(lo, hi, 400)
            ys = []
            for xv in xs:
                try:
                    ys.append(float(expr_sym.subs(var_sym, xv)))
                except Exception:
                    ys.append(float('nan'))
        else:
            raise RuntimeError("sympy required for plot()")

        # Plot
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(xs, ys, linewidth=2, color='#0f3460')
        ax.axhline(0, color='black', linewidth=0.8, alpha=0.5)
        ax.axvline(0, color='black', linewidth=0.8, alpha=0.5)
        ax.grid(True, alpha=0.3)
        ax.set_xlabel(var_str, fontsize=12)
        ax.set_ylabel(f'f({var_str})', fontsize=12)
        label = title_str if title_str else f'f({var_str}) = {expr_str}'
        ax.set_title(label, fontsize=13)
        plt.tight_layout()

        # Save to file
        out_file = 'vect_plot.png'
        plt.savefig(out_file, dpi=150)
        plt.close()
        print(f"[plot saved to {out_file}]")

        return 0
    except Exception as e:
        print(f"[plot error: {e}]")
        return 0


def _plot_vec(x_ptr: int, y_ptr: int, title_ptr: int) -> int:
    """
    Plot two vectors as x/y data.
    plot_xy(x_vec, y_vec, "title")
    """
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        x_vec = _get(x_ptr)
        y_vec = _get(y_ptr)
        xs = list(x_vec.data)
        ys = list(y_vec.data)

        title_str = ''
        if title_ptr and title_ptr > 0:
            try:
                title_str = ctypes.string_at(title_ptr).decode('utf-8')
            except Exception:
                title_obj = _registry.get(title_ptr)
                if isinstance(title_obj, str):
                    title_str = title_obj

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(xs, ys, linewidth=2, color='#0f3460', marker='o',
                markersize=4)
        ax.axhline(0, color='black', linewidth=0.8, alpha=0.5)
        ax.grid(True, alpha=0.3)
        if title_str:
            ax.set_title(title_str, fontsize=13)
        plt.tight_layout()
        out_file = 'vect_plot.png'
        plt.savefig(out_file, dpi=150)
        plt.close()
        print(f"[plot saved to {out_file}]")
        return 0
    except Exception as e:
        print(f"[plot error: {e}]")
        return 0

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
    reg('vect_sym_diff',              _sym_diff,              C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_sym_eval',              _sym_eval,              C.c_double, C.c_void_p, C.c_void_p, C.c_double)
    reg('vect_sym_integrate',         _sym_integrate,         C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_sym_integrate_definite',_sym_integrate_definite,C.c_double, C.c_void_p, C.c_void_p, C.c_double, C.c_double)

    # Math
    reg('vect_sqrt',  _sqrt,  C.c_double, C.c_double)
    reg('vect_sin',   _sin,   C.c_double, C.c_double)
    reg('vect_cos',   _cos,   C.c_double, C.c_double)
    reg('vect_tan',   _tan,   C.c_double, C.c_double)
    reg('vect_abs_f', _abs_f, C.c_double, C.c_double)
    reg('vect_floor', _floor, C.c_int64,  C.c_double)
    reg('vect_ceil',  _ceil,  C.c_int64,  C.c_double)

    # Vec/Mat stdlib (v2)
    reg('vect_vec_norm',      _vec_norm,      C.c_double, C.c_void_p)
    reg('vect_vec_cross',     _vec_cross,     C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_vec_normalize', _vec_normalize, C.c_void_p, C.c_void_p)
    reg('vect_mat_det',       _mat_det,       C.c_double, C.c_void_p)
    reg('vect_mat_inv',       _mat_inv,       C.c_void_p, C.c_void_p)
    reg('vect_mat_solve',     _mat_solve,     C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_zeros',         _vec_zeros,     C.c_void_p, C.c_int64)
    reg('vect_ones',          _vec_ones,      C.c_void_p, C.c_int64)

    # Plot (v2)
    reg('vect_plot_sym',  _plot_sym,  C.c_int32, C.c_void_p, C.c_void_p, C.c_double, C.c_double, C.c_void_p)
    reg('vect_plot_vec',  _plot_vec,  C.c_int32, C.c_void_p, C.c_void_p, C.c_void_p)

    # Strings
    reg('vect_str_concat',   _str_concat,   C.c_void_p, C.c_void_p, C.c_void_p)
    reg('vect_int_to_str',   _int_to_str,   C.c_void_p, C.c_int64)
    reg('vect_float_to_str', _float_to_str, C.c_void_p, C.c_double)

    # Range
    reg('vect_range', _range_fn, C.c_void_p, C.c_int64, C.c_int64, C.c_int64)

    # Keep callbacks alive by storing on the dict
    symbols['_keep_alive'] = _callbacks
    return symbols
