#!/usr/bin/env python3
"""
axiom_graph.py — Parse `#print axioms` output from Lean 4 and emit
a Mermaid dependency graph showing which axioms underpin each theorem.

Usage:
    python3 scripts/axiom_graph.py --input axiom_audit.txt --out docs/axiom_graph.md

Input format (from `lean file.lean` with `#print axioms foo`):
    'foo' depends on axioms:
      [axiom1, axiom2, ...]
    -- or --
    foo uses axioms: [axiom1, axiom2, ...]
    -- or --
    'foo' does not depend on any axioms

The script groups axioms into:
  - STEEL_*         → steelman premises (red, the argument's implicit claims)
  - propext / Classical.* / Quot.sound  → Lean built-ins (grey, skip by default)
  - everything else → legal axioms (blue)
"""
import re
import sys
import argparse
from pathlib import Path
from collections import defaultdict

# Built-in Lean axioms that are uninteresting for legal audit
LEAN_BUILTINS = frozenset({
    'propext', 'Classical.choice', 'Quot.sound', 'funext',
    'Classical.em', 'Classical.propDecidable',
})

# Parse one block: theorem name + its axiom list
THEOREM_RE = re.compile(
    r"'?(\w[\w.]*)'?\s+(?:depends on axioms:|uses axioms:)\s*\[([^\]]*)\]",
    re.DOTALL,
)
NO_AXIOMS_RE = re.compile(
    r"'?(\w[\w.]*)'?\s+does not depend on any axioms"
)


def parse_audit(text: str) -> dict[str, list[str]]:
    """Return {theorem: [axiom, ...]} from audit text."""
    result: dict[str, list[str]] = {}

    for m in THEOREM_RE.finditer(text):
        theorem = m.group(1)
        raw_axioms = m.group(2)
        axioms = [a.strip() for a in raw_axioms.split(',') if a.strip()]
        result[theorem] = axioms

    for m in NO_AXIOMS_RE.finditer(text):
        result.setdefault(m.group(1), [])

    return result


def classify(name: str) -> str:
    if name in LEAN_BUILTINS:
        return 'builtin'
    if name.startswith('STEEL_'):
        return 'steel'
    return 'legal'


def sanitize(name: str) -> str:
    """Mermaid node IDs cannot have dots or special chars."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


def to_mermaid(deps: dict[str, list[str]], skip_builtins: bool = True) -> str:
    lines = ['```mermaid', 'graph TD']

    # Node style classes
    lines += [
        '  classDef steel fill:#ffcccc,stroke:#cc0000,color:#000',
        '  classDef legal fill:#cce5ff,stroke:#0066cc,color:#000',
        '  classDef theorem fill:#d4edda,stroke:#28a745,color:#000',
        '  classDef builtin fill:#eee,stroke:#999,color:#666',
    ]

    all_theorems = set(deps.keys())
    seen_nodes: set[str] = set()

    def node(name: str) -> str:
        sid = sanitize(name)
        if sid not in seen_nodes:
            seen_nodes.add(sid)
            label = name.replace('"', "'")
            cls = classify(name)
            if name in all_theorems:
                cls = 'theorem'
            lines.append(f'  {sid}["{label}"]:::{cls}')
        return sid

    for theorem, axioms in sorted(deps.items()):
        t_id = node(theorem)
        for ax in axioms:
            if skip_builtins and classify(ax) == 'builtin':
                continue
            a_id = node(ax)
            lines.append(f'  {t_id} --> {a_id}')

    lines.append('```')
    return '\n'.join(lines)


def to_markdown(deps: dict[str, list[str]], skip_builtins: bool = True) -> str:
    parts = [
        '# Axiom Dependency Graph',
        '',
        'Each theorem node (green) points to the axioms it depends on.',
        'Red nodes are **STEEL** premises — implicit claims the acórdão requires.',
        'Blue nodes are **legal axioms** — norms, precedents, factual claims.',
        '',
        to_mermaid(deps, skip_builtins),
        '',
        '## Per-theorem breakdown',
        '',
    ]

    for theorem, axioms in sorted(deps.items()):
        legal = [a for a in axioms if classify(a) == 'legal']
        steel = [a for a in axioms if classify(a) == 'steel']
        builtin = [a for a in axioms if classify(a) == 'builtin']

        parts.append(f'### `{theorem}`')
        if steel:
            parts.append(f'**⚠️ Steelman premises ({len(steel)}):** '
                         + ', '.join(f'`{a}`' for a in steel))
        if legal:
            parts.append(f'**Legal axioms ({len(legal)}):** '
                         + ', '.join(f'`{a}`' for a in legal))
        if builtin and not skip_builtins:
            parts.append(f'*Lean built-ins:* ' + ', '.join(f'`{a}`' for a in builtin))
        if not axioms:
            parts.append('*No axiom dependencies.*')
        parts.append('')

    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True,
                        help='axiom_audit.txt from CI (or stdin with -)')
    parser.add_argument('--out', default='docs/axiom_graph.md',
                        help='Output Markdown file')
    parser.add_argument('--include-builtins', action='store_true',
                        help='Include propext / Classical.* in graph')
    args = parser.parse_args()

    if args.input == '-':
        text = sys.stdin.read()
    else:
        text = Path(args.input).read_text(encoding='utf-8')

    deps = parse_audit(text)
    if not deps:
        print('WARNING: no #print axioms output found in input.', file=sys.stderr)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    md = to_markdown(deps, skip_builtins=not args.include_builtins)
    out.write_text(md, encoding='utf-8')
    print(f'Written: {out} ({len(deps)} theorems)')


if __name__ == '__main__':
    main()
