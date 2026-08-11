# Speculative visual gap loop

Use this reference when `cobogo-design-review` needs to move from static critique into an evidence-backed visual improvement cycle.

The protocol works at two scales:

- **macro** — website, page, section, end-to-end flow;
- **micro** — pattern, component, fragment, or one meaningful UI state.

The mechanism is the same:

```text
imagine
→ render reality
→ compare
→ classify
→ change
→ render again
```

The speculative image creates **design pressure**. The real screenshot creates **implementation evidence**. Neither replaces canonical Cobogó knowledge.

## 1. Freeze the comparison question

Write the question before generating an image.

Good examples:

- Can this homepage expose grammar and knowledge without becoming generic design-system documentation?
- Can this provenance block make source/status/action legible through `Faixa` + `Inscrição` rather than another card?
- Can this dense review row preserve fast scanning while gaining stronger rhythm and focus behavior?
- Can this status component become more memorable without relying on color alone?

Avoid vague prompts such as "make it more Brazilian" or "make it prettier".

## 2. Freeze real constraints

Record only constraints known to be real:

- viewport/device class;
- content and content length;
- state;
- framework/runtime constraints when relevant;
- accessibility requirements;
- local theme/brand identity;
- density/repetition context;
- interaction behavior;
- deployment/print constraints.

Do not pad the brief with plausible but unverified product facts.

## 3. Select Brazilian grammar pressure

Consult Cobogó knowledge first. Select 2–4 phenomena that could materially help the comparison question.

Examples:

- `Vão` for hierarchy without mass;
- `Faixa` for linear context/action grouping;
- `Inscrição` for source/status/category orientation;
- `Ritmo` for repeated recoverable order;
- module-with-variation for repeated items;
- text-as-architecture for editorial or metadata-heavy composition;
- explicit structure + localized gesture for one memorable emphasis;
- working ornament for geometry that encodes grouping/state/orientation;
- local material memory for the consumer theme without promoting that materiality into universal core.

If a cultural reference is not already supported by the corpus, route through `brazilian-web-design` instead of treating model memory as evidence.

## 4. Generate the speculative image

When image generation is available, produce a visual concept that is deliberately free to challenge the implementation.

Prompt it with:

- the product job;
- the selected grammar pressure;
- known content/constraints;
- explicit instruction to preserve local identity where known;
- explicit instruction that invented metrics, brands, partners, users, historical claims or capabilities are forbidden.

A concept may still accidentally invent facts. Treat those as artifacts to reject during comparison, never as requirements.

### For whole surfaces

Render enough of the page to judge:

- first-fold orientation;
- major hierarchy;
- transition between sections;
- density rhythm;
- relationship between navigation, content and evidence.

### For components

Render the component large enough to inspect composition but include enough surrounding context to judge its function.

When state matters, generate only relevant state hypotheses. Common useful sets:

- default + keyboard focus;
- default + selected;
- normal + warning/error;
- populated + empty;
- compact repeated list + one expanded item;
- short content + overflow/long content.

Do not create a full state matrix merely because a design-system component could theoretically have one.

## 5. Capture reality

Use a real browser capture when possible.

Prefer:

1. deployed artifact, if the question is about what users see;
2. branch preview, if reviewing an implementation before deploy;
3. isolated component harness only when the component cannot be judged reliably inside a product route.

Control:

- viewport width/height;
- color scheme;
- font loading;
- deterministic fixture/data where possible;
- component state;
- zoom/device scale.

For repeated rounds, reuse the same capture contract so later differences are meaningful.

## 6. Compare semantically before pixel-wise

Pixel difference is useful for deployment verification, not for judging a speculative concept.

Compare in this order:

1. **job** — which version makes the intended relation easier to perceive/use?
2. **hierarchy** — where does attention go first, second, third?
3. **grammar** — which Cobogó relations are doing visible work?
4. **density/rhythm** — what becomes easier or harder when repeated or scanned?
5. **text** — is text structural or merely content inside containers?
6. **gesture/materiality** — does expression earn its space?
7. **states/accessibility** — focus, semantics, contrast, state, targets, reduced motion;
8. **identity** — does the consumer remain itself?
9. **facts** — did the concept invent anything that must be rejected?

## 7. Classify each meaningful gap

Use one of these labels:

- `preserve-real`
- `concept-insight`
- `bug-regression`
- `information-architecture-gap`
- `grammar-gap`
- `generic-design-gap`
- `over-abstracted-concept`
- `invented-authority-rejection`
- `negative-evidence`

A comparison is successful even if every speculative idea is rejected, provided it explains why the real design should remain.

## 8. Convert insight into the smallest coherent change

Examples:

- remove one unnecessary container and recover hierarchy through `Vão`;
- turn metadata into an `Inscrição` rather than a badge cloud;
- add controlled variation to repeated modules;
- expose focus as part of component form;
- split a generic card into a `Faixa` + content field;
- introduce one functional geometric gesture that marks provenance/state;
- make a page's knowledge/consumer evidence visible without adding invented institutional metrics;
- keep an existing theme because the concept demonstrated that a neutral design-system skin would erase identity.

Do not implement the concept wholesale unless every relevant difference independently survives review.

## 9. Recapture after implementation

Capture the same route/component/state again.

Now there are three useful objects:

```text
real-before
speculative-concept
real-after
```

Use them to answer:

- Which speculative insight survived implementation?
- Which real property was preserved deliberately?
- Did the change improve the product job rather than merely increase visual similarity?
- Did implementation reveal a missing Cobogó core/pattern contract?

When verifying deploy correctness, compare branch preview vs deployed capture pixel-wise under identical conditions. That is a different question from concept-vs-real design comparison.

## 10. Feed learning back

Persist only reusable knowledge.

Potential destinations:

- Cobogó reference / research concept;
- canon or grammar concept;
- specimen;
- pattern evidence;
- consumer registry evidence;
- core contract issue;
- this skill/reference;
- test/spec;
- negative evidence.

Do not store generated images as canonical design authority merely because they produced a useful idea.

## Anti-patterns

### Pixel chasing

Bad:

> The concept has a 56px heading and the implementation has 48px, so increase it.

Better:

> The concept made the section transition readable because text hierarchy, spacing and inscription created a stronger pause; determine the smallest real change that reproduces that relation.

### Brazilian skinning

Bad:

> Add yellow/green, cobogó tiles and xilogravura texture.

Better:

> Use a documented Brazilian grammar phenomenon to solve the actual relation, and keep material references local unless evidence supports broader reuse.

### Invented institutional maturity

Bad concept artifacts:

- fake client logos;
- `400+ references` without corpus evidence;
- fake newsletter/search;
- fabricated adoption statistics;
- invented testimonials.

Treat these as `invented-authority-rejection` even if visually convincing.

### Component isolation theater

A beautiful isolated component can fail when repeated 30 times. Always test the density/context that motivated the component.

### One concept becomes canon

A generated concept is one hypothesis. Cross-consumer evidence, not aesthetic confidence, promotes rules into stable Cobogó contracts.
