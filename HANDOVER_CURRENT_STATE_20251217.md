# Übergabebericht – Medexamenai (Ist-Stand)

Stand: **2025-12-17** (Repo: `/Users/user/Medexamenai`)

Diese Übergabe ist als **„Single Source of Truth“** für neue Sessions/Agenten gedacht.
Für einen kompakten Index siehe zusätzlich: `AGENT_OVERVIEW.md`.

## Harte Constraints (müssen eingehalten werden)

- **NICHT überschreiben:** `_OUTPUT/evidenz_antworten.json` (kanonische Hauptdatei, read-only behandeln)
- **Keine inhaltlichen Rewrites in-place** in kanonischen Dateien
- **Outputs immer neu mit Timestamp**
- **Keine Secrets loggen/committen** (Repo enthält `.env` mit Keys)

## Zentrale Datenbestände (echte Zahlen)

- **Kanonische Q&A-Daten:** `_OUTPUT/evidenz_antworten.json`
  - **Einträge:** **4505**
- **Finalisierte Arbeitsdatei (NEU, Timestamp, enthält Batch-Review-Updates):**
  `_OUTPUT/evidenz_antworten_updated_20251216_142834.json`
  - **Einträge:** **4505**
- **Missing Questions Liste:** `_OUTPUT/questions_missing_strict.json`
  - **Einträge:** **3732** (Liste) – **historisch/strict**, enthält viele Fragmente/Duplikate (kein aktueller Gap)
- **Meaningful Coverage Referenz (authoritative für Coverage):** `_OUTPUT/meaningful_missing.json`
  - **Einträge:** **2527**
  - **Coverage-Check:** **2527/2527** matchen exakt in `_OUTPUT/evidenz_antworten.json` (siehe `CODEX.md`)

## Lern-Exports / SRS (ready + review)

- **Anki Ready TSV:** `_OUTPUT/anki_ready_20251215_162246.tsv`
  - **Zeilen:** **2090**
- **Anki Review Queue TSV:** `_OUTPUT/anki_review_queue_20251215_162246.tsv`
  - **Zeilen:** **431**
- **Study Dashboard:** `_OUTPUT/study_dashboard_20251215_162246.md`
- **Daily Plan:** `_OUTPUT/daily_plan_20251215_162246.json`

## Review Queue / needs_context (Status)

- **Review-Queue:** `_OUTPUT/review_queue_20251216_033807.json`
  - **Total:** **431**
  - **needs_review:** **298**
  - **needs_context:** **133**

### needs_context vollständig gelöst (Goldstandard-Kontext)

- **Prepared needs_context (133/133 matched):** `_OUTPUT/needs_context_prepared_20251216_054003.json`
  - enthält u.a. `frage_mit_kontext`, `context_lines`, `source_file`, `source_page`, `validation_md_stub`
- **Externe Validierungsliste:** `_OUTPUT/needs_context_external_validation_20251216_054003.md`
  - **0 offen** (nur Summary)

## Batch-Review Pipeline (umgesetzt & ausgeführt)

Ziel: **431 Review-Items** automatisch korrigieren und web-validieren, ohne `_OUTPUT/evidenz_antworten.json` anzufassen.

### Run-ID: `20251216_064700`

**1) Prepared Batch-Input (lokale Checks + Leitlinienzuordnung):**

- `_OUTPUT/batch_input_prepared_20251216_064043.json`

**2) Korrektur (LLM, resumable):**

- `_OUTPUT/batch_corrected_20251216_064700.json`
- Checkpoint: `_OUTPUT/batch_corrected_20251216_064700_checkpoint.jsonl`

**3) Web-Validierung (Perplexity, resumable):**

- `_OUTPUT/batch_validated_20251216_064700.json`
- Checkpoint: `_OUTPUT/batch_validated_20251216_064700_checkpoint.jsonl`
- Summary: **ok=285, maybe=79, problem=67, error=0**

**4) Finalisierung (NEUE Outputs mit Timestamp):**

- **Arbeitsdatei (Antworten aktualisiert, kanonische bleibt read-only):**
  `_OUTPUT/evidenz_antworten_updated_20251216_142834.json`
- **Report:** `_OUTPUT/batch_review_report_20251216_142834.md`
- **Remaining Issues (verdict=problem):** `_OUTPUT/batch_review_remaining_issues_20251216_142834.json`
  - **remaining_count:** **67**

**Finalisierungslogik:**

- `ok` + `maybe` → Antwort übernommen (**updated answers = 364**) + `validation.batch_review` gesetzt
- `problem` → nicht übernommen; landet in `batch_review_remaining_issues_*.json`

## Reproduzierbare Commands (wichtigste)

```bash
# Lern-Exports (Anki + Dashboard + optional Daily Plan)
python3 scripts/export_learning_materials.py --daily-plan

# needs_context Pakete (133/133)
python3 scripts/prepare_needs_context_packets.py

# Batch-Review Pipeline
python3 scripts/prepare_batch_review.py
python3 scripts/batch_correct_with_reasoning.py --resume
python3 scripts/batch_validate_with_perplexity.py --resume --retry-errors
python3 scripts/finalize_batch_review.py \
  --corrected _OUTPUT/batch_corrected_20251216_064700.json \
  --validated _OUTPUT/batch_validated_20251216_064700.json
```

## Was „der Plan vom neuen Agent“ NICHT abbildet

Der generierte Fortsetzungsplan ist in vielen Punkten generisch und **ignoriert** zentrale, bereits erledigte Arbeit:

- Batch-Review Pipeline ist **implementiert und vollständig durchgelaufen**
- `needs_context` ist **komplett gematcht (133/133)**
- Es existiert eine **finalisierte Arbeitsdatei** (`evidenz_antworten_updated_20251216_142834.json`)
- Es existiert eine **konkrete Remaining-Issues Liste** (67 Items) als nächster Fokus für Qualitätsarbeit

## Prompt für neue Agenten (Bitte 1:1 verwenden)

Du arbeitest im Repo `/Users/user/Medexamenai`. Beachte strikt:

- **Harte Regeln**
  - `_OUTPUT/evidenz_antworten.json` niemals überschreiben (read-only). Neue Outputs immer mit Timestamp schreiben.
  - Keine Secrets loggen/committen (`.env` existiert).
  - Agenten-Startpunkt: `HANDOVER_CURRENT_STATE_20251217.md` + `AGENT_OVERVIEW.md` lesen.

- **Aktueller Datenstand**
  - Q&A: 4.505 Einträge in `_OUTPUT/evidenz_antworten.json` (kanonisch) und `_OUTPUT/evidenz_antworten_updated_20251216_142834.json` (Arbeitsdatei mit Batch-Updates).
  - Review-Queue: 431 Items (`_OUTPUT/review_queue_20251216_033807.json`), davon 298 needs_review, 133 needs_context (alle 133 bereits gematcht in `_OUTPUT/needs_context_prepared_20251216_054003.json`).
  - Batch-Run `20251216_064700` durchgelaufen: korrigiert/validiert in `_OUTPUT/batch_corrected_20251216_064700.json` und `_OUTPUT/batch_validated_20251216_064700.json`; Report `_OUTPUT/batch_review_report_20251216_142834.md`.
  - Offene Problemfälle: 67 Items in `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` (höchster Fokus).
  - SRS/Exports: `_OUTPUT/anki_ready_20251215_162246.tsv`, `_OUTPUT/anki_review_queue_20251215_162246.tsv`, `_OUTPUT/study_dashboard_20251215_162246.md`.

- **Was `questions_missing_strict = 3732` bedeutet**
  - Datei `_OUTPUT/questions_missing_strict.json` enthält 3.732 Frage-Strings (`{question, source_file}`) aus einer alten, sehr strengen Phase; viele Fragmente/Duplikate.
  - **Kein aktueller Gap / keine To-Do-Liste.** Meaningful Coverage ist bereits 100 % (siehe `CODEX.md` und `meaningful_missing`-Check).
  - Wenn fehlende Fragen bearbeitet werden sollen: nur „meaningful“ nutzen, Fragmente ignorieren.
    - Authoritative Liste dafür: `_OUTPUT/meaningful_missing.json` (2527 Einträge)

- **Nächste Schritte (priorisiert)**
  - Fokus: 67 `problem`-Items aus `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` manuell oder per zweiter Batch-Runde fixen (neue Timestamp-Outputs).
  - Doku angleichen: `PROJECT_STATUS.md` und `TODO.md` auf Basis dieses Handovers aktualisieren.
  - Optional: Missing-Questions-Thema nur für meaningful Fragen angehen (siehe `CODEX.md`).

- **Relevante Commands**

```bash
# Meaningful Coverage prüfen (soll 2527/2527 sein)
python3 -c "import json; from pathlib import Path; mm=json.loads(Path('_OUTPUT/meaningful_missing.json').read_text()); qa=json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text()); s=set(x['frage'] for x in qa); print(sum(1 for x in mm if x['question'] in s), '/', len(mm))"

# needs_context Pakete (133/133)
python3 scripts/prepare_needs_context_packets.py

# Batch-Review Finalisierung (falls Re-Run)
python3 scripts/finalize_batch_review.py \
  --corrected _OUTPUT/batch_corrected_20251216_064700.json \
  --validated _OUTPUT/batch_validated_20251216_064700.json

# Lern-Exports (Anki + Dashboard + optional Daily Plan)
python3 scripts/export_learning_materials.py --daily-plan
```

## Empfohlene nächste Schritte (realistisch, high signal)

1) **Remaining Issues (67 Items) bearbeiten**
   - Quelle: `_OUTPUT/batch_review_remaining_issues_20251216_142834.json`
   - Optionen:
     - gezielte manuelle Korrektur der 67 Items
     - zweite Batch-Runde nur für `problem` Items (Prompt/Validierungsregeln anpassen)

2) **Missing Questions (3732) priorisieren**
   - Nur „meaningful“ Fragen beantworten, Fragmente aussortieren (Repo-Doku beachten, z.B. `CODEX.md`)

3) **Migration vereinfachen**
   - Für „einfach & robust“: Bundle statt 90k Dateien → siehe `MIGRATION_KIT/README.md`

## Migration (Google Drive / neuer Mac)

Siehe `MIGRATION_KIT/README.md` und insbesondere **Option C**:

- `MIGRATION_KIT/package_gdrive_bundle.sh` (tar bauen, ohne `.git/backups/dropbox_import/venv/.env`)
- `MIGRATION_KIT/rclone_upload_bundle.sh` (1 Datei hochladen, robust & schnell)
