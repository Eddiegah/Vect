"""
codegen.py — LLVM IR code generator for Vect (Milestone 3: vectors + matrices).

Architecture overview:
  - We walk the type-checked AST and emit LLVM IR using llvmlite's IR builder.
  - The result is JIT-compiled and executed in-process via llvmlite's MCJIT engine.
  - Vectors, matrices, and symbolic math are handled via a Python runtime
    (see runtime.py) called through ctypes-style external function pointers.

LLVM IR primer (so you can explain how this works):
  - LLVM IR is a typed, SSA (Static Single Assignment) intermediate language.
  - Every value is assigned exactly once. Mutable variables need alloca/load/store.
  - We use alloca to allocate stack slots for variables, store to write them,
    and load to read them back — this is the standard pattern for local variables.
  - llvmlite wraps this in a Python API: ir.Module, ir.Function, ir.IRBuilder.
  - After building IR, we pass it to llvmlite's binding layer to JIT-compile it.
"""

import ctypes
import sys
from typing import Dict, Optional, Any

import llvmlite.ir as ir
import llvmlite.binding as llvm

from .ast_nodes import *
from .type_checker import TypeChecker, INT, FLOAT, BOOL, STRING, VEC, MAT, VOID, SYM


# ---------------------------------------------------------------------------
# LLVM type mappings
# ---------------------------------------------------------------------------

# We represent Vect types as LLVM IR types:
#   int    → i64
#   float  → double
#   bool   → i1
#   string → i8* (pointer to null-terminated C string)
#   vec    → i8* (pointer to our runtime VectVec struct)
#   mat    → i8* (pointer to our runtime VectMat struct)

INT_T    = ir.IntType(64)
FLOAT_T  = ir.DoubleType()
BOOL_T   = ir.IntType(1)
I32_T    = ir.IntType(32)
I8_T     = ir.IntType(8)
PTR_T    = ir.PointerType(I8_T)   # generic pointer — used for strings, vec, mat
VOID_T   = ir.VoidType()


def vect_type_to_llvm(t: str) -> ir.Type:
    """Map a Vect type string to the corresponding LLVM IR type."""
    if t == INT:    return INT_T
    if t == FLOAT:  return FLOAT_T
    if t == BOOL:   return BOOL_T
    if t in (STRING, VEC, MAT, SYM): return PTR_T
    if t.startswith('vec<') or t.startswith('mat<'): return PTR_T  # typed vectors
    if t == VOID:   return VOID_T
    if t == 'unknown': return FLOAT_T
    return PTR_T   # fallback


# ---------------------------------------------------------------------------
# Code generation error
# ---------------------------------------------------------------------------

class CodegenError(Exception):
    def __init__(self, msg: str, line: int = 0, col: int = 0):
        self.line = line
        self.col = col
        super().__init__(f"Code generation error at line {line}, col {col}: {msg}")


# ---------------------------------------------------------------------------
# Runtime bridge declarations
# These are C functions in our Python runtime module (runtime.py / runtime.c).
# We declare them in LLVM IR as external functions so the JIT can call them.
# ---------------------------------------------------------------------------

def _declare_runtime_functions(module: ir.Module) -> Dict[str, ir.Function]:
    """
    Declare all external C-ABI runtime functions that generated code can call.
    These are implemented in src/runtime.py using ctypes callbacks and
    registered with the JIT execution engine.
    """
    fns = {}

    def decl(name: str, ret: ir.Type, *args: ir.Type) -> ir.Function:
        fn_type = ir.FunctionType(ret, list(args))
        fn = ir.Function(module, fn_type, name=name)
        fns[name] = fn
        return fn

    # I/O
    decl('vect_print_int',    VOID_T, INT_T)
    decl('vect_print_float',  VOID_T, FLOAT_T)
    decl('vect_print_bool',   VOID_T, BOOL_T)
    decl('vect_print_string', VOID_T, PTR_T)
    decl('vect_print_vec',    VOID_T, PTR_T)
    decl('vect_print_mat',    VOID_T, PTR_T)
    decl('vect_input',        PTR_T)

    # Vector construction and operations
    decl('vect_vec_new',      PTR_T,  INT_T)          # (length) → vec*
    decl('vect_vec_set',      VOID_T, PTR_T, INT_T, FLOAT_T)  # (vec*, i, val)
    decl('vect_vec_get',      FLOAT_T, PTR_T, INT_T)  # (vec*, i) → float
    decl('vect_vec_len',      INT_T,  PTR_T)           # (vec*) → int
    decl('vect_vec_add',      PTR_T,  PTR_T, PTR_T)
    decl('vect_vec_sub',      PTR_T,  PTR_T, PTR_T)
    decl('vect_vec_mul_elem', PTR_T,  PTR_T, PTR_T)   # element-wise *
    decl('vect_vec_scale',    PTR_T,  PTR_T, FLOAT_T) # scalar multiply
    decl('vect_vec_dot',      FLOAT_T, PTR_T, PTR_T)  # dot product

    # Matrix construction and operations
    decl('vect_mat_new',      PTR_T,  INT_T, INT_T)   # (rows, cols) → mat*
    decl('vect_mat_set_row',  VOID_T, PTR_T, INT_T, PTR_T)  # (mat*, row, vec*)
    decl('vect_mat_get_row',  PTR_T,  PTR_T, INT_T)   # (mat*, row) → vec*
    decl('vect_mat_mul',      PTR_T,  PTR_T, PTR_T)   # matrix multiply
    decl('vect_mat_add',      PTR_T,  PTR_T, PTR_T)
    decl('vect_mat_sub',      PTR_T,  PTR_T, PTR_T)
    decl('vect_mat_transpose', PTR_T, PTR_T)
    decl('vect_mat_scale',    PTR_T,  PTR_T, FLOAT_T)

    # Symbolic math
    decl('vect_sym_diff',               PTR_T,   PTR_T, PTR_T)
    decl('vect_sym_eval',               FLOAT_T, PTR_T, PTR_T, FLOAT_T)
    decl('vect_sym_integrate',          PTR_T,   PTR_T, PTR_T)
    decl('vect_sym_integrate_definite', FLOAT_T, PTR_T, PTR_T, FLOAT_T, FLOAT_T)

    # Math builtins
    decl('vect_sqrt',  FLOAT_T, FLOAT_T)
    decl('vect_sin',   FLOAT_T, FLOAT_T)
    decl('vect_cos',   FLOAT_T, FLOAT_T)
    decl('vect_tan',   FLOAT_T, FLOAT_T)
    decl('vect_abs_f', FLOAT_T, FLOAT_T)
    decl('vect_floor', INT_T,   FLOAT_T)
    decl('vect_ceil',  INT_T,   FLOAT_T)

    # String operations
    decl('vect_str_concat',  PTR_T, PTR_T, PTR_T)
    decl('vect_int_to_str',  PTR_T, INT_T)
    decl('vect_float_to_str',PTR_T, FLOAT_T)
    decl('vect_str_len',     INT_T,  PTR_T)
    decl('vect_str_upper',   PTR_T,  PTR_T)
    decl('vect_str_lower',   PTR_T,  PTR_T)
    decl('vect_str_contains',BOOL_T, PTR_T, PTR_T)
    decl('vect_str_starts',  BOOL_T, PTR_T, PTR_T)
    decl('vect_str_ends',    BOOL_T, PTR_T, PTR_T)
    decl('vect_str_replace', PTR_T,  PTR_T, PTR_T, PTR_T)
    decl('vect_str_trim',    PTR_T,  PTR_T)
    decl('vect_str_repeat',  PTR_T,  PTR_T, INT_T)

    # Range
    decl('vect_range',       PTR_T, INT_T, INT_T, INT_T)  # (start, stop, step)

    # Vec/Mat stdlib (v2)
    decl('vect_vec_norm',      FLOAT_T, PTR_T)
    decl('vect_vec_cross',     PTR_T,   PTR_T, PTR_T)
    decl('vect_vec_normalize', PTR_T,   PTR_T)
    decl('vect_mat_det',       FLOAT_T, PTR_T)
    decl('vect_mat_inv',       PTR_T,   PTR_T)
    decl('vect_mat_solve',     PTR_T,   PTR_T, PTR_T)
    decl('vect_zeros',         PTR_T,   INT_T)
    decl('vect_ones',          PTR_T,   INT_T)

    # Plot (v2)
    decl('vect_plot_sym', I32_T, PTR_T, PTR_T, FLOAT_T, FLOAT_T, PTR_T)
    decl('vect_plot_vec', I32_T, PTR_T, PTR_T, PTR_T)

    return fns


# ---------------------------------------------------------------------------
# Code generator class
# ---------------------------------------------------------------------------

class CodeGen:
    """
    Walks a type-checked AST and emits LLVM IR.

    Usage:
        cg = CodeGen(type_checker)
        cg.compile(program)
        result = cg.execute()   # JIT-compiles and runs main()
    """

    def __init__(self, checker: TypeChecker):
        self.checker = checker

        # The LLVM module holds all IR for this compilation unit.
        self.module = ir.Module(name='vect_program')
        self.module.triple = llvm.get_default_triple()

        # Declare all runtime functions we might call.
        self.rt = _declare_runtime_functions(self.module)

        # Maps variable name → alloca pointer (ir.AllocaInstr)
        # Each scope is a dict; we use a stack.
        self.var_stack: list = []       # stack of dicts {name: alloca_ptr}

        # Current IR builder — set when entering a function.
        self.builder: Optional[ir.IRBuilder] = None

        # The main function (entry point for the program)
        self.main_fn: Optional[ir.Function] = None

        # User-defined LLVM functions: name → ir.Function
        self.user_fns: Dict[str, ir.Function] = {}

        # Symbolic functions: name → (param_names, expr_AST)
        # These are not compiled to LLVM; they're handled by the runtime.
        self.sym_fns: Dict[str, Any] = {}

        # String literal interning: value → global constant pointer
        self._string_cache: Dict[str, ir.GlobalVariable] = {}

        # Counter for generating unique block names
        self._block_counter = 0

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------

    def _push_scope(self):
        self.var_stack.append({})

    def _pop_scope(self):
        self.var_stack.pop()

    def _define_var(self, name: str, alloca: ir.AllocaInstr):
        self.var_stack[-1][name] = alloca

    def _lookup_var(self, name: str) -> Optional[ir.AllocaInstr]:
        for scope in reversed(self.var_stack):
            if name in scope:
                return scope[name]
        return None

    # ------------------------------------------------------------------
    # Utility: unique block name
    # ------------------------------------------------------------------

    def _unique(self, prefix: str) -> str:
        self._block_counter += 1
        return f'{prefix}_{self._block_counter}'

    # ------------------------------------------------------------------
    # String literal helper
    # ------------------------------------------------------------------

    def _string_const(self, value: str) -> ir.Constant:
        """
        Create (or reuse) a global i8 array for a string literal and
        return a pointer to its first element.
        This is how C string literals work in LLVM IR.
        """
        if value in self._string_cache:
            gv = self._string_cache[value]
        else:
            # Encode to bytes, add null terminator
            encoded = (value + '\0').encode('utf-8')
            arr_type = ir.ArrayType(I8_T, len(encoded))
            gv = ir.GlobalVariable(self.module, arr_type,
                                   name=f'_str_{len(self._string_cache)}')
            gv.global_constant = True
            gv.initializer = ir.Constant(arr_type, bytearray(encoded))
            self._string_cache[value] = gv

        # GEP (Get Element Pointer) to get i8* from [N x i8]*
        zero = ir.Constant(I32_T, 0)
        return self.builder.gep(gv, [zero, zero], inbounds=True)

    # ------------------------------------------------------------------
    # Main compile entry point
    # ------------------------------------------------------------------

    def compile(self, program: Program):
        """
        Compile the entire program.
        First pass: compile only ANNOTATED user functions.
        Inferred (annotation-free) functions are compiled on-demand
        when first called with concrete argument types.
        Second pass: compile top-level statements into main().
        """
        # First pass: compile only fully-annotated functions
        for node in program.body:
            if isinstance(node, FuncDef):
                param_types, ret = self.checker.functions.get(node.name, ([], 'void'))
                has_unknown = 'unknown' in param_types or ret == 'unknown'
                if not has_unknown:
                    self._compile_func_def(node)
            elif isinstance(node, SymbolicFunc):
                self.sym_fns[node.name] = node

        # Build main() — the entry point
        main_type = ir.FunctionType(I32_T, [])
        self.main_fn = ir.Function(self.module, main_type, name='vect_main')
        entry_block = self.main_fn.append_basic_block('entry')
        self.builder = ir.IRBuilder(entry_block)
        self._push_scope()

        for node in program.body:
            if not isinstance(node, (FuncDef, SymbolicFunc)):
                self._compile_stmt(node)

        # Return 0 from main (unless already terminated by a prior branch)
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(I32_T, 0))

        self._pop_scope()

    # ------------------------------------------------------------------
    # Statement compilation
    # ------------------------------------------------------------------

    def _compile_stmt(self, node: Node):
        if isinstance(node, VarDecl):
            self._compile_var_decl(node)
        elif isinstance(node, TupleUnpack):
            self._compile_tuple_unpack(node)
        elif isinstance(node, Assign):
            self._compile_assign(node)
        elif isinstance(node, IndexAssign):
            self._compile_index_assign(node)
        elif isinstance(node, If):
            self._compile_if(node)
        elif isinstance(node, While):
            self._compile_while(node)
        elif isinstance(node, For):
            self._compile_for(node)
        elif isinstance(node, Return):
            self._compile_return(node)
        elif isinstance(node, Break):
            if self._break_target:
                self.builder.branch(self._break_target)
            else:
                raise CodegenError("'break' outside loop", node.line, node.col)
        elif isinstance(node, Continue):
            if self._continue_target:
                self.builder.branch(self._continue_target)
            else:
                raise CodegenError("'continue' outside loop", node.line, node.col)
        elif isinstance(node, ExprStatement):
            self._compile_expr(node.expr)   # discard the value
        else:
            raise CodegenError(
                f"Cannot compile statement: {type(node).__name__}",
                getattr(node, 'line', 0), getattr(node, 'col', 0)
            )

    # Loop control targets (set when entering while/for loops)
    _break_target = None
    _continue_target = None

    def _compile_var_decl(self, node: VarDecl):
        """
        Compile:  var name = expr
        Strategy: evaluate the RHS, alloca a stack slot, store the value.
        """
        val = self._compile_expr(node.value)
        llvm_type = val.type

        # alloca creates a stack slot. The name is just for IR readability.
        alloca = self.builder.alloca(llvm_type, name=node.name)
        self.builder.store(val, alloca)
        self._define_var(node.name, alloca)

    def _compile_assign(self, node: Assign):
        """Compile:  name = expr"""
        alloca = self._lookup_var(node.name)
        if alloca is None:
            raise CodegenError(
                f"Variable '{node.name}' not found (should have been caught by type checker)",
                node.line, node.col
            )
        val = self._compile_expr(node.value)
        # Type-coerce int→double if the slot is a double
        val = self._coerce(val, alloca.type.pointee)
        self.builder.store(val, alloca)

    def _compile_index_assign(self, node: IndexAssign):
        """Compile:  name[index] = expr"""
        alloca = self._lookup_var(node.name)
        vec_ptr = self.builder.load(alloca)
        idx = self._compile_expr(node.index)
        val = self._compile_expr(node.value)
        # Ensure float
        val = self._coerce(val, FLOAT_T)
        self.builder.call(self.rt['vect_vec_set'], [vec_ptr, idx, val])

    def _compile_if(self, node: If):
        """
        Compile if/else using LLVM basic blocks.

        LLVM has no structured control flow — everything is explicit jumps
        between basic blocks.  The pattern is:

            %cond = <condition>
            br %cond, if_true, if_false
          if_true:
            <body>
            br merge
          if_false:          ; only if there's an else
            <else body>
            br merge
          merge:
            <continue>
        """
        cond_val = self._compile_expr(node.condition)
        cond_bool = self._to_bool(cond_val)

        fn = self.builder.function
        then_block  = fn.append_basic_block(self._unique('if_then'))
        merge_block = fn.append_basic_block(self._unique('if_merge'))
        else_block  = fn.append_basic_block(self._unique('if_else')) \
                      if node.else_body else merge_block

        self.builder.cbranch(cond_bool, then_block, else_block)

        # then branch
        self.builder.position_at_end(then_block)
        self._push_scope()
        for stmt in node.body:
            if self.builder.block.is_terminated:
                break
            self._compile_stmt(stmt)
        self._pop_scope()
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        # else branch
        if node.else_body:
            self.builder.position_at_end(else_block)
            self._push_scope()
            for stmt in node.else_body:
                if self.builder.block.is_terminated:
                    break
                self._compile_stmt(stmt)
            self._pop_scope()
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)

    def _compile_while(self, node: While):
        """
        Compile while loop:
            br loop_header
          loop_header:
            %cond = <condition>
            br %cond, loop_body, loop_exit
          loop_body:
            <body>
            br loop_header
          loop_exit:
        """
        fn = self.builder.function
        header_block = fn.append_basic_block(self._unique('while_header'))
        body_block   = fn.append_basic_block(self._unique('while_body'))
        exit_block   = fn.append_basic_block(self._unique('while_exit'))

        self.builder.branch(header_block)
        self.builder.position_at_end(header_block)

        cond_val  = self._compile_expr(node.condition)
        cond_bool = self._to_bool(cond_val)
        self.builder.cbranch(cond_bool, body_block, exit_block)

        # Save/restore loop targets for break/continue
        old_break    = self._break_target
        old_continue = self._continue_target
        self._break_target    = exit_block
        self._continue_target = header_block

        self.builder.position_at_end(body_block)
        self._push_scope()
        for stmt in node.body:
            if self.builder.block.is_terminated:
                break
            self._compile_stmt(stmt)
        self._pop_scope()
        if not self.builder.block.is_terminated:
            self.builder.branch(header_block)

        self._break_target    = old_break
        self._continue_target = old_continue

        self.builder.position_at_end(exit_block)

    def _compile_for(self, node: For):
        """
        Compile for-in loop over a vec (the common case).
        Uses an index counter that runs from 0 to len(vec).
        """
        vec_val = self._compile_expr(node.iterable)

        fn = self.builder.function
        header_block = fn.append_basic_block(self._unique('for_header'))
        body_block   = fn.append_basic_block(self._unique('for_body'))
        exit_block   = fn.append_basic_block(self._unique('for_exit'))

        # Allocate and initialise index counter
        idx_alloca = self.builder.alloca(INT_T, name='_for_idx')
        self.builder.store(ir.Constant(INT_T, 0), idx_alloca)

        # Get the length of the vector
        vec_len = self.builder.call(self.rt['vect_vec_len'], [vec_val])

        self.builder.branch(header_block)
        self.builder.position_at_end(header_block)

        idx_val = self.builder.load(idx_alloca)
        cond = self.builder.icmp_signed('<', idx_val, vec_len)
        self.builder.cbranch(cond, body_block, exit_block)

        old_break    = self._break_target
        old_continue = self._continue_target
        self._break_target    = exit_block
        self._continue_target = header_block

        self.builder.position_at_end(body_block)
        self._push_scope()

        # Load current element and bind to loop variable
        elem_val = self.builder.call(self.rt['vect_vec_get'], [vec_val, idx_val])
        elem_alloca = self.builder.alloca(FLOAT_T, name=node.var)
        self.builder.store(elem_val, elem_alloca)
        self._define_var(node.var, elem_alloca)

        for stmt in node.body:
            if self.builder.block.is_terminated:
                break
            self._compile_stmt(stmt)

        # Increment index
        if not self.builder.block.is_terminated:
            new_idx = self.builder.add(
                self.builder.load(idx_alloca),
                ir.Constant(INT_T, 1)
            )
            self.builder.store(new_idx, idx_alloca)
            self.builder.branch(header_block)

        self._pop_scope()
        self._break_target    = old_break
        self._continue_target = old_continue

        self.builder.position_at_end(exit_block)

    def _compile_return(self, node: Return):
        if node.value is None:
            self.builder.ret_void()
        else:
            val = self._compile_expr(node.value)
            # Coerce to the function's declared return type
            fn = self.builder.function
            ret_type = fn.function_type.return_type
            val = self._coerce(val, ret_type)
            self.builder.ret(val)

    def _compile_tuple_literal(self, node) -> ir.Value:
        """
        Compile (a, b, c) as a vec — stores all elements as float64.
        Elements are coerced to float. Result is a PTR_T vec pointer.
        """
        elements = [self._compile_expr(e) for e in node.elements]
        n = len(elements)
        vec_ptr = self.builder.call(
            self.rt['vect_vec_new'], [ir.Constant(INT_T, n)]
        )
        for i, elem in enumerate(elements):
            val = self._coerce(elem, FLOAT_T)
            self.builder.call(
                self.rt['vect_vec_set'],
                [vec_ptr, ir.Constant(INT_T, i), val]
            )
        return vec_ptr

    def _compile_tuple_unpack(self, node) -> None:
        """
        Compile: var (a, b) = expr
        Gets each element from the tuple vec and stores in separate allocas.
        """
        tup_val = self._compile_expr(node.value)
        for i, name in enumerate(node.names):
            elem = self.builder.call(
                self.rt['vect_vec_get'],
                [tup_val, ir.Constant(INT_T, i)]
            )
            alloca = self.builder.alloca(FLOAT_T, name=name)
            self.builder.store(elem, alloca)
            self._define_var(name, alloca)

    def _compile_func_def(self, node: FuncDef):
        """Compile a user-defined function to an LLVM function."""
        param_types, ret_type = self.checker.functions.get(
            node.name, ([], VOID)
        )
        llvm_params = [vect_type_to_llvm(t) for t in param_types]
        llvm_ret    = vect_type_to_llvm(ret_type)
        fn_type = ir.FunctionType(llvm_ret, llvm_params)
        fn = ir.Function(self.module, fn_type, name=f'vect_user_{node.name}')
        self.user_fns[node.name] = fn

        entry_block = fn.append_basic_block('entry')
        old_builder = self.builder
        self.builder = ir.IRBuilder(entry_block)
        self._push_scope()

        # Allocate stack slots for each parameter
        for param, llvm_arg, vect_t in zip(node.params, fn.args, param_types):
            llvm_arg.name = param.name
            alloca = self.builder.alloca(vect_type_to_llvm(vect_t), name=param.name)
            self.builder.store(llvm_arg, alloca)
            self._define_var(param.name, alloca)

        for stmt in node.body:
            if self.builder.block.is_terminated:
                break
            self._compile_stmt(stmt)

        # Add implicit void return if needed
        if not self.builder.block.is_terminated:
            if llvm_ret == VOID_T:
                self.builder.ret_void()
            else:
                self.builder.ret(ir.Constant(llvm_ret, 0))

        self._pop_scope()
        self.builder = old_builder

    # ------------------------------------------------------------------
    # Expression compilation
    # ------------------------------------------------------------------

    def _compile_inferred_func(self, node: FuncDef, specialized_name: str,
                                param_llvm_types: list):
        """
        Compile a type-inferred function with a specific set of concrete
        LLVM types. This is monomorphization — one compiled version per
        distinct argument type combination.
        """
        # Infer the return type by type-checking the body
        from .type_checker import Env as TCEnv
        func_env = TCEnv(parent=self.checker.global_env)
        vect_param_types = []
        for p, llvm_t in zip(node.params, param_llvm_types):
            if llvm_t == INT_T:    vt = 'int'
            elif llvm_t == FLOAT_T: vt = 'float'
            elif llvm_t == BOOL_T:  vt = 'bool'
            elif llvm_t == PTR_T:   vt = 'string'
            else:                   vt = 'string'
            vect_param_types.append(vt)
            func_env.define(p.name, vt)

        inferred_ret = self.checker._infer_return_type(node.body, func_env)
        ret_vect = inferred_ret if inferred_ret else 'void'
        llvm_ret = vect_type_to_llvm(ret_vect)

        fn_type = ir.FunctionType(llvm_ret, param_llvm_types)
        fn = ir.Function(self.module, fn_type, name=f'vect_user_{specialized_name}')
        self.user_fns[specialized_name] = fn

        entry_block = fn.append_basic_block('entry')
        old_builder = self.builder
        self.builder = ir.IRBuilder(entry_block)
        self._push_scope()

        for param, llvm_arg, llvm_t in zip(node.params, fn.args, param_llvm_types):
            llvm_arg.name = param.name
            alloca = self.builder.alloca(llvm_t, name=param.name)
            self.builder.store(llvm_arg, alloca)
            self._define_var(param.name, alloca)

        for stmt in node.body:
            if self.builder.block.is_terminated:
                break
            self._compile_stmt(stmt)

        if not self.builder.block.is_terminated:
            if llvm_ret == VOID_T:
                self.builder.ret_void()
            else:
                self.builder.ret(ir.Constant(llvm_ret, 0))

        self._pop_scope()
        self.builder = old_builder

    def _compile_expr(self, node: Node) -> ir.Value:
        """Compile an expression node, returning its LLVM IR value."""

        if isinstance(node, IntLiteral):
            return ir.Constant(INT_T, node.value)

        if isinstance(node, FloatLiteral):
            return ir.Constant(FLOAT_T, node.value)

        if isinstance(node, BoolLiteral):
            return ir.Constant(BOOL_T, int(node.value))

        if isinstance(node, StringLiteral):
            return self._string_const(node.value)

        if isinstance(node, TupleLiteral):
            return self._compile_tuple_literal(node)

        if isinstance(node, Identifier):
            return self._compile_identifier(node)

        if isinstance(node, VectorLiteral):
            return self._compile_vector_literal(node)

        if isinstance(node, MatrixLiteral):
            return self._compile_matrix_literal(node)

        if isinstance(node, BinOp):
            return self._compile_binop(node)

        if isinstance(node, UnaryOp):
            return self._compile_unaryop(node)

        if isinstance(node, FuncCall):
            return self._compile_call(node)

        if isinstance(node, IndexAccess):
            return self._compile_index_access(node)

        if isinstance(node, Derivative):
            return self._compile_derivative(node)

        if isinstance(node, SymbolicEval):
            return self._compile_symbolic_eval(node)

        raise CodegenError(
            f"Cannot compile expression: {type(node).__name__}",
            getattr(node, 'line', 0), getattr(node, 'col', 0)
        )

    def _compile_identifier(self, node: Identifier) -> ir.Value:
        alloca = self._lookup_var(node.name)
        if alloca is not None:
            return self.builder.load(alloca, name=node.name)
        # Could be a symbolic function name used in a derivative context
        if node.name in self.sym_fns:
            # Return a pointer to its string representation
            sym_node = self.sym_fns[node.name]
            expr_str = self._ast_to_sym_string(sym_node.expr, sym_node.params)
            return self._string_const(expr_str)
        raise CodegenError(
            f"Variable '{node.name}' not found",
            node.line, node.col
        )

    def _compile_vector_literal(self, node: VectorLiteral) -> ir.Value:
        """
        Compile [e1, e2, e3] by:
        1. Calling vect_vec_new(len) to allocate a runtime vector.
        2. Calling vect_vec_set(ptr, i, val) for each element.
        3. Returning the pointer.
        """
        n = len(node.elements)
        vec_ptr = self.builder.call(
            self.rt['vect_vec_new'],
            [ir.Constant(INT_T, n)]
        )
        for i, elem in enumerate(node.elements):
            val = self._compile_expr(elem)
            val = self._coerce(val, FLOAT_T)
            self.builder.call(
                self.rt['vect_vec_set'],
                [vec_ptr, ir.Constant(INT_T, i), val]
            )
        return vec_ptr

    def _compile_matrix_literal(self, node: MatrixLiteral) -> ir.Value:
        """
        Compile [[row0], [row1], ...] by:
        1. Allocating a matrix.
        2. Compiling each row as a vec and setting it with vect_mat_set_row.
        """
        nrows = len(node.rows)
        ncols = len(node.rows[0].elements) if nrows > 0 else 0
        mat_ptr = self.builder.call(
            self.rt['vect_mat_new'],
            [ir.Constant(INT_T, nrows), ir.Constant(INT_T, ncols)]
        )
        for i, row in enumerate(node.rows):
            row_ptr = self._compile_vector_literal(row)
            self.builder.call(
                self.rt['vect_mat_set_row'],
                [mat_ptr, ir.Constant(INT_T, i), row_ptr]
            )
        return mat_ptr

    def _compile_index_access(self, node: IndexAccess) -> ir.Value:
        obj  = self._compile_expr(node.obj)
        idx  = self._compile_expr(node.index)
        idx  = self._coerce(idx, INT_T)
        return self.builder.call(self.rt['vect_vec_get'], [obj, idx])

    def _compile_binop(self, node: BinOp) -> ir.Value:
        """
        Compile binary operations.
        Numeric ops use LLVM integer/float arithmetic instructions.
        Vector/matrix ops call runtime functions.
        """
        op = node.op

        # Short-circuit logical ops (and/or) — evaluate lazily
        if op == 'and':
            return self._compile_short_circuit(node, is_and=True)
        if op == 'or':
            return self._compile_short_circuit(node, is_and=False)

        left  = self._compile_expr(node.left)
        right = self._compile_expr(node.right)

        left_type  = left.type
        right_type = right.type

        # --- Vector/matrix operations ---
        if left_type == PTR_T or right_type == PTR_T:
            return self._compile_ptr_binop(op, left, right, node)

        # --- Mixed int/float: promote int to float ---
        if left_type == INT_T and right_type == FLOAT_T:
            left = self.builder.sitofp(left, FLOAT_T)
            left_type = FLOAT_T
        elif left_type == FLOAT_T and right_type == INT_T:
            right = self.builder.sitofp(right, FLOAT_T)
            right_type = FLOAT_T

        is_float = (left_type == FLOAT_T)

        # Arithmetic
        if op == '+':
            return self.builder.fadd(left, right) if is_float \
                   else self.builder.add(left, right)
        if op == '-':
            return self.builder.fsub(left, right) if is_float \
                   else self.builder.sub(left, right)
        if op == '*':
            return self.builder.fmul(left, right) if is_float \
                   else self.builder.mul(left, right)
        if op == '/':
            return self.builder.fdiv(left, right) if is_float \
                   else self.builder.sdiv(left, right)
        if op == '%':
            return self.builder.frem(left, right) if is_float \
                   else self.builder.srem(left, right)
        if op == '**':
            # Power: convert to float, call pow-like runtime
            lf = self.builder.sitofp(left, FLOAT_T) if not is_float else left
            rf = self.builder.sitofp(right, FLOAT_T) if right_type != FLOAT_T else right
            pow_fn = self._get_or_declare_pow()
            return self.builder.call(pow_fn, [lf, rf])

        # Comparisons
        if op in ('==', '!=', '<', '<=', '>', '>='):
            if is_float:
                pred_map = {'==': '==', '!=': '!=', '<': '<',
                            '<=': '<=', '>': '>', '>=': '>='}
                return self.builder.fcmp_ordered(pred_map[op], left, right)
            else:
                return self.builder.icmp_signed(op, left, right)

        raise CodegenError(f"Unknown operator '{op}'", node.line, node.col)

    def _compile_ptr_binop(self, op, left, right, node):
        """Handle operations where one or both operands are pointers (vec/mat/string)."""
        rt = self.rt

        # Determine Vect-level types so we can distinguish string from vec/mat
        left_vt  = self._vect_type_of(node.left)
        right_vt = self._vect_type_of(node.right)

        # string + string concatenation — must check BEFORE vec ops
        if op == '+' and (left_vt == STRING or right_vt == STRING):
            return self.builder.call(rt['vect_str_concat'], [left, right])

        # vec op vec
        if left.type == PTR_T and right.type == PTR_T:
            if op == '+': return self.builder.call(rt['vect_vec_add'], [left, right])
            if op == '-': return self.builder.call(rt['vect_vec_sub'], [left, right])
            if op == '*': return self.builder.call(rt['vect_vec_mul_elem'], [left, right])
            if op == '@': return self.builder.call(rt['vect_mat_mul'], [left, right])
            if op == '·': return self.builder.call(rt['vect_vec_dot'], [left, right])

        # vec * scalar  or  scalar * vec
        if left.type == PTR_T and right.type in (INT_T, FLOAT_T):
            scalar = self._coerce(right, FLOAT_T)
            if op == '*': return self.builder.call(rt['vect_vec_scale'], [left, scalar])
        if left.type in (INT_T, FLOAT_T) and right.type == PTR_T:
            scalar = self._coerce(left, FLOAT_T)
            if op == '*': return self.builder.call(rt['vect_vec_scale'], [right, scalar])

        # fallback string concat
        if op == '+':
            return self.builder.call(rt['vect_str_concat'], [left, right])

        raise CodegenError(
            f"Operator '{op}' not supported for these operand types.",
            node.line, node.col
        )

    def _compile_short_circuit(self, node: BinOp, is_and: bool) -> ir.Value:
        """
        Compile 'and'/'or' with short-circuit evaluation.
        For 'and': if left is false, skip right.
        For 'or':  if left is true,  skip right.
        """
        fn = self.builder.function
        right_block = fn.append_basic_block(self._unique('sc_right'))
        merge_block = fn.append_basic_block(self._unique('sc_merge'))

        left_val  = self._compile_expr(node.left)
        left_bool = self._to_bool(left_val)
        left_block = self.builder.block

        if is_and:
            self.builder.cbranch(left_bool, right_block, merge_block)
        else:
            self.builder.cbranch(left_bool, merge_block, right_block)

        self.builder.position_at_end(right_block)
        right_val  = self._compile_expr(node.right)
        right_bool = self._to_bool(right_val)
        right_block_end = self.builder.block
        self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(BOOL_T, name='sc_result')
        if is_and:
            phi.add_incoming(ir.Constant(BOOL_T, 0), left_block)
        else:
            phi.add_incoming(ir.Constant(BOOL_T, 1), left_block)
        phi.add_incoming(right_bool, right_block_end)
        return phi

    def _compile_unaryop(self, node: UnaryOp) -> ir.Value:
        val = self._compile_expr(node.operand)
        if node.op == '-':
            if val.type == INT_T:
                return self.builder.neg(val)
            if val.type == FLOAT_T:
                return self.builder.fneg(val)
        if node.op == 'not':
            b = self._to_bool(val)
            return self.builder.not_(b)
        raise CodegenError(f"Unknown unary op '{node.op}'", node.line, node.col)

    def _compile_call(self, node: FuncCall) -> ir.Value:
        """Compile function calls — both built-ins and user-defined."""
        name = node.name

        # --- integral must be handled BEFORE args are compiled ---
        # because its first arg contains unbound symbolic variables
        if name == 'integral':
            expr_str = self._ast_to_sym_string(node.args[0], [])
            expr_ptr = self._string_const(expr_str)
            var_arg = node.args[1]
            if isinstance(var_arg, Identifier):
                var_ptr = self._string_const(var_arg.name)
            elif isinstance(var_arg, StringLiteral):
                var_ptr = self._string_const(var_arg.value)
            else:
                var_ptr = self._compile_expr(var_arg)
            if len(node.args) == 2:
                return self.builder.call(
                    self.rt['vect_sym_integrate'], [expr_ptr, var_ptr])
            else:
                lo = self._coerce(self._compile_expr(node.args[2]), FLOAT_T)
                hi = self._coerce(self._compile_expr(node.args[3]), FLOAT_T)
                return self.builder.call(
                    self.rt['vect_sym_integrate_definite'],
                    [expr_ptr, var_ptr, lo, hi])

        # --- plot — also before args, sym expr contains unbound vars ---
        if name == 'plot':
            expr_str = self._ast_to_sym_string(node.args[0], [])
            expr_ptr = self._string_const(expr_str)
            var_arg  = node.args[1]
            var_ptr  = self._string_const(
                var_arg.name if isinstance(var_arg, Identifier) else 'x')
            lo = self._coerce(self._compile_expr(node.args[2]), FLOAT_T)
            hi = self._coerce(self._compile_expr(node.args[3]), FLOAT_T)
            title_ptr = self._string_const(
                node.args[4].value if len(node.args) >= 5
                and isinstance(node.args[4], StringLiteral) else '')
            return self.builder.call(
                self.rt['vect_plot_sym'],
                [expr_ptr, var_ptr, lo, hi, title_ptr])

        if name == 'plot_xy':
            x_vec = self._compile_expr(node.args[0])
            y_vec = self._compile_expr(node.args[1])
            title_ptr = self._string_const(
                node.args[2].value if len(node.args) >= 3
                and isinstance(node.args[2], StringLiteral) else '')
            return self.builder.call(
                self.rt['vect_plot_vec'], [x_vec, y_vec, title_ptr])

        args = [self._compile_expr(a) for a in node.args]

        # --- print ---
        if name == 'print':
            for arg, arg_node in zip(args, node.args):
                self._emit_print(arg, arg_node)
            return ir.Constant(I32_T, 0)  # void, return dummy

        # --- input ---
        if name == 'input':
            return self.builder.call(self.rt['vect_input'], [])

        # --- math builtins ---
        math_map = {
            'sqrt': 'vect_sqrt', 'sin': 'vect_sin', 'cos': 'vect_cos',
            'tan': 'vect_tan', 'abs': 'vect_abs_f',
            'floor': 'vect_floor', 'ceil': 'vect_ceil',
        }
        if name in math_map:
            a = self._coerce(args[0], FLOAT_T)
            return self.builder.call(self.rt[math_map[name]], [a])

        # --- type conversions ---
        if name == 'int':
            a = args[0]
            if a.type == FLOAT_T: return self.builder.fptosi(a, INT_T)
            if a.type == BOOL_T:  return self.builder.zext(a, INT_T)
            return a  # already int
        if name == 'float':
            a = args[0]
            if a.type == INT_T:  return self.builder.sitofp(a, FLOAT_T)
            if a.type == BOOL_T: return self.builder.uitofp(a, FLOAT_T)
            return a
        if name == 'str':
            a = args[0]
            if a.type == INT_T:   return self.builder.call(self.rt['vect_int_to_str'], [a])
            if a.type == FLOAT_T: return self.builder.call(self.rt['vect_float_to_str'], [a])
            if a.type == BOOL_T:
                as_int = self.builder.zext(a, INT_T)
                return self.builder.call(self.rt['vect_int_to_str'], [as_int])
            return a  # already a string/pointer — return as-is

        # --- string operations (v4) ---
        str_unary = {
            'str_len':     ('vect_str_len',     INT_T),
            'str_upper':   ('vect_str_upper',   PTR_T),
            'str_lower':   ('vect_str_lower',   PTR_T),
            'str_trim':    ('vect_str_trim',     PTR_T),
        }
        if name in str_unary:
            rt_name, _ = str_unary[name]
            return self.builder.call(self.rt[rt_name], [args[0]])

        str_binary = {
            'str_contains': ('vect_str_contains', BOOL_T),
            'str_starts':   ('vect_str_starts',   BOOL_T),
            'str_ends':     ('vect_str_ends',     BOOL_T),
            'str_repeat':   ('vect_str_repeat',   PTR_T),
        }
        if name in str_binary:
            rt_name, _ = str_binary[name]
            a0 = args[0]
            a1 = self._coerce(args[1], INT_T) if name == 'str_repeat' else args[1]
            return self.builder.call(self.rt[rt_name], [a0, a1])

        if name == 'str_replace':
            return self.builder.call(self.rt['vect_str_replace'],
                                     [args[0], args[1], args[2]])

        # --- transpose ---
        if name == 'transpose':
            return self.builder.call(self.rt['vect_mat_transpose'], [args[0]])

        # --- len ---
        if name == 'len':
            return self.builder.call(self.rt['vect_vec_len'], [args[0]])

        # --- range ---
        if name == 'range':
            if len(args) == 1:
                start = ir.Constant(INT_T, 0)
                stop  = self._coerce(args[0], INT_T)
                step  = ir.Constant(INT_T, 1)
            elif len(args) == 2:
                start = self._coerce(args[0], INT_T)
                stop  = self._coerce(args[1], INT_T)
                step  = ir.Constant(INT_T, 1)
            else:
                start = self._coerce(args[0], INT_T)
                stop  = self._coerce(args[1], INT_T)
                step  = self._coerce(args[2], INT_T)
            return self.builder.call(self.rt['vect_range'], [start, stop, step])

        # --- vec/mat stdlib (v2) ---
        if name == 'norm':
            return self.builder.call(self.rt['vect_vec_norm'], [args[0]])
        if name == 'cross':
            return self.builder.call(self.rt['vect_vec_cross'], [args[0], args[1]])
        if name == 'normalize':
            return self.builder.call(self.rt['vect_vec_normalize'], [args[0]])
        if name == 'det':
            return self.builder.call(self.rt['vect_mat_det'], [args[0]])
        if name == 'inv':
            return self.builder.call(self.rt['vect_mat_inv'], [args[0]])
        if name == 'solve':
            return self.builder.call(self.rt['vect_mat_solve'], [args[0], args[1]])
        if name == 'zeros':
            n = self._coerce(args[0], INT_T)
            return self.builder.call(self.rt['vect_zeros'], [n])
        if name == 'ones':
            n = self._coerce(args[0], INT_T)
            return self.builder.call(self.rt['vect_ones'], [n])

        # --- symbolic integration ---
        # integral(expr, "var")           → symbolic antiderivative (sym)
        # integral(expr, "var", lo, hi)   → definite integral (float)
        if name == 'integral':
            # Build the expression string from the first argument AST
            # without compiling it (it may contain unbound symbolic vars)
            expr_str = self._ast_to_sym_string(node.args[0], [])
            expr_ptr = self._string_const(expr_str)
            # Second arg is the variable name
            var_arg = node.args[1]
            if isinstance(var_arg, Identifier):
                var_ptr = self._string_const(var_arg.name)
            elif isinstance(var_arg, StringLiteral):
                var_ptr = self._string_const(var_arg.value)
            else:
                var_ptr = self._compile_expr(var_arg)
            if len(node.args) == 2:
                return self.builder.call(
                    self.rt['vect_sym_integrate'], [expr_ptr, var_ptr])
            else:
                lo = self._coerce(self._compile_expr(node.args[2]), FLOAT_T)
                hi = self._coerce(self._compile_expr(node.args[3]), FLOAT_T)
                return self.builder.call(
                    self.rt['vect_sym_integrate_definite'],
                    [expr_ptr, var_ptr, lo, hi])

        # --- user-defined function (annotated) ---
        if name in self.user_fns:
            fn = self.user_fns[name]
            coerced_args = []
            for arg, param_type in zip(args, fn.function_type.args):
                coerced_args.append(self._coerce(arg, param_type))
            return self.builder.call(fn, coerced_args)

        # --- inferred function (no annotations) — monomorphize per call ---
        if name in self.checker._func_nodes:
            node_ast = self.checker._func_nodes[name]
            param_types_inferred = [a.type for a in args]
            # Build a unique name for this specialization
            type_sig = '_'.join(
                'i' if t == INT_T else 'f' if t == FLOAT_T
                else 'b' if t == BOOL_T else 'p'
                for t in param_types_inferred
            )
            specialized_name = f'{name}_{type_sig}'
            if specialized_name not in self.user_fns:
                self._compile_inferred_func(node_ast, specialized_name,
                                             param_types_inferred)
            fn = self.user_fns[specialized_name]
            coerced_args = []
            for arg, param_type in zip(args, fn.function_type.args):
                # Don't coerce pointer types — they are already the right type
                if arg.type == PTR_T or param_type == PTR_T:
                    coerced_args.append(arg)
                else:
                    coerced_args.append(self._coerce(arg, param_type))
            return self.builder.call(fn, coerced_args)

        raise CodegenError(
            f"Unknown function '{name}'",
            node.line, node.col
        )

    def _emit_print(self, val: ir.Value, arg_node: Node):
        """
        Dispatch to the correct vect_print_* runtime function.
        We infer the Vect-level type from the AST node so we can call
        the right handler — vect_print_vec, vect_print_mat, etc.
        This matters because at the LLVM IR level, vec/mat/string are
        all i8* and look identical.
        """
        rt = self.rt
        t = val.type

        if t == INT_T:
            self.builder.call(rt['vect_print_int'], [val])
        elif t == FLOAT_T:
            self.builder.call(rt['vect_print_float'], [val])
        elif t == BOOL_T:
            self.builder.call(rt['vect_print_bool'], [val])
        elif t == PTR_T:
            # Determine the Vect-level type from the AST node
            vect_t = self._vect_type_of(arg_node)
            if vect_t == VEC:
                self.builder.call(rt['vect_print_vec'], [val])
            elif vect_t == MAT:
                self.builder.call(rt['vect_print_mat'], [val])
            elif vect_t == SYM:
                self.builder.call(rt['vect_print_string'], [val])
            else:
                # STRING or unknown pointer — use print_string
                self.builder.call(rt['vect_print_string'], [val])
        else:
            self.builder.call(rt['vect_print_int'], [val])

    def _vect_type_of(self, node: Node) -> str:
        """Lightweight type inference for print dispatch etc."""
        if isinstance(node, IntLiteral):     return INT
        if isinstance(node, FloatLiteral):   return FLOAT
        if isinstance(node, BoolLiteral):    return BOOL
        if isinstance(node, StringLiteral):  return STRING
        if isinstance(node, VectorLiteral):
            if node.elements and isinstance(node.elements[0], IntLiteral):
                return 'vec<int>'
            return VEC
        if isinstance(node, MatrixLiteral):  return MAT
        if isinstance(node, Derivative):     return SYM
        if isinstance(node, SymbolicEval):   return FLOAT

        if isinstance(node, Identifier):
            # Look up in alloca map — the LLVM type tells us what it is
            alloca = self._lookup_var(node.name)
            if alloca is not None:
                lt = alloca.type.pointee
                if lt == INT_T:   return INT
                if lt == FLOAT_T: return FLOAT
                if lt == BOOL_T:  return BOOL
                # PTR_T — could be vec, mat, string, or sym
                # Check the type checker's symbol table
                t = self.checker.global_env.lookup(node.name)
                if t: return t
                return STRING
            # Might be a symbolic function name
            if node.name in self.sym_fns:
                return SYM
            return STRING

        if isinstance(node, BinOp):
            op = node.op
            lt = self._vect_type_of(node.left)
            rt = self._vect_type_of(node.right)
            if op == '@':  return MAT
            if op == '·':  return FLOAT
            if lt == VEC or rt == VEC:  return VEC
            if lt == MAT or rt == MAT:  return MAT
            if lt == FLOAT or rt == FLOAT: return FLOAT
            if lt == INT and rt == INT: return INT
            return FLOAT

        if isinstance(node, UnaryOp):
            return self._vect_type_of(node.operand)

        if isinstance(node, FuncCall):
            name = node.name
            # Built-in returns
            builtin_returns = {
                'print': VOID, 'input': STRING, 'len': INT,
                'sqrt': FLOAT, 'sin': FLOAT, 'cos': FLOAT,
                'tan': FLOAT, 'abs': FLOAT, 'floor': INT, 'ceil': INT,
                'int': INT, 'float': FLOAT, 'str': STRING,
                'range': VEC, 'transpose': MAT, 'dot': FLOAT,
                'zeros': VEC, 'ones': VEC,
                # v2 stdlib
                'norm': FLOAT, 'cross': VEC, 'normalize': VEC,
                'det': FLOAT, 'inv': MAT, 'solve': VEC,
                'integral': SYM, 'plot': VOID,
            }
            if name in builtin_returns:
                return builtin_returns[name]
            # User function
            if name in self.checker.functions:
                _, ret = self.checker.functions[name]
                return ret
            return FLOAT

        if isinstance(node, IndexAccess):
            obj_t = self._vect_type_of(node.obj)
            if obj_t == MAT: return VEC
            if obj_t == VEC: return FLOAT
            return STRING

        return STRING  # safe fallback

    def _compile_derivative(self, node: Derivative) -> ir.Value:
        """
        Compile d/dx(expr).

        Strategy: convert the expression AST to a sympy-compatible string,
        pass it (along with the variable name) to the runtime function
        vect_sym_diff, which uses sympy to differentiate and returns a
        string representation of the result.

        The result is a PTR_T (i8*) pointing to the sympy expression string.
        The user can then pass it to eval(...) to get a concrete float.
        """
        expr_str = self._ast_to_sym_string(node.expr, [node.variable])
        var_str  = node.variable

        expr_ptr = self._string_const(expr_str)
        var_ptr  = self._string_const(var_str)

        return self.builder.call(
            self.rt['vect_sym_diff'],
            [expr_ptr, var_ptr]
        )

    def _compile_symbolic_eval(self, node: SymbolicEval) -> ir.Value:
        """
        Compile eval(sym_expr, x=val).

        For simple single-variable evaluation, we call vect_sym_eval(expr, var, val).
        For multi-variable, we chain calls.
        """
        expr_val = self._compile_expr(node.expr)

        # Handle single binding (the common case)
        if len(node.bindings) == 1:
            var_name, val_expr = node.bindings[0]
            val = self._compile_expr(val_expr)
            val = self._coerce(val, FLOAT_T)
            var_ptr = self._string_const(var_name)
            return self.builder.call(
                self.rt['vect_sym_eval'],
                [expr_val, var_ptr, val]
            )

        # Multiple bindings: chain eval calls
        result = expr_val
        for var_name, val_expr in node.bindings:
            val = self._compile_expr(val_expr)
            val = self._coerce(val, FLOAT_T)
            var_ptr = self._string_const(var_name)
            result = self.builder.call(
                self.rt['vect_sym_eval'],
                [result, var_ptr, val]
            )
        return result

    def _ast_to_sym_string(self, node: Node, sym_vars: list) -> str:
        """
        Convert an AST expression node to a sympy-parseable string.
        This is called at compile time to build the string we'll pass
        to the sympy runtime.
        """
        if isinstance(node, IntLiteral):
            return str(node.value)
        if isinstance(node, FloatLiteral):
            return str(node.value)
        if isinstance(node, Identifier):
            return node.name
        if isinstance(node, BinOp):
            op_map = {'*': '*', '+': '+', '-': '-', '/': '/', '**': '**'}
            op = op_map.get(node.op, node.op)
            l = self._ast_to_sym_string(node.left, sym_vars)
            r = self._ast_to_sym_string(node.right, sym_vars)
            return f'({l} {op} {r})'
        if isinstance(node, UnaryOp):
            if node.op == '-':
                return f'(-{self._ast_to_sym_string(node.operand, sym_vars)})'
        if isinstance(node, FuncCall):
            # Called symbolic function: substitute its expression
            if node.name in self.sym_fns:
                sym_fn = self.sym_fns[node.name]
                return self._ast_to_sym_string(sym_fn.expr, sym_fn.params)
            # Math function
            args = ', '.join(self._ast_to_sym_string(a, sym_vars) for a in node.args)
            return f'{node.name}({args})'
        return '0'

    # ------------------------------------------------------------------
    # Helper: coerce an IR value to a target type
    # ------------------------------------------------------------------

    def _coerce(self, val: ir.Value, target: ir.Type) -> ir.Value:
        """Cast val to target if needed.  Handles int↔float conversion."""
        if val.type == target:
            return val
        if val.type == INT_T and target == FLOAT_T:
            return self.builder.sitofp(val, FLOAT_T)
        if val.type == FLOAT_T and target == INT_T:
            return self.builder.fptosi(val, INT_T)
        if val.type == BOOL_T and target == INT_T:
            return self.builder.zext(val, INT_T)
        if val.type == BOOL_T and target == FLOAT_T:
            return self.builder.uitofp(val, FLOAT_T)
        if val.type == INT_T and target == BOOL_T:
            return self.builder.icmp_signed('!=', val, ir.Constant(INT_T, 0))
        return val  # best-effort, let LLVM verify

    def _to_bool(self, val: ir.Value) -> ir.Value:
        """Convert any value to i1 (bool) for use in branch conditions."""
        if val.type == BOOL_T:
            return val
        if val.type == INT_T:
            return self.builder.icmp_signed('!=', val, ir.Constant(INT_T, 0))
        if val.type == FLOAT_T:
            return self.builder.fcmp_ordered('!=', val, ir.Constant(FLOAT_T, 0.0))
        # pointer: non-null check
        null = ir.Constant(PTR_T, None)
        return self.builder.icmp_unsigned('!=', val, null)

    def _get_or_declare_pow(self) -> ir.Function:
        """Get or declare the llvm.pow intrinsic for float power operations."""
        name = 'llvm.pow.f64'
        if name in self.module.globals:
            return self.module.globals[name]
        fn_type = ir.FunctionType(FLOAT_T, [FLOAT_T, FLOAT_T])
        return ir.Function(self.module, fn_type, name=name)

    # ------------------------------------------------------------------
    # JIT execution
    # ------------------------------------------------------------------

    def execute(self, runtime_symbols: dict) -> int:
        """
        JIT-compile the module and run vect_main().

        runtime_symbols: dict mapping function name → ctypes function pointer.
        These are the Python runtime functions declared as external in LLVM IR.
        """
        # Initialise LLVM targets (safe to call multiple times)
        llvm.initialize()
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()

        # Parse and verify the IR we built
        ir_str = str(self.module)
        try:
            llvm_mod = llvm.parse_assembly(ir_str)
        except Exception as e:
            raise CodegenError(f"LLVM IR parse error: {e}")

        llvm_mod.verify()

        # Create a target machine for the current CPU
        target    = llvm.Target.from_default_triple()
        target_machine = target.create_target_machine(opt=2)

        # Build a JIT execution engine (MCJIT)
        engine = llvm.create_mcjit_compiler(llvm_mod, target_machine)

        # Register all runtime symbol pointers BEFORE finalising.
        # add_global_mapping(ValueRef, int_address) maps the declared
        # external function to the actual Python callback address.
        for sym_name, fn_ptr in runtime_symbols.items():
            if sym_name.startswith('_'):
                continue  # skip internal keys like _keep_alive
            try:
                fn_ref = llvm_mod.get_function(sym_name)
                addr = ctypes.cast(fn_ptr, ctypes.c_void_p).value
                if addr is not None:
                    engine.add_global_mapping(fn_ref, addr)
            except Exception:
                pass  # symbol not used in this module — that's fine

        engine.finalize_object()
        engine.run_static_constructors()

        # Look up and call vect_main
        main_ptr = engine.get_function_address('vect_main')
        main_fn  = ctypes.CFUNCTYPE(ctypes.c_int)(main_ptr)
        return main_fn()

    def get_ir(self) -> str:
        """Return the LLVM IR as a string (useful for debugging)."""
        return str(self.module)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compile_and_run(program: Program, checker: TypeChecker,
                    runtime_symbols: dict) -> int:
    """
    Compile a type-checked program and run it.
    Returns the exit code.
    """
    cg = CodeGen(checker)
    cg.compile(program)
    return cg.execute(runtime_symbols)
