# 🤖 Agent Work Directory - Koordination & Tracking

**Zweck:** Zentrale Koordination für Multi-Agent-Workflows
**Erstellt:** 2025-12-18
**Version:** 1.0

---

## 📁 Ordnerstruktur

```
_AGENT_WORK/
├── README.md                           # Diese Datei
├── ACTIVE_AGENTS.txt                   # Registry aller aktiven Agents
├── monitoring_dashboard.sh             # Monitoring Script
│
├── <AgentName>_YYYYMMDD_HHMMSS/       # Ein Ordner pro Agent
│   ├── STATUS.md                       # Human-readable Status
│   ├── COORDINATION.json               # Machine-readable Koordination
│   ├── progress.log                    # Chronologisches Log
│   │
│   ├── input/                          # Eingehende Aufgaben
│   │   └── NEXT_TASK_XXX.md           # Neue Aufgaben vom Coordinator
│   │
│   ├── output/                         # Ergebnisse
│   │   ├── *.json                     # Daten-Outputs
│   │   └── *.md                       # Dokumentation
│   │
│   └── logs/                           # Detaillierte Logs
│       ├── task_XXX.log               # Pro-Task Logs
│       └── errors.log                 # Fehler-Tracking
│
└── ARCHIVE/                            # Abgeschlossene Agent-Sessions
    └── <AgentName>_YYYYMMDD_HHMMSS/   # Archivierte Ordner
```

---

## 🚀 Quick Start für Agents

### 1. Setup-Script ausführen

```bash
#!/bin/bash
AGENT_NAME="DeinAgentName"  # z.B. GPT52, Composer1, etc.
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORK_DIR="_AGENT_WORK/${AGENT_NAME}_${TIMESTAMP}"

# Erstelle Ordner
mkdir -p "$WORK_DIR"/{input,output,logs}
cd "$WORK_DIR"

# Erstelle Standard-Dateien
cat > STATUS.md << EOF
# Agent Status Report - ${AGENT_NAME}
**Started:** $(date '+%Y-%m-%d %H:%M:%S')
**Status:** 🟢 ACTIVE
EOF

cat > COORDINATION.json << EOF
{
  "agent_name": "${AGENT_NAME}",
  "work_dir": "$(pwd)",
  "started_at": "$(date -Iseconds)",
  "status": "active"
}
EOF

touch progress.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Agent ${AGENT_NAME} initialized" >> progress.log

# Registriere Agent
echo "${AGENT_NAME}:${AGENT_NAME}_${TIMESTAMP}" >> ../ACTIVE_AGENTS.txt

echo "✅ Setup complete! Work dir: $WORK_DIR"
```

### 2. Während der Arbeit

**Nach jedem Schritt:**
```bash
echo "[$(date '+%Y-%m-%d %H:%M:%S')] SCHRITT_BESCHREIBUNG" >> progress.log
```

**Bei Task-Completion:**
```bash
# Task Report erstellen
cat > TASK_REPORT_XXX.md << EOF
# Task Report #XXX
**Task:** TASK_NAME
**Completed:** $(date '+%Y-%m-%d %H:%M:%S')
**Status:** ✅ COMPLETED
...
EOF
```

**Bei Sync Points:**
```bash
# Flag-Datei erstellen
touch ../../_OUTPUT/.sync_point_name

# Log update
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync Point erreicht: sync_point_name" >> progress.log
```

---

## 📊 Monitoring

### Live Dashboard
```bash
./monitoring_dashboard.sh
```

### Kontinuierliches Monitoring
```bash
watch -n 10 ./monitoring_dashboard.sh
```

### Einzelner Agent
```bash
# Status
cat GPT52_*/STATUS.md

# Recent Progress
tail -f GPT52_*/progress.log

# Outputs
ls -lh GPT52_*/output/
```

---

## 📝 Datei-Templates

### STATUS.md Template
```markdown
# Agent Status Report - [AGENT_NAME]

**Agent:** [NAME]
**Started:** [TIMESTAMP]
**Status:** 🟢 ACTIVE
**Role:** [BESCHREIBUNG]

## Current Task
[BESCHREIBUNG]

## Progress Log
- [TIME] Step 1 completed
- [TIME] Step 2 in progress

## Output Files Created
| Datei | Größe | Beschreibung |
|-------|-------|--------------|
| output/file.json | 100KB | Beschreibung |

## Next Steps
1. [STEP 1]
2. [STEP 2]
```

### TASK_REPORT_XXX.md Template
```markdown
# Task Report #XXX - [TASK_NAME]

**Agent:** [NAME]
**Task ID:** XXX
**Started:** [START_TIME]
**Completed:** [END_TIME]
**Duration:** [MINUTES] Minuten
**Status:** ✅ COMPLETED

## Aufgabe
[BESCHREIBUNG]

## Durchgeführte Schritte
1. ✅ Step 1
2. ✅ Step 2

## Ergebnisse
- Output 1: [DATEI]
- Output 2: [DATEI]

## Metriken
| Metrik | Wert |
|--------|------|
| Items processed | XX |
| Files created | X |

## Nächste Schritte
[BESCHREIBUNG]
```

### NEXT_TASK_XXX.md Template
```markdown
# Nächste Aufgabe #XXX für [AGENT]

**Erstellt:** [TIMESTAMP]
**Von:** Coordinator
**Priorität:** 🔴 HOCH

## Aufgabe
[BESCHREIBUNG]

## Input
- Datei 1
- Datei 2

## Output
- Zu erstellen: output/result.json

## Schritte
1. Step 1
2. Step 2

## Validierung
- [ ] Check 1
- [ ] Check 2

## Zeitschätzung
[DAUER]
```

---

## 🔄 Workflow-Übersicht

```
START
  │
  ├─ Agent Setup (JEDES MAL NEU!)
  │   ├─ Ordner erstellen: <Name>_<Timestamp>
  │   ├─ STATUS.md initialisieren
  │   ├─ COORDINATION.json erstellen
  │   └─ In ACTIVE_AGENTS.txt registrieren
  │
  ├─ Task Execution
  │   ├─ NEXT_TASK_XXX.md aus input/ lesen
  │   ├─ Arbeit durchführen
  │   ├─ progress.log aktualisieren
  │   └─ Outputs in output/ speichern
  │
  ├─ Sync Points
  │   ├─ Flag-Datei in _OUTPUT/ erstellen
  │   ├─ COORDINATION.json aktualisieren
  │   └─ Auf andere Agents warten (falls nötig)
  │
  ├─ Task Completion
  │   ├─ TASK_REPORT_XXX.md erstellen
  │   ├─ STATUS.md aktualisieren
  │   └─ COORDINATION.json finalisieren
  │
  └─ Archive (Optional)
      └─ Ordner nach ARCHIVE/ verschieben
```

---

## 🚨 Wichtige Regeln

1. **Eindeutige Namen:** Jeder Agent-Run hat eigenen Ordner mit Timestamp
2. **Keine Überschreibungen:** Alte Agent-Ordner NICHT löschen
3. **Regelmäßige Updates:** progress.log alle 5-10 Minuten
4. **Sync Points:** IMMER Flag-Datei + COORDINATION.json
5. **Output-Ordner:** Alle Outputs in `output/`, nicht woanders

---

## 📈 Erfolgs-Metriken

**Am Ende eines erfolgreichen Multi-Agent-Workflows:**

```
✅ Alle 4 Agents haben eigene Ordner
✅ Alle STATUS.md zeigen "completed"
✅ Alle TASK_REPORT_XXX.md vorhanden
✅ Alle Sync Points erreicht (Flag-Dateien in _OUTPUT/)
✅ Monitoring Dashboard zeigt 100% Completion
```

---

## 🔍 Troubleshooting

### Problem: Agent findet keine Input-Dateien
**Lösung:** Prüfe ob im richtigen Arbeitsordner: `pwd` sollte `.../Agent_TIMESTAMP/` sein

### Problem: Sync Point wird nicht erreicht
**Lösung:**
1. Prüfe Flag-Datei: `ls -la _OUTPUT/.sync_point_name`
2. Prüfe COORDINATION.json: `cat COORDINATION.json | grep sync_points`

### Problem: Monitoring Script zeigt nichts
**Lösung:** Prüfe ACTIVE_AGENTS.txt: `cat ACTIVE_AGENTS.txt`

---

## 📞 Support

Bei Fragen oder Problemen:
1. Check README.md (diese Datei)
2. Check AGENT_COORDINATION_SETUP.md (Setup-Anleitung)
3. Check monitoring_dashboard.sh Output
4. Check individual Agent STATUS.md files

---

**Erstellt:** 2025-12-18
**Maintainer:** System Coordinator
**Version:** 1.0

🚀 **Ready to coordinate! Start your agents now!**
