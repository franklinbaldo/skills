---
name: free-llm-api
description: >-
  Find, verify, compare and use no-cost hosted LLM inference APIs, selecting
  a genuinely free model and account quota without silently spending money.
  Use for unattended jobs, API integrations, OpenAI-compatible endpoints,
  prototyping, and DeepSeek or other open model access; recheck new providers
  and changed terms before each material selection.
compatibility: >-
  Requires web access for live offer verification and optionally API keys
  supplied through the user's secret store. Never requires payment.
---

# Free LLM via API

Choose a **currently free** hosted inference route, not simply a low-cost model.
The inventory in [references/provider-survey.md](references/provider-survey.md)
is a dated *discovery snapshot*, not a guarantee of availability.

## Mandatory live discovery (every selection, not only when the file ages)

1. Record today's date. Search the web for **new free LLM API providers or free
   models announced since 2026-11-18** and for changes to listed providers.
   Include official pricing, rate limits, model catalogs, changelogs, and at
   least one independent, recently maintained free-inference directory as a
   discovery lead. Search broad terms plus task-specific models (DeepSeek,
   coding, vision, reasoning, embeddings). Do not treat the directory as proof.
2. Open the provider's **official** current pricing, limits, API-key and model
   endpoint documentation. Reconcile conflicting pages, favor the newest
   authoritative publication and account dashboard; mark unresolved conflicts.
   Check country restrictions, sign-up/payment method, free-plan eligibility,
   commercial-use restrictions, retention/training and input-data rules.
3. Confirm the exact **model ID**, endpoint, zero price for both input/output,
   request/token limits (RPM/RPD/TPM/TPD), quota scope (key/account/project),
   reset, concurrency, uptime and billing behavior when free quota runs out.
   A $0 listing can still require a funded account. No fixed model identifier
   may be assumed to remain free.
4. Classify: **A** recurring free API allowance without payment;
   **B** free evaluation key or limited non-production use; **C** one-time
   trial/promotional credits or free use requiring paid enrollment;
   **D** unconfirmed, unavailable, retired or changed terms. Prefer A.
5. Report dated source URLs, caveats and the selected provider/model. On a
   newly discovered offer, add it to the inventory in a follow-up contribution
   with official evidence; do not silently rewrite this repository without
   authorization. If live research is unavailable, say inventory is stale
   and require user confirmation before any spend-capable request.

## Selection and integration

- Default ranking: no card/no billing > recurring quota > task fit and
  quality > data policy > rate/token capacity > latency. If the user explicitly
  needs DeepSeek, **verify a DeepSeek endpoint**; a generic free router does
  not guarantee that model.
- For tasks inside an agent harness with subagent support, consult
  [llm-work-via-subagents](../llm-work-via-subagents/SKILL.md): interactive
  batch work may not need an API. Use this skill when the caller actually
  needs external API access, a reproducible automated pipeline, or a provider.
- Never enroll in billing, purchase credits or switch to a paid model without
  explicit authorization. Prefer non-billable free projects and hard caps.
  For a metered account, confirm auto-billing is disabled or a zero-spend
  hard stop is enforced before making requests.
- Obtain API keys using the provider's official console. Keep them in an
  existing secret manager or environment variable, never commits, URLs,
  screenshots, logs or chat. Never print the full key.
- Use a small single-request smoke test only after a key is available and the
  current endpoint is confirmed free. Do not claim tested API access from
  documentation alone. Verify returned model, status, tokens and quota.
- Respect 429 and Retry-After; use bounded jittered backoff, an overall
  request/token budget, queueing and idempotency. Do not rotate accounts/keys
  to bypass restrictions. A failed request may count against quota.
- If free capacity is exhausted: stop, notify the user or explicitly switch
  to another **verified free** route that meets the data policy. Never
  silently fall back to a paid endpoint.

## OpenAI-compatible API example (only after current verification)

```bash
# The account's verified free model ID must be supplied explicitly.
: "${FREE_LLM_BASE_URL:?}"
: "${FREE_LLM_MODEL:?}"
: "${FREE_LLM_API_KEY:?}"
curl --fail-with-body --silent --show-error \
  "${FREE_LLM_BASE_URL%/}/chat/completions" \
  -H "Authorization: Bearer ${FREE_LLM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(printf '{"model":"%s","messages":[{"role":"user","content":"Reply OK"}],"max_tokens":16}' "$FREE_LLM_MODEL")"
```

This example assumes a compatible `/chat/completions` endpoint. Google
Gemini, Cloudflare and others may need their own path/auth/payload; follow
their current official API documentation. Do not embed real keys.

## Answer contract

Provide: (1) date of fresh check, (2) newly found candidates and changed
offerings since the snapshot, (3) provider/model/endpoint with official links,
(4) category A/B/C/D and precise limits or 'account-dependent/unconfirmed',
(5) cost and payment-method risk, (6) data-handling caveat, (7) test status
'not tested / tested with user key', (8) next action. Do not imply exhaustive
coverage of all internet providers; the search is best-effort and repeatable.

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction
effect and friction/workarounds. Routine success stays ephemeral. For actionable
learning, search existing `franklinbaldo/skills` issues and update a matching
issue or open a sanitized **Skill use feedback** issue. Never publish secrets
or confidential material to report skill behavior.
