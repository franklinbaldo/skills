---
name: license-enforcement
description: >-
  Audit public evidence of operational use of Franklin Baldo's licensed skills, distinguish
  signals from verified use, check whether a license may already exist, build a provenance-rich
  evidence bundle, and prepare compliance outreach or a retroactive licensing offer. Never
  treat similarity as proof, never invent a debt, and require explicit human approval before
  contacting a target, sending a formal notice, or escalating legally.
when_to_use: >-
  Use when the rights holder wants to investigate whether a company, repository, product,
  agent, or workflow may be using material from franklinbaldo/skills beyond the permissions
  of Skill Use License 0.1, or when a user wants to self-audit their own compliance.
---

# Enforce a skill license without turning suspicion into a verdict

This skill operationalizes the repository's licensing policy. Its job is not to maximize the
number of accusations or invoices. Its job is to turn a weak public signal into a reviewable
record while preserving the distinction between:

```text
similarity
  → evidence of use
  → scope of protected material
  → license status
  → actionable concern
  → human decision
```

The controlling legal text is [`../LICENSE.md`](../LICENSE.md). The machine-readable policy is
[`../licensing/policy.yaml`](../licensing/policy.yaml). If they conflict, the legal text wins.

Read [`references/evidence-model.md`](references/evidence-model.md) before classifying a case.
Read [`references/outreach.md`](references/outreach.md) before drafting any external message.

## Hard boundaries

1. **Public evidence by default.** Do not bypass authentication, evade access controls, use
   stolen credentials, impersonate someone, scrape in violation of an explicit technical
   barrier, or obtain private material merely to prove a licensing case.
2. **Ideas are not enough.** Similar concepts, workflows, methods, structures, or functionality
   may be legally unprotected. Look for protectable expression or another concrete legal basis.
3. **Similarity is a signal, not a conclusion.** Independent creation, common upstream
   conventions, generated boilerplate, prior versions, statutory exceptions, or a separate
   license may explain a match.
4. **Unknown license status is not unlicensed status.** A target may hold a private agreement
   that is not discoverable publicly.
5. **Do not manufacture a debt.** A public price, quote, or proposed retroactive license does
   not automatically become an amount already owed merely because use appears unauthorized.
6. **No autonomous adverse action.** Explicit human approval is required before any external
   contact, formal notice, collection step, takedown request, legal filing, or public accusation.
7. **Preserve exculpatory evidence.** Record facts that weaken the case with the same care as
   facts that strengthen it.

## Workflow

### 1. Freeze the rights-side reference

Identify exactly what material is allegedly being used:

- repository and path;
- skill name;
- version, tag, or commit SHA;
- publication date if material;
- license version attached to that version;
- distinctive passages, scripts, schemas, examples, or arrangement alleged to be copied.

Do not compare a target against a moving `main` branch and later describe the result as though
it proved use of a particular historical version.

### 2. Collect the target-side public evidence

Record the target artifact with stable locators whenever possible:

- repository commit or release;
- package version;
- archived public page;
- marketplace listing;
- product documentation;
- public prompt/skill file;
- public demonstration that exposes relevant implementation detail.

Capture retrieval time and enough surrounding context to assess whether a match is meaningful.
Do not reduce evidence to decontextualized snippets.

### 3. Classify each match

Use the evidence model and classify observations rather than jumping directly to infringement.
Useful match types include:

- exact or near-exact protected prose;
- distinctive selection/arrangement reproduced with small edits;
- code or script correspondence;
- copied examples, schemas, or resource layout;
- attribution or notice remnants;
- references to the original skill/repository;
- functional similarity only;
- idea/method similarity only.

The last two are weak or non-actionable on copyright alone.

### 4. Build an evidence bundle

Create one case record containing at least:

```yaml
case_id: <stable-id>
target:
  name: <entity-or-project>
  artifact: <public-locator>
  observed_at: <timestamp>
source:
  repository: franklinbaldo/skills
  commit: <sha>
  skill: <skill-name>
  license_id: Skill-Use-License-0.1
observations:
  - kind: <match-kind>
    source_locator: <path-and-lines-or-hash>
    target_locator: <stable-public-locator>
    confidence: <low|medium|high>
    supports_use: true
    supports_protected_expression: true
counterevidence: []
license_status: <licensed|unlicensed|unknown>
classification: <signal|verified_use|actionable_concern>
```

Hashes are useful for integrity, not as substitutes for human-readable provenance.

### 5. Check license status

Before classifying a case as an actionable concern, check records available to the rights
holder for a paid Operational License, prior written permission, contributor agreement, or
other authorization that may cover the use.

If no authoritative licensing record is available, use `unknown`, not `unlicensed`.

### 6. Apply the three-stage evidentiary threshold

**Signal** means there is enough resemblance or context to justify inspection, but not enough
to conclude that protected material was used.

**Verified use** means the evidence supports actual copying, adaptation, embedding, or execution
of Licensed Material with sufficient confidence for internal review. This still does not prove
that the use is unauthorized.

**Actionable concern** means verified use plus evidence that the use is operational and no
known license or exception appears to cover it, after checking plausible lawful explanations.
This remains an internal classification, not a judicial conclusion.

### 7. Stop for human review

Before contacting anyone, present a compact decision packet:

- strongest evidence;
- strongest counterevidence;
- exact protected material at issue;
- why the use appears operational rather than evaluative;
- license status and how it was checked;
- unresolved legal or factual questions;
- proposed next action.

Ask for an explicit decision to contact, close, or investigate further.

### 8. Start with a compliance inquiry

If approved, begin with a neutral inquiry rather than an accusation. The initial objective is
to resolve license status and offer a path to regularization.

A good first contact says, in substance:

- what public artifact was observed;
- what source material it appears to incorporate;
- that the public repository license reserves Operational Use for paid licensing;
- that the sender may be missing a private authorization;
- how the recipient can identify an existing license or discuss regularization;
- a reasonable response window.

Do not threaten litigation in the first message merely to increase response rate.

### 9. Prepare a retroactive licensing offer

If the rights holder wants to regularize past use, draft an offer that clearly separates:

- prospective Operational License terms;
- scope of any retroactive release or settlement;
- price or pricing metric supplied by the rights holder;
- covered period and covered skills;
- attribution, confidentiality, or other negotiated terms;
- whether acceptance resolves the identified past use.

Never invent a price. If the current policy says `quote_required`, ask the rights holder for the
commercial terms before producing a monetary demand.

### 10. Escalate only by explicit decision

If an inquiry fails or the target disputes the matter, update the evidence bundle with the
response. A formal extrajudicial notice may then be drafted for human/legal review.

The agent may assemble chronology, provenance, correspondence, claimed rights, counterarguments,
and requested resolution. It must not autonomously file suit, send a takedown, publish an
accusation, or represent that a court has determined infringement.

## Self-audit mode

A user may invoke this skill under the License's Compliance Skill Exception to determine whether
their own workflow requires an Operational License.

In self-audit mode:

1. identify which repository material is loaded or incorporated;
2. distinguish evaluation from productive use;
3. identify whether the use depends on copyrightable material rather than merely an idea or
   method learned from it;
4. check any existing written license;
5. if a paid license appears necessary, prepare a concise inquiry to the Licensor.

Do not turn self-audit into a presumption against the user.

## Definition of done

An enforcement investigation is complete when:

01. both source and target artifacts are frozen to stable versions or locators;
02. each material match is classified by evidentiary type;
03. idea/method similarity is not treated as protected expression;
04. plausible lawful explanations and counterevidence are recorded;
05. license status is checked and `unknown` remains distinct from `unlicensed`;
06. the case is classified as signal, verified use, or actionable concern;
07. no external communication occurs without explicit human approval;
08. any monetary proposal uses terms supplied or approved by the rights holder;
09. correspondence and subsequent evidence are appended to the case record; and
10. legal escalation, if any, is handed to a human decision-maker with a provenance-rich
    packet rather than an agent-generated verdict.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction effect, and any friction/workaround. Routine success stays ephemeral. If there is actionable learning, search `franklinbaldo/skills` issues and update a matching issue or open a sanitized **Skill use feedback** issue. Never publish secrets or private/confidential data merely to report feedback.
