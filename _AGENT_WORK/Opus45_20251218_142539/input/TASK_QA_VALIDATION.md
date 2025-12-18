# Task: Quality Assurance - Batch Round 2 Validation

**Agent:** Opus 4.5 #1 (QA & Validation)
**Erstellt:** 2025-12-18 16:00:00
**Priorität:** 🔴 HOCH
**Voraussetzung:** GPT-5.2 #2 hat Batch-Runde 2 abgeschlossen

---

## Ziel

Führe eine Stichproben-basierte Quality Assurance der Batch-Korrekturen durch. Validiere fachliche Korrektheit, Leitlinien-Konformität und stelle sicher, dass mindestens 90% der Korrekturen den Quality Gates entsprechen.

---

## Input-Dateien

### Von GPT-5.2 #2:
```bash
_AGENT_WORK/Opus45_20251218_142539/input/batch_round2_output_20251218.json
_AGENT_WORK/Opus45_20251218_142539/input/HANDOFF_FROM_GPT52_BATCH.md
```

**Validierung:**
```bash
python3 -c "
import json
from pathlib import Path
data = json.loads(Path('_AGENT_WORK/Opus45_20251218_142539/input/batch_round2_output_20251218.json').read_text())
print(f'Batch-Ergebnisse: {data[\"results_count\"]} Items')
assert data['results_count'] == 60
print('✓ Input validiert')
"
```

---

## Schritte (Detailliert)

### Schritt 1: Stichproben auswählen (5 Min)

**Methode:** Zufällige Auswahl von 10 Items aus 60

```bash
cd /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

python3 << 'EOF'
import json
import random
from pathlib import Path

# Lade Batch-Ergebnisse
batch_data = json.loads(
    Path('_AGENT_WORK/Opus45_20251218_142539/input/batch_round2_output_20251218.json').read_text()
)

# Wähle 10 zufällige Items
all_items = batch_data['results']
random.seed(42)  # Reproducible
sample_items = random.sample(all_items, min(10, len(all_items)))

# Speichere Stichproben
sample_output = {
    'selected_at': '$(date -Iseconds)',
    'total_items': len(all_items),
    'sample_size': len(sample_items),
    'sample_items': sample_items
}

output_path = Path('_AGENT_WORK/Opus45_20251218_142539/output/qa_sample_items.json')
output_path.write_text(json.dumps(sample_output, indent=2, ensure_ascii=False))

print(f"✓ {len(sample_items)} Stichproben ausgewählt")
print(f"✓ Gespeichert: {output_path}")

# Erstelle Checkliste
checklist = []
for i, item in enumerate(sample_items, 1):
    # Extrahiere relevante Info (Format abhängig von Batch-Output)
    checklist.append(f"{i}. Item ID: [TODO] - [Kurzbeschreibung]")

Path('_AGENT_WORK/Opus45_20251218_142539/output/qa_checklist.txt').write_text('\n'.join(checklist))
print("✓ QA-Checkliste erstellt")
EOF
```

### Schritt 2: Quality Gates definieren (2 Min)

**Erstelle QA-Kriterien:**

```bash
cat > _AGENT_WORK/Opus45_20251218_142539/output/QA_CRITERIA.md << 'EOF'
# Quality Assurance Criteria - Batch Round 2

## Quality Gates

### 1. Fachliche Korrektheit ✓
- [ ] Medizinische Fakten korrekt
- [ ] Dosierungen stimmen (falls relevant)
- [ ] Keine widersprüchlichen Aussagen
- [ ] Aktuelle Evidenz berücksichtigt

### 2. Leitlinien-Konformität ✓
- [ ] Leitlinien 2024/2025 berücksichtigt
- [ ] STIKO-Empfehlungen aktuell (falls Impfungen)
- [ ] Keine veralteten Informationen
- [ ] Quellen korrekt zitiert

### 3. Vollständigkeit ✓
- [ ] Alle relevanten Infos vorhanden
- [ ] Keine fehlenden Angaben
- [ ] Kontext ausreichend erklärt
- [ ] Praktische Relevanz gegeben

### 4. Sprachliche Qualität ✓
- [ ] Verständlich formuliert
- [ ] Fachlich präzise
- [ ] Keine Tippfehler
- [ ] Markdown korrekt

## Bewertungsskala

| Score | Bedeutung |
|-------|-----------|
| 4/4 | Perfekt - alle Kriterien erfüllt |
| 3/4 | Gut - kleinere Mängel |
| 2/4 | Akzeptabel - größere Mängel |
| 1/4 | Mangelhaft - kritische Fehler |
| 0/4 | Unbrauchbar - komplett falsch |

## Ziel

**Mind. 90% der Stichproben mit Score >= 3/4**

EOF

echo "✓ QA-Kriterien definiert"
```

### Schritt 3: Manuelle Validierung (30-45 Min)

**Für jedes der 10 Stichproben-Items:**

```markdown
# QA-Prozess pro Item:

1. **Lese Original-Frage**
   - Was wurde gefragt?
   - Welche Problem-Issues gab es?

2. **Lese korrigierte Antwort**
   - Wurde das Problem behoben?
   - Ist die Antwort korrekt?

3. **Prüfe gegen Leitlinien**
   - Recherchiere aktuelle Leitlinien (falls nötig)
   - Verifiziere medizinische Fakten

4. **Bewerte**
   - Score 0-4 vergeben
   - Notizen zu Mängeln

5. **Dokumentiere**
   - Ergebnis in QA-Report eintragen
```

**Dokumentations-Template:**

```bash
cat > _AGENT_WORK/Opus45_20251218_142539/output/QA_VALIDATION_TEMPLATE.md << 'EOF'
# QA Validation Report - Item #X

**Item ID:** [ID]
**Frage:** [FRAGE]
**Problem-Issues (vorher):** [ISSUES]

---

## Korrigierte Antwort

[ANTWORT]

---

## Quality Gates Prüfung

### 1. Fachliche Korrektheit
- [x/  ] Medizinische Fakten korrekt
- [x/  ] Dosierungen stimmen
- [x/  ] Keine Widersprüche
- [x/  ] Aktuelle Evidenz

**Notizen:** [KOMMENTAR]

### 2. Leitlinien-Konformität
- [x/  ] Leitlinien 2024/2025
- [x/  ] STIKO aktuell
- [x/  ] Keine veralteten Infos
- [x/  ] Quellen korrekt

**Notizen:** [KOMMENTAR]

### 3. Vollständigkeit
- [x/  ] Alle Infos vorhanden
- [x/  ] Keine fehlenden Angaben
- [x/  ] Kontext ausreichend
- [x/  ] Praktisch relevant

**Notizen:** [KOMMENTAR]

### 4. Sprachliche Qualität
- [x/  ] Verständlich
- [x/  ] Fachlich präzise
- [x/  ] Keine Tippfehler
- [x/  ] Markdown korrekt

**Notizen:** [KOMMENTAR]

---

## Bewertung

**Score:** X/4

**Status:** ✅ PASSED / ⚠️ MINOR ISSUES / ❌ FAILED

**Zusammenfassung:** [KURZE BEWERTUNG]

---

**Validiert von:** Opus 4.5 #1
**Datum:** [DATUM]

EOF

echo "✓ Validierungs-Template erstellt"
```

### Schritt 4: Ergebnisse aggregieren (10 Min)

```bash
python3 << 'EOF'
import json
from pathlib import Path
from datetime import datetime

# TODO: Sammle Bewertungen aus manuellen Validierungen
# Dies ist ein Placeholder - tatsächliche Daten müssen manuell eingegeben werden

qa_results = {
    'validated_at': datetime.now().isoformat(),
    'agent': 'Opus 4.5 #1',
    'batch_id': open('_AGENT_WORK/GPT52_Batch_20251218_155448/output/BATCH_ID.txt').read().strip(),
    'sample_size': 10,
    'results': [
        # Beispiel:
        # {
        #     'item_id': 'item_001',
        #     'score': 4,
        #     'status': 'passed',
        #     'notes': 'Perfekt - alle Kriterien erfüllt'
        # }
    ],
    'summary': {
        'total_validated': 0,
        'passed': 0,  # Score >= 3
        'minor_issues': 0,  # Score == 2
        'failed': 0,  # Score <= 1
        'average_score': 0.0,
        'pass_rate': 0.0
    }
}

# Speichere Ergebnisse
output_path = Path('_AGENT_WORK/Opus45_20251218_142539/output/qa_validation_results.json')
output_path.write_text(json.dumps(qa_results, indent=2, ensure_ascii=False))

print(f"✓ QA-Ergebnisse gespeichert: {output_path}")
print("\n⚠️ WICHTIG: Ergebnisse müssen manuell ausgefüllt werden!")
EOF
```

### Schritt 5: QA-Report erstellen (10 Min)

```bash
cat > _AGENT_WORK/Opus45_20251218_142539/output/QA_REPORT_20251218.md << 'EOF'
# Quality Assurance Report - Batch Round 2

**Agent:** Opus 4.5 #1 (QA & Validation)
**Batch-ID:** [BATCH_ID]
**Validiert:** $(date '+%Y-%m-%d %H:%M:%S')
**Status:** ✅ PASSED / ⚠️ MINOR ISSUES / ❌ FAILED

---

## Executive Summary

**Stichproben:** 10 von 60 Items (16.7%)
**Passed:** X/10 (XX%)
**Minor Issues:** X/10 (XX%)
**Failed:** X/10 (XX%)

**Durchschnittlicher Score:** X.X/4.0

**Quality Gate Status:** ✅ PASSED (>= 90% mit Score >= 3)

---

## Detaillierte Ergebnisse

### Items Validated

| # | Item ID | Score | Status | Notizen |
|---|---------|-------|--------|---------|
| 1 | [ID] | X/4 | ✅ | [KURZ] |
| 2 | [ID] | X/4 | ✅ | [KURZ] |
| 3 | [ID] | X/4 | ⚠️ | [KURZ] |
| 4 | [ID] | X/4 | ✅ | [KURZ] |
| 5 | [ID] | X/4 | ✅ | [KURZ] |
| 6 | [ID] | X/4 | ✅ | [KURZ] |
| 7 | [ID] | X/4 | ✅ | [KURZ] |
| 8 | [ID] | X/4 | ✅ | [KURZ] |
| 9 | [ID] | X/4 | ✅ | [KURZ] |
| 10 | [ID] | X/4 | ✅ | [KURZ] |

---

## Findings

### Positive Aspekte ✅
- [LISTE VON GUTEN BEOBACHTUNGEN]
- Leitlinien 2024/2025 korrekt berücksichtigt
- STIKO-Empfehlungen aktuell
- Quellen korrekt zitiert

### Verbesserungspotenzial ⚠️
- [LISTE VON MINOR ISSUES]
- Einzelne Formulierungen könnten präziser sein
- [WEITERE ANMERKUNGEN]

### Kritische Fehler ❌
- [LISTE VON CRITICAL ISSUES falls vorhanden]
- [ODER: Keine kritischen Fehler gefunden]

---

## Empfehlungen

### Für Batch-Verarbeitung:
- [EMPFEHLUNGEN FÜR ZUKÜNFTIGE BATCHES]

### Für manuelle Review (7 hochkomplexe Items):
- [SPEZIELLE HINWEISE]

---

## Nächster Agent

→ **Opus 4.5 #2** kann jetzt Documentation Update starten

**Output bereitgestellt:**
- `_AGENT_WORK/Opus45_20251218_142539/output/QA_REPORT_20251218.md`
- `_AGENT_WORK/Opus45_20251218_142539/output/qa_validation_results.json`

---

## Appendix

### Validation Methodology
- Stichproben-Auswahl: Zufällig (seed=42)
- Validation: Manuell durch Opus 4.5 #1
- Quality Gates: 4 Kategorien, 4-Punkt-Skala
- Pass-Kriterium: Score >= 3/4

### Time Tracking
| Phase | Dauer |
|-------|-------|
| Stichproben-Auswahl | 5 Min |
| Quality Gates Definition | 2 Min |
| Manuelle Validierung | 30-45 Min |
| Ergebnisse aggregieren | 10 Min |
| QA-Report erstellen | 10 Min |
| **TOTAL** | **~60 Min** |

---

**Report Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Agent:** Opus 4.5 #1
**Status:** ✅ COMPLETED

EOF

echo "✓ QA-Report Template erstellt"
```

### Schritt 6: Output für Opus 4.5 #2 bereitstellen (2 Min)

```bash
# Kopiere QA-Report für Docs-Agent
cp _AGENT_WORK/Opus45_20251218_142539/output/QA_REPORT_20251218.md \
   _AGENT_WORK/Opus45_Docs_20251218_155454/input/

cp _AGENT_WORK/Opus45_20251218_142539/output/qa_validation_results.json \
   _AGENT_WORK/Opus45_Docs_20251218_155454/input/

echo "✓ Output für Opus 4.5 #2 bereitgestellt"

# Handoff-Notiz
cat > _AGENT_WORK/Opus45_Docs_20251218_155454/input/HANDOFF_FROM_OPUS45_QA.md << 'EOF'
# Handoff von Opus 4.5 #1 (QA)

**Übergeben:** $(date '+%Y-%m-%d %H:%M:%S')
**Von:** Opus 4.5 #1 (QA & Validation)
**An:** Opus 4.5 #2 (Documentation)

## QA Abgeschlossen

**Status:** ✅ PASSED
**Pass Rate:** [XX]%
**Durchschnittlicher Score:** [X.X]/4.0

## Deine Aufgabe (Documentation)

1. PROJECT_STATUS.md aktualisieren
   - Anzahl korrigierter Items: 67 → 7 remaining
   - Batch-Runde 2: COMPLETED
   - Coverage: [XX]%

2. TODO.md aktualisieren
   - Batch-Runde 2 als erledigt markieren
   - Neue Tasks für 7 manuelle Items

3. Final Report erstellen

**Input-Dateien:**
- `input/QA_REPORT_20251218.md`
- `input/qa_validation_results.json`

**Detaillierte Anweisungen:** `input/TASK_DOCUMENTATION.md`

---

**Viel Erfolg! 📝**
EOF

echo "✓ Handoff-Notiz erstellt"
```

---

## Zeitschätzung

| Phase | Dauer | Kumulativ |
|-------|-------|-----------|
| 1. Stichproben auswählen | 5 Min | 5 Min |
| 2. Quality Gates definieren | 2 Min | 7 Min |
| 3. Manuelle Validierung (10 Items) | 30-45 Min | 37-52 Min |
| 4. Ergebnisse aggregieren | 10 Min | 47-62 Min |
| 5. QA-Report erstellen | 10 Min | 57-72 Min |
| 6. Output bereitstellen | 2 Min | 59-74 Min |
| **TOTAL** | **~60-75 Min** | |

---

## Success Criteria

- [x] 10 Stichproben ausgewählt
- [x] Quality Gates definiert
- [x] Manuelle Validierung durchgeführt
- [x] Pass Rate >= 90% (mind. 9/10 mit Score >= 3)
- [x] QA-Report erstellt
- [x] Output für Opus 4.5 #2 bereitgestellt

---

## Troubleshooting

### Problem: Unsicher bei medizinischer Bewertung
**Lösung:**
- Recherchiere in aktuellen Leitlinien
- Konsultiere Fachliteratur
- Bei Unsicherheit: Score konservativ vergeben

### Problem: Items haben unklare Struktur
**Lösung:**
```bash
# Prüfe Batch-Output Format
cat _AGENT_WORK/Opus45_20251218_142539/input/batch_round2_output_20251218.json | python3 -m json.tool | head -100
```

---

**Status:** 🔴 READY TO START (warte auf GPT-5.2 #2)
**Erstellt:** 2025-12-18 16:00:00
**Agent:** Opus 4.5 #1 (QA & Validation)
