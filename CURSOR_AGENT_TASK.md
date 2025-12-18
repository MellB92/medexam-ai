# Cursor Agent Task: Batch-Review-Pipeline implementieren

**Priorität:** HIGH
**Geschätzte Dauer:** 2-3 Stunden
**Budget:** ~$3.50 für API-Calls

---

## Kontext

Du arbeitest am MedExamAI-Projekt - einem Prüfungsvorbereitungssystem für die deutsche Kenntnisprüfung (Approbationsprüfung für ausländische Ärzte).

Es gibt 431 Q&A-Paare, die automatisiert korrigiert und validiert werden müssen:
- 298 Items mit faktischen Problemen (`needs_review`)
- 133 Items mit fehlendem Kontext (`needs_context`)

**Ziel:** Automatisierte Batch-Verarbeitung ohne manuellen Review, aber mit hoher Qualität.

## Harte Constraints (müssen eingehalten werden)

- **NICHT anfassen/überschreiben:** `_OUTPUT/evidenz_antworten.json`
- **Keine Secrets loggen oder committen** (API-Keys nur über `.env`, nie ausgeben).
- **Outputs immer neu mit Timestamp** (keine Überschreibung vorhandener Dateien).
- **Keine inhaltliche Umschreibung in-place** ohne expliziten Output als neue Datei.

---

## Deine Aufgabe

Erstelle 4 Python-Skripte, die eine Batch-Pipeline implementieren:

```
prepare_batch_review.py → batch_correct_with_reasoning.py → batch_validate_with_perplexity.py → finalize_batch_review.py
```

---

## Script 1: `scripts/prepare_batch_review.py`

### Zweck
Merge und Vorbereitung aller Review-Items mit Leitlinien-Zuordnung.

### Inputs
- `_OUTPUT/review_queue_20251216_033807.json` (431 Items)
- `_OUTPUT/needs_context_prepared_20251216_054003.json` (133 Items mit Kontext)
- `_BIBLIOTHEK/leitlinien_manifest.json` (60 lokale Leitlinien-PDFs)

### Zu verwendende Module
```python
from core.guideline_fetcher import detect_medical_themes, map_themes_to_societies
from core.medical_validator import MedicalValidationLayer
```

### Logik
1. Lade `review_queue` und `needs_context_prepared`
2. Merge: Für `needs_context` Items, füge den vorbereiteten Kontext hinzu
3. Pro Item:
   - `detect_medical_themes(frage)` → Themen erkennen
   - Matching mit `leitlinien_manifest.json` → lokale PDF-Pfade
   - `MedicalValidationLayer().validate(antwort)` → Dosierungs-/Laborwert-Check
   - Komplexitäts-Score berechnen (low/medium/high)
4. Output als JSON

### Output
```json
{
  "generated_at": "2025-12-16T...",
  "total_items": 431,
  "items": [
    {
      "id": "review_001",
      "frage": "...",
      "antwort_original": "...",
      "issues": ["..."],
      "optional_fix_snippet": "...",
      "fachgebiet": "Innere Medizin",
      "priority": "high",
      "context_lines": ["..."],  // nur bei needs_context
      "zugeordnete_leitlinien": [
        {"titel": "Herzinsuffizienz", "pfad": "Leitlinien/Kardiologie/nvl-006_Herzinsuffizienz.pdf", "reg_nr": "nvl-006"}
      ],
      "lokale_validierung": {
        "dosierungen_ok": true,
        "laborwerte_ok": true,
        "issues": []
      },
      "komplexitaet": "medium"
    }
  ]
}
```

### CLI
```bash
PYTHONPATH=. .venv/bin/python3 scripts/prepare_batch_review.py \
  --output _OUTPUT/batch_input_prepared.json
```

---

## Script 2: `scripts/batch_correct_with_reasoning.py`

### Zweck
Korrektur der Antworten mit OpenAI o4-mini und High Reasoning Effort.

### API-Konfiguration
```python
# Nutze bestehenden UnifiedAPIClient
from core.unified_api_client import UnifiedAPIClient

client = UnifiedAPIClient()
# Model: openai/o4-mini via Requesty
# reasoning_effort: "high"
```

### Alternativ: Direkter OpenAI-Call via Requesty
```python
import requests

response = requests.post(
    "https://router.requesty.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('REQUESTY_API_KEY')}",
        "Content-Type": "application/json"
    },
    json={
        "model": "openai/o4-mini",
        "messages": [...],
        "reasoning_effort": "high",  # WICHTIG: High Thinking
        "max_tokens": 2000
    }
)
```

### System-Prompt
```
Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung (Approbationsprüfung).

AUFGABE:
Korrigiere die folgende Antwort basierend auf den identifizierten Problemen.

REGELN:
1. Nutze nur evidenzbasierte Informationen
2. Bevorzuge: AWMF-Leitlinien, RKI, STIKO, Fachgesellschaften (ESC, ERS, DGIM, DKG)
3. Gib die Leitlinien-Registriernummer an (z.B. "AWMF 021-003")
4. Halte dich an aktuelle Empfehlungen (Stand 2024/2025)
5. Antworte auf Deutsch, prüfungsrelevant und präzise

FORMAT:
Strukturierte Antwort mit:
- Kurze Definition/Zusammenfassung
- Kernpunkte (nummeriert)
- Quellenangabe am Ende

OUTPUT als JSON:
{
  "korrigierte_antwort": "Strukturierte Antwort hier...",
  "verwendete_quellen": [
    {"titel": "NVL Herzinsuffizienz", "reg_nr": "nvl-006", "url": "https://..."}
  ],
  "aenderungen": ["Dosierung korrigiert: 5mg statt 50mg", "..."],
  "konfidenz": 0.85
}
```

### User-Prompt Template
```
FRAGE:
{frage}

ORIGINAL-ANTWORT:
{antwort_original}

IDENTIFIZIERTE PROBLEME:
{issues}

VORGESCHLAGENE KORREKTUR (als Hilfe):
{optional_fix_snippet}

ZUGEORDNETE LEITLINIEN:
{zugeordnete_leitlinien}

Bitte korrigiere die Antwort.
```

### Features (WICHTIG)
- **Checkpoint/Resume:** JSONL-Datei für Wiederaufnahme nach Abbruch
- **Batch-Size:** 50 Items parallel (oder sequentiell mit Delay)
- **Rate-Limiting:** 0.5s Pause zwischen Requests
- **Cost-Tracking:** Tokens und Kosten loggen
- **Error-Handling:** Bei Fehler → retry 3x, dann skip

### Output
```json
{
  "generated_at": "...",
  "model": "openai/o4-mini",
  "reasoning_effort": "high",
  "total_processed": 431,
  "total_cost_usd": 1.50,
  "items": [
    {
      "id": "review_001",
      "frage": "...",
      "antwort_korrigiert": "...",
      "verwendete_quellen": [...],
      "aenderungen": [...],
      "konfidenz": 0.85,
      "tokens": {"input": 1200, "output": 800}
    }
  ]
}
```

### CLI
```bash
PYTHONPATH=. .venv/bin/python3 scripts/batch_correct_with_reasoning.py \
  --input _OUTPUT/batch_input_prepared.json \
  --output _OUTPUT/batch_corrected.json \
  --batch-size 50 \
  --resume
```

---

## Script 3: `scripts/batch_validate_with_perplexity.py`

### Zweck
Validierung der korrigierten Antworten mit Perplexity (Web-Suche für aktuelle Quellen).

### Basis
Erweitere das bestehende `scripts/perplexity_factcheck_sample.py` - die Infrastruktur ist bereits vorhanden.

### API-Konfiguration
```python
# Perplexity API (bereits in .env konfiguriert)
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
MODEL = "sonar-pro"  # oder "sonar" falls sonar-pro nicht verfügbar
```

### System-Prompt
```
Du bist ein medizinischer Faktenprüfer für die deutsche Kenntnisprüfung.

AUFGABE:
Validiere die folgende korrigierte Antwort auf:
1. Faktische Richtigkeit
2. Aktualität (Leitlinien 2024/2025)
3. Vollständigkeit für Prüfungszwecke

RECHERCHE:
Nutze Web-Suche für aktuelle Quellen. Bevorzuge:
- AWMF Leitlinien-Register
- RKI, STIKO
- Fachgesellschaften (ESC, ERS, DGIM, DKG)
- DocCheck/Flexikon nur als Sekundärquelle

OUTPUT als JSON:
{
  "verdict": "ok|maybe|problem",
  "issues": ["Falls vorhanden..."],
  "aktuelle_quellen": [
    {"titel": "...", "url": "https://...", "relevanz": "..."}
  ],
  "empfehlung": "Kurze Empfehlung falls Änderung nötig"
}

WICHTIG:
- verdict=ok: Antwort ist korrekt und aktuell
- verdict=maybe: Kleine Unklarheiten, aber verwendbar
- verdict=problem: Faktische Fehler, muss überarbeitet werden
```

### Features
- **Checkpoint/Resume:** Wie in perplexity_factcheck_sample.py
- **Rate-Limiting:** 0.5s zwischen Requests (Perplexity Limits beachten)
- **Dual-Key-Support:** PERPLEXITY_API_KEY_1 und _2 für Fallback

### Output
```json
{
  "generated_at": "...",
  "model": "sonar-pro",
  "total_processed": 431,
  "summary": {"ok": 350, "maybe": 60, "problem": 21},
  "items": [
    {
      "id": "review_001",
      "verdict": "ok",
      "issues": [],
      "aktuelle_quellen": [
        {"titel": "AWMF 021-003", "url": "https://...", "relevanz": "Primärquelle"}
      ]
    }
  ]
}
```

### CLI
```bash
PYTHONPATH=. .venv/bin/python3 scripts/batch_validate_with_perplexity.py \
  --input _OUTPUT/batch_corrected.json \
  --output _OUTPUT/batch_validated.json \
  --model sonar-pro \
  --resume
```

---

## Script 4: `scripts/finalize_batch_review.py`

### Zweck
Merge der Ergebnisse und **Erzeugung einer neuen, aktualisierten Arbeitsdatei**.

WICHTIG:
- `_OUTPUT/evidenz_antworten.json` wird **nur gelesen** und **niemals überschrieben**.
- Ergebnis wird als neue Datei mit Timestamp geschrieben.

### Inputs
- `_OUTPUT/batch_corrected.json` (aus Script 2)
- `_OUTPUT/batch_validated.json` (aus Script 3)
- `_OUTPUT/evidenz_antworten.json` (**read-only** Referenz)

### Logik
```python
base = load_evidenz_antworten_readonly()
updated = deepcopy(base)

for item in validated_items:
    if item["verdict"] == "ok":
        # In updated übernehmen (nicht in-place in base!)
        update_updated(updated, item["id"], item["antwort_korrigiert"])
        set_status(updated, item["id"], "ready")

    elif item["verdict"] == "maybe":
        # In updated übernehmen + Caveats-Liste
        update_updated(updated, item["id"], item["antwort_korrigiert"])
        set_status(updated, item["id"], "ready_with_caveats")
        add_to_caveats_list(item)

    elif item["verdict"] == "problem":
        # Nicht übernehmen, separate Liste
        add_to_remaining_issues(item)

write_json("_OUTPUT/evidenz_antworten_updated_<TS>.json", updated)
```

### Outputs
1. **`_OUTPUT/evidenz_antworten_updated_<TS>.json`** - Aktualisierte Arbeitsdatei (neu)
2. **`_OUTPUT/batch_review_report_YYYYMMDD.md`** - Markdown-Report
3. **`_OUTPUT/remaining_issues_YYYYMMDD.json`** - Items mit verdict=problem

### Report-Format
```markdown
# Batch-Review Report

**Datum:** 2025-12-16
**Verarbeitet:** 431 Items

## Zusammenfassung

| Status | Anzahl | Prozent |
|--------|--------|---------|
| ready | 350 | 81% |
| ready_with_caveats | 60 | 14% |
| needs_human_review | 21 | 5% |

## Kosten

| Phase | Modell | Kosten |
|-------|--------|--------|
| Korrektur | o4-mini:high | $1.50 |
| Validierung | sonar-pro | $2.00 |
| **Gesamt** | | **$3.50** |

## Top-Änderungen

1. **Dosierungen korrigiert:** 45 Items
2. **Leitlinien aktualisiert:** 32 Items
3. **Rechtliche Hinweise ergänzt:** 18 Items

## Verbleibende Issues (21)

| ID | Frage | Problem |
|----|-------|---------|
| review_042 | STIKO-Empfehlung... | Widersprüchliche Quellen |
| ... | ... | ... |
```

### CLI
```bash
PYTHONPATH=. .venv/bin/python3 scripts/finalize_batch_review.py \
  --corrected _OUTPUT/batch_corrected.json \
  --validated _OUTPUT/batch_validated.json \
  --output-dir _OUTPUT
```

---

## Wichtige Hinweise

### API-Keys (bereits in .env vorhanden)
```
REQUESTY_API_KEY=...      # Für OpenAI o4-mini
PERPLEXITY_API_KEY=...    # Für Sonar
```

### Bestehende Module nutzen
```python
# Diese Module existieren bereits und sollten verwendet werden:
from core.unified_api_client import UnifiedAPIClient
from core.guideline_fetcher import detect_medical_themes, GuidelineFetcher
from core.medical_validator import MedicalValidationLayer, validate_medical_content
```

### Checkpoint-Pattern (aus perplexity_factcheck_sample.py kopieren)
```python
def _append_checkpoint_jsonl(path: Path, obj: Dict[str, Any], fsync: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        if fsync:
            os.fsync(f.fileno())
```

### Error-Handling
```python
# Bei API-Fehlern: 3x retry mit exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_api(...):
    ...
```

---

## Ausführungsreihenfolge

```bash
# 1. Vorbereitung (keine API-Calls)
PYTHONPATH=. .venv/bin/python3 scripts/prepare_batch_review.py

# 2. OpenAI-Korrektur (~$1.50)
PYTHONPATH=. .venv/bin/python3 scripts/batch_correct_with_reasoning.py --resume

# 3. Perplexity-Validierung (~$2.00)
PYTHONPATH=. .venv/bin/python3 scripts/batch_validate_with_perplexity.py --resume

# 4. Finalisierung (keine API-Calls)
PYTHONPATH=. .venv/bin/python3 scripts/finalize_batch_review.py
```

---

## Erfolgskriterien

Nach Durchführung:
- [ ] 431 Items verarbeitet
- [ ] ~80% als `ready` markiert
- [ ] Alle mit Quellenangaben (Leitlinien-Reg.-Nr.)
- [ ] Report generiert
- [ ] **Neue** Datei `evidenz_antworten_updated_<TS>.json` geschrieben (ohne Überschreiben)
- [ ] Kosten < $5

---

## Bei Fragen

Die Projektdokumentation findest du in:
- `CLAUDE.md` - Projekt-Kontext und Workflow
- `BATCH_REVIEW_PLAN.md` - Detaillierter Plan
- `scripts/perplexity_factcheck_sample.py` - Referenz für Perplexity-Integration
- `core/unified_api_client.py` - Referenz für OpenAI/Requesty-Integration
