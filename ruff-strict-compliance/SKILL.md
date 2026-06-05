---
name: ruff-strict-compliance
description: >-
  Enforces strict compliance with Ruff linting and formatting rules. Stops agents from using '# noqa' comments, dismissing warnings as "stylistic," or claiming rules do not apply to CLI tools like Typer.
---

# Ruff Strict Compliance

## Overview
This skill enforces **strict, zero-warning compliance** with the Ruff linter and formatter. Coding agents often vibe-code around linter errors by dismissing them as "stylistic/optional" or lazy-patching them with `# noqa` comments. This skill bans those practices and mandates writing clean, idiomatic Python that naturally passes Ruff.

---

## Core Mandates

### 1. No Excuses, No Dismissals
* You are **never** allowed to dismiss a Ruff warning as "purely stylistic," "optional," or "non-critical." 
* You must fix the underlying code pattern. If Ruff flags it, it is a code smell.

### 2. Zero-Tolerance for `# noqa`
* Do **NOT** add `# noqa` or `# type: ignore` comments to bypass Ruff alerts.
* You may only use `# noqa` if there is a documented, unavoidable library conflict (e.g., importing a module to trigger side effects in a legacy framework where there is no entrypoint). Even then, you must seek explicit user approval first.

### 3. Verification
* After editing any Python code, you must run `ruff check` and `ruff format` to verify compliance. Do not wait for the user to report lint failures.

---

## Refactoring Recipes for Common Rules

### 1. Typer CLI (Resolving B008, F841, etc.)

**The Problem:** In Typer, developers often write CLI options using `typer.Option(...)` or `typer.Argument(...)` directly in function signatures as default values. This triggers Ruff rule **B008** (Do not perform function call `typer.Option` in argument defaults). 

To bypass this, lazy agents write `# noqa: B008` or `# noqa: F841`.

**The Right Way (Typer with Annotated):**
Use Python's `typing.Annotated` (or `typing_extensions.Annotated` for Python < 3.9) to define options and arguments. This completely avoids B008 and is the modern, type-safe standard recommended by Typer.

```python
# ❌ INCORRECT (Triggers B008 and F841)
import typer

app = typer.Typer()

@app.command()
def main(
    name: str = typer.Option("World", help="Who to greet"), # B008 triggered here
    verbose: bool = typer.Option(False, "--verbose", "-v") # B008 triggered here
):
    print(f"Hello {name}")
```

```python
#  CORRECT (Modern Type-Safe Pattern - 0 Ruff Warnings)
import typer
from typing import Annotated

app = typer.Typer()

@app.command()
def main(
    name: Annotated[str, typer.Option(help="Who to greet")] = "World",
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False
):
    print(f"Hello {name}")
```

---

### 2. Mutable Default Arguments (B006 / B008)

**The Problem:** Using mutable structures like empty lists `[]` or dicts `{}` or function calls as default arguments.

```python
# ❌ INCORRECT (B006/B008)
def process_items(items: list = [], config: dict = dict()):
    items.append("new_item")
    return items
```

```python
#  CORRECT
from typing import Optional

def process_items(items: Optional[list] = None, config: Optional[dir] = None):
    if items is None:
        items = []
    if config is None:
        config = {}
    items.append("new_item")
    return items
```

---

### 3. Unused Imports & Variables (F401, F841)

**The Problem:** Leaving debug imports or assigning variables that are never read.

```python
# ❌ INCORRECT (F401/F841)
import os  # F401: unused import
import sys # noqa: F401 (Banned bypass!)

def compute(x):
    result = x * 2  # F841: local variable is assigned but never used
    return x
```

```python
#  CORRECT
def compute(x):
    return x
```

---

### 4. Star Imports (F403 / F405)

**The Problem:** Importing everything from a module (`from module import *`), which pollutes the namespace and breaks static analysis.

```python
# ❌ INCORRECT (F403)
from math import * # noqa: F403
```

```python
#  CORRECT
from math import pi, sin, cos
```

---

### 5. Blind Exceptions (BLE) & Tryceratops (TRY)

**The Problem:** Coding agents often catch broad, generic exceptions (`Exception`) to suppress errors, triggering rule **BLE001** (Do not catch blind `Exception`). Furthermore, they use generic `Exception` types or embed verbose strings directly in raised errors, triggering Tryceratops (**TRY**) rules (e.g., `TRY002` for custom exceptions, `TRY003` for avoiding long exception messages).

```python
# ❌ INCORRECT (Triggers BLE001, TRY002, TRY003)
def process_data(data):
    try:
        return data["value"] * 10
    except Exception: # BLE001 (blind exception caught)
        raise Exception("We failed to process the data because the value key was missing or malformed") # TRY002 (raw Exception), TRY003 (long string)
```

```python
#  CORRECT (Modern Standard - 0 Ruff Warnings)
class DataProcessingError(Exception):
    """Custom exception for domain-specific errors."""
    pass

def process_data(data: dict) -> int:
    try:
        return data["value"] * 10
    except KeyError as e: # Specific Exception
        raise DataProcessingError("Missing 'value' key") from e
    except TypeError as e: # Specific Exception
        raise DataProcessingError("Value is not a number") from e
```

---

## Checklist Before Ending Your Turn

1. **Format:** Run `ruff format .` to make sure all code matches the project styling.
2. **Lint:** Run `ruff check .` to inspect all warnings.
3. **Fix:** Refactor any violations using the clean patterns described above. Do **NOT** use `# noqa`.

