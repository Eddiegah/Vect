<div align="center">

<br/>

```
██╗   ██╗███████╗ ██████╗████████╗
██║   ██║██╔════╝██╔════╝╚══██╔══╝
██║   ██║█████╗  ██║        ██║
╚██╗ ██╔╝██╔══╝  ██║        ██║
 ╚████╔╝ ███████╗╚██████╗   ██║
  ╚═══╝  ╚══════╝ ╚═════╝   ╚═╝
```

### *A compiled programming language where scientific computing is the syntax — not the library.*

<br/>

[![Python](https://img.shields.io/badge/Python-3.9%E2%80%933.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LLVM](https://img.shields.io/badge/LLVM-Native%20Codegen-262D3A?style=for-the-badge&logo=llvm&logoColor=white)](https://llvm.org)
[![Tests](https://img.shields.io/badge/Tests-138%20Passing-00C853?style=for-the-badge&logo=pytest&logoColor=white)](./tests)
[![CI](https://github.com/Eddiegah/Vect/actions/workflows/test.yml/badge.svg)](https://github.com/Eddiegah/Vect/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/License-MIT-FF6F00?style=for-the-badge)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-0.1.0-7C4DFF?style=for-the-badge)](https://github.com/Eddiegah/Vect)

<br/>

> **"Most languages bolt scientific computing on as an afterthought.**
> **Vect builds it into the grammar itself."**

<br/>

<!-- Demo GIF — record using: python scripts/record_demo.py -->
<!-- After recording, replace the line below with: <img src="docs/demo.gif" alt="Vect REPL demo" width="720"/> -->

[**⚡ Quickstart**](#-quickstart) · [**🗺 Language Tour**](#-language-tour) · [**🏗 How It Works**](#%EF%B8%8F-how-the-compiler-works) · [**📦 Install**](#-installation) · [**🧪 Tests**](#-tests)

<br/>
</div>

---

## ✨ The Big Idea

Every data science language you've used makes you do this:

```python
# Python — you're always aware of the library
import numpy as np
import sympy as sp

v = np.array([1, 2, 3])
x = sp.Symbol('x')
f = x**2 + 3*x
df = sp.diff(f, x)
print(float(df.subs(x, 2)))
```

**Vect does this instead:**

```vect
var v = [1, 2, 3]

sym f(x) = x**2 + 3*x
print(eval(d/dx(f(x)), x=2.0))
```

`d/dx` is not a function call. It's an **operator** — part of the grammar. Vectors aren't wrapped arrays. Matrices aren't objects. They're **literals**, like `42` or `"hello"` — native to the language from the ground up.

And it compiles to **real machine code** via LLVM. Not interpreted. Not transpiled. Actual native x86-64 binary execution.

---

## 🔥 See It In Action

```vect
# Five things that would take paragraphs of setup in other languages.
# In Vect, this is the whole program.

print("=== Vectors ===")
var force    = [0.0, -9.81, 0.0]
var velocity = [10.0, 15.0, 0.0]
print(force + velocity)         # [10, 5.19, 0]
print(force · velocity)         # -147.15  (dot product — native syntax)

print("=== Matrices ===")
var rotate = [[0.0, -1.0], [1.0, 0.0]]
var point  = [[1.0], [0.0]]
print(rotate @ point)           # [[0], [1]]  (rotated 90°)

print("=== Symbolic Calculus ===")
sym position(t) = 10.0*t - 4.9*t**2
var v = d/dt(position(t))       # 10.0 - 9.8*t  (symbolic derivative)
print(v)
print(eval(v, t=1.0))           # 0.2  (velocity at t=1s)

print("=== Recursion ===")
fn fib(n: int) -> int {
    if n <= 1 { return n }
    return fib(n-1) + fib(n-2)
}
print(fib(10))                  # 55
```

**Run it:**
```powershell
vect run examples/showcase.vect
```

---

## 📦 Installation

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | **3.11 recommended** (3.9–3.12) | Python 3.13+ not yet supported |
| Git | Any | For cloning |
| VS Code | Any | Optional, for syntax highlighting |

> ⚠️ **Windows users:** no C++ compiler, no Visual Studio, no CMake required. `llvmlite` ships as a prebuilt wheel.

---

### Option 1 — One-shot setup (Windows, recommended)

```powershell
git clone https://github.com/Eddiegah/Vect.git
cd Vect
.\setup_vect.ps1
```

That script creates the virtualenv, installs all dependencies, verifies the LLVM backend, and installs the VS Code extension automatically.

---

### Option 2 — Manual setup (Windows / macOS / Linux)

**Step 1 — Clone**
```bash
git clone https://github.com/Eddiegah/Vect.git
cd Vect
```

**Step 2 — Create a virtual environment**
```bash
# Windows
py -3.11 -m venv venv
venv\Scripts\activate

# macOS / Linux
python3.11 -m venv venv
source venv/bin/activate
```

**Step 3 — Install dependencies**
```bash
pip install -r requirements.txt
pip install -e .
```

**Step 4 — Verify everything works**
```bash
python -c "import llvmlite.binding as llvm; llvm.initialize(); llvm.initialize_native_target(); llvm.initialize_native_asmprinter(); print('✓ LLVM backend OK')"
```

You should see:
```
✓ LLVM backend OK
```

**Step 5 — Run your first program**
```bash
# Windows
venv\Scripts\vect run examples\demo.vect

# macOS / Linux
venv/bin/vect run examples/demo.vect
```

---

### Install VS Code syntax highlighting

```powershell
# Windows — copies the extension to VS Code's extensions folder
Copy-Item -Recurse vscode-extension "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"
```

```bash
# macOS / Linux
cp -r vscode-extension ~/.vscode/extensions/vect-lang-0.1.0
```

Restart VS Code. Open any `.vect` file — it's highlighted automatically.

---

## ⚡ Quickstart

### The REPL (fastest way to explore)

```bash
venv\Scripts\vect        # Windows
venv/bin/vect            # macOS / Linux
```

```
__   __       _
\ \ / /__ ___| |_
 \ V / -_) _|  _|
  \_/\___\__|\__|

Vect 0.1.0 — a language with native scientific computing
Type 'help' for tips, 'exit' to quit.

vect> var x = 42
vect> print(x * 2)
84
vect> var v = [1.0, 2.0, 3.0]
vect> print(v + [4.0, 5.0, 6.0])
[5, 7, 9]
vect> sym f(x) = x**3 - x
vect> print(eval(d/dx(f(x)), x=2.0))
11.0
vect> exit
Bye!
```

Variables and functions you define persist across lines — the REPL remembers your full session.

---

### Run a file

```bash
vect run examples/demo.vect
vect run examples/fibonacci.vect
vect run examples/symbolic_derivative.vect
```

### Type-check without running

```bash
vect check myprogram.vect
# ✓ myprogram.vect — no type errors found
```

### See the actual LLVM IR your code compiles to

```bash
vect ir examples/fibonacci.vect
```
```llvm
define i64 @"vect_user_fib"(i64 %"n") {
entry:
  %"n.1" = alloca i64
  store i64 %"n", i64* %"n.1"
  %".4" = icmp sle i64 %"n.2", 1
  br i1 %".4", label %"if_then_1", label %"if_merge_2"
if_merge_2:
  %".8" = call i64 @"vect_user_fib"(i64 %".7")
  %".10" = call i64 @"vect_user_fib"(i64 %".9")
  %".11" = add i64 %".8", %".10"
  ret i64 %".11"
}
```

That's real LLVM IR — the same intermediate representation used by Clang, Rust, and Swift.

---

## 🗺 Language Tour

### Variables

```vect
var x     = 42            # int — inferred automatically
var pi    = 3.14159       # float
var name  = "Vect"        # string
var ready = true          # bool

# Optional explicit type annotations
var count: int   = 0
var speed: float = 9.8
```

---

### Arithmetic

```vect
var a = 2 + 3 * 4         # 14  — standard operator precedence
var b = (2 + 3) * 4       # 20  — parentheses override it
var c = 2.0 ** 10.0       # 1024.0  — exponentiation
var d = 17 % 5            # 2   — modulo
var e = -c                # -1024.0 — unary negation
```

---

### Comparisons & Logic

```vect
var hot   = temp > 30.0
var valid = x >= 0 and x <= 100
var open  = not closed

if hot and valid {
    print("conditions met")
}
```

---

### Control Flow

```vect
# if / else if / else — as many branches as you need
if score >= 90 {
    print("A")
} else if score >= 80 {
    print("B")
} else if score >= 70 {
    print("C")
} else {
    print("F")
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
for x in [1.0, 4.0, 9.0, 16.0, 25.0] {
    print(sqrt(x))   # 1, 2, 3, 4, 5
}

# break and continue work as expected
var n = 0
while true {
    n = n + 1
    if n % 2 == 0 { continue }
    if n > 9      { break    }
    print(n)   # 1, 3, 5, 7, 9
}
```

---

### Functions

```vect
# Basic function with typed parameters and return type
fn add(a: int, b: int) -> int {
    return a + b
}

# Void function (no return type annotation = void)
fn greet(name: string) {
    print("Hello, " + name + "!")
}

# Recursion works fully
fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

print(factorial(10))   # 3628800

# Functions can call each other (mutual recursion supported)
fn is_even(n: int) -> bool {
    if n == 0 { return true }
    return is_odd(n - 1)
}
fn is_odd(n: int) -> bool {
    if n == 0 { return false }
    return is_even(n - 1)
}
```

---

### ⭐ Vectors — Native, Not Imported

In Vect, `[1.0, 2.0, 3.0]` is a vector literal — as fundamental as the number `42`.

```vect
var a = [1.0, 2.0, 3.0]
var b = [4.0, 5.0, 6.0]

# Element-wise operations
print(a + b)       # [5, 7, 9]
print(a - b)       # [-3, -3, -3]
print(a * b)       # [4, 10, 18]  (element-wise multiply)

# Scalar operations
print(a * 3.0)     # [3, 6, 9]
print(a * -1.0)    # [-1, -2, -3]

# Dot product — uses the middle-dot operator ·
print(a · b)       # 32.0   (1×4 + 2×5 + 3×6)

# Indexing
print(a[0])        # 1.0
print(a[2])        # 3.0

# Assignment to an index
a[1] = 99.0
print(a)           # [1, 99, 3]

# Iterate over elements
for x in a {
    print(x * x)
}
```

> **Typing the dot product `·` character:**
> Copy-paste from here, or on Windows press `Alt+0183` on the numpad.
> In the REPL you can also type `dot(a, b)` as an alternative.

---

### ⭐ Matrices — Built Right In

```vect
var A = [[1.0, 2.0],
         [3.0, 4.0]]

var B = [[5.0, 6.0],
         [7.0, 8.0]]

# Matrix multiplication — @ operator
print(A @ B)
# [
#   [19, 22],
#   [43, 50]
# ]

# Transpose — T() built-in
print(T(A))
# [
#   [1, 3],
#   [2, 4]
# ]

# Element-wise add/subtract
print(A + B)
# [
#   [6, 8],
#   [10, 12]
# ]

# Scalar multiply
print(A * 2.0)
# [
#   [2, 4],
#   [6, 8]
# ]

# Matrix × vector (column vector)
var v = [[1.0], [0.0]]
print(A @ v)    # [[1], [3]]  — first column of A

# Row access by index
var row0 = A[0]   # returns the first row as a vector
print(row0)       # [1, 2]
```

---

### ⭐⭐ Symbolic Differentiation — The Headline Feature

This is what makes Vect unlike anything else. Symbolic calculus is **syntax**, not a library.

```vect
# Step 1: define a symbolic function with 'sym'
sym f(x) = x**2 + 3*x + 1

# Step 2: differentiate with d/dx  — this is a language operator
var df = d/dx(f(x))
print(df)               # 2*x + 3

# Step 3: evaluate numerically with eval()
print(eval(df, x=0.0))  # 3.0
print(eval(df, x=2.0))  # 7.0
print(eval(df, x=5.0))  # 13.0
```

**Any variable name works after `d/d`:**

```vect
sym area(r)   = 3.14159 * r**2
var dA = d/dr(area(r))          # 6.28318*r
print(eval(dA, r=5.0))          # 31.4159

sym volume(h) = 3.14159 * 4.0 * h
var dV = d/dh(volume(h))        # 12.56637
print(eval(dV, h=1.0))          # 12.56637
```

**Real physics examples:**

```vect
# Free-fall: height = v₀t - ½gt²
sym height(t) = 20.0*t - 0.5*9.8*t**2

var velocity     = d/dt(height(t))      # 20.0 - 9.8*t
var acceleration = d/dt(velocity)       # -9.8  (constant)

print(velocity)
print(eval(velocity, t=0.0))    # 20.0  (launch velocity)
print(eval(velocity, t=2.041))  # ≈ 0   (peak height — velocity = 0)
```

```vect
# Energy: KE = ½mv²
sym KE(v) = 0.5 * 2.0 * v**2    # mass = 2kg

var momentum = d/dv(KE(v))       # mv = 2v  (that's momentum!)
print(eval(momentum, v=10.0))    # 20.0
```

---

### Built-in Math Functions

```vect
print(sqrt(2.0))       # 1.41421
print(sin(3.14159))    # ≈ 0.0
print(cos(0.0))        # 1.0
print(tan(0.7854))     # ≈ 1.0  (π/4)
print(abs(-42.5))      # 42.5
print(floor(3.9))      # 3
print(ceil(3.1))       # 4
```

### String Operations

```vect
var lang  = "Vect"
var msg   = "Welcome to " + lang + "!"
print(msg)                         # Welcome to Vect!
print(str(42) + " is the answer")  # 42 is the answer

var n = input()                    # read a line from stdin
print("You typed: " + n)
```

### Type Conversion

```vect
var x: float = float(7)        # int → float
var n: int   = int(3.99)       # float → int  (truncates, gives 3)
var s: string = str(100)       # int → string
```

### Range (for loops over numbers)

```vect
# range(stop)
for i in range(5) {
    print(i)    # 0.0, 1.0, 2.0, 3.0, 4.0
}

# range(start, stop)
for i in range(1, 6) {
    print(i)    # 1.0, 2.0, 3.0, 4.0, 5.0
}
```

---

## 🗂 Example Programs

### `fibonacci.vect` — Classic recursion
```vect
fn fib(n: int) -> int {
    if n <= 1 { return n }
    return fib(n - 1) + fib(n - 2)
}
var i = 0
while i <= 10 {
    print(fib(i))
    i = i + 1
}
# Output: 0 1 1 2 3 5 8 13 21 34 55
```

### `linear_system.vect` — Full vector/matrix demo
```vect
var v1 = [1.0, 2.0, 3.0]
var v2 = [4.0, 5.0, 6.0]
print(v1 + v2)                          # [5, 7, 9]
print(v1 · v2)                          # 32.0

var A = [[1.0, 2.0], [3.0, 4.0]]
var B = [[5.0, 6.0], [7.0, 8.0]]
print(A @ B)                            # [[19,22],[43,50]]
print(T(A))                             # [[1,3],[2,4]]
```

### `symbolic_derivative.vect` — Calculus as syntax
```vect
sym f(x) = x**2 + 3*x + 1
var df = d/dx(f(x))
print(df)                    # 2*x + 3
print(eval(df, x=2.0))       # 7.0

sym s(t) = 0.5 * 9.8 * t**2
var velocity = d/dt(s(t))
print(velocity)              # 9.8*t
print(eval(velocity, t=3.0)) # 29.4
```

### `demo.vect` — Everything in one file *(best for live demos)*
```powershell
venv\Scripts\vect run examples\demo.vect
```

---

## 🏗️ How the Compiler Works

Vect is a **complete, real compiler** — not an interpreter, not a transpiler. Here's the full pipeline:

```
  Your .vect file
        │
        ▼
  ┌──────────────────────────────────────────────┐
  │  LEXER  (src/lexer.py)                       │
  │                                              │
  │  Reads raw text → stream of tokens           │
  │  Handles: keywords, numbers, strings,        │
  │  operators including d/dx, ·, @, **          │
  └───────────────────┬──────────────────────────┘
                      │ tokens
                      ▼
  ┌──────────────────────────────────────────────┐
  │  PARSER  (src/parser.py)                     │
  │                                              │
  │  Tokens → Abstract Syntax Tree (AST)         │
  │  Recursive descent, 7 precedence levels      │
  │  25 AST node types in ast_nodes.py           │
  └───────────────────┬──────────────────────────┘
                      │ AST
                      ▼
  ┌──────────────────────────────────────────────┐
  │  TYPE CHECKER  (src/type_checker.py)         │
  │                                              │
  │  Walks the AST, infers every expression type │
  │  Catches errors before a single instruction  │
  │  runs. Plain-English messages with line/col  │
  └───────────────────┬──────────────────────────┘
                      │ typed AST
                      ▼
  ┌──────────────────────────────────────────────┐
  │  CODE GENERATOR  (src/codegen.py)            │
  │                                              │
  │  AST → LLVM IR via llvmlite                  │
  │  Variables: alloca / load / store (SSA)      │
  │  Control flow: explicit basic block jumps    │
  │  Vec/mat ops: calls to Python runtime        │
  │  d/dx: sympy at runtime, opaque to user      │
  └───────────────────┬──────────────────────────┘
                      │ LLVM IR
                      ▼
  ┌──────────────────────────────────────────────┐
  │  LLVM MCJIT  (llvmlite binding)              │
  │                                              │
  │  Compiles IR → native x86-64 machine code    │
  │  Runs immediately in-process                 │
  │  Same backend used by Clang, Rust, Swift     │
  └───────────────────┬──────────────────────────┘
                      │ machine code
                      ▼
  ┌──────────────────────────────────────────────┐
  │  RUNTIME  (src/runtime.py)                   │
  │                                              │
  │  Python ctypes callbacks for vec/mat/sym     │
  │  Object registry maps int IDs → Python objs │
  │  sympy handles symbolic math transparently   │
  └──────────────────────────────────────────────┘
```

### Why these design choices?

| Decision | Reason |
|----------|--------|
| `llvmlite` instead of C++ LLVM | Prebuilt wheel — `pip install` just works. No Visual Studio, no CMake, no hours of toolchain setup. |
| Python runtime for vec/mat | Writing a memory manager in raw IR is hundreds of lines of pointer math. Python runtime is correct, readable, and easy to extend. |
| sympy for symbolic diff | Writing a CAS from scratch is a PhD thesis. sympy does the math; Vect provides clean syntax. The user never sees it. |
| Static type checker | Catches errors early with helpful messages instead of cryptic runtime crashes. |
| Recursive descent parser | Easiest to understand, easiest to extend, handles all our precedence rules cleanly. |

---

## ❌ Error Messages That Actually Help

Vect's type checker produces errors you can act on immediately.

**Undefined variable:**
```vect
print(myVector + [1.0, 2.0])
```
```
  ⚠  Type Error
  Type error at line 1, col 7: 'myVector' is not defined.
  Check the spelling or make sure you declared it with 'var'.
```

**Wrong types for an operator:**
```vect
print("price: " + 9.99)
```
```
  ⚠  Type Error
  Type error at line 1, col 16: Cannot use '+' between a string and a 'float'.
  To concatenate, convert to string first with str(...).
```

**Wrong argument count:**
```vect
fn add(a: int, b: int) -> int { return a + b }
print(add(1, 2, 3))
```
```
  ⚠  Type Error
  Type error at line 2, col 7: Function 'add' expects 2 argument(s) but got 3.
```

**Type mismatch in declaration:**
```vect
var x: int = 3.14
```
```
  ⚠  Type Error
  Type error at line 1, col 5: Variable 'x' is declared as 'int' but the value
  is a float. Use 'int(...)' to convert explicitly, or declare it as 'float'.
```

---

## 🧪 Tests

138 tests. Every layer of the compiler is tested independently.

```bash
# Run everything
venv\Scripts\pytest tests/ -v       # Windows
venv/bin/pytest tests/ -v           # macOS / Linux

# Run a specific suite
venv\Scripts\pytest tests/test_lexer.py -v
venv\Scripts\pytest tests/test_parser.py -v
venv\Scripts\pytest tests/test_end_to_end.py -v
```

| Test file | What it covers | Tests |
|-----------|---------------|-------|
| `test_lexer.py` | All token types, positions, error chars, `d/dx`, `·`, `@` | 39 |
| `test_parser.py` | All 25 AST node types, operator precedence, all 5 example files | 47 |
| `test_end_to_end.py` | Full compile → JIT → run → assert stdout is correct | 52 |

The end-to-end tests literally compile Vect programs to machine code, execute them, capture the output, and assert byte-for-byte. If anything breaks anywhere in the pipeline, a test catches it.

```
======================== 138 passed in 2.04s ========================
```

---

## 📁 Project Structure

```
Vect/
│
├── src/                        ← The compiler (read this!)
│   ├── lexer.py                  Tokenizer: text → token stream
│   ├── ast_nodes.py              25 AST node dataclasses
│   ├── parser.py                 Recursive-descent parser
│   ├── type_checker.py           Static type checker
│   ├── codegen.py                LLVM IR code generator
│   ├── runtime.py                Python ctypes runtime for vec/mat/sym
│   ├── pipeline.py               Glues all stages together
│   ├── repl.py                   Interactive REPL
│   └── main.py                   CLI entry point (vect command)
│
├── examples/                   ← Start here to learn the language
│   ├── demo.vect                 Live demo — best starting point
│   ├── fibonacci.vect            Recursive functions
│   ├── control_flow.vect         if/else, loops, grade calculator
│   ├── linear_system.vect        Vectors, dot product, matrices
│   ├── symbolic_derivative.vect  d/dx, eval, physics formulas
│   └── showcase.vect             Everything at once
│
├── tests/                      ← 138 passing tests
│   ├── test_lexer.py
│   ├── test_parser.py
│   └── test_end_to_end.py
│
├── vscode-extension/           ← Syntax highlighting
│   ├── package.json
│   ├── language-configuration.json
│   └── syntaxes/vect.tmLanguage.json
│
├── stdlib/
│   └── math.vect               clamp, lerp, sign, min_f, max_f
│
├── requirements.txt            llvmlite, sympy, click, pytest
├── pyproject.toml              pip-installable package config
├── setup_vect.ps1              One-shot Windows setup script
└── README.md                   You are here
```

---

## 🖥️ VS Code Syntax Highlighting

Open a `.vect` file in VS Code after installing the extension and you get:

| Element | Colour |
|---------|--------|
| Keywords (`var`, `fn`, `if`, `while`, `for`, `return`) | Blue / purple |
| Types (`int`, `float`, `vec`, `mat`, `string`, `bool`) | Teal |
| `sym`, `d/dx`, `eval` — symbolic operators | Orange / distinct |
| String literals | Green |
| Numbers | Light orange |
| Comments (`# ...`) | Grey italic |
| Built-ins (`print`, `sqrt`, `sin`, `T`, `len`) | Yellow |
| Operators (`@`, `·`, `**`, `->`) | White / bright |

Auto-closing brackets, auto-indent inside `{` blocks, and correct indentation rules all included.

---

## 🚀 CLI Reference

```
USAGE:
  vect                       Start the interactive REPL
  vect run  <file.vect>      Compile and run a program
  vect check <file.vect>     Type-check only (no execution)
  vect ir   <file.vect>      Dump generated LLVM IR

EXAMPLES:
  vect run examples/demo.vect
  vect run examples/showcase.vect
  vect check myprogram.vect
  vect ir examples/fibonacci.vect

REPL COMMANDS (inside the REPL):
  help     Show available commands and syntax cheatsheet
  clear    Reset the session (forget all variables/functions)
  ir       Show LLVM IR for the last compiled statement
  exit     Quit
```

---

## 📚 Dependencies

```
llvmlite==0.43.0    LLVM Python bindings — JIT compiler backend
sympy==1.13.1       Symbolic math (powers d/dx under the hood)
click==8.1.7        CLI framework
pytest==8.2.2       Test runner
```

All installed automatically via `pip install -r requirements.txt`.

---

## 🗺️ Roadmap / Future Work

| Feature | Status | Notes |
|---------|--------|-------|
| Core language (vars, functions, control flow) | ✅ Done | |
| Native vectors and matrices | ✅ Done | |
| Symbolic differentiation (`d/dx`) | ✅ Done | |
| Interactive REPL | ✅ Done | |
| VS Code syntax highlighting | ✅ Done | |
| Static type checker | ✅ Done | |
| 138-test suite | ✅ Done | |
| Multi-file imports | 🔲 Future | Single-file programs only in v1 |
| AOT compilation to `.exe` | 🔲 Future | JIT only for now |
| Richer stdlib | 🔲 Future | File I/O, more string ops |
| Type inference (no annotations needed) | 🔲 Future | |
| Typed vectors `vec<int>` | 🔲 Future | |
| Package manager | 🔲 Aspirational | |

---

## 👤 Author

<div align="center">

Built by **Eddie** — [@Eddiegah](https://github.com/Eddiegah)

This project exists to prove three things:
1. Compiler construction is approachable — you don't need a PhD
2. Language design is a creative act, not just engineering
3. Scientific computing can be syntax, not scaffolding

Every source file is thoroughly commented. Read the code — it's meant to be understood.

<br/>

---

*If Vect made you think differently about what a programming language can be — that's the whole point.*

**⭐ Star the repo. Run the demo. Try the REPL.**

```
vect run examples/demo.vect
```

</div>
