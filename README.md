<div align="center">

```
██╗   ██╗███████╗ ██████╗████████╗
██║   ██║██╔════╝██╔════╝╚══██╔══╝
██║   ██║█████╗  ██║        ██║
╚██╗ ██╔╝██╔══╝  ██║        ██║
 ╚████╔╝ ███████╗╚██████╗   ██║
  ╚═══╝  ╚══════╝ ╚═════╝   ╚═╝
```

**A compiled programming language where scientific computing is the syntax — not the library.**

<br/>

[![Tests](https://img.shields.io/badge/Tests-138%20Passing-00C853?style=for-the-badge&logo=pytest&logoColor=white)](./tests)
[![CI](https://github.com/Eddiegah/Vect/actions/workflows/test.yml/badge.svg?style=for-the-badge)](https://github.com/Eddiegah/Vect/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.9%20–%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LLVM](https://img.shields.io/badge/LLVM-Native%20Codegen-262D3A?style=for-the-badge&logo=llvm&logoColor=white)](https://llvm.org)
[![License](https://img.shields.io/badge/License-MIT-FF6F00?style=for-the-badge)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.0-7C4DFF?style=for-the-badge)](https://github.com/Eddiegah/Vect/releases)

<br/>

[**⚡ Install**](#-installation) · [**🚀 Quickstart**](#-quickstart) · [**📖 Language Tour**](#-language-tour) · [**🏗 How It Works**](#%EF%B8%8F-how-the-compiler-works) · [**🧪 Tests**](#-tests) · [**📁 Structure**](#-project-structure)

</div>

---

## 💡 The Idea

Every scientific language makes you do this:

```python
# Python — you're always aware of the library seams
import numpy as np
import sympy as sp

v = np.array([1, 2, 3])
x = sp.Symbol('x')
df = sp.diff(x**2 + 3*x, x)
print(float(df.subs(x, 2)))
```

**Vect removes the seams entirely:**

```vect
var v = [1, 2, 3]

sym f(x) = x**2 + 3*x
print(eval(d/dx(f(x)), x=2.0))   # 7.0
```

`d/dx` is not a function call — it is a **language operator**, like `+` or `*`.
`[1, 2, 3]` is a vector **literal**, as native as the number `42`.
`@` is matrix multiply. `·` is dot product. No imports. No library names. Just the language.

> Vect compiles to real **native x86-64 machine code** via LLVM — the same backend used by Clang, Rust, and Swift. Not an interpreter. Not a transpiler. A real compiler.

---

## ✨ Feature Highlights

| Feature | What it looks like |
|---------|-------------------|
| **Native vectors** | `var v = [1.0, 2.0, 3.0]` |
| **Element-wise ops** | `v1 + v2`, `v1 * 2.0`, `v1 - v2` |
| **Dot product** | `v1 · v2` → `32.0` |
| **Matrix multiply** | `A @ B` |
| **Transpose** | `T(A)` |
| **Symbolic function** | `sym f(x) = x**2 + 3*x` |
| **Differentiation** | `d/dx(f(x))` → `2*x + 3` |
| **Evaluate** | `eval(df, x=2.0)` → `7.0` |
| **Recursion** | `fn fib(n: int) -> int { ... }` |
| **Type checker** | Catches errors before running, plain-English messages |
| **REPL** | Interactive session with persistent state |
| **VS Code highlighting** | Included and auto-installed |

---

## 📦 Installation

### Requirements

| | Requirement | Notes |
|--|------------|-------|
| ✅ | Python **3.11** (3.9–3.12) | 3.13+ not yet supported |
| ✅ | Git | For cloning |
| ✅ | VS Code | Optional, for syntax highlighting |

> **Windows users:** No C++ compiler, no Visual Studio, no CMake needed. `llvmlite` ships as a prebuilt wheel.

---

### Option A — One-shot setup (Windows, recommended)

```powershell
git clone https://github.com/Eddiegah/Vect.git
cd Vect
.\setup_vect.ps1
```

That's it. The script creates the virtualenv, installs all dependencies, verifies LLVM, and installs VS Code highlighting automatically.

---

### Option B — Step by step

```bash
# 1. Clone
git clone https://github.com/Eddiegah/Vect.git
cd Vect

# 2. Virtual environment
py -3.11 -m venv venv          # Windows
python3.11 -m venv venv        # macOS / Linux

# 3. Activate
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux

# 4. Install
pip install -r requirements.txt
pip install -e .

# 5. Verify
python -c "import llvmlite.binding as llvm; llvm.initialize(); llvm.initialize_native_target(); llvm.initialize_native_asmprinter(); print('✓ LLVM OK')"
```

---

### VS Code Syntax Highlighting

```powershell
# Windows
Copy-Item -Recurse vscode-extension "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"

# macOS / Linux
cp -r vscode-extension ~/.vscode/extensions/vect-lang-0.1.0
```

Restart VS Code — open any `.vect` file and it's highlighted automatically.

---

## 🚀 Quickstart

### Run a program

```powershell
# Windows
venv\Scripts\vect run examples\demo.vect

# macOS / Linux
venv/bin/vect run examples/demo.vect
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

```
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
Bye!
```

Variables and functions you define persist across lines — the REPL remembers your full session.

---

## 📖 Language Tour

### Variables & Types

```vect
var age    = 21            # int
var height = 1.82          # float
var name   = "Vect"        # string
var ready  = true          # bool

# Optional type annotations
var count: int   = 0
var ratio: float = 1.0 / 3.0
```

**Type conversion**

```vect
var n = int(3.99)          # → 3      (truncates)
var f = float(7)           # → 7.0
var s = str(42)            # → "42"
```

---

### Arithmetic

```vect
print(2 + 3 * 4)           # 14  — standard precedence
print((2 + 3) * 4)         # 20  — parentheses override
print(2.0 ** 10.0)         # 1024.0  — exponentiation
print(17 % 5)              # 2        — modulo
print(-42)                 # -42      — unary negation
```

**Operator precedence (highest → lowest)**

| Level | Operators | Note |
|-------|-----------|------|
| 1 | `**` | Right-associative |
| 2 | `* / % @ ·` | |
| 3 | `+ -` | |
| 4 | `== != < <= > >=` | |
| 5 | `not` | |
| 6 | `and` | Short-circuit |
| 7 | `or` | Short-circuit |

---

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
var i = 1
var total = 0
while i <= 100 {
    total = total + i
    i = i + 1
}
print(total)   # 5050

# for loop — iterates over a vector
for x in [1.0, 4.0, 9.0, 16.0] {
    print(sqrt(x))         # 1, 2, 3, 4
}

# break and continue
var n = 0
while true {
    n = n + 1
    if n % 2 == 0 { continue }
    if n > 9      { break    }
    print(n)               # 1 3 5 7 9
}
```

---

### Functions

```vect
fn add(a: int, b: int) -> int {
    return a + b
}

fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)   # recursion works
}

fn greet(name: string) {          # void — no return type
    print("Hello, " + name + "!")
}

print(factorial(10))   # 3628800
greet("Eddie")         # Hello, Eddie!
```

> Functions can call each other regardless of definition order — the compiler does a first-pass registration of all signatures.

---

### ⭐ Native Vectors

```vect
var a = [1.0, 2.0, 3.0]
var b = [4.0, 5.0, 6.0]

print(a + b)           # [5, 7, 9]      element-wise add
print(a - b)           # [-3, -3, -3]   element-wise subtract
print(a * b)           # [4, 10, 18]    element-wise multiply
print(a * 3.0)         # [3, 6, 9]      scalar scale
print(a · b)           # 32.0           dot product ← native operator
print(a[0])            # 1.0            zero-based index
print(len(a))          # 3              length

a[1] = 99.0            # modify element
print(a)               # [1, 99, 3]

# Iterate
for x in a {
    print(x * x)
}
```

> **Typing `·`:** Copy from here, or press `Alt+0183` on Windows numpad.

---

### ⭐ Native Matrices

```vect
var A = [[1.0, 2.0], [3.0, 4.0]]
var B = [[5.0, 6.0], [7.0, 8.0]]

print(A @ B)           # [[19,22],[43,50]]   matrix multiply
print(T(A))            # [[1,3],[2,4]]        transpose
print(A + B)           # [[6,8],[10,12]]      element-wise
print(A * 2.0)         # [[2,4],[6,8]]        scalar scale

# 90° rotation
var R = [[0.0, -1.0], [1.0, 0.0]]
var p = [[1.0], [0.0]]
print(R @ p)           # [[0],[1]]  — (1,0) rotated to (0,1)

# Row access
var row = A[0]         # returns [1, 2] as a vec
```

---

### ⭐⭐ Symbolic Differentiation

> This is what makes Vect unlike anything else. `d/dx` is a real language operator.

```vect
# Step 1 — define a symbolic function
sym f(x) = x**2 + 3*x + 1

# Step 2 — differentiate
var df = d/dx(f(x))
print(df)                    # 2*x + 3

# Step 3 — evaluate numerically
print(eval(df, x=0.0))       # 3.0
print(eval(df, x=2.0))       # 7.0
```

**Any variable name works after `d/d`:**

```vect
# Free-fall under gravity
sym height(t) = 20.0*t - 4.9*t**2
var velocity = d/dt(height(t))
print(velocity)              # 20.0 - 9.8*t
print(eval(velocity, t=2.0)) # 0.4  (nearly at peak)

# Kinetic energy — derivative IS momentum
sym KE(v) = 0.5 * 2.0 * v**2
var p = d/dv(KE(v))
print(p)                     # 2.0*v
print(eval(p, v=10.0))       # 20.0 kg·m/s

# Circle: derivative of area IS circumference
sym area(r) = 3.14159 * r**2
var circ = d/dr(area(r))
print(eval(circ, r=5.0))     # 31.4159
```

---

### Built-in Functions

| Function | Input | Returns | Example |
|----------|-------|---------|---------|
| `print(x)` | any | void | `print("hi")` |
| `input()` | — | string | `var s = input()` |
| `len(v)` | vec | int | `len([1,2,3])` → `3` |
| `sqrt(x)` | float | float | `sqrt(9.0)` → `3.0` |
| `sin(x)` | float (rad) | float | `sin(0.0)` → `0.0` |
| `cos(x)` | float (rad) | float | `cos(0.0)` → `1.0` |
| `tan(x)` | float (rad) | float | `tan(0.785)` → `≈1.0` |
| `abs(x)` | float | float | `abs(-5.5)` → `5.5` |
| `floor(x)` | float | int | `floor(3.9)` → `3` |
| `ceil(x)` | float | int | `ceil(3.1)` → `4` |
| `int(x)` | numeric | int | `int(3.7)` → `3` |
| `float(x)` | numeric | float | `float(7)` → `7.0` |
| `str(x)` | numeric | string | `str(42)` → `"42"` |
| `range(n)` | int | vec | `range(4)` → `[0,1,2,3]` |
| `T(m)` | mat | mat | transpose |
| `eval(e, v=n)` | sym, binding | float | `eval(df, x=2.0)` |

---

### Error Messages That Help

```vect
print("price: " + 9.99)
```
```
  ⚠  Type Error
  Type error at line 1, col 16: Cannot use '+' between a string and a 'float'.
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

---

## 🎬 Example Programs

| File | What it demonstrates |
|------|----------------------|
| `examples/demo.vect` | Everything — **start here for live demos** |
| `examples/fibonacci.vect` | Recursive functions, while loop |
| `examples/control_flow.vect` | if/else, for, break, grade calculator |
| `examples/linear_system.vect` | Vectors, dot product, matrix operations |
| `examples/symbolic_derivative.vect` | `sym`, `d/dx`, `eval`, physics formulas |
| `examples/showcase.vect` | KE, rotation matrix, factorial, projectile |
| `examples/tour_01_arithmetic.vect` | Hands-on: variables & arithmetic |
| `examples/tour_02_control_flow.vect` | Hands-on: if/while/for/break |
| `examples/tour_03_functions.vect` | Hands-on: functions & recursion |
| `examples/tour_04_vectors.vect` | Hands-on: all vector operations |
| `examples/tour_05_matrices.vect` | Hands-on: matrix ops & rotation |
| `examples/tour_06_symbolic.vect` | Hands-on: full symbolic calculus tour |

---

## 🛠 CLI Reference

| Command | What it does |
|---------|-------------|
| `vect` | Start the interactive REPL |
| `vect run <file.vect>` | Compile and run a program |
| `vect check <file.vect>` | Type-check without running |
| `vect ir <file.vect>` | Dump generated LLVM IR |

**See the actual machine-level IR your code compiles to:**

```powershell
vect ir examples/fibonacci.vect
```

```llvm
define i64 @"vect_user_fib"(i64 %"n") {
entry:
  %"n.1" = alloca i64
  store i64 %"n", i64* %"n.1"
  ...
  %".8" = call i64 @"vect_user_fib"(i64 %".7")   ← recursive call
  %".11" = add i64 %".8", %".10"
  ret i64 %".11"
}
```

The same IR format used by Clang, Rust, and Swift.

---

## 🏗️ How the Compiler Works

Vect is a complete, real compiler. Every stage is hand-written and documented.

```
  source.vect  ──────────────────────────────────────────────────┐
                                                                  │
  ┌─────────────────────────────────────────────────────────┐    │
  │  LEXER   src/lexer.py                                   │ ◄──┘
  │  Text → token stream                                    │
  │  Handles: d/dx  ·  @  **  keywords  strings  numbers   │
  └───────────────────────┬─────────────────────────────────┘
                          │ tokens
  ┌───────────────────────▼─────────────────────────────────┐
  │  PARSER   src/parser.py                                 │
  │  Tokens → Abstract Syntax Tree (25 node types)         │
  │  7-level operator precedence, right-assoc **            │
  └───────────────────────┬─────────────────────────────────┘
                          │ AST
  ┌───────────────────────▼─────────────────────────────────┐
  │  TYPE CHECKER   src/type_checker.py                     │
  │  Infers types, catches mismatches before codegen        │
  │  Plain-English errors with exact line + column          │
  └───────────────────────┬─────────────────────────────────┘
                          │ verified AST
  ┌───────────────────────▼─────────────────────────────────┐
  │  CODE GENERATOR   src/codegen.py                        │
  │  AST → LLVM IR via llvmlite                             │
  │  Variables: alloca / load / store  (SSA pattern)        │
  │  Control flow: explicit basic-block jumps               │
  │  Vec/mat ops: calls to Python runtime via ctypes        │
  │  d/dx: sympy at runtime, result stored as sym object    │
  └───────────────────────┬─────────────────────────────────┘
                          │ LLVM IR
  ┌───────────────────────▼─────────────────────────────────┐
  │  LLVM MCJIT   (llvmlite binding)                        │
  │  IR → native x86-64 machine code, runs immediately      │
  │  Same backend as Clang, Rust, Swift                     │
  └───────────────────────┬─────────────────────────────────┘
                          │ machine code ↔ callbacks
  ┌───────────────────────▼─────────────────────────────────┐
  │  RUNTIME   src/runtime.py                               │
  │  Python ctypes callbacks for vec / mat / sym operations │
  │  Object registry: int IDs map to Python objects         │
  │  sympy handles symbolic math — completely transparent   │
  └─────────────────────────────────────────────────────────┘
```

### Why these choices?

| Decision | Reason |
|----------|--------|
| `llvmlite` over C++ LLVM | Prebuilt wheel — `pip install` just works on Windows, no Visual Studio or CMake |
| Python runtime for vec/mat | Correct, readable, easy to extend — no raw pointer arithmetic in IR |
| sympy for symbolic diff | Full CAS in one pip package; the language hides it completely |
| Recursive descent parser | Easiest to understand and extend; handles all precedence levels cleanly |
| Static type checker | Catches errors early with helpful messages instead of cryptic crashes |

---

## 🧪 Tests

**138 tests across three files — every layer of the compiler covered.**

```powershell
venv\Scripts\pytest tests/ -v        # full output
venv\Scripts\pytest tests/ -q        # summary only
```

| File | What it covers | Count |
|------|---------------|-------|
| `test_lexer.py` | All token types, positions, `d/dx`, `·`, error chars | 39 |
| `test_parser.py` | All 25 AST node types, precedence, all example files | 47 |
| `test_end_to_end.py` | Compile → JIT → run → assert exact stdout | 52 |

The end-to-end tests compile real Vect programs to machine code, execute them, capture stdout, and assert byte-for-byte. If anything in the pipeline breaks anywhere, a test catches it.

```
======================== 138 passed in 1.21s ========================
```

---

## 📁 Project Structure

```
Vect/
│
├── src/                         ← The compiler — read this!
│   ├── lexer.py                   Tokenizer (text → token stream)
│   ├── ast_nodes.py               25 AST node dataclasses
│   ├── parser.py                  Recursive-descent parser
│   ├── type_checker.py            Static type checker
│   ├── codegen.py                 LLVM IR code generator
│   ├── runtime.py                 Python ctypes runtime
│   ├── pipeline.py                Compilation pipeline glue
│   ├── repl.py                    Interactive REPL
│   └── main.py                    CLI entry point
│
├── examples/                    ← Start here
│   ├── demo.vect                  Full demo — best for live use
│   ├── fibonacci.vect             Recursive functions
│   ├── control_flow.vect          if/else, loops, grade logic
│   ├── linear_system.vect         Vectors, dot product, matrices
│   ├── symbolic_derivative.vect   d/dx, eval, physics
│   ├── showcase.vect              Everything together
│   ├── tour_01_arithmetic.vect    Hands-on: variables
│   ├── tour_02_control_flow.vect  Hands-on: if/while/for
│   ├── tour_03_functions.vect     Hands-on: functions
│   ├── tour_04_vectors.vect       Hands-on: vector ops
│   ├── tour_05_matrices.vect      Hands-on: matrix ops
│   └── tour_06_symbolic.vect      Hands-on: d/dx tour
│
├── tests/                       ← 138 passing tests
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── test_end_to_end.py
│
├── docs/
│   └── vect-language-guide.html  Complete language guide (save as PDF)
│
├── vscode-extension/            ← Syntax highlighting
│   ├── package.json
│   ├── language-configuration.json
│   └── syntaxes/vect.tmLanguage.json
│
├── scripts/
│   ├── record_demo.py             Auto-runs a REPL session for recording
│   └── RECORDING.md              Guide for creating demo GIFs
│
├── stdlib/
│   └── math.vect                  clamp, lerp, sign, min_f, max_f
│
├── .github/workflows/test.yml   ← CI runs on every push
├── requirements.txt
├── pyproject.toml
├── setup_vect.ps1               One-shot Windows setup script
├── LICENSE                      MIT
└── README.md                    This file
```

---

## 📚 Dependencies

| Package | Version | Role |
|---------|---------|------|
| `llvmlite` | 0.43.0 | LLVM Python bindings — JIT compiler |
| `sympy` | 1.13.1 | Symbolic math backend for `d/dx` |
| `click` | 8.1.7 | CLI framework |
| `pytest` | 8.2.2 | Test runner |

All installed with a single command: `pip install -r requirements.txt`

---

## 🗺️ Roadmap

| Feature | Status |
|---------|--------|
| Core language (vars, functions, control flow) | ✅ Complete |
| Native vectors with all operators | ✅ Complete |
| Native matrices with `@` and `T()` | ✅ Complete |
| Symbolic differentiation (`d/dx`, `eval`) | ✅ Complete |
| Static type checker with helpful errors | ✅ Complete |
| Interactive REPL with session persistence | ✅ Complete |
| 138-test suite | ✅ Complete |
| GitHub Actions CI | ✅ Complete |
| VS Code syntax highlighting | ✅ Complete |
| Complete language documentation | ✅ Complete |
| Multi-file imports | 🔲 v2 |
| AOT compilation to `.exe` | 🔲 v2 |
| Richer standard library | 🔲 v2 |
| Full type inference (no annotations) | 🔲 v2 |

---

## 📄 Documentation

The full language guide is at [`docs/vect-language-guide.html`](./docs/vect-language-guide.html) — open it in any browser and print to PDF for a complete offline reference.

It covers all 18 topics from installation through the compiler internals, with worked examples for every feature.

---

<div align="center">

## 👤 Author

**Eddie Gah** — [@Eddiegah](https://github.com/Eddiegah)

<br/>

*This project exists to prove three things:*
*compiler construction is approachable,*
*language design is a creative act,*
*and scientific computing can be syntax — not scaffolding.*

<br/>

---

**If Vect made you think differently about what a language can be — that's the whole point.**

```
venv\Scripts\vect run examples\demo.vect
```

⭐ **Star the repo if you found this interesting.**

<br/>

[![GitHub](https://img.shields.io/badge/github.com%2FEddiegah%2FVect-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Eddiegah/Vect)

</div>
