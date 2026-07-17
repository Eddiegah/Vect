"""
record_demo.py — Simulates a Vect REPL session for screen recording.

Run this script, then record the terminal window to create your demo GIF.
It types output with a natural delay so it looks like live interaction.

Usage:
    venv\Scripts\python scripts\record_demo.py
"""

import time
import sys
import io
import contextlib

# Make sure we can import from src/
sys.path.insert(0, '.')

from colorama import Fore, Style, init as colorama_init
colorama_init()

def dim(s):    return Style.DIM + s + Style.RESET_ALL
def cyan(s):   return Fore.CYAN + s + Style.RESET_ALL
def green(s):  return Fore.GREEN + s + Style.RESET_ALL
def yellow(s): return Fore.YELLOW + s + Style.RESET_ALL
def bold(s):   return Style.BRIGHT + s + Style.RESET_ALL
def red(s):    return Fore.RED + s + Style.RESET_ALL
def blue(s):   return Fore.BLUE + Style.BRIGHT + s + Style.RESET_ALL

_L1 = blue('__   __       _')
_L2 = blue(r'\ \ / /__ ___| |_')
_L3 = blue(r' \ V / -_) _|  _|')
_L4 = blue(r'  \_/\___\__|\__|')
_L5 = cyan('Vect 0.1.0') + ' \u2014 a language with native scientific computing'
_L6 = dim("Type 'help' for tips, 'exit' to quit.")
BANNER = f"\n{_L1}\n{_L2}\n{_L3}\n{_L4}\n\n{_L5}\n{_L6}\n"

PROMPT = bold('vect') + cyan('> ')

def pause(n=0.6):
    time.sleep(n)

def type_line(text, delay=0.04):
    """Print text character by character to simulate typing."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def show_prompt():
    sys.stdout.write('\n' + PROMPT)
    sys.stdout.flush()
    pause(0.3)

# Persistent history — accumulated across demo steps
_history = []
_prev_output_lines = 0   # track how many lines previous runs produced

def run_vect(source):
    """Run all history plus new source, return only newly added output lines."""
    from src.pipeline import _parse
    from src.type_checker import type_check
    from src.codegen import CodeGen
    from src.runtime import reset_registry
    global _history, _rt, _prev_output_lines
    _history.append(source.strip())
    full = '\n'.join(_history)
    reset_registry()
    buf = io.StringIO()
    try:
        program = _parse(full, '<demo>')
        checker = type_check(program)
        cg = CodeGen(checker)
        cg.compile(program)
        with contextlib.redirect_stdout(buf):
            cg.execute(_rt)
    except Exception as e:
        _history.pop()
        return f"Error: {e}"
    all_lines = buf.getvalue().splitlines()
    new_lines  = all_lines[_prev_output_lines:]
    _prev_output_lines = len(all_lines)
    return '\n'.join(new_lines).strip()

# Build runtime once
from src.runtime import build_runtime as _br
_rt = _br()

def demo_step(code_lines, speed=0.045):
    """Show prompt, type code, then show output."""
    full_code = '\n'.join(code_lines)

    if len(code_lines) == 1:
        show_prompt()
        type_line(code_lines[0], delay=speed)
    else:
        show_prompt()
        type_line(code_lines[0], delay=speed)
        for line in code_lines[1:]:
            sys.stdout.write('  ... ')
            sys.stdout.flush()
            pause(0.2)
            type_line(line, delay=speed)

    pause(0.4)
    result = run_vect(full_code)
    if result:
        print(green(result))

def main():
    # Clear screen
    print('\033[2J\033[H', end='')

    # Banner
    print(BANNER)
    pause(1.2)

    # ── Step 1: Basic arithmetic ──────────────────────────────
    print(yellow('  # 1. Variables and arithmetic'))
    pause(0.5)
    demo_step(['var x = 40'])
    demo_step(['var y = 2'])
    demo_step(['print(x + y)'])
    pause(0.8)

    # ── Step 2: Vectors ───────────────────────────────────────
    print(yellow('\n  # 2. Native vectors — no imports needed'))
    pause(0.5)
    demo_step(['var v1 = [1.0, 2.0, 3.0]'])
    demo_step(['var v2 = [4.0, 5.0, 6.0]'])
    demo_step(['print(v1 + v2)'])
    demo_step(['print(v1 \u00b7 v2)'])    # · dot product
    pause(0.8)

    # ── Step 3: Matrix multiply ────────────────────────────────
    print(yellow('\n  # 3. Matrices — @ is matrix multiply'))
    pause(0.5)
    demo_step(['var A = [[1.0, 2.0], [3.0, 4.0]]'])
    demo_step(['var B = [[5.0, 6.0], [7.0, 8.0]]'])
    demo_step(['print(A @ B)'])
    demo_step(['print(T(A))'])
    pause(0.8)

    # ── Step 4: Symbolic differentiation ─────────────────────
    print(yellow('\n  # 4. Symbolic calculus — d/dx is real syntax'))
    pause(0.5)
    demo_step(['sym f(x) = x**2 + 3*x + 1'])
    demo_step(['var df = d/dx(f(x))'])
    demo_step(['print(df)'])
    demo_step(['print(eval(df, x=2.0))'])
    pause(0.8)

    # ── Step 5: Physics ───────────────────────────────────────
    print(yellow('\n  # 5. Physics in one line'))
    pause(0.5)
    demo_step(['sym height(t) = 20.0*t - 4.9*t**2'])
    demo_step(['var velocity = d/dt(height(t))'])
    demo_step(['print(velocity)'])
    demo_step(['print(eval(velocity, t=2.0))'])
    pause(0.8)

    # ── Step 6: Recursive function ────────────────────────────
    print(yellow('\n  # 6. Recursion'))
    pause(0.5)
    demo_step([
        'fn fib(n: int) -> int {',
        '    if n <= 1 { return n }',
        '    return fib(n-1) + fib(n-2)',
        '}'
    ])
    demo_step(['print(fib(10))'])
    pause(0.5)

    # Exit
    show_prompt()
    type_line('exit')
    pause(0.3)
    print(dim('Bye!'))
    print()
    pause(0.5)
    print(bold(cyan('  Vect — github.com/Eddiegah/Vect')))
    print()

if __name__ == '__main__':
    main()
