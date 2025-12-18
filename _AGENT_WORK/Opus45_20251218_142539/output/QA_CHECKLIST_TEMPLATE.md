# QA Checklist - Batch Round 2 Validation

**Agent:** Opus 4.5
**Erstellt:** 2025-12-18
**Status:** VORBEREITET (Warte auf Signal)

---

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

---

## Quality Gates

### 1. Fachliche Korrektheit
- [ ] Leitlinien-Konformität (2024/2025)
- [ ] STIKO-Empfehlungen aktuell
- [ ] Dosierungen korrekt
- [ ] Keine veralteten Informationen

### 2. Vollständigkeit
- [ ] Alle relevanten Infos vorhanden
- [ ] Keine fehlenden Angaben
- [ ] Kontext ausreichend

### 3. Formatierung
- [ ] JSON-Struktur valide
- [ ] Markdown korrekt
- [ ] Keine Encoding-Fehler

### 4. Dokumentation
- [ ] PROJECT_STATUS.md aktualisiert
- [ ] TODO.md aktualisiert
- [ ] Alle Änderungen dokumentiert

---

## Erfolgs-Kriterien

| Kriterium | Schwelle | Status |
|-----------|----------|--------|
| Stichproben korrekt | ≥90% | ⏳ |
| Quality Gates | ALLE PASSED | ⏳ |
| Dokumentation | Vollständig | ⏳ |

---

## Validierungs-Script (für später)

```python
import json, random
from pathlib import Path

base = Path("/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617")
files = list((base / "_OUTPUT").glob("evidenz_antworten_updated_round2_*.json"))
if not files: exit("ERROR: No Round 2 results")

data = json.loads(files[0].read_text())
samples = random.sample(data.get('items', []), min(10, len(data.get('items', []))))

ok = sum(1 for s in samples if s.get('antwort_korrigiert') and 
         s.get('validation_summary', {}).get('verdict') in ['ok', 'maybe'])

rate = (ok / len(samples)) * 100
print(f"\nQuality Gate: {ok}/{len(samples)} = {rate:.0f}%")
print(f"Status: {'✅ PASSED' if rate >= 90 else '❌ FAILED'}")
```
