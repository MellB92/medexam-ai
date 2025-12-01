# Codex Status Report – 2025-12-01

## Aktueller Stand
- Struktur aufgeräumt in `~/Documents/Medexamenai` (Gold-Standard, Derived, Extracted, Output, Docs).
- Neue/aktualisierte Skripte:
  - `scripts/prepare_blocks.py` – Tagging, Leitlinien-Preselection, RAG-Snippets → `_OUTPUT/blocks_prepared.json`.
  - `scripts/generate_answers.py` – Budget-/Routing-Stubs, Dry-Run/LLM-Hooks, Validation-Integration.
  - Übernommene Kernmodule aus Comet: `core/spaced_repetition.py`, `core/exam_formatter.py`, `core/subject_classifier.py`, `core/auto_corrector.py`.
- Wichtigste Doku: `_DOCS/PRÜFUNGSSTRUKTUR_MÜNSTER.md` (Prüfungsablauf), README/DEV/TODO/etc. im Root.

## Offene Integration (LLM/RAG, vollautomatisiert)
- LLM-Clients noch als Platzhalter:
  - Requesty (eigene API) → primär für kostenkritische Hochqualität.
  - Anthropic (Claude) → Bedrock/Requesty.
  - AWS Bedrock → Backup für Claude.
  - Comet API → als weiterer Fallback.
  - Perplexity (über Portkey) → gezielt bei Dosis-/Leitlinienlücken, Budget-Cap.
  - OpenRouter → günstige Modelle, fallback.
  - OpenAI → nur Embeddings bei Bedarf (Cap).
- `generate_answers.py` routet aktuell stubbasiert; echter API-Call pro Provider muss ergänzt werden.

## Zu retten aus altem Projekt (priorisiert)
- HOCH: `spaced_repetition.py`, `exam_formatter.py`.
- MITTEL: `subject_classifier.py`, `auto_corrector.py`.
- RESILIENZ: `crash_handler.py`, `recovery_manager.py`, `state_persistence.py` (noch nicht kopiert).

## MedGemma (A100, €217.75 Budget) – Empfehlung
- Option C (Hybrid, bevorzugt):
  - Lokale/servierte MedGemma für Validation/Red-Team (klinische Plausi, Dosis-Check, Evidenz-Check).
  - High-precision Generierung über Claude Sonnet (Requesty/Bedrock) für Therapie/Dosis.
  - Günstige Modelle (OpenRouter) für Definition/Diagnostik ohne Dosis.

## Nächste Schritte (automatisiert)
1) API-Clients implementieren (Requesty, Anthropic/Bedrock, Comet, Perplexity via Portkey, OpenRouter) im `scripts/generate_answers.py` Hook `_generate_with_llm`.
2) Budget-Guards harden (per Provider Caps, Stop-on-cap, Logging in Output-JSON).
3) Optional: `crash_handler.py`, `recovery_manager.py`, `state_persistence.py` nach `core/` übernehmen für Resilienz.
4) MedGemma-Serving anschließen: Validator-Endpoint an `medical_validator` oder eigener Post-Validator.
5) Vollpipeline-Runner (z. B. `pipeline.py`): prepare → generate → validate → export → backup (GitHub Action).
