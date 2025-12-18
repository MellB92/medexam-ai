# Nächste Aufgabe #002 für GPT-5.2

**Erstellt:** 2025-12-18 14:45:00
**Von:** Coordinator
**Für:** GPT-5.2 (Lead Agent)
**Priorität:** 🔴 HOCH
**Abhängigkeit:** Task #001 abgeschlossen ✅

---

## Aufgabe: Vorbereitung Phase 1 - Items splitten & Batch vorbereiten

### Ziel
Bereite die 67 Problem-Items für die Batch-Runde 2 vor, indem du sie nach Komplexität in zwei Gruppen aufteilst.

---

## Input

### Dateien:
- `_OUTPUT/batch_review_remaining_issues_20251216_142834.json` (67 Items)

### Kontext:
- Du hast bereits analysiert: 60 Items (niedrig/mittel), 7 Items (hoch)
- Schweregrad basiert auf Anzahl Issues pro Item
- Alle Items haben bereits korrigierte Antworten

---

## Output

### Zu erstellende Dateien:

1. **`output/batch_round2_input_20251218.json`**
   - 60 Items mit mittlerer/niedriger Komplexität (≤5 Issues)
   - Format: JSON mit Items-Array
   - Metadata: run_id, generated_at, source
   - Größe: ca. 400-500 KB

2. **`output/manual_review_items_20251218.json`**
   - 7 Items mit hoher Komplexität (6+ Issues)
   - Format: JSON mit Items-Array
   - Metadata: generated_at, count
   - Größe: ca. 50-70 KB

3. **`logs/preparation_phase1.log`**
   - Chronologisches Log aller Schritte
   - Errors/Warnings falls vorhanden

---

## Schritte (Detailliert)

### Schritt 1: Backup erstellen
```bash
cp _OUTPUT/batch_review_remaining_issues_20251216_142834.json \
   _OUTPUT/batch_review_remaining_issues_20251216_142834_backup.json
```
**Erwartetes Ergebnis:** Backup-Datei existiert

### Schritt 2: Items nach Komplexität splitten
```python
import json
from pathlib import Path
from datetime import datetime

# Lade Problem-Items
data = json.loads(Path('_OUTPUT/batch_review_remaining_issues_20251216_142834.json').read_text())
items = data['items']

# Trenne nach Schweregrad (5 Issues als Grenze)
niedrig_mittel = [item for item in items if len(item.get('issues', [])) <= 5]
hoch = [item for item in items if len(item.get('issues', [])) > 5]

# Validierung
assert len(niedrig_mittel) == 60, f"Erwartet 60 Items, gefunden {len(niedrig_mittel)}"
assert len(hoch) == 7, f"Erwartet 7 Items, gefunden {len(hoch)}"

print(f"✓ Split erfolgreich: {len(niedrig_mittel)} Batch, {len(hoch)} Manual")
```

### Schritt 3: Batch-Input generieren
```python
# Erstelle Batch-Input für Runde 2
batch_input = {
    'generated_at': datetime.now().isoformat(),
    'run_id': f"{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    'source': 'batch_review_remaining_issues_20251216_142834.json',
    'items': niedrig_mittel,
    'count': len(niedrig_mittel),
    'complexity': 'niedrig_mittel',
    'focus': [
        'leitlinien_updates_2024_2025',
        'stiko_empfehlungen',
        'fehlende_informationen'
    ]
}

# Speichern
output_path = Path('_AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json')
output_path.write_text(json.dumps(batch_input, indent=2, ensure_ascii=False))

print(f"✓ Batch-Input erstellt: {output_path}")
```

### Schritt 4: Manual Review Input generieren
```python
# Erstelle Manual Review Input
manual_review = {
    'generated_at': datetime.now().isoformat(),
    'items': hoch,
    'count': len(hoch),
    'complexity': 'hoch',
    'note': 'Hochkomplexe Items benötigen manuelle medizinische Review',
    'estimated_time': '3-4 Stunden'
}

# Speichern
manual_path = Path('_AGENT_WORK/GPT52_20251218_142539/output/manual_review_items_20251218.json')
manual_path.write_text(json.dumps(manual_review, indent=2, ensure_ascii=False))

print(f"✓ Manual Review Input erstellt: {manual_path}")
```

### Schritt 5: Sync Point setzen
```bash
# Erstelle Flag-Datei für Composer1
touch _OUTPUT/.ready_for_batch_round2

# Log Entry
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Sync Point erreicht: ready_for_batch_round2" >> \
  _AGENT_WORK/GPT52_20251218_142539/progress.log
```

### Schritt 6: Update COORDINATION.json
```python
import json
from pathlib import Path
from datetime import datetime

coord_file = Path('_AGENT_WORK/GPT52_20251218_142539/COORDINATION.json')
data = json.loads(coord_file.read_text())

data['sync_points_reached'].append({
    'name': 'ready_for_batch_round2',
    'timestamp': datetime.now().isoformat(),
    'status': 'reached'
})

data['status'] = 'waiting'
data['current_task'] = 'Warte auf Composer1 Signal (batch_round2_started)'
data['output_files'].extend([
    'output/batch_round2_input_20251218.json',
    'output/manual_review_items_20251218.json'
])

coord_file.write_text(json.dumps(data, indent=2))
```

---

## Validierung

### Erfolgs-Kriterien:
- [x] Backup existiert: `*_backup.json`
- [x] 60 Items in Batch-Input
- [x] 7 Items in Manual-Input
- [x] Flag-Datei existiert: `_OUTPUT/.ready_for_batch_round2`
- [x] COORDINATION.json aktualisiert
- [x] progress.log aktualisiert

### Quality Checks:
```bash
# Check 1: Datei-Existenz
ls -lh _AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json
ls -lh _AGENT_WORK/GPT52_20251218_142539/output/manual_review_items_20251218.json

# Check 2: Item-Counts
python3 -c "import json; d=json.load(open('_AGENT_WORK/GPT52_20251218_142539/output/batch_round2_input_20251218.json')); print(f'Batch Items: {d[\"count\"]}')"
python3 -c "import json; d=json.load(open('_AGENT_WORK/GPT52_20251218_142539/output/manual_review_items_20251218.json')); print(f'Manual Items: {d[\"count\"]}')"

# Check 3: Sync Point
ls -la _OUTPUT/.ready_for_batch_round2
```

---

## Nach Completion

### Erstelle Task Report:
1. Kopiere Template: `TASK_REPORT_001.md` → `TASK_REPORT_002.md`
2. Fülle aus:
   - Task Name: "Vorbereitung Phase 1"
   - Duration: [MESSE ZEIT]
   - Output Files: [LISTE DATEIEN]
   - Metriken: [ANZAHL ITEMS, DATEIGRÖSSEN]
   - Status: ✅ COMPLETED

### Update STATUS.md:
```markdown
### 2025-12-18 15:XX:XX - Vorbereitung abgeschlossen ✅
- ✅ 60 Items für Batch-Runde 2 vorbereitet
- ✅ 7 Items für manuelle Review vorbereitet
- ✅ Sync Point gesetzt: `.ready_for_batch_round2`
- ⏳ Warte auf Composer1 Signal: `.batch_round2_started`
```

---

## Zeitschätzung

| Schritt | Geschätzte Dauer |
|---------|------------------|
| Backup | 1 Min |
| Split & Validate | 2 Min |
| Batch-Input generieren | 3 Min |
| Manual-Input generieren | 2 Min |
| Sync Point setzen | 1 Min |
| Dokumentation | 3 Min |
| **TOTAL** | **12 Min** |

---

## Abhängigkeiten

### Wartet auf:
- Keine (Task #001 ist abgeschlossen ✅)

### Blockiert:
- **Composer1 Task #001:** Wartet auf dein `.ready_for_batch_round2` Signal

### Nächster Agent:
→ **Composer1** startet Batch-Runde 2 sobald du Signal gegeben hast

---

## Parallel Tasks (Optional)

Während du auf Composer1 wartest (nach Completion):
1. Bereite manuelle Review-Templates vor
2. Recherchiere Leitlinien für die 7 hochkomplexen Items
3. Dokumentiere Recherche-Quellen

---

## Notizen

- ⚠️ **WICHTIG:** `_OUTPUT/evidenz_antworten.json` NICHT anfassen (READ-ONLY!)
- ✅ Alle neuen Dateien mit Timestamp
- ✅ Outputs in `_AGENT_WORK/GPT52_*/output/`
- ✅ Logs in `_AGENT_WORK/GPT52_*/logs/`

---

## Support & Fragen

Bei Problemen:
1. Check logs: `_AGENT_WORK/GPT52_*/logs/preparation_phase1.log`
2. Validate mit Quality Checks oben
3. Dokumentiere in `TASK_REPORT_002.md`

---

**Task Assignment:** ✅ CONFIRMED
**Erstellt:** 2025-12-18 14:45:00
**Start ASAP:** JA
**Estimated Completion:** 2025-12-18 15:00:00

---

**Viel Erfolg! 🚀**
