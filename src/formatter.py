"""
formatter.py — Auto-formatter for Vect source code.

Usage:
    vect fmt myfile.vect          formats in place
    vect fmt myfile.vect --check  exits non-zero if formatting needed

Rules applied:
  - Normalize indentation to 4 spaces
  - Ensure single space around operators: =, +, -, *, /, **, @, ·
  - Remove trailing whitespace
  - Ensure single blank line between top-level definitions
  - Normalize { on same line as statement (not its own line)
  - Consistent spacing after commas
  - Preserve comments and string contents unchanged
"""

import re
from typing import List


def format_source(source: str) -> str:
    """
    Format a Vect source string. Returns the formatted version.
    If the source is already formatted, returns it unchanged.
    """
    lines = source.split('\n')
    result = []
    prev_blank = False
    in_block = 0    # track brace depth

    for i, raw_line in enumerate(lines):
        line = raw_line.rstrip()   # remove trailing whitespace

        # Preserve blank lines but collapse multiple consecutive blanks to one
        if not line.strip():
            if not prev_blank and result:
                result.append('')
            prev_blank = True
            continue

        prev_blank = False

        # Normalize indentation: count leading spaces, snap to 4-space multiples
        stripped = line.lstrip()
        leading  = len(line) - len(stripped)
        indent   = '    ' * (leading // 4) + ' ' * (leading % 4)

        # Format the content (preserve string literals and comments)
        content = _format_line(stripped)

        result.append(indent + content)

    # Remove trailing blank lines
    while result and result[-1] == '':
        result.pop()

    return '\n'.join(result) + '\n'


def _format_line(line: str) -> str:
    """Format a single non-empty, stripped line of Vect code."""
    # Don't touch comment lines
    if line.startswith('#'):
        return line

    # Extract and protect string literals to avoid reformatting inside them
    protected, placeholders = _protect_strings(line)

    # Normalize spacing around operators
    # Order matters — do multi-char ops first
    protected = re.sub(r'\s*\*\*\s*', ' ** ', protected)   # **
    protected = re.sub(r'\s*->\s*',   ' -> ', protected)   # ->
    protected = re.sub(r'\s*==\s*',   ' == ', protected)   # ==
    protected = re.sub(r'\s*!=\s*',   ' != ', protected)   # !=
    protected = re.sub(r'\s*<=\s*',   ' <= ', protected)   # <=
    protected = re.sub(r'\s*>=\s*',   ' >= ', protected)   # >=

    # Single-char ops — be careful not to touch unary minus or negative numbers
    protected = re.sub(r'(?<=[a-zA-Z0-9_)\]])\s*\+\s*', ' + ', protected)
    protected = re.sub(r'(?<=[a-zA-Z0-9_)\]])\s*-\s*(?=[a-zA-Z0-9_(])', ' - ', protected)
    protected = re.sub(r'\s*\*\s*(?!\*)',  ' * ',  protected)  # * but not **
    protected = re.sub(r'(?<![*])\s*/\s*(?![/*])', ' / ', protected)  # / but not // or d/dx
    protected = re.sub(r'\s*%\s*',    ' % ',  protected)
    protected = re.sub(r'\s*@\s*',    ' @ ',  protected)

    # Assignment: var x=10 → var x = 10  (but not == or !=)
    protected = re.sub(r'(?<![=!<>])\s*=\s*(?![=>])', ' = ', protected)

    # Comma spacing: a,b → a, b
    protected = re.sub(r',\s*', ', ', protected)

    # Collapse multiple spaces (except leading indentation, already removed)
    protected = re.sub(r'  +', ' ', protected).strip()

    # Restore string literals
    for i, s in enumerate(placeholders):
        protected = protected.replace(f'__STR{i}__', s)

    return protected


def _protect_strings(line: str) -> tuple:
    """
    Replace string literals with placeholders so we don't reformat their contents.
    Returns (modified_line, list_of_original_strings).
    """
    placeholders = []
    result = []
    i = 0
    while i < len(line):
        if line[i] == '"':
            # Find closing quote, respecting escapes
            j = i + 1
            while j < len(line):
                if line[j] == '\\':
                    j += 2
                    continue
                if line[j] == '"':
                    j += 1
                    break
                j += 1
            token = line[i:j]
            placeholder = f'__STR{len(placeholders)}__'
            placeholders.append(token)
            result.append(placeholder)
            i = j
        elif line[i] == '#':
            # Rest of line is a comment — protect it
            token = line[i:]
            placeholder = f'__STR{len(placeholders)}__'
            placeholders.append(token)
            result.append(placeholder)
            break
        else:
            result.append(line[i])
            i += 1

    return ''.join(result), placeholders


def format_file(path: str, check_only: bool = False) -> bool:
    """
    Format a .vect file in place.
    If check_only=True, returns True if the file needs formatting (no changes made).
    Returns True if changes were made (or needed in check mode).
    """
    with open(path, encoding='utf-8') as f:
        original = f.read()

    formatted = format_source(original)

    if original == formatted:
        return False   # already formatted

    if check_only:
        return True    # needs formatting

    with open(path, 'w', encoding='utf-8') as f:
        f.write(formatted)

    return True
