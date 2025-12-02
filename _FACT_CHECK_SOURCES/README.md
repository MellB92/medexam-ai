# _FACT_CHECK_SOURCES

## Zweck

Dieser Ordner enthält **ausschliesslich Referenzquellen zur Faktenprufung**.

Die Dateien in diesem Ordner werden **NUR** verwendet um:
- Medizinische Fakten in den Lerndaten zu verifizieren
- Dosierungen, Klassifikationen und Laborwerte zu prufen
- Falsche Informationen zu identifizieren

## NICHT verwenden fur

- Generierung von neuen Lerninhalten
- Training von Modellen
- Export in Endprodukte

## Unterstutzte Formate

- PDF (Leitlinien, Fachbucher)
- Markdown (.md)
- Text (.txt)
- JSON (strukturierte Daten)

## Struktur

```
_FACT_CHECK_SOURCES/
├── README.md           # Diese Datei
├── leitlinien/         # AWMF-Leitlinien
├── fachinformation/    # Fachinformationen zu Medikamenten
├── laborwerte/         # Referenzbereiche
└── klassifikationen/   # Medizinische Klassifikationen
```

## Verwendung

Der `medical_fact_checker.py` liest diese Quellen automatisch:

```python
from core.medical_fact_checker import MedicalFactChecker

checker = MedicalFactChecker(
    use_web_search=True,
    use_local_sources=True,  # Liest aus _FACT_CHECK_SOURCES
)
```
