"""
kernel.py — Vect Jupyter kernel.

Lets you run Vect code directly in Jupyter notebooks.

Install:
    python -m src.kernel install

Then launch Jupyter and select "Vect" from the kernel menu.

Architecture:
    - Subclasses ipykernel.kernelbase.Kernel
    - do_execute() runs Vect source through our pipeline
    - Captures stdout and sends it back as notebook output
    - Maintains a persistent session (like the REPL) so variables
      and functions defined in one cell work in the next
    - Errors are displayed with colour and line numbers
"""

import sys
import io
import os
import contextlib
import traceback
from ipykernel.kernelbase import Kernel

# Add project root to path so we can import src.*
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class VectKernel(Kernel):
    implementation         = 'Vect'
    implementation_version = '2.0'
    language               = 'vect'
    language_version       = '2.0'
    language_info = {
        'name':            'vect',
        'mimetype':        'text/x-vect',
        'file_extension':  '.vect',
        'pygments_lexer':  'text',
        'codemirror_mode': 'text',
    }
    banner = (
        "Vect 2.0 — A compiled language with native scientific computing\n"
        "d/dx is an operator. [1,2,3] is a native vector. @ is matrix multiply.\n"
        "github.com/Eddiegah/Vect"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._history: list = []     # accumulated source lines (like REPL)
        self._rt = None              # runtime symbols — built once

    def _get_rt(self):
        if self._rt is None:
            from src.runtime import build_runtime
            self._rt = build_runtime()
        return self._rt

    def do_execute(self, code: str, silent: bool,
                   store_history: bool = True,
                   user_expressions=None, allow_stdin: bool = False):
        """Execute a cell of Vect code."""

        if not code.strip():
            return self._ok()

        # Handle special commands
        cmd = code.strip().lower()
        if cmd in ('clear', '%clear'):
            self._history.clear()
            from src.runtime import reset_registry
            reset_registry()
            if not silent:
                self._send_output('Session cleared.\n', stream='stderr')
            return self._ok()

        if cmd in ('help', '%help'):
            help_text = self._help_text()
            if not silent:
                self._send_output(help_text)
            return self._ok()

        # Accumulate history and try to compile
        from src.pipeline import _parse_and_resolve
        from src.type_checker import type_check, MultiTypeError
        from src.codegen import CodeGen, CodegenError
        from src.lexer import LexError
        from src.parser import ParseError
        from src.runtime import reset_registry

        test_history = self._history + [code.strip()]
        full_source = '\n'.join(test_history)

        # Compile
        try:
            reset_registry()
            program = _parse_and_resolve(full_source, '<notebook>')
            checker = type_check(program)
            cg = CodeGen(checker)
            cg.compile(program)
        except LexError as e:
            return self._error(f'Syntax Error: {e}')
        except ParseError as e:
            return self._error(f'Parse Error: {e}')
        except MultiTypeError as e:
            msgs = '\n'.join(f'  [{i+1}] {err}' for i, err in enumerate(e.errors))
            return self._error(f'Type Errors ({len(e.errors)} found):\n{msgs}')
        except Exception as e:
            return self._error(f'Compile Error: {e}')

        # Run
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                cg.execute(self._get_rt())
        except Exception as e:
            return self._error(f'Runtime Error: {e}')

        # Accept into history
        self._history.append(code.strip())

        output = buf.getvalue()
        if output and not silent:
            self._send_output(output)

        return self._ok()

    def _send_output(self, text: str, stream: str = 'stdout'):
        self.send_response(self.iopub_socket, 'stream', {
            'name': stream,
            'text': text,
        })

    def _error(self, message: str):
        self.send_response(self.iopub_socket, 'stream', {
            'name': 'stderr',
            'text': f'\x1b[31m{message}\x1b[0m\n',
        })
        return {
            'status': 'error',
            'execution_count': self.execution_count,
            'ename': 'VectError',
            'evalue': message,
            'traceback': [message],
        }

    def _ok(self):
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }

    def _help_text(self) -> str:
        return """Vect Kernel — Quick Reference
═══════════════════════════════════════════════════

VARIABLES          var x = 42
F-STRINGS          f"Hello {name}, score: {x*2}"
VECTORS            var v = [1.0, 2.0, 3.0]
VECTOR OPS         v1 + v2  |  v1 · v2  |  norm(v)  |  cross(a,b)
MATRICES           var A = [[1.0,2.0],[3.0,4.0]]
MATRIX OPS         A @ B  |  T(A)  |  det(A)  |  inv(A)  |  solve(A,b)
FUNCTIONS          fn add(a, b) { return a + b }  # annotations optional
IMPORTS            import "stdlib/physics.vect"
SYMBOLIC DIFF      sym f(x) = x**2 + 3*x
                   var df = d/dx(f(x))
                   print(eval(df, x=2.0))
INTEGRATION        integral(f(x), "x", 0.0, 3.0)
PLOT               plot(f(x), x, -3.14, 3.14, "title")

COMMANDS           clear   — reset session
                   help    — show this message
"""

    def do_complete(self, code: str, cursor_pos: int):
        """Basic tab-completion for Vect keywords."""
        keywords = [
            'var', 'fn', 'sym', 'if', 'else', 'while', 'for', 'in',
            'return', 'break', 'continue', 'import', 'print', 'input',
            'true', 'false', 'and', 'or', 'not',
            'norm(', 'cross(', 'normalize(', 'det(', 'inv(', 'solve(',
            'zeros(', 'ones(', 'sqrt(', 'sin(', 'cos(', 'tan(', 'abs(',
            'floor(', 'ceil(', 'range(', 'T(', 'len(', 'str(', 'int(', 'float(',
            'eval(', 'integral(', 'plot(', 'plot_xy(', 'd/dx(', 'd/dt(',
        ]
        # Find the token being completed
        token_start = cursor_pos
        while token_start > 0 and (code[token_start-1].isalnum() or
                                    code[token_start-1] in ('_', '/')):
            token_start -= 1
        token = code[token_start:cursor_pos]
        matches = [k for k in keywords if k.startswith(token)]
        return {
            'status': 'ok',
            'matches': matches,
            'cursor_start': token_start,
            'cursor_end': cursor_pos,
            'metadata': {},
        }


def install_kernel():
    """Install the Vect kernel into Jupyter."""
    import json, shutil, tempfile

    kernel_json = {
        'argv': [sys.executable, '-m', 'src.kernel', '-f', '{connection_file}'],
        'display_name': 'Vect',
        'language': 'vect',
        'name': 'vect',
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        kernel_dir = os.path.join(tmpdir, 'vect')
        os.makedirs(kernel_dir)

        with open(os.path.join(kernel_dir, 'kernel.json'), 'w') as f:
            json.dump(kernel_json, f, indent=2)

        try:
            from jupyter_client.kernelspec import KernelSpecManager
            ksm = KernelSpecManager()
            ksm.install_kernel_spec(kernel_dir, kernel_name='vect',
                                    user=True, replace=True)
            print('Vect kernel installed successfully.')
            print('Launch Jupyter and select "Vect" from the kernel menu.')
        except Exception as e:
            print(f'Error installing kernel: {e}')
            print('Manual install: copy the kernel.json to your Jupyter kernels directory.')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'install':
        install_kernel()
    else:
        from ipykernel.kernelapp import IPKernelApp
        IPKernelApp.launch_instance(kernel_class=VectKernel)
