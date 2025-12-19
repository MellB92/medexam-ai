# Claude Code Prompt (Copy/Paste) — Parallel Abschluss MedExamAI (2025-12-19)

Du bist **Claude Code** (Terminal) und arbeitest **parallel** zu GPT‑5.2 (Cursor).  
Ziel: Projekt schnell abschließen, ohne Überschneidungen/Dateikonflikte.

## 0) Arbeitsverzeichnis

```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
```

## 1) Aufgabenverteilung (verbindlich)

- **GPT‑5.2 (Cursor)** macht **nur Batch-Pipeline**:
  - `batch_correct_with_reasoning.py` (60 Items)
  - danach `batch_validate_with_perplexity.py`
  - danach `finalize_batch_review.py`
  - Backup + Promotion in `_OUTPUT/evidenz_antworten.json`
  - Coverage-Check

- **Du (Claude Code)** machst **nur Doku + 7 manuelle Items**:
  - 7 manuelle Rest-Items bearbeiten
  - `PROJECT_STATUS.md` + `TODO.md` updaten
  - Final Report erstellen

## 2) Gemeinsames Sync-Protokoll (damit wir wirklich „kommunizieren“)

Bitte schreibe deine Zwischenstände laufend in:

`_AGENT_WORK/PARALLEL_SYNC_20251219.md`

Format kurz & eindeutig:
- Timestamp
- Was erledigt
- Was blockt
- Nächster Schritt

## 3) Status Batch (nur lesen/monitoren)

Der Batch-Run läuft im Migrations-Repo als Hintergrundprozess.
Wenn du den Status checken willst (ohne den Run zu stören):

```bash
RUN_ID=$(cat _AGENT_WORK/GPT52_Batch_20251218_155448/output/RUN_ID.txt)
PID=$(cat _AGENT_WORK/GPT52_Batch_20251218_155448/output/BATCH_CORRECT_PID.txt)

echo "RUN_ID=$RUN_ID PID=$PID"
ps -p "$PID" -o pid,etime,command
wc -l "_OUTPUT/batch_corrected_${RUN_ID}_checkpoint.jsonl"
tail -n 40 "_AGENT_WORK/GPT52_Batch_20251218_155448/logs/batch_correct_${RUN_ID}.log"
```

## 4) Wenn der Batch fertig ist (Trigger für dich)

Sobald GPT‑5.2 fertig gemerged hat, wird in `_AGENT_WORK/PARALLEL_SYNC_20251219.md`
ein Eintrag „MERGE DONE“ stehen und eine neue Datei in `_OUTPUT/` existieren:

- `_OUTPUT/batch_review_remaining_issues_<TS>.json`  (sollte ~7 remaining sein)

Dann kannst du:
- `PROJECT_STATUS.md` und `TODO.md` aktualisieren
- deine 7 manuellen Items finalisieren
- Final Report schreiben

## 5) Wichtige Regeln

- **Niemals** `.env` loggen oder committen.
- `_OUTPUT/evidenz_antworten.json` **nur** nach Backup ersetzen (macht GPT‑5.2).
- Keine parallelen Writes an denselben Dateien.


