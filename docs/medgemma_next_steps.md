# MedGemma Integration - Nächste Schritte

## Übersicht

Die MedGemma 27B Integration wurde erfolgreich abgeschlossen:

- **Endpoint:** `mg-endpoint-f9aef307-eca7-4627-8290-b6e971b34474`
- **Modell:** `google/medgemma-27b-it` (Multimodal)
- **Region:** `us-central1`
- **GPU:** A100 80GB

Dieses Dokument beschreibt die drei verfügbaren Skripte für die nächsten Schritte.

---

## 1. Bild-Extraktion aus PDFs

### Skript: `scripts/extract_ekg_images.py`

Extrahiert medizinische Bilder (EKG, Röntgen, etc.) aus PDFs.

### Verwendung

```bash
# Standard-Extraktion (EKG-Verzeichnis)
python scripts/extract_ekg_images.py

# Mit benutzerdefinierten Parametern
python scripts/extract_ekg_images.py \
  --input-dir _FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie \
  --output-dir _OUTPUT/ekg_images \
  --dpi 200

# Nur EKG-relevante PDFs
python scripts/extract_ekg_images.py --ekg-only

# Mit OCR (erfordert pytesseract)
python scripts/extract_ekg_images.py --ocr

# Dry-Run (zeigt was gemacht würde)
python scripts/extract_ekg_images.py --dry-run
```

### Parameter

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--input-dir` | `_FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie` | Quellverzeichnis |
| `--output-dir` | `_OUTPUT/ekg_images` | Zielverzeichnis |
| `--dpi` | 200 | Bildauflösung |
| `--pattern` | `*.pdf` | Datei-Pattern |
| `--ocr` | False | OCR aktivieren |
| `--ekg-only` | False | Nur EKG-PDFs |

### Ausgabe

- `_OUTPUT/ekg_images/*.png` - Extrahierte Bilder
- `_OUTPUT/ekg_images/extraction_manifest.json` - Metadaten

### Abhängigkeiten

```bash
pip install PyMuPDF
# Optional für OCR:
pip install pytesseract pillow
```

---

## 2. Multimodale Validierung

### Skript: `scripts/validate_medgemma_images.py`

Sendet Fragen mit zugehörigen Bildern an MedGemma für multimodale Analyse.

### Verwendung

```bash
# Standard-Validierung (5 Fragen, 10€ Budget)
python scripts/validate_medgemma_images.py

# Mit Parametern
python scripts/validate_medgemma_images.py \
  --batch-size 5 \
  --budget 10.0 \
  --filter-type EKG

# Nur bestimmte Anzahl
python scripts/validate_medgemma_images.py --limit 20

# Dry-Run
python scripts/validate_medgemma_images.py --dry-run
```

### Parameter

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--questions` | `_OUTPUT/medgemma_bild_fragen.json` | Fragen-Datei |
| `--images-dir` | `_OUTPUT/ekg_images` | Bilder-Verzeichnis |
| `--output` | `_OUTPUT/medgemma_image_responses.json` | Ausgabedatei |
| `--batch-size` | 5 | Anfragen pro Batch |
| `--budget` | 10.0 | Max. Budget (EUR) |
| `--filter-type` | - | EKG, Röntgen, CT, MRT, Sonographie, Dermatologie |
| `--limit` | - | Max. Anzahl Fragen |

### Ausgabe

```json
{
  "validation_stats": {
    "total_questions": 50,
    "validated": 45,
    "with_image": 30,
    "errors": 5,
    "total_cost_usd": 0.0234
  },
  "results": [
    {
      "frage_id": "IMG_0001",
      "bild_typ": "EKG",
      "medgemma_antwort": "...",
      "success": true
    }
  ]
}
```

---

## 3. Batch-Validierung (alle Fragen)

### Skript: `scripts/batch_validate_medgemma_questions.py`

Validiert alle 310 MedGemma-relevanten Fragen mit Checkpointing.

### Verwendung

```bash
# Standard-Batch (alle relevanten Fragen)
python scripts/batch_validate_medgemma_questions.py --budget 20.0

# Nur hohe Priorität
python scripts/batch_validate_medgemma_questions.py --priority hoch

# Nur MedGemma-relevante
python scripts/batch_validate_medgemma_questions.py --medgemma-relevant-only

# Von Checkpoint fortsetzen
python scripts/batch_validate_medgemma_questions.py --resume

# Begrenzte Anzahl
python scripts/batch_validate_medgemma_questions.py --max-questions 50
```

### Parameter

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--questions` | `_OUTPUT/medgemma_bild_fragen.json` | Fragen-Datei |
| `--output` | `_OUTPUT/medgemma_batch_validation.jsonl` | Ausgabe (JSONL) |
| `--budget` | 20.0 | Max. Budget (EUR) |
| `--batch-size` | 10 | Anfragen pro Batch |
| `--resume` | False | Von Checkpoint fortsetzen |
| `--priority` | - | hoch, mittel, niedrig |
| `--medgemma-relevant-only` | False | Nur relevante Fragen |
| `--max-questions` | - | Max. Anzahl |

### Ausgabe

- `medgemma_batch_validation.jsonl` - Eine Zeile pro Frage (Streaming)
- `medgemma_batch_validation.checkpoint.json` - Für Wiederaufnahme
- `medgemma_batch_validation.summary.json` - Zusammenfassung

### Checkpointing

Das Skript speichert alle 10 Fragen einen Checkpoint. Bei Unterbrechung:

```bash
# Fortsetzen von letztem Stand
python scripts/batch_validate_medgemma_questions.py --resume
```

---

## Konfiguration (.env)

Die Skripte nutzen folgende Umgebungsvariablen:

```env
# Google Cloud / MedGemma
GOOGLE_CLOUD_PROJECT=medexamenai
GOOGLE_CLOUD_REGION=us-central1
MEDGEMMA_ENDPOINT_ID=mg-endpoint-f9aef307-eca7-4627-8290-b6e971b34474
MEDGEMMA_MODEL=google/medgemma-27b-it
MEDGEMMA_BUDGET_EUR=217.75
```

---

## UnifiedAPIClient Integration

MedGemma ist jetzt in `core/unified_api_client.py` integriert:

```python
from core.unified_api_client import UnifiedAPIClient

# MedGemma direkt nutzen
client = UnifiedAPIClient()
result = client.chat_completion(
    prompt="Was sind die EKG-Befunde bei Vorhofflimmern?",
    provider="medgemma",
    max_tokens=500
)

print(result.response_text)
```

### Unterstützte Modi

1. **Endpoint-Modus** (empfohlen): Nutzt deployed Endpoint via `MEDGEMMA_ENDPOINT_ID`
2. **Model-Modus**: Direkte GenerativeModel-Nutzung (erfordert Service Account)

---

## Kosten-Übersicht

| Aktion | Geschätzte Kosten |
|--------|-------------------|
| 10 Fragen validieren | ~€0.10 |
| 100 Fragen validieren | ~€1.00 |
| Alle 310 relevanten Fragen | ~€3.00 |
| Mit Bildern (multimodal) | ~€0.50/Bild zusätzlich |

**Budget:** €217.75 verfügbar

---

## Empfohlene Reihenfolge

1. **Bild-Extraktion** - Extrahiere EKG-Bilder aus PDFs
   ```bash
   python scripts/extract_ekg_images.py --ekg-only
   ```

2. **Test-Validierung** - Teste mit 10 Fragen
   ```bash
   python scripts/batch_validate_medgemma_questions.py --max-questions 10 --budget 1.0
   ```

3. **Multimodale Validierung** - Teste Bilder
   ```bash
   python scripts/validate_medgemma_images.py --limit 5 --filter-type EKG
   ```

4. **Batch-Validierung** - Alle relevanten Fragen
   ```bash
   python scripts/batch_validate_medgemma_questions.py --medgemma-relevant-only --budget 20.0
   ```

---

## Statistik der identifizierten Fragen

| Bildtyp | Anzahl | MedGemma-relevant |
|---------|--------|-------------------|
| EKG | 122 | ✓ |
| Röntgen | 100 | ✓ |
| CT | 73 | ✓ |
| Sonographie | 26 | ✓ |
| MRT | 15 | ✓ |
| Sonstige | 111 | - |
| **Gesamt** | **447** | **310** |

Hohe Priorität: 222 Fragen

---

## Troubleshooting

### Fehler: "MEDGEMMA_ENDPOINT_ID nicht konfiguriert"

Prüfe `.env`:
```bash
grep MEDGEMMA .env
```

### Fehler: "google.auth.exceptions.DefaultCredentialsError"

```bash
gcloud auth application-default login
```

### Budget erschöpft

```bash
# Prüfe verbleibende Kosten
python -c "from core.unified_api_client import UnifiedAPIClient; c = UnifiedAPIClient(); print(c.providers.get('medgemma'))"
```

---

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `scripts/extract_ekg_images.py` | Bild-Extraktion |
| `scripts/validate_medgemma_images.py` | Multimodale Validierung |
| `scripts/batch_validate_medgemma_questions.py` | Batch-Validierung |
| `core/unified_api_client.py` | API-Client (angepasst) |
| `_OUTPUT/medgemma_bild_fragen.json` | Identifizierte Bild-Fragen |
