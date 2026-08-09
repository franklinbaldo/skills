# Evidence model for license-enforcement

Use this reference to keep copyright/use evidence separate from mere resemblance.

## 1. Two questions, not one

Every case has at least two independent questions:

1. **Did the target use material from the source?**
2. **If so, did that use require and lack permission?**

Strong evidence on the first does not answer the second.

## 2. Match classes

### A. Exact protected expression

Examples:

- identical or nearly identical prose beyond short/common phrases;
- identical code with meaningful expressive choices;
- distinctive examples copied with the same wording and structure;
- unique comments, typos, ordering, labels, or internal terminology surviving in the target.

This is usually strong evidence of copying, subject to provenance and lawful-use checks.

### B. Distinctive selection or arrangement

A target may reproduce a protectable combination or arrangement even when individual pieces
are common. Treat this as contextual evidence, not an automatic conclusion. Identify what is
distinctive about the combination rather than saying only that the files “look similar”.

### C. Transformation or adaptation

Look for source expression that survives paraphrase, reorganization, translation, or format
conversion. Record both similarities and meaningful differences.

### D. Attribution/provenance remnants

Repository URLs, author names, license notices, copied comments, source_path metadata, commit
hashes, or references to the source skill can strongly establish provenance. They do not by
themselves establish unauthorized use.

### E. Functional or methodological similarity

Same purpose, workflow, algorithm, sequence of abstract steps, prompt strategy, schema idea, or
agent behavior is not enough by itself. Methods, systems, procedures, ideas, and functionality
may fall outside copyright protection or may be constrained by other doctrines.

Keep this class as a signal unless another concrete legal basis exists.

## 3. Confidence is evidentiary, not judicial

Use `low`, `medium`, and `high` only to describe confidence in the observed factual link.
Do not translate them into legal probabilities or damages.

A suggested internal reading:

- `low`: plausible resemblance; multiple independent explanations remain;
- `medium`: several source-specific correspondences point to use;
- `high`: provenance or substantial source-specific expression makes independent coincidence
  difficult to explain.

## 4. Counterevidence checklist

Actively look for:

- target publication predating the alleged source;
- common upstream template or dependency;
- generated boilerplate shared by many projects;
- permissive or paid license covering the relevant version;
- written permission;
- statutory exception or mandatory user right;
- only ideas/methods/functionality being shared;
- target implementation materially independent despite similar purpose;
- source material derived from the same third party.

## 5. Provenance record

For every strong observation, preserve:

- source repository, path, commit/release, and locator;
- target repository/page/package, version, and locator;
- retrieval timestamp;
- exact excerpt or normalized hash when appropriate;
- surrounding context;
- who collected the evidence;
- any transformation performed for comparison.

Do not silently overwrite evidence when a public page changes. Append a new observation.

## 6. Legal boundary for this repository

The repository license explicitly does not claim exclusive rights over ideas, methods,
systems, procedures, facts, concepts, or other unprotected subject matter. In Brazil, this
boundary also tracks Article 8 of Law 9.610/1998, which excludes ideas, normative procedures,
systems, methods, projects, mathematical concepts, and certain other subject matter from
copyright protection as such.

The operational-use restriction matters only where the Licensor has a right or contractual
permission to grant or withhold. Do not convert the license into a claim of ownership over
knowledge itself.
