---
name: cobogo-design-review
description: >-
  Review and improve a website, page, section, pattern, component, or UI state against
  Cobogó's Brazilian visual grammar. Use when a surface needs more than compliance review:
  reconstruct its product job, imagine a stronger Brazilian-grammar hypothesis, compare that
  concept with the real rendered implementation, classify the visual gap, and turn useful
  differences into concrete design-system or consumer changes without inventing facts.
---

# Cobogó design review

Cobogó centralizes **visual grammar and reusable design knowledge**, not one shared look.
The skill is not a checklist for deciding whether an implementation is sufficiently
"Brazilian". It is a recurring design loop that deliberately creates a stronger visual
hypothesis, confronts it with the real implementation, and learns from the difference.

The core loop is:

```text
product job
→ canonical Cobogó evidence
→ Brazilian-grammar imagination
→ concept image
→ real rendered capture
→ visual gap classification
→ smallest useful implementation change
→ recapture
→ reusable learning
```

Run it at any useful scale:

- entire website;
- page;
- section;
- pattern;
- component;
- component state or interaction state.

Use the canonical corpus in `franklinbaldo/cobogo/knowledge` through `okf-parser` as the
source of current canon, grammar, references, counterexamples and specimens. Do not treat
this skill, a generated image, `DESIGN.md`, Pico CSS, Svelte components, or another consumer
as stronger authority than accepted corpus knowledge.

## Two kinds of evidence

Keep these separate throughout the review.

### Factual evidence

May support claims about the real product:

- rendered screenshots;
- source code;
- current product behavior;
- canonical OKF concepts;
- verified consumer registry facts;
- measured accessibility/performance/state behavior.

### Speculative evidence

May suggest composition but **must not create facts**:

- generated concept images;
- sketches;
- speculative layouts;
- imagined component states;
- deliberately exaggerated visual alternatives.

A generated concept may invent hierarchy, rhythm, geometry, visual relations, materiality,
spacing and expressive emphasis. It may **not** be cited as evidence that a product has
features, users, adoption, metrics, partners, history, logos, content or states that were not
verified independently.

## Before reviewing

1. Identify the exact surface and its actual product job.
2. Choose the review scale. If the problem is a component, do not redesign the whole product
   merely because a page screenshot is easier to obtain.
3. Identify consumer context: editorial, administrative, analytical, transactional,
   public-service, authoring, document/print, immersive, or another concrete mode.
4. Inspect the current Cobogó corpus directly. Prefer `okf-parser` inventory/graph/query
   surfaces when available; do not route through Astronauta merely because it can render the
   bundle.
5. Distinguish authored product constraints from inherited design-system habits.
6. If the work introduces a new Brazilian reference or cultural claim, use
   `brazilian-web-design` to derive and persist the rule before treating that reference as
   design authority.

## Core sequence

### 1. State the relation the surface must make perceptible

Write one sentence naming the primary relation the user needs to understand or act on.
Examples:

- concept → fields → relations → diagnostics → mutation;
- event → evidence → context → provenance;
- question → answer → source → next action;
- status → consequence → available action;
- source text → preview → publication artifact.

For a component, describe its role in context rather than naming the component type. "Card",
"badge", "table" or "accordion" is implementation vocabulary, not the design problem.

### 2. Build the Brazilian imagination brief

Before generating a visual concept, choose a small set of **operative phenomena** from the
corpus that could improve the product job. Do not start from decoration.

Useful prompts include:

- **Vão antes de massa** — can separation, air and alignment do work that another box would
  otherwise do?
- **Módulo sem monotonia** — what repeats, what rotates/varies, and what remains stable?
- **Estrutura explícita, gesto localizado** — where should the system stay quiet and where can
  one expressive rupture earn attention?
- **Texto é arquitetura** — can title, inscription, metadata, measure or typographic rhythm
  carry structure that generic containers currently carry?
- **Faixa** — can a linear band organize context, provenance, actions or state?
- **Inscrição** — what short text can orient category, source, status or sequence?
- **Ritmo** — what recurring order makes the information recoverable?
- **Ornamento deve trabalhar** — if geometry/materiality is introduced, what information or
  orientation job will it perform?
- **Parentesco sem uniformidade** — how can this consumer remain recognizably related to
  Cobogó without looking like another consumer?
- **Acessibilidade é forma** — what focus, state, contrast, motion or semantic behavior must
  remain visually integrated rather than bolted on?

Use references broadly: Brazilian editorial design, urban graphics, cordel/xilogravura,
signage, vernacular production, modernism/concretism/neoconcretism, Afro-Brazilian,
Indigenous and regional production when supported by context and sources. Never reduce the
brief to a palette or a famous motif.

The imagination brief should usually contain **2–4 operative ideas**, not every canon rule.

### 3. Generate a concept image

When image generation is available and the visual decision is material, generate at least one
concept image **before** judging the real implementation.

The concept should:

- preserve the real product job and known constraints;
- make the selected Brazilian grammar visible through composition;
- be allowed to diverge substantially from the current implementation;
- avoid copying a named consumer or famous work as a skin;
- use plausible real content when available;
- use clearly neutral placeholders when content is unknown;
- never invent factual adoption, metrics, partners, users, history or product capabilities.

The concept is a **probe**, not a target screenshot. Its job is to expose possibilities the
current implementation may be hiding.

For a component, imagine it at component scale. Include the context necessary to judge the
relation and, when material, produce a state set such as:

- default;
- hover/focus;
- selected/active;
- error/warning/success;
- loading/empty;
- dense/compact;
- long-content/overflow.

Do not generate decorative state variants that the product does not need.

Read [`references/speculative-visual-gap-loop.md`](references/speculative-visual-gap-loop.md)
for the detailed capture/comparison protocol.

### 4. Capture the real implementation

Compare against pixels, not memory.

Prefer a real browser capture of the actual implementation at a controlled viewport. For a
component, capture the component in its representative context and relevant state. If the
surface is already deployed, prefer the deployed artifact when the question is about what
users actually see.

Keep capture conditions stable enough that differences are attributable to design rather than
viewport, font loading, data drift or random state.

### 5. Compare concept and reality

Do **not** ask "how do we make reality match the generated image?"

Ask what the divergence reveals.

Classify each meaningful difference as one of:

- **Preserve real** — the implementation is stronger, more authentic, more accessible, or
  better fitted to the product than the speculative concept.
- **Concept insight** — the imagined version exposes a useful hierarchy, relation, density,
  rhythm, materiality or orientation improvement.
- **Bug / regression** — the implementation is broken, misleading or fails its own intended
  visual behavior.
- **Information-architecture gap** — appearance may be coherent but the surface communicates
  an outdated or incomplete product model.
- **Grammar gap** — the surface satisfies function but misses an applicable Cobogó relation
  that could improve clarity or identity.
- **Generic-design gap** — the real surface collapses into a generic dashboard/docs/card
  vocabulary even though stronger structural identity is possible.
- **Over-abstracted concept** — the concept looks polished but erases product identity,
  introduces unnecessary uniformity or behaves like generic design-system marketing.
- **Invented-authority rejection** — a visually attractive concept element depends on facts or
  capabilities that are not real and therefore must not be implemented as presented.

Negative evidence is useful. A concept can prove that the current implementation should stay
as-is.

### 6. Map visible composition to grammar

For each major region or component part, identify the operative grammar rather than the
component name.

Current examples include:

- `Vão` — separation that works without adding a container;
- `Faixa` — linear grouping of related context/action;
- `Inscrição` — short text that structurally orients state, source, category or action;
- `Ritmo` — recurring informational order that makes content recoverable.

A `Card`, `Badge`, `Panel`, grid component or CSS class is implementation. Ask what relation it
represents and whether a simpler or more expressive grammar operation would do the job.

### 7. Check canon as constraints, not mood

For every applicable canon rule, record a visible consequence or mark it not applicable.
Do not award credit for prose alignment without implementation consequence.

Review at least the rules that materially apply, especially:

- **vão antes de massa**;
- **módulo sem monotonia**;
- **texto é arquitetura**;
- **parentesco sem uniformidade**;
- accessibility rules present in the corpus/spec.

Do not force every rule into every component.

### 8. Run the surface-swap test

Ask which visible signs could be replaced without changing the underlying composition:

- green/yellow or a named palette;
- cobogó/azulejo pattern;
- concrete/paper texture;
- a Brazilian-sounding token name;
- xilogravura/cordel styling;
- a famous designer's visual motif.

If swapping those signs leaves a generic dashboard/article/component gallery unchanged, the
Brazilian identity is superficial.

Report this as a design defect only when the surface claims Cobogó/Brazilian identity or when
structural differentiation is part of the task. Do not demand decorative Brazilian markers as
remediation.

### 9. Check ornament for work

Every decorative or expressive element must do at least one job:

- explain grouping;
- establish hierarchy;
- convey state;
- support orientation;
- improve recognition/memory;
- preserve provenance/context;
- create a deliberate, accessible emphasis or rupture.

"It references Brazil" is not a function.

### 10. Check density against context

Do not use one whitespace target across products.

- administrative surfaces may be dense if hierarchy and focus remain legible;
- editorial surfaces may use larger pauses and measures for sustained reading;
- data-heavy views may need compact repeated structures;
- public transactional flows may need stronger sequencing and larger targets;
- component density should be judged in the layout where the component actually repeats.

### 11. Check local design-system duplication

Look for the consumer reinventing foundations or grammar already owned by Cobogó:

- parallel semantic tokens for the same role;
- local spacing/geometry rules presented as universal;
- duplicate status semantics;
- a second pattern abstraction created only because Cobogó's public contract was not
  consulted.

Do not flag legitimate product themes, domain components, workflow states or editorial identity.
The goal is family, not centralized appearance.

### 12. Use specimens and screenshots for different jobs

A **screenshot** is evidence of what a real or speculative surface looks like.
A **Cobogó specimen** is evidence that a grammar relation survived a context.

Do not use either as a template to copy.

For Astronauta-like administrative work, inspect density, relations, diagnostics, preview and
commit hierarchy. For O Vigia-like editorial work, inspect long-form reading, evidence,
context and provenance. For a new context, use the concept-vs-real loop to discover whether a
new specimen or pattern is warranted.

### 13. Implement the smallest useful convergence

Do not blindly converge toward the concept image.

Prefer the smallest change that captures a validated insight while preserving what the real
surface already does better. Typical outputs include:

- one CSS/layout adjustment;
- one component-state redesign;
- one information-hierarchy change;
- one new/changed Cobogó pattern;
- one consumer theme mapping;
- one accessibility correction;
- one upstream core capability exposed because self/consumer use revealed a missing public
  contract.

Then recapture the same surface and compare again.

### 14. Classify findings

Use these severities:

- **P1 — breaks a canonical/accessibility invariant**: likely causes error, exclusion,
  ambiguity in critical state/action, or directly contradicts an accepted normative rule.
- **P2 — architecture/grammar defect**: duplicates the design system, encodes superficial
  brasilidade, makes different consumers clones, or obscures the intended relation.
- **P3 — refinement**: improves rhythm, hierarchy, density or expressiveness while the current
  surface remains coherent and usable.
- **Observation**: useful design-system knowledge, concept insight, rejected speculative idea,
  or candidate rule/reference that should be researched; not yet a defect.

Do not inflate taste disagreements into P1/P2 findings.

### 15. Persist reusable learning

A review is incomplete if reusable knowledge remains only in chat or a generated image.
Classify it:

- Brazilian/reference evidence → Cobogó OKF visual-reference/research concept;
- reusable composition rule → canon/grammar concept;
- demonstrated composition → specimen;
- repeated relation across consumers → pattern candidate or pattern evidence;
- repeated review method → this skill/reference;
- technological choice → ADR/RFC;
- enforceable invariant → test/spec;
- consumer-only identity → keep downstream;
- rejected concept / failed hypothesis → negative evidence when it would prevent repetition.

Avoid duplicating one rule in several authorities. Link instead.

## Component-scale protocol

When reviewing one component, keep the loop narrow:

```text
component job in context
→ relevant Brazilian grammar
→ imagined component/state
→ real component/state screenshot
→ gap
→ component or upstream-contract change
→ state recapture
```

Ask:

- Does the component have enough context to judge its meaning?
- Is repeated structure monotonous where controlled variation would improve recognition?
- Is a box/card doing work that spacing, inscription or typography could do?
- Does focus look like part of the component rather than a browser afterthought?
- Are status and action communicated without color-only semantics?
- Does an expressive gesture improve recognition/state/orientation, or merely decorate?
- If the component repeats 20 times, does the imagined solution still work at that density?
- Does the component remain recognizably the consumer's, rather than becoming a Cobogó demo?

## Review output

Prefer concrete findings over a design essay. For each material gap include:

1. severity or gap class;
2. exact surface/component/state;
3. what the real screenshot shows;
4. what the speculative concept revealed;
5. relevant grammar/canon relation;
6. why it matters to the product job;
7. smallest coherent correction;
8. persistence destination when reusable.

Then summarize:

- what the real surface already does better and must be preserved;
- which concept insights are worth implementing;
- which concept ideas were rejected as generic, ornamental or factually invented;
- whether Brazilian identity is structural or mostly surface-level;
- whether family resemblance exists without clone uniformity;
- what should feed back into Cobogó knowledge/core/patterns.

## Guardrails

- Do not require Pico, Svelte, Astro, classless CSS, Atomic Design, or any framework unless a
  current contract independently requires it.
- Do not use Brazilian references as authority for accessibility regressions.
- Do not demand a visual motif merely because the repo historically shipped it.
- Do not infer a canon rule from one famous work without documenting phenomenon and limits.
- Do not turn every cultural reference into a token or pattern.
- Do not treat a generated concept as factual product evidence.
- Do not optimize for pixel similarity to the generated concept.
- Do not fabricate logos, adoption, metrics, testimonials, partners, users, features or
  historical claims to make a concept feel complete.
- Do not let image generation override negative evidence from the real consumer.
- Do not treat Astronauta as canonical knowledge administrator; agents use `okf-parser`
  directly.
- Do not make O Vigia, Astronauta, Ficha, CausaGanha, Baliza or future consumers visually
  identical.

## Definition of done

A material Cobogó design review is complete when:

1. product job, context and review scale are explicit;
2. relevant canonical evidence was consulted;
3. the imagination brief names a small set of operative Brazilian grammar ideas;
4. a concept image was generated when visual divergence was material and image generation was
   available;
5. the real implementation was captured in a comparable state;
6. concept-vs-real gaps were classified without treating the concept as authority;
7. fabricated/speculative facts were rejected rather than copied into product claims;
8. applicable canon and accessibility constraints have visible consequences;
9. the smallest useful convergence was identified or implemented;
10. the surface was recaptured when implementation changed;
11. reusable learning has a persistence destination;
12. negative evidence is preserved when it changes what should be attempted next.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and
any friction/workaround. Routine success stays ephemeral. If there is actionable learning,
search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use
feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
