# 🛠️ Development Guide - MedExamAI

## Inhaltsverzeichnis

- [Setup](#setup)
- [Architektur](#architektur)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Git Workflow](#git-workflow)
- [Common Tasks](#common-tasks)
- [Automated Reviews](#automated-reviews)

---

## Setup

### Voraussetzungen

```bash
# Python 3.11+
python3 --version

# Git
git --version
```

### Lokales Setup

```bash
# 1. Repository klonen
cd ~/Documents/Medexamenai

# 2. Virtual Environment (optional, aber empfohlen)
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# oder: .venv\Scripts\activate  # Windows

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Config validieren
python3 -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

### requirements.txt

```txt
pypdf>=3.17.0
python-docx>=1.1.0
pyyaml>=6.0.1

# Optional - für erweiterte Features
pytesseract>=0.3.10  # OCR für gescannte PDFs
```

---

## Architektur

### Design-Prinzipien

1. **KISS** - Keep It Simple, Stupid
2. **Single Responsibility** - Jedes Skript hat genau eine Aufgabe
3. **Stateless** - Keine komplexen State-Files
4. **Transparent** - Jede Datei kennt ihre Herkunft (`source_file`, `source_tier`)

### Pipeline-Übersicht

```
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: EXTRAKTION                                     │
├─────────────────────────────────────────────────────────┤
│ Input:  _GOLD_STANDARD/*.{pdf,docx}                     │
│ Tool:   scripts/extract_dialog_blocks.py                │
│ Output: _EXTRACTED_FRAGEN/frage_bloecke.json            │
│                                                          │
│ Funktion: Extrahiert echte Prüfungsfragen in Blöcken   │
│           mit Patientenkontext (F:, A: Pattern)         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: ANTWORT-GENERIERUNG                            │
├─────────────────────────────────────────────────────────┤
│ Input:  _EXTRACTED_FRAGEN/frage_bloecke.json            │
│ Tool:   scripts/generate_answers.py                     │
│ Output: _OUTPUT/qa_gold_standard.json                   │
│                                                          │
│ Funktion: Generiert Antworten im 5-Punkte-Schema       │
│           basierend auf Leitlinien (AWMF, ESC, DGK)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: MEDICAL VALIDATION                             │
├─────────────────────────────────────────────────────────┤
│ Input:  _OUTPUT/qa_gold_standard.json                   │
│ Tool:   scripts/validate_medical.py                     │
│ Output: _OUTPUT/_validated/qa_validated.json            │
│                                                          │
│ Funktion: 4 Prüfer (Dosage, ICD-10, Lab, Logic)        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: EXPORT                                         │
├─────────────────────────────────────────────────────────┤
│ Input:  _OUTPUT/_validated/qa_validated.json            │
│ Tool:   scripts/export.py                               │
│ Output: Anki-Karten, PDF, etc.                          │
└─────────────────────────────────────────────────────────┘
```

### Datenfluss-Diagramm

```
_GOLD_STANDARD/
    │
    ├── *.pdf      ─┐
    ├── *.docx     ─┼──> extract_dialog_blocks.py
    └── *.txt      ─┘
                     │
                     ↓
            _EXTRACTED_FRAGEN/
              frage_bloecke.json
                     │
                     ↓
            generate_answers.py
                     │
                     ↓
              _OUTPUT/
         qa_gold_standard.json
                     │
                     ↓
            validate_medical.py
                     │
                     ↓
           _OUTPUT/_validated/
            qa_validated.json
                     │
                     ↓
              export.py
                     │
                     ↓
          Anki/PDF/Web
```

---

## Coding Standards

### Python Style

Wir folgen **PEP 8** mit einigen Ausnahmen:

```python
# ✅ Gut
def extract_questions(pdf_path: Path) -> List[Question]:
    """Extrahiert Fragen aus einem PDF.
    
    Args:
        pdf_path: Pfad zum PDF
        
    Returns:
        Liste von Question-Objekten
    """
    questions = []
    # ...
    return questions

# ❌ Schlecht
def extractQuestions(pdfPath):
    qs = []
    # ...
    return qs
```

### Docstrings

```python
def process_document(
    file_path: Path,
    context_lines: int = 6
) -> Dict[str, Any]:
    """Verarbeitet ein Dokument und extrahiert Frage-Blöcke.
    
    Args:
        file_path: Pfad zum Dokument (PDF, DOCX, TXT)
        context_lines: Anzahl der Kontext-Zeilen vor jeder Frage
        
    Returns:
        Dictionary mit:
            - block_id: Eindeutige ID
            - questions: Liste von Fragen
            - context: Kontext-Text
            
    Raises:
        FileNotFoundError: Wenn Datei nicht existiert
        ValueError: Wenn Datei-Format nicht unterstützt
    """
    pass
```

### Type Hints

**Immer** Type Hints verwenden:

```python
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# ✅ Gut
def load_config(path: Path) -> Dict[str, str]:
    pass

# ❌ Schlecht
def load_config(path):
    pass
```

### Error Handling

```python
# ✅ Gut - Spezifische Exceptions
try:
    data = json.load(open(file_path))
except FileNotFoundError:
    print(f"❌ Datei nicht gefunden: {file_path}")
    return None
except json.JSONDecodeError as e:
    print(f"❌ Ungültiges JSON: {e}")
    return None

# ❌ Schlecht - Generische Exception
try:
    data = json.load(open(file_path))
except Exception as e:
    print(f"Error: {e}")
```

### Logging

```python
# ✅ Gut - Strukturiertes Logging
def extract_questions(pdf_path: Path) -> List[Question]:
    print(f"📄 Verarbeite: {pdf_path.name}")
    questions = []
    
    for idx, page in enumerate(pages):
        print(f"   Seite {idx + 1}/{total_pages}...", end='\r')
        # ...
    
    print(f"✅ {len(questions)} Fragen extrahiert")
    return questions

# ❌ Schlecht - Keine Ausgabe
def extract_questions(pdf_path):
    questions = []
    # ...
    return questions
```

---

## Testing

### Test-Struktur

```
tests/
├── test_extract_questions.py
├── test_extract_dialog_blocks.py
├── test_generate_answers.py
└── fixtures/
    ├── sample.pdf
    └── expected_output.json
```

### Beispiel-Test

```python
# tests/test_extract_questions.py
import pytest
from pathlib import Path
from scripts.extract_questions import extract_from_pdf, Question

def test_extract_simple_question():
    """Test: Einfache Frage wird korrekt extrahiert."""
    # Arrange
    pdf_path = Path("tests/fixtures/sample.pdf")
    
    # Act
    questions = list(extract_from_pdf(pdf_path))
    
    # Assert
    assert len(questions) > 0
    assert isinstance(questions[0], Question)
    assert questions[0].source_tier == "gold_standard"

def test_extract_no_hallucination():
    """Test: Keine fiktiven Cases werden erfunden."""
    pdf_path = Path("tests/fixtures/sample.pdf")
    questions = list(extract_from_pdf(pdf_path))
    
    # Alle Fragen müssen aus dem PDF stammen
    for q in questions:
        assert q.source_file == pdf_path.name
        assert q.frage.endswith("?")
```

### Tests ausführen

```bash
# Alle Tests
pytest tests/ -v

# Einzelner Test
pytest tests/test_extract_questions.py::test_extract_simple_question -v

# Mit Coverage
pytest --cov=scripts tests/

# Nur schnelle Tests (keine Integration)
pytest tests/ -m "not slow"
```

---

## Git Workflow

### Branch-Strategie

```bash
main                    # Production-ready code
  ├── feature/extract-dialog-blocks
  ├── feature/answer-generation
  └── fix/dosage-validation
```

### Commit-Konventionen

```bash
# Format: <type>(<scope>): <subject>

# Types:
feat:     Neues Feature
fix:      Bugfix
docs:     Dokumentation
style:    Formatierung (keine Code-Änderung)
refactor: Code-Refactoring
test:     Tests hinzufügen/ändern
chore:    Build/Setup

# Beispiele:
git commit -m "feat(extraction): Add dialog block extraction with context"
git commit -m "fix(dosage): Validate mg/kg dosages correctly"
git commit -m "docs(readme): Update quick start guide"
```

### Pre-Commit Checklist

Vor jedem Commit:

```bash
# 1. Code formatieren (optional)
black scripts/

# 2. Linting (optional)
pylint scripts/*.py

# 3. Tests laufen
pytest tests/ -v

# 4. Commit
git add .
git commit -m "feat(extraction): Add new feature"
git push
```

---

## Common Tasks

### Neue Frage-Extraktion hinzufügen

```bash
# 1. Feature-Branch erstellen
git checkout -b feature/new-extraction-pattern

# 2. Code ändern
# scripts/extract_dialog_blocks.py

# 3. Test hinzufügen
# tests/test_extract_dialog_blocks.py

# 4. Testlauf
pytest tests/test_extract_dialog_blocks.py -v

# 5. Commit & Push
git add scripts/ tests/
git commit -m "feat(extraction): Add new pattern for XYZ"
git push origin feature/new-extraction-pattern
```

### Neue Klassifikation hinzufügen

```python
# 1. In scripts/generate_answers.py (oder separates config file)
KLASSIFIKATIONEN = {
    # ... bestehende ...
    "neue_erkrankung": "Name der Klassifikation",
}

# 2. Test schreiben
def test_new_classification():
    # ...
    
# 3. Dokumentieren in README
```

### Debug-Modus

```python
# Füge am Anfang des Skripts hinzu:
import logging
logging.basicConfig(level=logging.DEBUG)

# Dann im Code:
logging.debug(f"Variable x = {x}")
logging.info(f"Processing {filename}")
logging.warning(f"Unexpected value: {value}")
logging.error(f"Failed to process: {error}")
```

### Performance-Profiling

```python
import time

start = time.time()
# ... code ...
end = time.time()
print(f"⏱️ Verarbeitung dauerte {end - start:.2f}s")
```

---

## Troubleshooting

### Problem: pypdf kann PDF nicht lesen

```bash
# Lösung 1: OCR verwenden
pip install pytesseract
# Dann in Code: ocr_fallback=True

# Lösung 2: PDF konvertieren
# Nutze Adobe Acrobat oder online-tools
```

### Problem: Zu viele/zu wenige Fragen extrahiert

```python
# Debug: Zeige erkannte Pattern
def extract_questions(..., debug=True):
    if debug:
        print(f"Pattern matches: {matches}")
        print(f"Context: {context}")
```

### Problem: Encoding-Fehler

```python
# Immer UTF-8 verwenden
with open(file_path, 'r', encoding='utf-8') as f:
    data = f.read()
```

---

## Best Practices

### 1. NIEMALS fiktive Cases erfinden

```python
# ❌ FALSCH
if "Pankreatitis" in text:
    case = generate_fake_case("Pankreatitis")  # VERBOTEN!

# ✅ RICHTIG
if "F:" in line:
    question = extract_literal_question(line)
```

### 2. Immer Tier taggen

```python
# ✅ RICHTIG
question = {
    "frage": "...",
    "source_tier": "gold_standard",  # PFLICHT!
    "source_file": "protokoll.pdf"
}
```

### 3. Backup vor Änderungen

```python
def safe_process(input_file: Path, output_file: Path):
    # Backup erstellen
    if output_file.exists():
        backup = output_file.with_suffix('.json.backup')
        shutil.copy(output_file, backup)
        print(f"💾 Backup: {backup}")
    
    # Dann Verarbeitung
    result = process(input_file)
    output_file.write_text(json.dumps(result, indent=2))
```

### 4. Validierung nach Filter

```python
def safe_filter(original: List, filtered: List, operation: str) -> bool:
    loss_percent = (1 - len(filtered) / len(original)) * 100
    
    if loss_percent > 90:
        print(f"🚨 KRITISCH: {operation} entfernt {loss_percent:.1f}%!")
        return False
    
    return True
```

---

## Nächste Schritte

1. [ ] `generate_answers.py` implementieren
2. [ ] `validate_medical.py` implementieren
3. [ ] `export.py` implementieren
4. [ ] Tests für alle Skripte schreiben
5. [ ] CI/CD Setup (GitHub Actions)
6. [ ] Jira-Integration dokumentieren

---

## Hilfreiche Links

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [PEP 8 Style Guide](https://pep8.org/)
- [Git Commit Conventions](https://www.conventionalcommits.org/)

---

## Automated Reviews

1. **AI Reviewer Workflow**
   - Workflow-Datei: `.github/workflows/ai-reviews.yml`
   - Trigger: PR Events (`opened`, `synchronize`, `reopened`) sowie Issue-Kommentare mit `@claude`, `@gemini`, `@ai-review`.
   - Claude nutzt `ANTHROPIC_API_KEY`, Gemini `GOOGLE_AI_API_KEY`. Ohne Keys werden Hinweise im Log ausgegeben.
   - Kommentare werden über die GitHub REST API gepostet, damit keine YAML-Quote-Probleme entstehen.

2. **CI Quality Gate**
   - Workflow: `.github/workflows/ci.yml`
   - Jobs `test` und `safety-check` müssen bestehen; das Job `quality-gate` aggregiert die Ergebnisse und schlägt fehl, wenn ein Check rot ist.
   - Branch Protection kann auf das `Quality Gate Summary`-Resultat verweisen.

3. **Manual Fallbacks**
   - GitHub Apps (Copilot PRs, CodeRabbit, Gemini for GitHub) können ohne API-Key installiert werden.
   - Reviewer können `@ai-review` kommentieren, um Hinweise zu erhalten (auch wenn keine Secrets konfiguriert sind).

4. **Setup Checklist**
   - [ ] Secrets in GitHub: `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`, `CODECOV_TOKEN`.
   - [ ] Optional: `CODECOV_TOKEN` (Coverage Upload) aktivieren.
   - [ ] Branch Protection Regel erstellt mit `Required status checks: Tests, Safety & Security, Quality Gate Summary`.
   - [ ] Team informiert (siehe README Abschnitt "Automated Code Reviews & Quality Gate").

---

**Letzte Aktualisierung:** 2024-12-01
