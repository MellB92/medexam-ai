# 🤖 Agent Prompts Index - MedExamAI

**Letzte Aktualisierung:** 2025-12-18

Dieser Index verweist auf alle verfügbaren Agent-Prompts für verschiedene AI-Tools, um die Arbeit im MedExamAI-Projekt fortzusetzen.

---

## 📚 Verfügbare Prompts

### 1. Cursor Agent (Vollständig)

**Datei:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md)
**Umfang:** 637 Zeilen (vollständig)
**Für:** Cursor IDE, detaillierte Workflows
**Enthält:**
- ✅ Harte Regeln & Constraints
- ✅ Aktueller Datenstand (4.505 Q&A)
- ✅ Priorisierte Aufgaben (67 Problem-Items)
- ✅ Wichtige Commands (Copy & Paste)
- ✅ Workflows (Problem-Items fixen, Exports, Coverage)
- ✅ Debugging & Troubleshooting
- ✅ Metriken & KPIs
- ✅ Pre-Flight Checklist

**Wann verwenden:** Für intensive Coding-Sessions mit vollständigem Kontext

---

### 2. Cursor Composer (Kompakt)

**Datei:** [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md)
**Umfang:** ~100 Zeilen (kompakt)
**Für:** Cursor Composer, Quick Start
**Enthält:**
- ✅ Harte Regeln (kurz)
- ✅ Aktueller Stand (Überblick)
- ✅ Top 3 Aufgaben
- ✅ Wichtigste Commands
- ✅ DON'Ts & DOs
- ✅ Pre-Flight Check

**Wann verwenden:** Für schnelle Code-Änderungen, wenn du nur das Wichtigste brauchst

---

### 3. Agent Overview (Schnelleinstieg)

**Datei:** [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md)
**Umfang:** ~137 Zeilen
**Für:** Alle AI-Tools (Claude, GPT, Gemini, Codex)
**Enthält:**
- ✅ Harte Constraints
- ✅ Goldstandard-Quellen
- ✅ Zentrale Arbeitsbasis (SRS/Review)
- ✅ needs_context Workflow
- ✅ Batch-Review Pipeline Status
- ✅ Wichtigste Scripts

**Wann verwenden:** Als erste Anlaufstelle für neue Agent-Sessions

---

### 4. Complete Handover

**Datei:** [COMPLETE_HANDOVER.md](COMPLETE_HANDOVER.md)
**Umfang:** ~100 Zeilen
**Für:** Vollständiger Projekt-Übergabe
**Enthält:**
- ✅ Session 4 Update
- ✅ Was du bekommen hast
- ✅ Pre-commit Hooks
- ✅ VSCode Configuration
- ✅ Git Repository Status

**Wann verwenden:** Für historischen Kontext und Setup-Details

---

### 5. CODEX Handover (2025-12-01)

**Datei:** [CODEX_HANDOVER_2025-12-01.md](CODEX_HANDOVER_2025-12-01.md)
**Umfang:** ~300 Zeilen
**Für:** Detaillierter Handover vom 1. Dezember
**Enthält:**
- ✅ Vollständige Projekt-Historie
- ✅ Datenstand zum 1. Dezember
- ✅ Technische Details
- ✅ Lessons Learned

**Wann verwenden:** Für tiefes Verständnis der Projekt-Entwicklung

---

## 🎯 Welchen Prompt soll ich verwenden?

### Schnell-Auswahl

| Szenario | Empfohlener Prompt | Begründung |
|----------|-------------------|------------|
| **Neue Session starten** | [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | Schnelleinstieg, alle wichtigen Infos |
| **Cursor IDE verwenden** | [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md) | Vollständige Workflows & Commands |
| **Cursor Composer** | [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md) | Kompakt für schnelle Änderungen |
| **Claude Code / GPT** | [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | Tool-agnostisch |
| **Projekt übernehmen** | [COMPLETE_HANDOVER.md](COMPLETE_HANDOVER.md) → [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | Kontext + Quick Start |
| **Historischen Kontext** | [CODEX_HANDOVER_2025-12-01.md](CODEX_HANDOVER_2025-12-01.md) | Projekt-Geschichte |

---

## 📋 Empfohlene Reihenfolge (Neue Agents)

### Erste Session

1. **Start:** [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) (5 Min lesen)
2. **Details:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md) (10 Min lesen)
3. **Kontext:** [PROJECT_STATUS.md](PROJECT_STATUS.md) (5 Min lesen)
4. **Aufgaben:** [TODO.md](TODO.md) (3 Min lesen)

**Gesamt:** ~23 Minuten für vollständiges Onboarding

### Folge-Sessions

1. **Quick Start:** [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md) (2 Min)
2. **Bei Bedarf:** [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) für Details

**Gesamt:** ~2-5 Minuten

---

## 🔄 Workflow-spezifische Prompts

### 67 Problem-Items fixen

**Basis-Prompt:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md)
**Relevante Sektion:** "Workflow 1: 67 Problem-Items fixen"
**Zusätzlich:** [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) > "Batch-Review Pipeline"

**Quick Command:**
```bash
# Copy & Paste aus CURSOR_AGENT_PROMPT_20251218.md > Workflow 1
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('_OUTPUT/batch_review_remaining_issues_20251216_142834.json').read_text())
print(f'Problem Items: {len(data)}')
for i, item in enumerate(data[:3], 1):
    print(f'{i}. {item[\"frage\"][:80]}')
"
```

### Lern-Materialien exportieren

**Basis-Prompt:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md)
**Relevante Sektion:** "Workflow 2: Lern-Materialien exportieren"

**Quick Command:**
```bash
python3 scripts/export_learning_materials.py --daily-plan
```

### Coverage validieren

**Basis-Prompt:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md)
**Relevante Sektion:** "Workflow 3: Coverage validieren"

**Quick Command:**
```bash
python3 -c "
import json
from pathlib import Path
mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())
qa_set = set(x['frage'] for x in qa)
matched = sum(1 for x in mm if x['question'] in qa_set)
print(f'Meaningful Coverage: {matched}/{len(mm)} ({matched/len(mm)*100:.1f}%)')
"
```

---

## 🚨 Wichtige Hinweise (für alle Prompts)

### Harte Regeln (immer beachten!)

1. **READ-ONLY:** `_OUTPUT/evidenz_antworten.json` niemals überschreiben
2. **Timestamps:** Neue Outputs mit Timestamp: `_OUTPUT/file_$(date +%Y%m%d_%H%M%S).json`
3. **Secrets:** Keine API-Keys loggen/committen (`.env` existiert)
4. **venv:** Immer aktivieren: `source venv/bin/activate`

### Aktueller Stand (2025-12-16)

- **Q&A:** 4.505 Einträge (kanonisch in `evidenz_antworten.json`)
- **Problem-Items:** 67 (höchste Priorität!)
- **Coverage:** 2.527/2.527 = 100% ✅
- **Review-Queue:** 431 Items (298 needs_review, 133 needs_context)

---

## 📦 Prompt-Pakete für verschiedene Szenarien

### Paket 1: "Schneller Start" (5 Min)

```
1. CURSOR_COMPOSER_PROMPT.md
2. venv aktivieren
3. Pre-Flight Check
→ Ready to code!
```

### Paket 2: "Vollständiges Onboarding" (25 Min)

```
1. AGENT_OVERVIEW.md
2. CURSOR_AGENT_PROMPT_20251218.md
3. PROJECT_STATUS.md
4. TODO.md
→ Vollständig informiert!
```

### Paket 3: "Projekt-Übergabe" (40 Min)

```
1. COMPLETE_HANDOVER.md
2. CODEX_HANDOVER_2025-12-01.md
3. AGENT_OVERVIEW.md
4. CURSOR_AGENT_PROMPT_20251218.md
5. MIGRATION_GUIDE.md
→ Kompletter Kontext!
```

---

## ✅ Pre-Flight Check (vor jeder Session)

```bash
# Kopiere aus CURSOR_COMPOSER_PROMPT.md oder CURSOR_AGENT_PROMPT_20251218.md

pwd  # Sollte: .../Medexamenai_migration_full_20251217_204617
which python3  # Sollte: .../venv/bin/python3
ls -lh _OUTPUT/evidenz_antworten.json  # Sollte: ~11M
grep -c "^OPENAI_API_KEY=" .env  # Sollte: 1
```

**Wenn alle ✅: Ready! 🚀**

---

## 📞 Support & Weitere Ressourcen

| Ressource | Pfad |
|-----------|------|
| Scripts Übersicht | [scripts/README.md](scripts/README.md) (falls vorhanden) |
| Entwickler-Guide | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Migration History | [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) |
| Projekt-Status | [PROJECT_STATUS.md](PROJECT_STATUS.md) |
| Aufgabenliste | [TODO.md](TODO.md) |

---

**Erstellt:** 2025-12-18
**Für:** Alle AI-Agenten (Cursor, Claude Code, GPT, Gemini, etc.)

**Viel Erfolg! 🎓**
