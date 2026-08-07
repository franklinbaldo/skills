# Ruff rule recipes

Load this reference **on demand** when a concrete Ruff diagnostic needs an implementation pattern or when the repository has no Ruff configuration yet. The entry-point skill intentionally omits this catalog from always-loaded context.

## Enabling strict rule families

Ruff's default `select` only enables `E4`, `E7`, `E9`, and `F`. Several recipes below (PTH, TRY, BLE, G, ERA, S, plus B, C4, SIM, RET, UP, A, RUF) cover opt-in families that only fire if the project enables them in `pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["ALL"]  # or explicitly: ["E", "F", "B", "C4", "SIM", "RET", "UP", "A", "PTH", "TRY", "BLE", "G", "ERA", "S", "RUF"]
ignore = ["D", "ANN", "COM812"]  # common ignores; tune to the project
```

If the project has no such config, propose adding one rather than assuming these rules are active.

## Refactoring recipes for common rules

### Typer CLI — B008, F841
Prefer `typing.Annotated` for Typer options/arguments instead of function calls as defaults.

### Mutable defaults — B006 / B008
Use `None` and initialize inside the function rather than mutable/default-call expressions.

### Unused imports and variables — F401 / F841
Remove unused imports and collapse throwaway assignments instead of suppressing them.

### Star imports — F403 / F405
Import the exact names required rather than `from module import *`.

### Blind exceptions / Tryceratops — BLE / TRY
Catch specific exceptions and translate them to domain-specific exceptions when appropriate.

### `os.path` → `pathlib` — PTH
Prefer `Path` operations and explicit encodings.

### Mutable class attributes — RUF012
Mark true class state as `ClassVar`, or initialize instance state in `__init__`.

### Comprehension wrappers — C4
Prefer direct literals/comprehensions instead of redundant wrappers.

### Returns and unnecessary branches — RET
Return expressions directly and remove `else` / `elif` after an unconditional `return` or `raise`.

### Simplify — SIM
Collapse redundant nested conditions and direct boolean returns where that preserves clarity.

### Modern type syntax — UP
For supported Python versions, prefer builtin generics.

### Builtin shadowing — A
Use semantic names such as `user_id` and `statuses`, not `id`, `list`, `type`, etc.

### Logging interpolation — G
Prefer lazy logging interpolation.

### Assertions and swallowed exceptions — S
Do not use `assert` for production input validation and do not silently `pass`/`continue` in exception handlers.

### Commented-out code — ERA
Delete dead commented-out code. Version control is the archive.

## Rule lookup discipline

These recipes are examples, not a substitute for the project's configured Ruff version or the current rule documentation. When a diagnostic is unfamiliar or version-sensitive, inspect the actual diagnostic and current Ruff documentation before choosing a refactor.