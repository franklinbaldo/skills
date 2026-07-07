# Adversarial mode — formalizing the *embargado*, not the *embargante*

> Companion reference for the `legal-argument-lean` skill. Read this file
> in full before doing any adversarial formalization (steelmanning an
> acórdão). Worked Lean examples: `template_adversarial.lean`,
> `template_steelmanning.lean`, `template_filtro.lean`,
> `vedacao_motivos_genericos.lean`, `sec1III_check_quatro_v2s.lean`,
> `sec1III_check_STEEL1_STEEL3.lean`.

The most powerful application of this skill is **not** formalizing the
peça's own argument, but formalizing the **acórdão being challenged**.
The methodology is *steelmanning via sorry-replacement*, applied
**exhaustively** across all plausible interpretations of each gap.

## The basic loop

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

## Going further: exhaustive steelmanning

A single steelman is methodologically insufficient. The court could
reply: "but I meant a different interpretation of that step." The
proper response is to enumerate **all plausible steelmans in
ascending order of deference to the court** and refute each by its
own strategy. This is the case-analysis-exhaustivo technique applied
to legal argument.

## Pre-step: filtro de trivialidade

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

## Exhaustive steelmanning of the surviving readings

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

## MANDATORY trivialness check (§1º, III)

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

A worked example is at `vedacao_motivos_genericos.lean`,
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
