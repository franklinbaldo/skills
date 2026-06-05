# Ontology recipes — designing a span label space

How to design the label space for a span tagger, with worked examples. The examples are
**proposals to iterate on**, not gospel — the right set emerges from `preview`-rendering
real documents. They're framed as reusable patterns; the project names are illustrations.

## The design checklist (do this before annotating)

For each thing you want to extract, decide:

1. **Scheme** (Warning 2 in SKILL.md):
   - *Short span* — a compact target (a value, a reference, an outcome verb). Tag directly.
   - *Single-anchor* — a region that tiles the document. Tag the opening cue; region =
     open → next opening / EOD.
   - *Start/end pair* — a discrete, non-tiling region, or one with a reliable closer. Tag
     `_inicio` + `_fim` as two short categories; region = matched pair.
2. **Cues** — the exact opening (and, for pairs, closing) phrases. Be specific; vague cues
   are the main source of boundary noise.
3. **Scope rules** — where a category may legitimately appear (e.g. an operative outcome
   only inside the dispositivo / a mérito chapter), and the rule that prevents
   over-labeling (one operative instance, not every occurrence).
4. **Define vs. activate** — define every category now (definitions are durable), but only
   *activate* in the trained label space the ones above an example floor, unless you
   deliberately activate all and accept the interference risk (then report per-category
   F1+support and keep the active set a one-line reversible config). See SKILL.md
   "Ontology design".

Then: **start narrow.** Get one or two categories working before adding breadth — a model
that nails the two highest-value anchors is already useful. Keep a `category_version` and
archive run summaries so you can compare.

## Pattern A — operative-outcome extraction from decisions

Goal: locate the operative part and read the result (e.g. CausaGanha: outcome statistics).

```json
["O", "dispositivo_abertura", "resultado", "ref_processual", "valor_condenacao"]
```

- `dispositivo_abertura` (single-anchor) — opening cue of the operative part: `Ante o
  exposto`, `Diante do exposto`, `Isto posto`, `Posto isso`. **Exactly one operative
  instance** — not transition cues like "Decido", not intermediate rulings.
- `resultado` (short span, scoped) — the operative verb phrase: `julgo
  procedente/improcedente/parcialmente procedente`, `nego/dou provimento`, `extingo`,
  `condeno`. Keep short; map surface → outcome label downstream with a rule/lookup (fewer
  categories, clearer errors). Only inside the dispositivo or an explicit mérito-chapter
  scope — never on reasoning ("merece ser julgado procedente").
- `ref_processual` / `valor_condenacao` — short spans.

For multi-pedido decisions (partially granted), add `capitulo_merito_inicio/_fim` (pair)
and attribute each `resultado` to the chapter that contains it — that yields the full
outcome *vector*, not one floating line. For collegiate decisions add `voto_inicio/_fim`
(pair) per vote and `acordao_decisorio_inicio/_fim` for the collegiate result.

## Pattern B — structural tagging of hierarchical documents

Goal: segment a document into its formal structure (e.g. Leizilla: statutes).

```json
["O", "ementa", "artigo_marcador", "paragrafo_marcador", "inciso_marcador", "alinea_marcador", "vigencia", "revogacao"]
```

- Tag the **structural markers** (`Art. 5º`, `§ 2º`, `III -`, `a)`) as short anchors, not
  the whole clause — the clause body is the text between consecutive markers (reconstruct
  in post). This sidesteps the long-region problem entirely.
- `vigencia` / `revogacao` — short, cue-driven, high value (`entra em vigor…`,
  `revogam-se as disposições em contrário`).
- For a known formatting regime a regex baseline on the markers is strong; the model earns
  its keep on the messy cases (OCR, inconsistent numbering, a marker quoted inside text).

## Pattern C — field extraction from semi-structured documents

Goal: pull fields a structured feed doesn't already give you cleanly (e.g. Baliza:
editais / PNCP).

```json
["O", "objeto", "modalidade", "valor_estimado", "prazo", "orgao", "fundamento_legal", "dotacao_orcamentaria"]
```

- Mostly short, discrete fields — a clean token-classification fit; ETL-shaped (CPU batch,
  results joined back onto records).
- **Weak supervision for free:** where the structured feed already has a field
  (`valor_estimado`), it doubles as a bootstrap label and an audit signal.
- Consider *union* mode (annotation-format.md) if the documents also carry personal data
  to mask in the same pass.

## Sampling the corpus (stopgap when there's no consolidated dataset)

When you have per-source archives but no unified table yet, sample directly from the
per-source archives with the GHA matrix pattern in `colab-and-drive.md`: **equal allocation
across all sources** (floor + cap, not proportional — the tagger must see every format,
and the source closest at hand must not dominate), fixed seed, dedup boilerplate, and a
`sample_manifest.json` recording per-source counts + archive item ids. Include every
document *type* the ontology covers (e.g. both first-instance decisions and acórdãos, or
the acórdão-only categories starve). When consolidation lands, swap the matrix-over-archives
for a stratified query over the consolidated table — allocation, seed, and manifest
discipline stay identical, so the stopgap isn't throwaway.

## Cross-cutting

- **Start narrow**, add categories as data justifies (and as they cross the activation
  floor).
- **Regex where stable; model where fragile.** Don't spend the model on the category a
  rule nails — and don't let an easy, high-frequency category dominate the training spans
  and flatter macro-F1 (report metrics with it excluded).
- **Version everything** (`category_version`, manifest) so a checkpoint traces to the exact
  ontology + data that produced it.
