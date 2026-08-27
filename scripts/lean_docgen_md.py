#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///
"""
lean_docgen_md.py — Extract docstrings and declarations from Lean 4 files
and emit one Markdown file per module.

Usage:
    python3 scripts/lean_docgen_md.py \
        --src legal-argument-lean/references \
        --out docs/references
"""
import re
import sys
import argparse
from pathlib import Path

# Matches /-- ... -/ docstrings (possibly multi-line)
DOCSTRING_RE = re.compile(r'/--\s*(.*?)\s*-/', re.DOTALL)

# Matches the declaration that follows a docstring
DECL_RE = re.compile(
    r'^(axiom|theorem|def|lemma|abbrev)\s+(\S+)',
    re.MULTILINE,
)

# Matches module-level block comment /-  ... -/ (not docstring)
MODULE_COMMENT_RE = re.compile(r'^/-(?!-)\s*(.*?)\s*-/', re.DOTALL | re.MULTILINE)

# Matches namespace declaration
NAMESPACE_RE = re.compile(r'^namespace\s+(\S+)', re.MULTILINE)


def lean_type_after_decl(text: str, decl_start: int) -> str:
    """Extract declaration signature up to proof body / next declaration / comment."""
    segment = text[decl_start:].lstrip()
    first_nl = segment.find('\n')
    search_from = (first_nl + 1) if first_nl != -1 else len(segment)

    # In the continuation lines, stop at: proof body, docstring, block comment,
    # or any new top-level declaration at column 0.
    stop = re.search(
        r':= *by\b'
        r'|:=(?!\s*$)'
        r'|^/-'                                               # block or docstring comment
        r'|^(?:axiom|theorem|def|lemma|abbrev|end|namespace)\b',
        segment[search_from:],
        re.MULTILINE,
    )
    if stop:
        raw = segment[: search_from + stop.start()].strip()
    else:
        blank = re.search(r'\n\s*\n', segment[search_from:])
        raw = (segment[: search_from + blank.start()].strip()
               if blank else segment[:400].strip())
    raw = re.sub(r'\s+', ' ', raw)
    return raw[:300] + ('…' if len(raw) > 300 else '')


def parse_lean_file(path: Path) -> dict:
    text = path.read_text(encoding='utf-8')

    # Module namespace
    ns_match = NAMESPACE_RE.search(text)
    namespace = ns_match.group(1) if ns_match else path.stem

    # Module-level description: first /- ... -/ block comment
    mod_match = MODULE_COMMENT_RE.search(text)
    module_doc = mod_match.group(1).strip() if mod_match else ''

    # Collect (docstring, declaration_name, declaration_kind, type_snippet) tuples
    entries = []
    pos = 0
    while pos < len(text):
        ds_match = DOCSTRING_RE.search(text, pos)
        if not ds_match:
            break
        docstring = ds_match.group(1).strip()
        after = text[ds_match.end():]
        # Find the next declaration immediately after (skip whitespace/newlines)
        decl_match = re.match(r'\s*(axiom|theorem|def|lemma|abbrev)\s+(\S+)', after)
        if decl_match:
            kind = decl_match.group(1)
            name = decl_match.group(2).rstrip(':')
            type_sig = lean_type_after_decl(after, decl_match.start())
            entries.append({
                'kind': kind,
                'name': name,
                'doc': docstring,
                'type': type_sig,
            })
        pos = ds_match.end()

    return {
        'namespace': namespace,
        'module_doc': module_doc,
        'entries': entries,
        'source': path.name,
    }


def entry_to_md(e: dict) -> str:
    badge = {'axiom': '📌 axiom', 'theorem': '✅ theorem', 'def': '🔧 def',
             'lemma': '✅ lemma', 'abbrev': '🔧 abbrev'}.get(e['kind'], e['kind'])
    lines = [
        f"### `{e['name']}` <small>{badge}</small>",
        '',
        e['doc'],
        '',
        f"```lean",
        e['type'],
        '```',
        '',
    ]
    return '\n'.join(lines)


def module_to_md(parsed: dict) -> str:
    parts = [
        f"# {parsed['namespace']}",
        f"*Source: `{parsed['source']}`*",
        '',
    ]
    if parsed['module_doc']:
        parts += [parsed['module_doc'], '']

    if parsed['entries']:
        parts.append('## Declarations\n')
        for e in parsed['entries']:
            parts.append(entry_to_md(e))
    else:
        parts.append('*No documented declarations found.*\n')

    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--src', default='legal-argument-lean/references',
                        help='Directory with .lean files')
    parser.add_argument('--out', default='docs/references',
                        help='Output directory for .md files')
    args = parser.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    lean_files = sorted(src.rglob('*.lean'))
    if not lean_files:
        print(f'No .lean files found under {src}', file=sys.stderr)
        sys.exit(1)

    index_rows = []
    for lf in lean_files:
        parsed = parse_lean_file(lf)
        rel = lf.relative_to(src)
        md_path = out / rel.with_suffix('.md')
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(module_to_md(parsed), encoding='utf-8')
        n = len(parsed['entries'])
        print(f'  {md_path}  ({n} declarations)')
        index_rows.append((str(rel), parsed['namespace'], n,
                           str(md_path.relative_to(out.parent))))

    # Write index
    index_md = out / 'INDEX.md'
    rows = ['# Reference Library Index', '',
            '| File | Namespace | Declarations |',
            '|---|---|---|']
    for (rel, ns, n, md_rel) in index_rows:
        rows.append(f'| `{rel}` | `{ns}` | [{n}]({md_rel}) |')
    index_md.write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(f'\nIndex: {index_md}')


if __name__ == '__main__':
    main()
