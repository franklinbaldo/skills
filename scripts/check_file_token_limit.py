#!/usr/bin/env python3
"""File size ratchet: 4 UTF-8 bytes ~ 1 token; no external dependencies."""
import json
import os
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 20_000
POLICY = ".token-limit-exceptions.json"

def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)

def paths_from(raw):
    return {p.decode("utf-8", "surrogateescape") for p in raw.split(b"\0") if p}

def base_ref():
    ref = os.environ.get("TOKEN_LIMIT_BASE_SHA")
    if ref:
        git("rev-parse", "--verify", ref + "^{commit}")
        return ref
    for candidate in ("origin/main", "main", "HEAD^"):
        try:
            git("rev-parse", "--verify", candidate + "^{commit}")
            return candidate
        except subprocess.CalledProcessError:
            continue
    raise RuntimeError("Fetch origin/main or provide TOKEN_LIMIT_BASE_SHA")

def text_size(data):
    if b"\0" in data:
        return None
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return len(data)

def main():
    policy = json.loads(Path(POLICY).read_text(encoding="utf-8"))
    allow = policy.get("exceptions")
    if set(policy) != {"exceptions"} or not isinstance(allow, list) or any(
        not isinstance(x, str) or not x or x.startswith("/") or ".." in x.split("/")
        or any(c in x for c in "*?[]") for x in allow
    ) or len(allow) != len(set(allow)):
        raise ValueError("Exceptions must be unique exact relative paths; no patterns")
    base = base_ref()
    changed = paths_from(git("diff", "--name-only", "-z", "--diff-filter=ACMR", base, "HEAD"))
    if not os.environ.get("CI"):
        for args in (("diff", "--name-only", "-z", "--cached"), ("diff", "--name-only", "-z")):
            changed |= paths_from(git(*args))
        changed |= paths_from(git("ls-files", "-z", "--others", "--exclude-standard"))
    failures = []
    for name in sorted(changed - set(allow)):
        try:
            current = text_size(Path(name).read_bytes())
        except OSError:
            continue
        if current is None or current <= MAX_BYTES:
            continue
        try:
            old = text_size(git("show", f"{base}:{name}"))
        except subprocess.CalledProcessError:
            old = None
        if old is None or old <= MAX_BYTES or current > old:
            failures.append((name, current, old))
    for name, current, old in failures:
        print(f"\nFILE SIZE RATCHET FAILED: {name}")
        print(f"  Current: {current:,} bytes (~{current / 4:,.0f} tokens). Target: <= {MAX_BYTES:,} bytes (~5,000 tokens).")
        if old is not None and old > MAX_BYTES:
            print(f"  Legacy baseline: {old:,} bytes. Existing oversized files must not grow.")
        else:
            print("  New or previously compliant files must stay under the limit.")
        print("  WHY: Smaller, focused files are easier for humans and AI agents to locate, read, review and edit.")
        print("  HOW TO FIX:")
        print("    1. Split by cohesive responsibilities, topics or public interfaces; preserve behavior and tests.")
        print("    2. Give each extracted file a descriptive, semantic name that reveals its content and purpose.")
        print("       Prefer e.g. processo_autenticacao.py, processo_documentos.py over utils2.py, part3.py.")
        print("    3. Update imports, references, navigation/indexes and tests. Keep related definitions together.")
        print("    4. Do not delete useful context, minify, rename vaguely, or game the metric.")
        print("    5. If splitting genuinely harms clarity, request an explicit HUMAN-approved exact-path exception")
        print(f"       in {POLICY}; an AI agent may propose but must never self-authorize an exception.")
    print(f"\nFile size ratchet: {len(changed)} changed/new paths; {len(failures)} failures; legacy unchanged oversized files exempt.")
    return int(bool(failures))

if __name__ == "__main__":
    sys.exit(main())
