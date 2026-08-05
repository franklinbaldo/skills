# skills

A collection of [Claude Code agent skills](https://docs.claude.com/en/docs/claude-code/skills) by Franklin Baldo, plus Lean 4 tooling for legal formalization.

## Install

```bash
bash skills.sh
```

Each skill is installed as a directory under `~/.claude/skills/<name>/`, with its bundled `references/` and `scripts/` copied alongside `SKILL.md`. The `<skill-dir>` placeholder in skill instructions is resolved to the installed path. Re-running the script replaces previous installs (and cleans up flat `<name>.md` files from the old install scheme).

## Skills

| Skill | Description |
| --- | --- |
| [anonimizacao-documentos](anonimizacao-documentos/SKILL.md) | Detect PII with OpenAI Privacy Filter locally or on Colab, review tagged spans, and generate deterministic anonymized Markdown copies. |
| [blank-sheet-redesign](blank-sheet-redesign/SKILL.md) | Redesign an existing artifact from a blank sheet by first principles, then reconcile it against brownfield constraints — software or legal strategy. |
| [convert-to-pdfa](convert-to-pdfa/SKILL.md) | Convert PDFs to PDF/A-1b, PDF/A-2b, or PDF/A-3b and validate the archival result. |
| [datajud](datajud/SKILL.md) | Query case metadata (docket + movements) from any Brazilian court via the CNJ DataJud public API. |
| [franklin-blog](franklin-blog/SKILL.md) | Write posts for Franklin's blog, preserving his voice via draft-and-react workflow. |
| [free-gpu](free-gpu/SKILL.md) | Run GPU workloads through Colab or Kaggle CLIs, including native Windows without WSL or administrator rights. |
| [juris-tjro](juris-tjro/SKILL.md) | Search TJRO (Rondonia court) case law via the JURIS system. |
| [legal-argument-lean](legal-argument-lean/SKILL.md) | Formalize Brazilian legal arguments (CPC-anchored vicios) in Lean 4. |
| [litebox](litebox/SKILL.md) | Adapt Linux-only CLI workflows to locked-down Windows with LiteBox when native Linux, WSL, containers, VMs, or admin installation are unavailable. |
| [llm-work-via-subagents](llm-work-via-subagents/SKILL.md) | Do bulk LLM work with parallel subagents instead of API-key scripts. |
| [meme-image](meme-image/SKILL.md) | Generate image memes via the memegen.link API for markdown content. |
| [notebooklm-processos](notebooklm-processos/SKILL.md) | Draft grounded NotebookLM question blocks to verify case-file facts before drafting. |
| [opf-finetune](opf-finetune/SKILL.md) | Fine-tune the OpenAI Privacy Filter for custom span/token classification. |
| [paddleocr](paddleocr/SKILL.md) | Run PaddleOCR locally or on a Colab GPU and export OCR results to Markdown with performance metrics. |
| [pdf-compression](pdf-compression/SKILL.md) | Compress image-heavy or scanned PDFs via downscaling and CCITT G4/JPEG re-encoding. |
| [pdf-to-markdown](pdf-to-markdown/SKILL.md) | Convert court/process PDFs (PJe, SEI) into structured Markdown per document. |
| [revisao-minutas](revisao-minutas/SKILL.md) | Adversarial risk triage of draft legal filings before they're submitted. |
| [ruff-strict-compliance](ruff-strict-compliance/SKILL.md) | Enforce zero-warning Ruff linting and formatting in Python projects. |
| [suno-curator](suno-curator/SKILL.md) | Audit and curate the Suno/blog mirror with deterministic drift checks and guarded editorial workflows. |
| [suno-profile](suno-profile/SKILL.md) | Manage Franklin's Suno profile as a whole — bio, tags, pinned songs, playlists — via an authorized write API, SEO/taste guidance, and a living curation plan. |
| [text-meme-injection](text-meme-injection/SKILL.md) | Inject text memes (EN and PT-BR) into long-form prose without breaking voice. |
| [verne-orchestration](verne-orchestration/SKILL.md) | Orchestrate Jules coding sessions via the Verne CLI (uvx verne). |
| [vibevoice-asr](vibevoice-asr/SKILL.md) | Transcribe audio through Colab CLI with BitNet on CPU or the full VibeVoice ASR 7B model on GPU. |

## Repo-level scripts

`scripts/` contains Lean 4 tooling used by the [`lean-compile.yml`](.github/workflows/lean-compile.yml) workflow: `lean_docgen_md.py` generates Markdown docs from Lean sources, and `axiom_graph.py` builds an axiom dependency graph. These support the `legal-argument-lean` skill.

## Note

Some skills (franklin-blog, meme-image, text-meme-injection) reference a `franklin-essay` skill that is kept outside this repository.
