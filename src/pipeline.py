"""
pipeline.py — Glues together lexer → parser → type checker → codegen → runtime.

This is the main compilation pipeline.  Call run_source() to go from source
text to execution result.
"""

from .lexer import tokenize, LexError
from .parser import Parser, ParseError
from .type_checker import type_check, TypeError
from .codegen import CodeGen, CodegenError
from .runtime import build_runtime, reset_registry
from .ast_nodes import Import, FuncDef, SymbolicFunc, Program

# Keep the runtime symbols alive for the process lifetime
_runtime_symbols = None


def _get_runtime():
    global _runtime_symbols
    if _runtime_symbols is None:
        _runtime_symbols = build_runtime()
    return _runtime_symbols


def run_source(source: str, filename: str = '<input>') -> int:
    """
    Full pipeline: parse → resolve imports → type-check → codegen → execute.
    Returns the program's exit code (0 on success).
    """
    reset_registry()
    program = _parse_and_resolve(source, filename)
    checker = type_check(program)
    rt = _get_runtime()
    cg = CodeGen(checker)
    cg.compile(program)
    return cg.execute(rt)


def check_source(source: str, filename: str = '<input>'):
    """Parse, resolve imports, and type-check only. Raises on error."""
    program = _parse_and_resolve(source, filename)
    type_check(program)


def get_ir(source: str, filename: str = '<input>') -> str:
    """Return the LLVM IR string for a source program."""
    program = _parse_and_resolve(source, filename)
    checker = type_check(program)
    cg = CodeGen(checker)
    cg.compile(program)
    return cg.get_ir()


def _parse(source: str, filename: str) -> Program:
    """Parse only — used by REPL and AOT (which handle imports separately)."""
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse_program()


def _parse_and_resolve(source: str, filename: str,
                       _seen: set = None) -> Program:
    """
    Parse source and recursively resolve all import statements.

    Strategy:
    - Parse the file normally — Import nodes end up in program.body
    - For each Import node, find and parse the imported file
    - Extract only fn and sym declarations from imported programs
    - Inject them at the TOP of the current program body (so they are
      available to everything below, regardless of import position)
    - Guard against circular imports with _seen set

    Only fn and sym export — variables stay local to their file.
    This is the right design for v1: share functions and math definitions,
    not mutable state.
    """
    import os

    if _seen is None:
        _seen = set()

    # Resolve the filename to an absolute path for cycle detection
    abs_filename = os.path.abspath(filename) if filename != '<input>' else filename
    if abs_filename in _seen:
        return Program(body=[], line=0, col=0)  # circular import — skip
    _seen.add(abs_filename)

    # Parse this file
    tokens = tokenize(source)
    parser = Parser(tokens)
    program = parser.parse_program()

    # Separate import nodes from the rest of the body
    imports    = [n for n in program.body if isinstance(n, Import)]
    non_import = [n for n in program.body if not isinstance(n, Import)]

    injected = []  # fn/sym from imported files, in order

    for imp in imports:
        # Resolve the path relative to the current file's directory
        if filename != '<input>':
            base_dir = os.path.dirname(os.path.abspath(filename))
        else:
            base_dir = os.getcwd()

        imp_path = os.path.join(base_dir, imp.path)

        if not os.path.exists(imp_path):
            # Also try relative to the current working directory
            imp_path_cwd = os.path.join(os.getcwd(), imp.path)
            if os.path.exists(imp_path_cwd):
                imp_path = imp_path_cwd
            else:
                raise ParseError(
                    f"Cannot find imported file '{imp.path}'.\n"
                    f"  Tried: {imp_path}\n"
                    f"  Tried: {imp_path_cwd}\n"
                    f"  Make sure the path is relative to the importing file "
                    f"or the project root.",
                    imp.line, imp.col
                )

        with open(imp_path, encoding='utf-8') as f:
            imp_source = f.read()

        # Recursively resolve the imported file's own imports
        imp_program = _parse_and_resolve(imp_source, imp_path, _seen)

        # Extract only exportable declarations
        for node in imp_program.body:
            if isinstance(node, (FuncDef, SymbolicFunc)):
                injected.append(node)

    # Rebuild body: injected definitions first, then this file's body
    program.body = injected + non_import
    return program
