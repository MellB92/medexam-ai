# REPO_ORGANISATION

## Zweck

Dieses Dokument beschreibt die empfohlene Ordner- und Dateiorganisation für das Repository, Namenskonventionen, Guardrails sowie ein risikoarmes Vorgehen zur Migration existierender Artefakte. Ziel: klare funktionale Trennung, reproduzierbare Zeitreihen-Artefakte und verlässliche Regeln für kanonische Dateien und Outputs.

---

## Grundprinzipien / Ziele

- Funktionale Bündelung: Ordner nach Funktion (Code, Daten, Doku, Outputs).
- Zeitreihen-Artefakte: Runs/Reports werden nach Datum/Run-ID strukturiert.
- Eindeutige Benennung: `snake_case`, Zeitstempel `_YYYYMMDD_HHMMSS` vor der Dateiendung.
- Temporäre Artefakte: Präfix `tmp_rovodev_` (lokal, in `.gitignore`).
- Guardrails: Kanonische Dateien (z. B. canonical/evidenz_antworten.json) sind read-only im Repo; Outputs immer mit Timestamp; keine Secrets im Repo.

---

## Top-Level Struktur (empfohlen)

```
core/
scripts/
  batch_pipeline/
  enrichment/
  data_prep/
  validation/
  utilities/
prompts/
  agents/
  validation/
docs/
  guides/
  status/
  analysis/
_OUTPUT/
  canonical/
  batch_runs/
  reports/
  learning_exports/
  review_queue/
  run_reports/
  md_converted/
  tmp/
_FORENSIK/
_FACT_CHECK_SOURCES/
_ARCHIVE/
```

> Hinweis: `core/` bleibt wie bisher; `scripts/` fasst Pipelines zusammen.

---

## Detailliertes Verhalten für `_OUTPUT/`

- canonical/: `evidenz_antworten.json` – niemals überschreiben; Updates nur als neue Timestamp-Datei.
- batch_runs/<YYYYMMDD>/ oder batch_runs/<RUN_ID>/: pro Run Unterordner, Dateien mit Zeitstempel.
- learning_exports/<YYYYMMDD>/: Lernexporte (TSV, Dashboards) mit Zeitstempel.
- reports/<YYYYMMDD>/: Status-Reports/Analysen.
- review_queue/: `review_queue_YYYYMMDD_HHMMSS.json` etc.
- tmp/: nur lokal, `tmp_rovodev_*`, in `.gitignore`.

---

## Namenskonventionen

- Dateinamen: `snake_case`, keine Leerzeichen/Sonderzeichen.
- Zeitstempel: `_YYYYMMDD_HHMMSS` vor der Extension, z. B. `batch_review_report_20251216_142834.md`.
- Temporär: `tmp_rovodev_*`.
- Canonical: `canonical/evidenz_antworten.json` bleibt read-only.

---

## Vorgeschlagene Zielstruktur – Beispiele

### scripts/
```
batch_pipeline/: prepare_batch_review.py, batch_correct_with_reasoning.py, batch_validate_with_perplexity.py, finalize_batch_review.py
enrichment/: enrich_evidenz_for_srs.py, fix_enriched_for_srs.py, export_learning_materials.py
data_prep/: prepare_needs_context_packets.py, extract_questions.py, extract_dialog_blocks.py, prepare_blocks.py
validation/: validate_full_dataset.py, validate_medical.py, validate_answers_quality.py
utilities/: cleanup_evidenz_antworten.py, merge_*.py, filter_*.py, convert_to_exam_format.py, build_rag_index.py, download_guidelines.py
```

### prompts/
```
agents/: CURSOR_COMPOSER_PROMPT.md, CURSOR_AGENT_PROMPT_20251218.md, CURSOR_AGENT_TASK.md, AGENT_OVERVIEW.md, AGENT_PROMPTS_INDEX.md
validation/: antwort_generierung_lokal.md, antwort_validierung_lokal.md
```

### docs/
```
guides/: START_HERE.md, REPO_ORGANISATION.md, MIGRATION_GUIDE.md
status/: PROJECT_STATUS.md
analysis/: QUALITY_ASSESSMENT_REPORT.md, PIPELINE_STATISTICS.md
```

---

## Beispiel-Mappings (Quelle → Ziel)

| Quelle | Ziel |
|---|---|
| `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` | `_OUTPUT/batch_runs/20251216/batch_review_remaining_issues_20251216_142834.json` |
| `_OUTPUT/batch_review_report_20251216_142834.md` | `_OUTPUT/batch_runs/20251216/batch_review_report_20251216_142834.md` |
| `_OUTPUT/evidenz_antworten_updated_20251216_142834.json` | `_OUTPUT/batch_runs/20251216/evidenz_antworten_updated_20251216_142834.json` |
| `_OUTPUT/review_queue_20251216_033807.json` | `_OUTPUT/review_queue/review_queue_20251216_033807.json` |
| `_OUTPUT/anki_ready_20251215_162246.tsv` | `_OUTPUT/learning_exports/20251215/anki_ready_20251215_162246.tsv` |
| `_OUTPUT/run_reports/gpt5_run_20251210_150117.md` | `_OUTPUT/reports/20251210/gpt5_run_20251210_150117.md` |
| `CURSOR_AGENT_PROMPT_20251218.md` | `prompts/agents/CURSOR_AGENT_PROMPT_20251218.md` |
| `AGENT_OVERVIEW.md` | `prompts/agents/AGENT_OVERVIEW.md` |
| `START_HERE.md` | `docs/guides/START_HERE.md` |
| `PROJECT_STATUS.md` | `docs/status/PROJECT_STATUS.md` |

---

## Metadaten & Etiketten

- Für jede Datei in `_OUTPUT/` (außer `canonical/`) eine `.meta.json` neben die Datei legen mit:
  - `description`, `generated_by`, `status` (ok|needs_review|maybe|problem), `next_action`, `created_at`, `source_refs`.
- In jedem Ordner ein `README.md`/`index.md` mit Zweck, wichtigsten Dateien, offenen Aufgaben.
- `AGENT_GUIDE.md` im Repo-Root als zentrales Handbuch.

---

## Überwachung & Automatisierung

- Watcher (watchdog/watchman):
  - Validiert Namen (snake_case + `_YYYYMMDD_HHMMSS`), verbietet Änderungen in `_OUTPUT/canonical/`.
  - Erzeugt/aktualisiert `.meta.json` neben neuen Dateien.
  - Appendet Kurz-Einträge an `docs/status/PROJECT_STATUS.md`.
- CI-Regeln:
  - Blocke Änderungen an `_OUTPUT/canonical/evidenz_antworten.json`.
  - Secret-Scan, Dateinamen-Lint, Timestamp-Pflicht in `_OUTPUT/`.
- Jira-Integration (optional):
  - Bei `status=needs_review` in `.meta.json` automatisch Issue/Kommentar erzeugen.

---

## Workflow-Checkliste für Agenten

1. Struktur respektieren: `canonical/` nie ändern; neue Outputs immer mit Timestamp.
2. Meta pflegen: `.meta.json` aktualisieren; Ordner-`README.md` ergänzen.
3. Watcher triggern: Naming/Meta prüfen lassen.
4. Doku pflegen: `docs/status/PROJECT_STATUS.md` und `docs/guides/REPO_ORGANISATION.md` aktuell halten.
5. Secrets schützen: Nur via ENV, nie loggen/committen.

---

## CI / Pre-commit Vorschläge

- Pre-commit: blockiert `canonical/` & `_FACT_CHECK_SOURCES/` Änderungen, es sei denn PR-Kommentar.
- Secret scan in CI.
- Linter für Dateinamen (keine Leerzeichen/Sonderzeichen).
- Check: neue `_OUTPUT/`-Artefakte haben Timestamp.
- Automatischer Test: Pfad-Imports (`python -m py_compile` oder `pytest --collect-only`).

---

## `.gitignore` (Empfehlung)

```
# lokale temporäre Files
tmp_rovodev*
_OUTPUT/tmp/
_OUTPUT/tmp/**

# häufige output temp patterns
_OUTPUT/triage_summary*.md
_OUTPUT/manual_review_items*.json
_OUTPUT/batch_round2_input*.json

# IDE / Python
__pycache__/
*.pyc
.env
.venv/
```

---

## Sanftes Migrations-Vorgehen (3 Phasen)

### Phase 1 — Leitfaden + .gitignore (keine Moves)
- PR: `docs/guides/REPO_ORGANISATION.md` und `.gitignore` ergänzen.

### Phase 2 — Dry-Run Mapping-Report (separater PR)
- `scripts/utilities/tmp_rovodev_organize_dryrun.py` erzeugt `_OUTPUT/reports/organisation/dryrun_YYYYMMDD_HHMMSS.json` (nur Report).

### Phase 3 — Moves + Referenz-Update
- Kleine, atomare PRs; Pfad-Referenzen aktualisieren; Sanity-Checks; CI grün.

---

## PR-Vorlage / Commit-Message Vorschlag

- PR Titel: `docs: Repo Organisation Guide + .gitignore (phase 1)`
- PR Beschreibung: "Erstellt `docs/guides/REPO_ORGANISATION.md` mit Struktur, Namenskonventionen, Guardrails. Ergänzt `.gitignore`. Phase 1: nur Doku + ignore."
