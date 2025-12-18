# Medexamenai – Agent Overview (Start hier)

Diese Datei ist als schneller Einstieg für neue Sessions/Agenten gedacht
(Claude, Gemini, Codex, GPT). Sie listet die wichtigsten Artefakte, Scripts und
Constraints mit Pfaden im Repo.

## Harte Constraints (bitte respektieren)

- **Nicht anfassen/überschreiben:** `_OUTPUT/evidenz_antworten.json`
- **Keine inhaltlichen Rewrites** von Antworten in-place (nur Formatierung/Exports).
- **Outputs immer neu mit Timestamp** (keine Überschreibung vorhandener Dateien).
- **Keine Secrets loggen oder committen.**

## Goldstandard / Original-Quellen

- **Goldstandard-Dokumente (PDF/DOCX/ODT):** `_GOLD_STANDARD/`
- **Zusätzliche Quellen (groß):** `_FACT_CHECK_SOURCES/`
- **Weitere PDFs/Doku:** `_DOCS/`

## Zentrale Arbeitsbasis (SRS / Review)

### Enriched SRS (Arbeitsdateien)

- **Basis (Input):** `_OUTPUT/evidenz_antworten_enriched_for_srs_20251215_1529.json`
- **Fixed (konsistent, Timestamp):**
  `_OUTPUT/evidenz_antworten_enriched_for_srs_fixed_20251216_033807.json`

### Review-Queue (needs_review + needs_context)

- **Review-Queue JSON (431 Items):** `_OUTPUT/review_queue_20251216_033807.json`
- **SRS Review Cards (431 Cards):** `_OUTPUT/srs_cards_review_queue_20251216_033807.json`

## needs_context Workflow (Kontext aus Goldstandard)

### Kontext-Extrakt (aus Goldstandard)

- **Kontextblöcke + rekonstruierte Fragen:** `_OUTPUT/fragen_mit_kontext.json`
- **Kontextlose Fragenliste (historisch):** `_OUTPUT/kontextlose_fragen.json`

### Aktuelle Aufbereitung (alle 133 needs_context wurden gematcht)

- **Prepared JSON (133/133 matched):**
  `_OUTPUT/needs_context_prepared_20251216_054003.json`
  - enthält: `source_file`, `source_page`, `context_lines`, `frage_mit_kontext`,
    plus `validation_md_stub` (Template-Skelett) und Original-Antwort unverändert

- **Externe Validierungsliste (0 offen):**
  `_OUTPUT/needs_context_external_validation_20251216_054003.md`

## Lern-Exports (Anki + Dashboard)

### Anki / TSV

- **Ready (Front/Back/Tags):** `_OUTPUT/anki_ready_20251215_162246.tsv` (2090 Zeilen)
- **Review-Queue (needs_review + needs_context):**
  `_OUTPUT/anki_review_queue_20251215_162246.tsv` (431 Zeilen)

### Dashboard

- **Study Dashboard:** `_OUTPUT/study_dashboard_20251215_162246.md`
- **Daily Plan (optional):** `_OUTPUT/daily_plan_20251215_162246.json`

## Wichtige Scripts (wie reproduzieren)

- **Enrichment (SRS + Inventories):** `scripts/enrich_evidenz_for_srs.py`
- **Fix/Backfill + Review-Queue:** `scripts/fix_enriched_for_srs.py`
- **Anki/Dashboard Export:** `scripts/export_learning_materials.py`
- **needs_context Kontext-Pakete:** `scripts/prepare_needs_context_packets.py`
- **Batch-Review Pipeline (Prep → Korrektur → Web-Validierung → Finalize):**
  - `scripts/prepare_batch_review.py`
  - `scripts/batch_correct_with_reasoning.py`
  - `scripts/batch_validate_with_perplexity.py`
  - `scripts/finalize_batch_review.py`

## Roadmaps / Agent-Tasks

- **Batch-Review-Pipeline (4 Scripts, optional):** `CURSOR_AGENT_TASK.md`
  - Hinweis: Dieses Task-Dokument ist mit den Repo-Constraints abgeglichen
    (insbesondere: `_OUTPUT/evidenz_antworten.json` bleibt read-only).

## Batch-Review Pipeline (Status: umgesetzt)

Ziel: **431 Review-Items** automatisiert korrigieren (`needs_review` + `needs_context`) und
per Web-Check validieren, ohne jemals `_OUTPUT/evidenz_antworten.json` zu überschreiben.

### Aktuelle Run-Artefakte (Run-ID: `20251216_064700`)

- **Prepared Batch-Input (431 Items, lokal + Leitlinienzuordnung):**
  `_OUTPUT/batch_input_prepared_20251216_064043.json`
- **Korrigierte Antworten (431 Items):**
  `_OUTPUT/batch_corrected_20251216_064700.json`
  - Checkpoint: `_OUTPUT/batch_corrected_20251216_064700_checkpoint.jsonl`
- **Perplexity-Validierung (431 Items, summary ok/maybe/problem):**
  `_OUTPUT/batch_validated_20251216_064700.json`
  - Checkpoint (Resume, auch für Migration auf anderen Rechner): `_OUTPUT/batch_validated_20251216_064700_checkpoint.jsonl`
- **Finalisierte Arbeitsdatei (NEU, kanonische bleibt read-only):**
  `_OUTPUT/evidenz_antworten_updated_20251216_142834.json`
- **Report + Remaining Issues (verdict=problem):**
  - `_OUTPUT/batch_review_report_20251216_142834.md`
  - `_OUTPUT/batch_review_remaining_issues_20251216_142834.json`
  - Summary: `ok=285`, `maybe=79`, `problem=67` → **updated answers = 364**

### Typische Commands

```bash
# 1) Fixed enriched + review_queue (+ optional SRS review cards)
python3 scripts/fix_enriched_for_srs.py --write-srs-review

# 2) Lern-Exports (Anki + Dashboard + optional Daily Plan)
python3 scripts/export_learning_materials.py --daily-plan

# 3) needs_context Kontextpakete (prepared JSON + externe MD-Liste)
python3 scripts/prepare_needs_context_packets.py

# 4) Batch-Review Pipeline (benötigt API-Keys in ENV/.env, aber nie loggen)
python3 scripts/prepare_batch_review.py

# Korrektur (resumable, schreibt Checkpoint .jsonl)
python3 scripts/batch_correct_with_reasoning.py --resume

# Web-Validierung (resumable, schreibt Checkpoint .jsonl)
python3 scripts/batch_validate_with_perplexity.py --resume --retry-errors

# Finalisierung (schreibt NEUE Outputs mit Timestamp)
python3 scripts/finalize_batch_review.py
```

## Hinweise für Validierung (Briefing-Kompatibilität)

- In `needs_context_prepared_*.json` ist pro Item ein `validation_md_stub` enthalten,
  der dem Briefing-Template folgt (ohne „Verifizierte Antwort“ zu halluzinieren).
- Kontext wird als `context_lines` + `source_page` + `source_path` geliefert, damit
  man die Stelle im Goldstandard schnell aufschlagen kann.



