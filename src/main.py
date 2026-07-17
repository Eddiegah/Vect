"""
main.py — Vect compiler/runner CLI entry point.

Usage:
  vect run <file.vect>       Compile and run a .vect source file
  vect check <file.vect>     Type-check without running
  vect ir <file.vect>        Dump the generated LLVM IR (debug)
  vect                       Start the interactive REPL
"""

import sys
import os

import click

from .pipeline import run_source, check_source, get_ir


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """Vect — a language with native scientific computing."""
    if ctx.invoked_subcommand is None:
        # No subcommand: start the REPL
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
def check(file):
    """Type-check a .vect file without running it."""
    try:
        with open(file, encoding='utf-8') as f:
            source = f.read()
        check_source(source, filename=file)
        click.echo(f"✓ {file} — no type errors found")
    except Exception as e:
        _print_error(e)
        sys.exit(1)


@cli.command()
@click.argument('file', type=click.Path(exists=True))
def ir(file):
    """Dump generated LLVM IR for a .vect file (useful for debugging)."""
    try:
        with open(file, encoding='utf-8') as f:
            source = f.read()
        ir_text = get_ir(source, filename=file)
        click.echo(ir_text)
    except Exception as e:
        _print_error(e)
        sys.exit(1)


def _print_error(e: Exception):
    """Print a compiler error in a friendly format."""
    kind = type(e).__name__
    # Our custom errors already have nice messages; just print them cleanly
    if hasattr(e, 'line') and hasattr(e, 'col'):
        msg = str(e)
        # Highlight the error type
        if 'Syntax' in kind or 'Lex' in kind or 'Parse' in kind:
            click.echo(f'\n  ⚠  Syntax Error\n  {msg}\n', err=True)
        elif 'Type' in kind:
            click.echo(f'\n  ⚠  Type Error\n  {msg}\n', err=True)
        else:
            click.echo(f'\n  ✗  Error\n  {msg}\n', err=True)
    else:
        click.echo(f'\n  ✗  {kind}: {e}\n', err=True)


if __name__ == '__main__':
    cli()
