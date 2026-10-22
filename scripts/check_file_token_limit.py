#!/usr/bin/env python3
"""Ratchet: existing oversized files are grandfathered until they change."""
import json
import os
import subprocess
import sys
from pathlib import Path

import tiktoken

LIMIT = 5000
POLICY = ".token-limit-exceptions.json"


def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL)


def base_ref():
    explicit = os.environ.get("TOKEN_LIMIT_BASE_SHA")
    if explicit:
        git("rev-parse", "--verify", explicit + "^{commit}")
        return explicit
    for candidate in ("origin/main", "main", "HEAD^"):
        try:
            git("rev-parse", "--verify", candidate + "^{commit}")
            return candidate
        except subprocess.CalledProcessError:
            pass
    raise RuntimeError("No comparison base: fetch origin/main or set TOKEN_LIMIT_BASE_SHA")


def main():
    policy = json.loads(Path(POLICY).read_text(encoding="utf-8"))
    allow = policy.get("exceptions")
    if set(policy) != {"exceptions"} or not isinstance(allow, list) or any(
        not isinstance(x, str) or not x or x.startswith("/") or ".." in x.split("/")
        or any(c in x for c in "*?[]") for x in allow
    ) or len(allow) != len(set(allow)):
        raise ValueError("Exceptions must be distinct exact relative paths, without globs")
    base = base_ref()
    # Compare the *entire* change set against the target branch; do not recheck
    # untouched legacy files, regardless of their preexisting token counts.
    changed = git("diff", "--name-only", "-z", "--diff-filter=ACMR", base, "HEAD")
    paths = {p.decode("utf-8", "surrogateescape") for p in changed.split(b"\0") if p}
    # Local staged/worktree edits are checked too, without making existing
    # untouched violations suddenly fail.
    if not os.environ.get("CI"):
        for args in (("diff", "--name-only", "-z", "--cached"), ("diff", "--name-only", "-z")):
            paths |= {p.decode("utf-8", "surrogateescape") for p in git(*args).split(b"\0") if p}
    encoding = tiktoken.get_encoding("cl100k_base")
    failed = []
    for name in sorted(paths - set(allow)):
        try:
            raw = Path(name).read_bytes()
            if b"\0" in raw:
                continue
            content = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        n = len(encoding.encode(content, disallowed_special=()))
        if n > LIMIT:
            failed.append((name, n))
    for name, n in failed:
        print(f"FAIL {name}: {n} tokens > {LIMIT}; changed/new file must comply")
    print(f"Token ratchet: {len(paths)} changed files, {len(failed)} violations; legacy untouched files grandfathered")
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
