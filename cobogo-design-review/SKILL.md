---
name: cobogo-design-review
description: >-
  Review an interface, design-system PR, specimen, or implementation against Cobogó's
  Brazilian visual grammar and canonical OKF knowledge. Use when deciding whether a surface
  actually applies Cobogó rather than merely copying colors, patterns, components, Pico
  conventions, or another consumer's appearance.
---

# Review a surface against Cobogó grammar

Cobogó centralizes **visual grammar and reusable design knowledge**, not one shared look.
A successful review must be able to explain both family resemblance and legitimate product
specificity.

Use the canonical corpus in `franklinbaldo/cobogo/knowledge` through `okf-parser` as the
source of current canon, grammar, references, counterexamples and specimens. Do not treat
`DESIGN.md`, Pico CSS, Svelte components, the vitrine, or this skill as a stronger source than
the corpus when they disagree with an accepted corpus rule.

## Before reviewing

1. Identify the surface and its actual product job.
2. Identify the consumer context: editorial, administrative, analytical, transactional,
   public-service, or another concrete mode.
3. Inspect the current Cobogó corpus directly. Prefer `okf-parser` inventory/graph/query
   surfaces when available; do not route through Astronauta merely because it can render the
   bundle.
4. Distinguish authored product constraints from inherited design-system habits.
5. If the change introduces a new Brazilian reference or cultural claim, use the
   `brazilian-web-design` skill first to derive and persist the rule instead of laundering an
   unsupported aesthetic preference through review language.

## Core review sequence

### 1. State what the interface is trying to make perceptible

Write one sentence naming the principal relation the user must understand, for example:

- concept → fields → relations → diagnostics → mutation;
- event → evidence → context → provenance;
- question → answer → source → next action.

If the review cannot name the relation, component-level critique will be premature.

### 2. Map visible composition to grammar

For each major region, identify the operative grammar rather than the component name.
Current examples include:

- `Vão` — separation that works without adding a container;
- `Faixa` — linear grouping of related context/action;
- `Inscrição` — short text that structurally orients state, source, category or action;
- `Ritmo` — recurring informational order that makes content recoverable.

A `Card`, `Badge`, `Panel`, grid component or CSS class is implementation. Ask what relation it
represents and whether a simpler grammar operation would do the job.

### 3. Check canon as constraints, not mood

For every applicable canon rule, record a visible consequence or mark it not applicable.
Do not award credit for prose alignment without implementation consequence.

Review at least:

- **vão antes de massa** — could alignment/distance replace unnecessary containers?
- **módulo sem monotonia** — is there stable structure with legitimate variation, or either
  copy-paste sameness or arbitrary inconsistency?
- **texto é arquitetura** — do hierarchy, measure and metadata help form the structure, or is
  text merely filling boxes?
- **parentesco sem uniformidade** — does the consumer share Cobogó relations without becoming
  a clone of another product?
- accessibility rules present in the corpus/spec — are contrast, focus, semantics, keyboard,
  motion and state communication part of the form itself?

When another canon rule exists in the corpus and materially applies, include it.

### 4. Run the surface-swap test

Ask which visible signs could be replaced without changing the underlying composition:

- green/yellow or a named palette;
- cobogó/azulejo pattern;
- concrete/paper texture;
- a Brazilian-sounding token name;
- xilogravura/cordel styling;
- a famous designer's visual motif.

If swapping those signs leaves a generic dashboard/article/component gallery unchanged, the
Brazilian identity is superficial.

Report this as a concrete design defect only when the PR or surface claims Cobogó/Brazilian
identity. Do not demand decorative Brazilian markers as remediation.

### 5. Check ornament for work

Every decorative or expressive element must do at least one job:

- explain grouping;
- establish hierarchy;
- convey state;
- support orientation;
- improve recognition/memory;
- preserve provenance/context;
- create a deliberate, accessible emphasis or rupture.

If it does none, ask for removal or a functional justification. "It references Brazil" is not
a function.

### 6. Check density against context

Do not use one whitespace target across products.

- administrative surfaces may be dense if hierarchy and focus remain legible;
- editorial surfaces may use larger pauses and measures for sustained reading;
- data-heavy views may need compact repeated structures;
- public-facing transactional flows may need stronger sequencing and larger targets.

Flag density only when it harms the actual task, accessibility, rhythm or relation clarity.

### 7. Check local design-system duplication

Look for the consumer reinventing foundations or grammar already owned by Cobogó:

- a parallel token system for the same semantic role;
- local spacing/geometry rules presented as universal;
- duplicate status semantics;
- a second component/pattern abstraction that exists only because Cobogó's core was not
  consulted.

Do **not** flag legitimate product themes, editorial identity, domain-specific components, or
workflow-specific states merely because Cobogó does not own them. The goal is family, not
centralized appearance.

### 8. Compare against the right specimen, not a screenshot

Use Cobogó specimens as compositional tests.

For Astronauta-like administrative work, check density, relations, diagnostics, preview and
commit hierarchy.

For O Vigia-like editorial work, check long-form reading, evidence, context and provenance.

A specimen is evidence of grammar under a context. It is not a template to copy.

### 9. Classify findings

Use these severities:

- **P1 — breaks a canonical/accessibility invariant**: likely causes error, exclusion,
  ambiguity in critical state/action, or directly contradicts an accepted normative rule.
- **P2 — architecture/grammar defect**: duplicates the design system, encodes superficial
  brasilidade, makes different consumers clones, or uses component structure that obscures
  the intended visual relation.
- **P3 — refinement**: improves rhythm, hierarchy, density or expressiveness but the current
  surface remains coherent and usable.
- **Observation**: useful design-system knowledge or a candidate rule/reference that should be
  researched; not yet a defect.

Do not inflate taste disagreements into P1/P2 findings.

### 10. Persist reusable learning

A review is incomplete if it discovers reusable knowledge and leaves it only in a PR comment.
Classify the new fact:

- Brazilian/reference evidence → Cobogó OKF `visual-reference` / research concept;
- reusable composition rule → canon/grammar concept;
- demonstrated composition → specimen;
- repeated review method → this skill;
- technological choice → ADR/RFC;
- enforceable invariant → test/spec.

Avoid duplicating the same rule in several sources. Link instead.

## Review output

Prefer a short set of concrete findings over a design essay. Each finding should contain:

1. severity;
2. exact surface/location;
3. violated or weak grammar/canon relation;
4. why it matters for the product task;
5. smallest coherent correction;
6. corpus/reference link when the claim depends on Cobogó knowledge.

Then summarize:

- which Cobogó relations the surface already demonstrates well;
- whether its Brazilian identity is structural or mostly superficial;
- whether it is recognizably related to other consumers without becoming a clone;
- reusable knowledge that should be persisted.

## Guardrails

- Do not require Pico, Svelte, Astro, classless CSS, Atomic Design, or any framework unless a
  current contract independently requires it.
- Do not use Brazilian references as authority for accessibility regressions.
- Do not demand a visual motif merely because the repo historically shipped it.
- Do not infer a canon rule from one famous work without documenting the phenomenon and
  limits.
- Do not turn every cultural reference into a token or pattern.
- Do not treat Astronauta as the canonical knowledge administrator; agents use `okf-parser`
  directly.
- Do not make O Vigia, Astronauta, Ficha, CausaGanha, Baliza or future consumers visually
  identical.

## Definition of done

A Cobogó design review is complete when:

1. the product job and principal visual relation are explicit;
2. major composition is described through grammar rather than component names;
3. applicable canon rules have visible consequences;
4. superficial brasilidade has been tested rather than assumed;
5. accessibility is reviewed as form;
6. density is evaluated in product context;
7. local duplication is distinguished from legitimate product identity;
8. comparison uses appropriate specimens without template copying;
9. findings are severity-calibrated and actionable;
10. reusable knowledge discovered by the review has a persistence destination.
