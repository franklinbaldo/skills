# Modeling and Lean guide

Read this reference when the task reaches actual formalization or Lean execution. The main `SKILL.md` owns routing, safety, workflow choice, and delivery invariants; this file owns the detailed modeling conventions.

## Six-layer architecture

Map every legal element to one of six layers. Use these comment headers literally so the Lean file remains readable as a parallel of the peça.

```text
Camada 1 — Tipos básicos              (Caso, Vinculo, Precedente, ...)
Camada 2 — Predicados opacos          (qualificações jurídicas não-dedutivas)
Camada 3 — Normas                     (constitutivas do sistema; cite o dispositivo)
Camada 4 — Precedentes                (axiomas nomeados; cite no docstring)
Camada 5 — Claims fáticos             (extraídos do acórdão/peça, não inventados)
Camada 6 — Teoremas                   (as teses da peça)
```

### Camada 1 — Tipos básicos

Declare the universe of discourse with `axiom`, not `opaque`.

```lean
axiom Caso : Type
axiom Vinculo : Type
```

### Camada 2 — Predicados opacos

Use predicates for juridical qualifications that are decided rather than computed. Keeping them opaque makes explicit where the controversy is non-deductive.

```lean
axiom DependeReexameProbatorio : Caso → Prop
axiom FatosIncontroversos : Caso → Prop
```

### Camada 3 — Normas

State constitutional, statutory, and procedural norms as implicational or bidirectional axioms. Always cite the dispositivo in a docstring.

```lean
/-- Súmula 279/STF: definição operacional usada nesta formalização. -/
axiom sumula_279_definicao :
    ∀ (c : Caso), AplicaSumula279 c ↔ DependeReexameProbatorio c
```

### Camada 4 — Precedentes

Each cited precedent becomes one named axiom. The docstring carries the full verified citation and the proposition being modeled. The formal plane does not derive the precedent; it declares the authority whose application is being audited.

```lean
/-- RE 210.917, citation verified against the official source before reliance. -/
axiom RE_210_917 :
    ∀ (c : Caso),
      FatosIncontroversos c →
      ApenasQualificacaoJuridica c →
      ¬ DependeReexameProbatorio c
```

### Camada 5 — Claims fáticos

Anchor every case-specific claim in the record or source peça. Cite the location in the docstring. Never fabricate a claim merely to close a proof.

```lean
axiom caso_concreto : Caso

/-- Voto recorrido, localização verificada no processo. -/
axiom fatos_incontroversos : FatosIncontroversos caso_concreto
```

### Camada 6 — Teoremas

Theorems are the argumentative conclusions. When multiple routes support the same conclusion, keep separate proofs so `#print axioms` can expose which assumptions are load-bearing.

```lean
theorem sumula_279_inaplicavel : ¬ AplicaSumula279 caso_concreto := by
  rw [sumula_279_definicao]
  exact RE_210_917 caso_concreto fatos_incontroversos apenas_qualificacao
```

## Lean 4 setup

First check whether Lean already exists:

```bash
lean --version
```

If unavailable, do not install it automatically and never pipe a remote installer into a shell. Ask the user for permission and use the official Lean installation instructions. After an authorized Elan installation, pin the expected toolchain explicitly; prefer a project-local `lean-toolchain` file for reproducibility.

The current repository modules use pure first-order logic with axioms and do not require Mathlib unless a concrete extension truly needs it.

## Lean idioms

### `variable` for modules with a fixed subject

When a reusable module quantifies repeatedly over the same types, declare variables once. Prefer explicit parameters in standalone case files where explicitness helps auditability.

```lean
variable (d : Decisao) (p : Precedente)

theorem aplica_implica_invoca :
    AplicaCorretamente d p → InvocaPrecedente d p := by
  intro h
  exact h.1
```

### `@[simp]` on compound definitions

Mark reusable compound definitions with `@[simp]` when unfolding them is mechanically safe and makes proofs shorter.

```lean
@[simp]
def AplicaCorretamente (d : Decisao) (p : Precedente) : Prop :=
    InvocaPrecedente d p ∧
    IdentificaFundamentosDeterminantes d p ∧
    DemonstraAjusteAoCaso d p
```

### `sorry` in the adversarial draft phase

In the draft phase, use the real `sorry` keyword for steps that do not follow. In the steelman phase, replace each `sorry` with an explicitly named charitable premise (`STEEL_n`). A clean compilation after that does not prove the premise was actually adopted by the court; it makes the reconstruction auditable through `#print axioms`.

Attach the repository's `ClaimMeta.SteelMeta` metadata where the complex pipeline requires it. Do not replace real `sorry` with comments such as `-- sorry`; comments are invisible to the compiler and easy to lose.

## What maps well

- inadmissibility rules with clear predicates and implications;
- omission analysis after distinguishing express treatment and plausible implicit rejection;
- internal contradiction as a theorem deriving `False`;
- adherence to binding precedent through named axioms and application conditions;
- reductio arguments;
- prequestionamento represented as an explicit hypothesis/device inventory.

## What maps badly

Do not force classical deduction onto:

- vague merits disputes whose whole controversy is a juridical qualification;
- defeasibility with layered exceptions unless a simple antecedent model is genuinely useful;
- proportionality and balancing;
- open-ended principles;
- the judge's free evaluation of evidence.

When the legal disagreement remains inside an opaque predicate, say so. The inability to derive more is itself an informative boundary of the formalization.

## Output invariants

- Lean 4 only.
- Namespace every file.
- Use Portuguese comments/docstrings when the legal content is Portuguese.
- Never fabricate precedents, quotations, claims, or record locations.
- Verify material legal authority against current official sources before reliance.
- Never present compilation as legal correctness.
- Preserve every material argumentative step; do not simplify away the point being audited.
- End with `#print axioms` for every theorem whose dependency set matters.

For adversarial steelmanning, read `adversarial.md` before formalizing. For conversion of the analytical workspace into a forensic peça, read `forensic-translation.md` before drafting the product.