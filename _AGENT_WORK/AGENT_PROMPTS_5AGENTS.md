# Agent Prompts - 5-Agent Workflow

**Erstellt:** 2025-12-18 16:05:00
**Workflow:** Vereinfachter 5-Agent-Workflow (ohne Signal-System)

---

## Übersicht

| Agent | Rolle | Tool | Ordner |
|-------|-------|------|--------|
| GPT-5.2 #1 | Lead & Analysis | Cursor | GPT52_20251218_142539 |
| GPT-5.2 #2 | Batch Executor | Cursor | GPT52_Batch_20251218_155448 |
| Opus 4.5 #1 | QA & Validation | Cursor | Opus45_20251218_142539 |
| Opus 4.5 #2 | Documentation | Cursor | Opus45_Docs_20251218_155454 |
| Claude Code | Coordinator | Terminal | - |

---

## 1. GPT-5.2 #1 (Lead & Analysis)

**Status:** ✅ BEREITS AKTIV

**Aktueller Task:** Task #002 (Vorbereitung Phase 1)

**Prompt (wenn nötig):**
```
Du bist bereits mit Task #002 beschäftigt.

Lies und führe aus:
_AGENT_WORK/GPT52_20251218_142539/input/READY_TO_START_TASK002.md

Arbeite Schritt 1-8 durch:
1. Backup erstellen
2. Items splitten (60 Batch / 7 Manual)
3. Batch-Input generieren
4. Manual-Input generieren
5. Validieren
6. Output Files erstellen

Ziel: Erstelle batch_round2_input_20251218.json (60 Items)
Dauer: ~15 Minuten

Sobald fertig: Melde dich!
```

---

## 2. GPT-5.2 #2 (Batch Executor)

**Status:** ⏸️ WARTET auf GPT-5.2 #1

**Prompt (nach GPT-5.2 #1 fertig):**
```
Du bist GPT-5.2 #2 - Batch Executor.

Deine Aufgabe: Führe Batch-Runde 2 durch (60 Items automatisch korrigieren).

Lies und führe ALLE Schritte aus:
_AGENT_WORK/GPT52_Batch_20251218_155448/input/TASK_BATCH_EXECUTION.md

Wichtigste Schritte:
1. Input von GPT-5.2 #1 abholen und validieren
2. Batch-Request erstellen (batch_medexamen_reviewer_v2.py)
3. Batch-Monitoring starten
4. Warten auf API (1-2 Stunden)
5. Ergebnisse abholen
6. Backup erstellen (evidenz_antworten.json)
7. Merge durchführen
8. Validieren
9. Output für Opus 4.5 #1 bereitstellen

Dauer: ~2-3 Stunden (hauptsächlich API-Wartezeit)

WICHTIG:
- IMMER Backup vor Merge!
- Batch-ID speichern
- Monitoring läuft im Hintergrund

Arbeite die Schritte 1-9 nacheinander ab!
```

---

## 3. Opus 4.5 #1 (QA & Validation)

**Status:** ⏸️ WARTET auf GPT-5.2 #2

**Prompt (nach GPT-5.2 #2 fertig):**
```
Du bist Opus 4.5 #1 - Quality Assurance.

Deine Aufgabe: Validiere die Batch-Korrekturen (Stichproben-QA).

Lies und führe aus:
_AGENT_WORK/Opus45_20251218_142539/input/TASK_QA_VALIDATION.md

Wichtigste Schritte:
1. Wähle 10 zufällige Items aus Batch-Ergebnissen
2. Definiere Quality Gates (4 Kategorien)
3. Führe manuelle Validierung durch (pro Item 3-5 Min)
4. Aggregiere Ergebnisse
5. Erstelle QA-Report
6. Output für Opus 4.5 #2 bereitstellen

Quality Gates:
- Fachliche Korrektheit
- Leitlinien-Konformität 2024/2025
- Vollständigkeit
- Sprachliche Qualität

Ziel: Mind. 90% Pass Rate (Score >= 3/4)
Dauer: ~60-75 Minuten

WICHTIG: Manuelle Validierung ist essentiell!

Arbeite die Schritte 1-6 sorgfältig durch!
```

---

## 4. Opus 4.5 #2 (Documentation)

**Status:** ⏸️ WARTET auf Opus 4.5 #1

**Prompt (nach Opus 4.5 #1 fertig):**
```
Du bist Opus 4.5 #2 - Documentation.

Deine Aufgabe: Aktualisiere Projekt-Dokumentation.

Lies und führe aus:
_AGENT_WORK/Opus45_Docs_20251218_155454/input/TASK_DOCUMENTATION.md

Wichtigste Schritte:
1. Analysiere QA-Report
2. Update PROJECT_STATUS.md
   - Problem-Items: 67 → 7
   - Batch-Runde 2: COMPLETED
   - Coverage: ~99-100%
3. Update TODO.md
   - Batch-Tasks als done markieren
   - Neue Tasks für 7 manuelle Items
4. Erstelle Final Report
5. Update Workflow-Status

Dauer: ~30-45 Minuten

WICHTIG:
- IMMER Backups erstellen!
- Metriken aus QA-Report nehmen
- Klar dokumentieren

Arbeite die Schritte 1-5 durch!
```

---

## 5. Claude Code (Coordinator)

**Das bin ich!**

**Meine Aufgaben:**
- Workflow koordinieren
- Monitoring durchführen
- Scripts ausführen wenn nötig
- Bei Problemen eingreifen

**Monitoring:**
```bash
# Regelmäßig ausführen
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617/_AGENT_WORK
./monitoring_dashboard.sh

# Coverage-Check
cd ..
python3 -c "
import json
from pathlib import Path
mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())
coverage = sum(1 for x in mm if x['question'] in {q['frage'] for q in qa})/len(mm)*100
print(f'Coverage: {coverage:.1f}%')
"
```

---

## Workflow-Ablauf (Sequenziell)

```
┌────────────────────────────────────────────────────────────┐
│                  5-AGENT WORKFLOW                          │
└────────────────────────────────────────────────────────────┘

1. GPT-5.2 #1 (Lead)
   ├─ Status: 🟢 AKTIV (arbeitet an Task #002)
   ├─ Task: Items splitten (60/7)
   ├─ Output: batch_round2_input_20251218.json
   └─ Dauer: ~15 Min

2. GPT-5.2 #2 (Batch) ← Startet nach #1
   ├─ Status: ⏸️ WARTET
   ├─ Task: Batch-Runde 2 durchführen
   ├─ Output: Aktualisierte evidenz_antworten.json
   └─ Dauer: ~2-3 Std

3. Opus 4.5 #1 (QA) ← Startet nach #2
   ├─ Status: ⏸️ WARTET
   ├─ Task: Stichproben-QA (10 Items)
   ├─ Output: QA_REPORT_20251218.md
   └─ Dauer: ~60 Min

4. Opus 4.5 #2 (Docs) ← Startet nach #3
   ├─ Status: ⏸️ WARTET
   ├─ Task: Dokumentation updaten
   ├─ Output: FINAL_REPORT_20251218.md
   └─ Dauer: ~30 Min

5. Claude Code (Coordinator)
   ├─ Status: 🟢 LÄUFT
   ├─ Task: Monitoring & Koordination
   └─ Dauer: Gesamte Zeit

─────────────────────────────────────────────────────────────
GESAMT: ~4-4.5 Stunden
```

---

## Wichtige Hinweise

### Für alle Agents:

1. **Arbeitsordner:**
   - Jeder Agent hat seinen eigenen Ordner
   - Alle Outputs in `output/` Unterordner
   - Alle Logs in `logs/` Unterordner

2. **Kein Signal-System:**
   - Keine `.ready_for_*` Flag-Dateien mehr
   - Sequenzielle Ausführung
   - Direkter Handoff zwischen Agents

3. **Backups:**
   - IMMER vor kritischen Operationen
   - Timestamp im Dateinamen
   - Validieren nach Restore

4. **Dokumentation:**
   - progress.log regelmäßig updaten
   - Task Reports nach Completion
   - Fehler immer dokumentieren

---

## Schnellstart-Sequenz

**Jetzt sofort:**
1. Warte bis GPT-5.2 #1 Task #002 fertig hat

**Dann (~15 Min später):**
2. Starte GPT-5.2 #2 mit Prompt oben

**Dann (~2-3 Std später):**
3. Starte Opus 4.5 #1 mit Prompt oben

**Dann (~60 Min später):**
4. Starte Opus 4.5 #2 mit Prompt oben

**Dann (~30 Min später):**
5. ✅ FERTIG! Alle 67 → 7 Problem-Items

---

## Support

**Bei Problemen:**
1. Check Agent-Status in seinem Ordner
2. Lies TASK_*.md für detaillierte Schritte
3. Prüfe Logs in logs/ Ordner
4. Restore von Backup falls nötig

**Wichtige Dateien:**
- TASK_BATCH_EXECUTION.md (GPT-5.2 #2)
- TASK_QA_VALIDATION.md (Opus 4.5 #1)
- TASK_DOCUMENTATION.md (Opus 4.5 #2)

---

**Erstellt:** 2025-12-18 16:05:00
**Status:** ✅ READY TO START
**Nächster Agent:** GPT-5.2 #1 (bereits aktiv)

🚀 **Workflow ist bereit! Warte auf GPT-5.2 #1 Completion!**
