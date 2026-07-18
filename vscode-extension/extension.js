/**
 * extension.js — Vect Language VS Code Extension
 *
 * Provides:
 * - Syntax highlighting (via tmLanguage grammar)
 * - Code snippets
 * - Autocomplete for keywords, built-ins, and stdlib functions
 * - Hover documentation for built-in functions
 * - Basic diagnostics via the type checker (run on save)
 */

const vscode = require('vscode');
const { exec } = require('child_process');
const path = require('path');

// ── Completion items ─────────────────────────────────────────────────────────

const KEYWORDS = [
    'var', 'fn', 'sym', 'if', 'else', 'while', 'for', 'in',
    'return', 'break', 'continue', 'import', 'true', 'false',
    'and', 'or', 'not', 'int', 'float', 'bool', 'string', 'vec', 'mat'
];

const BUILTINS = {
    'print':       '(x: any) → void\nPrint any value to the console.',
    'input':       '() → string\nRead a line from stdin.',
    'len':         '(v: vec) → int\nLength of a vector.',
    'sqrt':        '(x: float) → float\nSquare root.',
    'sin':         '(x: float) → float\nSine (radians).',
    'cos':         '(x: float) → float\nCosine (radians).',
    'tan':         '(x: float) → float\nTangent (radians).',
    'abs':         '(x: float) → float\nAbsolute value.',
    'floor':       '(x: float) → int\nRound down.',
    'ceil':        '(x: float) → int\nRound up.',
    'int':         '(x) → int\nConvert to integer.',
    'float':       '(x) → float\nConvert to float.',
    'str':         '(x) → string\nConvert to string.',
    'range':       '(n: int) → vec\nCreate [0, 1, ..., n-1].',
    'T':           '(m: mat) → mat\nTranspose a matrix.',
    'norm':        '(v: vec) → float\nEuclidean magnitude of a vector.',
    'cross':       '(a: vec, b: vec) → vec\n3D cross product.',
    'normalize':   '(v: vec) → vec\nReturn unit vector (magnitude = 1).',
    'zeros':       '(n: int) → vec\nCreate a zero vector of length n.',
    'ones':        '(n: int) → vec\nCreate a ones vector of length n.',
    'det':         '(A: mat) → float\nDeterminant of a square matrix.',
    'inv':         '(A: mat) → mat\nInverse of a square matrix.',
    'solve':       '(A: mat, b: vec) → vec\nSolve the linear system Ax = b.',
    'eval':        '(expr: sym, var=val) → float\nEvaluate a symbolic expression.',
    'integral':    '(f, "var", lo, hi) → float\nDefinite integral.\nintegral(f, "var") → sym (indefinite).',
    'plot':        '(f, var, lo, hi, title) → void\nPlot a symbolic function. Saves vect_plot.png.',
    'plot_xy':     '(x: vec, y: vec, title) → void\nPlot two data vectors. Saves vect_plot.png.',
    'd/dx':        '(expr) → sym\nSymbolic derivative with respect to x.\nWorks with any variable: d/dt, d/dv, etc.',
};

const STDLIB_FUNCS = {
    // physics.vect
    'kinetic_energy':       '(mass: float, velocity: float) → float\nKE = ½mv²',
    'potential_energy':     '(mass: float, height: float) → float\nPE = mgh',
    'momentum':             '(mass: float, velocity: float) → float\np = mv',
    'free_fall_height':     '(v0: float, t: float) → float\nh = v₀t - ½gt²',
    'free_fall_velocity':   '(v0: float, t: float) → float\nv = v₀ - gt',
    'force':                '(mass: float, accel: float) → float\nF = ma',
    // vectors.vect
    'vec_sum':              '(v: vec) → float\nSum of all elements.',
    'vec_mean':             '(v: vec) → float\nArithmetic mean.',
    'vec_max':              '(v: vec) → float\nMaximum element.',
    'vec_min':              '(v: vec) → float\nMinimum element.',
    'vec_scale':            '(v: vec, s: float) → vec\nScale all elements by s.',
    // mathlib.vect
    'clamp':                '(x, lo, hi: float) → float\nClamp x between lo and hi.',
    'lerp':                 '(a, b, t: float) → float\nLinear interpolation.',
    'sign':                 '(x: float) → float\n1.0 if positive, -1.0 if negative, 0.0 if zero.',
    'max_f':                '(a, b: float) → float\nMaximum of two floats.',
    'min_f':                '(a, b: float) → float\nMinimum of two floats.',
    'pow_int':              '(base: float, exp: int) → float\nInteger power.',
};

// ── Completion provider ──────────────────────────────────────────────────────

function createCompletionProvider() {
    return vscode.languages.registerCompletionItemProvider(
        { language: 'vect' },
        {
            provideCompletionItems(document, position) {
                const items = [];

                // Keywords
                for (const kw of KEYWORDS) {
                    const item = new vscode.CompletionItem(
                        kw, vscode.CompletionItemKind.Keyword
                    );
                    item.detail = 'keyword';
                    items.push(item);
                }

                // Built-in functions
                for (const [name, doc] of Object.entries(BUILTINS)) {
                    const item = new vscode.CompletionItem(
                        name, vscode.CompletionItemKind.Function
                    );
                    item.detail = 'built-in';
                    item.documentation = new vscode.MarkdownString(
                        '**Vect built-in**\n\n`' + name + doc.split('\n')[0] + '`\n\n' +
                        doc.split('\n').slice(1).join('\n')
                    );
                    items.push(item);
                }

                // Stdlib functions
                for (const [name, doc] of Object.entries(STDLIB_FUNCS)) {
                    const item = new vscode.CompletionItem(
                        name, vscode.CompletionItemKind.Function
                    );
                    item.detail = 'stdlib';
                    item.documentation = new vscode.MarkdownString(
                        '**Vect stdlib**\n\n' + doc
                    );
                    items.push(item);
                }

                // Scan document for user-defined identifiers
                const text = document.getText();
                const varPattern = /var\s+(\w+)/g;
                const fnPattern  = /fn\s+(\w+)/g;
                const symPattern = /sym\s+(\w+)/g;
                const seen = new Set();

                for (const pattern of [varPattern, fnPattern, symPattern]) {
                    let m;
                    while ((m = pattern.exec(text)) !== null) {
                        if (!seen.has(m[1])) {
                            seen.add(m[1]);
                            const kind = pattern === fnPattern
                                ? vscode.CompletionItemKind.Function
                                : pattern === symPattern
                                    ? vscode.CompletionItemKind.Function
                                    : vscode.CompletionItemKind.Variable;
                            const item = new vscode.CompletionItem(m[1], kind);
                            item.detail = pattern === varPattern ? 'variable'
                                        : pattern === fnPattern ? 'function' : 'symbolic fn';
                            items.push(item);
                        }
                    }
                }

                return items;
            }
        },
        // Trigger on these characters
        '.', '(', ' ', '/'
    );
}

// ── Hover provider ───────────────────────────────────────────────────────────

function createHoverProvider() {
    return vscode.languages.registerHoverProvider(
        { language: 'vect' },
        {
            provideHover(document, position) {
                const range = document.getWordRangeAtPosition(position);
                if (!range) return;
                const word = document.getText(range);

                // Check d/dx pattern
                const lineText = document.lineAt(position.line).text;
                const ddxMatch = lineText.match(/d\/d(\w+)/);
                if (ddxMatch && lineText.indexOf('d/d') <= position.character) {
                    return new vscode.Hover(
                        new vscode.MarkdownString(
                            '**d/d' + ddxMatch[1] + '** — Symbolic derivative operator\n\n' +
                            'Differentiates a symbolic expression with respect to `' + ddxMatch[1] + '`.\n\n' +
                            '```vect\nsym f(x) = x**2 + 3*x\nvar df = d/dx(f(x))  # → 2*x + 3\n```'
                        )
                    );
                }

                if (BUILTINS[word]) {
                    const [sig, ...descLines] = BUILTINS[word].split('\n');
                    return new vscode.Hover(
                        new vscode.MarkdownString(
                            '**' + word + '**`' + sig + '`\n\n' + descLines.join('\n')
                        )
                    );
                }

                if (STDLIB_FUNCS[word]) {
                    return new vscode.Hover(
                        new vscode.MarkdownString(
                            '**' + word + '** (stdlib)\n\n' + STDLIB_FUNCS[word]
                        )
                    );
                }
            }
        }
    );
}

// ── Diagnostics (type checking on save) ─────────────────────────────────────

const diagnosticCollection = vscode.languages.createDiagnosticCollection('vect');

function runTypeCheck(document) {
    if (document.languageId !== 'vect') return;

    const filePath = document.fileName;
    const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!workspaceRoot) return;

    // Find the vect executable
    const isWin = process.platform === 'win32';
    const vectCmd = isWin
        ? path.join(workspaceRoot, 'venv', 'Scripts', 'vect.exe')
        : path.join(workspaceRoot, 'venv', 'bin', 'vect');

    exec(`"${vectCmd}" check "${filePath}"`, (error, stdout, stderr) => {
        diagnosticCollection.clear();
        if (!error) return;   // no errors

        const output = stderr || stdout;
        const diagnostics = [];

        // Parse "Type error at line N, col M: message"
        const pattern = /line (\d+), col (\d+): (.+)/g;
        let m;
        while ((m = pattern.exec(output)) !== null) {
            const line = parseInt(m[1]) - 1;
            const col  = parseInt(m[2]) - 1;
            const msg  = m[3];
            const range = new vscode.Range(
                new vscode.Position(line, col),
                new vscode.Position(line, col + 10)
            );
            diagnostics.push(
                new vscode.Diagnostic(range, msg, vscode.DiagnosticSeverity.Error)
            );
        }

        if (diagnostics.length > 0) {
            diagnosticCollection.set(document.uri, diagnostics);
        }
    });
}

// ── Activate ─────────────────────────────────────────────────────────────────

function activate(context) {
    console.log('Vect extension activated');

    context.subscriptions.push(createCompletionProvider());
    context.subscriptions.push(createHoverProvider());
    context.subscriptions.push(diagnosticCollection);

    // Run type check on save
    context.subscriptions.push(
        vscode.workspace.onDidSaveTextDocument(runTypeCheck)
    );

    // Run on open
    if (vscode.window.activeTextEditor) {
        runTypeCheck(vscode.window.activeTextEditor.document);
    }

    context.subscriptions.push(
        vscode.window.onDidChangeActiveTextEditor(editor => {
            if (editor) runTypeCheck(editor.document);
        })
    );
}

function deactivate() {
    diagnosticCollection.dispose();
}

module.exports = { activate, deactivate };
