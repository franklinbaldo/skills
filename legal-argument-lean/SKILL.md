---
name: legal-argument-lean
description: |
  Formalizes Brazilian legal arguments (peças forenses, especially Embargos
  de Declaração) in Lean 4. Models procedural vícios anchored in CPC
  dispositivos, with reusable axiom libraries for art. 489, 927, 1022 et al.
  Includes a six-phase pipeline for complex cases (Argdown → Lean →
  subjective legal analysis → defeat synthesis → forensic translation),
  with strict separation between identification of attacks and resolution of
  defeats to keep formalization honest. The payoff is not the
  proof itself but the `#print axioms` audit, which exposes hierarquia entre
  fundamentos jurídicos que a prosa coordena ("e", "ademais") esconde.
---

# legal-argument-lean

Formalize Brazilian legal arguments (peças forenses) in Lean 4. The
exercise is argumentative — its value lies in what survives translation,
what must be axiomatized, and what the dependency audit reveals about
the rhetorical structure of the original peça.

## When to use this skill

Apply when the request involves:

- formalizing a legal argument (peça forense) in Lean 4
- structural analysis of an acórdão to identify procedural vícios
- preparing Embargos de Declaração with formal audit of arguments
- translating a formal exercise into a Brazilian forensic peça

Especially well-suited to:

- **Embargos de declaração** — reclamação metalógica por excelência
  (omissão = falta de passo; contradição = `⊢ ⊥` literal)
- **Argumentos por aderência a precedente vinculante** (axiomas nomeados
  aplicados ao caso; violação = fora do espaço legítimo do art. 927)
- **Aplicação seletiva de ratio decidendi** (ressalva ignorada = vício
  de Warrant incompleto; formalizável via ADI + fato do caso)
- **Reductio** (assume a tese contrária + derive `False`)

Do **not** use for:

- Drafting the peça itself without a formalization goal
- Pure normative interpretation without an argumentative target
- Mérito puro centrado em qualificação jurídica (fica tudo predicado
  opaco; não há o que derivar)
- Proporcionalidade ou ponderação (não são lógica clássica)

## Why this exercise is valuable

The point is not to "prove" that a legal argument is correct — courts
are not theorem provers, and legal reasoning is not deductive in the
strict sense. The point is what the translation *forces you to notice*:

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

The fourth is the real prize. Comparing axiom sets across alternative
proofs reveals which precedent is *load-bearing* and which is rhetorical
reinforcement — strategic information not visible in the peça itself.

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

The pipeline uses [Argdown](https://argdown.org) as its single notation for
argument decomposition. Argdown is the operational successor to Toulmin (1958)
and Dung (1995) — those traditions are cited as intellectual lineage, not as
pipeline instruments. Argdown captures both argument anatomy (claims, premises,
warrants) and attack topology (support and defeat relations) in one Markdown-like
file with an official parser, VS Code plugin, and exporters to Mermaid/Graphviz.

For LLMs, Argdown is natural input: structured, unambiguous, indexed
documentation. The `<arg-P*> - [A*]` syntax makes attack topology explicit
without requiring a separate Dung formalism.

## Two workflows

### Direct workflow

For simple cases with a single obvious vício and a clear argumentative target.

1. **Read the peça.** Identify the argumentative structure: what is
   being claimed? Against what acórdão? What are the section-level
   theses?

2. **Inventory the layers as you read:**
   - What entities populate the universe? → Camada 1
   - Which qualificações jurídicas are contested or asserted? → Camada 2
   - Which constitutional/statutory/procedural norms? → Camada 3
   - Which precedents? → Camada 4
   - Which factual claims, with citations to the recorrido? → Camada 5
   - Which conclusions does the peça want? → Camada 6

3. **Write the Lean file** with section headers mirroring the peça's
   own structure. Readable as a parallel to the peça, not a recoding.

4. **Compile** with `lean file.lean`. Setup if needed (see below).

5. **End with `#print axioms`** for *every* theorem. Never skip.

6. **Report** the audit results: which proof is most economical, which
   precedent is load-bearing, which factual claims are critical.

### Pipeline workflow

For complex cases with multiple competing arguments or multiple
omissões. Six phases:

```
Fase 0: Material original (acórdão + apelação)
        ↓
Fase 1: Argdown — decomposição argumentativa unificada
        (anatomia dos argumentos + topologia de ataques)
        [pipeline/01_argdown.md]
        ↓
Fase 2: Lean (LLM-formalizadora) — um teorema por ataque
        [pipeline/02_briefing_lean.md]
        ↓
Fase 3: Análise subjetiva ⇄ Fase 2 (ciclo iterativo)
        [pipeline/03_analise_subjetiva.md]
        ↓
Fase 4: Síntese de derrotas — marcar derrotas com ref. cruzada
        [pipeline/04_sintese_derrotas.md]
        ↓
Fase 5: Tradução forense (a peça)
```

Um exemplo completo do pipeline aplicado retroativamente a um caso
real está em `pipeline/exemplo_marilene/`.

## Five principles of the pipeline

**Princípio 1 — Camada subjetiva.** Compilação Lean é condição
necessária mas não suficiente para marcar derrota. A Fase 4 avalia
qualidade material dos axiomas (ancoragem, contra-argumento
enfrentado, formulação razoável). Se algum critério falha, retorno
à Fase 3 para refinamento — nunca ajuste direto nos axiomas.

**Princípio 2 — Separação Argdown ↔ Síntese de derrotas.** Argdown
(Fase 1) mapeia ataques sem decidir vencedores. A Síntese de derrotas
(Fase 4) marca derrotas com base em Lean (Fase 2) + análise subjetiva
(Fase 3). Misturar os dois transforma a formalização em ritual de
confirmação.

**Princípio 3 — Prosa jurídica na análise.** A análise da Fase 4
é escrita em registro de parecer institucional, com qualificadores
cautelosos ("tem sólida ancoragem em...", "cabe ressalvar contudo
que..."). Não em jargão de workspace.

**Princípio 4 — Regra dura sobre falha de compilação.** Se um
teorema não compila na Fase 2, voltar à Fase 1 e revisar.
Nunca ajustar axiomas para forçar compilação — isso contamina a
Fase 3 e invalida o pipeline inteiro.

**Princípio 5 — Duas LLMs, contextos separados.** A LLM-formalizadora
(Fase 2) busca compilar teoremas relevantes; a LLM-analista (Fase 3)
avalia honestamente. Idealmente em contextos distintos para evitar
que a análise opere como justificativa do que a mesma LLM formalizou.

## Lean 4 setup

If `lean` is not on the path:

```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
  | sh -s -- -y --default-toolchain leanprover/lean4:v4.14.0
export PATH="$HOME/.elan/bin:$PATH"
lean --version
```

Mathlib is **not** needed for this kind of formalization — the logic is
pure first-order with axioms. A single `.lean` file compiled with `lean
file.lean` is enough. Avoid pulling in Mathlib unless a specific reason
arises (e.g., wanting to use lattice algebra for hierarchical norm
conflicts, which is rare).

## Lean 4 idioms to use

### `variable` for modules with a fixed subject

When a module's axioms all quantify over the same types, declare them
once with `variable` after `open`. Lean auto-inserts them wherever they
appear free — the API is unchanged, the source is shorter.

```lean
namespace Saidas.Aplicar
open Comum
variable (d : Decisao) (p : Precedente)

-- Lean adds (d : Decisao) (p : Precedente) automatically:
axiom InvocaPrecedente : Decisao → Precedente → Prop   -- unchanged (bound)

-- Here d and p appear free → auto-inserted:
theorem aplica_implica_invoca :
    AplicaCorretamente d p → InvocaPrecedente d p := by
  intro h; exact h.1
-- equivalent to: ∀ (d : Decisao) (p : Precedente), ...
```

Use `variable` in any Camada 3–6 file where one pair of types dominates.
Do **not** use it for standalone peça files — the explicitness is
documentation there.

### `@[simp]` on compound definitions

Mark compound `def`s (Camada 3) with `@[simp]` so the `simp` tactic
can unfold them automatically. This keeps proof bodies short when
multiple components need to be accessed in sequence:

```lean
@[simp]
def AplicaCorretamente (d : Decisao) (p : Precedente) : Prop :=
    InvocaPrecedente d p ∧
    IdentificaFundamentosDeterminantes d p ∧
    DemonstraAjusteAoCaso d p

-- Proof can then use simp to unfold and split:
theorem foo (h : AplicaCorretamente d p) : InvocaPrecedente d p := by
  simp [AplicaCorretamente] at h; exact h.1
```

All three Saidas compound definitions (`AplicaCorretamente`,
`DistingueCorretamente`, `SuperaPlenamente`, `ReconheceSuperacaoExterna`,
`SuperaRacionalmente`) are tagged `@[simp]` in the reference library.

### `sorry` in the adversarial draft phase

The adversarial workflow (steelmanning the acórdão) has two phases:

**Phase 1 — draft**: use the real `sorry` keyword where a step does not
follow. Lean compiles with warnings; `sorry`s are greppable.

```lean
theorem acordao_aplica_sumula_279 : Inadmissivel recurso_ParteA := by
  apply sumula_279
  · exact ParteA_eh_re
  · exact ParteA_recurso_do_caso
  · sorry  -- IMPLICIT PREMISE: why qualificação → reexame probatório?
```

**Phase 2 — steelman**: replace each `sorry` with the most charitable
axiom (`STEEL_n`). The file compiles cleanly. `#print axioms` lists every
STEEL axiom — each is an implicit premise of the acórdão.

Do **not** use comment `-- sorry` as a substitute for the real keyword.
The real `sorry` compiles, emits trackable warnings, and is greppable
(`grep -rn sorry`). Comment-based sorrys are invisible to the compiler
and easy to lose.

## Output rules

- **Lean 4 only.** Lean 3 syntax is obsolete and incompatible.
- **Always namespace** the file (`namespace EmbargosX.SecaoY`) so
  multiple sections of the same peça don't collide.
- **Comment in Portuguese** when the legal content is Portuguese.
  Docstrings (`/-- ... -/`) get rendered nicely by Lean's hover; use
  them for citations.
- **Never fabricate precedents or claims.** Use only what the peça
  itself invokes. If something is missing, flag it to the USER rather
  than inventing.
- **Never simplify the argument.** The point is to preserve every step
  the peça takes; reducing fidelity defeats the audit.
- **Always end with `#print axioms`** for each theorem.
- **Deliver in an artifact** (Lean code in a markdown ```lean block, or
  a `.lean` file). Match the USER's preferences for artifacts.

## What maps well, what maps badly

**Maps well:**
- Inadmissibilidade (Súmulas 279, 280, 282, 283, 284): clean syllogism
- Omissão em ED: literally "no derivation exists for X"
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

- **Smallest axiom set** → forensically strongest position. The proof
  consuming fewest claims is the one that survives the most adversarial
  factual contestation downstream.
- **Precedents present in some proofs but not others** → redundancy
  vs. essentiality. A precedent unique to one proof is doing real work;
  one shared across all proofs may be ornamental.
- **Factual claims that are load-bearing** → where the embargante must
  hold the line in the next instância.
- **`propext` appearing or not** → marker of whether the proof used `↔`
  rewriting or only `→` modus ponens. Not legally meaningful but worth
  noting.

When reporting to the USER, lead with the strategic insight (e.g.,
"Prova 3 é a mais robusta porque consome um único claim factual"), not
with the dump of axiom names.

## Example files

- `references/template_secao.lean` — single-section formalization,
  introductory (Súmula 279 inapplicability)
- `references/template_adversarial.lean` — adversarial mode,
  single-steelman per gap
- `references/template_steelmanning.lean` — exhaustive steelmanning
  of one gap, four variants, four refutation strategies
- `references/vedacao_motivos_genericos.lean` — the trivialness
  check (§1º, III) applied to a generic case
- `pipeline/exemplo_marilene/` — **retroactive pipeline example**
  on a complete real case (anonymized): five attacks against an
  acórdão invoking ADI 3.772, from Argdown through defeat synthesis

## Reference axiom libraries

The skill ships with reusable axiom libraries for high-frequency
Brazilian procedural law. These are not full peças — they populate
Camadas 1–3 (types, opaque predicates, norms) and Camada 4 (precedents),
ready to be combined with the case-specific Camada 5 (factual claims)
and Camada 6 (theorems) of any concrete formalization.

### Modular arquitecture: traits de saída + módulos de regime

A biblioteca da skill segue uma arquitetura em camadas modulares
para a vinculação a precedente:

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

**Princípio.** As três saídas legítimas diante de precedente
— aplicar, distinguir, superar — são modeladas como **traits
estruturais** independentes do regime. Os módulos de regime
(art. 926, art. 927) compõem os traits em **partições derivadas**
(teoremas, não axiomas), com qualificações dogmáticas próprias
de cada regime.

**Por que faz diferença.** A diferença mais importante está na
saída "superar". Sob art. 926 (jurisprudência do próprio tribunal),
a superação é plena (overruling robusto). Sob art. 927 (precedente
vinculante de tribunal superior), o tribunal vinculado NÃO pode
superar plenamente; só pode reconhecer superação superveniente do
próprio tribunal-fonte. Os módulos `Saidas/Superar.lean` e
`art_927_cpc.lean` modelam essa restrição de competência via
`apenas_tribunal_fonte_supera_plenamente`.

**Compilação.** Os módulos importam-se em ordem topológica.
Para compilar `art_927_cpc.lean`:

```bash
cd references/
LEAN_PATH=. lean -o Tipos.olean Tipos.lean
LEAN_PATH=. lean -o Saidas/Aplicar.olean Saidas/Aplicar.lean
LEAN_PATH=. lean -o Saidas/Distinguir.olean Saidas/Distinguir.lean
LEAN_PATH=. lean -o Saidas/Superar.olean Saidas/Superar.lean
LEAN_PATH=. lean -o art_927_cpc.olean art_927_cpc.lean
LEAN_PATH=. lean acordao_marilene.lean   # peça concreta
```

### Módulos individuais

- **`references/art_489_cpc.lean`** — `namespace CPC.Art489`. Covers
  art. 489 caput (validade ⇔ fundamentação) and art. 489, §1º, I-VI
  (the six hypotheses of non-fundamentação). Includes derived lemmas
  for the most frequent applications (omissão por inciso IV, invocação
  inadequada de precedente por inciso V).

- **`references/art_1022_cpc.lean`** — `namespace CPC.Art1022`. Covers
  cabimento de embargos de declaração com **definições rigorosas** de
  obscuridade, contradição e omissão:
    - **Obscuridade**: ambiguidade, incompreensibilidade, conclusão que
      não decorre dos fundamentos, expressão dúbia
    - **Contradição**: afirmação simultânea de proposição e sua negação;
      divergência entre fundamento e dispositivo
    - **Omissão**: dois ramos — (i) deduzida pela parte e capaz de
      infirmar; (ii) **matéria de ordem pública** (manifestação de ofício)
    - **Matérias de ordem pública** com axiomas explícitos: prescrição,
      decadência legal, coisa julgada, litispendência, perempção,
      pressupostos processuais, condições da ação, competência absoluta,
      conexão, continência, impedimento, nulidades absolutas, reserva
      de plenário (SV 10)
    - Pontes estruturais: parágrafo único, I (tese de repetitivo/IAC) e
      parágrafo único, II (qualquer conduta do art. 489, §1º) ↔
      caput do art. 1.022

- **`references/Tipos.lean`** — `namespace Comum`. Tipos básicos
  compartilhados (Decisao, Precedente, Caso, Tribunal, Servidor,
  Cargo). Importado por todos os módulos modulares. Mantido enxuto
  deliberadamente.

- **`references/Saidas/Aplicar.lean`** — `namespace Saidas.Aplicar`.
  Define `AplicaCorretamente d p` como conjunção de invocação,
  identificação de fundamentos determinantes e demonstração de
  ajuste do caso. Ancoragem dogmática: art. 489, §1º, V, do CPC.
  Independente de regime — vale para precedente próprio do tribunal
  (art. 926) e para precedente vinculante (art. 927).

- **`references/Saidas/Distinguir.lean`** — `namespace Saidas.Distinguir`.
  Define `DistingueCorretamente d p` com estrutura interna:
  identificação dos fundamentos do precedente + demonstração concreta
  de diferença substantiva no caso + declaração formal da distinção.
  Ancoragem: art. 489, §1º, VI, do CPC. Independente de regime.

- **`references/Saidas/Superar.lean`** — `namespace Saidas.Superar`.
  Modela TRÊS tipos de superação (refletindo o caráter racional
  da vinculação a precedente no direito brasileiro):
    - `SuperaPlenamente`: overruling robusto, disponível apenas
      para tribunal-fonte do precedente. Requer fundamentação
      adequada e específica + observância de segurança jurídica
      e proteção da confiança (art. 927, §4º).
    - `ReconheceSuperacaoExterna`: reconhecimento (declarativo)
      de superação superveniente do tribunal-fonte. Disponível
      a qualquer tribunal vinculado.
    - `SuperaRacionalmente`: superação constitutiva pelo tribunal
      vinculado, com ônus argumentativo qualificado — apontamento
      expresso de erro racional + demonstração de irracionalidade
      interna ou superação normativa + observância de segurança
      jurídica. Reflete a leitura do precedente brasileiro como
      vinculação racional (não meramente hierárquica): tribunal
      vinculado pode confrontar precedente superior, mas vence
      pela força do argumento, não pela autoridade.
  Inclui axioma `apenas_tribunal_fonte_supera_plenamente` que
  formaliza a restrição de competência (a saída plena é
  privativa, mas a saída racional permanece aberta).

- **`references/art_927_cpc.lean`** — `namespace CPC.Art927`. Importa
  os três módulos `Saidas.*` e modela os precedentes vinculantes:
    - I-V do caput como axiomas-construtores de `Vinculante`
    - §1º conectando o dever de observância às traits de saída
      (`art_927_par1_observancia` exige `AplicaCorretamente`;
      `art_927_par1_afastamento` exige `DistingueCorretamente` ou
      `SuperaPlenamente` ou `ReconheceSuperacaoExterna`)
    - §4º (alteração de tese — `art_927_par4`)
    - **TEOREMA CENTRAL**: `saidas_legitimas_precedente_vinculante` —
      derivação (não axioma) da partição: tribunal fundamentado que
      enfrenta precedente vinculante toma uma de cinco saídas
      (aplica, distingue, supera plenamente, reconhece superação
      superveniente, supera racionalmente).
    - **TEOREMA OPERACIONAL** (forma da peça): `fora_do_espaco_legitimo_nao_fundamentada`
      — contrapositiva: se nenhuma das cinco saídas, decisão não
      está fundamentada.
    - Lemas: `tema_rg_vinculante`, `tribunal_vinculado_nao_supera_plenamente`

- **`references/art_926_cpc.lean`** — `namespace CPC.Art926`. Importa
  os três módulos `Saidas.*` e modela:
    - **art_926_caput**: tribunais devem manter jurisprudência estável,
      íntegra e coerente
    - **violacao_coerencia_jurisprudencial**: teses incompatíveis em
      decisões distintas do mesmo tribunal sobre matéria análoga
      violam coerência da jurisprudência
    - **art_926_aplicacao_propria** e **art_926_afastamento_proprio**:
      tribunal que enfrenta sua própria jurisprudência está obrigado
      a aplicar corretamente OU distinguir/superar
    - **TEOREMA CENTRAL**: `saidas_legitimas_jurisprudencia_propria` —
      derivação da partição: aplicar, distinguir, OU superar
      plenamente. Só TRÊS saídas (não há `ReconheceSuperacaoExterna`),
      porque o tribunal é tribunal-fonte da própria jurisprudência.
    - **ATENÇÃO** — escopo. O artigo NÃO disciplina (a) precedente de
      tribunal superior — incidência do art. 927; (b) contradição
      intra-decisão — incidência do art. 1.022, I, c/c art. 489, §1º,
      V. Invocar o art. 926 nessas hipóteses expõe flanco argumentativo.

- **`references/art_10_cpc.lean`** — `namespace CPC.Art10`. Vedação à
  decisão surpresa (contraditório substancial). Núcleo:
    - `art_10_caput`: presença de fundamento + ausência de
      oportunidade efetiva = decisão surpresa
    - `art_10_clausula_oficio`: a vedação NÃO é afastada por se tratar
      de matéria de ordem pública (essência do contraditório
      substancial brasileiro)
    - `decisao_surpresa_nao_fundamentada`: ponte com art. 489
    - **Conexões expressas**: art. 927, §1º textualmente ordena
      observância ao art. 10 quando se decide com fundamento em
      precedente vinculante; art. 1.022, par. único, II equipara a
      omissão; art. 489, §1º, IV operacionaliza como não-enfrentamento

- **`references/art_5_e_6_cpc.lean`** — `namespace CPC.Art5e6`.
  Boa-fé objetiva e dever de cooperação, com **operacionalização da
  objetividade**:
    - **Distinção objetiva/subjetiva** explicitada no comentário:
      objetiva = padrão de conduta exteriormente verificável,
      independentemente de intenção
    - **Figuras parcelares como axiomas operativos**: cada uma é um
      padrão exterior aferido pela sequência observável de atos do
      sujeito — venire contra factum proprium, tu quoque, supressio,
      surrectio, adimplemento substancial, dever de cooperação
    - **Definições objetivas das figuras** (sem qualquer referência a
      estado mental): venire = conduta anterior + expectativa
      legítima + conduta posterior contrária; tu quoque = descumprir
      norma e invocá-la; etc.
    - **Estrutura dever vs. fato**: predicados separados
      `DevendoAgirBoaFe` (norma art. 5º) e `AgeBoaFeObjetiva`
      (descrição factual). Violação = dever existente + fato negativo.
    - **Conexões expressas**: venire institucional (do tribunal)
      complementa art. 926 (coerência); cooperação (art. 6º) é o
      contraditório substancial do art. 10 visto pelo lado dos
      sujeitos do processo.

- **`references/tema_1306_stj.lean`** — `namespace STJ.Tema1306`.
  Covers the **inteiro teor** of Tema 1306/STJ (REsp 2.148.059/MA et
  al., Rel. Min. Luis Felipe Salomão, Corte Especial, j. 20.08.2025),
  not just the two teses fixadas. Landmark case on fundamentação per
  relationem — when transcription of prior decision counts as proper
  reasoning and when it doesn't. Includes:
    - Tese 1 (forma bidirecional) and Tese 2
    - Distinção doutrinária pura vs. integrativa (the operative distinction
      for any peça challenging "decisão que apenas transcreve")
    - Apoio expresso em Tema 339/RG STF
    - Esclarecimento dos ED da FEBRABAN sobre o alcance de "novo"
    - Aplicação ao caso paradigma (transcrição ipsis litteris da
      sentença sem rebater elementos fáticos = nulidade)
    - Lemas derivados úteis em peças

- **`references/exemplo_composicao.lean`** — Demonstrates how to
  compose two libraries (art. 489 + Tema 1306) in a single peça. The
  same pattern applies to combining any subset of the libraries.

### When to use the libraries

- **Always** for ED/recursos arguing nulidade por ausência de
  fundamentação. The art. 489 axioms are the canonical hooks.
- **Always** for arguments about precedent vinculante. `art_927_cpc`
  provides `fora_do_espaco_legitimo_nao_fundamentada` — the operational
  theorem for peças challenging selective or incomplete application.
- **Always** for arguments about fundamentação per relationem. Tema 1306
  plugs into art. 489, §1º, IV with the distinção pura/integrativa
  giving operational sharpness to any challenge of copy-paste reasoning.
- For peças invoking other precedents, declare those as new axioms in
  Camada 4 of the peça file (do not modify the libraries themselves —
  treat them as immutable).

### Combining libraries in a peça

Lean 4 single-file compilation (no `lake` project setup) imports
across files via `import` + `LEAN_PATH`. Use `import Tipos`,
`import Saidas.Aplicar`, etc. at the top of the peça file and compile
with `LEAN_PATH=path/to/references lean file.lean`. Compatible naming
is preserved: `Decisao`, `Precedente`, `Fundamentada` mean the same
across all modules. See `pipeline/exemplo_marilene/02_lean_fase2.lean`
for the canonical composition pattern.

## Adversarial mode — formalizing the *embargado*, not the *embargante*

The most powerful application of this skill is **not** formalizing the
peça's own argument, but formalizing the **acórdão being challenged**.
The methodology is *steelmanning via sorry-replacement*, applied
**exhaustively** across all plausible interpretations of each gap.

### The basic loop

1. Translate the acórdão's argumentative chain into Lean, leaving
   `sorry` (or, equivalently, an unjustified gap) wherever a step does
   not follow deductively.
2. **Steelman**: replace each `sorry` with the *most charitable and
   strongest* axiom that would justify the move. Do not pick the
   weakest version — pick the most defensible one.
3. Compile until the acórdão's conclusion derives.
4. **Audit with `#print axioms`**: each axiom not corresponding to
   actually-cited authority is an implicit move. Each is a vício
   candidate.
5. **Consistency check**: try to derive `False` from the axiom set.
   If possible, the acórdão is *internally* inconsistent.

### Going further: exhaustive steelmanning

A single steelman is methodologically insufficient. The court could
reply: "but I meant a different interpretation of that step." The
proper response is to enumerate **all plausible steelmans in
ascending order of deference to the court** and refute each by its
own strategy. This is the case-analysis-exhaustivo technique applied
to legal argument.

### Pre-step: filtro de trivialidade

Before formalizing readings as steelmans, **filter out trivial
descartes**. A reading is trivially descartable if it conflicts with
sistemic presuppositions of the legal order:

- The very competence of the invoking court (e.g., "aplicação de
  norma constitucional = direito local" conflicts with art. 102 CF —
  it would deny the STF its constitutional jurisdiction)
- The existence of legal institutes (e.g., "RPPS estadual = direito
  local" conflicts with the existence of Tema 139/RG itself)
- The definition of central terms (e.g., "qualificação jurídica =
  reexame probatório" conflicts with the very definition of Súmula
  279, which presupposes the distinction)
- The definition of legal categories (e.g., "precedentes
  intercambiáveis sem aderência" conflicts with art. 489 §1º V's
  definition of precedent as carrying fundamentos determinantes)

The Lean analog is `[Field K]` or "we omit trivial cases": these are
not theses to be examined, they are *operating context*. Treat them
as `axiom` declarations in a "Pressupostos sistêmicos" preamble and
list the descartes in a comment block — never formalize them as
steelmans to be refuted.

The reason is partly methodological (don't waste effort) and partly
forensic (steelmanning a reading no rational actor would defend
*dignifies* the absurd by treating it as worthy of formal exam — and
implies, falsely, that the court might sustain it). In a peça, this
translates to a single dispatch sentence: *"descartadas, por óbvias,
leituras incompatíveis com a competência desta Suprema Corte..."*.
The reading is not refuted; it is *not even taken seriously*.

After the filter, only two kinds of readings survive:
- **Tautological readings** that pass §1º III check but require
  factual antecedents that may or may not hold for the case at bar
- **Genuine steelmans** that look defensible at first glance but
  reveal universalization on §1º III check

These get formal treatment.

### Going further: exhaustive steelmanning of the surviving readings

For each gap, write 3-5 steelmans:
- **V_n_a**: the rawest version the court must implicitly hold to
  reach the conclusion
- **V_n_b**: a more careful, almost-tautological reading
- **V_n_c**: an even more deferential reading (often a broad
  generalization)
- **V_n_d**: maximum charity — the most defensible reading of the
  court's actual move

For each variant, prove failure by one of:
- **Logical contradiction**: variant + cited axioms ⊢ False (use
  premises the court itself invokes)
- **Factual inertness**: variant is true but doesn't apply to the
  case at bar because the precondition fails for the facts
- **Reductio**: variant has consequences inconsistent with cited
  jurisprudence/legislation
- **Norm violation**: variant violates a procedural rule (typical:
  art. 489, §1º, V or VI)
- **Trivialness (§1º, III)**: variant is universalizable in the
  empty/vague sense — it would justify any decision when applied to
  paradigmatic counterexamples. See trivialness check below.

### MANDATORY trivialness check (§1º, III)

Before accepting any steelman as a "real" interpretation worth
refuting by other means, verify it does not violate art. 489, §1º,
III, do CPC: "não se considera fundamentada [...] decisão que
invocar motivos que se prestariam a justificar qualquer outra
decisão".

This is **not optional**. It is both a legal refutation strategy and
a sanity-check on the formalization itself. In Lean, it is precisely
the check that protects against axioms strong enough to "compile"
trivially — axioms whose form alone would prove not just the desired
conclusion but its opposite if instantiated on counterexample cases.

Procedure for every steelman of form `S(c) → P(c)`:

1. Identify a paradigmatic counterexample case `c*` — typically a
   case decided by the same court (often a precedent the acórdão
   itself cites!) where `P(c*)` is manifestly false.
2. Verify `S(c*)` holds (the antecedent applies to `c*`).
3. Apply the steelman: derive `P(c*)`, contradiction with the fact
   `¬ P(c*)`.
4. Conclude: the steelman violates art. 489, §1º, III. As "motivo",
   it would justify equally a decision the court did not (and would
   not) take.

A worked example is at `references/vedacao_motivos_genericos.lean`,
applying the check to a generic case. The §1º III refutation
is structurally more economical than the case-specific contradiction:
it depends only on three axioms about the counterexample case, none
about the case at bar. This is the formal-systems analog of "uma boa
fundamentação distingue casos".

When proposing a steelman, run through this check. If it fails, do
not waste effort on more elaborate refutation strategies — the §1º
III refutation is already the cleanest, and is what a careful peça
should lead with.

The terminal theorem is a disjunction: `(V_a ∨ V_c ∨ V_d) → False`,
plus a separate observation that V_b is inert (true but unhelpful).
This proves: no plausible reading of the acórdão's gap sustains the
conclusion. The court has no escape.

## From workspace to forensic peça

The Lean exercise is **workspace**, not **product**. It maps the
argumentative space; the peça delivers the conclusion. Translation
between the two is a real step — not a copy operation. The peça
should describe **the case**, not the reasoning that led to the
conclusion about the case.

This is invisible if you skip it. The peça compiles fine in the
sense that it states correct claims with correct citations. But the
voice betrays the workspace: the prose talks about "leituras dignas
de exame", "pressupostos sistêmicos", "universalização vazia",
"steelmans". The reader senses the machinery. Worse, dignifying
absurd readings as "leituras a refutar" implies, falsely, that the
court might sustain them — which insults the court and weakens the
attack.

### Translation rules

**Open with the processual verb, not the analytical setup.**
- Workspace voice: "cumpre examinar sob qual leitura defensável dessa
  premissa o enunciado se sustenta"
- Forensic voice: "o acórdão embargado aplicou a Súmula 280 sem
  indicar qual norma de direito local teria sido interpretada"

The first describes how the brief proceeds; the second describes
what the court did. Only the second is a peça opening.

**Vocabulary translation.** Workspace terms must not appear in the
peça. The forensic concepts they map to:

| Workspace (Lean / methodology) | Peça (forensic) |
|---|---|
| steelman, V_n_a/b/c | (subsumed in prose; leituras não são nomeadas) |
| universalização vazia | motivos genéricos do art. 489 §1º III; fundamento incapaz de distinguir o caso |
| leituras dignas de exame | (silently absent — só as leituras dignas aparecem) |
| pressupostos sistêmicos | competência constitucional desta Casa; existência do Tema X/RG |
| filtro de trivialidade | (silently absent — leituras triviais não aparecem) |
| §1º III check | argumento direto pelo art. 489 §1º III |
| caso de [Nome] | hipótese dos autos; caso concreto; decisão recorrida |
| compila / não compila | a tese sustenta-se / não se sustenta |
| ratio decidendi | (uso técnico OK, com parcimônia) |
| saída legítima, espaço de saídas | postura legítima; modo de uso do precedente |
| não-saída, fora do espaço legítimo | uso impróprio de precedente; aplicação seletiva |
| partição (das saídas) | (silently absent — a estrutura aparece como enumeração no corpo, sem nome) |
| trait, módulo de saída | (silently absent — categoria estrutural do Lean) |

**Cuidado com construções internas do Lean.** Termos inventados
*dentro* do exercício formal para descrever sua estrutura — partição,
trait, saída, espaço legítimo, não-saída — são workspace por
construção, ainda que pareçam neutros ou descritivos. Por familiaridade
ao longo do trabalho, esses termos tendem a migrar inadvertidamente
para a peça, onde causam estranhamento ao leitor versado (que reconhece
o vocabulário processual brasileiro reconhecido, e percebe ruído quando
algo escapa dele).

Regra operacional: **qualquer expressão criada dentro do Lean fica
dentro do Lean**. A peça usa apenas vocabulário que existe *fora* do
exercício formal — dispositivos legais nominados, doutrina reconhecida,
jurisprudência citada, fórmulas dogmáticas consagradas. O teste é
simples: se o termo não está em um manual de processo civil ou em
ementa de acórdão, não está pronto para a peça.

Exemplo concreto: o teorema `acordao_TJRO_fora_do_espaco_legitimo`
captura o vício de "uso impróprio de precedente vinculante por
aplicação seletiva de sua ratio". O nome do teorema serve à
arquitetura do Lean; a peça nomeia o vício pela fórmula dogmática.

**Show conclusions, not the discovery process.** If three readings
were examined and only one survived, the peça presents only the one
that survived (positively, as "a leitura correta é X") and the one
worth attacking (as "a leitura adotada pelo acórdão é defectiva").
Trivial leituras dispensa-se silentemente — não comparecem ao texto.

**Institutional, not professoral.** Avoid first-person plural
explanations of the argument's structure ("examinemos", "passemos",
"resta-nos"). Avoid phrases that frame the peça as an analysis
("quatro leituras se apresentam", "esgotadas as alternativas"). The
peça is a request, not a treatise.

**The forensic test.** Read each parágrafo and ask: *isto descreve o
caso ou descreve como cheguei à conclusão sobre o caso?* If it
describes the path, rewrite it to describe the conclusion. The Lean
file is where the path lives.

### What the workspace gets you (despite remaining hidden)

The strict separation does not waste workspace work:

- **Confidence.** You know the argument is correct because you
  formalized it. The peça's claims have been audited.
- **Robustness.** When the court replies "but I meant X", you have
  X formalized somewhere and refuted. The peça can address it
  briefly because the work is done.
- **Concision.** Knowing which leituras are trivial lets you skip
  them entirely instead of refuting weakly.
- **Anchor selection.** The §1º III audit identifies which
  precedents the court itself cannot deny — those become the
  citations in the peça.

The peça should read as if the lawyer simply *saw* the vício and
named it. The reader should never know how much work it took.

## Example files (in order of complexity)

- `references/template_secao.lean` — single-section formalization,
  introductory
- `references/exemplo_composicao.lean` — composition of two libraries
- `references/template_adversarial.lean` — adversarial mode,
  single-steelman per gap, ending with `theorem
  acordao_internamente_inconsistente : False`
- `references/template_steelmanning.lean` — exhaustive
  steelmanning of one gap, with four variant-versions and four distinct
  refutation strategies
- `references/vedacao_motivos_genericos.lean` — the trivialness
  check (§1º, III) applied to a generic case, with reusable template
  for any steelman

## Convention notes specific to the USER

- Match the USER's existing legal-document conventions: `## H2` and
  below; no horizontal rules; no `# H1` (handled by frontmatter or
  context).
- Skill output goes in artifacts only **after** the USER approves the
  plan/skeleton. The default workflow is: present the layer inventory
  → await approval → write the Lean file.
- Do not deliver Word versions unless asked. Lean files are
  text-native; if a Word version is requested, convert via pandoc per
  the USER's standing instructions.
