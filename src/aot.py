"""
aot.py — Ahead-of-Time (AOT) compilation for Vect.

Compiles a .vect program to a standalone native executable (.exe on Windows).

Pipeline:
  1. Parse + type-check the source (same as JIT)
  2. Code-generate LLVM IR (same CodeGen, but targeting AOT)
  3. Emit a native object file via llvmlite's target machine
  4. Write a C runtime shim (vect_runtime_shim.c) with all the
     vect_print_*, vect_vec_*, etc. functions backed by Python's
     embedded interpreter — OR use a pure-C runtime for portability.
  5. Compile and link with gcc into a final .exe

For v2, we use the "embedded Python" approach:
  - The generated .exe embeds a call to Py_Initialize() and imports
    the Vect runtime module, then calls vect_main().
  - This means the .exe requires Python 3.11 to be on PATH, but
    produces a real standalone binary that anyone can run with
    'myprogram.exe' from the command line.

Future work: a full static-C runtime would remove the Python dependency.
"""

import os
import sys
import subprocess
import tempfile
import ctypes
from pathlib import Path

import llvmlite.ir as ir
import llvmlite.binding as llvm

from .pipeline import _parse
from .type_checker import type_check
from .codegen import CodeGen


# ---------------------------------------------------------------------------
# C runtime shim — calls back into Python for vec/mat/sym/print/plot
# ---------------------------------------------------------------------------

_C_SHIM = r"""
/*
 * vect_runtime_shim.c
 *
 * Thin C wrapper that initialises a Python interpreter and delegates
 * all vect_* runtime calls to the Python runtime module.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* Forward declare the JIT-compiled main we link against */
extern int vect_main(void);

/* ── Registry ── */
#define MAX_OBJS 65536
static PyObject* _registry[MAX_OBJS];
static int _next_id = 1;

static int _register(PyObject* obj) {
    int id = _next_id++;
    if (id >= MAX_OBJS) { fprintf(stderr, "registry overflow\n"); exit(1); }
    _registry[id] = obj;
    Py_INCREF(obj);
    return id;
}

static PyObject* _get(int id) {
    if (id <= 0 || id >= MAX_OBJS || !_registry[id]) {
        fprintf(stderr, "Invalid Vect pointer: %d\n", id);
        exit(1);
    }
    return _registry[id];
}

/* ── Print ── */
void vect_print_int(long long v)  { printf("%lld\n", v); fflush(stdout); }
void vect_print_float(double v) {
    if (v == (long long)v && fabs(v) < 1e15)
        printf("%.1f\n", v);
    else
        printf("%g\n", v);
    fflush(stdout);
}
void vect_print_bool(int v) {
    printf("%s\n", v ? "true" : "false"); fflush(stdout);
}
void vect_print_string(void* ptr) {
    int id = (int)(long long)ptr;
    if (id > 0 && id < MAX_OBJS && _registry[id]) {
        PyObject* obj = _registry[id];
        PyObject* s = PyObject_Str(obj);
        if (s) { printf("%s\n", PyUnicode_AsUTF8(s)); Py_DECREF(s); }
    } else {
        printf("%s\n", ptr ? (char*)ptr : ""); 
    }
    fflush(stdout);
}
void vect_print_vec(void* ptr)  { vect_print_string(ptr); }
void vect_print_mat(void* ptr)  { vect_print_string(ptr); }

/* ── Math ── */
double vect_sqrt(double x)  { return sqrt(x); }
double vect_sin(double x)   { return sin(x); }
double vect_cos(double x)   { return cos(x); }
double vect_tan(double x)   { return tan(x); }
double vect_abs_f(double x) { return fabs(x); }
long long vect_floor(double x) { return (long long)floor(x); }
long long vect_ceil(double x)  { return (long long)ceil(x); }

/* ── Delegate to Python runtime for complex ops ── */
static PyObject* _rt_mod = NULL;

static PyObject* _call_rt(const char* fn, PyObject* args) {
    if (!_rt_mod) {
        _rt_mod = PyImport_ImportModule("src.runtime");
        if (!_rt_mod) { PyErr_Print(); exit(1); }
    }
    PyObject* func = PyObject_GetAttrString(_rt_mod, fn);
    if (!func) { fprintf(stderr, "runtime function not found: %s\n", fn); exit(1); }
    PyObject* result = PyObject_CallObject(func, args);
    Py_DECREF(func);
    Py_DECREF(args);
    return result;
}

void*   vect_vec_new(long long n)   { PyObject* r = _call_rt("_vec_new", Py_BuildValue("(L)", n)); return (void*)(long long)_register(r); }
void    vect_vec_set(void* p, long long i, double v) { _call_rt("_vec_set", Py_BuildValue("(LLd", (long long)p, i, v)); }
double  vect_vec_get(void* p, long long i) { PyObject* r = _call_rt("_vec_get", Py_BuildValue("(LL)", (long long)p, i)); double v = PyFloat_AsDouble(r); Py_DECREF(r); return v; }
long long vect_vec_len(void* p) { PyObject* r = _call_rt("_vec_len", Py_BuildValue("(L)", (long long)p)); long long v = PyLong_AsLongLong(r); Py_DECREF(r); return v; }
void*   vect_vec_add(void* a, void* b) { PyObject* r = _call_rt("_vec_add", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_vec_sub(void* a, void* b) { PyObject* r = _call_rt("_vec_sub", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_vec_mul_elem(void* a, void* b) { PyObject* r = _call_rt("_vec_mul_elem", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_vec_scale(void* a, double s) { PyObject* r = _call_rt("_vec_scale", Py_BuildValue("(Ld)", (long long)a, s)); return (void*)(long long)_register(r); }
double  vect_vec_dot(void* a, void* b) { PyObject* r = _call_rt("_vec_dot", Py_BuildValue("(LL)", (long long)a, (long long)b)); double v = PyFloat_AsDouble(r); Py_DECREF(r); return v; }
void*   vect_mat_new(long long r, long long c) { PyObject* o = _call_rt("_mat_new", Py_BuildValue("(LL)", r, c)); return (void*)(long long)_register(o); }
void    vect_mat_set_row(void* m, long long i, void* v) { _call_rt("_mat_set_row", Py_BuildValue("(LLL)", (long long)m, i, (long long)v)); }
void*   vect_mat_get_row(void* m, long long i) { PyObject* r = _call_rt("_mat_get_row", Py_BuildValue("(LL)", (long long)m, i)); return (void*)(long long)_register(r); }
void*   vect_mat_mul(void* a, void* b) { PyObject* r = _call_rt("_mat_mul", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_mat_add(void* a, void* b) { PyObject* r = _call_rt("_mat_add", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_mat_sub(void* a, void* b) { PyObject* r = _call_rt("_mat_sub", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_mat_transpose(void* m) { PyObject* r = _call_rt("_mat_transpose", Py_BuildValue("(L)", (long long)m)); return (void*)(long long)_register(r); }
void*   vect_mat_scale(void* m, double s) { PyObject* r = _call_rt("_mat_scale", Py_BuildValue("(Ld)", (long long)m, s)); return (void*)(long long)_register(r); }
void*   vect_sym_diff(void* e, void* v) { PyObject* r = _call_rt("_sym_diff", Py_BuildValue("(LL)", (long long)e, (long long)v)); return (void*)(long long)_register(r); }
double  vect_sym_eval(void* e, void* v, double val) { PyObject* r = _call_rt("_sym_eval", Py_BuildValue("(LLd)", (long long)e, (long long)v, val)); double res = PyFloat_AsDouble(r); Py_DECREF(r); return res; }
void*   vect_str_concat(void* a, void* b) { PyObject* r = _call_rt("_str_concat", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_int_to_str(long long v) { PyObject* r = _call_rt("_int_to_str", Py_BuildValue("(L)", v)); return (void*)(long long)_register(r); }
void*   vect_float_to_str(double v) { PyObject* r = _call_rt("_float_to_str", Py_BuildValue("(d)", v)); return (void*)(long long)_register(r); }
void*   vect_range(long long s, long long e, long long step) { PyObject* r = _call_rt("_range_fn", Py_BuildValue("(LLL)", s, e, step)); return (void*)(long long)_register(r); }
void*   vect_input(void) { PyObject* r = _call_rt("_input_fn", PyTuple_New(0)); return (void*)(long long)_register(r); }
double  vect_vec_norm(void* v) { PyObject* r = _call_rt("_vec_norm", Py_BuildValue("(L)", (long long)v)); double res = PyFloat_AsDouble(r); Py_DECREF(r); return res; }
void*   vect_vec_cross(void* a, void* b) { PyObject* r = _call_rt("_vec_cross", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_vec_normalize(void* v) { PyObject* r = _call_rt("_vec_normalize", Py_BuildValue("(L)", (long long)v)); return (void*)(long long)_register(r); }
double  vect_mat_det(void* m) { PyObject* r = _call_rt("_mat_det", Py_BuildValue("(L)", (long long)m)); double res = PyFloat_AsDouble(r); Py_DECREF(r); return res; }
void*   vect_mat_inv(void* m) { PyObject* r = _call_rt("_mat_inv", Py_BuildValue("(L)", (long long)m)); return (void*)(long long)_register(r); }
void*   vect_mat_solve(void* a, void* b) { PyObject* r = _call_rt("_mat_solve", Py_BuildValue("(LL)", (long long)a, (long long)b)); return (void*)(long long)_register(r); }
void*   vect_zeros(long long n) { PyObject* r = _call_rt("_vec_zeros", Py_BuildValue("(L)", n)); return (void*)(long long)_register(r); }
void*   vect_ones(long long n)  { PyObject* r = _call_rt("_vec_ones",  Py_BuildValue("(L)", n)); return (void*)(long long)_register(r); }
void*   vect_sym_integrate(void* e, void* v) { PyObject* r = _call_rt("_sym_integrate", Py_BuildValue("(LL)", (long long)e, (long long)v)); return (void*)(long long)_register(r); }
double  vect_sym_integrate_definite(void* e, void* v, double lo, double hi) { PyObject* r = _call_rt("_sym_integrate_definite", Py_BuildValue("(LLdd)", (long long)e, (long long)v, lo, hi)); double res = PyFloat_AsDouble(r); Py_DECREF(r); return res; }
int     vect_plot_sym(void* e, void* v, double lo, double hi, void* t) { _call_rt("_plot_sym", Py_BuildValue("(LLddL)", (long long)e, (long long)v, lo, hi, (long long)t)); return 0; }
int     vect_plot_vec(void* x, void* y, void* t) { _call_rt("_plot_vec", Py_BuildValue("(LLL)", (long long)x, (long long)y, (long long)t)); return 0; }
void*   vect_llvm_pow(double b, double e) { return (void*)(long long)0; }
double  llvm_pow_f64(double b, double e) { return pow(b, e); }

int main(int argc, char** argv) {
    Py_Initialize();
    /* Add current directory to sys.path so 'src.runtime' is importable */
    PyRun_SimpleString(
        "import sys, os\n"
        "sys.path.insert(0, os.getcwd())\n"
    );
    int ret = vect_main();
    Py_Finalize();
    return ret;
}
"""


# ---------------------------------------------------------------------------
# AOT compile function
# ---------------------------------------------------------------------------

def compile_to_exe(source: str, output_path: str,
                   filename: str = '<input>') -> str:
    """
    Compile Vect source to a native executable.

    Steps:
      1. Parse + type-check
      2. Generate LLVM IR
      3. Emit object file
      4. Write C shim
      5. Link with gcc

    Returns the path to the created executable.
    """
    # ── Step 1: parse + type-check ──────────────────────────────────────
    program = _parse(source, filename)
    checker = type_check(program)

    # ── Step 2: generate LLVM IR ─────────────────────────────────────────
    cg = CodeGen(checker)
    cg.compile(program)

    # ── Step 3: emit object file ──────────────────────────────────────────
    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()

    ir_str = cg.get_ir()
    llvm_mod = llvm.parse_assembly(ir_str)
    llvm_mod.verify()

    target    = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine(
        reloc='pic', codemodel='default', opt=2)

    obj_data = target_machine.emit_object(llvm_mod)

    # Write to temp files
    base     = Path(output_path).stem
    work_dir = Path(output_path).parent

    obj_file  = str(work_dir / f'{base}.o')
    shim_file = str(work_dir / f'{base}_shim.c')
    out_file  = str(output_path)
    if sys.platform == 'win32' and not out_file.endswith('.exe'):
        out_file += '.exe'

    with open(obj_file, 'wb') as f:
        f.write(obj_data)

    with open(shim_file, 'w', encoding='utf-8') as f:
        f.write(_C_SHIM)

    # ── Step 4: get Python flags for embedding ────────────────────────────
    python_exe = sys.executable
    # Get include and lib paths
    import sysconfig
    py_inc    = sysconfig.get_path('include')
    py_libdir = sysconfig.get_config_var('LIBDIR') or ''
    py_ver    = f"{sys.version_info.major}{sys.version_info.minor}"

    # ── Step 5: link with gcc ─────────────────────────────────────────────
    import sysconfig, glob, shutil

    gcc = r'C:\msys64\ucrt64\bin\gcc.exe' if sys.platform == 'win32' \
          else 'gcc'

    py_inc    = sysconfig.get_path('include')
    py_prefix = Path(sys.base_prefix)

    if sys.platform == 'win32':
        py_ver       = f"{sys.version_info.major}{sys.version_info.minor}"
        py_lib_name  = f'python{py_ver}'
        py_lib_path  = str(py_prefix / 'libs')

        gcc_cmd = [
            gcc, '-O2',
            shim_file, obj_file,
            f'-I{py_inc}',
            f'-L{py_lib_path}',
            f'-l{py_lib_name}',
            '-lm',
            '-o', out_file,
            # Add Python DLL dir to rpath equivalent on Windows — embed manifest
            f'-Wl,--enable-auto-import',
        ]

        # Copy python DLL next to the exe so it can be found at runtime
        dll_pattern = str(py_prefix / f'python{py_ver}.dll')
        dlls = glob.glob(dll_pattern)
        if not dlls:
            dlls = glob.glob(str(py_prefix / 'python3.dll'))
        exe_dir = str(work_dir)
        for dll in dlls:
            dest = os.path.join(exe_dir, os.path.basename(dll))
            if not os.path.exists(dest):
                shutil.copy2(dll, dest)
    else:
        py_ver    = f"{sys.version_info.major}.{sys.version_info.minor}"
        py_libdir = sysconfig.get_config_var('LIBDIR') or ''
        gcc_cmd = [
            gcc, '-O2',
            shim_file, obj_file,
            f'-I{py_inc}',
            f'-L{py_libdir}',
            f'-lpython{py_ver}',
            '-lm',
            '-o', out_file,
        ]

    result = subprocess.run(gcc_cmd, capture_output=True, text=True)

    # Clean up intermediate files
    try:
        os.remove(obj_file)
        os.remove(shim_file)
    except Exception:
        pass

    if result.returncode != 0:
        raise RuntimeError(
            f"Linker error:\n{result.stderr}\n\n"
            f"Command: {' '.join(gcc_cmd)}"
        )

    return out_file
