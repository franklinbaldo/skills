---
name: legal-argument-lean
description: |
  Formalizes Brazilian legal arguments (peças forenses, especially Embargos
  de Declaração) in Lean 4, with reusable axiom libraries for CPC art. 489,
  927, 1022 et al. and a six-phase pipeline (Argdown → Lean → análise
  subjetiva → síntese de derrotas → forensic translation). The payoff is the
  `#print axioms` audit, exposing hierarchies the prose hides. Use when
  formalizing a Brazilian legal argument in Lean 4, auditing which premises
  (precedents, factual claims) an argument rests on, steelmanning an acórdão
  to expose implicit premises, or translating the analysis into a peça.
---

# legal-argument-lean

Formalize Brazilian legal arguments (peças forenses) in Lean 4. The
exercise is argumentative — its value lies in what survives translation,
what must be axiomatized, and what the dependency audit reveals.

## When to use this skill

Apply when the request involves formalizing a legal argument (peça
forense) in Lean 4, structural analysis of an acórdão to identify
procedural vícios, preparing Embargos de Declaração with formal audit
of arguments, or translating a formal exercise into a forensic peça.

Especially well-suited to:

- **Embargos de declaração** — reclamação metalógica por excelência, após
  distinguir ausência textual, rejeição implícita e omissão genuína;
  contradição interna pode ser modelada como `⊢ ⊥`
- **Aderência a precedente vinculante** — axiomas nomeados aplicados ao caso; violação = fora do espaço legítimo do art. 927
- **Aplicação seletiva de ratio decidendi** — ressalva ignorada = Warrant incompleto (formalizável via ADI + fato do caso)
- **Reductio** — assume a tese contrária + derive `False`

Do **not** use for: drafting the peça without a formalization goal;
pure normative interpretation without an argumentative target; mérito
puro centrado em qualificação jurídica (fica tudo predicado opaco);
proporcionalidade ou ponderação (não são lógica clássica).

## Why this exercise is valuable

The point is not to "prove" that a legal argument is correct — courts
are not theorem provers. The point is what the translation *forces you
to notice*:

1. **What survives translation** is the logical skeleton of the
   argument.
2. **What must be axiomatized** marks where the argument depends on
   authority (precedent, statute) rather than deduction.
3. **What refuses to translate** marks the zones of normative vagueness
   — usually the contested core of the controversy.
4. **`#print axioms`** lists every authority and every factual claim
   each theorem rests on. This is the formal counterpart of "ônus
   argumentativo" and reveals hierarchies the prose hides under
   coordinative conjunctions.

The fourth is the real prize: comparing axiom sets across alternative
proofs reveals which precedent is *load-bearing* and which is
rhetorical reinforcement.

## Safety, privacy, and legal-validation boundaries

Lean verifies derivability from the declared axioms; it does **not**
verify that a factual claim is true, that a quotation is accurate, that
a precedent remains controlling, or that the chosen formalization is
the legally best interpretation. A compiling theorem is therefore an
argument audit, never a legal-validity certificate.

Before relying on any output:

1. Verify statutes, súmulas, precedents, holdings, dates, and quotations
   against current official sources.
2. Distinguish verbatim authority from the formalizer's paraphrase.
3. Treat every case-specific axiom as an assertion requiring a record
   citation, not as an established fact.
4. Have a qualified human review the legal conclusions and the final
   peça.

Do not send sealed, confidential, privileged, or personally sensitive
case material to a second model or external service without the USER's
explicit authorization and an appropriate data-handling basis. Prefer
local processing, redaction, or synthetic placeholders. If independent
review would expose protected material, keep both analytical roles in
the same authorized environment and disclose that limitation.

## The six-layer architecture

Map every legal element to one of six layers. Use the comment headers
literally; they make the file readable as a parallel of the peça.

```
Camada 1 — Tipos básicos              (Caso, Vinculo, Precedente, ...)
Camada 2 — Predicados opacos          (qualificações jurídicas
                                       não-dedutivas)
Camada 3 — Normas                     (constitutivas do sistema; cite o
                                       dispositivo)
Camada 4 — Precedentes                (axiomas nomeados; cite no
                                       docstring)
Camada 5 — Claims fáticos             (extraídos do acórdão recorrido,
                                       não inventados)
Camada 6 — Teoremas                   (as teses da peça)
```

### Camada 1 — Tipos básicos

Universe of discourse: `Caso`, `Vinculo`, `Precedente`, `TipoNorma`,
etc. Declare with `axiom`, never `opaque` (the latter requires the type
to be inhabited and is the wrong tool here).

```lean
axiom Caso : Type
axiom Vinculo : Type
```

### Camada 2 — Predicados opacos

Juridical qualifications that are *decided*, not *computed*. The
canonical example: `IngressoNoServicoPublico : Vinculo → Prop`. Lean
will not reduce these; the only way to attribute them to a particular
case is via Camada 4 (precedent) or Camada 5 (factual claim). This is
philosophically honest: it isolates exactly where the law is
non-deductive.

```lean
axiom DependeReexameProbatorio : Caso → Prop
axiom FatosIncontroversos : Caso → Prop
```

### Camada 3 — Normas

Constitutional, statutory, and procedural norms. State as bidirectional
or implicational axioms. **Always cite the dispositivo in the
docstring.**

```lean
/-- Súmula 279/STF: "Para simples reexame de prova não cabe recurso
    extraordinário." -/
axiom sumula_279_definicao :
    ∀ (c : Caso), AplicaSumula279 c ↔ DependeReexameProbatorio c
```

### Camada 4 — Precedentes

Each cited precedent becomes one named axiom. The docstring carries the
full citation (number, relator, court, date if relevant) and the rule it
establishes. The "proof" of a precedent is, in the formal plane, the
court's own enunciation — there is no derivation.

```lean
/-- **RE 210.917**, Rel. Min. Sepúlveda Pertence, Tribunal Pleno.
    Distinção entre reexame de prova e qualificação jurídica de fatos
    incontroversos. -/
axiom RE_210_917 :
    ∀ (c : Caso),
      FatosIncontroversos c →
      ApenasQualificacaoJuridica c →
      ¬ DependeReexameProbatorio c
```

### Camada 5 — Claims fáticos

Factual assertions about the concrete case. **Anchor every claim in the
peça or in the recorrido.** Use the docstring to cite the source ("Voto
da 1ª TR-RO, fl. X") so each axiom is auditable. Do not fabricate
claims; if the peça does not assert it, the formalization should not
either.

```lean
axiom caso_concreto : Caso

/-- Voto da instância recorrida: descrição resumida dos fatos relevantes.
    Fatos incontroversos. -/
axiom fatos_incontroversos : FatosIncontroversos caso_concreto
```

### Camada 6 — Teoremas

The teses of the peça. Where multiple precedents support the same
conclusion, write multiple proofs (different vias). The audit step
will reveal which is most economical.

```lean
theorem sumula_279_inaplicavel : ¬ AplicaSumula279 caso_concreto := by
  rw [sumula_279_definicao]
  exact RE_210_917 caso_concreto
    fatos_incontroversos
    apenas_qualificacao
```

## Argdown for argument mapping

The pipeline uses [Argdown](https://argdown.org) as its single notation
for argument decomposition — the operational successor to Toulmin and
Dung, cited as lineage only. Argdown captures argument anatomy (claims,
premises, warrants) and attack topology (support/defeat) in one
Markdown-like file; the `<arg-P*> - [A*]` syntax makes attack topology
explicit without a separate Dung formalism.

## Two workflows

### Direct workflow

For simple cases with a single obvious vício and a clear argumentative target.

1. **Read the peça**: what is claimed, against what acórdão, with what
   section-level theses?
2. **Inventory the layers as you read** (entities → Camada 1; contested
   qualificações → Camada 2; norms → Camada 3; precedents → Camada 4;
   factual claims with citations → Camada 5; conclusions → Camada 6).
3. **Write the Lean file** with section headers mirroring the peça's
   own structure — readable as a parallel, not a recoding.
4. **Compile** with `lean file.lean`. Setup if needed (see below).
5. **End with `#print axioms`** for *every* theorem. Never skip.
6. **Report** the audit: which proof is most economical, which
   precedent is load-bearing, which factual claims are critical.

For an alleged omission, run the Phase 1 omission gate before writing a
theorem: express treatment → implicit rejection → decisiveness →
univocal determinability. Classify genuine omissions as recognitive,
generative, or direction-without-unicity; do not equate every missing
sentence with a missing derivation.

### Pipeline workflow

For complex cases with multiple competing arguments or multiple
omissões. Fase 0 is the raw-material input; Fases 1–5 are analytical:

```
Fase 0: Material original (acórdão + apelação)              ← input
Fase 1: Argdown — decomposição argumentativa unificada
        (anatomia + topologia de ataques)                   [pipeline/01_argdown.md]
Fase 2: Lean (LLM-formalizadora) — um teorema por ataque    [pipeline/02_briefing_lean.md]
Fase 3: Análise subjetiva ⇄ Fase 2 (ciclo iterativo)        [pipeline/03_analise_subjetiva.md]
Fase 4: Síntese de derrotas — marcar com ref. cruzada       [pipeline/04_sintese_derrotas.md]
Fase 5: Tradução forense (a peça)
```

Um exemplo completo do pipeline aplicado retroativamente a um caso
real está em `pipeline/exemplo_marilene/`.

## Five principles of the pipeline

**1 — Camada subjetiva.** Compilação Lean é necessária mas não
suficiente para marcar derrota; a Fase 4 avalia qualidade material dos
axiomas (ancoragem, contra-argumento enfrentado, formulação razoável).
Se algum critério falha, retorno à Fase 3 — nunca ajuste direto nos
axiomas.

**2 — Separação Argdown ↔ Síntese de derrotas.** Argdown (Fase 1) mapeia
ataques sem decidir vencedores; a Fase 4 marca derrotas com base em Lean
+ análise subjetiva. Misturar os dois = ritual de confirmação.

**3 — Prosa jurídica na análise.** A Fase 4 é escrita em registro de
parecer institucional, com qualificadores cautelosos — não em jargão de
workspace.

**4 — Regra dura sobre falha de compilação.** Teorema que não compila na
Fase 2 → voltar à Fase 1 e revisar. Nunca ajustar axiomas para forçar
compilação — isso contamina a Fase 3 e invalida o pipeline.

**5 — Revisão independente quando autorizada.** A LLM-formalizadora
(Fase 2) busca compilar; uma segunda revisão (Fase 3) avalia
honestamente, idealmente em contexto distinto para reduzir viés de
confirmação. Isso não autoriza enviar autos ou dados pessoais a outro
modelo, provedor ou serviço. Use outro contexto somente quando ele
estiver dentro do ambiente e da política de dados autorizados pelo USER;
caso contrário, faça a revisão no mesmo ambiente e registre a limitação.

## Lean 4 setup

First check whether Lean is already available:

```bash
lean --version
```

If it is unavailable, **do not install it automatically** and never pipe
a remote script directly into a shell. Ask the USER for permission,
then direct them to the official installation instructions:
<https://lean-lang.org/install/>.

After an authorized Elan installation, pin and install the expected
toolchain explicitly:

```bash
elan toolchain install leanprover/lean4:v4.14.0
elan default leanprover/lean4:v4.14.0
lean --version
```

For reproducible project-local selection, prefer a `lean-toolchain`
file containing:

```text
leanprover/lean4:v4.14.0
```

Before running any downloaded installer, identify its official release
source and verify any publisher signature or checksum the release
provides. `npx` and `uvx` are not substitutes for Elan: wrappers from
the npm or Python ecosystems merely add another supply-chain layer
around the same native toolchain download.

Mathlib is **not** needed — the logic is pure first-order with axioms;
a single `.lean` file compiled with `lean file.lean` is enough. Avoid
pulling in Mathlib unless a specific (rare) reason arises.

## Lean 4 idioms to use

### `variable` for modules with a fixed subject

When a module's axioms all quantify over the same types, declare them
once with `variable (d : Decisao) (p : Precedente)` after `open`; Lean
auto-inserts them wherever they appear free:

```lean
theorem aplica_implica_invoca :
    AplicaCorretamente d p → InvocaPrecedente d p := by
  intro h; exact h.1
-- equivalent to: ∀ (d : Decisao) (p : Precedente), ...
```

Use it in any Camada 3–6 file where one pair of types dominates; do
**not** use it for standalone peça files — explicitness is
documentation there.

### `@[simp]` on compound definitions

Mark compound `def`s (Camada 3) with `@[simp]` so `simp` can unfold
them automatically, keeping proof bodies short:

```lean
@[simp]
def AplicaCorretamente (d : Decisao) (p : Precedente) : Prop :=
    InvocaPrecedente d p ∧ IdentificaFundamentosDeterminantes d p ∧
    DemonstraAjusteAoCaso d p
-- then: simp [AplicaCorretamente] at h; exact h.1
```

All five Saidas compound definitions are tagged `@[simp]`.

### `sorry` in the adversarial draft phase

**Phase 1 — draft**: use the real `sorry` keyword where a step does not
follow; Lean compiles with warnings and `sorry`s are greppable.
**Phase 2 — steelman**: replace each `sorry` with the most charitable
axiom (`STEEL_n`); the file compiles cleanly and `#print axioms` lists
every STEEL axiom — each a candidate reconstruction, not automatically
an implicit premise actually adopted by the acórdão. Attach a
`ClaimMeta.SteelMeta` record with actor, textual basis, reconstruction
type, support status, and falsification condition. Never use
comment `-- sorry` as a substitute: invisible to the compiler, easy to
lose.

## Output rules

- **Lean 4 only.** Lean 3 syntax is obsolete and incompatible.
- **Always namespace** the file (`namespace EmbargosX.SecaoY`) so
  multiple sections of the same peça don't collide.
- **Comment in Portuguese** when the legal content is Portuguese; use
  docstrings (`/-- ... -/`) for citations.
- **Never fabricate precedents or claims.** Use only what the peça
  itself invokes; if something is missing, flag it to the USER.
- **Verify legal authority before reliance.** Confirm every material
  citation and proposition in a current official source; library
  docstrings and model memory are not authoritative sources.
- **Never present compilation as legal correctness.** Report separately
  what Lean established and what remains a factual, interpretive, or
  precedential assumption.
- **Never simplify the argument.** Preserve every step the peça takes;
  reducing fidelity defeats the audit.
- **Always end with `#print axioms`** for each theorem.
- **Deliver in an artifact** (```lean block or `.lean` file), matching
  the USER's preferences.

## What maps well, what maps badly

**Maps well:**
- Inadmissibilidade (Súmulas 279, 280, 282, 283, 284): clean syllogism
- Omissão em ED: a missing step only after excluding express treatment
  and plausible implicit rejection; distinguish recognitive from
  generative integration
- Contradição interna: literally `theorem ... : False`
- Aderência a precedente vinculante (RG, SV): named axiom + application
- Reductio: `intro h_contraria; ... ; exact absurd ... ...`
- Prequestionamento: enumeração de dispositivos como hypothesis list

**Maps badly — don't force:**
- Mérito centrado em qualificação jurídica vaga: the predicate stays
  opaque and the proof becomes trivial or impossible. Honestly: just
  formalize the *consistency* of both teses and stop.
- Defeasibility com hierarquia de exceções: classical logic does not
  natively model "regra geral + exceções jurisprudenciais". If
  unavoidable, model exceptions as antecedents in implicational axioms,
  but the prose handles this better.
- Proporcionalidade, ponderação, princípios: these are not deductive.
  Don't pretend they are.
- Convencimento racional do julgador: outside scope.

## The audit payoff — what to look for

After running `#print axioms`, examine:

- **Smallest axiom set** → forensically strongest position; the proof
  consuming fewest claims survives the most adversarial contestation.
- **Precedents present in some proofs but not others** → a precedent
  unique to one proof is doing real work; one shared across all proofs
  may be ornamental.
- **Load-bearing factual claims** → where the embargante must hold the
  line in the next instância.
- **`propext` appearing or not** → whether the proof used `↔` rewriting
  or only `→` modus ponens. Not legally meaningful.

Do not eyeball large audits by hand — the repo-root script
`scripts/axiom_graph.py` automates this. It parses `#print axioms`
output, classifies each axiom as STEEL_* (steelman premise), Lean
builtin (skipped unless `--include-builtins`), or legal — subdividing
legal into factual claims vs. norms/precedents by name prefix — and
emits three Mermaid views: theorem→axiom dependency graph, sankey
weight view, and Ishikawa cause diagram.

```bash
lean file.lean > axiom_audit.txt 2>&1
python3 scripts/axiom_graph.py --input axiom_audit.txt --out docs/axiom_graph.md
# optional labels: --effect ... --pretensao ... --conclusion <root theorem>
```

**This script lives at the repo root, one level above this skill's own
directory, so it only runs from a full checkout of the skills repo —
`skills.sh` does not bundle it into a standalone install.** If you only
have this skill installed (no `scripts/` next to it), skip the script
and read the `#print axioms` output directly using the classification
rules above.

Both `scripts/axiom_graph.py` and `scripts/lean_docgen_md.py` are wired
into CI (`.github/workflows/lean-compile.yml`), which compiles the
reference modules topologically, audits every `template_*.lean`, and
uploads the generated graph and docs as artifacts.

When reporting to the USER, lead with the strategic insight ("Prova 3 é
a mais robusta porque consome um único claim factual"), not with the
dump of axiom names.

## Reference axiom libraries

Reusable axiom libraries for high-frequency Brazilian procedural law.
They populate Camadas 1–4, ready to combine with the case-specific
Camadas 5–6. Treat published revisions as **reproducible**, not
immutable: never silently change the meaning of an axiom used by an
earlier artifact. Version, label, deprecate, and replace declarations
under `references/VERSIONING.md`. Peças still declare case-specific new
precedents as Camada 4 axioms in their own file.

### Modular architecture: traits de saída + módulos de regime

```
Tipos.lean                      (Decisao, Precedente, Caso, Tribunal, ...)
   ↓
Saidas/Aplicar.lean             (AplicaCorretamente, art. 489 §1º V)
Saidas/Distinguir.lean          (DistingueCorretamente, art. 489 §1º VI)
Saidas/Superar.lean             (SuperaPlenamente, ReconheceSuperacaoExterna)
   ↓
art_926_cpc.lean                (compõe traits, deriva partição própria)
art_927_cpc.lean                (compõe traits, deriva partição vinculante)
   ↓
acordao_*.lean (peças)          (importa o regime adequado ao caso)
```

The three legitimate saídas — aplicar, distinguir, superar — are
regime-independent **structural traits**; the regime modules (art. 926,
927) compose them into **derived partitions** (theorems, not axioms).
Key asymmetry: under art. 927 the bound court cannot fully overrule a
superior court's precedent (`apenas_tribunal_fonte_supera_plenamente`);
under art. 926 the court is the source of its own jurisprudence.

Modules import in topological order — to compile `art_927_cpc.lean`:

```bash
cd references/
LEAN_PATH=. lean -o Tipos.olean Tipos.lean
LEAN_PATH=. lean -o Saidas/Aplicar.olean Saidas/Aplicar.lean
LEAN_PATH=. lean -o Saidas/Distinguir.olean Saidas/Distinguir.lean
LEAN_PATH=. lean -o Saidas/Superar.olean Saidas/Superar.lean
LEAN_PATH=. lean -o art_927_cpc.olean art_927_cpc.lean
LEAN_PATH=. lean acordao_marilene.lean   # peça concreta
```

### Library modules in `references/`

- `Tipos.lean` — shared basic types (Decisao, Precedente, Caso, Tribunal)
- `ClaimMeta.lean` — provenance/status/location metadata for Camada 5
  axioms (mandatory in new complex-pipeline cases) plus epistemic metadata
  for `STEEL_n`
- `VERSIONING.md` — stability labels and compatibility policy for evolving
  legal axiom libraries
- `Saidas/Aplicar.lean` — `AplicaCorretamente` trait (art. 489, §1º, V)
- `Saidas/Distinguir.lean` — `DistingueCorretamente` trait (art. 489, §1º, VI)
- `Saidas/Superar.lean` — three superação modes + competence restriction
- `art_489_cpc.lean` — fundamentação: art. 489 caput and §1º, I–VI
- `art_1022_cpc.lean` — cabimento de ED: obscuridade, contradição, omissão, ordem pública
- `art_926_cpc.lean` — jurisprudência própria: three-way partition theorem
- `art_927_cpc.lean` — precedente vinculante: five-way partition + operational theorem
- `art_10_cpc.lean` — vedação à decisão surpresa (contraditório substancial)
- `art_5_e_6_cpc.lean` — boa-fé objetiva e cooperação (figuras parcelares objetivas)
- `tema_1306_stj.lean` — Tema 1306/STJ, fundamentação per relationem

Example and template files (`template_*.lean`, `exemplo_*.lean`,
`sec1III_*.lean`, `vedacao_motivos_genericos.lean`) are inventoried
under "Example files" below.

For full per-module documentation, generate it from the Lean docstrings
with the repo-root script — `python3 scripts/lean_docgen_md.py --src
legal-argument-lean/references --out docs/references` (only available
from a full repo checkout, same caveat as `axiom_graph.py` above) — or
read the `/-- ... -/` docstrings in the `.lean` files directly.

Use the art. 489 modules as the repository's default modeling hooks for
an alleged ausência de fundamentação; consider `art_927_cpc`'s
`fora_do_espaco_legitimo_nao_fundamentada` for challenges to selective
precedent application; and consider `tema_1306_stj` for art. 489, §1º,
IV per relationem reasoning. These modules are reusable formalization
templates, not legal authorities. Inspect their axioms, verify their
legal premises against current official sources, and adapt or decline
them when the concrete case does not fit.

### Combining libraries in a peça

No `lake` project needed: use `import Tipos`, `import Saidas.Aplicar`,
etc. at the top of the peça file and compile with
`LEAN_PATH=path/to/references lean file.lean`. Naming is compatible
across modules (`Decisao`, `Precedente`, `Fundamentada` mean the same).
See `pipeline/exemplo_marilene/02_lean_fase2.lean` for the canonical
composition pattern.

## Example files (in order of complexity)

- `references/template_secao.lean` — single-section formalization, introductory (Súmula 279)
- `references/exemplo_composicao.lean` — composition of two libraries (art. 489 + Tema 1306)
- `references/template_adversarial.lean` — adversarial mode, single steelman per gap, ends in `acordao_internamente_inconsistente : False`
- `references/template_steelmanning.lean` — exhaustive steelmanning of one gap: four variants, four distinct refutation strategies
- `references/vedacao_motivos_genericos.lean` — trivialness check (§1º, III) on a generic case, reusable for any steelman
- `references/sec1III_check_quatro_v2s.lean` — §1º III check on all four variants of one steelman (STEEL_2)
- `references/sec1III_check_STEEL1_STEEL3.lean` — same check extended to the remaining steelmans (STEEL_1, STEEL_3)
- `references/template_filtro.lean` — filtro de trivialidade applied *before* formalization; only surviving readings get steelmanned
- `references/template_acordao.lean` — full acórdão analysis using the modular architecture (Tipos → Saidas → art. 927)
- `pipeline/exemplo_marilene/` — **retroactive pipeline example** on a complete real case (anonymized), from Argdown through defeat synthesis

## Adversarial mode — summary

The most powerful application: formalize the **acórdão under attack**,
not one's own argument, via steelman-by-sorry-replacement applied
**exhaustively** across every plausible reading of each gap. Trivially
descartable readings are filtered before formalization; the rest get
3–5 steelman variants each, refuted by one of five strategies.

For an adversarial analysis that actually alleges generic reasoning
under art. 489, §1º, III, include the trivialness check unless the USER
chooses a narrower scope. A steelman that would justify literally any
outcome is a strong warning that the premise is underconstrained. Report
that result as a formal and argumentative finding; do not state that it
automatically establishes a legal violation without validating the
applicable law and the concrete record.

**Read `references/adversarial.md` in full before any adversarial
formalization** — it has the full loop, the filtro, the variant
ladder, all five refutation strategies, and the trivialness-check
procedure worked through step by step.

## From workspace to forensic peça — summary

The Lean exercise is **workspace**, not **product**. The peça describes
the case, not the path to the conclusion: it opens with what the
acórdão did wrong, never with the analytical setup that led there. Any
term coined inside the Lean file stays in the Lean file — the peça
uses only vocabulary from processo civil manuals and ementas. The
discovery process (discarded readings, the steelmanning trail) stays
invisible; the peça reads as if the lawyer simply *saw* the vício.

**Read `references/forensic-translation.md` in full before writing the
peça** — it has the worked before/after example, the complete
workspace→forensic vocabulary table, and the per-paragraph translation
test.

## Out of scope (future work)

The skill models the **argumentative and decisional layer**: given a
decision, is it well-reasoned? Explicitly outside the current scope:
canonical process structure (`PeticaoInicial`, `Contestacao`, ... as
typed entities), procedural phases as a state machine, admissibility
conditions for appeals (legitimidade, tempestividade, preparo), and
petição inicial as a source of claims (the `ClaimMeta` types support
this but no petição/contestação modules exist yet). Extensions in these
directions are additive — they do not require changing existing modules.

## Convention notes specific to the USER

- Match the USER's legal-document conventions: `## H2` and below; no
  horizontal rules; no `# H1`.
- Skill output goes in artifacts only **after** the USER approves the
  plan/skeleton: present the layer inventory → await approval → write
  the Lean file.
- Do not deliver Word versions unless asked. Lean files are
  text-native; if a Word version is requested, convert via pandoc per
  the USER's standing instructions.
