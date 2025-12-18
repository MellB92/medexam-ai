# 🤖 Cursor Agent Prompt - MedExamAI (Neuer Mac)

**Erstellt:** 2025-12-18
**Repo-Pfad:** `/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617`
**Status:** Migration abgeschlossen, bereit für Entwicklung

---

## 📋 Quick Start Checklist

Bevor du startest, lies diese Dateien in dieser Reihenfolge:

1. ✅ [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) - Harte Constraints & Repo-Struktur
2. ✅ [PROJECT_STATUS.md](PROJECT_STATUS.md) - Aktueller Projektstatus
3. ✅ [TODO.md](TODO.md) - Priorisierte Aufgabenliste
4. ✅ Diese Datei - Handlungsanweisungen

---

## 🚨 HARTE REGELN (NIEMALS BRECHEN!)

### 1. READ-ONLY Dateien

```bash
# NIEMALS überschreiben oder direkt editieren:
_OUTPUT/evidenz_antworten.json  # Kanonische Q&A-Datenbank (4.505 Einträge)
```

**Warum?** Dies ist die Source of Truth. Alle Updates erfolgen über dedizierte Scripts mit Timestamp-Outputs.

### 2. Output-Konvention

```bash
# Alle neuen Outputs IMMER mit Timestamp schreiben:
_OUTPUT/neue_datei_$(date +%Y%m%d_%H%M%S).json

# Beispiel:
_OUTPUT/batch_review_report_20251218_153045.json
```

### 3. Secrets & Credentials

```bash
# .env existiert - NIEMALS loggen, committen oder anzeigen
# API Keys für: OpenAI, Anthropic, Perplexity
cat .env  # ❌ NIEMALS in Logs/Commits

# Prüfen ob Keys gesetzt sind (ohne Werte anzuzeigen):
grep -E "^(OPENAI|ANTHROPIC|PERPLEXITY)" .env | wc -l  # Sollte ≥ 2-3 sein
```

### 4. Python Environment

```bash
# Immer im venv arbeiten:
source venv/bin/activate

# Vor jedem Script-Run prüfen:
which python3  # Sollte: /Users/entropie/.../venv/bin/python3
```

---

## 📊 Aktueller Datenstand (Stand: 2025-12-16)

### Kanonische Datenbank

| Datei | Einträge | Status | Aktion |
|-------|----------|--------|--------|
| `_OUTPUT/evidenz_antworten.json` | 4.505 | READ-ONLY ✅ | Niemals editieren |
| `_OUTPUT/evidenz_antworten_updated_20251216_142834.json` | 4.505 | Arbeitsdatei 📝 | Enthält Batch-Updates |

### Review-Queue Status

| Kategorie | Anzahl | Datei |
|-----------|--------|-------|
| Gesamt Review Items | 431 | `_OUTPUT/review_queue_20251216_033807.json` |
| ├─ needs_review | 298 | In Batch verarbeitet |
| └─ needs_context | 133 | Bereits gematcht |
| **needs_context (prepared)** | 133/133 | `_OUTPUT/needs_context_prepared_20251216_054003.json` |

### Batch-Review Pipeline (Run: 20251216_064700)

| Status | Anzahl | Datei |
|--------|--------|-------|
| ✅ OK | 285 | `_OUTPUT/batch_corrected_20251216_064700.json` |
| ⚠️ Maybe | 79 | `_OUTPUT/batch_validated_20251216_064700.json` |
| ❌ Problem | **67** | `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` |

### Coverage-Status

| Metrik | Wert | Datei |
|--------|------|-------|
| Meaningful Missing | 2.527 | `_OUTPUT/meaningful_missing.json` |
| **Coverage** | **2.527/2.527 = 100%** ✅ | Alle meaningful Fragen vorhanden |
| Strict Missing (historisch) | 3.732 | `_OUTPUT/questions_missing_strict.json` (ignorieren!) |

**Wichtig:** `questions_missing_strict.json` (3.732) ist eine **alte, zu strenge** Analyse mit vielen Fragmenten/Duplikaten. **Nicht verwenden!** Die authoritative Liste ist `meaningful_missing.json` mit 100% Coverage.

---

## 🎯 Priorisierte Aufgaben (Nach Wichtigkeit)

### 🔴 HÖCHSTE PRIORITÄT: 67 Problem-Items fixen

**Datei:** `_OUTPUT/batch_review_remaining_issues_20251216_142834.json`
**Anzahl:** 67 Items mit `verdict: "problem"`
**Ziel:** Manuelle oder zweite Batch-Runde zur Korrektur

**Vorgehen:**

```bash
# 1. Problem-Items analysieren
python3 -c "
import json
from pathlib import Path
from collections import Counter

data = json.loads(Path('_OUTPUT/batch_review_remaining_issues_20251216_142834.json').read_text())

print(f'Total problem items: {len(data)}')

# Häufigste Problem-Gründe
reasons = [item.get('validation_summary', {}).get('reasoning', 'Unknown') for item in data]
print('\nTop Problem-Gründe:')
for reason, count in Counter(reasons).most_common(10):
    print(f'  {count:3d}x {reason[:80]}...')
"

# 2. Optional: Zweite Batch-Runde vorbereiten
python3 scripts/prepare_batch_review.py --filter-problems-only

# 3. Neue Outputs mit Timestamp schreiben
# NEU: _OUTPUT/batch_corrected_20251218_HHMMSS.json
# NEU: _OUTPUT/batch_validated_20251218_HHMMSS.json
```

**Wichtig:**
- Neue Outputs immer mit Timestamp
- Niemals `evidenz_antworten.json` überschreiben
- Checkpoint-Files (.jsonl) für Resume-Fähigkeit

### 🟡 Dokumentation aktualisieren

**Dateien zu aktualisieren:**

1. **PROJECT_STATUS.md** - Auf Stand 2025-12-18 bringen
2. **TODO.md** - Aktuelle Aufgaben statt veraltete 2024-Tasks

**Vorgehen:**

```bash
# Basis: AGENT_OVERVIEW.md (bereits aktuell)
# Update PROJECT_STATUS.md mit:
# - Aktueller Datenstand (4.505 Q&A, 67 offene Issues)
# - Batch-Review Pipeline Status
# - Coverage 100% (meaningful)

# Update TODO.md mit:
# - 67 Problem-Items als höchste Prio
# - Meaningful-Questions-Workflow (optional)
# - SRS-Exports aktualisieren
```

### 🟢 Optional: Meaningful Missing Questions

**Nur wenn explizit gewünscht!**

**Authoritative Liste:** `_OUTPUT/meaningful_missing.json` (2.527 Einträge)
**Aktueller Coverage:** 2.527/2.527 = 100% ✅

**Coverage-Check:**

```bash
# Prüfen ob alle meaningful questions bereits vorhanden sind
python3 -c "
import json
from pathlib import Path

mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())

qa_fragen = set(x['frage'] for x in qa)
matched = sum(1 for x in mm if x['question'] in qa_fragen)

print(f'Meaningful Coverage: {matched}/{len(mm)} = {matched/len(mm)*100:.1f}%')
"
# Erwartet: 2527/2527 = 100.0%
```

**Wenn neue Fragen generiert werden sollen:**

```bash
# NUR meaningful verwenden, nicht strict!
python3 scripts/generate_evidenz_answers.py \
  --input _OUTPUT/meaningful_missing.json \
  --output _OUTPUT/evidenz_antworten_regen_$(date +%Y%m%d_%H%M%S).json \
  --batch-size 100
```

---

## 🛠️ Wichtige Commands (Copy & Paste)

### Setup-Checks

```bash
# 1. Ins Repo wechseln
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# 2. venv aktivieren
source venv/bin/activate

# 3. Python-Version prüfen
python3 --version  # Sollte: Python 3.x

# 4. Datenbank prüfen
python3 -c "import json; print(len(json.load(open('_OUTPUT/evidenz_antworten.json'))))"
# Erwartete Ausgabe: 4505

# 5. API Keys prüfen (ohne Werte anzuzeigen)
grep -c "^OPENAI_API_KEY=" .env && grep -c "^ANTHROPIC_API_KEY=" .env
# Sollte jeweils: 1
```

### Meaningful Coverage Check

```bash
# Vollständiger Coverage-Check
python3 -c "
import json
from pathlib import Path

mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())

qa_set = set(x['frage'] for x in qa)
matched = sum(1 for x in mm if x['question'] in qa_set)

print(f'Coverage: {matched}/{len(mm)} = {matched/len(mm)*100:.1f}%')

if matched < len(mm):
    missing = [x for x in mm if x['question'] not in qa_set]
    print(f'\n{len(missing)} fehlende Fragen:')
    for m in missing[:5]:
        print(f'  - {m[\"question\"][:80]}...')
"
```

### needs_context Pakete

```bash
# 133 needs_context Items mit Kontext aus Goldstandard
python3 scripts/prepare_needs_context_packets.py

# Output:
# - _OUTPUT/needs_context_prepared_TIMESTAMP.json (133 Items mit Kontext)
# - _OUTPUT/needs_context_external_validation_TIMESTAMP.md (Liste für externe Prüfung)
```

### Batch-Review Finalisierung (Re-Run)

```bash
# Falls zweite Batch-Runde für die 67 Problem-Items
python3 scripts/finalize_batch_review.py \
  --corrected _OUTPUT/batch_corrected_20251218_HHMMSS.json \
  --validated _OUTPUT/batch_validated_20251218_HHMMSS.json

# Output:
# - _OUTPUT/evidenz_antworten_updated_TIMESTAMP.json (NEU)
# - _OUTPUT/batch_review_report_TIMESTAMP.md
# - _OUTPUT/batch_review_remaining_issues_TIMESTAMP.json
```

### Lern-Exports (Anki + Dashboard)

```bash
# Anki TSV + Study Dashboard + Daily Plan
python3 scripts/export_learning_materials.py --daily-plan

# Output:
# - _OUTPUT/anki_ready_TIMESTAMP.tsv (für Anki Import)
# - _OUTPUT/anki_review_queue_TIMESTAMP.tsv (Review-Items)
# - _OUTPUT/study_dashboard_TIMESTAMP.md (Übersicht)
# - _OUTPUT/daily_plan_TIMESTAMP.json (optional)
```

---

## 📁 Wichtige Dateien & Pfade

### Dokumentation (Start hier)

| Datei | Zweck |
|-------|-------|
| [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md) | 🚀 Agent-Schnelleinstieg (immer zuerst lesen!) |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | 📊 Projektstatus & Milestones |
| [TODO.md](TODO.md) | ✅ Priorisierte Aufgabenliste |
| [CODEX.md](CODEX.md) | 📝 Kurzer Task-Briefing |
| [README.md](README.md) | 📖 Projekt-Übersicht & Quick Start |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | 🔄 Migrations-Historie |

### Goldstandard-Quellen

| Pfad | Inhalt | Größe |
|------|--------|-------|
| `_GOLD_STANDARD/` | 40+ Prüfungsprotokolle (PDF/DOCX/ODT) | ~150 MB |
| `_FACT_CHECK_SOURCES/` | AWMF-Leitlinien, Lehrmaterial | ~500 MB |
| `_DOCS/` | Zusätzliche Dokumentation | ~10 MB |

### Q&A Datenbank (READ-ONLY!)

| Datei | Einträge | Status |
|-------|----------|--------|
| `_OUTPUT/evidenz_antworten.json` | 4.505 | ⛔ READ-ONLY |
| `_OUTPUT/evidenz_antworten_updated_20251216_142834.json` | 4.505 | 📝 Arbeitsdatei |

### Review-Queue

| Datei | Items | Beschreibung |
|-------|-------|--------------|
| `_OUTPUT/review_queue_20251216_033807.json` | 431 | needs_review + needs_context |
| `_OUTPUT/needs_context_prepared_20251216_054003.json` | 133 | Mit Kontext aus Goldstandard |
| `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` | **67** | **Problem-Items (FOKUS!)** |

### Coverage-Referenzen

| Datei | Einträge | Status |
|-------|----------|--------|
| `_OUTPUT/meaningful_missing.json` | 2.527 | ✅ Authoritative Liste (100% Coverage) |
| `_OUTPUT/questions_missing_strict.json` | 3.732 | ❌ Historisch, ignorieren! |

### Scripts (Wichtigste)

| Script | Zweck |
|--------|-------|
| `scripts/prepare_batch_review.py` | Batch-Review vorbereiten |
| `scripts/batch_correct_with_reasoning.py` | Antworten korrigieren (resumable) |
| `scripts/batch_validate_with_perplexity.py` | Web-Validierung (resumable) |
| `scripts/finalize_batch_review.py` | Ergebnisse finalisieren |
| `scripts/prepare_needs_context_packets.py` | needs_context mit Goldstandard-Kontext |
| `scripts/export_learning_materials.py` | Anki + Dashboard Exports |
| `scripts/generate_evidenz_answers.py` | Neue Q&A generieren |

---

## 🎬 Typische Workflows

### Workflow 1: 67 Problem-Items fixen

```bash
# 1. Problem-Items analysieren
python3 -c "
import json
from pathlib import Path

data = json.loads(Path('_OUTPUT/batch_review_remaining_issues_20251216_142834.json').read_text())
print(f'Problem Items: {len(data)}')

# Erste 3 Items anzeigen
for i, item in enumerate(data[:3], 1):
    print(f'\n{i}. {item[\"frage\"][:80]}...')
    print(f'   Problem: {item.get(\"validation_summary\", {}).get(\"reasoning\", \"N/A\")[:100]}')
"

# 2. Manuelle Korrektur ODER zweite Batch-Runde

# Option A: Manuell in neuem File
# (Niemals evidenz_antworten.json direkt editieren!)

# Option B: Zweite Batch-Runde
python3 scripts/batch_correct_with_reasoning.py --resume
python3 scripts/batch_validate_with_perplexity.py --resume
python3 scripts/finalize_batch_review.py

# 3. Neue Outputs validieren
ls -lh _OUTPUT/*$(date +%Y%m%d)*.json
```

### Workflow 2: Lern-Materialien exportieren

```bash
# 1. Aktuellen Stand prüfen
python3 -c "
import json
from pathlib import Path

qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())
ready = [x for x in qa if x.get('antwort', '').strip()]
review = [x for x in qa if x.get('needs_review') or x.get('needs_context')]

print(f'Ready für SRS: {len(ready)}')
print(f'In Review: {len(review)}')
"

# 2. Exports generieren
python3 scripts/export_learning_materials.py --daily-plan

# 3. Outputs prüfen
ls -lh _OUTPUT/anki_ready_*.tsv
ls -lh _OUTPUT/study_dashboard_*.md
```

### Workflow 3: Coverage validieren

```bash
# Meaningful Coverage Check
python3 -c "
import json
from pathlib import Path

mm = json.loads(Path('_OUTPUT/meaningful_missing.json').read_text())
qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())

qa_set = set(x['frage'] for x in qa)
matched = sum(1 for x in mm if x['question'] in qa_set)

print(f'Meaningful Coverage: {matched}/{len(mm)} ({matched/len(mm)*100:.1f}%)')

if matched == len(mm):
    print('✅ 100% Coverage erreicht!')
else:
    print(f'⚠️ {len(mm) - matched} Fragen fehlen noch')
"
```

---

## 🔍 Debugging & Troubleshooting

### Problem: API Keys nicht gefunden

```bash
# Prüfen ob .env existiert
ls -la .env

# Prüfen ob Keys gesetzt sind (ohne Werte anzuzeigen)
grep -E "^(OPENAI|ANTHROPIC|PERPLEXITY)_API_KEY=" .env | wc -l
# Sollte: 3

# Wenn nicht gesetzt:
# 1. .env.example als Template verwenden
cp .env.example .env
# 2. Keys manuell eintragen (NIEMALS committen!)
```

### Problem: venv nicht gefunden

```bash
# venv neu erstellen
python3 -m venv venv

# Aktivieren
source venv/bin/activate

# Packages installieren
pip install -r requirements.txt
```

### Problem: JSON Parse Error

```bash
# JSON-Datei validieren
python3 -c "
import json
from pathlib import Path

try:
    data = json.loads(Path('DATEI.json').read_text())
    print(f'✅ Valid JSON ({len(data)} items)')
except json.JSONDecodeError as e:
    print(f'❌ Invalid JSON: {e}')
"
```

### Problem: Script hängt

```bash
# Checkpoint-File prüfen (für resumable Scripts)
ls -lh _OUTPUT/*checkpoint.jsonl

# Script mit --resume neu starten
python3 scripts/SCRIPT_NAME.py --resume
```

---

## 📊 Metriken & KPIs

### Datenbank-Metriken

```bash
python3 -c "
import json
from pathlib import Path

qa = json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text())

total = len(qa)
with_answer = len([x for x in qa if x.get('antwort', '').strip()])
empty = total - with_answer
needs_review = len([x for x in qa if x.get('needs_review')])
needs_context = len([x for x in qa if x.get('needs_context')])

print(f'Total Q&A: {total}')
print(f'  Mit Antwort: {with_answer} ({with_answer/total*100:.1f}%)')
print(f'  Leer: {empty} ({empty/total*100:.1f}%)')
print(f'  needs_review: {needs_review}')
print(f'  needs_context: {needs_context}')
"
```

### Quality-Metriken

```bash
python3 -c "
import json
from pathlib import Path

# Batch-Review Status
report_path = Path('_OUTPUT/batch_review_report_20251216_142834.md')
if report_path.exists():
    print(report_path.read_text())
else:
    print('Kein Batch-Review-Report gefunden')
"
```

---

## 🎯 Nächste Schritte (Empfohlen)

### Diese Woche (2025-12-18 bis 2025-12-24)

1. **🔴 HÖCHSTE PRIO:** 67 Problem-Items aus `batch_review_remaining_issues` analysieren und fixen
   - Häufigste Problem-Gründe identifizieren
   - Systematische Korrektur-Strategie entwickeln
   - Zweite Batch-Runde durchführen ODER manuelle Korrektur

2. **🟡 DOKU:** PROJECT_STATUS.md und TODO.md aktualisieren
   - Aktueller Stand (4.505 Q&A, 67 offene Issues)
   - Batch-Review Pipeline Status
   - Coverage 100% dokumentieren

3. **🟢 OPTIONAL:** Lern-Exports aktualisieren
   - Neue Anki-TSVs generieren
   - Study Dashboard aktualisieren
   - Daily Plan erstellen

### Nächste Woche (2025-12-25 bis 2025-12-31)

1. **Empty Answers Workflow** (falls noch leer)
   - Leere Antworten identifizieren
   - Batch-Generierung durchführen
   - Qualitäts-Validierung

2. **SRS Integration** finalisieren
   - Spaced Repetition Algorithmus testen
   - Mentor Agent Integration vorbereiten

3. **Medical Validation Pass** durchführen
   - Stichprobe von 100 Q&A
   - Medizinische Fakten-Checks
   - Dosierungen validieren

---

## ⚠️ Wichtige Erinnerungen

### DON'Ts (Niemals tun!)

- ❌ `_OUTPUT/evidenz_antworten.json` direkt editieren oder überschreiben
- ❌ Secrets/API-Keys loggen, committen oder anzeigen
- ❌ `questions_missing_strict.json` verwenden (veraltet!)
- ❌ Ohne venv arbeiten (`source venv/bin/activate`)
- ❌ Outputs ohne Timestamp schreiben

### DOs (Immer tun!)

- ✅ AGENT_OVERVIEW.md zuerst lesen
- ✅ venv aktivieren vor jedem Script
- ✅ Neue Outputs mit Timestamp schreiben
- ✅ Checkpoint-Files (.jsonl) für Resume nutzen
- ✅ `meaningful_missing.json` für Coverage verwenden

---

## 📚 Weitere Ressourcen

| Ressource | Pfad/Link |
|-----------|-----------|
| Vollständiger Handover | [COMPLETE_HANDOVER.md](COMPLETE_HANDOVER.md) |
| CODEX Handover (2025-12-01) | [CODEX_HANDOVER_2025-12-01.md](CODEX_HANDOVER_2025-12-01.md) |
| Entwickler-Guide | [DEVELOPMENT.md](DEVELOPMENT.md) |
| Migration History | [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) |
| Scripts Übersicht | [scripts/](scripts/) |

---

## ✅ Pre-Flight Checklist (Vor dem Start)

```bash
# 1. Repo-Pfad
pwd
# Sollte: /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# 2. venv aktiv?
which python3
# Sollte: .../venv/bin/python3

# 3. Datenbank vorhanden?
ls -lh _OUTPUT/evidenz_antworten.json
# Sollte: ~11M

# 4. API Keys gesetzt?
grep -c "^OPENAI_API_KEY=" .env && grep -c "^ANTHROPIC_API_KEY=" .env
# Sollte jeweils: 1

# 5. Wichtige Dateien gelesen?
# [ ] AGENT_OVERVIEW.md
# [ ] PROJECT_STATUS.md
# [ ] TODO.md
# [ ] Diese Datei

# Wenn alle ✅: Ready to go! 🚀
```

---

**Ende des Cursor Agent Prompts**

Bei Fragen oder Problemen:
- Konsultiere [AGENT_OVERVIEW.md](AGENT_OVERVIEW.md)
- Prüfe [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Schaue in [TODO.md](TODO.md)

**Viel Erfolg! 🎓**
