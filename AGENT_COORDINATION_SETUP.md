# 🤖 Agent Coordination Setup - Fortschritts-Tracking

**Erstellt:** 2025-12-18
**Zweck:** Koordination & Fortschritts-Tracking für Multi-Agent-Workflow

---

## 📁 Ordnerstruktur für Agent-Koordination

Jeder Agent erstellt seinen eigenen Arbeitsordner mit **eindeutigem Namen + Timestamp**.

### Benennungskonvention

```
_AGENT_WORK/<agent_name>_<datum>_<uhrzeit>/
```

**Beispiele:**
```
_AGENT_WORK/GPT52_20251218_143022/
_AGENT_WORK/Composer1_20251218_143025/
_AGENT_WORK/Composer2_20251218_143028/
_AGENT_WORK/Opus45_20251218_143030/
```

---

## 🚀 SETUP-ANWEISUNG FÜR ALLE AGENTS

**Kopiere dies und führe es SOFORT aus, bevor du mit deiner Hauptaufgabe beginnst:**

```bash
#!/bin/bash
set -euo pipefail

# === AGENT COORDINATION SETUP ===
# Führe dieses Script SOFORT aus, bevor du mit deiner Arbeit beginnst!

# 1. DEFINIERE DEINEN AGENT-NAMEN
# WICHTIG: Ändere dies auf deinen spezifischen Namen!
AGENT_NAME="GPT52"  # Optionen: GPT52, Composer1, Composer2, Opus45

# 2. ERSTELLE TIMESTAMP
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 3. ERSTELLE ARBEITSORDNER
BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
WORK_DIR="$BASE_DIR/_AGENT_WORK/${AGENT_NAME}_${TIMESTAMP}"

mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

echo "✓ Agent Arbeitsordner erstellt: $WORK_DIR"

# 4. ERSTELLE STANDARD-DATEIEN
cat > STATUS.md << 'EOF'
# Agent Status Report

**Agent:** AGENT_NAME_PLACEHOLDER
**Started:** TIMESTAMP_PLACEHOLDER
**Status:** 🟢 ACTIVE

---

## Current Task
[Wird automatisch aktualisiert]

## Progress Log
- [TIMESTAMP] Setup completed

## Issues
[Keine]

## Next Steps
[Siehe Hauptaufgabe]

---
**Last Updated:** TIMESTAMP_PLACEHOLDER
EOF

# Ersetze Platzhalter
sed -i.bak "s/AGENT_NAME_PLACEHOLDER/$AGENT_NAME/g" STATUS.md
sed -i.bak "s/TIMESTAMP_PLACEHOLDER/$(date '+%Y-%m-%d %H:%M:%S')/g" STATUS.md
rm STATUS.md.bak

# 5. ERSTELLE LOG-DATEI
touch progress.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Agent $AGENT_NAME initialized" >> progress.log

# 6. ERSTELLE INPUT/OUTPUT ORDNER
mkdir -p input output logs

# 7. ERSTELLE COORDINATION FILE
cat > COORDINATION.json << EOF
{
  "agent_name": "$AGENT_NAME",
  "work_dir": "$WORK_DIR",
  "started_at": "$(date -Iseconds)",
  "status": "active",
  "current_task": "initialization",
  "dependencies": [],
  "output_files": [],
  "sync_points_reached": []
}
EOF

# 8. REGISTRIERE AGENT
echo "$AGENT_NAME:$WORK_DIR" >> "$BASE_DIR/_AGENT_WORK/ACTIVE_AGENTS.txt"

# 9. ZEIGE ERFOLG
echo ""
echo "🎉 Agent Setup Complete!"
echo "================================"
echo "Agent Name:     $AGENT_NAME"
echo "Work Directory: $WORK_DIR"
echo "Status File:    $WORK_DIR/STATUS.md"
echo "Log File:       $WORK_DIR/progress.log"
echo "Coordination:   $WORK_DIR/COORDINATION.json"
echo "================================"
echo ""
echo "Du kannst jetzt mit deiner Hauptaufgabe beginnen!"
echo "WICHTIG: Aktualisiere regelmäßig STATUS.md und progress.log!"
```

---

## 📊 FORTSCHRITTS-TRACKING (Während der Arbeit)

### Jeder Agent muss regelmäßig Updates schreiben:

#### 1. Nach jedem wichtigen Schritt:

```bash
# Update Progress Log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] SCHRITT_BESCHREIBUNG completed" >> progress.log

# Beispiel:
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Vorbereitung: 60 Items für Batch-Runde 2 erstellt" >> progress.log
```

#### 2. Bei Task-Wechsel:

```bash
# Update STATUS.md
cat >> STATUS.md << EOF

## Progress Update - $(date '+%Y-%m-%d %H:%M:%S')
**Current Task:** NEUE_AUFGABE_BESCHREIBUNG
**Previous Task:** ALTE_AUFGABE (✅ COMPLETED)
**Status:** 🟢 ACTIVE

EOF
```

#### 3. Bei Sync Points:

```bash
# Update COORDINATION.json
python3 << PYTHON
import json
from pathlib import Path
from datetime import datetime

coord_file = Path("COORDINATION.json")
data = json.loads(coord_file.read_text())

data["sync_points_reached"].append({
    "name": "ready_for_batch_round2",
    "timestamp": datetime.now().isoformat(),
    "status": "reached"
})

data["status"] = "waiting"
data["current_task"] = "Warte auf Composer1 Signal"

coord_file.write_text(json.dumps(data, indent=2))
PYTHON

# Erstelle Flag-Datei
touch "$BASE_DIR/_OUTPUT/.ready_for_batch_round2"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync Point erreicht: ready_for_batch_round2" >> progress.log
```

#### 4. Bei Completion:

```bash
# Update COORDINATION.json
python3 << PYTHON
import json
from pathlib import Path
from datetime import datetime

coord_file = Path("COORDINATION.json")
data = json.loads(coord_file.read_text())

data["status"] = "completed"
data["completed_at"] = datetime.now().isoformat()
data["current_task"] = "FINISHED"

coord_file.write_text(json.dumps(data, indent=2))
PYTHON

# Final Status Update
cat >> STATUS.md << EOF

## FINAL STATUS - $(date '+%Y-%m-%d %H:%M:%S')
**Status:** ✅ COMPLETED
**Total Duration:** [BERECHNE DAUER]

### Summary
- [Liste alle erledigten Tasks]
- [Wichtige Outputs]
- [Probleme/Lösungen]

EOF
```

---

## 📂 Ordnerstruktur im Detail

```
_AGENT_WORK/
├── ACTIVE_AGENTS.txt                    # Registry aller aktiven Agents
├── GPT52_20251218_143022/
│   ├── STATUS.md                        # Human-readable Status
│   ├── COORDINATION.json                # Machine-readable Coordination
│   ├── progress.log                     # Chronologisches Log
│   ├── input/                           # Input-Dateien für diesen Agent
│   │   └── [vom Coordinator bereitgestellt]
│   ├── output/                          # Output-Dateien von diesem Agent
│   │   ├── batch_round2_input_20251218.json
│   │   └── manual_review_items_20251218.json
│   └── logs/                            # Detaillierte Logs
│       ├── batch_correction.log
│       └── errors.log
├── Composer1_20251218_143025/
│   ├── STATUS.md
│   ├── COORDINATION.json
│   ├── progress.log
│   ├── input/
│   ├── output/
│   │   ├── batch_corrected_round2_*.json
│   │   └── batch_validated_round2_*.json
│   └── logs/
├── Composer2_20251218_143028/
│   ├── STATUS.md
│   ├── COORDINATION.json
│   ├── progress.log
│   ├── input/
│   ├── output/
│   │   ├── PROJECT_STATUS_updated.md
│   │   └── TODO_updated.md
│   └── logs/
└── Opus45_20251218_143030/
    ├── STATUS.md
    ├── COORDINATION.json
    ├── progress.log
    ├── input/
    ├── output/
    │   ├── quality_gate_report_*.json
    │   └── qa_recommendations_*.md
    └── logs/
```

---

## 🔍 COORDINATOR MONITORING SCRIPT

**Für dich (Human) oder einen Coordinator-Agent:**

```bash
#!/bin/bash
# monitoring.sh - Überwache alle Agents

BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"

echo "=== AGENT MONITORING DASHBOARD ==="
echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Lese alle aktiven Agents
while IFS=: read -r agent_name work_dir; do
    if [ -d "$work_dir" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Agent: $agent_name"
        echo "Work Dir: $work_dir"

        # Lese COORDINATION.json
        if [ -f "$work_dir/COORDINATION.json" ]; then
            status=$(python3 -c "import json; print(json.load(open('$work_dir/COORDINATION.json'))['status'])")
            task=$(python3 -c "import json; print(json.load(open('$work_dir/COORDINATION.json'))['current_task'])")

            echo "Status: $status"
            echo "Current Task: $task"
        fi

        # Zeige letzte 3 Log-Einträge
        if [ -f "$work_dir/progress.log" ]; then
            echo ""
            echo "Recent Progress:"
            tail -3 "$work_dir/progress.log" | sed 's/^/  /'
        fi

        # Zeige Output-Dateien
        if [ -d "$work_dir/output" ]; then
            echo ""
            echo "Output Files:"
            ls -lh "$work_dir/output" 2>/dev/null | tail -n +2 | sed 's/^/  /'
        fi

        echo ""
    fi
done < "$BASE_DIR/_AGENT_WORK/ACTIVE_AGENTS.txt"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Prüfe Sync Points
echo "=== SYNC POINTS STATUS ==="
for flag in .ready_for_batch_round2 .batch_round2_started .batch_round2_complete .ready_for_documentation_update .documentation_updated .ready_for_qa .qa_complete; do
    if [ -f "$BASE_DIR/_OUTPUT/$flag" ]; then
        timestamp=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$BASE_DIR/_OUTPUT/$flag")
        echo "✓ $flag (reached at $timestamp)"
    else
        echo "⏳ $flag (pending)"
    fi
done
```

**Ausführung:**
```bash
chmod +x monitoring.sh
./monitoring.sh

# Oder kontinuierlich überwachen:
watch -n 10 ./monitoring.sh
```

---

## 📝 TEMPLATE FÜR NÄCHSTE AUFGABEN

**Wenn du einem Agent eine neue Aufgabe geben willst:**

```bash
# Beispiel: Neue Aufgabe für GPT-5.2

AGENT_DIR=$(ls -dt _AGENT_WORK/GPT52_* | head -1)

cat > "$AGENT_DIR/input/NEXT_TASK.md" << 'EOF'
# Neue Aufgabe für GPT-5.2

**Erstellt:** $(date '+%Y-%m-%d %H:%M:%S')
**Priorität:** 🔴 HOCH

## Aufgabe
Führe die manuelle Review der 7 hochkomplexen Items durch.

## Input
- `_AGENT_WORK/GPT52_*/output/manual_review_items_20251218.json`

## Output
Erstelle:
- `output/manual_corrections_20251218.json`
- `output/manual_review_report.md`

## Schritte
1. Für jedes der 7 Items:
   - Recherchiere aktuelle Leitlinien
   - Korrigiere Antwort
   - Validiere Quellen
2. Speichere Korrekturen
3. Erstelle Bericht

## Deadline
Heute, 18:00 Uhr

---
**Erstellt von:** Coordinator
EOF

# Signal an Agent
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Neue Aufgabe: Siehe input/NEXT_TASK.md" >> "$AGENT_DIR/progress.log"
```

---

## ✅ CHECKLIST FÜR JEDEN AGENT

**Vor dem Start:**
- [ ] Setup-Script ausgeführt
- [ ] Arbeitsordner mit Name + Timestamp erstellt
- [ ] STATUS.md initialisiert
- [ ] COORDINATION.json erstellt
- [ ] progress.log angelegt

**Während der Arbeit:**
- [ ] Nach jedem Schritt: progress.log aktualisieren
- [ ] Bei Task-Wechsel: STATUS.md aktualisieren
- [ ] Bei Sync Points: COORDINATION.json + Flag-Datei
- [ ] Output-Dateien in `output/` ablegen
- [ ] Logs in `logs/` schreiben

**Nach Completion:**
- [ ] COORDINATION.json auf "completed" setzen
- [ ] Final Summary in STATUS.md
- [ ] Alle Output-Dateien dokumentiert
- [ ] progress.log abgeschlossen

---

## 🚨 WICHTIGE REGELN

1. **Eindeutige Namen:** Jeder Agent MUSS seinen eigenen Ordner mit Timestamp haben
2. **Keine Überschreibungen:** Alte Agent-Ordner NIEMALS löschen (für Audit-Trail)
3. **Regelmäßige Updates:** Mindestens alle 15 Minuten progress.log aktualisieren
4. **Sync Points:** IMMER COORDINATION.json + Flag-Datei aktualisieren
5. **Output-Dateien:** Alle Outputs in `output/` Ordner, nicht irgendwo anders

---

## 📊 ERFOLGS-METRIKEN

Am Ende des Workflows solltest du sehen können:

```
_AGENT_WORK/
├── ACTIVE_AGENTS.txt (4 Einträge)
├── GPT52_20251218_143022/ (✅ completed)
├── Composer1_20251218_143025/ (✅ completed)
├── Composer2_20251218_143028/ (✅ completed)
└── Opus45_20251218_143030/ (✅ completed)

_OUTPUT/
├── .ready_for_batch_round2 (✓)
├── .batch_round2_started (✓)
├── .batch_round2_complete (✓)
├── .ready_for_documentation_update (✓)
├── .documentation_updated (✓)
├── .ready_for_qa (✓)
└── .qa_complete (✓)
```

**Alle Agents haben ihre Arbeit dokumentiert und koordiniert abgeschlossen!** ✅

---

**Erstellt:** 2025-12-18
**Version:** 1.0
**Status:** Ready for Use

🚀 **Kopiere das Setup-Script und starte jetzt!**
