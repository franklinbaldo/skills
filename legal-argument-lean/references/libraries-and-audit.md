# Libraries and audit guide

Read this reference when choosing reusable legal modules, compiling the library graph, or interpreting `#print axioms` output.

## Reference axiom libraries

Reusable libraries populate Camadas 1–4 and are combined with case-specific Camadas 5–6. Published revisions are reproducible, not immutable: do not silently change the meaning of an axiom used by an earlier artifact. Follow `VERSIONING.md` to version, label, deprecate, and replace declarations.

### Modular architecture

```text
Tipos.lean
   ↓
Saidas/Aplicar.lean
Saidas/Distinguir.lean
Saidas/Superar.lean
   ↓
art_926_cpc.lean
art_927_cpc.lean
   ↓
acordao_*.lean
```

The three legitimate responses to a precedent — apply, distinguish, overcome — are modeled as regime-independent structural traits. Regime modules compose them into derived partitions. Under art. 927, a bound court cannot fully overrule the superior source court's precedent; under art. 926, the court is the source of its own jurisprudence.

Compile modules in topological order. Example:

```bash
cd references/
LEAN_PATH=. lean -o Tipos.olean Tipos.lean
LEAN_PATH=. lean -o Saidas/Aplicar.olean Saidas/Aplicar.lean
LEAN_PATH=. lean -o Saidas/Distinguir.olean Saidas/Distinguir.lean
LEAN_PATH=. lean -o Saidas/Superar.olean Saidas/Superar.lean
LEAN_PATH=. lean -o art_927_cpc.olean art_927_cpc.lean
```

## Main modules

- `Tipos.lean` — shared basic types.
- `ClaimMeta.lean` — provenance/status/location metadata for case-specific claims and steelman premises.
- `VERSIONING.md` — stability and compatibility policy.
- `Saidas/Aplicar.lean` — application trait, art. 489 §1º V.
- `Saidas/Distinguir.lean` — distinguishing trait, art. 489 §1º VI.
- `Saidas/Superar.lean` — modes of overruling plus competence restriction.
- `art_489_cpc.lean` — fundamentação under art. 489.
- `art_1022_cpc.lean` — embargos de declaração defects.
- `art_926_cpc.lean` — court's own jurisprudence regime.
- `art_927_cpc.lean` — binding-precedent regime.
- `art_10_cpc.lean` — decision-surprise / substantial adversarial process.
- `art_5_e_6_cpc.lean` — objective good faith and cooperation.
- `tema_1306_stj.lean` — Tema 1306/STJ, per-relationem reasoning.

These are formalization templates, not legal authorities. Inspect the axioms and verify the underlying legal proposition against current official sources before relying on them in a case.

Generate per-module documentation from Lean docstrings with the repo-root helper when working from a full checkout:

```bash
uv run scripts/lean_docgen_md.py \
  --src legal-argument-lean/references \
  --out docs/references
```

A standalone installation produced by `skills.sh` does not include repo-root scripts.

## Example files, increasing in complexity

- `template_secao.lean` — single-section introductory formalization.
- `exemplo_composicao.lean` — composition of reusable libraries.
- `template_adversarial.lean` — one steelman per gap and internal-consistency test.
- `template_steelmanning.lean` — multiple charitable reconstructions of one gap.
- `vedacao_motivos_genericos.lean` — reusable trivialness test under art. 489 §1º III.
- `sec1III_check_quatro_v2s.lean` and `sec1III_check_STEEL1_STEEL3.lean` — trivialness checks across steelman variants.
- `template_filtro.lean` — pre-formalization triviality filter.
- `template_acordao.lean` — full decision analysis with the modular architecture.
- `pipeline/exemplo_marilene/` — complete retroactive pipeline example from Argdown through defeat synthesis.

## Audit payoff

After compiling, inspect `#print axioms` for each material theorem.

Look for:

- the smallest dependency set: usually the most robust argumentative route;
- precedents unique to one proof: likely load-bearing rather than ornamental;
- factual claims consumed by multiple conclusions: these deserve the strongest record anchoring;
- `STEEL_*` dependencies: explicit charitable premises introduced during adversarial reconstruction;
- Lean builtins such as `propext`: technically relevant but not a legal finding.

Do not eyeball large audits when the full repo checkout is available. Use:

```bash
lean file.lean > axiom_audit.txt 2>&1
uv run scripts/axiom_graph.py \
  --input axiom_audit.txt \
  --out docs/axiom_graph.md
```

The helper classifies steelman premises, builtins, factual claims, norms, and precedents and can emit dependency, weight, and cause views. It lives at the repo root and is not bundled by `skills.sh`; on a standalone skill installation, inspect `#print axioms` directly.

When reporting to the user, lead with the strategic implication of the dependency structure rather than dumping axiom names.
