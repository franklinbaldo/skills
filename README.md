# skills

A collection of [Claude Code agent skills](https://docs.claude.com/en/docs/claude-code/skills) by Franklin Baldo, plus Lean 4 tooling for legal formalization.

## Install and use

Use Vercel's open `skills` CLI as the canonical distribution/runtime boundary for this repository. Do not add a repository-specific installer, agent registry, path-mapping layer, or competing skills runtime when `npx skills` already provides that capability.

Install from this repository:

```bash
npx skills add franklinbaldo/skills
```

Install a specific skill:

```bash
npx skills add franklinbaldo/skills --skill software-review
```

Target a specific supported agent when needed:

```bash
npx skills add franklinbaldo/skills --skill software-review --agent claude-code
```

Use a skill without making installation semantics part of this repository:

```bash
npx skills use franklinbaldo/skills --skill software-review --agent claude-code
```

`npx skills` owns discovery, selection, agent-specific installation paths, symlink/copy behavior, updates, removal, and supported-agent integration. This repository owns the skills themselves, their tests/evals, and repository-specific analysis. See [`okf-agent-skills/references/tooling-boundary.md`](okf-agent-skills/references/tooling-boundary.md).

## Skills

| Skill | Description |
| --- | --- |
| [anonimizacao-documentos](anonimizacao-documentos/SKILL.md) | Detect PII with OpenAI Privacy Filter locally or on Colab, review tagged spans, and generate deterministic anonymized Markdown copies. |
| [blank-sheet-redesign](blank-sheet-redesign/SKILL.md) | Redesign an existing artifact from a blank sheet by first principles, then reconcile it against brownfield constraints — software or legal strategy. |
| [brazilian-web-design](brazilian-web-design/SKILL.md) | Research Brazilian visual culture, consult the Cobogó OKF corpus, and translate references into concrete, accessible interface grammar without ornamental brasilidade. |
| [cobogo-design-review](cobogo-design-review/SKILL.md) | Review interfaces and PRs against Cobogó canon, grammar, accessibility and consumer-specific identity, distinguishing structural brasilidade from superficial motifs. |
| [convert-to-pdfa](convert-to-pdfa/SKILL.md) | Convert PDFs to PDF/A-1b, PDF/A-2b, or PDF/A-3b and validate the archival result. |
| [datajud](datajud/SKILL.md) | Query case metadata (docket + movements) from any Brazilian court via the CNJ DataJud public API. |
| [franklin-blog](franklin-blog/SKILL.md) | Write posts for Franklin's blog, preserving his voice via draft-and-react workflow. |
| [free-gpu](free-gpu/SKILL.md) | Run GPU workloads through Colab or Kaggle CLIs, including native Windows without WSL or administrator rights. |
| [juris-tjro](juris-tjro/SKILL.md) | Search TJRO (Rondonia court) case law via the JURIS system. |
| [legal-argument-lean](legal-argument-lean/SKILL.md) | Formalize legal arguments in Lean 4 only when doing so reduces a concrete structural uncertainty, with explicit dependency auditing and stopping rules. |
| [license-enforcement](license-enforcement/SKILL.md) | Audit public evidence of operational skill use, build provenance-rich compliance cases, and prepare guarded licensing outreach with mandatory human approval before external action. |
| [litebox](litebox/SKILL.md) | Adapt Linux-only CLI workflows to locked-down Windows with LiteBox when native Linux, WSL, containers, VMs, or admin installation are unavailable. |
| [llm-work-via-subagents](llm-work-via-subagents/SKILL.md) | Do bulk LLM work with parallel subagents instead of API-key scripts. |
| [loop-engineering](loop-engineering/SKILL.md) | Engineer self-improving loops in which skills, benchmarks, evaluation methods, coverage, and neighboring skills co-evolve from evidence. |
| [meme-image](meme-image/SKILL.md) | Generate image memes via the memegen.link API for markdown content. |
| [notebooklm-processos](notebooklm-processos/SKILL.md) | Turn large case files into grounded, provenance-preserving evidence for the next legal or institutional decision. |
| [okf-agent-skills](okf-agent-skills/SKILL.md) | Inspect and govern Agent Skills through a derived OKF relational/graph projection while keeping Agent Skills as the source format. |
| [opf-finetune](opf-finetune/SKILL.md) | Fine-tune the OpenAI Privacy Filter for custom span/token classification. |
| [paddleocr](paddleocr/SKILL.md) | Run PaddleOCR locally or on a Colab GPU and export OCR results to Markdown with performance metrics. |
| [pdf-compression](pdf-compression/SKILL.md) | Compress image-heavy or scanned PDFs via downscaling and CCITT G4/JPEG re-encoding. |
| [pdf-to-markdown](pdf-to-markdown/SKILL.md) | Convert court/process PDFs (PJe, SEI) into structured Markdown per document. |
| [revisao-minutas](revisao-minutas/SKILL.md) | Review existing legal and institutional drafts for concrete risk, missing context, unintended commitments, and readiness to sign, issue, or file. |
| [ruff-strict-compliance](ruff-strict-compliance/SKILL.md) | Enforce zero-warning Ruff linting and formatting in Python projects. |
| [software-review](software-review/SKILL.md) | Review PRs and RFCs for reproducible defects, broken invariants, false-green gates, and architecture issues calibrated to the real application. |
| [suno-curator](suno-curator/SKILL.md) | Audit and curate the Suno/blog mirror with deterministic drift checks and guarded editorial workflows. |
| [suno-profile](suno-profile/SKILL.md) | Manage Franklin's Suno profile as a whole — bio, tags, pinned songs, playlists — via an authorized write API, SEO/taste guidance, and a living curation plan. |
| [text-meme-injection](text-meme-injection/SKILL.md) | Inject text memes (EN and PT-BR) into long-form prose without breaking voice. |
| [verne-orchestration](verne-orchestration/SKILL.md) | Orchestrate Jules coding sessions via the Verne CLI (uvx verne). |
| [vibevoice-asr](vibevoice-asr/SKILL.md) | Transcribe audio through Colab CLI with BitNet on CPU or the full VibeVoice ASR 7B model on GPU. |

## Repo-level scripts

`scripts/` contains Lean 4 tooling used by the [`lean-compile.yml`](.github/workflows/lean-compile.yml) workflow: `lean_docgen_md.py` generates Markdown docs from Lean sources, and `axiom_graph.py` builds an axiom dependency graph. These support the `legal-argument-lean` skill.

## License

This repository is distributed under the [Skill Use License 0.1](LICENSE.md): it is **source-available, not Open Source**. Reading, inspection, and good-faith evaluation are permitted; operational use of the licensed skills/material requires a separate paid license unless a stated exception applies.

The machine-readable policy is in [`licensing/policy.yaml`](licensing/policy.yaml). The [`license-enforcement`](license-enforcement/SKILL.md) skill is deliberately usable without charge for self-audit, license inquiries, and compliance responses under the License's Compliance Skill Exception.

The license does not claim ownership of abstract ideas, methods, systems, facts, or other subject matter that applicable law leaves unprotected. See the License for the exact scope and exceptions.

## Note

Some skills (franklin-blog, meme-image, text-meme-injection) reference a `franklin-essay` skill that is kept outside this repository.
