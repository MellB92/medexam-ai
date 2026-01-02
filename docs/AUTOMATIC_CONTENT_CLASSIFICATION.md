# Automatische Content-Klassifikation für MedExamAI

## Übersicht

Das automatische Klassifikationssystem ermöglicht es LLMs, medizinische Inhalte automatisch zu erkennen und das passende Antwortformat auszuwählen:

- **Krankheitsbilder/Klinische Fälle** → Strukturiertes Prüfungsformat (5 Abschnitte)
- **Andere Themen** (Ethik, Recht, Organisation) → Flexibles Format

## Architektur

### Kernkomponenten

1. **Content Classifier** (`core/content_classifier.py`)
   - Keyword-basierte Klassifikation
   - Pattern-Matching für strukturelle Erkennung
   - Konfidenz-Score und Fallback-Mechanismen

2. **Template Manager** (`core/template_manager.py`)
   - Verwaltet verschiedene Antwort-Templates
   - Automatische Template-Auswahl
   - Erweiterbare Template-Architektur

3. **Integration** (`scripts/generate_evidenz_answers.py`)
   - Automatische Klassifikation vor jeder Antwortgenerierung
   - Template-spezifische Prompt-Erstellung

## Content-Types

| Type | Beschreibung | Template | Strukturiert |
|------|-------------|----------|-------------|
| `DISEASE` | Krankheitsbilder, klinische Fälle | `structured_medical` | ✅ |
| `ETHICS` | Medizinethik, moralische Fragen | `ethics_discussion` | ❌ |
| `LAW` | Recht, Gesetze, Vorschriften | `legal_analysis` | ❌ |
| `ORGANIZATION` | Abläufe, Prozesse, Koordination | `organizational_process` | ❌ |
| `OTHER` | Sonstige Themen | `flexible_answer` | ❌ |

## Klassifikationslogik

### Keywords und Patterns

**Disease Keywords:**
- Symptome: symptome, beschwerden, schmerzen, dyspnoe
- Diagnostik: diagnose, diagnostik, labor, bildgebung
- Therapie: therapie, behandlung, medikation, operation
- Pathophysiologie: pathophysiologie, ätiologie, pathogenese

**Disease Patterns:**
- `chronisch.*erkrankung`
- `diagnose.*therapie`
- `symptome.*behandlung`

### Beispiel-Klassifikationen

```python
# Krankheitsbild → strukturiertes Format
"Was sind die Symptome einer Pneumonie?"
→ DISEASE (structured_medical, strukturiert=True)

# Ethik → flexibles Format
"Wie lässt sich dieser Widerspruch lösen?" (Organspende-Kontext)
→ ETHICS (ethics_discussion, strukturiert=False)

# Recht → flexibles Format
"Welches Gesetz regelt die Organspende?"
→ LAW (legal_analysis, strukturiert=False)
```

## Template-Strukturen

### Structured Medical (für Krankheiten)

```markdown
## 1) Definition/Klassifikation
## 2) Pathophysiologie/Ätiologie
## 3) Diagnostik (Schritte, Red Flags)
## 4) Therapie (inkl. Dosierungen – nur nach Leitlinienvalidierung)
## 5) Rechtliches/Organisation (falls relevant)
```

### Ethics Discussion (für ethische Fragen)

```markdown
## Ethischer Konflikt
## Relevante ethische Prinzipien
## Verschiedene Standpunkte
## Empfehlung und Begründung
```

### Legal Analysis (für rechtliche Fragen)

```markdown
## Rechtliche Grundlagen
## Gesetzliche Regelungen
## Praktische Anwendung
## Fallbeispiele
```

## Integration in die Pipeline

### Automatische Klassifikation

```python
from core.template_manager import get_answer_template

# Vor jeder Antwortgenerierung
instructions = get_answer_template(question, context)
# → Gibt automatisch das passende Template zurück
```

### Prompt-Erstellung

Der System-Prompt wird automatisch um Template-spezifische Instructions erweitert:

```
Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.
[... standard instructions ...]

# Antwort-Template: structured_medical
Strukturiertes Prüfungsformat für Krankheitsbilder...

## Wichtige Regeln:
- Antworte NUR auf Deutsch
- Verwende evidenzbasierte Informationen
[...]
```

## Verwendung

### Für Entwickler

```python
from core.content_classifier import classify_medical_content
from core.template_manager import get_answer_template

# Klassifikation
result = classify_medical_content("Wie behandelt man eine Pneumonie?")
print(f"Type: {result.content_type.value}")
print(f"Template: {result.suggested_template}")
print(f"Strukturiert: {result.requires_structured_format}")

# Template-Instructions
instructions = get_answer_template("Wie behandelt man eine Pneumonie?")
# → Vollständige Prompt-Instructions für KI
```

### Für KI-Workflows

Die Integration erfolgt automatisch in `generate_evidenz_answers.py`:

1. Frage wird klassifiziert
2. Passendes Template wird ausgewählt
3. Prompt wird mit Template-Instructions angereichert
4. KI erhält kontext-spezifische Format-Anweisungen

## Erweiterung und Anpassung

### Neue Templates hinzufügen

1. **Template definieren** in `core/template_manager.py`:

```python
self.templates['new_template'] = AnswerTemplate(
    name='new_template',
    description='Beschreibung...',
    structure=['Abschnitt 1', 'Abschnitt 2'],
    instructions='Detaillierte Anweisungen...',
    examples=['Beispiel 1', 'Beispiel 2'],
    required_sections=['Abschnitt 1']
)
```

2. **Klassifikation erweitern** in `core/content_classifier.py`:

```python
# Neue Keywords
self.new_keywords = {'keyword1', 'keyword2'}

# In _count_keywords hinzufügen
scores[ContentType.NEW_TYPE] = self._count_keywords(text, self.new_keywords)
```

### Custom Templates

Templates können als JSON-Dateien in `core/templates/` gespeichert werden:

```json
{
  "name": "custom_template",
  "description": "Custom template description",
  "structure": ["Section 1", "Section 2"],
  "instructions": "Detailed instructions...",
  "examples": ["Example 1"],
  "required_sections": ["Section 1"]
}
```

## Testing und Validation

### Unit Tests

```bash
cd Medexamenai_migration_full_20251217_204617
python -m pytest tests/test_content_classifier.py -v
```

### Beispiel-Tests

```python
# Test-Klassifikation
test_cases = [
    ("Herzinsuffizienz Symptome?", "DISEASE"),
    ("Organspende Ethik?", "ETHICS"),
    ("Transplantationsgesetz?", "LAW"),
    ("Stationsablauf?", "ORGANIZATION")
]

for question, expected in test_cases:
    result = classify_medical_content(question)
    assert result.content_type.value == expected
```

## Performance und Monitoring

### Metriken

- **Klassifikationsgenauigkeit:** % korrekt klassifizierter Fragen
- **Template-Zufriedenheit:** % Antworten, die Template einhalten
- **Fallback-Rate:** % Fälle, die auf `flexible_answer` zurückfallen

### Monitoring

```python
# In generate_evidenz_answers.py
classification_result = classify_medical_content(question, context)
logger.info(f"Classification: {classification_result.content_type.value} "
           f"(confidence: {classification_result.confidence:.2f})")
```

## Troubleshooting

### Häufige Probleme

1. **Falsche Klassifikation**
   - Keywords erweitern in `content_classifier.py`
   - Neue Patterns hinzufügen

2. **Template passt nicht**
   - Template-Instructions anpassen
   - Neues Template erstellen

3. **KI hält sich nicht an Format**
   - Instructions verstärken
   - Temperature reduzieren (für strukturierte Antworten)

### Debug-Modus

```python
# Detaillierte Klassifikation anzeigen
result = classify_medical_content(question, context)
print(f"Content-Type: {result.content_type.value}")
print(f"Confidence: {result.confidence}")
print(f"Indicators: {result.indicators}")
print(f"Template: {result.suggested_template}")
```

## Zukunftsentwicklung

### Mögliche Erweiterungen

1. **ML-basierte Klassifikation**
   - Training mit annotierten Daten
   - BERT-basierte Content-Analyse

2. **Kontext-sensitive Templates**
   - Berücksichtigung vorheriger Fragen
   - Adaptive Templates basierend auf Konversation

3. **Multi-linguale Unterstützung**
   - Englische Keywords
   - Sprach-erkennung

4. **Feedback Loop**
   - Manuelle Korrektur von Klassifikationen
   - Continuous Learning

## Support

Bei Fragen oder Problemen:
1. **Dokumentation prüfen:** `docs/AUTOMATIC_CONTENT_CLASSIFICATION.md`
2. **Tests ausführen:** `python -m pytest tests/test_content_classifier.py`
3. **Logs prüfen:** Classification-Events in den Logs
4. **Issue erstellen:** Mit Beispiel-Frage und erwartetem Ergebnis

