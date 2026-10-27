#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Enforce ~5k tokens (20,000 UTF-8 bytes) on new or modified source files."""
import os
import subprocess
import sys
from pathlib import Path

LIMIT = 20_000

def git(*args):
    return subprocess.check_output(["git", *args])

def paths(raw):
    return {p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p}

def base():
    ref = os.environ.get("TOKEN_LIMIT_BASE_SHA")
    if ref and set(ref) != {"0"}:
        git("rev-parse", "--verify", ref + "^{commit}")
        return ref
    for candidate in ("origin/main", "main", "HEAD^"):
        try:
            git("rev-parse", "--verify", candidate + "^{commit}")
            return candidate
        except subprocess.CalledProcessError:
            continue
    raise SystemExit("Cannot determine base commit; fetch origin/main or set TOKEN_LIMIT_BASE_SHA.")

def exempt(name):
    """Technical exclusions only: lockfiles and generated artifacts, not source exemptions."""
    p = Path(name)
    return (
        p.name in {"uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock", "poetry.lock"}
        or p.suffix in {".lock", ".min.js", ".map"}
        or any(part in {"node_modules", "dist", "build", "__pycache__", ".venv", "vendor", "generated"} for part in p.parts)
    )

def main():
    ref = base()
    changed = paths(git("diff", "--name-only", "-z", "--diff-filter=ACMR", ref, "HEAD"))
    # Local checks include staged changes as well as committed branch changes.
    if not os.environ.get("CI"):
        changed |= paths(git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"))
    failed = []
    for name in sorted(changed):
        if exempt(name):
            continue
        p = Path(name)
        try:
            raw = p.read_bytes()
            if b"\0" in raw:
                continue
            raw.decode("utf-8")
        except (OSError, UnicodeError):
            continue
        if len(raw) > LIMIT:
            failed.append((name, len(raw)))
    for name, size in failed:
        print(f"\nBLOCKED: {name}: {size:,} bytes (~{size / 4:,.0f} estimated tokens); maximum 20,000 bytes (~5,000 tokens).")
        print("WHY: Files with clear responsibilities and semantic names are easier for agents and people to discover, read, test and change.")
        print("ACTION FOR AGENTS: Refactor the changed file into cohesive, discoverable units.")
        print("Name each file semantically so its contents can be found from the filename alone.")
        print("For documentation, split by subject and add links from the parent index.")
        print("GOOD: processo_autenticacao.py, processo_documentos.py; BAD: utils2.py, parte3.py.")
        print("Update imports, references, navigation and tests; maintain functionality and context.")
        print("Do not minify, discard context, create numbered fragments or bypass the check.")
        print("Existing oversized files are ignored UNTIL CHANGED; once changed, they must meet this limit.")
    print(f"File size check: {len(changed)} changed paths; {len(failed)} over limit; unchanged legacy files not checked.")
    return int(bool(failed))

if __name__ == "__main__":
    sys.exit(main())
