# Quality E2E 0001 — text-meme-injection

This is a deliberately small end-to-end quality loop for a low-risk skill. It tests whether a skill change improves the *felt quality* of outputs, not only routing accuracy.

## Method

Four PT-BR passages were selected across distinct registers:

1. dry observational / literary essay;
2. tech/dev blog;
3. personal/confessional prose;
4. cultural criticism.

For each passage, a baseline output was generated under the pre-change skill contract and a candidate output was generated after identifying a recurring failure pattern. The full pairs live in `../evals/quality-e2e-0001.json`.

This first pilot uses the same capable model family for generation and subjective judgment. It is **not an independent blind judge** and should not be treated as statistically independent evidence. Its purpose is to discover useful quality dimensions, obvious regressions and the next benchmark design.

## Rubric

Each output is judged 1–5 on six dimensions:

- naturalness;
- voice preservation;
- timing/rhythm;
- semantic contribution;
- freshness/restraint;
- meme-texture fidelity when internet/meme texture was requested.

The sixth dimension was added during the experiment after noticing a real benchmark failure mode: optimizing only for elegant humorous prose can erase the defining meme/internet character of the skill.

## Subjective results

| Case | Baseline | Candidate | Main reason |
| --- | ---: | ---: | --- |
| memory-borges | 19/30 | 25/30 | Candidate integrates the comic turn into the Funes argument instead of appending a detachable reaction. It loses a little explicit meme signaling, which is now tracked separately. |
| framework-abstraction | 17/30 | 27/30 | `A complexidade não foi embora; ganhou onboarding` is domain-native, compresses the argument and lands as internet/dev humor without a generic reaction tag. |
| moving-boxes | 18/30 | 24/30 | Candidate extends the existing orphan-cable image and preserves intimate voice. It is less explicitly meme-coded, exposing the need for the meme-texture dimension. |
| algorithm-taste | 15/30 | 25/30 | Candidate stays inside the argument about prediction/conditioning; the baseline loanword catchphrase is highly detachable and louder than the paragraph. |

Mean subjective score:

- baseline: **17.25 / 30**
- candidate: **25.25 / 30**

The magnitude should not be interpreted as a calibrated population effect. The useful result is the repeated qualitative pattern across four different registers.

## Failure pattern discovered

The old skill was already conservative about density and safety, but its workflow made it easy to reach a catalog and append a recognizable reaction phrase after finding a slot. The resulting output can technically satisfy “meme injection” while still feeling pasted on.

Repeated baseline pattern:

```text
finished paragraph + detachable meme reaction
```

Preferred pattern:

```text
existing image/argument
  → local structural bend
  → comic/internet beat that also does semantic work
```

This produced three changes to the skill:

1. **endogenous humor first** — transform local material before consulting a catalog;
2. **integration + semantic-dividend gates** — punish detachable reactions that add no compression/contrast;
3. **lighter delivery metadata** — one best edit per slot by default; taxonomy only when it changes the user's choice.

## Benchmark self-correction

The first candidate pass exposed a second-order problem: several “better” candidates were simply better witty prose and less recognizably meme-derived. If the rubric only rewards naturalness/voice/semantics, the benchmark can optimize the skill out of its own identity.

The benchmark therefore gained **meme-texture fidelity** as an explicit dimension. This is an example of the loop improving the evaluator while it improves the skill.

The rule is not to maximize conspicuous meme signaling. The target is:

> integrated meme texture: internet-derived form/rhythm/sensibility that still belongs to the paragraph.

## What this pilot does and does not prove

It supports the hypothesis that local transformation should precede catalog lookup and that quality judging needs to distinguish “good humorous prose” from “good meme-textured prose”.

It does **not** yet prove:

- that another model/host prefers the candidate outputs;
- that human readers prefer them;
- that the improvement generalizes beyond these four passages;
- that the skill is better at block memes;
- that the same policy works in English.

## Next frontier

The next cycle should make the quality benchmark harder rather than merely add more similar passages:

1. add 4 held-out cases not used to tune this change, including one already-funny passage where the correct action is **no insertion**;
2. add one block-meme case to test setup/landing;
3. run blind pairwise judging with candidate identities hidden and, when practical, a different model/host as judge;
4. compare **skill vs no-skill** output to measure whether the skill adds value beyond a competent generic rewrite;
5. add a “generic witty prose” adversary specifically to test meme-texture fidelity;
6. preserve these four cases as a regression set rather than tuning them again immediately.

## Loop outcome

This small E2E produced all four artifacts expected by `loop-engineering`:

- **skill improvement:** endogenous humor + stronger quality gate;
- **benchmark improvement:** six-dimensional subjective rubric;
- **method innovation:** paired output-quality comparison instead of routing-only accuracy;
- **new blind spot:** good generic humor can masquerade as good meme injection.

That blind spot becomes the next frontier rather than being smoothed over by a higher headline score.
