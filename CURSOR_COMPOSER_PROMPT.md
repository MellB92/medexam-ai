# Cursor Composer Prompt - MedExamAI Quick Start

**Kopiere diesen Prompt 1:1 in Cursor Composer**

---

Du arbeitest im MedExamAI Repository. Beachte strikt:

## 🚨 Harte Regeln

1. **READ-ONLY:** `_OUTPUT/evidenz_antworten.json` niemals überschreiben (4.505 Q&A, kanonisch)
2. **Timestamps:** Neue Outputs immer mit Timestamp: `_OUTPUT/file_$(date +%Y%m%d_%H%M%S).json`
3. **Secrets:** Keine API-Keys loggen/committen (`.env` existiert)
4. **venv:** Immer aktivieren: `source venv/bin/activate`

## 📊 Aktueller Stand (2025-12-16)

**Datenbank:**
- 4.505 Q&A in `_OUTPUT/evidenz_antworten.json` (READ-ONLY)
- 4.505 Q&A in `_OUTPUT/evidenz_antworten_updated_20251216_142834.json` (Arbeitsdatei)

**Review-Queue:**
- 431 Items total (`_OUTPUT/review_queue_20251216_033807.json`)
  - 298 needs_review
  - 133 needs_context (alle gematcht in `_OUTPUT/needs_context_prepared_20251216_054003.json`)

**Batch-Review Pipeline (Run: 20251216_064700):**
- ✅ 285 OK
- ⚠️ 79 Maybe
- ❌ **67 Problem** → `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` (FOKUS!)

**Coverage:**
- Meaningful: **2.527/2.527 = 100%** ✅ (`_OUTPUT/meaningful_missing.json`)
- Strict (historisch): 3.732 (ignorieren!)

## 🎯 Priorisierte Aufgaben

### 1. HÖCHSTE PRIORITÄT: 67 Problem-Items fixen

```bash
# Analysieren
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('_OUTPUT/batch_review_remaining_issues_20251216_142834.json').read_text())
print(f'Problem Items: {len(data)}')
for i, item in enumerate(data[:3], 1):
    print(f'{i}. {item[\"frage\"][:80]}')
"

# Option: Zweite Batch-Runde
python3 scripts/batch_correct_with_reasoning.py --resume
python3 scripts/batch_validate_with_perplexity.py --resume
python3 scripts/finalize_batch_review.py
```

### 2. Dokumentation aktualisieren

- `PROJECT_STATUS.md` auf Stand 2025-12-18 bringen
- `TODO.md` mit aktuellen Tasks aktualisieren

### 3. Optional: Lern-Exports

```bash
python3 scripts/export_learning_materials.py --daily-plan
```

## 📁 Wichtige Dateien

**Dokumentation (lies zuerst):**
- `AGENT_OVERVIEW.md` - Schnelleinstieg & Constraints
- `PROJECT_STATUS.md` - Projektstatus
- `TODO.md` - Aufgabenliste
- `CURSOR_AGENT_PROMPT_20251218.md` - Vollständiger Agent-Prompt

**Daten (READ-ONLY!):**
- `_OUTPUT/evidenz_antworten.json` - Kanonische Q&A (⛔ niemals editieren!)
- `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` - 67 Problem-Items

**Scripts:**
- `scripts/finalize_batch_review.py` - Batch-Review finalisieren
- `scripts/export_learning_materials.py` - Anki + Dashboard
- `scripts/prepare_needs_context_packets.py` - needs_context mit Kontext

## 🛠️ Häufige Commands

```bash
# Setup
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
source venv/bin/activate

# Datenbank-Check
python3 -c "import json; print(len(json.load(open('_OUTPUT/evidenz_antworten.json'))))"
# Erwartet: 4505

# Coverage-Check
python3 -c "
import json
from pathlib import Path
mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())
qa_set = set(x['frage'] for x in qa)
matched = sum(1 for x in mm if x['question'] in qa_set)
print(f'Coverage: {matched}/{len(mm)} = {matched/len(mm)*100:.1f}%')
"
# Erwartet: 2527/2527 = 100.0%

# Lern-Exports
python3 scripts/export_learning_materials.py --daily-plan
```

## ⚠️ DON'Ts

- ❌ `_OUTPUT/evidenz_antworten.json` direkt editieren
- ❌ Secrets/API-Keys loggen oder committen
- ❌ `questions_missing_strict.json` verwenden (veraltet!)
- ❌ Outputs ohne Timestamp schreiben

## ✅ DOs

- ✅ `AGENT_OVERVIEW.md` zuerst lesen
- ✅ venv aktivieren
- ✅ Neue Outputs mit Timestamp
- ✅ `meaningful_missing.json` für Coverage

## 📋 Pre-Flight Check

```bash
pwd  # Sollte: .../Medexamenai_migration_full_20251217_204617
which python3  # Sollte: .../venv/bin/python3
ls -lh _OUTPUT/evidenz_antworten.json  # Sollte: ~11M
grep -c "^OPENAI_API_KEY=" .env  # Sollte: 1
```

**Wenn alle ✅: Ready! 🚀**

---

**Für Details:** Siehe `CURSOR_AGENT_PROMPT_20251218.md` (637 Zeilen, vollständig)
