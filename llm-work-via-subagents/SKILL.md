---
name: llm-work-via-subagents
description: >-
  When you (an agent that can spawn subagents) are about to write a script that calls an
  LLM API with a key to do BULK or REPEATED LLM work — labeling, classifying, extracting,
  reviewing, summarizing, or judging across many items, or running an evaluator ensemble —
  stop and spawn parallel subagents instead. Spawning is more efficient, needs no API key,
  and carries no rate-limit/retry/cost plumbing. Trigger on ANY batch or iterative LLM task,
  even with no ML, annotation, or training involved: "label this corpus", "classify these
  records", "review these documents", "extract fields from these files", "summarize each of
  these", "have a few models check this", "process these messages/emails/transcripts". The
  smell to catch is "I'll write a Python loop that calls the API for each item" — that is the
  signal to use subagents. Does NOT apply to a single one-off LLM call, or to genuinely
  unattended very-large batch jobs (see the exception below).
---

# Do LLM work by spawning subagents, not by scripting an API

## The default

You are an agent that can spawn subagents. When a task needs an LLM applied to **many
items** or in **several distinct roles**, the instinct to "write a script that calls the
Anthropic (or any) API with a key, looping over the items" is almost always the wrong tool.
Spawn subagents instead.

Why subagents win:

- **No API key, no plumbing.** The script approach reinvents auth, rate-limit handling,
  retries/backoff, cost accounting, and error recovery — all of which subagents give you
  for free.
- **Parallel by construction.** N subagents run concurrently; a script loop is serial
  unless you also build concurrency.
- **Natural orchestration.** You stay the orchestrator: dispatch work, collect structured
  results, merge. No separate process to babysit.
- **It's what the agent harness is for.** Reaching for a raw API call from inside an agent
  that already spawns agents is working against the grain.

## The two shapes

**1. Shard a bulk task across parallel subagents.** Split the items into batches; spawn one
subagent per batch with the same brief; collect and merge. Use for: labeling/annotating a
corpus, classifying or tagging many records, extracting fields from many documents,
summarizing many items, processing many messages/emails/transcripts.

**2. One subagent per role (ensembles / multi-perspective).** When you want several
*different* takes on the same input — an evaluator ensemble, multi-rater review, a
panel of personas — spawn one subagent per role, each with its **own brief**, in parallel.
Differentiated briefs make their outputs (and errors) decorrelate, which is the whole point
of an ensemble. Use for: judging/verifying labels, bulk QA, red-team vs. defend, scoring
against multiple rubrics.

In both shapes the subagents return **structured output** (JSON, tagged spans, verdicts)
and the orchestrator does the merge/validation. Subagents should not need shared mutable
state; give each a self-contained brief and let it return its piece.

## The one real exception

Write a script with a programmatic API call when the job is **unattended, very-large
batch** at a scale where spawning is impractical — tens of thousands of items, scheduled
CI runs, or pipelines that must be reproducible without an agent in the loop. There, a
scripted call (often to a cheaper/smaller model) is the right tool. For interactive work,
hundreds-to-low-thousands of items, and anything needing judgment or an ensemble,
subagents are strictly better. When in doubt at human scale, spawn.

## What this looks like

- "Label these 2,000 documents with categories X/Y/Z" → shard into batches, one labeling
  subagent per batch, merge. NOT a `for doc in docs: client.messages.create(...)` script.
- "Have a strict reviewer, a blind re-labeler, and an adversarial checker verify this gold
  set" → three subagents, three briefs, in parallel. NOT one script with three prompts.
- "Summarize each of these 300 transcripts into a newsletter blurb" → shard across
  subagents. NOT an API loop.
- "Translate this one paragraph" → just do it inline; not a batch, no subagents needed.
- "Re-tag this 40k-row dataset nightly in CI" → scripted batch call (the exception).
