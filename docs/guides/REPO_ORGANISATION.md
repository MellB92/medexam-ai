# REPO_ORGANISATION

## Zweck

Dieses Dokument beschreibt die empfohlene Ordner- und Dateiorganisation für das Repository, Namenskonventionen, Guardrails sowie ein risikoarmes Vorgehen zur Migration existierender Artefakte. Ziel: klare funktionale Trennung, reproduzierbare Zeitreihen-Artefakte und verlässliche Regeln für kanonische Dateien und Outputs.

---

## Grundprinzipien / Ziele

* Funktionale Bündelung: Ordner nach Funktion (Code, Daten, Doku, Outputs).
* Zeitreihen-Artefakte: Runs/Reports werden nach Datum/Run-ID strukturiert.
* Eindeutige Benennung: `snake_case`, Zeitstempel `_YYYYMMDD_HHMMSS` vor der Dateiendung.
* Temporäre Artefakte: Präfix `tmp_rovodev_` (lokal, in `.gitignore`).
* Guardrails: Kanonische Dateien (z. B. canonical/evidenz_antworten.json) sind read-only im Repo; Outputs immer mit Timestamp; keine Secrets im Repo.

---

## Top-Level Struktur (empfohlen)

```
core/                    # Python-Kernlogik (unverändert)
scripts/                 # ausführbare Pipelines + utilities
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
  canonical/             # READ-ONLY: kanonische Dateien
  batch_runs/
  reports/
  learning_exports/
  review_queue/
  run_reports/
  md_converted/
  tmp/                   # lokal, ignored
_FORENSIK/
_FACT_CHECK_SOURCES/     # READ-ONLY, große Quellen
_ARCHIVE/                # veraltetes/quarantänisiertes Material
```

> Hinweis: `core/` bleibt wie bisher; `scripts/` fasst Pipelines zusammen (nicht alle Skripte müssen umgezogen werden, Vorschlag siehe weiter unten).

---

## Detailliertes Verhalten für `_OUTPUT/`

* canonical/
  * Enthält z. B. `evidenz_antworten.json` — darf im Repo nicht überschrieben oder verändert werden. Änderungen nur via Review/PR und mit ACL-Hinweis.
* batch_runs/<YYYYMMDD>/ oder batch_runs/<RUN_ID>/
  * Jede Run-ID → eigener Unterordner. Dateien mit Zeitstempel als Suffix. Beispiel: `_OUTPUT/batch_runs/20251216/batch_corrected_20251216_064700.json`
* learning_exports/<YYYYMMDD>/
  * Lernexportartefakte (z. B. Anki TSVs, Dashboards) mit Timestamp.
* reports/<YYYYMMDD>/
  * Status-Reports, Analyse-Summaries.
* review_queue/
  * Review-Queues nach Datum: `review_queue_YYYYMMDD_HHMMSS.json`
* tmp/
  * Nur lokal: `tmp_rovodev_*` (in `.gitignore`).

---

## Namenskonventionen

* Dateinamen: `snake_case`, deutschsprachige Bezeichnungen zulässig, aber keine Sonderzeichen/spaces.
* Zeitstempelformat: `_YYYYMMDD_HHMMSS` Suffix vor der Extension, z. B. `batch_review_report_20251216_142834.md`.
* Temporär: Dateien beginnen mit `tmp_rovodev_` (immer in `.gitignore`).
* Outputs: niemals kanonische Dateien ohne neuen Zeitstempel überschreiben.
* Ausnahme / Canonical: `canonical/evidenz_antworten.json` bleibt kanonisch/read-only.

---

## Read-only / Schreibregeln / Guardrails

* `canonical/` und `_FACT_CHECK_SOURCES/` sind read-only. Änderungen nur per PR und mit Zustimmung eines Maintainers.
* Alle generierten Outputs müssen Timestamp enthalten und in passenden `_OUTPUT/` Unterordnern liegen.
* `evidenz_antworten.json` (in `canonical/`) darf nicht überschrieben werden; Updates als neue Datei z. B. `evidenz_antworten_updated_YYYYMMDD_HHMMSS.json`.
* Keine Secrets in Repo — CI/Pre-commit/Scan erzwingen.
* `tmp_rovodev_*` nur lokal und in `.gitignore` aufnehmen.

---

## Vorgeschlagene Zielstruktur (konkret mit Beispielen)

### `scripts/` (Beispielaufteilung)

```
scripts/
  batch_pipeline/
    prepare_batch_review.py
    batch_correct_with_reasoning.py
    batch_validate_with_perplexity.py
    finalize_batch_review.py
  enrichment/
    enrich_evidenz_for_srs.py
    fix_enriched_for_srs.py
    export_learning_materials.py
  data_prep/
    prepare_needs_context_packets.py
    extract_questions.py
    extract_dialog_blocks.py
    prepare_blocks.py
  validation/
    validate_full_dataset.py
    validate_medical.py
    validate_answers_quality.py
  utilities/
    cleanup_evidenz_antworten.py
    merge_*.py
    filter_*.py
    convert_to_exam_format.py
    build_rag_index.py
    download_guidelines.py
```

### `prompts/`

```
prompts/
  agents/
    CURSOR_COMPOSER_PROMPT.md
    CURSOR_AGENT_PROMPT_20251218.md
    CURSOR_AGENT_TASK.md
    AGENT_OVERVIEW.md
    AGENT_PROMPTS_INDEX.md
  validation/
    antwort_generierung_lokal.md
    antwort_validierung_lokal.md
```

### `docs/`

```
docs/
  guides/
    START_HERE.md
    REPO_ORGANISATION.md  # dieses Dokument
    MIGRATION_GUIDE.md
  status/
    PROJECT_STATUS.md
  analysis/
    QUALITY_ASSESSMENT_REPORT.md
    PIPELINE_STATISTICS.md
```

---

## Beispiel-Mappings (Quell → Ziel)

| Quelle                                                       | Vorschlag Ziel                                                                   |
| ------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` | `_OUTPUT/batch_runs/20251216/batch_review_remaining_issues_20251216_142834.json` |
| `_OUTPUT/batch_review_report_20251216_142834.md`             | `_OUTPUT/batch_runs/20251216/batch_review_report_20251216_142834.md`             |
| `_OUTPUT/evidenz_antworten_updated_20251216_142834.json`     | `_OUTPUT/batch_runs/20251216/evidenz_antworten_updated_20251216_142834.json`     |
| `_OUTPUT/review_queue_20251216_033807.json`                  | `_OUTPUT/review_queue/review_queue_20251216_033807.json`                         |
| `_OUTPUT/anki_ready_20251215_162246.tsv`                     | `_OUTPUT/learning_exports/20251215/anki_ready_20251215_162246.tsv`               |
| `_OUTPUT/run_reports/gpt5_run_20251210_150117.md`            | `_OUTPUT/reports/20251210/gpt5_run_20251210_150117.md`                           |
| `CURSOR_AGENT_PROMPT_20251218.md`                            | `prompts/agents/CURSOR_AGENT_PROMPT_20251218.md`                                 |
| `AGENT_OVERVIEW.md`                                          | `prompts/agents/AGENT_OVERVIEW.md`                                               |
| `START_HERE.md`                                              | `docs/guides/START_HERE.md`                                                      |
| `PROJECT_STATUS.md`                                          | `docs/status/PROJECT_STATUS.md`                                                  |

---

## Migrationshinweise / Sanity-Checks

* Referenzen prüfen: Vor Moves alle Pfadreferenzen in Skripten/Prompts prüfen (`grep -R "old/path" .`).
* Sanity Check: Nach Moves Skripte nur auf Import/Path-Level starten (keine aktiven Runs); sicherstellen dass `import`/`from .. import` weiterhin funktioniert.
* Kanonische Dateien: Nicht automatisch ersetzen – nur neue Datei mit Timestamp erzeugen.
* `_FACT_CHECK_SOURCES/` & `_FORENSIK/`: Nur verschieben, wenn wirklich nötig; ggf. nur verlinken.

---

## CI / Pre-commit Vorschläge

* Pre-commit Hook: blockiere Commits, die `canonical/` oder `_FACT_CHECK_SOURCES/` modifizieren (ohne PR-Kommentar).
* Secret scan in CI.
* Linter für Dateinamen (keine Leerzeichen, keine Sonderzeichen).
* Check: neue `_OUTPUT/` Artefakte müssen Timestamp enthalten.
* Automatischer Test: Skripte auf path-import prüfen (`python -m py_compile` oder `pytest --collect-only`).

---

## `.gitignore` (Empfehlung)

Füge in `.gitignore` mindestens:

```
# lokale temporäre Files
tmp_rovodev*
_OUTPUT/tmp/
_OUTPUT/tmp/**
OUTPUT/tmp_rovodev*
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

## Sanftes Migrations-Vorgehen (3 Phasen, risikoarm)

### Phase 1 — Leitfaden + .gitignore-PR (keine Moves)

* Erstelle PR mit `docs/guides/REPO_ORGANISATION.md` und `.gitignore`-Erweiterungen.
* Ziel: Team-Review, Konsens über Konventionen.

**Deliverables:** `docs/guides/REPO_ORGANISATION.md`, `.gitignore` PR.

### Phase 2 — Dry-Run Mapping-Report

* Script `tmp_rovodev_organize_dryrun.py` (nur Report): scannt Repo, schlägt Quelle→Ziel Mappings vor und schreibt Ergebnis nach `_OUTPUT/reports/organisation/` als JSON/MD. Keine Moves.
* Team prüft und genehmigt Mappings.

**Deliverables:** `_OUTPUT/reports/organisation/dryrun_<YYYYMMDD_HHMMSS>.json` (Mapping-Report).

### Phase 3 — Moves + Referenz-Update

* Ausgewählte Moves als PRs (kleine, atomare Moves).
* Update Pfadreferenzen in Prompts/Skripten (grep + sed/patch).
* Sanity-Checks: `import` tests, Skript-dry runs, CI grün.
* Abschließende Review und Merge. Optional: Archive alter Pfade in `_ARCHIVE/`.

**Deliverables:** PRs mit Moves, Referenzupdates, CI-Grün.

---

## Dry-Run Script — kurze Skizze (Benennung / Output)

**Name:** `scripts/utilities/tmp_rovodev_organize_dryrun.py`
**Funktion:**

* Scannt bekannte Muster (z. B. `_OUTPUT/*`, `CURSOR_*.md`)
* Erzeugt JSON mit Einträgen `{source, suggested_target, reason, safe_to_move_bool}`
* Speichert Report `_OUTPUT/reports/organisation/dryrun_YYYYMMDD_HHMMSS.json`
* Keine Änderungen am Repo.

**Beispielausgabe (JSON):**

```
{
  "mappings": [
    {
      "source": "_OUTPUT/batch_review_report_20251216_142834.md",
      "suggested_target": "_OUTPUT/batch_runs/20251216/batch_review_report_20251216_142834.md",
      "reason": "Batch report gehört zum Run 20251216",
      "safe_to_move": true
    }
  ]
}
```

---

## PR-Vorlage / Commit-Message Vorschlag

**PR Titel:** `docs: Repo Organisation Guide + .gitignore (phase 1)`
**PR Beschreibung:**
Kurz: "Erstellt `docs/guides/REPO_ORGANISATION.md` mit vorgeschlagener Ordnerstruktur, Namenskonventionen und Guardrails. Ergänzt `.gitignore` um lokale tmp-Pattern. Dies ist Phase 1 der Migration (nur Dokumentation + ignore)."
