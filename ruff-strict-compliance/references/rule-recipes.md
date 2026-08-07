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

Prefer `typing.Annotated` for Typer options/arguments instead of function calls as defaults:

```python
import typer
from typing import Annotated

app = typer.Typer()

@app.command()
def main(
    name: Annotated[str, typer.Option(help="Who to greet")] = "World",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
):
    print(f"Hello {name}")
```

### Mutable defaults — B006 / B008

Use `None` and initialize inside the function rather than mutable/default-call expressions:

```python
def process_items(items: list | None = None, config: dict | None = None):
    if items is None:
        items = []
    if config is None:
        config = {}
    items.append("new_item")
    return items
```

### Unused imports and variables — F401 / F841

Remove unused imports and collapse throwaway assignments instead of suppressing them.

### Star imports — F403 / F405

Import the exact names required rather than `from module import *`.

### Blind exceptions / Tryceratops — BLE / TRY

Catch specific exceptions and translate them to domain-specific exceptions when appropriate:

```python
class DataProcessingError(Exception):
    """Custom exception for domain-specific errors."""


def process_data(data: dict) -> int:
    try:
        return data["value"] * 10
    except KeyError as exc:
        raise DataProcessingError("Missing 'value' key") from exc
    except TypeError as exc:
        raise DataProcessingError("Value is not a number") from exc
```

### `os.path` → `pathlib` — PTH

Prefer `Path` operations and explicit encodings:

```python
from pathlib import Path


def get_config_content(filename: str) -> str:
    full_path = Path.cwd() / "config" / filename
    if full_path.exists():
        return full_path.read_text(encoding="utf-8")
    return ""
```

### Mutable class attributes — RUF012

Mark true class state as `ClassVar`, or initialize instance state in `__init__`:

```python
from typing import ClassVar


class ProjectManager:
    active_tasks: ClassVar[list[str]] = []
    default_config: ClassVar[dict[str, str]] = {}
```

### Comprehension wrappers — C4

Prefer direct literals/comprehensions instead of redundant wrappers such as `list([x for x in data])` or `dict()` when `{}` is clearer.

### Returns and unnecessary branches — RET

Return expressions directly and remove `else` / `elif` after an unconditional `return` or `raise`:

```python
def check_value(x) -> str:
    if x > 10:
        return "large"
    return "small"
```

### Simplify — SIM

Collapse redundant nested conditions and direct boolean returns where that preserves clarity:

```python
def is_valid_user(user) -> bool:
    return bool(user.is_active and user.has_permission)
```

### Modern type syntax — UP

For supported Python versions, prefer builtin generics:

```python
def process_data(items: list[str]) -> dict[str, tuple[int, int]]:
    ...
```

### Builtin shadowing — A

Use semantic names such as `user_id` and `statuses`, not `id`, `list`, `type`, etc.

### Logging interpolation — G

Prefer lazy logging interpolation:

```python
logger.info("Processing event: %s", name)
```

### Assertions and swallowed exceptions — S

Do not use `assert` for production input validation and do not silently `pass`/`continue` in exception handlers. Validate explicitly and handle, log, translate, or re-raise expected exceptions.

```python
def process_age(age: int):
    if age < 0:
        raise ValueError("Age cannot be negative")
    try:
        do_something()
    except ValueError as exc:
        logger.warning("Swallowing expected error: %s", exc)
```

### Commented-out code — ERA

Delete dead commented-out code. Version control is the archive.

## Rule lookup discipline

These recipes are examples, not a substitute for the project's configured Ruff version or the current rule documentation. When a diagnostic is unfamiliar or version-sensitive, inspect the actual diagnostic and current Ruff documentation before choosing a refactor.