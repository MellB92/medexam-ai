# Entwickler-Leitfaden: Content-Klassifikation

## Schnellstart

```python
from core.template_manager import get_answer_template

# Automatische Template-Auswahl
instructions = get_answer_template("Wie behandelt man eine Pneumonie?")
print(instructions)  # → Vollständige KI-Instructions mit passendem Format
```

## Wichtige Konzepte

### Content Types

| Typ | Wann verwenden | Template |
|-----|---------------|----------|
| `DISEASE` | Symptome, Diagnose, Therapie | `structured_medical` |
| `ETHICS` | Moral, Autonomie, Prinzipien | `ethics_discussion` |
| `LAW` | Gesetze, Paragraphen, Recht | `legal_analysis` |
| `ORGANIZATION` | Abläufe, Prozesse, Koordination | `organizational_process` |
| `OTHER` | Alles andere | `flexible_answer` |

### Template-Struktur

```python
from core.template_manager import create_custom_template

# Neues Template erstellen
template = create_custom_template(
    name="my_template",
    description="Mein custom Template",
    structure=["Abschnitt 1", "Abschnitt 2"],
    instructions="Detaillierte Anweisungen...",
    examples=["Beispiel 1"],
    required_sections=["Abschnitt 1"]
)
```

## Testing

### Unit Tests

```bash
# Einzelne Tests
python -c "
from core.content_classifier import classify_medical_content
result = classify_medical_content('Pneumonie Symptome?')
print(f'Type: {result.content_type.value}, Template: {result.suggested_template}')
"
```

### Integration Tests

```bash
# Vollständige Pipeline testen
cd scripts
python generate_evidenz_answers.py --test-classification \
  --input test_questions.json \
  --output test_results.json
```

## Häufige Fehler

### 1. Falsche Klassifikation

**Problem:** Frage wird falsch klassifiziert
**Lösung:**
```python
# Keywords erweitern in content_classifier.py
self.disease_keywords.add('neues_keyword')
```

### 2. Template passt nicht

**Problem:** KI hält sich nicht an Template
**Lösung:**
```python
# Instructions verstärken in template_manager.py
instructions += "\n\nWICHTIG: Halte dich EXAKT an diese Struktur!"
```

### 3. Neue Content-Types

**Problem:** Neuer Themenbereich nicht abgedeckt
**Lösung:**
```python
# Neuen ContentType hinzufügen
class ContentType(Enum):
    NEW_TYPE = "new_type"

# Keywords und Template hinzufügen
self.new_keywords = {'keyword1', 'keyword2'}
# Template in _create_default_templates() hinzufügen
```

## Best Practices

1. **Keywords regelmäßig erweitern** basierend auf neuen Fragen
2. **Templates testen** mit verschiedenen Beispielen
3. **Fallback-Mechanismen** für unklare Fälle beibehalten
4. **Logging aktivieren** für Debugging
5. **Metrics tracken** für Qualitätsverbesserung

## Monitoring

```python
# Klassifikation loggen
import logging
logger = logging.getLogger(__name__)

result = classify_medical_content(question, context)
logger.info(f"Classification: {result.content_type.value} "
           f"(confidence: {result.confidence:.2f}, "
           f"template: {result.suggested_template})")
```

## Erweiterte Features

### Custom Templates laden

```python
# Aus JSON-Datei
{
  "name": "special_template",
  "description": "Special case template",
  "structure": ["Intro", "Details", "Conclusion"],
  "instructions": "Special instructions...",
  "examples": ["Example question"],
  "required_sections": ["Details"]
}
```

### Context-sensitive Klassifikation

```python
# Mit zusätzlichem Kontext
result = classify_medical_content(
    question="Wie lässt sich dieser Widerspruch lösen?",
    context="Patientenverfügung Organspende"  # Zusätzlicher Kontext
)
# → Erkennt automatisch ETHICS statt OTHER
```

## Support

- **Dokumentation:** `docs/AUTOMATIC_CONTENT_CLASSIFICATION.md`
- **Code-Beispiele:** `core/content_classifier.py` und `core/template_manager.py`
- **Tests:** `tests/test_content_classifier.py` (falls vorhanden)

