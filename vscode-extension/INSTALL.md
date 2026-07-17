# Installing Vect Syntax Highlighting in VS Code

No marketplace publishing needed — install directly from this folder in under a minute.

## Option A: Copy to extensions folder (simplest)

1. Find your VS Code extensions folder:
   - **Windows**: `%USERPROFILE%\.vscode\extensions\`
   - **macOS/Linux**: `~/.vscode/extensions/`

2. Copy this entire `vscode-extension/` folder there, renamed to `vect-lang-0.1.0`:
   ```
   # Windows (PowerShell)
   Copy-Item -Recurse vscode-extension "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"
   ```

3. Restart VS Code. Open any `.vect` file — it will be highlighted automatically.

## Option B: Package as .vsix (if you have Node.js/vsce)

```bash
npm install -g @vscode/vsce
cd vscode-extension
vsce package
# Produces vect-lang-0.1.0.vsix
code --install-extension vect-lang-0.1.0.vsix
```

## What you get

- Keywords highlighted (`var`, `fn`, `if`, `while`, `for`, `return`, ...)
- Types in a distinct colour (`int`, `float`, `vec`, `mat`, ...)
- The signature operators stand out: `d/dx`, `sym`, `@`, `·`
- String literals, numbers, and comments all coloured
- Auto-close brackets `{}`, `[]`, `()`
- Auto-indent inside `{` blocks
