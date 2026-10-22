#!/usr/bin/env python3
"""Check token sizes of every tracked UTF-8 text file (cl100k_base)."""
import json
import subprocess
import sys
from pathlib import Path

import tiktoken

LIMIT = 5000
POLICY = ".token-limit-exceptions.json"


def main() -> int:
    exceptions = json.loads(Path(POLICY).read_text(encoding="utf-8"))
    if not isinstance(exceptions, dict) or set(exceptions) != {"exceptions"}:
        raise ValueError("Policy must be an object with exactly an 'exceptions' list")
    allow = exceptions["exceptions"]
    if not isinstance(allow, list) or any(not isinstance(x, str) or not x or any(c in x for c in "*?[]") for x in allow) or len(allow) != len(set(allow)):
        raise ValueError("Exceptions must be unique, exact repository-relative paths (no globs)")
    paths = subprocess.check_output(["git", "ls-files", "-z"]).split(b"\0")
    tracked = {p.decode("utf-8", "surrogateescape") for p in paths if p}
    unknown = set(allow) - tracked
    if unknown:
        print("Stale/invalid exceptions:", ", ".join(sorted(unknown)), file=sys.stderr)
        return 1
    encoding = tiktoken.get_encoding("cl100k_base")
    failures = []
    for path in sorted(tracked):
        if path in allow:
            continue
        try:
            content = Path(path).read_bytes()
        except (FileNotFoundError, IsADirectoryError):
            continue
        if b"\0" in content:
            continue
        try:
            data = content.decode("utf-8")
        except UnicodeDecodeError:
            continue
        count = len(encoding.encode(data, disallowed_special=()))
        if count > LIMIT:
            failures.append((path, count))
    for path, count in failures:
        print(f"FAIL {path}: {count} tokens (limit {LIMIT})")
    print(f"Checked {len(tracked)} tracked paths; {len(failures)} over limit; {len(allow)} explicitly exempted")
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
