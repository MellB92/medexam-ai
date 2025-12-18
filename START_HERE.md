# 🚀 START HERE - MedExamAI Quick Guide

**Neu hier? Lies diese Datei zuerst!**

---

## 📍 Du bist hier

```
/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
```

**Projekt:** MedExamAI - AI-gestützte Prüfungsvorbereitung für Mediziner
**Status:** Migration abgeschlossen, bereit für Entwicklung
**Datum:** 2025-12-18

---

## ⚡ Quick Start (2 Minuten)

### Option 1: Cursor Agent (empfohlen)

```bash
# 1. Ins Repo wechseln
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# 2. venv aktivieren
source venv/bin/activate

# 3. Cursor öffnen und diesen Prompt kopieren:
cat CURSOR_COMPOSER_PROMPT.md
# → In Cursor Composer einfügen

# 4. Ready! 🚀
```

### Option 2: Claude Code / GPT / Andere AI

```bash
# 1. Lies zuerst:
open AGENT_OVERVIEW.md

# 2. Dann für Details:
open CURSOR_AGENT_PROMPT_20251218.md

# 3. Ready! 🚀
```

---

## 📚 Wichtigste Dateien (in dieser Reihenfolge lesen)

### 🟢 Für Anfänger (Start hier!)

| Nr | Datei | Dauer | Zweck |
|----|-------|-------|-------|
| 1️⃣ | **Diese Datei** | 2 Min | Orientierung |
| 2️⃣ | [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | 5 Min | Schnelleinstieg & Constraints |
| 3️⃣ | [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md) | 3 Min | Quick Start Commands |

**Total:** ~10 Minuten → Du bist startklar!

### 🟡 Für Fortgeschrittene

| Nr | Datei | Dauer | Zweck |
|----|-------|-------|-------|
| 4️⃣ | [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md) | 15 Min | Vollständige Workflows |
| 5️⃣ | [PROJECT_STATUS.md](PROJECT_STATUS.md) | 5 Min | Projektstatus & Metriken |
| 6️⃣ | [TODO.md](TODO.md) | 3 Min | Priorisierte Aufgaben |

**Total:** ~23 Minuten → Vollständig informiert!

### 🔴 Für Experten / Projekt-Übergabe

| Nr | Datei | Dauer | Zweck |
|----|-------|-------|-------|
| 7️⃣ | [COMPLETE_HANDOVER.md](COMPLETE_HANDOVER.md) | 10 Min | Vollständige Übergabe |
| 8️⃣ | [CODEX_HANDOVER_2025-12-01.md](CODEX_HANDOVER_2025-12-01.md) | 15 Min | Historischer Kontext |
| 9️⃣ | [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | 10 Min | Migrations-Historie |

**Total:** ~35 Minuten → Kompletter Kontext!

---

## 🚨 HARTE REGELN (Niemals brechen!)

### ⛔ READ-ONLY Datei

```bash
_OUTPUT/evidenz_antworten.json  # ← NIEMALS überschreiben!
```

**Warum?** Dies ist die kanonische Q&A-Datenbank mit 4.505 Einträgen. Alle Updates erfolgen über dedizierte Scripts.

### ✅ Immer beachten

1. **Timestamps:** Neue Outputs mit `$(date +%Y%m%d_%H%M%S)`
2. **Secrets:** `.env` existiert - NIEMALS loggen/committen
3. **venv:** Immer aktivieren: `source venv/bin/activate`
4. **meaningful:** Verwende `meaningful_missing.json`, NICHT `questions_missing_strict.json`

---

## 🎯 Was ist die höchste Priorität?

**67 Problem-Items fixen!**

```bash
# Datei mit den Problem-Items:
_OUTPUT/batch_review_remaining_issues_20251216_142834.json

# Quick-Check (wie viele?):
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('_OUTPUT/batch_review_remaining_issues_20251216_142834.json').read_text())
print(f'Problem Items: {len(data)}')
"
# Erwartet: 67
```

**Siehe:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md) → "Workflow 1: 67 Problem-Items fixen"

---

## 📊 Aktueller Stand (Zahlen & Fakten)

| Metrik | Wert | Status |
|--------|------|--------|
| **Q&A Total** | 4.505 | ✅ Kanonisch |
| **Mit Antwort** | ~2.725 | ✅ |
| **Review-Queue** | 431 | ⚠️ In Bearbeitung |
| ├─ needs_review | 298 | ⚠️ |
| └─ needs_context | 133 | ✅ Alle gematcht |
| **Batch-Review** | | |
| ├─ OK | 285 | ✅ |
| ├─ Maybe | 79 | ⚠️ |
| └─ **Problem** | **67** | ❌ **FOKUS!** |
| **Coverage** | 2.527/2.527 | ✅ **100%** |

---

## 🛠️ Setup-Check (Pre-Flight)

```bash
# Kopiere diese Commands und führe sie aus:

# 1. Richtige Location?
pwd
# Sollte: /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# 2. venv aktiviert?
which python3
# Sollte: .../venv/bin/python3

# 3. Datenbank vorhanden?
ls -lh _OUTPUT/evidenz_antworten.json
# Sollte: ~11M Dec 12

# 4. API Keys gesetzt?
grep -c "^OPENAI_API_KEY=" .env
# Sollte: 1

# 5. Funktioniert Python?
python3 -c "import json; print(len(json.load(open('_OUTPUT/evidenz_antworten.json'))))"
# Sollte: 4505
```

**Wenn alle ✅: Du bist ready! 🚀**

---

## 🎬 Erste Schritte (Copy & Paste)

### Setup

```bash
# Terminal öffnen und:
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
source venv/bin/activate
```

### Quick Data Check

```bash
# Wie viele Q&A?
python3 -c "
import json
from pathlib import Path
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())
total = len(qa)
with_answer = len([x for x in qa if x.get('antwort', '').strip()])
print(f'Total: {total}, Mit Antwort: {with_answer} ({with_answer/total*100:.1f}%)')
"
```

### Coverage Check

```bash
# Meaningful Coverage (sollte 100% sein)
python3 -c "
import json
from pathlib import Path
mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())
qa_set = set(x['frage'] for x in qa)
matched = sum(1 for x in mm if x['question'] in qa_set)
print(f'Coverage: {matched}/{len(mm)} = {matched/len(mm)*100:.1f}%')
"
```

---

## 📖 Alle verfügbaren Prompts

**Vollständige Übersicht:** [AGENT_PROMPTS_INDEX.md](AGENT_PROMPTS_INDEX.md)

| Prompt | Zweck | Umfang |
|--------|-------|--------|
| [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md) | Quick Start | 139 Zeilen |
| [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md) | Vollständig | 637 Zeilen |
| [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | Schnelleinstieg | 137 Zeilen |
| [AGENT_PROMPTS_INDEX.md](AGENT_PROMPTS_INDEX.md) | Übersicht | 263 Zeilen |

---

## 🆘 Hilfe & Support

### Probleme?

1. **Lies:** [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md) → "Debugging & Troubleshooting"
2. **Prüfe:** [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) → "Harte Constraints"
3. **Schaue:** [PROJECT_STATUS.md](PROJECT_STATUS.md) → Aktueller Stand

### Weitere Ressourcen

| Ressource | Pfad |
|-----------|------|
| Entwickler-Guide | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Migration History | [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) |
| JIRA Integration | [JIRA_INTEGRATION.md](JIRA_INTEGRATION.md) |
| Scripts | [scripts/](scripts/) |

---

## ✅ Zusammenfassung

**Du willst:**

- ⚡ **Schnell starten?** → Lies [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md) (3 Min)
- 🎯 **Arbeiten?** → Lies [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) (5 Min) + aktiviere venv
- 📚 **Alles verstehen?** → Lies alle Dateien in der Reihenfolge oben (~25 Min)
- 🤖 **Cursor verwenden?** → Öffne [CURSOR_AGENT_PROMPT_20251218.md](CURSOR_AGENT_PROMPT_20251218.md)

**Nächster Schritt:**
→ Öffne [CURSOR_COMPOSER_PROMPT.md](CURSOR_COMPOSER_PROMPT.md) und kopiere den Inhalt in Cursor Composer!

---

**Erstellt:** 2025-12-18
**Viel Erfolg! 🎓**
