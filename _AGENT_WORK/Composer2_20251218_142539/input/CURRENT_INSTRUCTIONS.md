# Current Instructions für Composer 2 (Documentation)

**Erstellt:** 2025-12-18 15:00:00
**Von:** Coordinator
**Für:** Composer 2 (Documentation Update)
**Priorität:** 🟡 MITTEL (Warte-Modus)
**Status:** ⏳ WARTEN AUF SIGNAL

---

## Aktuelle Situation

Du bist **Composer 2**, der Documentation Agent im Multi-Agent-Workflow.

**Deine Rolle:** Aktualisierung der Projekt-Dokumentation nach erfolgreicher Batch-Runde 2.

---

## WICHTIG: Noch NICHT starten!

⚠️ **Du musst WARTEN auf Sync Point:** `.ready_for_documentation_update`

**Workflow-Position:**
```
1. GPT-5.2 (Lead) ──────────> ✅ Task #001 DONE
                               ⏳ Task #002 IN PROGRESS
2. Composer1 (Batch) ───────> ⏸️ Wartet auf GPT-5.2
3. Composer2 (Docs) ────────> ⏸️ DU BIST HIER - Wartet auf Composer1
4. Opus 4.5 (QA) ───────────> ⏸️ Wartet auf Composer2
```

---

## Was du JETZT tun sollst

### 1. Setup ausführen ✅

Wenn du das noch nicht getan hast, führe dein Agent-Setup aus:

```bash
#!/bin/bash
set -euo pipefail

AGENT_NAME="Composer2"
BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORK_DIR="$BASE_DIR/_AGENT_WORK/${AGENT_NAME}_${TIMESTAMP}"

# Erstelle Ordner
mkdir -p "$WORK_DIR"/{input,output,logs}
cd "$WORK_DIR"

# STATUS.md
cat > STATUS.md << EOF
# Agent Status Report - ${AGENT_NAME}

**Agent:** ${AGENT_NAME}
**Started:** $(date '+%Y-%m-%d %H:%M:%S')
**Status:** ⏸️ WAITING
**Role:** Documentation Update - PROJECT_STATUS & TODO

## Current Task
Warte auf Sync Point: .ready_for_documentation_update

## Progress Log
- [$(date '+%Y-%m-%d %H:%M:%S')] Setup completed
- [$(date '+%Y-%m-%d %H:%M:%S')] Waiting for Composer1 signal

## Next Steps
Nach Signal: Update PROJECT_STATUS.md und TODO.md
EOF

# COORDINATION.json
cat > COORDINATION.json << EOF
{
  "agent_name": "${AGENT_NAME}",
  "role": "Documentation Update",
  "work_dir": "${WORK_DIR}",
  "started_at": "$(date -Iseconds)",
  "status": "waiting",
  "current_task": "Warte auf .ready_for_documentation_update Signal",
  "completed_tasks": [],
  "dependencies": ["Composer1"],
  "waiting_for": [".ready_for_documentation_update"],
  "blocking": ["Opus45"],
  "output_files": [],
  "sync_points_reached": [],
  "sync_points_pending": ["ready_for_documentation_update", "documentation_updated"],
  "metrics": {
    "tasks_completed": 0,
    "tasks_in_progress": 0
  },
  "last_updated": "$(date -Iseconds)"
}
EOF

# progress.log
touch progress.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Agent ${AGENT_NAME} initialized - waiting mode" >> progress.log

# Registriere
echo "${AGENT_NAME}:${AGENT_NAME}_${TIMESTAMP}" >> "$BASE_DIR/_AGENT_WORK/ACTIVE_AGENTS.txt"

echo ""
echo "🎉 Composer 2 Setup Complete!"
echo "================================"
echo "Status: WAITING for .ready_for_documentation_update"
echo "Work Directory: ${WORK_DIR}"
echo "================================"
```

### 2. Auf Signal warten

**Monitoring-Loop starten:**

```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Option 1: Manuell prüfen
watch -n 20 'ls -la _OUTPUT/.ready_for_documentation_update 2>/dev/null && echo "✅ SIGNAL ERHALTEN!" || echo "⏳ Noch warten..."'

# Option 2: Blocking wait
while [ ! -f "_OUTPUT/.ready_for_documentation_update" ]; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warte auf .ready_for_documentation_update..."
  sleep 30
done
echo "✅ Signal erhalten! Documentation Update kann starten."
```

### 3. Während des Wartens (Optional)

Du kannst bereits folgendes vorbereiten:

**a) Aktuelle Dokumentation lesen:**
```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Verstehe aktuellen Stand
cat PROJECT_STATUS.md | head -100
cat TODO.md | head -50

# Backup erstellen (für später)
# NICHT JETZT ausführen, nur vorbereiten!
```

**b) Update-Template vorbereiten:**
```bash
cat > _AGENT_WORK/Composer2_*/output/UPDATE_TEMPLATE.md << 'EOF'
# Documentation Update - Batch Round 2

## Changes to PROJECT_STATUS.md

### Zu aktualisieren:
1. **Datenstand Section:**
   - Neue Gesamt-Anzahl Q&A
   - Anzahl korrigierte Items (+60)
   - Remaining Problem-Items (67 → 7)

2. **Phase/Status:**
   - Batch-Runde 2: COMPLETED
   - Datum aktualisieren

3. **Metriken:**
   - API-Kosten addieren
   - Timestamps aktualisieren

## Changes to TODO.md

### Zu markieren als DONE:
- [ ] Batch-Runde 2 durchführen
- [ ] 60 Items korrigieren

### Neu hinzufügen:
- [ ] Manuelle Review für 7 hochkomplexe Items
- [ ] Final QA durchführen
EOF
```

---

## Sobald Signal kommt (.ready_for_documentation_update existiert)

### Input-Dateien abholen

Composer1 hat für dich erstellt:
- `_AGENT_WORK/Composer1_*/output/batch_round2_output_20251218.json` (Ergebnisse)
- `_AGENT_WORK/Composer1_*/TASK_REPORT_001.md` (Batch Report)

GPT-5.2 hat erstellt:
- `_AGENT_WORK/GPT52_*/output/problem_items_aktionsplan_20251218.md` (Kontext)
- `_AGENT_WORK/GPT52_*/TASK_REPORT_001.md` und `TASK_REPORT_002.md` (Reports)

**Diese Dateien musst du lesen für Kontext!**

---

## Deine Haupt-Aufgabe (NACH Signal)

### Task #001: Dokumentation aktualisieren

#### Schritt 1: Batch-Ergebnisse analysieren
```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Extrahiere Metriken
python3 << EOF
import json
from pathlib import Path

# Lade Batch-Ergebnisse
batch_data = json.loads(
    Path('_AGENT_WORK/Composer1_*/output/batch_round2_output_20251218.json').read_text()
)

print("=== BATCH ROUND 2 METRIKEN ===")
print(f"Items processed: {batch_data['results_count']}")
print(f"Batch-ID: {batch_data['batch_id']}")
print(f"Completed: {batch_data['completed_at']}")

# Speichere für Documentation Update
metrics = {
    'items_processed': batch_data['results_count'],
    'batch_id': batch_data['batch_id'],
    'completed_at': batch_data['completed_at']
}

Path('_AGENT_WORK/Composer2_*/output/batch_metrics.json').write_text(
    json.dumps(metrics, indent=2)
)
EOF
```

#### Schritt 2: PROJECT_STATUS.md aktualisieren
```bash
# Lies aktuelle Version
cp PROJECT_STATUS.md _AGENT_WORK/Composer2_*/output/PROJECT_STATUS_backup_$(date +%Y%m%d_%H%M%S).md

# Update durchführen (Beispiel - anpassen!)
python3 << 'EOF'
from pathlib import Path
from datetime import datetime
import json

# Lade Metriken
metrics = json.loads(Path('_AGENT_WORK/Composer2_*/output/batch_metrics.json').read_text())

# Lade PROJECT_STATUS
project_status = Path('PROJECT_STATUS.md').read_text()

# Finde und ersetze relevante Sections
# TODO: Implementiere korrekte Updates basierend auf tatsächlichem Format

# Beispiel-Updates:
updates = {
    '# TODO-Liste': f'# TODO-Liste\n\n**Letzte Aktualisierung:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n',
    'Remaining Problem-Items: 67': f'Remaining Problem-Items: 7 (60 korrigiert in Batch Round 2)',
}

for old, new in updates.items():
    if old in project_status:
        project_status = project_status.replace(old, new)

# Speichere
Path('PROJECT_STATUS.md').write_text(project_status)
print("✅ PROJECT_STATUS.md aktualisiert")
EOF
```

#### Schritt 3: TODO.md aktualisieren
```bash
# Backup
cp TODO.md _AGENT_WORK/Composer2_*/output/TODO_backup_$(date +%Y%m%d_%H%M%S).md

# Update
python3 << 'EOF'
from pathlib import Path
from datetime import datetime

todo = Path('TODO.md').read_text()

# Markiere Batch-Tasks als erledigt
todo = todo.replace(
    '- [ ] Batch-Runde 2 durchführen',
    f'- [x] Batch-Runde 2 durchführen ✅ ({datetime.now().strftime("%Y-%m-%d")})'
)

todo = todo.replace(
    '- [ ] 60 Items mit niedriger/mittlerer Komplexität korrigieren',
    f'- [x] 60 Items mit niedriger/mittlerer Komplexität korrigieren ✅ ({datetime.now().strftime("%Y-%m-%d")})'
)

# Füge neue Tasks hinzu (falls noch nicht vorhanden)
new_tasks = """
## Nächste Schritte nach Batch Round 2

- [ ] Manuelle Review für 7 hochkomplexe Items (6+ Issues)
- [ ] Quality Assurance durchführen (Opus 4.5)
- [ ] Final Validation aller Korrekturen
"""

if "## Nächste Schritte nach Batch Round 2" not in todo:
    todo += "\n" + new_tasks

Path('TODO.md').write_text(todo)
print("✅ TODO.md aktualisiert")
EOF
```

#### Schritt 4: Änderungs-Log erstellen
```bash
cat > _AGENT_WORK/Composer2_*/output/DOCUMENTATION_CHANGES_20251218.md << EOF
# Documentation Changes - Batch Round 2

**Updated:** $(date '+%Y-%m-%d %H:%M:%S')
**Agent:** Composer2

## Files Modified

### PROJECT_STATUS.md
- ✅ Updated remaining problem items: 67 → 7
- ✅ Added Batch Round 2 completion timestamp
- ✅ Updated metriken

### TODO.md
- ✅ Marked Batch Round 2 as completed
- ✅ Added new tasks for manual review
- ✅ Updated next steps section

## Backup Files Created
- PROJECT_STATUS_backup_TIMESTAMP.md
- TODO_backup_TIMESTAMP.md

## Metrics from Batch Round 2
$(cat _AGENT_WORK/Composer2_*/output/batch_metrics.json)

## Next Steps
→ Signal Opus 4.5 für QA
EOF
```

#### Schritt 5: Completion Signal setzen
```bash
# Signals für Opus 4.5
touch _OUTPUT/.documentation_updated
touch _OUTPUT/.ready_for_qa

# Log Update
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Dokumentation aktualisiert - Signals gesetzt" >> \
  _AGENT_WORK/Composer2_*/progress.log
```

#### Schritt 6: Task Report erstellen
```bash
cat > _AGENT_WORK/Composer2_*/TASK_REPORT_001.md << EOF
# Task Report #001 - Documentation Update

**Agent:** Composer2
**Task:** Update PROJECT_STATUS.md & TODO.md
**Started:** [STARTZEIT]
**Completed:** $(date '+%Y-%m-%d %H:%M:%S')
**Duration:** XX Minuten
**Status:** ✅ COMPLETED

## Durchgeführte Schritte
1. ✅ Batch-Ergebnisse analysiert
2. ✅ PROJECT_STATUS.md aktualisiert
3. ✅ TODO.md aktualisiert
4. ✅ Backup-Dateien erstellt
5. ✅ Änderungs-Log erstellt
6. ✅ Signals gesetzt

## Output Files
- DOCUMENTATION_CHANGES_20251218.md
- PROJECT_STATUS_backup_*.md
- TODO_backup_*.md
- batch_metrics.json

## Signals gesetzt
- ✅ .documentation_updated
- ✅ .ready_for_qa

## Nächster Agent
→ Opus 4.5 kann starten (QA)

## Metriken
| Metrik | Wert |
|--------|------|
| Dateien aktualisiert | 2 |
| Backups erstellt | 2 |
| Dauer | XX Min |
EOF
```

---

## Zeitplan (Geschätzt)

```
JETZT:        Setup + Warten
+2-3 Std:     GPT-5.2 & Composer1 fertig → Signal für Composer2
DANN:         DU STARTEST
  +5 Min:     Batch-Ergebnisse analysieren
  +15 Min:    PROJECT_STATUS.md updaten
  +10 Min:    TODO.md updaten
  +5 Min:     Dokumentation & Signals
DONE:         Signal an Opus 4.5
```

**Erwartete Dauer:** 30-40 Minuten nach Start

---

## ⚠️ Wichtige Warnungen

1. **Backup immer:** Vor Updates IMMER Backup-Dateien erstellen
2. **Validation:** Nach Updates prüfen dass Markdown valide ist
3. **Keine Overwrites:** Backups mit Timestamp, nicht überschreiben
4. **Genaue Metriken:** Zahlen aus Batch-Ergebnissen extrahieren, nicht schätzen

---

## Bei Problemen

### Signal kommt nicht
Prüfe Composer1 Status:
```bash
cat _AGENT_WORK/Composer1_*/STATUS.md
tail -20 _AGENT_WORK/Composer1_*/progress.log
```

### Batch-Ergebnisse fehlen
Prüfe Output-Ordner:
```bash
ls -lh _AGENT_WORK/Composer1_*/output/
```

### Markdown-Fehler
Validiere Syntax:
```bash
# Mit markdownlint (falls installiert)
markdownlint PROJECT_STATUS.md TODO.md
```

---

## Zusammenfassung

**Status:** ⏸️ WAITING
**Nächster Schritt:** Warte auf `.ready_for_documentation_update` Signal
**Danach:** Update Dokumentation (Task #001)
**Geschätzte Wartezeit:** 2-3 Stunden

---

**Viel Erfolg! 📝**

Sobald das Signal kommt, arbeite die Schritte oben Schritt für Schritt ab.
