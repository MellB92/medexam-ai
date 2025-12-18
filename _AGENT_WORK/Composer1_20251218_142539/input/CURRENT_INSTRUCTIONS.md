# Current Instructions für Composer 1 (Batch Coordinator)

**Erstellt:** 2025-12-18 15:00:00
**Von:** Coordinator
**Für:** Composer 1 (Batch Round 2 Coordinator)
**Priorität:** 🟡 MITTEL (Warte-Modus)
**Status:** ⏳ WARTEN AUF SIGNAL

---

## Aktuelle Situation

Du bist **Composer 1**, der Batch Coordinator im Multi-Agent-Workflow.

**Deine Rolle:** Koordination und Ausführung der Batch-Runde 2 (60 Items mit niedriger/mittlerer Komplexität).

---

## WICHTIG: Noch NICHT starten!

⚠️ **Du musst WARTEN auf Sync Point:** `.ready_for_batch_round2`

**Workflow-Position:**
```
1. GPT-5.2 (Lead) ──────────> ✅ Task #001 DONE
                               ⏳ Task #002 IN PROGRESS (Vorbereitung)
2. Composer1 (Batch) ───────> ⏸️ DU BIST HIER - Wartet auf GPT-5.2 Signal
3. Composer2 (Docs) ────────> ⏸️ Wartet auf Batch Completion
4. Opus 4.5 (QA) ───────────> ⏸️ Wartet auf Docs
```

---

## Was du JETZT tun sollst

### 1. Setup ausführen ✅

Wenn du das noch nicht getan hast, führe dein Agent-Setup aus:

```bash
#!/bin/bash
set -euo pipefail

AGENT_NAME="Composer1"
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
**Role:** Batch Coordinator - Round 2 (60 Items)

## Current Task
Warte auf Sync Point: .ready_for_batch_round2

## Progress Log
- [$(date '+%Y-%m-%d %H:%M:%S')] Setup completed
- [$(date '+%Y-%m-%d %H:%M:%S')] Waiting for GPT-5.2 signal

## Next Steps
Nach Signal: Starte Batch-Runde 2
EOF

# COORDINATION.json
cat > COORDINATION.json << EOF
{
  "agent_name": "${AGENT_NAME}",
  "role": "Batch Coordinator - Round 2",
  "work_dir": "${WORK_DIR}",
  "started_at": "$(date -Iseconds)",
  "status": "waiting",
  "current_task": "Warte auf .ready_for_batch_round2 Signal",
  "completed_tasks": [],
  "dependencies": ["GPT52"],
  "waiting_for": [".ready_for_batch_round2"],
  "blocking": ["Composer2", "Opus45"],
  "output_files": [],
  "sync_points_reached": [],
  "sync_points_pending": ["ready_for_batch_round2", "batch_round2_complete"],
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
echo "🎉 Composer 1 Setup Complete!"
echo "================================"
echo "Status: WAITING for .ready_for_batch_round2"
echo "Work Directory: ${WORK_DIR}"
echo "================================"
```

### 2. Auf Signal warten

**Monitoring-Loop starten:**

```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Option 1: Manuell prüfen
watch -n 10 'ls -la _OUTPUT/.ready_for_batch_round2 2>/dev/null && echo "✅ SIGNAL ERHALTEN!" || echo "⏳ Noch warten..."'

# Option 2: Blocking wait
while [ ! -f "_OUTPUT/.ready_for_batch_round2" ]; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warte auf .ready_for_batch_round2..."
  sleep 20
done
echo "✅ Signal erhalten! Batch kann starten."
```

### 3. Während des Wartens (Optional)

Du kannst bereits folgendes vorbereiten:

**a) Batch-Scripts validieren:**
```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Prüfe ob Scripts existieren
ls -lh batch_medexamen_reviewer_v2.py
ls -lh batch_request_manager_v2.py
ls -lh batch_continue_monitor.py

# Prüfe ob API-Keys gesetzt sind
python3 -c "import os; print('✅ API Key OK' if os.getenv('ANTHROPIC_API_KEY') else '❌ API Key fehlt')"
```

**b) Test-Run vorbereiten (NICHT ausführen!):**
```bash
# Nur lesen, NICHT ausführen!
cat batch_medexamen_reviewer_v2.py | head -50

# Verstehe die Parameter
grep -A 10 "argparse" batch_medexamen_reviewer_v2.py
```

---

## Sobald Signal kommt (.ready_for_batch_round2 existiert)

### Input-Datei abholen

GPT-5.2 hat für dich vorbereitet:
- `_AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json` (60 Items)

**Diese Datei musst du verwenden!**

---

## Deine Haupt-Aufgabe (NACH Signal)

### Task #001: Batch-Runde 2 durchführen

**Ziel:** 60 Items mit niedriger/mittlerer Komplexität korrigieren.

#### Schritt 1: Start-Signal setzen
```bash
# Signal an andere Agents
touch _OUTPUT/.batch_round2_started

# Log Update
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch-Runde 2 gestartet" >> \
  _AGENT_WORK/Composer1_*/progress.log
```

#### Schritt 2: Input validieren
```bash
# Prüfe Input-Datei
INPUT_FILE="_AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json"

# Validierung
python3 << EOF
import json
from pathlib import Path

data = json.loads(Path('$INPUT_FILE').read_text())
print(f"✓ Items gefunden: {data['count']}")
print(f"✓ Komplexität: {data['complexity']}")
print(f"✓ Focus: {', '.join(data['focus'])}")

assert data['count'] == 60, f"Erwartet 60 Items, gefunden {data['count']}"
print("✅ Input-Validierung OK")
EOF
```

#### Schritt 3: Batch-Request erstellen
```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Batch-Request starten
python3 batch_medexamen_reviewer_v2.py \
  --input "_AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json" \
  --run-name "batch_round2_20251218" \
  --focus leitlinien_updates_2024_2025 stiko_empfehlungen \
  --output "_AGENT_WORK/Composer1_20251218_*/output/batch_request_metadata.json"

# Speichere Batch-ID
BATCH_ID=$(cat _AGENT_WORK/Composer1_*/output/batch_request_metadata.json | python3 -c "import sys,json; print(json.load(sys.stdin)['batch_id'])")
echo "Batch-ID: $BATCH_ID"
echo "$BATCH_ID" > _AGENT_WORK/Composer1_*/output/BATCH_ID.txt
```

#### Schritt 4: Monitoring starten
```bash
# Monitor-Script starten (läuft im Hintergrund)
python3 batch_continue_monitor.py \
  --batch-id "$BATCH_ID" \
  --check-interval 30 \
  --log-file "_AGENT_WORK/Composer1_*/logs/batch_monitor.log" \
  > _AGENT_WORK/Composer1_*/output/batch_monitor_output.txt 2>&1 &

# PID speichern
echo $! > _AGENT_WORK/Composer1_*/output/MONITOR_PID.txt
```

#### Schritt 5: Warten auf Completion
```bash
# Warte bis Batch fertig ist
while true; do
  STATUS=$(python3 batch_request_manager_v2.py --batch-id "$BATCH_ID" --status | grep "status" | cut -d'"' -f4)

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch Status: $STATUS" >> \
    _AGENT_WORK/Composer1_*/progress.log

  if [ "$STATUS" = "ended" ]; then
    echo "✅ Batch completed!"
    break
  fi

  sleep 60  # Prüfe alle 60 Sekunden
done
```

#### Schritt 6: Ergebnisse abholen
```bash
# Download Batch Results
python3 batch_request_manager_v2.py \
  --batch-id "$BATCH_ID" \
  --download \
  --output "_AGENT_WORK/Composer1_*/output/batch_round2_results_20251218.jsonl"

# Konvertiere zu JSON
python3 << EOF
import json
from pathlib import Path

# Lade JSONL
results = []
with open('_AGENT_WORK/Composer1_*/output/batch_round2_results_20251218.jsonl') as f:
    for line in f:
        results.append(json.loads(line))

# Speichere als JSON
output = {
    'batch_id': '$BATCH_ID',
    'completed_at': '$(date -Iseconds)',
    'results_count': len(results),
    'results': results
}

Path('_AGENT_WORK/Composer1_*/output/batch_round2_output_20251218.json').write_text(
    json.dumps(output, indent=2, ensure_ascii=False)
)

print(f"✅ {len(results)} Ergebnisse gespeichert")
EOF
```

#### Schritt 7: Merge mit evidenz_antworten.json
```bash
# WICHTIG: Dies aktualisiert die kanonische Datenbank!
python3 << EOF
import json
from pathlib import Path
from datetime import datetime

# Lade Basis-Daten
evidenz_path = Path('_OUTPUT/evidenz_antworten.json')
evidenz_data = json.loads(evidenz_path.read_text())

# Lade Batch-Ergebnisse
batch_results = json.loads(
    Path('_AGENT_WORK/Composer1_*/output/batch_round2_output_20251218.json').read_text()
)

# Erstelle Backup
backup_path = evidenz_path.parent / f'evidenz_antworten_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
backup_path.write_text(json.dumps(evidenz_data, indent=2, ensure_ascii=False))
print(f"✓ Backup erstellt: {backup_path}")

# Merge Logic hier (siehe batch_medexamen_reviewer_v2.py für Details)
# TODO: Implementiere korrekten Merge basierend auf Item-IDs

print("✅ Merge abgeschlossen")
EOF
```

#### Schritt 8: Completion Signal setzen
```bash
# Signals für nachfolgende Agents
touch _OUTPUT/.batch_round2_complete
touch _OUTPUT/.ready_for_documentation_update

# Log Update
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Batch-Runde 2 abgeschlossen - Signals gesetzt" >> \
  _AGENT_WORK/Composer1_*/progress.log
```

#### Schritt 9: Task Report erstellen
```bash
cat > _AGENT_WORK/Composer1_*/TASK_REPORT_001.md << EOF
# Task Report #001 - Batch Round 2

**Agent:** Composer1
**Task:** Batch-Runde 2 Koordination
**Started:** [STARTZEIT]
**Completed:** $(date '+%Y-%m-%d %H:%M:%S')
**Status:** ✅ COMPLETED

## Ergebnisse
- Items processed: 60
- Batch-ID: $BATCH_ID
- Output: batch_round2_output_20251218.json
- Merge: evidenz_antworten.json aktualisiert

## Metriken
| Metrik | Wert |
|--------|------|
| Success Rate | XX% |
| API Kosten | ~$3.50 |
| Dauer | XX Min |

## Signals gesetzt
- ✅ .batch_round2_complete
- ✅ .ready_for_documentation_update

## Nächster Agent
→ Composer2 kann starten (Dokumentation)
EOF
```

---

## Zeitplan (Geschätzt)

```
JETZT:        Setup + Warten
+15 Min:      GPT-5.2 fertig → Signal für Composer1
DANN:         DU STARTEST
  +5 Min:     Batch-Request erstellen
  +90-120 Min: Batch läuft (Anthropic API)
  +10 Min:    Ergebnisse abholen & mergen
DONE:         Signal an Composer2
```

**Erwartete Dauer:** 2-2.5 Stunden nach Start

---

## ⚠️ Wichtige Warnungen

1. **READ-ONLY bis Merge:** `evidenz_antworten.json` NICHT manuell editieren
2. **Backup immer:** Vor Merge IMMER Backup erstellen
3. **Validation:** Nach Merge validieren dass JSON valide ist
4. **Kosten:** Batch kostet ca. $3.50 - API Key muss Credits haben

---

## Bei Problemen

### Signal kommt nicht
Prüfe GPT-5.2 Status:
```bash
cat _AGENT_WORK/GPT52_*/STATUS.md
tail -20 _AGENT_WORK/GPT52_*/progress.log
```

### Batch-Script Fehler
Prüfe Logs:
```bash
cat _AGENT_WORK/Composer1_*/logs/batch_monitor.log
```

### API Fehler
Prüfe API Key:
```bash
python3 -c "import anthropic; client = anthropic.Anthropic(); print('✅ API OK')"
```

---

## Zusammenfassung

**Status:** ⏸️ WAITING
**Nächster Schritt:** Warte auf `.ready_for_batch_round2` Signal
**Danach:** Starte Batch-Runde 2 (Task #001)
**Geschätzte Wartezeit:** 10-20 Minuten

---

**Viel Erfolg! 🚀**

Sobald das Signal kommt, arbeite die Schritte oben Schritt für Schritt ab.
