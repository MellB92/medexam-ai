# Gemini CLI (Gemini 3 Pro) – Aufgabenbriefing (Stand: 2025-12-12)

---

## MedGemma Deployment auf Vertex AI (Stand: 2025-12-26)

### Endpoint-Konfiguration

| Parameter | Wert |
|-----------|------|
| Projekt | `medexamenai` |
| Region | `us-central1` |
| Endpoint ID | `mg-endpoint-f9aef307-eca7-4627-8290-b6e971b34474` |
| Model ID | `google_medgemma-27b-it-1766491479319` |
| GPU | NVIDIA A100 80GB (a2-ultragpu-1g) |

### Deploy-Befehl (GETESTET)

```bash
gcloud ai endpoints deploy-model mg-endpoint-f9aef307-eca7-4627-8290-b6e971b34474 \
  --project=medexamenai \
  --region=us-central1 \
  --model=google_medgemma-27b-it-1766491479319 \
  --display-name=medgemma-27b-deployment \
  --machine-type=a2-ultragpu-1g \
  --accelerator=type=nvidia-a100-80gb,count=1 \
  --min-replica-count=1 \
  --max-replica-count=1
```

### API-Aufruf Format (chatCompletions)

```json
{
    "instances": [{
        "@requestFormat": "chatCompletions",
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": "Du bist ein medizinischer Experte."}]},
            {"role": "user", "content": [
                {"type": "text", "text": "Frage hier..."},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
            ]}
        ],
        "max_tokens": 300
    }]
}
```

### Python SDK Beispiel

```python
from google.cloud import aiplatform

project = 'medexamenai'
region = 'us-central1'
endpoint_id = 'mg-endpoint-f9aef307-eca7-4627-8290-b6e971b34474'

aiplatform.init(project=project, location=region)
endpoint = aiplatform.Endpoint(
    endpoint_name=f'projects/{project}/locations/{region}/endpoints/{endpoint_id}'
)

request = {
    '@requestFormat': 'chatCompletions',
    'messages': [
        {'role': 'system', 'content': [{'type': 'text', 'text': 'Du bist ein medizinischer Experte.'}]},
        {'role': 'user', 'content': [{'type': 'text', 'text': 'Was sind die EKG-Zeichen bei Vorhofflimmern?'}]}
    ],
    'max_tokens': 300
}

response = endpoint.predict(instances=[request])
```

### Validierungsstatus

- **Validiert:** 356/447 (80%)
- **Ausstehend:** ~91 Fragen
- **Kosten bisher:** ~$0.08
- **Script:** `scripts/batch_validate_medgemma_questions.py --resume`

### Bekannte Fehler

| Fehler | Lösung |
|--------|--------|
| "Model server exited" | GPU-Parameter fehlen beim Deploy |
| "Model not found" | Korrekte Model ID: `google_medgemma-27b-it-1766491479319` |

---

## Aktueller Stand (verifiziert)
- Fragenbasis dedupe: 4.556 (Meaningful 2.527, Fragmente 2.029) in `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json`.
- Meaningful Coverage: **100.0% (2.527/2.527)**.
- Hauptantwortdatei: `_OUTPUT/evidenz_antworten.json` (**4.505 Q&A**).
- Relevanz-Vollvalidierung (gpt-4o-mini Judge): `_OUTPUT/validation_full_results.json` (Score 1–2 kommen überwiegend von Fragment-Fragen).

## Deine Aufgaben (Priorität)
### 1) Fragmente rekonstruieren (kontextbasiert, batchweise, automatisch weiter)
Ziel: Aus fragmentartigen Fragen echte, beantwortbare Fragen rekonstruieren (nur wenn klarer Kontext im Gold-Standard existiert).

Input:
- `_OUTPUT/fragmente_relevant.json` (≈385 Kandidaten; enthält `original`, `reconstructed`, `source_file`, `block_id`)

Output:
- `_OUTPUT/fragmente_reconstructed_batches.json` (append-only), Einträge:
  - `index`, `original`, `new_question`, `source_file`, `block_id`, `confidence`, `notes`

Arbeitsweise:
- In Batches von 20 (0–19, 20–39, …) bis Dateiende.
- Kontext nur in der angegebenen `source_file` unter `_GOLD_STANDARD/` prüfen (keine globale Volltextsuchen über alle Quellen).
- Wenn rekonstruierbar: `new_question` so nah wie möglich am Wortlaut des Dokuments; **keine neuen Inhalte erfinden**.
- Wenn nicht rekonstruierbar: markiere als `unanswerable_reason: "no_context"` und **keine Frage formulieren**.
- Automatisierung: schreibe/führe ein kleines Python-Skript aus, das Batches der Reihe nach verarbeitet und nach jedem Batch speichert (kein reines Chat-“Weiter?”).

### 2) Fakten-/Quellen-Stichprobe (Perplexity/Leitlinien)
Ziel: evidenzbasierte Quellenvorschläge für echte Verbesserungen, ohne gute Antworten unnötig umzuschreiben.

Input:
- `_OUTPUT/evidenz_antworten.json` (nur meaningful oder priorisiert: meaningful mit Score≤2)

Output:
- Kurzliste (JSON/MD): `{frage, issue, suggested_source_url_or_guideline, optional_fix_snippet}`

## Hinweise (wichtig)
- Relevanz-Validator ≠ Perplexity: der Relevanz-Check ist gpt-4o-mini; Perplexity ist für Web-Suche/Faktencheck.
- Fokus auf Evidenz/Quellen (AWMF/RKI/PEI/DocCheck/Fachinfo) und konkrete Korrekturen.
