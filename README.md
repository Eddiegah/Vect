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

[![Tests](https://img.shields.io/badge/Tests-174%20Passing-00C853?style=for-the-badge&logo=pytest&logoColor=white)](./tests)
[![CI](https://github.com/Eddiegah/Vect/actions/workflows/test.yml/badge.svg)](https://github.com/Eddiegah/Vect/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.9%20–%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LLVM](https://img.shields.io/badge/LLVM-Native%20Codegen-262D3A?style=for-the-badge&logo=llvm&logoColor=white)](https://llvm.org)
[![License](https://img.shields.io/badge/License-MIT-FF6F00?style=for-the-badge)](./LICENSE)
[![Version](https://img.shields.io/badge/Version-5.0-7C4DFF?style=for-the-badge)](https://github.com/Eddiegah/Vect)

<br/>

[**⚡ Install**](#-installation) · [**🚀 Quickstart**](#-quickstart) · [**📖 Language Tour**](#-language-tour) · [**🏗 How It Works**](#-how-the-compiler-works) · [**🧪 Tests**](#-tests) · [**📁 Structure**](#-project-structure)

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

`d/dx` is not a function call — it is a **language operator**, like `+` or `*`. `[1, 2, 3]` is a vector **literal**, as native as the number `42`. `@` is matrix multiply. `·` is dot product. `integral()` integrates. No imports. No library names. Just the language.

> Vect compiles to **real native x86-64 machine code** via LLVM — the same backend used by Clang, Rust, and Swift. Not an interpreter. Not a transpiler. A genuine compiler.

---

## ✨ Everything Vect Can Do

| Feature | Syntax | Result |
|---------|--------|--------|
| Native vectors | `var v = [1.0, 2.0, 3.0]` | First-class value |
| Element-wise ops | `v1 + v2`, `v1 * 2.0` | `[5, 7, 9]` |
| Dot product | `v1 · v2` | `32.0` |
| Cross product | `cross(a, b)` | 3D vector |
| Vector norm | `norm(v)` | `5.0` |
| Normalize | `normalize(v)` | Unit vector |
| Matrix multiply | `A @ B` | Matrix |
| Transpose | `T(A)` | Matrix |
| Determinant | `det(A)` | `-2.0` |
| Inverse | `inv(A)` | Matrix |
| Solve Ax=b | `solve(A, b)` | Solution vector |
| Differentiation | `d/dx(f(x))` | `2*x + 3` |
| Evaluate symbolic | `eval(df, x=2.0)` | `7.0` |
| Definite integral | `integral(f(x), "x", 0, 3)` | `9.0` |
| Indefinite integral | `integral(f(x), "x")` | Symbolic |
| Plot function | `plot(f(x), x, lo, hi)` | PNG file |
| Plot data | `plot_xy(xs, ys, "title")` | PNG file |
| f-strings | `f"Hello {name}!"` | `Hello Eddie!` |
| Type inference | `fn add(a, b) { return a+b }` | No annotations needed |
| Multi-file import | `import "stdlib/physics.vect"` | Functions available |
| AOT compile | `vect build file.vect` | Native `.exe` |
| Jupyter kernel | `vect notebook` | Run in notebooks |
| REPL | `vect` | Interactive session |
| Error recovery | `vect check file.vect` | All errors at once |

---

## 📦 Installation

### Requirements

| | Requirement | Notes |
|--|------------|-------|
| ✅ | Python **3.11** (3.9–3.12) | 3.13+ not yet supported |
| ✅ | Git | For cloning |
| ✅ | VS Code | Optional, for syntax highlighting |
| ✅ | gcc (MSYS2) | Only for `vect build` (AOT) |

> **Windows:** No Visual Studio, no CMake needed for normal use.

---

### Option A — One-shot setup (Windows)

```powershell
git clone https://github.com/Eddiegah/Vect.git
cd Vect
.\setup_vect.ps1
```

---

### Option B — Manual (all platforms)

```bash
git clone https://github.com/Eddiegah/Vect.git
cd Vect

# Windows
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

# macOS / Linux
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

**Verify:**
```bash
python -c "import llvmlite.binding as llvm; llvm.initialize(); llvm.initialize_native_target(); print('LLVM OK')"
```

---

### VS Code Syntax Highlighting

```powershell
# Windows
Copy-Item -Recurse vscode-extension "$env:USERPROFILE\.vscode\extensions\vect-lang-0.1.0"

# macOS / Linux
cp -r vscode-extension ~/.vscode/extensions/vect-lang-0.1.0
```

Restart VS Code — open any `.vect` file to see syntax highlighting.

---

## 🚀 Quickstart

### REPL
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
```

### Run a file
```powershell
venv\Scripts\vect run examples\demo.vect
venv\Scripts\vect run examples\calculus_v2.vect
venv\Scripts\vect run examples\multifile_demo.vect
```

### Build a native executable
```powershell
venv\Scripts\vect build examples\fibonacci.vect -o fib
.\fib.exe
# 0 1 1 2 3 5 8 13 21 34 55
```

### Open in Jupyter
```powershell
venv\Scripts\python -m src.kernel install
venv\Scripts\pip install jupyter
venv\Scripts\jupyter notebook examples\vect_demo.ipynb
```

### CLI reference
| Command | Description |
|---------|-------------|
| `vect` | Start REPL |
| `vect run <file>` | Compile and run |
| `vect build <file> [-o name]` | AOT → native .exe |
| `vect check <file>` | Type-check, show all errors |
| `vect ir <file>` | Dump LLVM IR |
| `vect notebook` | Install kernel + launch Jupyter |

---

## 📖 Language Tour

### Variables
```vect
var x     = 42
var pi    = 3.14159
var name  = "Vect"
var ready = true

# Type annotations optional
var count: int   = 0
var ratio: float = 1.0 / 3.0
```

### F-strings
```vect
var score = 95
var name  = "Eddie"
print(f"Hello, {name}!")              # Hello, Eddie!
print(f"Score: {score}, doubled: {score * 2}")
```

### Arithmetic
```vect
print(2 + 3 * 4)        # 14
print((2 + 3) * 4)      # 20
print(2.0 ** 10.0)      # 1024.0
print(17 % 5)           # 2
```

### Control flow
```vect
if score >= 90 { print("A") }
else if score >= 80 { print("B") }
else { print("C") }

var i = 1
var total = 0
while i <= 100 { total = total + i\ni = i + 1 }

for x in [1.0, 4.0, 9.0] { print(sqrt(x)) }
```

### Functions — annotations optional
```vect
# Annotated
fn factorial(n: int) -> int {
    if n <= 1 { return 1 }
    return n * factorial(n - 1)
}

# Inferred — works for any numeric type
fn double(x) { return x * 2 }
print(double(5))        # 10
print(double(3.14))     # 6.28

# String inference
fn greet(name) { print(f"Hello, {name}!") }
greet("Alice")
```

### ⭐ Native Vectors
```vect
var a = [1.0, 2.0, 3.0]
var b = [4.0, 5.0, 6.0]

print(a + b)            # [5, 7, 9]
print(a * 3.0)          # [3, 6, 9]
print(a · b)            # 32.0  dot product
print(norm(a))          # 3.742
print(normalize(a))     # [0.267, 0.535, 0.802]
print(cross(a, b))      # [0, 0, 0]
print(zeros(4))         # [0, 0, 0, 0]
print(ones(3))          # [1, 1, 1]
print(a[0])             # 1.0
```

### ⭐ Native Matrices
```vect
var A = [[1.0, 2.0], [3.0, 4.0]]
var B = [[5.0, 6.0], [7.0, 8.0]]

print(A @ B)            # [[19,22],[43,50]]
print(T(A))             # [[1,3],[2,4]]
print(det(A))           # -2.0
print(inv(A))           # [[-2,1],[1.5,-0.5]]

var b = [1.0, 0.0]
print(solve(A, b))      # solution to Ax=b
```

### ⭐⭐ Symbolic Differentiation
```vect
sym f(x) = x**2 + 3*x + 1
var df = d/dx(f(x))
print(df)                    # 2*x + 3
print(eval(df, x=2.0))       # 7.0

# Physics
sym height(t) = 20.0*t - 4.9*t**2
var velocity = d/dt(height(t))
print(velocity)              # 20.0 - 9.8*t
print(eval(velocity, t=2.0)) # 0.4
```

### ⭐⭐ Symbolic Integration
```vect
sym f(x) = x**2
var area = integral(f(x), "x", 0.0, 3.0)
print(area)              # 9.0

sym force(x) = 2.0*x + 1.0
var work = integral(force(x), "x", 0.0, 5.0)
print(work)              # 30.0
```

### Plot
```vect
sym wave(x) = sin(x) * 2.0
plot(wave(x), x, -6.28, 6.28, "Sine Wave")   # saves vect_plot.png

var xs = [0.0, 1.0, 2.0, 3.0]
var ys = [0.0, 1.0, 4.0, 9.0]
plot_xy(xs, ys, "x squared")
```

### Multi-file imports
```vect
import "stdlib/mathlib.vect"
import "stdlib/vectors.vect"
import "stdlib/physics.vect"

print(clamp(15.0, 0.0, 10.0))          # 10.0
var scores = [88.0, 92.0, 95.0, 78.0]
print(vec_mean(scores))                 # 88.25
print(kinetic_energy(70.0, 10.0))       # 3500.0
```

### Error messages — all at once
```vect
# vect check myfile.vect shows ALL errors:
# Found 3 error(s):
# [1] Type error at line 3: 'x' is not defined
# [2] Type error at line 5: Cannot use '+' on string and int
# [3] Type error at line 8: Wrong number of arguments
```

---

## 🎬 Example Programs

| File | What it shows |
|------|---------------|
| `examples/demo.vect` | Everything — **start here** |
| `examples/fibonacci.vect` | Recursion |
| `examples/control_flow.vect` | if/else, loops |
| `examples/linear_system.vect` | Vectors + matrices |
| `examples/symbolic_derivative.vect` | d/dx + eval |
| `examples/calculus_v2.vect` | Integration |
| `examples/stdlib_test.vect` | norm, det, inv, solve |
| `examples/plot_demo.vect` | plot() → PNG |
| `examples/fstring_test.vect` | f-string interpolation |
| `examples/multifile_demo.vect` | 3 imports working together |
| `examples/vect_demo.ipynb` | Jupyter notebook |
| `examples/tour_01–06.vect` | Hands-on learning series |

---

## 🏗 How the Compiler Works

```
  source.vect
      │
  ┌───▼─────────────────────────────────────────────┐
  │  LEXER  src/lexer.py                            │
  │  Text → tokens  (d/dx · @ f"..." import)       │
  └───┬─────────────────────────────────────────────┘
      │
  ┌───▼─────────────────────────────────────────────┐
  │  PARSER  src/parser.py                          │
  │  Tokens → AST (25 node types, 7 precedence lvl)│
  └───┬─────────────────────────────────────────────┘
      │
  ┌───▼─────────────────────────────────────────────┐
  │  IMPORT RESOLVER  src/pipeline.py               │
  │  Recursively loads imported files               │
  │  Injects fn/sym defs, prevents cycles           │
  └───┬─────────────────────────────────────────────┘
      │
  ┌───▼─────────────────────────────────────────────┐
  │  TYPE CHECKER  src/type_checker.py              │
  │  Infers types, collects ALL errors at once     │
  │  Monomorphizes inferred functions per call      │
  └───┬─────────────────────────────────────────────┘
      │
  ┌───▼─────────────────────────────────────────────┐
  │  CODE GENERATOR  src/codegen.py                 │
  │  AST → LLVM IR via llvmlite                    │
  │  Inferred fns: compiled on demand per type      │
  └───┬──────────────────┬──────────────────────────┘
      │                  │
  ┌───▼──────────┐  ┌────▼─────────────────────────┐
  │  JIT         │  │  AOT  src/aot.py              │
  │  vect run    │  │  vect build → native .exe     │
  └──────────────┘  └──────────────────────────────┘
      │
  ┌───▼─────────────────────────────────────────────┐
  │  RUNTIME  src/runtime.py                        │
  │  Python ctypes: vec/mat/sym/plot callbacks      │
  └─────────────────────────────────────────────────┘
```

---

## 🧪 Tests

```powershell
venv\Scripts\pytest tests/ -q    # 159 tests, ~4 seconds
```

| File | Covers | Count |
|------|--------|-------|
| `test_lexer.py` | Tokens, positions, f-strings, d/dx, · | 39 |
| `test_parser.py` | All AST nodes, precedence, examples | 47 |
| `test_end_to_end.py` | Compile → run → assert stdout | 73 |

```
======================== 159 passed in 4.04s ========================
```

---

## 📁 Project Structure

```
Vect/
├── src/
│   ├── lexer.py              Tokenizer
│   ├── ast_nodes.py          25 AST node dataclasses
│   ├── parser.py             Recursive-descent parser
│   ├── type_checker.py       Type inference + error collection
│   ├── codegen.py            LLVM IR generator + monomorphization
│   ├── runtime.py            Python ctypes runtime
│   ├── aot.py                AOT compiler → .exe
│   ├── pipeline.py           Import resolver + pipeline
│   ├── repl.py               Interactive REPL
│   ├── kernel.py             Jupyter kernel
│   └── main.py               CLI entry point
│
├── examples/                 16 example programs + demo notebook
├── stdlib/                   mathlib.vect · vectors.vect · physics.vect
├── tests/                    159 passing tests
├── docs/
│   ├── vect-language-guide.html    Full reference (→ PDF)
│   └── vect-wow-factor.html        Shareable wow document (→ PDF)
├── vscode-extension/         Syntax highlighting
├── scripts/
│   ├── record_demo.py        Demo recording script
│   └── RECORDING.md          GIF guide
├── .github/workflows/        CI — runs on every push
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
| `ipykernel` | ≥6.0.0 | Jupyter kernel |
| `click` | 8.1.7 | CLI |
| `pytest` | 8.2.2 | Tests |

---

## 🗺️ Roadmap

| Feature | Version | Status |
|---------|---------|--------|
| Core language + LLVM codegen | v1 | ✅ |
| Vectors, matrices, d/dx | v1 | ✅ |
| REPL, CLI, type checker, 138 tests | v1 | ✅ |
| f-strings, stdlib, integration | v2 | ✅ |
| plot(), AOT .exe compilation | v2 | ✅ |
| Multi-file imports | v3 | ✅ |
| Error recovery (all errors at once) | v3 | ✅ |
| Type inference (no annotations) | v3 | ✅ |
| Jupyter kernel | v3 | ✅ |
| 159 tests, CI | v3 | ✅ |
| Better error recovery | v4 | ✅ |
| String operations (10 built-ins) | v4 | ✅ |
| VS Code autocomplete + hover + diagnostics | v4 | ✅ |
| Auto-formatter (`vect fmt`) | v4 | ✅ |
| Extended stdlib (statistics, linalg, strings) | v4 | ✅ |
| 174 tests | v4 | ✅ |
| Typed vectors `vec<int>`, `vec<float>` | v5 | ✅ |
| Multiple return values / tuple syntax | v5 | ✅ |
| 9 stdlib files (math, vectors, physics, statistics, linalg, strings, geometry, ml, calculus) | v5 | ✅ |
| Better AOT runtime (standalone .exe) | v6 | 🔲 |
| Package manager | v6 | 🔲 |

---

## 📄 Documentation

| Document | Description |
|----------|-------------|
| [`docs/vect-language-guide.html`](./docs/vect-language-guide.html) | Full language reference — open in browser, Ctrl+P → Save as PDF |
| [`docs/vect-wow-factor.html`](./docs/vect-wow-factor.html) | What makes Vect different — shareable PDF |

---

<div align="center">

## 👤 Author

**Eddie Gah** — [@Eddiegah](https://github.com/Eddiegah)

*Compiler construction is approachable. Language design is a creative act.*
*Scientific computing can be syntax — not scaffolding.*

---

**⭐ Star the repo if Vect made you think differently about what a language can be.**

```
venv\Scripts\vect run examples\demo.vect
```

[![GitHub](https://img.shields.io/badge/github.com%2FEddiegah%2FVect-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Eddiegah/Vect)

</div>
