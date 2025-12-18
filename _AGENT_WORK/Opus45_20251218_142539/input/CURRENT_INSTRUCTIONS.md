# Current Instructions für Opus 4.5 (QA Agent)

**Erstellt:** 2025-12-18 15:00:00
**Von:** Coordinator
**Für:** Opus 4.5 (Quality Assurance)
**Priorität:** 🟡 MITTEL (Warte-Modus)
**Status:** ⏳ WARTEN AUF SIGNAL

---

## Aktuelle Situation

Du bist **Opus 4.5**, der Quality Assurance Agent im Multi-Agent-Workflow.

**Deine Rolle:** Final QA & Validation nach allen Batch-Korrekturen und Dokumentations-Updates.

---

## WICHTIG: Noch NICHT starten!

⚠️ **Du musst WARTEN auf Sync Point:** `.ready_for_qa`

**Workflow-Position:**
```
1. GPT-5.2 (Lead) ──────────> ✅ Task #001 DONE
                               ⏳ Task #002 IN PROGRESS
2. Composer1 (Batch) ───────> ⏸️ Wartet auf GPT-5.2 Signal
3. Composer2 (Docs) ────────> ⏸️ Wartet auf Batch Completion
4. Opus 4.5 (QA) ───────────> ⏸️ DU BIST HIER - Wartet auf Docs
```

---

## Was du JETZT tun sollst

### 1. Setup ausführen ✅

Wenn du das noch nicht getan hast, führe dein Agent-Setup aus:

```bash
#!/bin/bash
set -euo pipefail

AGENT_NAME="Opus45"
BASE_DIR="/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
WORK_DIR="$BASE_DIR/_AGENT_WORK/${AGENT_NAME}_${TIMESTAMP}"

# Erstelle Ordner (falls noch nicht vorhanden)
mkdir -p "$WORK_DIR"/{input,output,logs}
cd "$WORK_DIR"

# STATUS.md
cat > STATUS.md << EOF
# Agent Status Report - ${AGENT_NAME}

**Agent:** ${AGENT_NAME}
**Started:** $(date '+%Y-%m-%d %H:%M:%S')
**Status:** ⏸️ WAITING
**Role:** Quality Assurance - Final Validation

## Current Task
Warte auf Sync Point: .ready_for_qa

## Progress Log
- [$(date '+%Y-%m-%d %H:%M:%S')] Setup completed
- [$(date '+%Y-%m-%d %H:%M:%S')] Waiting for Composer2 signal

## Next Steps
Nach Signal: Starte QA Task #001
EOF

# COORDINATION.json
cat > COORDINATION.json << EOF
{
  "agent_name": "${AGENT_NAME}",
  "role": "QA - Quality Assurance",
  "work_dir": "${WORK_DIR}",
  "started_at": "$(date -Iseconds)",
  "status": "waiting",
  "current_task": "Warte auf .ready_for_qa Signal",
  "completed_tasks": [],
  "dependencies": ["Composer2"],
  "waiting_for": [".ready_for_qa"],
  "blocking": [],
  "output_files": [],
  "sync_points_reached": [],
  "sync_points_pending": ["ready_for_qa", "qa_complete"],
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
echo "🎉 Opus 4.5 Setup Complete!"
echo "================================"
echo "Status: WAITING for .ready_for_qa"
echo "Work Directory: ${WORK_DIR}"
echo "================================"
```

### 2. Auf Signal warten

**Monitoring-Loop starten:**

```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Option 1: Manuell prüfen
watch -n 20 'ls -la _OUTPUT/.ready_for_qa 2>/dev/null && echo "✅ SIGNAL ERHALTEN!" || echo "⏳ Noch warten..."'

# Option 2: Blocking wait
while [ ! -f "_OUTPUT/.ready_for_qa" ]; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warte auf .ready_for_qa..."
  sleep 30
done
echo "✅ Signal erhalten! QA kann starten."
```

### 3. Während des Wartens (Optional)

Du kannst bereits folgendes vorbereiten:

**a) QA-Checkliste erstellen:**
```bash
cat > _AGENT_WORK/Opus45_*/output/QA_CHECKLIST_TEMPLATE.md << 'EOF'
# QA Checklist - Batch Round 2 Validation

## Stichproben-Validierung (10 Items)

### Items zu prüfen:
- [ ] Item 1: [ID] - [Kategorie]
- [ ] Item 2: [ID] - [Kategorie]
- [ ] Item 3: [ID] - [Kategorie]
- [ ] Item 4: [ID] - [Kategorie]
- [ ] Item 5: [ID] - [Kategorie]
- [ ] Item 6: [ID] - [Kategorie]
- [ ] Item 7: [ID] - [Kategorie]
- [ ] Item 8: [ID] - [Kategorie]
- [ ] Item 9: [ID] - [Kategorie]
- [ ] Item 10: [ID] - [Kategorie]

## Quality Gates

### 1. Fachliche Korrektheit ✓
- [ ] Leitlinien-Konformität (2024/2025)
- [ ] STIKO-Empfehlungen aktuell
- [ ] Dosierungen korrekt
- [ ] Keine veralteten Informationen

### 2. Vollständigkeit ✓
- [ ] Alle relevanten Infos vorhanden
- [ ] Keine fehlenden Angaben
- [ ] Kontext ausreichend

### 3. Formatierung ✓
- [ ] JSON-Struktur valide
- [ ] Markdown korrekt
- [ ] Keine Encoding-Fehler

### 4. Dokumentation ✓
- [ ] PROJECT_STATUS.md aktualisiert
- [ ] TODO.md aktualisiert
- [ ] Alle Änderungen dokumentiert

## Erfolgs-Kriterien
- Mind. 90% der Stichproben = korrekt
- Alle Quality Gates = PASSED
- Dokumentation = vollständig
EOF
```

**b) Monitoring Dashboard beobachten:**
```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617/_AGENT_WORK
./monitoring_dashboard.sh
```

---

## Sobald Signal kommt (.ready_for_qa existiert)

Du bekommst dann eine neue Aufgabe:

**`input/QA_TASK_001.md`** wird erstellt mit:
- 10 Items für Stichproben-Validierung
- Quality Gate Checkliste
- Detaillierte Prüfschritte
- Validierungs-Scripts

---

## Deine Haupt-Aufgabe (SPÄTER)

### Task #001: Quality Gate Durchführung

**Schritte:**
1. Stichproben auswählen (10 Items aus batch_round2_output)
2. Fachliche Korrektheit prüfen
3. Leitlinien-Konformität validieren
4. Dokumentation prüfen (PROJECT_STATUS, TODO)
5. Quality Report erstellen
6. Signal setzen: `.qa_complete`

**Output:**
- `output/QA_REPORT_20251218.md`
- `output/qa_validation_results.json`
- Signal: `_OUTPUT/.qa_complete`

---

## Wichtige Dateien für QA (SPÄTER)

Zu prüfen:
- `_OUTPUT/batch_round2_output_TIMESTAMP.json` (60 korrigierte Items)
- `PROJECT_STATUS.md` (Update von Composer2)
- `TODO.md` (Update von Composer2)
- `_AGENT_WORK/Composer1_*/output/*` (Batch-Logs)

---

## Zeitplan (Geschätzt)

```
JETZT:        Setup + Warten
+2-3 Std:     GPT-5.2 fertig → Signal für Composer1
+2-3 Std:     Composer1 fertig (Batch) → Signal für Composer2
+30 Min:      Composer2 fertig (Docs) → Signal für Opus 4.5
DANN:         DU STARTEST (QA Task #001)
Dauer QA:     1-2 Stunden
```

**Erwarteter Start:** ca. 2025-12-18 19:00-20:00

---

## Progress Updates

Während du wartest, aktualisiere regelmäßig:

```bash
# Alle 30 Minuten
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Warte weiter auf .ready_for_qa Signal" >> \
  _AGENT_WORK/Opus45_*/progress.log
```

---

## Bei Problemen

### Signal kommt nicht
1. Prüfe Composer2 Status: `cat _AGENT_WORK/Composer2_*/STATUS.md`
2. Prüfe Composer1 Status: `cat _AGENT_WORK/Composer1_*/STATUS.md`
3. Prüfe Monitoring: `./monitoring_dashboard.sh`

### Fragen zur Aufgabe
1. Lies: `AGENT_COORDINATION_SETUP.md` > "Agent 4: Opus 4.5"
2. Lies: `_AGENT_WORK/README.md`
3. Check: `_AGENT_WORK/GPT52_*/TASK_REPORT_001.md` (Kontext)

---

## Zusammenfassung

**Status:** ⏸️ WAITING
**Nächster Schritt:** Warte auf `.ready_for_qa` Signal
**Danach:** Starte QA Task #001
**Geschätzte Wartezeit:** 5-7 Stunden

---

**Viel Erfolg beim Warten! 😊**

Sobald das Signal kommt, erhältst du detaillierte Anweisungen in `input/QA_TASK_001.md`.
