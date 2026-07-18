"""
main.py — Vect compiler/runner CLI entry point.

Usage:
  vect run   <file.vect>        Compile and run a .vect source file
  vect build <file.vect> [-o]   Compile to native .exe (AOT)
  vect check <file.vect>        Type-check without running
  vect ir    <file.vect>        Dump generated LLVM IR
  vect                          Start the interactive REPL
"""

import sys
import click
from .pipeline import run_source, check_source, get_ir


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Vect — a language with native scientific computing."""
    if ctx.invoked_subcommand is None:
        from .repl import start_repl
        start_repl()


@cli.command()
@click.argument('file', type=click.Path(exists=True))
def run(file):
    """Compile and run a .vect source file."""
    try:
        with open(file, encoding='utf-8') as f:
            source = f.read()
        exit_code = run_source(source, filename=file)
        sys.exit(exit_code)
    except Exception as e:
        _print_error(e)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('-o', '--output', default=None,
              help='Output path (default: input filename without .vect)')
def build(file, output):
    """Compile a .vect file to a native executable (AOT)."""
    try:
        from .aot import compile_to_exe
        with open(file, encoding='utf-8') as f:
            source = f.read()
        if output is None:
            output = str(file).replace('.vect', '')
        out = compile_to_exe(source, output, filename=file)
        click.echo(f'  Built: {out}')
        click.echo(f'  Run with: {out}')
    except Exception as e:
        _print_error(e)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
def check(file):
    """Type-check a .vect file without running it."""
    try:
        with open(file, encoding='utf-8') as f:
            source = f.read()
        check_source(source, filename=file)
        click.echo(f'  {file} — no type errors found')
    except Exception as e:
        _print_error(e)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
@click.option('--check', is_flag=True, help='Check formatting without changing the file')
def fmt(file, check):
    """Auto-format a .vect file (normalises spacing and indentation)."""
    try:
        from .formatter import format_file
        changed = format_file(file, check_only=check)
        if check:
            if changed:
                click.echo(f'  {file} — needs formatting (run vect fmt to fix)', err=True)
                raise SystemExit(1)
            else:
                click.echo(f'  {file} — already formatted')
        else:
            if changed:
                click.echo(f'  Formatted: {file}')
            else:
                click.echo(f'  {file} — already formatted')
    except Exception as e:
        _print_error(e)
        raise SystemExit(1)


@cli.command()
def notebook():
    """Install the Vect Jupyter kernel and launch Jupyter."""
    try:
        from .kernel import install_kernel
        install_kernel()
        click.echo('\nLaunching Jupyter...')
        import subprocess
        subprocess.run([sys.executable, '-m', 'jupyter', 'notebook'], check=False)
    except ImportError:
        click.echo('Jupyter not installed. Run: pip install jupyter', err=True)
        sys.exit(1)
    except Exception as e:
        _print_error(e)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
def ir(file):
    """Dump generated LLVM IR (useful for debugging / learning)."""
    try:
        with open(file, encoding='utf-8') as f:
            source = f.read()
        ir_text = get_ir(source, filename=file)
        click.echo(ir_text)
    except Exception as e:
        _print_error(e)
        sys.exit(1)
    """Dump generated LLVM IR (useful for debugging / learning)."""
    try:
        with open(file, encoding='utf-8') as f:
            source = f.read()
        ir_text = get_ir(source, filename=file)
        click.echo(ir_text)
    except Exception as e:
        _print_error(e)
        sys.exit(1)


def _print_error(e: Exception):
    from .type_checker import MultiTypeError
    kind = type(e).__name__

    # Multiple type errors — show all of them
    if isinstance(e, MultiTypeError):
        click.echo(f'\n  Found {len(e.errors)} error(s):\n', err=True)
        for i, err in enumerate(e.errors, 1):
            click.echo(f'  [{i}] {err}\n', err=True)
        return

    if hasattr(e, 'line') and hasattr(e, 'col'):
        msg = str(e)
        if 'Syntax' in kind or 'Lex' in kind or 'Parse' in kind:
            click.echo(f'\n  Warning  Syntax Error\n  {msg}\n', err=True)
        elif 'Type' in kind:
            click.echo(f'\n  Warning  Type Error\n  {msg}\n', err=True)
        else:
            click.echo(f'\n  Error\n  {msg}\n', err=True)
    else:
        click.echo(f'\n  {kind}: {e}\n', err=True)


if __name__ == '__main__':
    cli()
