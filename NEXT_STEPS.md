# Vect — Next Steps (Resume Later)

## Current state (July 2025)

- **Version:** v5.0
- **Tests:** 174 passing
- **GitHub:** github.com/Eddiegah/Vect

### Everything that's been built

| Feature | Status |
|---------|--------|
| Core language (vars, functions, control flow) | ✅ |
| Vectors, matrices, dot product, d/dx, integral | ✅ |
| f-strings, plot(), AOT .exe, string ops | ✅ |
| Multi-file imports + 9 stdlib files | ✅ |
| Type inference (no annotations needed) | ✅ |
| Typed vectors `vec<int>`, `vec<float>` | ✅ |
| Multiple return values / tuple syntax | ✅ |
| Error recovery (all errors at once) | ✅ |
| Jupyter kernel | ✅ |
| VS Code autocomplete + hover + diagnostics | ✅ |
| Auto-formatter (`vect fmt`) | ✅ |
| REPL, CLI (run/build/check/ir/fmt/notebook) | ✅ |
| 9 stdlib files (math, vectors, physics, stats, linalg, strings, geometry, ml, calculus) | ✅ |

---

## How to get back up to speed

```powershell
cd C:\Projects\Vect
py -3.11 -m venv venv          # if venv is gone
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
venv\Scripts\pytest tests\ -q   # confirm 174 tests pass
venv\Scripts\vect run examples\demo.vect
```

---

## What's genuinely left (v6)

| Feature | What it means | Effort |
|---------|--------------|--------|
| **Better AOT runtime** | `.exe` that needs zero Python on PATH. Use Cython/Nuitka to compile the Python runtime to a static lib. | High |
| **Package manager** | `vect pkg install physics` — GitHub-based registry. Separate product. | Very high |
| **More example programs** | Physics simulations, ML demos, data visualisation | Low |
| **Performance profiling** | Measure JIT vs Python overhead, optimise hot paths | Medium |

---

## Files to read first when resuming

| File | Why |
|------|-----|
| `src/codegen.py` | LLVM IR generation — most complex file |
| `src/type_checker.py` | Type inference and error collection |
| `src/pipeline.py` | Import resolution |
| `src/runtime.py` | Vec/mat/sym/plot/string operations |
| `tests/test_end_to_end.py` | Best overview of what the language can do |

---

*Built July 2025 by Edmund Eric Gah.*
*github.com/Eddiegah/Vect*
