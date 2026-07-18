"""
repl.py — Interactive REPL (Read-Eval-Print Loop) for Vect.

Run with: vect   (no arguments)

The REPL maintains a persistent environment — variables and functions
defined in one line are available in subsequent lines.  This is
implemented by accumulating all previous statements and re-compiling
the full program each time (simple and reliable for v1).
"""

import sys
import io
import contextlib

import click

from .pipeline import run_source, _parse
from .lexer import LexError
from .parser import ParseError
from .type_checker import type_check, TypeError as VectTypeError, MultiTypeError
from .codegen import CodeGen, CodegenError
from .runtime import build_runtime, reset_registry

# ANSI colour helpers (fall back gracefully on Windows without colorama)
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
    def _red(s):    return Fore.RED + s + Style.RESET_ALL
    def _green(s):  return Fore.GREEN + s + Style.RESET_ALL
    def _cyan(s):   return Fore.CYAN + s + Style.RESET_ALL
    def _yellow(s): return Fore.YELLOW + s + Style.RESET_ALL
    def _bold(s):   return Style.BRIGHT + s + Style.RESET_ALL
except ImportError:
    def _red(s):    return s
    def _green(s):  return s
    def _cyan(s):   return s
    def _yellow(s): return s
    def _bold(s):   return s

BANNER = r"""
__   __       _
\ \ / /__ ___| |_
 \ V / -_) _|  _|
  \_/\___\__|\__|

""" + _cyan("Vect 0.1.0") + " — a language with native scientific computing\n" + \
      _yellow("Type 'help' for tips, 'exit' to quit.\n")

HELP_TEXT = """
Available commands:
  help          Show this message
  exit / quit   Exit the REPL
  clear         Clear the session (forget all variables/functions)
  ir            Show LLVM IR for the last statement

Vect quick reference:
  var x = 42                     Declare a variable
  fn add(a: int, b: int) -> int  Define a function
  v = [1.0, 2.0, 3.0]           Vector literal
  A = [[1,2],[3,4]]              Matrix literal
  v1 · v2                        Dot product
  A @ B                          Matrix multiply
  T(A)                           Transpose
  sym f(x) = x**2 + 3*x         Symbolic function
  d/dx(f(x))                     Differentiate
  eval(expr, x=2.0)              Evaluate symbolic expr
"""

_MULTILINE_OPENERS = ('{',)  # lines ending with { need continuation


def _needs_continuation(line: str) -> bool:
    """Return True if the line looks like it opens a block (needs more input)."""
    stripped = line.rstrip()
    return stripped.endswith('{') and stripped.count('{') > stripped.count('}')


def _count_open_braces(text: str) -> int:
    return text.count('{') - text.count('}')


class Repl:
    def __init__(self):
        self._history: list[str] = []   # lines of accepted code
        self._rt = build_runtime()
        self._last_ir: str = ''

    def run(self):
        click.echo(BANNER)
        while True:
            try:
                line = self._read_input()
            except (EOFError, KeyboardInterrupt):
                click.echo('\nBye!')
                break

            if not line.strip():
                continue

            cmd = line.strip().lower()
            if cmd in ('exit', 'quit'):
                click.echo('Bye!')
                break
            if cmd == 'help':
                click.echo(HELP_TEXT)
                continue
            if cmd == 'clear':
                self._history.clear()
                reset_registry()
                click.echo(_green('Session cleared.'))
                continue
            if cmd == 'ir':
                if self._last_ir:
                    click.echo(_cyan(self._last_ir))
                else:
                    click.echo('No IR available yet.')
                continue

            self._execute(line)

    def _read_input(self) -> str:
        """
        Read one logical statement, handling multi-line blocks.
        Shows '...' prompt when inside an open brace block.
        """
        line = input(_bold('vect') + _cyan('> '))
        if _count_open_braces(line) > 0:
            lines = [line]
            while _count_open_braces('\n'.join(lines)) > 0:
                cont = input('  ... ')
                lines.append(cont)
            return '\n'.join(lines)
        return line

    def _execute(self, new_code: str):
        """
        Append new_code to history, compile and run the full program,
        but only print output produced by the new statements.
        """
        # Try to compile the new code alone first, for faster error feedback
        test_history = self._history + [new_code]
        full_source = '\n'.join(test_history)

        try:
            reset_registry()
            program = _parse(full_source, '<repl>')
            checker = type_check(program)
            cg = CodeGen(checker)
            cg.compile(program)
            self._last_ir = cg.get_ir()
        except LexError as e:
            click.echo(_red(f'  Syntax error: {e}'), err=False)
            return
        except ParseError as e:
            click.echo(_red(f'  Parse error: {e}'), err=False)
            return
        except VectTypeError as e:
            click.echo(_red(f'  Type error: {e}'), err=False)
            return
        except MultiTypeError as e:
            for err in e.errors:
                click.echo(_red(f'  Type error: {err}'), err=False)
            return
        except CodegenError as e:
            click.echo(_red(f'  Code error: {e}'), err=False)
            return
        except CodegenError as e:
            click.echo(_red(f'  Code error: {e}'), err=False)
            return

        # Run it and capture output
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                cg.execute(self._rt)
        except Exception as e:
            click.echo(_red(f'  Runtime error: {e}'), err=False)
            return

        # Accept the line into history
        self._history.append(new_code)

        output = buf.getvalue()
        if output:
            click.echo(_green(output.rstrip()))


def start_repl():
    """Entry point called by main.py when vect is run with no arguments."""
    repl = Repl()
    repl.run()
