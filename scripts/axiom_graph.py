#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
# ]
# ///
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
# Diagram 2 — sankey-beta (argument death funnel)
# ---------------------------------------------------------------------------

def to_sankey(deps: dict[str, list[str]],
              pretensao: str = 'Pretensão do embargante',
              conclusion: str = 'Conclusão do acórdão',
              skip_builtins: bool = True) -> str:
    """
    Sankey showing WHERE each argument path dies in the reasoning chain.

    Flow direction (left → right):
        Pretensão → [via theorem/path] → STEEL axiom (death point) → Conclusão

    Interpretation:
    - Each theorem represents one attack path the acórdão takes.
    - STEEL axioms are the unjustified leaps — the death points of the
      embargante's argument. If a STEEL axiom is successfully challenged
      in the peça, the flow from that path never reaches the conclusion.
    - Theorems with NO STEEL axioms flow directly to the conclusion
      (argument has no vulnerability — hard to attack).
    - Theorems with MULTIPLE STEEL axioms require the embargante to break
      ALL of them to escape the conclusion via that path.

    Width at a STEEL node = number of paths that depend on it.
    A wide STEEL node is the most critical vulnerability to attack.
    """
    lines = ['```mermaid', 'sankey-beta']
    p = pretensao.replace(',', ';')
    c = conclusion.replace(',', ';')

    for theorem, axioms in sorted(deps.items()):
        steel_axioms = [ax for ax in axioms if classify(ax) == 'steel']
        t = theorem.replace(',', ';')

        if not steel_axioms:
            # No vulnerability: argument flows directly to conclusion
            lines.append(f'{p},{t},1')
            lines.append(f'{t},{c},1')
        else:
            # Argument passes through each STEEL bottleneck before reaching conclusion
            lines.append(f'{p},{t},1')
            for ax in steel_axioms:
                a = ax.replace(',', ';')
                lines.append(f'{t},{a},1')
                lines.append(f'{a},{c},1')

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
                effect: str = 'Conclusão do acórdão',
                pretensao: str = 'Pretensão do embargante',
                conclusion: str | None = None) -> str:
    _conclusion = conclusion or effect
    parts = [
        '# Axiom Dependency Analysis',
        '',
        '## Dependency graph',
        '',
        'Green = theorems (peça claims) · Blue = legal axioms · Red = STEEL premises',
        '',
        to_graph_td(deps, skip_builtins),
        '',
        '## Sankey — where the argument dies',
        '',
        f'**Pretensão:** {pretensao}  **Conclusão:** {_conclusion}',
        '',
        'Each path flows from the pretensão through a theorem (attack vector),',
        'then through its STEEL axioms (death points), and reaches the conclusion.',
        'A wide STEEL node means multiple paths depend on it — priority attack target.',
        'A path with no STEEL node flows directly to the conclusion (no vulnerability).',
        '',
        to_sankey(deps, pretensao, _conclusion, skip_builtins),
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
    parser.add_argument('--pretensao', default='Pretensão do embargante',
                        help='Label for the Sankey source node (embargante\'s claim)')
    parser.add_argument('--conclusion', default=None,
                        help='Label for the Sankey sink node (defaults to --effect)')
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
                               effect=args.effect,
                               pretensao=args.pretensao,
                               conclusion=args.conclusion))
    print(f'Written: {out} ({len(deps)} theorems, 3 diagram formats)')


if __name__ == '__main__':
    main()
