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

[![Tests](https://img.shields.io/badge/Tests-154%20Passing-00C853?style=for-the-badge&logo=pytest&logoColor=white)](./tests)
[![CI](https://github.com/Eddiegah/Vect/actions/workflows/test.yml/badge.svg?style=for-the-badge)](https://github.com/Eddiegah/Vect/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.9%20–%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LLVM](https://img.shields.io/badge/LLVM-Native%20Codegen-262D3A?style=for-the-badge&logo=llvm&logoColor=white)](https://llvm.org)
[![License](https://img.shields.io/badge/License-MIT-FF6F00?style=for-the-badge)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-7C4DFF?style=for-the-badge)](https://github.com/Eddiegah/Vect/releases)

<br/>

[**⚡ Install**](#-installation) · [**🚀 Quickstart**](#-quickstart) · [**📖 Language Tour**](#-language-tour) · [**🏗 How It Works**](#%EF%B8%8F-how-the-compiler-works) · [**🧪 Tests**](#-tests) · [**📁 Structure**](#-project-structure)

</div>

---

## 💡 The Idea

Every scientific language makes you do this:

```python
# Python — library seams everywhere
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
`@` is matrix multiply. `·` is dot product. `integral()` integrates.
No imports. No library names. Just the language.

> Vect compiles to **real native x86-64 machine code** via LLVM — the same backend used by Clang, Rust, and Swift. Not an interpreter. Not a transpiler. A genuine compiler with `vect build` producing standalone executables.

---

## ✨ What Vect Can Do

| Feature | Syntax | Example |
|---------|--------|---------|
| Native vectors | `[1.0, 2.0, 3.0]` | `var v = [1.0, 2.0, 3.0]` |
| Element-wise ops | `v1 + v2`, `v * 2.0` | `print(v1 + v2)` → `[5, 7, 9]` |
| Dot product | `v1 · v2` | `print(v1 · v2)` → `32.0` |
| Cross product | `cross(a, b)` | `print(cross(a, b))` → `[0, 0, 1]` |
| Vector norm | `norm(v)` | `print(norm([3.0,4.0,0.0]))` → `5.0` |
| Matrix multiply | `A @ B` | `print(A @ B)` → `[[19,22],[43,50]]` |
| Transpose | `T(A)` | `print(T(A))` |
| Determinant | `det(A)` | `print(det(A))` → `-2.0` |
| Inverse | `inv(A)` | `var Ainv = inv(A)` |
| Solve Ax=b | `solve(A, b)` | `var x = solve(A, b)` |
| Differentiation | `d/dx(f(x))` | `var df = d/dx(f(x))` → `2*x + 3` |
| Symbolic eval | `eval(df, x=2.0)` | `print(eval(df, x=2.0))` → `7.0` |
| Integration | `integral(f(x), "x", 0, 3)` | `print(integral(f(x), "x", 0.0, 3.0))` → `9.0` |
| Plot | `plot(f(x), x, lo, hi)` | Saves `vect_plot.png` |
| f-strings | `f"Hello {name}!"` | `print(f"Score: {score}")` |
| AOT compile | `vect build file.vect` | Produces `.exe` |
| REPL | `vect` | Interactive session |

---

## 📦 Installation

### Requirements

| | Requirement | Notes |
|--|------------|-------|
| ✅ | Python **3.11** (3.9–3.12 supported) | 3.13+ not yet supported |
| ✅ | Git | For cloning |
| ✅ | VS Code | Optional, for syntax highlighting |
| ✅ | gcc (MSYS2) | Only needed for `vect build` (AOT) |

> **Windows users:** No Visual Studio or CMake needed for JIT mode. `llvmlite` ships as a prebuilt wheel.

---

### Option A — One-shot setup (Windows)

```powershell
git clone https://github.com/Eddiegah/Vect.git
cd Vect
.\setup_vect.ps1
```

Creates the virtualenv, installs all dependencies, verifies LLVM, and installs VS Code highlighting automatically.

---

### Option B — Manual (Windows / macOS / Linux)

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
python -c "import llvmlite.binding as llvm; llvm.initialize(); llvm.initialize_native_target(); llvm.initialize_native_asmprinter(); print('LLVM OK')"
```

---

### VS Code Syntax Highlighting

```powershell
# Windows
Copy-Item -Recurse vscode-extension "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"

# macOS / Linux
cp -r vscode-extension ~/.vscode/extensions/vect-lang-0.1.0
```

Restart VS Code — open any `.vect` file and it highlights automatically.

---

## 🚀 Quickstart

### The REPL

```powershell
venv\Scripts\vect        # Windows
venv/bin/vect            # macOS / Linux
```

```
vect> var v = [1.0, 2.0, 3.0]
vect> print(v · [4.0, 5.0, 6.0])
32.0
vect> sym f(x) = x**3 - x
vect> print(eval(d/dx(f(x)), x=2.0))
11.0
vect> exit
```

### Run a file

```powershell
venv\Scripts\vect run examples\demo.vect
venv\Scripts\vect run examples\calculus_v2.vect
venv\Scripts\vect run examples\plot_demo.vect     # generates vect_plot.png
```

### Build a native executable

```powershell
venv\Scripts\vect build examples\fibonacci.vect -o fib
.\fib.exe
# Output: 0 1 1 2 3 5 8 13 21 34 55
```

### Check and inspect

```powershell
venv\Scripts\vect check myprogram.vect   # type-check only
venv\Scripts\vect ir    myprogram.vect   # dump LLVM IR
```

---

## 📖 Language Tour

### Variables

```vect
var age    = 21
var pi     = 3.14159
var name   = "Vect"
var active = true

# Optional type annotations
var count: int   = 0
var ratio: float = 1.0 / 3.0
```

### F-strings *(v2)*

```vect
var name  = "Eddie"
var score = 95
print(f"Hello, {name}!")               # Hello, Eddie!
print(f"Score: {score}, Grade: A")     # Score: 95, Grade: A
print(f"Double: {score * 2}")          # Double: 190
```

### Arithmetic & Operators

```vect
print(2 + 3 * 4)        # 14  — standard precedence
print((2 + 3) * 4)      # 20
print(2.0 ** 10.0)      # 1024.0
print(17 % 5)           # 2
```

### Control Flow

```vect
if score >= 90 { print("A") }
else if score >= 80 { print("B") }
else { print("C") }

var i = 1
var total = 0
while i <= 100 { total = total + i\ni = i + 1 }
print(total)    # 5050

for x in [1.0, 4.0, 9.0] { print(sqrt(x)) }  # 1, 2, 3
```

### Functions & Recursion

```vect
fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}
print(factorial(10))   # 3628800
```

---

### ⭐ Native Vectors

```vect
var a = [1.0, 2.0, 3.0]
var b = [4.0, 5.0, 6.0]

print(a + b)             # [5, 7, 9]
print(a * 3.0)           # [3, 6, 9]
print(a · b)             # 32.0  (dot product)
print(norm(a))           # 3.74166  (magnitude)
print(normalize(a))      # [0.267, 0.535, 0.802]

var c = cross(a, b)      # 3D cross product
print(c)                 # [0, 0, 0]  (parallel vectors → zero)

print(zeros(4))          # [0, 0, 0, 0]
print(ones(3))           # [1, 1, 1]
print(a[0])              # 1.0
print(len(a))            # 3
```

---

### ⭐ Native Matrices

```vect
var A = [[1.0, 2.0], [3.0, 4.0]]
var B = [[5.0, 6.0], [7.0, 8.0]]

print(A @ B)             # [[19,22],[43,50]]  matrix multiply
print(T(A))              # [[1,3],[2,4]]       transpose
print(det(A))            # -2.0               determinant
print(inv(A))            # [[-2,1],[1.5,-0.5]] inverse

# Solve Ax = b
var b2 = [1.0, 0.0]
var x = solve(A, b2)
print(x)                 # [-2, 1.5]

# 90° rotation
var R = [[0.0, -1.0], [1.0, 0.0]]
var p = [[1.0], [0.0]]
print(R @ p)             # [[0],[1]]
```

---

### ⭐⭐ Symbolic Differentiation

```vect
sym f(x) = x**2 + 3*x + 1

var df = d/dx(f(x))
print(df)                    # 2*x + 3
print(eval(df, x=2.0))       # 7.0
print(eval(df, x=0.0))       # 3.0

# Physics — free fall
sym height(t) = 20.0*t - 4.9*t**2
var velocity = d/dt(height(t))
print(velocity)              # 20.0 - 9.8*t
print(eval(velocity, t=2.0)) # 0.4

# Kinetic energy — derivative IS momentum
sym KE(v) = 0.5 * 2.0 * v**2
var p = d/dv(KE(v))
print(p)                     # 2.0*v
print(eval(p, v=10.0))       # 20.0
```

---

### ⭐⭐ Symbolic Integration *(v2)*

```vect
# Definite integral — area under curve
sym f(x) = x**2
var area = integral(f(x), "x", 0.0, 3.0)
print(area)              # 9.0

# Work done by variable force F(x) = 2x + 1
sym force(x) = 2.0*x + 1.0
var work = integral(force(x), "x", 0.0, 5.0)
print(work)              # 30.0

# Indefinite integral — returns symbolic antiderivative
var F = integral(f(x), "x")
print(eval(F, x=3.0))    # 9.0
```

---

### ⭐ Plot *(v2)*

```vect
# Plot any symbolic function — saves vect_plot.png
sym wave(x) = sin(x) * 2.0
plot(wave(x), x, -6.28, 6.28, "Sine Wave")

# Plot two data vectors
var xs = [0.0, 1.0, 2.0, 3.0, 4.0]
var ys = [0.0, 1.0, 4.0, 9.0, 16.0]
plot_xy(xs, ys, "x squared")
```

---

### Built-in Functions

| Function | Returns | Description |
|----------|---------|-------------|
| `print(x)` | void | Print any value |
| `input()` | string | Read line from stdin |
| `len(v)` | int | Length of vector |
| `sqrt/sin/cos/tan(x)` | float | Math functions |
| `abs/floor/ceil(x)` | float/int | Rounding |
| `int/float/str(x)` | converted | Type conversion |
| `range(n)` | vec | `[0,1,...,n-1]` |
| `T(m)` | mat | Transpose |
| `norm(v)` | float | Vector magnitude |
| `cross(a,b)` | vec | 3D cross product |
| `normalize(v)` | vec | Unit vector |
| `det(A)` | float | Determinant |
| `inv(A)` | mat | Matrix inverse |
| `solve(A,b)` | vec | Solve Ax=b |
| `zeros(n)` | vec | Zero vector |
| `ones(n)` | vec | Ones vector |
| `eval(e,v=n)` | float | Evaluate symbolic expr |
| `integral(f,v,lo,hi)` | float | Definite integral |
| `integral(f,v)` | sym | Indefinite integral |
| `plot(f,v,lo,hi)` | void | Save function plot PNG |
| `plot_xy(x,y)` | void | Save data plot PNG |

---

## 🎬 Example Programs

| File | What it demonstrates |
|------|----------------------|
| `examples/demo.vect` | **Everything — start here for live demos** |
| `examples/fibonacci.vect` | Recursive functions |
| `examples/control_flow.vect` | if/else, loops, grade logic |
| `examples/linear_system.vect` | Vectors, dot product, matrices |
| `examples/symbolic_derivative.vect` | d/dx, eval, physics |
| `examples/showcase.vect` | KE, rotation, factorial |
| `examples/calculus_v2.vect` | Integration, differentiation v2 |
| `examples/stdlib_test.vect` | norm, cross, det, inv, solve |
| `examples/plot_demo.vect` | plot() generating PNG output |
| `examples/fstring_test.vect` | f-string interpolation |
| `examples/tour_01_arithmetic.vect` | Hands-on: variables |
| `examples/tour_02_control_flow.vect` | Hands-on: if/while/for |
| `examples/tour_03_functions.vect` | Hands-on: functions |
| `examples/tour_04_vectors.vect` | Hands-on: vector ops |
| `examples/tour_05_matrices.vect` | Hands-on: matrix ops |
| `examples/tour_06_symbolic.vect` | Hands-on: calculus |

---

## 🛠 CLI Reference

| Command | Description |
|---------|-------------|
| `vect` | Start interactive REPL |
| `vect run <file.vect>` | Compile and run |
| `vect build <file.vect> [-o name]` | **AOT compile to .exe** |
| `vect check <file.vect>` | Type-check without running |
| `vect ir <file.vect>` | Dump LLVM IR |

---

## 🏗️ How the Compiler Works

```
  source.vect
      │
  ┌───▼──────────────────────────────────────────────────────┐
  │  LEXER  src/lexer.py                                     │
  │  Text → tokens.  Handles d/dx  ·  @  **  f"..."         │
  └───┬──────────────────────────────────────────────────────┘
      │
  ┌───▼──────────────────────────────────────────────────────┐
  │  PARSER  src/parser.py                                   │
  │  Tokens → AST (25 node types, 7 precedence levels)      │
  └───┬──────────────────────────────────────────────────────┘
      │
  ┌───▼──────────────────────────────────────────────────────┐
  │  TYPE CHECKER  src/type_checker.py                       │
  │  Infers types, catches errors, plain-English messages    │
  └───┬──────────────────────────────────────────────────────┘
      │
  ┌───▼──────────────────────────────────────────────────────┐
  │  CODE GENERATOR  src/codegen.py                          │
  │  AST → LLVM IR via llvmlite                              │
  │  Variables: alloca/load/store (SSA)                      │
  │  Loops/branches: explicit basic blocks                   │
  │  Vec/mat/sym: runtime calls via ctypes                   │
  └───┬──────────────────────────────────────────────────────┘
      │
  ┌───▼──────────────────────────────────────────────────────┐
  │  JIT (vect run)            AOT (vect build)              │
  │  llvmlite MCJIT            Object file + gcc link        │
  │  Runs in-process           Produces standalone .exe      │
  └───┬──────────────────────────────────────────────────────┘
      │
  ┌───▼──────────────────────────────────────────────────────┐
  │  RUNTIME  src/runtime.py                                 │
  │  Python ctypes callbacks for vec/mat/sym/plot            │
  │  Object registry: int IDs → Python objects              │
  │  sympy: diff, integrate — completely hidden from user    │
  │  matplotlib: plot() — saves PNG                         │
  └──────────────────────────────────────────────────────────┘
```

### Design decisions

| Decision | Reason |
|----------|--------|
| `llvmlite` not C++ LLVM | Prebuilt wheel — `pip install` works with no C++ toolchain |
| Python runtime for vec/mat | Correct, readable, easy to extend |
| sympy for diff/integrate | Full CAS in one package, hidden behind language syntax |
| matplotlib for plot | Zero setup, outputs clean PNG |
| AOT via gcc | MSYS2 gcc is the most available linker on Windows |

---

## 🧪 Tests

```powershell
venv\Scripts\pytest tests/ -q     # 154 tests, ~5 seconds
```

| File | What it covers | Count |
|------|---------------|-------|
| `test_lexer.py` | Tokens, positions, f-strings, operators | 39 |
| `test_parser.py` | All 25 AST node types, precedence | 47 |
| `test_end_to_end.py` | Compile → JIT → run → assert stdout | 68 |

```
======================== 154 passed in 5.10s ========================
```

---

## 📁 Project Structure

```
Vect/
├── src/
│   ├── lexer.py              Tokenizer (f-strings, d/dx, ·, @)
│   ├── ast_nodes.py          25 AST node dataclasses
│   ├── parser.py             Recursive-descent parser
│   ├── type_checker.py       Static type checker
│   ├── codegen.py            LLVM IR code generator
│   ├── runtime.py            Python ctypes runtime
│   ├── aot.py                AOT compiler (vect build)
│   ├── pipeline.py           Compilation pipeline
│   ├── repl.py               Interactive REPL
│   └── main.py               CLI (vect command)
│
├── examples/
│   ├── demo.vect             Full demo — best for presentations
│   ├── fibonacci.vect        Recursion
│   ├── linear_system.vect    Vectors & matrices
│   ├── symbolic_derivative.vect   d/dx, eval, physics
│   ├── calculus_v2.vect      Integration (v2)
│   ├── stdlib_test.vect      norm, cross, det, inv, solve
│   ├── plot_demo.vect        plot() output
│   ├── fstring_test.vect     f-string interpolation
│   ├── tour_01 – tour_06.vect Hands-on learning programs
│   └── showcase.vect         Everything at once
│
├── tests/                    154 tests
├── docs/
│   └── vect-language-guide.html  Full language guide (→ PDF)
├── vscode-extension/         Syntax highlighting
├── scripts/
│   ├── record_demo.py        Demo recording script
│   └── RECORDING.md          GIF recording guide
├── stdlib/math.vect          clamp, lerp, sign, min, max
├── .github/workflows/test.yml CI on every push
├── requirements.txt
├── pyproject.toml
├── setup_vect.ps1            One-shot Windows setup
└── LICENSE                   MIT
```

---

## 📚 Dependencies

| Package | Version | Role |
|---------|---------|------|
| `llvmlite` | 0.43.0 | LLVM Python bindings + JIT |
| `sympy` | 1.13.1 | Symbolic math (d/dx, integral) |
| `matplotlib` | ≥3.7.0 | plot() PNG output |
| `click` | 8.1.7 | CLI framework |
| `pytest` | 8.2.2 | Test runner |

---

## 🗺️ Roadmap

| Feature | Version | Status |
|---------|---------|--------|
| Core language + LLVM codegen | v1 | ✅ |
| Vectors, matrices, dot product | v1 | ✅ |
| Symbolic differentiation (d/dx) | v1 | ✅ |
| REPL, CLI, type checker | v1 | ✅ |
| 138-test suite, CI | v1 | ✅ |
| f-string interpolation | **v2** | ✅ |
| norm, cross, det, inv, solve | **v2** | ✅ |
| Symbolic integration | **v2** | ✅ |
| plot() / plot_xy() | **v2** | ✅ |
| AOT compilation to .exe | **v2** | ✅ |
| Multi-file imports | v3 | 🔲 |
| Type inference (no annotations) | v3 | 🔲 |
| Better error recovery | v3 | 🔲 |
| Jupyter kernel | v3 | 🔲 |
| Full static C runtime | v3 | 🔲 |

---

## 📄 Documentation

Full language guide at [`docs/vect-language-guide.html`](./docs/vect-language-guide.html)

Open in any browser → **Ctrl+P → Save as PDF** for a complete offline reference covering all 18 topics from installation through the compiler internals.

---

<div align="center">

## 👤 Author

**Eddie Gah** — [@Eddiegah](https://github.com/Eddiegah)

<br/>

*Built to prove that compiler construction is approachable,*
*language design is a creative act,*
*and scientific computing can be syntax — not scaffolding.*

<br/>

---

**If Vect made you think differently about what a programming language can be — that's the whole point.**

```
venv\Scripts\vect run examples\demo.vect
```

⭐ **Star the repo if you found it interesting.**

<br/>

[![GitHub](https://img.shields.io/badge/github.com%2FEddiegah%2FVect-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Eddiegah/Vect)

</div>
