# MedExamAI

AI-assisted exam preparation for medical students and physicians with a focus on evidence-based answers.

This repository contains a Retrieval-Augmented Generation (RAG) pipeline, guideline ingestion utilities, question extraction, structured answer generation, and medical validation tools. It supports local embeddings and optional cloud providers via a unified API client.

Status: actively developed.


## Overview

Core capabilities:
- Build a knowledge base from medical guidelines (PDF/DOCX) and perform semantic search (RAG)
- Extract real exam-style questions from Gold-Standard documents
- Generate structured answers (5-point schema) with references and optional provider routing
- Validate medical content (dosages, ICD-10, labs, consistency) and quarantine risky outputs
- Track and limit LLM costs/budgets


## Tech stack and tooling

- Language: Python (TODO: confirm minimal supported version; currently developed with 3.9+)
- Package manager: pip via requirements.txt
- Embeddings: sentence-transformers (local by default) or OpenAI embeddings via Portkey/OpenRouter/OpenAI
- Providers/unified routing: Requesty (Bedrock/Anthropic), Portkey/OpenRouter (OpenAI/Anthropic), optional OpenAI
- Data processing: pypdf, python-docx, PyYAML, requests, numpy
- Env management: python-dotenv
- Testing: pytest (no test suite included yet; see TODO)


## Requirements

- Python 3.9+ (recommended; TODO: confirm minimum version)
- OS: macOS/Linux/Windows
- Optional provider accounts/keys if you intend to call external LLMs (see Environment variables)

Install dependencies:
```
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```


## Configuration

Global configuration lives in config.yaml. Key values (with defaults):
- base_dir: .
- gold_dir: _GOLD_STANDARD
- extracted_dir: _EXTRACTED_FRAGEN
- output_dir: _OUTPUT
- processing_dir: _PROCESSING
- derived_chunks_dir: _DERIVED_CHUNKS
- bibliothek_dir: _BIBLIOTHEK
- docs_dir: _DOCS
- rag:
  - embedding_model: text-embedding-3-small
  - embedding_dimension: 1536
  - chunk_size: 500
  - chunk_overlap: 100
  - top_k: 5
  - similarity_threshold: 0.7 (code defaults lower for recall)
  - cache_dir: .embedding_cache
  - use_openai: false (set true to prefer OpenAI embeddings)

Note: In code, RAG defaults may override config for improved recall; consult core/rag_system.py.


## Environment variables

You can place these in a .env file at the project root (python-dotenv is loaded by the unified client). Only set those you need.

Embedding/OpenAI routing for RAG:
- PORTKEY_API_KEY: use Portkey gateway for OpenAI-compatible embeddings
- OPENROUTER_API_KEY: use OpenRouter for OpenAI-compatible embeddings
- OPENAI_API_KEY: direct OpenAI embeddings

Unified API Client (LLM routing, generation):
- REQUESTY_API_KEY: key for Requesty router
- REQUESTY_MODEL: default bedrock/claude-sonnet-4-5@us-east-1 (via Requesty)
- REQUESTY_OPUS_MODEL: default anthropic/claude-opus-4-5 (via Requesty)

Budget soft caps (used by scripts/generate_answers.py and unified client):
- REQUESTY_BUDGET (default 69.95)
- ANTHROPIC_BUDGET (default 37.62)
- AWS_BEDROCK_BUDGET (default 24.00)
- COMET_API_BUDGET (default 8.65)
- PERPLEXITY_BUDGET (default 15.00)
- OPENROUTER_BUDGET (default 5.78)
- OPENAI_BUDGET (default 9.99)

Guideline location:
- LEITLINIEN_DIR: override guidelines directory (default _BIBLIOTHEK/Leitlinien)

Tip: Start with local embeddings only (no keys required). Add keys later when you want faster or higher-quality model generations.


## Typical workflows

1) Download curated guidelines (PDFs)
```
python scripts/download_guidelines.py
```
Downloads selected AWMF/DGIM/etc. guidelines into _BIBLIOTHEK/Leitlinien.

2) Build RAG index from guidelines
```
python scripts/build_rag_index.py \
  --leitlinien-dir _BIBLIOTHEK/Leitlinien \
  --output _OUTPUT/rag_knowledge_base.json \
  --chunk-size 500 --overlap 100 \
  [--use-openai]
```
By default uses local sentence-transformers. Pass --use-openai to use OpenAI-compatible embeddings if keys are set.

3) Extract real questions from Gold-Standard documents
```
python scripts/extract_questions.py --config config.yaml \
  --output _EXTRACTED_FRAGEN/echte_fragen.json
```
Scans _GOLD_STANDARD for PDFs/DOCX/TXT and extracts lines ending with question marks and typical interrogatives.

4) Generate structured answers (5-point schema) with validation
```
python scripts/generate_answers.py \
  --config config.yaml \
  --input _EXTRACTED_FRAGEN/echte_fragen.json \
  --output _OUTPUT/qa_gold_standard.json \
  [--use-openai] [--no-validation] [--dry-run] [--budget 40.0] [--verbose]
```
Uses the RAG system and UnifiedAPIClient to produce answers; can include guideline references and perform medical validation.

5) Validate existing Q&A pairs
```
python scripts/validate_medical.py --help
```
Writes results to _OUTPUT/validated/.


## CLI scripts

Most scripts provide --help with parameters and defaults:
- scripts/download_guidelines.py — download a curated set of guideline PDFs
- scripts/build_rag_index.py — parse PDFs to chunks and embed into a RAG knowledge base
- scripts/extract_questions.py — extract “real” questions from Gold-Standard sources
- scripts/generate_answers.py — generate 5-part structured answers with optional validation and budget control
- scripts/validate_medical.py — run the medical validation layer and quarantine issues
- scripts/generate_evidenz_answers.py — generate evidence-focused answers (TODO: document usage)
- scripts/extract_cases.py — extract case blocks (TODO: document usage)
- scripts/extract_dialog_blocks.py — extract dialog blocks (TODO: document usage)
- scripts/dedupe_questions.py — deduplicate extracted questions (TODO: document usage)
- scripts/match_existing_answers.py — align previous answers to current questions (TODO: document usage)
- scripts/prepare_blocks.py — preprocessing utilities (TODO: document usage)
- scripts/guideline_urls.py, scripts/guideline_urls_complete.py — guideline URL utilities (TODO: document usage)
- analyze_answer_quality.py — analyze answer quality heuristically


## Project structure

Top-level directories and files (selected):
- core/ — main library code
  - rag_system.py — RAG implementation (local or OpenAI embeddings)
  - guideline_fetcher.py — detect themes and fetch guidelines, caches and manifests
  - medical_validator.py — validation layer for clinical safety/consistency
  - unified_api_client.py — provider routing, budgets, retries
- scripts/ — CLI entry points (see above)
- _BIBLIOTHEK/, _GOLD_STANDARD/, _EXTRACTED_FRAGEN/, _OUTPUT/ — data and generated artifacts
- config.yaml — project configuration
- requirements.txt — Python dependencies
- LICENSE — MIT License

For a deeper developer guide, see DEVELOPMENT.md and QUICK_REFERENCE.md.


## Running tests

Pytest is included in requirements.txt.
```
pytest -q
```
Note: A formal test suite might not yet be present in this repository. TODO: add unit/integration tests (e.g., for question extraction and chunking).


## License

This project is licensed under the MIT License. See LICENSE for details.


## Notes and TODOs

- Confirm minimal supported Python version (README currently states 3.9+)
- Document usage for helper scripts marked as TODO
- Add example .env template with common keys and sample budgets
- Add unit tests and CI instructions

## Automated Code Reviews & Quality Gate

MedExamAI nutzt automatisierte Reviews, damit jede Pull-Request medizinische, sicherheitsrelevante und qualitative Checks besteht:
- `.github/workflows/ai-reviews.yml` ruft Claude (Anthropic) und Gemini (Google) auf und postet Feedback direkt im PR; optional über Issue-Kommentare via `@claude`, `@gemini`, `@ai-review`.
- `.github/workflows/ci.yml` bündelt Tests, Linting, Safety-Checks und erzeugt einen blockierenden "Quality Gate"-Status.
- GitHub Copilot/CodeRabbit können zusätzlich via GitHub Apps aktiviert werden (kein API-Key nötig).
- Secrets: `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`, `CODECOV_TOKEN` im Repository oder in Organisation-Settings setzen.

Siehe DEVELOPMENT.md > Git Workflow für manuelle Reviewer-Schritte und Eskalationspfade.
