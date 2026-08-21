#!/usr/bin/env python3
"""Check (or apply) mdformat formatting on the repo's .md files.

Ported from pge-iperon/judicial (scripts/check_markdown_format.py), which
adopted it so a downstream consumer of `npx skills add` wouldn't see a
SKILL.md diverge from this repo's blob on formatting alone. By default only
checks files that differ from the base ref; --all checks every tracked .md
file.

wrap="keep"/number=True/end_of_line="lf" match .mdformat.toml (the CLI
reads that automatically; the Python API used here does not, so options
are duplicated explicitly — keep the two in sync if either changes).
"""

import argparse
import os
import subprocess
import sys

import mdformat

OPTIONS = {"number": True, "wrap": "keep", "end_of_line": "lf"}
EXTENSIONS = {"frontmatter", "gfm", "tables"}
EXCLUDE_DIRNAMES = {".git", ".venv", "node_modules", "vendor"}


def run_command(cmd, cwd=None):
    try:
        res = subprocess.run(
            cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command '{cmd}': {e.stderr}", file=sys.stderr)
        return None


def get_changed_files(base_ref):
    check_ref = run_command(f"git rev-parse --verify {base_ref}")
    if not check_ref:
        print(f"Base ref {base_ref} not found. Falling back to HEAD~1...")
        base_ref = "HEAD~1"
        check_ref = run_command(f"git rev-parse --verify {base_ref}")
        if not check_ref:
            print("Cannot determine git diff. Returning empty list.")
            return []

    stdout = run_command(f"git diff --name-only {base_ref}")
    if not stdout:
        return []
    return [f.strip() for f in stdout.splitlines() if f.strip()]


def is_excluded(filepath):
    if not filepath.endswith(".md"):
        return True
    parts = filepath.replace("\\", "/").split("/")
    return any(p in EXCLUDE_DIRNAMES for p in parts)


def collect_all_files():
    files = []
    for root, dirs, filenames in os.walk("."):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRNAMES]
        for filename in filenames:
            if filename.endswith(".md"):
                files.append(os.path.join(root, filename))
    return files


def main():
    parser = argparse.ArgumentParser(description="Check/apply mdformat on repository .md files.")
    parser.add_argument("--all", action="store_true", help="Check every tracked .md file, not just changed ones.")
    parser.add_argument("--base", default="origin/main", help="Base ref to diff against for changed files.")
    parser.add_argument("--files", nargs="*", help="Specific files to check.")
    parser.add_argument("--fix", action="store_true", help="Apply formatting in place instead of just checking.")
    args = parser.parse_args()

    if args.files:
        files_to_check = args.files
    elif args.all:
        files_to_check = collect_all_files()
    else:
        base = args.base
        if os.getenv("GITHUB_ACTIONS") == "true":
            gh_base_ref = os.getenv("GITHUB_BASE_REF")
            base = f"origin/{gh_base_ref}" if gh_base_ref else "HEAD~1"
            print(f"Comparing against base: {base}")
        else:
            print(f"Comparing against base: {base}")
        changed = get_changed_files(base)
        files_to_check = [f for f in changed if not is_excluded(f)]

    files_to_check = [f for f in files_to_check if not is_excluded(f) and os.path.exists(f)]

    if not files_to_check:
        print("No markdown files to check.")
        return 0

    print(f"Checking {len(files_to_check)} file(s)...")
    unformatted = []
    for filepath in files_to_check:
        with open(filepath, encoding="utf-8") as fh:
            before = fh.read()
        after = mdformat.text(before, options=OPTIONS, extensions=EXTENSIONS)
        if before != after:
            unformatted.append(filepath)
            if args.fix:
                with open(filepath, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(after)

    if unformatted and not args.fix:
        print("\n❌ FILES NOT FORMATTED (run `python scripts/check_markdown_format.py --fix --files <path>` or `--all --fix`):\n")
        for f in unformatted:
            print(f"   - {f}")
        return 1

    if unformatted:
        print(f"\n✅ Reformatted {len(unformatted)} file(s).")
    else:
        print("\n✅ All checked files are already formatted!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
