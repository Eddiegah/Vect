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

# Keep the runtime symbols alive for the process lifetime
_runtime_symbols = None


def _get_runtime():
    global _runtime_symbols
    if _runtime_symbols is None:
        _runtime_symbols = build_runtime()
    return _runtime_symbols


def run_source(source: str, filename: str = '<input>') -> int:
    """
    Full pipeline: parse → type-check → codegen → execute.
    Returns the program's exit code (0 on success).
    Raises LexError / ParseError / TypeError / CodegenError on failure.
    """
    reset_registry()   # fresh object registry for each run
    program = _parse(source, filename)
    checker = type_check(program)
    rt = _get_runtime()
    cg = CodeGen(checker)
    cg.compile(program)
    return cg.execute(rt)


def check_source(source: str, filename: str = '<input>'):
    """Parse and type-check only (no execution). Raises on error."""
    program = _parse(source, filename)
    type_check(program)


def get_ir(source: str, filename: str = '<input>') -> str:
    """Return the LLVM IR string for a source program."""
    program = _parse(source, filename)
    checker = type_check(program)
    cg = CodeGen(checker)
    cg.compile(program)
    return cg.get_ir()


def _parse(source: str, filename: str):
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse_program()
