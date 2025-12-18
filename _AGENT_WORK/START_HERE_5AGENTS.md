# 🚀 START HERE - 5-Agent Workflow

**Erstellt:** 2025-12-18 16:10:00
**Status:** ✅ ALLE PROMPTS BEREIT

---

## Was wurde erstellt?

✅ **2 neue Agent-Ordner** mit kompletter Struktur
✅ **3 detaillierte Prompt-Dateien** (TASK_*.md)
✅ **1 Workflow-Übersicht** (AGENT_PROMPTS_5AGENTS.md)
✅ **1 Quick-Start-Guide** (diese Datei)

---

## Deine 5 Agents

| # | Agent | Tool | Status | Ordner |
|---|-------|------|--------|--------|
| 1 | **GPT-5.2 #1** | Cursor | 🟢 AKTIV | GPT52_20251218_142539 |
| 2 | **GPT-5.2 #2** | Cursor | ⏸️ WARTET | GPT52_Batch_20251218_155448 |
| 3 | **Opus 4.5 #1** | Cursor | ⏸️ WARTET | Opus45_20251218_142539 |
| 4 | **Opus 4.5 #2** | Cursor | ⏸️ WARTET | Opus45_Docs_20251218_155454 |
| 5 | **Claude Code** | Terminal | 🟢 LÄUFT | - (das bin ich!) |

---

## Was du JETZT tun sollst

### Schritt 1: Warte auf GPT-5.2 #1 ⏰

**Er arbeitet gerade an:** Task #002 (Vorbereitung Phase 1)

**Erwartet:** batch_round2_input_20251218.json (60 Items)

**Dauer:** ~10-15 Minuten ab jetzt

**Prüfen:**
```bash
ls -lh _AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json
```

✅ **Sobald diese Datei existiert → Weiter zu Schritt 2!**

---

### Schritt 2: Starte GPT-5.2 #2 (Batch Executor)

**Öffne:** Neuen Cursor Agent (GPT-5.2 Modell)

**Gib ihm diesen Prompt:**

```
Du bist GPT-5.2 #2 - Batch Executor.

Führe Batch-Runde 2 durch (60 Items automatisch korrigieren).

Lies und führe ALLE Schritte aus:
_AGENT_WORK/GPT52_Batch_20251218_155448/input/TASK_BATCH_EXECUTION.md

Arbeite Schritt 1-9 nacheinander ab:
1. Input validieren
2. Batch-Request erstellen
3. Monitoring starten
4. Warten (1-2 Std)
5. Ergebnisse abholen
6. Backup!
7. Merge
8. Validieren
9. Output bereitstellen

WICHTIG: IMMER Backup vor Merge!

Dauer: ~2-3 Stunden
```

**Erwartetes Ergebnis:** Aktualisierte evidenz_antworten.json + Batch-Ergebnisse

---

### Schritt 3: Starte Opus 4.5 #1 (QA) nach GPT-5.2 #2

**Öffne:** Neuen Cursor Agent (Opus 4.5 Modell)

**Gib ihm diesen Prompt:**

```
Du bist Opus 4.5 #1 - Quality Assurance.

Validiere Batch-Korrekturen (Stichproben-QA).

Lies und führe aus:
_AGENT_WORK/Opus45_20251218_142539/input/TASK_QA_VALIDATION.md

Arbeite Schritt 1-6 durch:
1. Wähle 10 zufällige Items
2. Definiere Quality Gates
3. Manuelle Validierung (je 3-5 Min)
4. Aggregiere Ergebnisse
5. Erstelle QA-Report
6. Output bereitstellen

Ziel: Mind. 90% Pass Rate

Dauer: ~60-75 Minuten
```

**Erwartetes Ergebnis:** QA_REPORT_20251218.md + Validation Results

---

### Schritt 4: Starte Opus 4.5 #2 (Docs) nach Opus 4.5 #1

**Öffne:** Neuen Cursor Agent (Opus 4.5 Modell)

**Gib ihm diesen Prompt:**

```
Du bist Opus 4.5 #2 - Documentation.

Aktualisiere Projekt-Dokumentation.

Lies und führe aus:
_AGENT_WORK/Opus45_Docs_20251218_155454/input/TASK_DOCUMENTATION.md

Arbeite Schritt 1-5 durch:
1. QA-Report analysieren
2. PROJECT_STATUS.md updaten
3. TODO.md updaten
4. Final Report erstellen
5. Workflow-Status updaten

WICHTIG: IMMER Backups erstellen!

Dauer: ~30-45 Minuten
```

**Erwartetes Ergebnis:** FINAL_REPORT + Aktualisierte Docs

---

## Timeline (Geschätzt)

```
JETZT (16:10):    Warte auf GPT-5.2 #1
16:25:            Starte GPT-5.2 #2
16:30:            Batch läuft (1-2 Std Wartezeit)
18:05:            Starte Opus 4.5 #1
19:20:            Starte Opus 4.5 #2
19:50:            ✅ FERTIG!
```

**Gesamt:** ~3.5-4 Stunden

---

## Wichtige Dateien (für dich)

### Prompts:
- [AGENT_PROMPTS_5AGENTS.md](AGENT_PROMPTS_5AGENTS.md) - Alle Prompts auf einen Blick

### Detaillierte Task-Beschreibungen:
- [GPT52_Batch_20251218_155448/input/TASK_BATCH_EXECUTION.md](GPT52_Batch_20251218_155448/input/TASK_BATCH_EXECUTION.md) - 9 Schritte
- [Opus45_20251218_142539/input/TASK_QA_VALIDATION.md](Opus45_20251218_142539/input/TASK_QA_VALIDATION.md) - 6 Schritte
- [Opus45_Docs_20251218_155454/input/TASK_DOCUMENTATION.md](Opus45_Docs_20251218_155454/input/TASK_DOCUMENTATION.md) - 5 Schritte

### Monitoring:
```bash
# Status aller Agents
cd _AGENT_WORK
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

## Meine Rolle (Claude Code)

**Ich koordiniere und helfe bei:**
- Monitoring während Batch läuft
- Scripts ausführen wenn nötig
- Bei Problemen eingreifen
- Status-Updates geben

**Du kannst mich jederzeit fragen:**
- "Wie ist der Status?"
- "Kann ich Agent X starten?"
- "Wo finde ich Datei Y?"

---

## Erfolgs-Kriterien

Am Ende solltest du haben:

- ✅ 60 Items korrigiert (67 → 7 verbleibend)
- ✅ QA passed (>= 90% Pass Rate)
- ✅ Dokumentation aktualisiert
- ✅ Coverage ~99-100%
- ✅ Final Report

---

## Bei Problemen

### Agent steckt fest?
→ Check `logs/` Ordner im Agent-Folder

### Datei fehlt?
→ Check `output/` Ordner vom vorherigen Agent

### Script-Fehler?
→ Lies die TASK_*.md Datei für Troubleshooting

### Unsicher?
→ Frag mich (Claude Code)!

---

## Quick Commands

```bash
# Prüfe ob GPT-5.2 #1 fertig ist
ls -lh _AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json

# Prüfe ob GPT-5.2 #2 fertig ist
ls -lh _AGENT_WORK/GPT52_Batch_20251218_155448/output/batch_round2_output_20251218.json

# Prüfe ob Opus 4.5 #1 fertig ist
ls -lh _AGENT_WORK/Opus45_20251218_142539/output/QA_REPORT_20251218.md

# Prüfe ob Opus 4.5 #2 fertig ist
ls -lh _AGENT_WORK/Opus45_Docs_20251218_155454/output/FINAL_REPORT_20251218.md
```

---

## 🎯 Nächster Schritt

**JETZT:** Warte auf GPT-5.2 #1 (~10-15 Min)

**DANN:** Kopiere den Prompt für GPT-5.2 #2 (siehe Schritt 2 oben)

**GOAL:** 67 → 7 Problem-Items in ~4 Stunden! 🚀

---

**Erstellt:** 2025-12-18 16:10:00
**Status:** ✅ READY TO GO
**Nächste Aktion:** Warte auf GPT-5.2 #1

---

🎉 **Alles bereit! Workflow kann starten sobald GPT-5.2 #1 fertig ist!**
