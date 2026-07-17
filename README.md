<div align="center">

<img src="https://img.shields.io/badge/version-0.1.0-blue?style=for-the-badge" />
<img src="https://img.shields.io/badge/python-3.9--3.12-yellow?style=for-the-badge&logo=python" />
<img src="https://img.shields.io/badge/LLVM-native%20codegen-red?style=for-the-badge" />
<img src="https://img.shields.io/badge/tests-138%20passing-brightgreen?style=for-the-badge" />
<img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=for-the-badge" />

# ⚡ Vect

### *A compiled programming language where vectors, matrices, and symbolic differentiation are native syntax — not library imports.*

```vect
sym kinetic(v) = 0.5 * 1.0 * v**2     # define a symbolic function
var dKE = d/dv(kinetic(v))             # differentiate it — d/dv is real syntax
var rate = eval(dKE, v=5.0)            # evaluate at v=5 → 5.0
print(rate)
```

**`d/dx` is an operator. `[1,2,3]` is a first-class vector. `@` is matrix multiply. No imports. No library names. Just the language.**

[What is Vect?](#-what-is-vect) • [Quickstart](#-5-minute-quickstart) • [Language Tour](#-language-tour) • [How It Works](#️-how-the-compiler-works) • [Examples](#-example-programs) • [Install](#-installation)

</div>

---

## 🧠 What is Vect?

Most programming languages treat scientific computing as an afterthought — you import NumPy, SymPy, write `np.dot()`, `sympy.diff()`, and the seams show everywhere. **Vect takes the opposite approach**: vectors, matrices, and symbolic calculus are woven into the language itself, at the syntax level.

Vect is a **real compiled language**, not an interpreter or a transpiler:

- **Lexer → Parser → Type Checker → LLVM IR → Native Machine Code**
- Built from scratch in Python using `llvmlite` (LLVM Python bindings)
- Programs compile to native x86-64 via LLVM's JIT engine
- Static type checker catches errors before a single instruction runs
- Interactive REPL for exploration
- VS Code syntax highlighting included

> This is a passion project demonstrating real compiler construction. It runs real programs. The compiler pipeline is genuine — every stage is hand-written and explained.

---

## ⚡ 5-Minute Quickstart

### Install

```powershell
# Clone and enter the project
git clone https://github.com/Eddiegah/Vect.git
cd Vect

# Python 3.11 recommended on Windows
py -3.11 -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pip install -e .
```

Or run the one-shot setup script:
```powershell
.\setup_vect.ps1
```

### Run the demo

```powershell
venv\Scripts\vect run examples\demo.vect
```

```
--- 1. Functions & Recursion ---
55
--- 2. Native Vectors ---
[4, 1, 4, 2, 5]
4.0
--- 3. Matrix Multiply ---
[
  [0],
  [1]
]
--- 4. Symbolic Differentiation ---
3*x**2 - 4*x + 1
0.0
5.0
--- 5. Physics: Projectile ---
10.0 - 9.8*t
10.0
Done.
```

### Start the REPL

```powershell
venv\Scripts\vect
```

```
__   __       _
\ \ / /__ ___| |_
 \ V / -_) _|  _|
  \_/\___\__|\__|

Vect 0.1.0 — a language with native scientific computing
Type 'help' for tips, 'exit' to quit.

vect> var v = [3.0, 1.0, 4.0]
vect> print(v * 2.0)
[6, 2, 8]
vect> sym f(x) = x**3 - x
vect> print(eval(d/dx(f(x)), x=2.0))
11.0
vect> exit
```

---

## 🗺 Language Tour

### Variables & Types

```vect
var x     = 42          # int
var pi    = 3.14159     # float
var name  = "Vect"      # string
var flag  = true        # bool

# Optional type annotations
var count: int   = 0
var ratio: float = 1.0 / 3.0
```

### Arithmetic & Operators

```vect
var a = 2 + 3 * 4       # 14  — standard precedence
var b = (2 + 3) * 4     # 20  — parentheses work
var c = 2.0 ** 10.0     # 1024.0
var d = 17 % 5          # 2
```

### Control Flow

```vect
# if / else if / else
if score >= 90 {
    print("A")
} else if score >= 80 {
    print("B")
} else {
    print("C")
}

# while loop
var i = 0
while i < 10 {
    i = i + 1
}

# for loop over a vector
for x in [1.0, 4.0, 9.0, 16.0] {
    print(sqrt(x))
}

# break and continue work inside loops
```

### Functions

```vect
fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)   # recursion works
}

print(factorial(10))   # 3628800
```

### ⭐ Native Vectors

Vectors are a built-in type. No `import numpy`. No `.array()`. Just brackets.

```vect
var v1 = [1.0, 2.0, 3.0]
var v2 = [4.0, 5.0, 6.0]

print(v1 + v2)      # [5, 7, 9]      — element-wise addition
print(v1 - v2)      # [-3, -3, -3]   — element-wise subtraction
print(v1 * 3.0)     # [3, 6, 9]      — scalar multiply
print(v1 · v2)      # 32.0           — dot product (middle dot operator)
print(v1[0])        # 1.0            — zero-based indexing
```

### ⭐ Native Matrices

```vect
var A = [[1.0, 2.0], [3.0, 4.0]]
var B = [[5.0, 6.0], [7.0, 8.0]]

print(A @ B)    # matrix multiply  → [[19, 22], [43, 50]]
print(T(A))     # transpose        → [[1, 3], [2, 4]]
print(A + B)    # element-wise     → [[6, 8], [10, 12]]
```

### ⭐⭐ Symbolic Differentiation

This is Vect's headline feature. Define a symbolic function with `sym`, differentiate with `d/dx`, evaluate numerically with `eval`. The user never sees SymPy. It's just the language.

```vect
# Polynomial differentiation
sym f(x) = x**2 + 3*x + 1

var df    = d/dx(f(x))          # → 2*x + 3   (symbolic expression)
print(df)                        # prints: 2*x + 3

var slope = eval(df, x=2.0)     # → 7.0        (numerical evaluation)
print(slope)
```

```vect
# Physics: free-fall under gravity
sym height(t) = 10.0*t - 0.5*9.8*t**2

var velocity    = d/dt(height(t))          # → 10.0 - 9.8*t
var v_at_3sec   = eval(velocity, t=3.0)    # → 0.6  m/s (almost at peak)
print(velocity)
print(v_at_3sec)
```

```vect
# Chain through any variable name
sym energy(m) = m * 9.8 * 100.0    # potential energy at 100m
var dE_dm = d/dm(energy(m))         # → 980.0
print(eval(dE_dm, m=1.0))           # → 980.0
```

### String I/O

```vect
print("Hello, world!")
var name = input()           # read a line from stdin
print("Hi, " + name + "!")  # string concatenation with +
```

### Built-in Math Functions

```vect
print(sqrt(2.0))    # 1.41421
print(sin(3.14))    # ≈ 0.00159
print(cos(0.0))     # 1.0
print(abs(-7.5))    # 7.5
print(floor(3.9))   # 3
print(ceil(3.1))    # 4
```

---

## 🎬 Example Programs

| File | What it demonstrates |
|------|----------------------|
| `examples/demo.vect` | Everything in one file — perfect for live demos |
| `examples/fibonacci.vect` | Recursive functions, while loop, 0–10 Fibonacci |
| `examples/control_flow.vect` | if/else chains, for loops, break, grade calculator |
| `examples/linear_system.vect` | Vectors, dot product, matrix multiply, transpose |
| `examples/symbolic_derivative.vect` | `sym`, `d/dx`, `eval`, physics velocity formula |
| `examples/showcase.vect` | KE derivative, rotation matrix, factorial, projectile |

```powershell
venv\Scripts\vect run examples\demo.vect
venv\Scripts\vect run examples\symbolic_derivative.vect
venv\Scripts\vect run examples\showcase.vect
```

---

## 🛠️ CLI Reference

```
vect                      Start the interactive REPL
vect run  <file.vect>     Compile and run a program
vect check <file.vect>    Type-check without running (catches errors early)
vect ir   <file.vect>     Dump the generated LLVM IR  (see inside the compiler)
```

### Type errors are clear

```vect
print("hello" + 1)
```
```
  ⚠  Type Error
  Type error at line 1, col 7: Cannot use '+' between a string and a 'int'.
  To concatenate, convert to string first with str(...).
```

```vect
print(undeclared)
```
```
  ⚠  Type Error
  Type error at line 1, col 7: 'undeclared' is not defined.
  Check the spelling or make sure you declared it with 'var'.
```

### See the actual LLVM IR your code compiles to

```powershell
venv\Scripts\vect ir examples\fibonacci.vect
```
```llvm
define i64 @"vect_user_fib"(i64 %"n") {
entry:
  %"n.1" = alloca i64
  store i64 %"n", i64* %"n.1"
  ...
  %".8" = call i64 @"vect_user_fib"(i64 %".7")   ; recursive call
  %".10" = call i64 @"vect_user_fib"(i64 %".9")
  %".11" = add i64 %".8", %".10"
  ret i64 %".11"
}
```

---

## 🏗️ How the Compiler Works

```
  source.vect
      │
      ▼
  ┌─────────┐
  │  Lexer  │  lexer.py — turns text into tokens
  │         │  handles: keywords, d/dx, ·, @, string literals
  └────┬────┘
       │ tokens
       ▼
  ┌─────────┐
  │ Parser  │  parser.py — recursive descent, 7 precedence levels
  │         │  builds an AST (25 node types in ast_nodes.py)
  └────┬────┘
       │ AST
       ▼
  ┌──────────────┐
  │ Type Checker │  type_checker.py — static analysis before codegen
  │              │  infers types, catches mismatches, plain-English errors
  └──────┬───────┘
         │ typed AST
         ▼
  ┌──────────────┐
  │ Code Gen     │  codegen.py — emits LLVM IR via llvmlite
  │              │  variables → alloca/load/store (SSA pattern)
  │              │  if/while/for → basic block jumps
  │              │  vec/mat ops → runtime calls via ctypes
  │              │  d/dx → sympy at runtime, returns string
  └──────┬───────┘
         │ LLVM IR
         ▼
  ┌──────────────┐
  │  LLVM MCJIT  │  llvmlite binding — JIT compiles to native x86-64
  │              │  runs immediately in-process
  └──────┬───────┘
         │ machine code
         ▼
  ┌──────────────┐
  │   Runtime    │  runtime.py — Python ctypes callbacks
  │              │  vec/mat objects in a Python registry
  │              │  sympy handles symbolic math transparently
  └──────────────┘
```

### Key design decisions explained

**Why `llvmlite` instead of a C++ LLVM toolchain?**
`llvmlite` ships as a prebuilt wheel — `pip install llvmlite` just works on Windows without Visual Studio, CMake, or any C++ build tools. The tradeoff is we use Python as the host language for the compiler, which is actually great for readability and hackability.

**Why a Python runtime instead of pure LLVM IR for vectors?**
Writing a full vector/matrix memory manager in raw LLVM IR is hundreds of lines of pointer arithmetic. Using a Python runtime via ctypes function pointers lets us get correct, readable code quickly. The JIT calls back into Python at runtime — fast enough, and the logic is transparent.

**Why sympy for symbolic differentiation?**
Because writing a symbolic algebra engine from scratch is a dissertation, not a milestone. Sympy does the math; Vect provides the syntax. The user sees `d/dx`, not `sympy.diff`. The abstraction is clean.

---

## 🧪 Tests

138 tests across three files, covering every layer of the compiler.

```powershell
venv\Scripts\pytest tests/ -v
```

| File | What's tested |
|------|---------------|
| `tests/test_lexer.py` | All token types, positions, error cases |
| `tests/test_parser.py` | All AST node types, precedence, all 5 example files |
| `tests/test_end_to_end.py` | Compile + run programs, check exact stdout output |

End-to-end tests literally compile Vect code to LLVM IR, JIT-execute it, capture stdout, and assert on the bytes. If anything in the pipeline breaks, a test fails.

---

## 📦 Project Structure

```
Vect/
├── src/
│   ├── lexer.py          # tokenizer
│   ├── ast_nodes.py      # 25 AST node dataclasses
│   ├── parser.py         # recursive-descent parser
│   ├── type_checker.py   # static type checker
│   ├── codegen.py        # LLVM IR generator
│   ├── runtime.py        # Python ctypes runtime
│   ├── pipeline.py       # glues all stages together
│   ├── repl.py           # interactive REPL
│   └── main.py           # CLI entry point
├── examples/
│   ├── demo.vect                  # live demo — start here
│   ├── fibonacci.vect             # recursion
│   ├── control_flow.vect          # if/else/for/while
│   ├── linear_system.vect         # vectors + matrices
│   ├── symbolic_derivative.vect   # d/dx + eval
│   └── showcase.vect              # everything together
├── tests/
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── test_end_to_end.py
├── vscode-extension/              # syntax highlighting
│   ├── package.json
│   ├── language-configuration.json
│   └── syntaxes/vect.tmLanguage.json
├── stdlib/
│   └── math.vect                  # clamp, lerp, sign, min_f, max_f
├── requirements.txt
├── pyproject.toml
├── setup_vect.ps1                 # one-shot Windows setup
└── README.md
```

---

## 🎨 VS Code Syntax Highlighting

The extension is in `vscode-extension/`. It was automatically installed when you ran `setup_vect.ps1`. To install manually:

```powershell
# Windows
Copy-Item -Recurse vscode-extension "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"
```

Restart VS Code. Open any `.vect` file. You get:
- **Keywords** coloured (`var`, `fn`, `if`, `while`, `return` ...)
- **Types** in a distinct tone (`int`, `float`, `vec`, `mat` ...)
- **The `d/dx` operator** highlighted as a symbolic keyword
- **`sym`** and **`eval`** in their own colour
- **Strings**, **numbers**, **comments** — all distinct
- **Auto-close** brackets, auto-indent inside `{` blocks

---

## 🚀 Requirements

| Dependency | Version | Why |
|------------|---------|-----|
| Python | 3.9 – 3.12 | Compiler host language |
| `llvmlite` | 0.43.0 | LLVM IR builder + JIT, prebuilt wheel |
| `sympy` | 1.13.1 | Symbolic differentiation backend |
| `click` | 8.1.7 | CLI argument parsing |
| `pytest` | 8.2.2 | Test runner |

> ⚠️ Python 3.13+ is **not** supported yet — `llvmlite==0.43.0` requires 3.9–3.12. Python 3.11 is the recommended version.

---

## 🗺️ What's Next (Future Work)

Things deliberately left out of v1 — natural next steps:

- **Multi-file imports** — single-file programs only in v1
- **AOT compilation** — compile to a standalone `.exe`
- **Better error recovery** — currently stops at first error
- **Richer stdlib** — file I/O, string utilities, more math
- **Type inference** — remove the need for type annotations entirely
- **Generics / parametric types** — typed vectors `vec<int>`
- **Package manager** — aspirational, far out

---

## 👤 Author

**Eddie** — [@Eddiegah](https://github.com/Eddiegah)

Built as a demonstration that compiler construction is approachable, that LLVM IR is learnable, and that language design is genuinely fun. Every source file is heavily commented — read the code.

---

<div align="center">

**If you got this far — open a `.vect` file, run the demo, and try the REPL. It actually works.**

```
venv\Scripts\vect run examples\demo.vect
```

⭐ Star the repo if Vect made you think differently about what a language can be.

</div>
