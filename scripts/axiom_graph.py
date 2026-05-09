#!/usr/bin/env python3
"""
axiom_graph.py — Parse `#print axioms` output from Lean 4 and emit
Mermaid dependency diagrams (graph TD, sankey-beta, ishikawa-beta).

Usage:
    python3 scripts/axiom_graph.py --input axiom_audit.txt --out docs/axiom_graph.md

Input format (from `lean file.lean` with `#print axioms foo`):
    'foo' depends on axioms: [axiom1, axiom2, ...]
    'foo' does not depend on any axioms

Axiom classification:
  - STEEL_*                     → steelman premises (implicit claims of the acórdão)
  - propext / Classical.* / ... → Lean built-ins (skipped by default)
  - everything else             → legal axioms (norms, precedents, factual claims)

Legal axiom sub-classification (for Ishikawa bones):
  - ParteA_* / caso_* / recurso_* / fatos_* → factual claims
  - sumula_* / art_* / juris_* / interpretacao_* / RE_* / Rcl_* / ARE_* / PRECEDENTE_*
    → norms & precedents
  - everything else → other
"""
import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path

LEAN_BUILTINS = frozenset({
    'propext', 'Classical.choice', 'Quot.sound', 'funext',
    'Classical.em', 'Classical.propDecidable',
})

FACTUAL_PREFIXES = ('ParteA_', 'caso_', 'recurso_', 'fatos_', 'h_', 'axiom_caso')
NORM_PREFIXES = ('sumula_', 'art_', 'juris_', 'interpretacao_', 'tema_',
                 'RE_', 'Rcl_', 'ARE_', 'PRECEDENTE_', 'STJ_', 'STF_')

THEOREM_RE = re.compile(
    r"'?(\w[\w.]*)'?\s+(?:depends on axioms:|uses axioms:)\s*\[([^\]]*)\]",
    re.DOTALL,
)
NO_AXIOMS_RE = re.compile(r"'?(\w[\w.]*)'?\s+does not depend on any axioms")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_audit(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for m in THEOREM_RE.finditer(text):
        axioms = [a.strip() for a in m.group(2).split(',') if a.strip()]
        result[m.group(1)] = axioms
    for m in NO_AXIOMS_RE.finditer(text):
        result.setdefault(m.group(1), [])
    return result


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify(name: str) -> str:
    if name in LEAN_BUILTINS:
        return 'builtin'
    if name.startswith('STEEL_'):
        return 'steel'
    return 'legal'


def subclassify(name: str) -> str:
    """Finer grain for Ishikawa bones."""
    if any(name.startswith(p) for p in FACTUAL_PREFIXES):
        return 'factual'
    if any(name.startswith(p) for p in NORM_PREFIXES):
        return 'norm'
    return 'other'


def sanitize(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)


# ---------------------------------------------------------------------------
# Diagram 1 — graph TD (dependency graph)
# ---------------------------------------------------------------------------

def to_graph_td(deps: dict[str, list[str]], skip_builtins: bool = True) -> str:
    lines = ['```mermaid', 'graph TD',
             '  classDef steel fill:#ffcccc,stroke:#cc0000,color:#000',
             '  classDef legal fill:#cce5ff,stroke:#0066cc,color:#000',
             '  classDef theorem fill:#d4edda,stroke:#28a745,color:#000',
             '  classDef builtin fill:#eee,stroke:#999,color:#666']

    all_theorems = set(deps.keys())
    seen: set[str] = set()

    def node(name: str) -> str:
        sid = sanitize(name)
        if sid not in seen:
            seen.add(sid)
            cls = 'theorem' if name in all_theorems else classify(name)
            lines.append(f'  {sid}["{name}"]:::{cls}')
        return sid

    for theorem, axioms in sorted(deps.items()):
        t = node(theorem)
        for ax in axioms:
            if skip_builtins and classify(ax) == 'builtin':
                continue
            lines.append(f'  {t} --> {node(ax)}')

    lines.append('```')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Diagram 2 — sankey-beta (load-bearing axioms)
# ---------------------------------------------------------------------------

def to_sankey(deps: dict[str, list[str]], skip_builtins: bool = True) -> str:
    """
    Sankey: theorem → axiom, value=1 per dependency.
    Axioms used by multiple theorems appear with wider flows — visually
    identifying load-bearing premises (forensic priority targets).
    """
    lines = ['```mermaid', 'sankey-beta']
    for theorem, axioms in sorted(deps.items()):
        for ax in axioms:
            if skip_builtins and classify(ax) == 'builtin':
                continue
            # Sankey format: source,target,value  (commas must be escaped in labels)
            t_label = theorem.replace(',', ';')
            a_label = ax.replace(',', ';')
            lines.append(f'{t_label},{a_label},1')
    lines.append('```')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Diagram 3 — ishikawa-beta (cause-and-effect of the acórdão)
# ---------------------------------------------------------------------------

def to_ishikawa(deps: dict[str, list[str]],
                effect: str = 'Conclusão do acórdão',
                skip_builtins: bool = True) -> str:
    """
    Fishbone / Ishikawa: effect = acórdão conclusion; causes = axiom categories.

    Bones (top-level causes):
      - Premissas implícitas (STEEL)   ← the vulnerabilities
      - Normas e precedentes           ← load-bearing legal authority
      - Claims fáticos                 ← factual anchors
      - Outros axiomas legais

    Sub-bones = the individual axioms, grouped under each theorem that uses them.
    """
    # Collect axioms by category, preserving which theorem uses each
    steel: dict[str, list[str]] = defaultdict(list)    # axiom → theorems
    norms: dict[str, list[str]] = defaultdict(list)
    factual: dict[str, list[str]] = defaultdict(list)
    other: dict[str, list[str]] = defaultdict(list)

    for theorem, axioms in deps.items():
        for ax in axioms:
            if skip_builtins and classify(ax) == 'builtin':
                continue
            cls = classify(ax)
            if cls == 'steel':
                steel[ax].append(theorem)
            elif cls == 'legal':
                sub = subclassify(ax)
                if sub == 'norm':
                    norms[ax].append(theorem)
                elif sub == 'factual':
                    factual[ax].append(theorem)
                else:
                    other[ax].append(theorem)

    lines = ['```mermaid', 'ishikawa-beta', f'  {effect}']

    def bone(title: str, items: dict[str, list[str]]) -> None:
        if not items:
            return
        lines.append(f'  {title}')
        for ax, theorems in sorted(items.items()):
            # Sub-bone: axiom name; indent deeper if used by multiple theorems
            lines.append(f'    {ax}')
            if len(theorems) > 1:
                for t in sorted(theorems):
                    lines.append(f'      usado em: {t}')

    bone('Premissas implícitas (STEEL)', steel)
    bone('Normas e precedentes', norms)
    bone('Claims fáticos', factual)
    bone('Outros axiomas legais', other)

    lines.append('```')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Combined Markdown output
# ---------------------------------------------------------------------------

def to_markdown(deps: dict[str, list[str]],
                skip_builtins: bool = True,
                effect: str = 'Conclusão do acórdão') -> str:
    parts = [
        '# Axiom Dependency Analysis',
        '',
        '## Dependency graph',
        '',
        'Green = theorems (peça claims) · Blue = legal axioms · Red = STEEL premises',
        '',
        to_graph_td(deps, skip_builtins),
        '',
        '## Sankey — load-bearing axioms',
        '',
        'Flow width ∝ number of theorems that depend on each axiom.',
        'Wide flows = load-bearing premises. Narrow flows = ornamental support.',
        '',
        to_sankey(deps, skip_builtins),
        '',
        '## Ishikawa — cause-and-effect of the acórdão',
        '',
        'The effect is the acórdão\'s conclusion. Each bone is a category of',
        'premises that cause it. STEEL bones are the argument\'s vulnerabilities.',
        '',
        to_ishikawa(deps, effect, skip_builtins),
        '',
        '## Per-theorem breakdown',
        '',
    ]

    for theorem, axioms in sorted(deps.items()):
        legal = [a for a in axioms if classify(a) == 'legal']
        steel = [a for a in axioms if classify(a) == 'steel']

        parts.append(f'### `{theorem}`')
        if steel:
            parts.append(f'**⚠️ Steelman premises ({len(steel)}):** '
                         + ', '.join(f'`{a}`' for a in steel))
        if legal:
            parts.append(f'**Legal axioms ({len(legal)}):** '
                         + ', '.join(f'`{a}`' for a in legal))
        if not axioms:
            parts.append('*No axiom dependencies.*')
        parts.append('')

    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True,
                        help='axiom_audit.txt (or - for stdin)')
    parser.add_argument('--out', default='docs/axiom_graph.md')
    parser.add_argument('--effect', default='Conclusão do acórdão',
                        help='Label for the Ishikawa effect (head of the fishbone)')
    parser.add_argument('--include-builtins', action='store_true')
    args = parser.parse_args()

    text = sys.stdin.read() if args.input == '-' else Path(args.input).read_text()
    deps = parse_audit(text)
    if not deps:
        print('WARNING: no #print axioms output found.', file=sys.stderr)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(deps,
                               skip_builtins=not args.include_builtins,
                               effect=args.effect))
    print(f'Written: {out} ({len(deps)} theorems, 3 diagram formats)')


if __name__ == '__main__':
    main()
