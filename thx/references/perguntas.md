# Writing questions for decision models

These practices come from the official guides of the decision APIs (Google,
OpenAI, HAL-X, Liquid) and from the `ies` calibration runs. The sources are
listed at the end. Where the vendors disagree, the difference is noted.

## Split the work: code first, model last

- **Compute in code everything code can decide.** Google says it outright:
  do arithmetic in code and pass the result. For source code, that means the
  AST answers "is it constructed?", "does it carry a field?" and "is its only
  field another error?". The model sees those answers as data in the state and
  is asked only what needs judgement.
- **Turn facts into a verdict with a rule in code.** Never ask the model "what
  should be done?": that is your policy, not a fact in the input.
- **Check the extractor before the model.** In `ies`, a bug that cut
  production code after the first `#[cfg(test)]` made the model look right
  for the wrong reason on 3 of 14 items.

## The state

- **Send only what the questions need.** Unrelated content lowers accuracy
  (Google). For code: the declaration and the construction sites, not the
  whole file.
- **Prefer JSON with named fields.** It keeps fields unambiguous (HAL-X).
  Refer to the fields by name in the instructions, for example "Read
  `condition_before_creation`".
- **Treat the input as untrusted** (Google): text in the state can try to
  steer the answer.
- **Put the options in the criteria, not in the state** (HAL-X).

## The instructions

- **Write the full question in `instructions`.** The model never sees the
  question key (Google).
- **Ask one thing per question, in the positive form** (Copes).
- **Ask about something observable,** for example "ignore shadows and damage
  to the packaging" (OpenAI).

## The criteria

- **`noul`: describe both sides.** Give `criteria: {"true": ..., "false": ...}`
  with a concrete example of each. A bare yes/no question leaves the boundary
  to the model.
- **`choice`: describe each option, don't just name it** (HAL-X, OpenAI). Add
  an escape option such as `other` (all vendors). Google sorts option keys
  alphabetically and breaks ties toward the first key, so a key named
  `none_of_the_above` does not stay last. Name it for what it means.
- **`score`: order the levels from lowest to highest and give each one
  distinct criteria.** Use 2 to 10 linear levels: an exponential scale skews
  the probability-weighted score (Google, Copes).
- **Questions do not see each other** (Google). If one decision depends on
  another's answer, send a second request. THX-02 is the exception: it reads
  questions of the same type with the same criteria together.

## Thresholds and confidence

- **Choose the threshold on a few hundred labelled examples from your own
  traffic** (HAL-X, OpenAI, Copes: "don't copy 0.7 from here"). Weigh the
  cost of a false positive against that of a false negative. A 14-item key is
  a smoke test, not a threshold.
- **Threshold on the winning option's probability.** "Confidence" means
  different things: Google uses the top probability, while THX-02 uses the
  distance above uniform.
- **Send whatever falls below the threshold to a person.**
- **Compute the ceiling.** First count the labels your questions plus rule
  could reach with perfect answers. If the ceiling is low, a question is
  missing; no model will fix it.

## THX-02 specifics

- **`tta=4`** averages each `choice` over four option orders, at about twice
  the latency. Use it when option order might bias the answer.
- **`think="auto"`** helps arithmetic, dates and thresholds. Keep
  `think=False` for routing and tagging, where thinking costs 1 to 3 points.
- **Limits:** 64 questions per request, 2 to 255 options, a 32k-token
  training context.

## Sources

- [OpenAI — Decisions guide](https://developers.openai.com/api/docs/guides/decisions)
- [Google AI Studio — Decisions API](https://aistudio.google.com/docs/decisions-api)
- [Google blog — Gemini Decisions API](https://blog.google/innovation-and-ai/technology/developers-tools/gemini-decisions-api/)
- [HAL-X-AI/THX-02 model card](https://huggingface.co/HAL-X-AI/THX-02)
- [HAL-X API reference](https://api.hal-x.ai/docs/thx-02)
- [Liquid — Decisions guide](https://docs.liquid.ai/api/guides/decisions)
- [Flavio Copes — How to use the Gemini Decisions API](https://flaviocopes.com/gemini-decisions-api/)
