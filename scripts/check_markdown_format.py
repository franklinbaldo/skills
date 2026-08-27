#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "mdformat>=1.0.0",
#     "mdformat-frontmatter>=2.1.2",
#     "mdformat-gfm>=1.0.0",
# ]
# ///
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
        return ""


def get_changed_files(base_ref=None):
    """Return Markdown files changed from a safe comparison base.

    In GitHub Actions PRs, use the remote base branch. On push, compare with
    the previous commit. Locally, prefer the merge-base with origin/main (or
    origin/master), then fall back to HEAD~1.
    """
    if base_ref:
        diff_base = base_ref
    elif os.environ.get("GITHUB_ACTIONS") == "true":
        pr_base = os.environ.get("GITHUB_BASE_REF")
        if pr_base:
            diff_base = f"origin/{pr_base}"
        else:
            before = os.environ.get("GITHUB_EVENT_BEFORE")
            diff_base = before if before and set(before) != {"0"} else "HEAD~1"
    else:
        diff_base = None
        for remote_ref in ("origin/main", "origin/master"):
            merge_base = run_command(f"git merge-base HEAD {remote_ref}")
            if merge_base:
                diff_base = merge_base
                break
        diff_base = diff_base or "HEAD~1"

    output = run_command(f"git diff --name-only --diff-filter=ACMRTUXB {diff_base}...HEAD")
    return [path for path in output.splitlines() if path.endswith(".md")]


def get_all_markdown_files():
    output = run_command("git ls-files '*.md'")
    return [path for path in output.splitlines() if path]


def should_skip(path):
    parts = path.replace("\\", "/").split("/")
    return any(part in EXCLUDE_DIRNAMES for part in parts)


def check_file(path, fix=False):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"Could not read {path}: {e}", file=sys.stderr)
        return False

    formatted = mdformat.text(text, options=OPTIONS, extensions=EXTENSIONS)
    if formatted == text:
        return True
    if fix:
        try:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(formatted)
            print(f"formatted: {path}")
            return True
        except OSError as e:
            print(f"Could not write {path}: {e}", file=sys.stderr)
            return False
    print(f"needs formatting: {path}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Check every tracked Markdown file")
    parser.add_argument("--fix", action="store_true", help="Rewrite files in place")
    parser.add_argument("--base", help="Explicit git comparison base")
    args = parser.parse_args()

    files = get_all_markdown_files() if args.all else get_changed_files(args.base)
    files = [path for path in files if not should_skip(path) and os.path.exists(path)]
    bad = [path for path in files if not check_file(path, fix=args.fix)]
    if bad and not args.fix:
        print(f"\n{len(bad)} Markdown file(s) need formatting.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
