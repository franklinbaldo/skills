---
name: legal-argument-lean
description: |
  Formalizes Brazilian legal arguments (especially Embargos de Declaração) in Lean 4,
  with reusable CPC axiom libraries and an Argdown → Lean → adversarial review → forensic
  translation pipeline. Use when auditing which premises a legal argument depends on,
  steelmanning a decision to expose implicit premises, testing argumentative consistency,
  or translating a formal audit into a peça. Do not use for ordinary drafting without a
  formalization goal.
---

# legal-argument-lean

Use Lean as an **argument audit**, not as a legal-validity oracle. The payoff is the forced
separation between deduction, authority, factual claims, and unresolved juridical judgment —
especially the dependency set exposed by `#print axioms`.

## Use when

Use this skill for:

- formalizing a legal argument or a challenged decision in Lean 4;
- auditing which precedents and factual claims are load-bearing;
- testing alleged omission or internal contradiction structurally;
- exhaustive steelmanning of a decision before alleging a reasoning defect;
- comparing alternative proofs of the same forensic conclusion;
- translating a completed formal audit into conventional legal prose.

Especially good fits include embargos de declaração, adherence/distinguishing of binding
precedent, reductio arguments, and procedural inadmissibility rules with explicit logical
structure.

Do **not** use it merely to draft a peça, for pure normative interpretation without an
argumentative target, or where the dispute is principally proportionality, balancing,
open-ended principles, or another domain that classical deduction would only disguise.

## Non-negotiable boundaries

Lean proves derivability from declared assumptions. It does **not** establish that:

- a factual claim is true;
- a quotation is accurate;
- a precedent remains controlling;
- an interpretation is legally best;
- a charitable premise was actually adopted by the court.

Therefore:

1. verify material statutes, precedents, holdings, dates, and quotations against current
   official sources before reliance;
2. anchor every case-specific factual axiom in the record or source peça;
3. distinguish quoted authority from the formalizer's paraphrase;
4. never change or add axioms merely to force a theorem to compile;
5. report formal results separately from factual, precedential, and interpretive assumptions;
6. do not send confidential or sensitive case material to another model/service without
   explicit authorization and an appropriate data-handling basis.

## Choose the workflow

### Direct workflow

Use for a simple case with one clear defect or argumentative target.

1. Read the peça/decision and state the target conclusion.
2. Inventory the six modeling layers: types → opaque juridical predicates → norms →
   precedents → factual claims → theorems.
3. Write the Lean file with sections mirroring the legal argument.
4. Compile.
5. Run `#print axioms` for every material theorem.
6. Report which assumptions are load-bearing and which proof route is most economical.

Before actually modeling the layers or writing Lean, read
[`references/modeling-and-lean.md`](references/modeling-and-lean.md).

For an alleged omission, do not equate a missing sentence with a missing derivation. First
check express treatment, plausible implicit rejection, decisiveness, and whether the omitted
conclusion was univocally determinable from the premises.

### Pipeline workflow

Use for a complex decision with competing arguments, several alleged omissions, or an
adversarial reconstruction goal.

```text
Fase 0: material original
Fase 1: Argdown — anatomy + attack topology        pipeline/01_argdown.md
Fase 2: Lean — one theorem per material attack     pipeline/02_briefing_lean.md
Fase 3: independent/substantive review ↔ Fase 2    pipeline/03_analise_subjetiva.md
Fase 4: defeat synthesis with cross-references     pipeline/04_sintese_derrotas.md
Fase 5: forensic translation
```

Keep these invariants:

- Fase 1 maps arguments; it does not choose winners.
- Compilation is necessary but insufficient for a defeat finding.
- A theorem that fails to compile sends the analysis back to the argument map; do not repair
  the failure by manufacturing stronger axioms.
- Independent review is useful only inside an authorized data environment. If isolation
  would expose protected material, review in the same environment and record that limitation.
- Fase 4 is written as substantive legal analysis, not Lean/workspace jargon.

A complete worked pipeline exists under `pipeline/exemplo_marilene/`.

## Modeling contract

The six layers are:

```text
1. Tipos básicos
2. Predicados jurídicos opacos
3. Normas
4. Precedentes
5. Claims fáticos do caso
6. Teoremas
```

Detailed declarations, examples, Lean idioms, setup, and the boundary between what maps well
and badly are in [`references/modeling-and-lean.md`](references/modeling-and-lean.md). Read
that file when formalization begins; it is not necessary merely to decide whether this skill
applies.

Core rules that always stay active:

- namespace every Lean artifact;
- use Lean 4, never Lean 3 syntax;
- cite norms/precedents and record locations in docstrings;
- use real `sorry` during adversarial drafting when a step does not follow;
- replace `sorry` with explicitly named `STEEL_n` premises only during the charitable
  reconstruction phase;
- preserve material argumentative steps instead of simplifying the proof until it becomes
  legally unfaithful;
- end every material theorem with a dependency audit via `#print axioms`.

## Reusable libraries

Before selecting or composing repository axiom modules, read
[`references/libraries-and-audit.md`](references/libraries-and-audit.md). It documents the
`Tipos`/`Saidas`/art. 926/art. 927 architecture, module catalog, compile order, example files,
and interpretation of dependency audits.

Treat those modules as **formalization templates, not legal authorities**. Verify their legal
premises before case-specific reliance. Follow `references/VERSIONING.md` when changing a
published axiom's semantics: version/deprecate/replace instead of silently rewriting history.

Repo-root helpers such as `scripts/axiom_graph.py` and `scripts/lean_docgen_md.py` are
available only from a full checkout. `skills.sh` installs the skill directory, not repo-root
scripts. On a standalone skill installation, compile the Lean files and inspect `#print
axioms` directly.

## Adversarial mode

The strongest use of this skill is to formalize the **decision under attack**, not merely the
user's preferred thesis.

Use an explicit gap-finding and steelman loop:

1. identify a potentially missing or inconsistent argumentative step;
2. discard trivially impossible readings before formalization;
3. represent surviving gaps with real `sorry` placeholders;
4. replace each with several plausible `STEEL_n` premises when warranted;
5. attempt independent refutations/consistency checks;
6. inspect dependency sets;
7. only then decide whether the legal record supports alleging a defect.

Read [`references/adversarial.md`](references/adversarial.md) **in full before any adversarial
formalization**. It contains the variant ladder, filtering procedure, refutation strategies,
and the art. 489 §1º III trivialness check.

A formal inconsistency or underconstrained steelman is evidence for legal analysis, not an
automatic finding of a CPC violation.

## Translate the workspace into a peça

The Lean/Argdown trail is analytical workspace, not the product submitted to court. The final
peça should lead with what the challenged decision did, using conventional procedural-law
vocabulary, not with how the formalization discovered it.

Before drafting the forensic product, read
[`references/forensic-translation.md`](references/forensic-translation.md). Keep discarded
readings, steelman labels, theorem names, and other workspace vocabulary out of the final
prose unless they are independently useful legal concepts.

## Definition of done

A formalization task is complete only when:

1. the argumentative target is explicit;
2. every material premise is classified as norm, precedent, factual claim, or declared
   juridical predicate;
3. factual and legal authorities are traceable to verified sources;
4. Lean compiles without hiding unexplained gaps in comments;
5. every material theorem has a `#print axioms` audit;
6. steelman premises remain visibly distinguishable from authored/verified premises;
7. the report identifies load-bearing assumptions rather than dumping Lean output;
8. any forensic translation has removed workspace-only jargon and preserves the legal
   distinction actually established by the analysis.

## Out of scope

The current library models the argumentative/decisional layer. Canonical process entities,
procedural phases as a state machine, generalized appeal admissibility, and a complete typed
petition/answer model remain future additive work rather than hidden assumptions of this
skill.

## User-specific delivery conventions

- In legal documents, use `## H2` and below; avoid horizontal rules and `# H1`.
- Present the layer inventory/plan before producing a substantial Lean artifact when the task
  requires a strategic modeling choice.
- Do not create Word versions unless requested.
