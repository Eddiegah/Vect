# Vect — Next Steps (Resume in September)

## Current state when you left (July 2025)

- **Version:** v4.0
- **Tests:** 174 passing
- **All features working:** vectors, matrices, d/dx, integral, plot, f-strings,
  multi-file imports, type inference, Jupyter kernel, AOT .exe,
  string operations, formatter, VS Code autocomplete
- **Repo:** github.com/Eddiegah/Vect

---

## How to get back up to speed

```powershell
cd C:\Projects\Vect
venv\Scripts\activate
venv\Scripts\pytest tests\ -q          # confirm 174 tests pass
venv\Scripts\vect run examples\demo.vect   # confirm it runs
```

If venv is gone (3+ months later), rebuild it:
```powershell
py -3.11 -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pip install -e .
```

---

## What to build in September (priority order)

### Priority 1 — Most impactful
**Multiple return values**
```vect
fn min_max(v: vec) -> (float, float) {
    return (vec_min(v), vec_max(v))
}
var (lo, hi) = min_max(scores)
```
Files to touch: `ast_nodes.py`, `parser.py`, `type_checker.py`, `codegen.py`

---

**More stdlib files**
- `stdlib/calculus.vect` — Newton's method, numerical gradient
- `stdlib/ml.vect` — dot product similarity, softmax, sigmoid
- `stdlib/geometry.vect` — distance, area, rotation
These are just `.vect` files — no compiler changes needed.

---

### Priority 2 — Nice to have
**Typed vectors `vec<int>`**
Currently all vectors are float64. `vec<int>` would allow integer arrays.
Requires type system changes in `type_checker.py` and `runtime.py`.

**Better AOT runtime**
Currently `vect build` .exe needs Python on PATH.
Goal: produce a truly standalone binary.
Approach: compile the Python runtime to a static library using Cython or Nuitka.

---

### Priority 3 — When there's an ecosystem
**Package manager**
`vect pkg install physics`
Requires: a GitHub-based registry, a manifest format, and a resolver.
This is a separate product, not a feature. Only worth doing if people
are actually writing and sharing Vect libraries.

---

## Files you'll want to read first

| File | Why |
|------|-----|
| `src/codegen.py` | The most complex file — LLVM IR generation |
| `src/type_checker.py` | Type inference and error collection |
| `src/pipeline.py` | Import resolution — understand this before touching multi-file stuff |
| `src/runtime.py` | Where vec/mat/sym/plot/string operations live |
| `tests/test_end_to_end.py` | Best place to understand what the language can do |

---

## People to share with before September

- Push the `eddie.vect` screenshot to socials
- Share `docs/vect-wow-factor.html` as PDF with friends
- Point them to `docs/vect-starter-guide.html` if they want to try it
- The LinkedIn description is already written — post it if you haven't

---

*Built July 2025 by Edmund Eric Gah.*
*github.com/Eddiegah/Vect*
