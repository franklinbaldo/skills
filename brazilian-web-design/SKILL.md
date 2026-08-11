---
name: brazilian-web-design
description: >-
  Research Brazilian visual culture and translate it into concrete, accessible web-interface
  rules using the Cobogó OKF corpus as the canonical knowledge base. Use when designing or
  reviewing a Franklin project, researching references for Cobogó, deriving visual grammar,
  creating specimens, or deciding whether a Brazilian reference has an operational software
  consequence rather than functioning as decoration.
when_to_use: >-
  Use for visual-language research, interface grammar, design-system decisions, consumer
  specimens, or design review where Brazilian references, Cobogó, or brasilidade materially
  affect the work. Do not use merely to add Brazilian colors, names, textures, or motifs.
compatibility: >-
  Best results require access to franklinbaldo/cobogo and a current franklinbaldo/okf-parser.
  Web research is required when new external references are needed. No Astronauta dependency
  is required: agents operate against the OKF corpus directly.
---

# Brazilian web design as operational grammar

The goal is not to make an interface **look Brazilian after the fact**. The goal is to derive
rules of composition from Brazilian design, architecture, graphic culture, editorial practice,
material culture and vernacular production, then test whether those rules improve a real
software surface.

The governing question for every reference is:

> **Que regra de interface pode ser derivada disso?**

If you cannot answer that concretely, keep the material as research. Do not promote it to
canon, CSS, tokens, components, or a consumer theme.

## Architecture boundary

Use this separation:

```text
Cobogó knowledge + canon + grammar
  ↓
okf-parser
  ├── validation
  ├── graph
  ├── queries / DuckDB
  ├── preview / commit when enabled
  └── agents

Astronauta
  = optional human browse/edit/projection surface over the same OKF bundle
```

Do not insert Astronauta between an agent and the Cobogó corpus. Do not invent a Cobogó
knowledge wrapper, database, graph model, or identity scheme if `okf-parser` already covers
the need.

## Before researching

1. Identify the concrete consumer or interface problem.
2. Locate the Cobogó checkout and `knowledge/` bundle.
3. Inspect the current corpus before browsing for new material. Reuse beats rediscovery.
4. Identify which canon rules or references already touch the problem.
5. Only then search externally for missing evidence.

With a current `okf-parser` checkout:

```bash
uv run okf-parser check /path/to/cobogo/knowledge
uv run okf-parser inventory /path/to/cobogo/knowledge
uv run okf-parser graph /path/to/cobogo/knowledge
```

If `okf-parser` is not installed, a current checkout may be invoked without creating a local
wrapper:

```bash
uvx --from 'git+https://github.com/franklinbaldo/okf-parser.git' \
  okf-parser check /path/to/cobogo/knowledge
```

Use DuckDB or typed relations when the question is relational and the current corpus exposes
the needed fields. Do not scrape Markdown a second time for facts already available through
`okf-parser`.

## Reference universe

Do not reduce Brazilian design to canonical modernist names. Search according to the problem.
Relevant families can include:

- cobogó and other climate-responsive architectural devices;
- azulejaria and Athos Bulcão;
- Lina Bo Bardi, Lúcio Costa, Niemeyer and modern architecture;
- brutalism tropical and public/institutional architecture;
- concrete and neoconcrete art;
- Aloisio Magalhães and Brazilian graphic design;
- public and urban signage;
- newspapers, books, book covers, posters and record sleeves;
- cordel, xilogravura and popular print;
- lambe-lambe, hand-painted signs and commercial lettering;
- fairs, storefronts, boat painting, truck bodies and vernacular color systems;
- football graphics and stadium/public-event visual culture;
- Afro-Brazilian, Indigenous and regional visual languages when sourced and contextualized
  carefully rather than extracted as generic motifs;
- contemporary Brazilian digital and graphic culture.

This list is a search space, not a checklist or canon.

## Source discipline

Prefer primary, archival, institutional, museum, foundation, library and scholarly sources.
Use secondary design journalism when it adds documentation unavailable elsewhere, but do not
let popularity substitute for provenance.

For each usable reference, capture:

1. source;
2. historical/social context;
3. observed phenomenon;
4. derived interface rule;
5. possible software application;
6. when not to use it;
7. stereotype/extraction risk;
8. related canon rules, consumers, specimens or counterexamples.

Do not infer a broad cultural rule from one image without corroboration. Do not imitate a
specific artwork as a shortcut to cultural legitimacy.

## Workflow

### 1. State the software problem first

Write the concrete need before opening references.

Good:

> “O Vigia precisa distinguir matéria, evidência e arquivo sem transformar cada bloco em um card.”

Bad:

> “Quero algo mais brasileiro.”

If the request is only the second form, derive a real interface problem from the consumer
before proceeding.

### 2. Query the existing Cobogó corpus

Look for:

- canon rules that constrain the task;
- visual references already carrying derived rules;
- counterexamples/failure modes;
- consumer-specific context;
- prior specimens.

Follow reverse relations when useful. A known rule with a strong existing reference is usually
better than adding another famous name.

### 3. Research the missing phenomenon

Search for evidence that answers the interface problem, not for pictures that match a mood.

For example, if the problem is repetitive dashboard composition, research systems where a
small module vocabulary produces controlled variation. If the problem is hierarchy without
boxes, research spatial devices that structure through void, rhythm, permeability or type.

### 4. Separate observation from derived rule

Use this template internally:

```text
Observed phenomenon:
Evidence/source:
Why it matters:
Derived interface rule:
Visible consequence:
When not to use:
Stereotype/extraction risk:
```

The observed phenomenon must be descriptive. The derived rule is a design judgment and must
remain distinguishable from the historical source.

### 5. Run the “surface swap” test

Ask:

> If I remove the color, texture, motif, name and illustration, does any Brazilian-derived
> rule remain in the composition?

If no, the proposal is probably `Brasil por superfície`: keep researching or discard the
claim of brasilidade.

### 6. Run the accessibility test

A cultural derivation does not outrank accessibility.

Check, where relevant:

- semantic structure;
- keyboard path;
- focus visibility;
- text contrast and non-text contrast;
- target size;
- reading order;
- reduced motion;
- screen-reader semantics;
- density and cognitive load.

If a visual idea fails, redesign the idea. Do not add an accessibility patch that leaves the
underlying composition hostile.

### 7. Test against at least one real consumer

Prefer two when the rule might accidentally create a universal skin.

Reference tests:

- **Astronauta** — high-density administrative/knowledge interface;
- **O Vigia** — editorial, reading and archive interface.

A good Cobogó rule should allow **parentesco sem uniformidade**. If both surfaces converge on
the same cards, radii, density and page skeleton, the rule is too implementation-specific.

### 8. Persist reusable knowledge

Reusable knowledge must not die in chat, issue or PR prose.

Persist according to kind:

```text
visual/historical reference → Cobogó OKF visual-reference
operational visual rule      → canon-rule or design-grammar
failed/cliché approach       → counterexample or failure-mode
consumer-specific need       → consumer / consumer-theme
reusable reasoning method    → skill
technology choice            → ADR/RFC
verifiable invariant         → test/spec
```

Do not duplicate the same fact in several layers. The corpus stores knowledge; this skill
stores method.

### 9. Write OKF concepts conservatively

Reuse the current concept types when they fit. Do not create a new type because a directory
name suggests one.

For a new `visual-reference`, preserve at least the fields currently used by the corpus:

```yaml
type: visual-reference
title: ...
source: ...
source_url: ...
context: ...
phenomenon: ...
derived_rule: ...
when_not_to_use: ...
stereotype_risk: ...
```

Then link the concept body to the canon rule, consumer, specimen or counterexample it actually
supports. Markdown links are graph evidence; do not add fake edges merely to make the graph
look connected.

### 10. Validate before proposing promotion

Run at least:

```bash
okf-parser check <cobogo>/knowledge
okf-parser inventory <cobogo>/knowledge
okf-parser graph <cobogo>/knowledge
```

When a change affects typed declarations or relational policy, use the strongest current
`okf-parser` schema/DuckDB surface available rather than assuming an older CLI.

Do not describe a new rule as canonical if the repository still marks it proposed or if the
supporting evidence is unresolved.

## Review heuristics

Treat these as strong warning signs:

- green/yellow/blue selected before semantics;
- azulejo/cobogó pattern added without a job;
- Brazilian names assigned to ordinary spacing/radius tokens as proof of identity;
- famous architect named with no operational consequence;
- one artwork imitated too literally;
- “tropical” used as an aesthetic adjective without climate, material or social context;
- popular, Afro-Brazilian, Indigenous or regional visual production detached from provenance;
- every consumer receiving the same composition because “the design system says so”;
- accessibility deferred until after the expressive decision;
- new research left only in a PR description.

## Output contract

A substantive use of this skill should end with four things, scaled to the task:

1. **problem** — the concrete interface question;
2. **evidence** — existing corpus concepts and/or new researched sources;
3. **rule** — the derived operational constraint, including when not to use it;
4. **persistence** — where reusable knowledge was added or why no new knowledge deserved
   promotion.

For implementation work, add a fifth:

5. **specimen/evidence** — a concrete consumer example showing the rule in context, including
   accessibility behavior where relevant.

## Definition of done

The task is complete when:

1. the interface problem was stated independently of a desired Brazilian “look”;
2. the existing Cobogó corpus was consulted first;
3. new references, when needed, are sourced and contextualized;
4. observation and derived rule are clearly separated;
5. the rule has a visible software consequence and an explicit non-use case;
6. stereotype/extraction risk was considered;
7. accessibility shaped the rule rather than being appended later;
8. at least one real consumer was used to test the proposal;
9. reusable knowledge was persisted in the correct canonical layer;
10. the OKF bundle validates with current `okf-parser` before the knowledge change is treated as ready.
