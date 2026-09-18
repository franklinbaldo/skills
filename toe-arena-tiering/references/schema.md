# ToE Arena record schema

Recommended canonical record for one contender:

```yaml
slug: string
name: string
kind: contender | adjacent | exhibition
scientific_tier: S | A | B | C | D | F | NR
interest_tier: S | A | B | C | D | F
confidence: low | medium | high
status: active | historical | disputed | exploratory
origin:
  authors: [string]
  first_published: YYYY-MM-DD
  source: URL
claims: string
scope: [string]
strengths: [string]
open_problems: [string]
predictions: [string]
sources:
  - label: string
    url: URL
    date: YYYY-MM-DD
last_reviewed: YYYY-MM-DD
movement:
  from: tier | null
  to: tier
  date: YYYY-MM-DD
  reason: string
```

`NR` means not ranked scientifically. Use it for adjacent/exhibition entries that do not actually claim to be a Theory of Everything or fundamental unification framework.

A clash record should name both slugs, one battleground, each side's concrete advantage/liability, what evidence could change the comparison, and whether the clash caused a tier movement.
