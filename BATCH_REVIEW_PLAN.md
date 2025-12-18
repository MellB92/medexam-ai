# Batch-Review-Plan: Automatisierte Qualitätssicherung

**Erstellt:** 2025-12-16
**Zweck:** Automatisierte Batch-Verarbeitung der Review-Queue ohne manuellen Aufwand
**Ziel:** Hochrangige Qualität und Evidenzgrad für alle 431 Review-Items

---

## 1. Ausgangslage

### Zu verarbeitende Dateien

| Datei | Items | Status |
|-------|-------|--------|
| `_OUTPUT/review_queue_20251216_033807.json` | 431 | Master-Liste |
| → `needs_review` | 298 | Faktische Probleme identifiziert |
| → `needs_context` | 133 | Kontext aus Goldstandard fehlt |
| `_OUTPUT/needs_context_prepared_20251216_054003.json` | 133 | Kontext bereits vorbereitet |

### Vorhandene Infrastruktur

- `scripts/perplexity_factcheck_sample.py` - Perplexity API (sonar) für Quellenvalidierung
- `core/unified_api_client.py` - OpenAI/Requesty mit High Reasoning Support
- `core/guideline_fetcher.py` - Leitlinien-Zuordnung (60 PDFs lokal)
- `core/medical_validator.py` - Lokale Validierung (Dosierungen, Laborwerte)

---

## 2. Batch-Verarbeitungs-Pipeline

### Phase 1: Vorbereitung (Cursor Agent)

```
┌─────────────────────────────────────────────────────────────────┐
│  INPUT: review_queue + needs_context_prepared                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Merge beider Dateien                                        │
│  2. Leitlinien-Zuordnung via guideline_fetcher.py               │
│  3. Lokale Validierung via medical_validator.py                 │
│  4. Kategorisierung nach Komplexität (low/medium/high)          │
├─────────────────────────────────────────────────────────────────┤
│  OUTPUT: _OUTPUT/batch_input_prepared_YYYYMMDD.json             │
│  - 431 Items mit Kontext, Leitlinien-Links, Validierungsinfos   │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Dual-Model Batch-Verarbeitung

#### 2a. OpenAI GPT o4-mini mit High Reasoning (Korrektur)

```
┌─────────────────────────────────────────────────────────────────┐
│  MODEL: openai/o4-mini:high via Requesty                        │
│  TASK: Korrektur der Antworten basierend auf Issues             │
├─────────────────────────────────────────────────────────────────┤
│  INPUT pro Item:                                                │
│  - Frage + Original-Antwort                                     │
│  - Issues aus Perplexity-Factcheck                              │
│  - Zugeordnete Leitlinie(n)                                     │
│  - optional_fix_snippet als Hilfe                               │
├─────────────────────────────────────────────────────────────────┤
│  OUTPUT:                                                        │
│  - Korrigierte Antwort (evidenzbasiert)                         │
│  - Verwendete Quellen (Leitlinien-Reg.-Nr.)                     │
│  - Konfidenz-Score                                              │
└─────────────────────────────────────────────────────────────────┘
```

#### 2b. Perplexity Sonar Pro (Quellenvalidierung)

```
┌─────────────────────────────────────────────────────────────────┐
│  MODEL: sonar-pro (mit Web-Suche)                               │
│  TASK: Validierung der korrigierten Antworten                   │
├─────────────────────────────────────────────────────────────────┤
│  INPUT pro Item:                                                │
│  - Frage + KORRIGIERTE Antwort (aus Phase 2a)                   │
│  - Fachgebiet                                                   │
├─────────────────────────────────────────────────────────────────┤
│  OUTPUT:                                                        │
│  - verdict: ok | maybe | problem                                │
│  - Aktuelle Quellen (URLs zu AWMF, RKI, ESC etc.)               │
│  - Remaining issues (falls noch vorhanden)                      │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 3: Finalisierung

```
┌─────────────────────────────────────────────────────────────────┐
│  Merge & Quality Gate                                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Nur Items mit verdict=ok → direkt in evidenz_antworten.json │
│  2. verdict=maybe → erneuter Durchlauf oder manuelle Queue      │
│  3. verdict=problem → separate Datei für Spezialfälle           │
├─────────────────────────────────────────────────────────────────┤
│  OUTPUT:                                                        │
│  - evidenz_antworten_updated_YYYYMMDD.json                      │
│  - batch_review_report_YYYYMMDD.md                              │
│  - remaining_issues_YYYYMMDD.json (falls vorhanden)             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Zu erstellende Skripte (Cursor Agent)

### Script 1: `scripts/prepare_batch_review.py`

**Zweck:** Vorbereitung der Batch-Inputs

```python
# Inputs:
#   - review_queue_20251216_033807.json
#   - needs_context_prepared_20251216_054003.json
#   - leitlinien_manifest.json
#
# Outputs:
#   - batch_input_prepared_YYYYMMDD.json
#
# Funktionen:
#   1. Merge review_queue + needs_context
#   2. detect_medical_themes() pro Frage
#   3. Zuordnung zu lokalen Leitlinien-PDFs
#   4. MedicalValidationLayer für Dosierungen/Laborwerte
#   5. Komplexitäts-Score (low/medium/high)
```

### Script 2: `scripts/batch_correct_with_reasoning.py`

**Zweck:** OpenAI-Korrektur mit High Reasoning

```python
# Model: openai/o4-mini via Requesty mit reasoning_effort="high"
#
# Prompt-Template:
SYSTEM_PROMPT = """Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.
Korrigiere die folgende Antwort basierend auf den identifizierten Problemen.

REGELN:
1. Nutze nur evidenzbasierte Informationen (AWMF-Leitlinien, RKI, Fachgesellschaften)
2. Gib die Leitlinien-Registriernummer an, wenn verfügbar
3. Halte dich an aktuelle Empfehlungen (Stand 2024/2025)
4. Format: Strukturierte Antwort mit Quellenangaben

OUTPUT als JSON:
{
  "korrigierte_antwort": "...",
  "verwendete_quellen": [{"titel": "...", "reg_nr": "...", "url": "..."}],
  "aenderungen": ["..."],
  "konfidenz": 0.0-1.0
}
"""

# Features:
#   - Checkpoint/Resume (JSONL)
#   - Batch-Size 50
#   - Rate-Limiting
#   - Cost-Tracking
```

### Script 3: `scripts/batch_validate_with_perplexity.py`

**Zweck:** Quellenvalidierung der korrigierten Antworten

```python
# Model: sonar-pro (oder sonar mit search)
#
# Erweitert perplexity_factcheck_sample.py:
#   - Nimmt korrigierte Antworten als Input
#   - Validiert gegen aktuelle Web-Quellen
#   - Findet fehlende/veraltete Informationen
#
# Output:
#   - verdict: ok | maybe | problem
#   - aktuelle_quellen: [URLs]
#   - remaining_issues: [...]
```

### Script 4: `scripts/finalize_batch_review.py`

**Zweck:** Merge und Quality Gate

```python
# Inputs:
#   - batch_corrected_YYYYMMDD.json (aus Script 2)
#   - batch_validated_YYYYMMDD.json (aus Script 3)
#
# Outputs:
#   - evidenz_antworten_updated_YYYYMMDD.json
#   - batch_review_report_YYYYMMDD.md
#   - remaining_issues_YYYYMMDD.json
#
# Logik:
#   - verdict=ok: Übernehmen in Hauptdatei
#   - verdict=maybe: Optional 2. Durchlauf
#   - verdict=problem: Separate Datei
```

---

## 4. Kosten-Schätzung

| Phase | Model | Items | Est. Tokens/Item | Kosten |
|-------|-------|-------|------------------|--------|
| 2a | o4-mini:high | 431 | ~2000 in + 1500 out | ~$1.50 |
| 2b | sonar-pro | 431 | ~1500 in + 800 out | ~$2.00 |
| **Gesamt** | | | | **~$3.50** |

*(Sehr günstig dank o4-mini und sonar-pro)*

---

## 5. Ausführungsreihenfolge

```bash
# 1. Vorbereitung
PYTHONPATH=. .venv/bin/python3 scripts/prepare_batch_review.py

# 2. OpenAI-Korrektur mit High Reasoning
PYTHONPATH=. .venv/bin/python3 scripts/batch_correct_with_reasoning.py \
  --input _OUTPUT/batch_input_prepared_YYYYMMDD.json \
  --batch-size 50 \
  --resume

# 3. Perplexity-Validierung
PYTHONPATH=. .venv/bin/python3 scripts/batch_validate_with_perplexity.py \
  --input _OUTPUT/batch_corrected_YYYYMMDD.json \
  --model sonar-pro \
  --resume

# 4. Finalisierung
PYTHONPATH=. .venv/bin/python3 scripts/finalize_batch_review.py \
  --corrected _OUTPUT/batch_corrected_YYYYMMDD.json \
  --validated _OUTPUT/batch_validated_YYYYMMDD.json
```

---

## 6. Zusätzliche Items für Batch-Verarbeitung

Neben den 431 Review-Items könnten folgende Dateien ähnliche Verarbeitung benötigen:

| Datei | Status | Aktion |
|-------|--------|--------|
| `evidenz_antworten.json` (restliche ~2500) | Nicht geprüft | Optional: Stichprobe mit Perplexity |
| `fragmente_relevant.json` (~350) | Kontext fehlt | In Phase 1 integrieren |
| `frage_bloecke_dedupe_verifiziert.json` (ohne Antwort) | Keine Antwort | Separat generieren |

---

## 7. Erwartetes Ergebnis

Nach Durchführung:

- **431 korrigierte Antworten** mit:
  - Evidenzbasierter Korrektur (OpenAI High Reasoning)
  - Quellenvalidierung (Perplexity Sonar Pro)
  - Leitlinien-Referenzen (AWMF Reg.-Nr.)
  - Konfidenz-Scores

- **Qualitätssicherung:**
  - ~80-90% direkt als `ready` markiert
  - ~10-20% als `needs_human_review` für Spezialfälle

---

## 8. Nächste Schritte

**Für Cursor Agent:**
1. Script 1 erstellen: `prepare_batch_review.py`
2. Script 2 erstellen: `batch_correct_with_reasoning.py`
3. Script 3 erstellen: `batch_validate_with_perplexity.py`
4. Script 4 erstellen: `finalize_batch_review.py`
5. Tests mit kleiner Stichprobe (10 Items)
6. Vollständiger Durchlauf

**Priorität:** High - blockiert SRS-Export für Prüfungsvorbereitung
