from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def candidates() -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*.py")
        if "scripts" in p.parts
        and not p.name.startswith("test_")
        and p.name != Path(__file__).name
    )


def imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def main() -> None:
    rows = []
    for path in candidates():
        sibling_modules = {p.stem for p in path.parent.glob("*.py")}
        imports = imported_roots(path)
        external = sorted(
            name
            for name in imports
            if name not in sys.stdlib_module_names
            and name not in sibling_modules
            and not name.startswith("_")
        )
        rows.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "already_pep723": "# /// script" in path.read_text(encoding="utf-8"),
                "external_imports": external,
            }
        )
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
