# Free hosted LLM APIs: discovery snapshot

**Survey date:** 2026-11-18 (UTC). **Scope:** remotely hosted text/generative
LLM inference accessible via a programmable API, with no-cost access or a
plausible free trial. This is a bounded survey, **not an exhaustive statement
that no other options exist**. The agent MUST redo live discovery whenever the
skill is used; see ../SKILL.md. Official documents can change without notice.
No authenticated account-level quotas or live API calls were tested.

## Recurring zero-cost API offerings (category A unless qualified)

| Provider | Evidence and initial offer | Caveats and verification |
| --- | --- | --- |
| Google Gemini Developer API (AI Studio) | Certain models have free input/output tokens; quotas vary by model/project and are shown in AI Studio. [pricing](https://ai.google.dev/gemini-api/docs/pricing), [limits](https://ai.google.dev/gemini-api/docs/rate-limits), [billing](https://ai.google.dev/gemini-api/docs/billing) | Free tier may use content to improve products. Check region, eligible model and active per-project RPD/TPM; no hard-coded RPD. |
| GroqCloud | Free-plan inference, model-dependent limits with RPM/RPD/TPM/TPD. [limits](https://console.groq.com/docs/rate-limits) | Dashboard is authoritative for actual organization quotas; no universal RPD. |
| OpenRouter | IDs ending `:free` and `openrouter/free`; 50 RPD and 20 RPM without topping up; up to 1,000 RPD after cumulative paid credit purchase. [official free models](https://openrouter.ai/collections/free-models), [pricing](https://openrouter.ai/pricing) | 1,000 RPD tier is **not payment-free**. Failed requests count. `openrouter/free` does not promise DeepSeek. Some $0 models may require funded account. |
| Routeway | Starter advertises 200 RPD, one concurrent call, shared low-priority queue; experimental models. [plans](https://routeway.ai/) | Best-effort availability; verify model-specific `:free` eligibility and exact ID in dashboard; do not extrapolate quota to every model. |
| Cloudflare Workers AI | Workers Free includes 10,000 Neurons/day, not a fixed request count; overage fails without paid plan. [pricing](https://developers.cloudflare.com/workers-ai/platform/pricing/) | Some models explicitly require paid access; check individual catalog. [model restriction announcement](https://developers.cloudflare.com/changelog/post/2026-07-28-models-require-workers-paid/). |
| Cohere evaluation keys (B) | Free trial/evaluation API keys; docs cite 1,000 calls/month and Chat rate limits per model. [FAQ](https://docs.cohere.com/v2/docs/cohere-faqs), [rate limits](https://docs.cohere.com/v1/docs/rate-limits) | Evaluation/non-production limitations; check model terms and endpoint, do not treat as unrestricted production free tier. |
| NVIDIA build endpoints (B) | Developer documentation describes free hosted NVIDIA Endpoints accessible from build.nvidia.com. [NVIDIA AI Workbench](https://docs.nvidia.com/ai-workbench/how-to/ai-workbench-build-assistant/) | Free prototyping terms and credits/limits not quantified in retrieved official source; confirm account limits and model before selection. |

## Conditional, promotional, or changed offers: do not rank as guaranteed free

| Provider | Status on survey date | Evidence |
| --- | --- | --- |
| Cerebras Inference | **C**: current provider pricing describes $5 one-time credit upon adding a valid payment method, expiring after 30 days. An older docs page advertises a $0 tier: inconsistent, so do **not** claim an enduring free API without current dashboard confirmation. | [current pricing](https://www.cerebras.ai/pricing), [older documentation](https://inference-docs.cerebras.ai/support/pricing) |
| Hugging Face Inference Providers | **D/changed**: newer main docs say free accounts have **no** monthly included credits, older stable docs still say $0.10/month. Resolve by current account billing page; do not assume free credits. | [current main pricing](https://huggingface.co/docs/inference-providers/main/pricing), [older pricing](https://huggingface.co/docs/inference-providers/pricing) |
| Mistral API | **D/conflicting**: current usage-limits page says Free mode does **not** include API access, despite older Experiment communications and another quickstart describing free API. Confirm in current console before listing as active. | [current limits](https://docs.mistral.ai/admin/billing-usage/usage-limits), [prior announcement](https://mistral.ai/news/mistral-vibe-2-0/) |
| SambaNova Cloud | **D/conditional**: pricing page says free plan requires adding payment method and purchasing credits to run first requests; community discussion describes per-model free limits. Account-level verification required. | [plans](https://cloud.sambanova.ai/plans), [community](https://community.sambanova.ai/t/the-daily-limit-is-not-resetting-after-24-hours/1704/3) |
| GitHub Models | **D/retired**: inference API retired 2026-07-30; exclude from candidate list. | [GitHub announcement/documentation](https://docs.github.com/en/github-models) |

## Other leads to check anew rather than assert as free

Together AI, Fireworks AI, DeepInfra, Novita, SiliconFlow, Alibaba Cloud
Model Studio/Qwen, Z.ai/GLM, Baidu Qianfan, AI21, Hyperbolic, Baseten,
Scaleway, OVHcloud AI Endpoints, Modal and Replicate may offer trial credits,
special free models, region-specific programs or promotions. No sufficiently
current official no-cost API entitlement was established for all of these in
this survey. Discover/re-evaluate, then source every claimed quota. A free
**website/chat app** is not equivalent to a free **developer API**. Do not
assume the official DeepSeek API is free because an intermediary has a free
DeepSeek endpoint.

## Freshness checklist and delta log

At **every material use** search: `free LLM inference API 2026`,
`new free model API providers [current month]`, `[provider] free API pricing
rate limits`, `[desired model] free endpoint`, and official release notes.
Also inspect a maintained community directory such as
[free-inference](https://github.com/surendranb/free-inference) **for leads
only**, checking each lead against provider-owned documentation.
Compare with this inventory and explicitly report added/removed/repriced
offers. Check terms for credit-card requirements, hard spending stops,
model IDs, geographic limitations, data retention, commercial production
permission and renewal cadence. Never create payment-bearing resources
merely to validate a listing.

Next confirmed review: **not yet performed**. Update this date and add a
dated delta with official URLs when new evidence is actually gathered.
