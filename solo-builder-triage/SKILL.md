---
name: solo-builder-triage
description: >-
  Run one day of the solo-builder triage ritual: sample public GitHub for people
  producing a lot, alone, with an agent, on something that is not a commodity, and
  receiving no interaction; read the next one in the queue; and record what they are
  building, what appears to be blocking them, and who they should meet. The point is
  introduction, not cataloguing.
compatibility: >-
  Requires uv and network access to GH Archive and public GitHub. A GITHUB_TOKEN is
  recommended for the confirmation hops. Records are written as OKF Markdown in
  franklinbaldo.github.io and validated with okf-parser.
---

# One day of solo-builder triage

This skill is the ritual, not the tool. Read it, run one pass, leave one record behind.

## What we are looking for, and why

Someone is producing a great deal, alone, with an AI agent, on something that is not
a commodity — and nobody is interacting with them. No stars, no forks, no issues from
other people, no external pull requests. Often no clear product, or a product with no
users. And they keep going anyway.

The working hypothesis is that some of these people are in a **local minimum that a
single interaction could undo**. They are not receiving signal, so they do not know
that someone else is building something adjacent, so they keep building alone.

That makes the end of this pipeline an **introduction**, not a case file. The
observatory catalogues in order to connect. Everything below is shaped by that: a
record exists so that a future pass can say "these two should meet".

## What this is not

Do not filter on vocabulary. An earlier version of this work searched for
`consciousness`, `ontology`, `soul` and similar terms. That is a proxy, and it fails
in both directions: it catches ordinary ontology engineering (`diabetes-ontology-agent`)
and misses the actual subject entirely — a person writing their own BSD, their own
Lisp, or their own file system matches none of those words.

The subject is defined by **production without reception**, not by what the work is
about.

Do not diagnose. These are public artifacts and public interaction counts. Nothing
here supports a claim about anyone's mental health, and clinical vocabulary must never
appear in a record.

## The daily pass

One pass analyses **one person**. Depth is the point; the queue will still be there
tomorrow.

### 1. Refresh the queue

```bash
uv run https://raw.githubusercontent.com/franklinbaldo/skills/main/solo-builder-triage/scripts/queue.py \
  --date "$(date -u -d yesterday +%F)" --append queue.json
```

The queue accumulates across days and marks who has already been analysed. Work
top-down. Never re-analyse someone already recorded; update their record instead.

### 2. Take the next unanalysed candidate

Read their public work directly on GitHub. Their repositories, their README, their
commit history, their own site if they have one. Spend the time here — this is the
part no script does.

### 3. Write the record

One OKF card per person, in `knowledge/solo-builders/` of
`franklinbaldo.github.io`, conforming to `specs/okf-types/solo-builder.md`. Validate
with okf-parser before committing; do not hand-maintain any second index.

The fields that carry the work are these:

- **`building`** — what they are actually making, in plain terms. Not the repository
  description; what it *is*.
- **`blocking_constraint`** — what appears to be stopping them, read from the
  artifacts. A rewrite that keeps restarting. A component attempted five times. A
  README promising something the code does not reach.
- **`missing_resource`** — what that constraint implies is absent. This is the field
  that turns observation into action, and the one worth thinking hardest about. Is it
  knowledge? A tool they do not know exists? A reviewer? A single user? A peer?
- **`unlock`** — the cheap hint, if there is one. Sometimes the blockage is simply
  not visible from inside that repository, and a pointer would be enough.

### 4. Look for synergy against every prior record

This is why the fields are fixed. Read the new record against the existing ones and
ask whether two people are solving adjacent problems, or whether one has already
built what the other is stuck on.

When that happens, record an `ai-epistemic-convergence` with
`cross_pollination_candidates`. Obey its independence rule: different maintainers is
not evidence of independence. Check for shared upstream documents, copied prompts, and
prior observatory touches first.

### 5. Only then consider contact

An introduction is an `ai-epistemic-intervention` with
`intervention_kind: cross-pollination`. That type already carries the constraints that
matter — `disclosure` is required, `followup_gate` limits how often a person may be
touched, and steering belief is forbidden. Respect them. A person who does not answer
has answered.

## Criteria, and the fact that they move

The criteria below are current as of 2026-09-21 and were derived by running against
real data, not by reasoning. They will keep changing. **Record in every queue entry
which criteria version admitted it**, or in a month you will not be able to tell
whether an old entry earned its place or came from a filter since abandoned.

Current admission band, per sampled day:

| Filter | Current value | Why |
|---|---|---|
| events | 20–300 | a floor for output, a ceiling against automation |
| distinct repositories | ≤ 10 | concentration; fleets spread across ~100 |
| events on own repositories | ≥ 80% | their own work, not employment in an org |
| distinct event kinds | **≥ 3** | the strongest human/cron separator found |
| other actors on their repos | 0 | the reception signal |
| login shape | not `^[a-z0-9]{8,12}$` | disposable generated accounts |

A personal site — a repository named `<login>.github.io` — raises priority. Someone
maintaining one is choosing what to present, which is production aimed at a reader
even when there is no reader yet.

### Failure modes already measured

Each of these cost a run to discover. They are the reason the band looks the way it
does.

**Sorting search by recency destroys the sample.** Requesting `sort=updated&order=desc`
returned 23 of 24 candidates who had pushed that same day, so recency could not
discriminate at all; and two runs twenty minutes apart returned different queues, six
of twenty-one changed. Anything time-related measured on such a queue describes the
scanner.

**The top of the output distribution is spam.** Ranking by raw event volume, 297 of
the top 300 accounts passed a naive "solo" test. They were fleets: dozens of accounts
with near-identical counts across exactly 100 repositories, and ten-character random
logins. The subject is productive *for a person*, not for a machine.

**One event kind means a cron job.** Within the human band, most single-kind accounts
were scrapers committing data hourly — `auto-push`, `fail2banlist`,
`daily-ai-news-brief`. A person opens issues, cuts releases, edits a wiki. This filter
was not in any initial hypothesis and turned out to be the sharpest one.

**Reception inside a sampling window understates reception.** Zero other actors across
six sampled hours does not mean zero stars. For the few candidates that survive the
band, confirm accumulated stars, forks, contributors and third-party issues through the
API before believing the isolation.

### What must never enter the score

Activity volume, commit counts, repository counts and streaks establish nothing on
their own, and clinical vocabulary contributes nothing ever. Volume is used here only
as a *band* — a floor and a ceiling for admission — never as a rank, and never as
evidence about a person.

## Definition of done for one pass

- the queue was refreshed and the entry carries its criteria version;
- exactly one person was read directly, not summarised from the queue row;
- one OKF record exists, validated by okf-parser;
- the record was compared against all prior records;
- any synergy found is recorded as a convergence, not left in prose;
- no contact was made without an `ai-epistemic-intervention` record and its disclosure.
