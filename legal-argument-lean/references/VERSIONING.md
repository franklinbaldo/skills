# Versioning the legal axiom libraries

The reference modules are reproducible formalization artifacts, not immutable
statements of law. Dogmatic refinement must remain possible without silently
changing the premises of an earlier case.

## Stability labels

Every new or materially revised module should declare one label in its opening
comment:

- `stable`: supported by verified primary authority and no material live
  dispute recorded by the project.
- `contested`: at least two materially different legal readings remain viable.
- `experimental`: a proposed formalization that has not completed legal and
  adversarial review.
- `deprecated`: retained only to reproduce earlier artifacts; new cases should
  use the named replacement.

The label describes the project's epistemic posture, not the binding force of
the legal source.

## Change policy

1. Corrections that do not change a declaration's meaning may be made in place.
2. A change to an axiom's antecedents, consequent, quantification, or legal
   interpretation requires a new declaration or module version.
3. Do not delete or silently rewrite a declaration used by a published case
   artifact. Deprecate it and point to the replacement.
4. Record the supporting official source, access or decision date, and the
   paper or review that motivated the change.
5. A case artifact must identify the module revision it used, preferably by
   repository commit SHA in its header.

## Naming

Prefer a descriptive new name when the legal meaning changes:

```lean
axiom regra_original_v1 : ...
axiom regra_refinada_v2 : ...
```

Use a versioned module only when several declarations change together:

```text
art_1022_cpc_v2.lean
```

Aliases may ease migration, but an alias must not hide a change in meaning.

## Case-file header

New complex case files should include:

```lean
/-
  Library revision: <git commit SHA>
  Stability assumptions:
  - art_1022_cpc: stable
  - <module/declaration>: contested | experimental
-/
```

This policy preserves old proofs while allowing the dogmatic model to evolve.
