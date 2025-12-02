# Medexamenai - Projekt-Kontext

## Projektziel
Medizinisches Prufungsvorbereitungssystem fur die **Kenntnisprufung** (Approbationsprufung fur auslandische arzte in Deutschland).

## Kernfunktionen
1. **Fragen-Datenbank**: Extraktion und Deduplizierung von Prufungsfragen
2. **Antwort-Generierung**: KI-gestutzte Antworten basierend auf Leitlinien
3. **Fakten-Verifikation**: Prufung medizinischer Fakten gegen Perplexity/Leitlinien
4. **RAG-System**: Retrieval-Augmented Generation fur prazise Antworten

## Wichtige Verzeichnisse
- `_GOLD_STANDARD/` - Original-Prufungsprotokolle (PDFs)
- `_LLM_ARCHIVE/` - Generierte Antworten (roh)
- `_LLM_ARCHIVE_CLEAN/` - Bereinigte Antworten (ohne Halluzinationen)
- `_BIBLIOTHEK/Leitlinien/` - AWMF-Leitlinien nach Fachgebiet
- `_FACT_CHECK_SOURCES/` - Referenzquellen NUR fur Faktenprufung
- `_DERIVED_CHUNKS/` - Verarbeitete Textchunks

## Kernskripte
- `core/medical_fact_checker.py` - Medizinische Faktenprufung
- `core/rag_system.py` - RAG-Implementierung
- `core/web_search.py` - Perplexity API Integration
- `scripts/generate_answers.py` - Antwort-Generierung
- `scripts/sort_fact_check_sources.py` - Quellenorganisation

## API-Konfiguration
- Perplexity API fur Web-Suche (PERPLEXITY_API_KEY)
- Portkey fur Multi-Provider-Routing
- OpenRouter als Fallback

## Aktuelle Arbeit (Stand: 2025-12-02)
- Halluzinations-Bereinigung abgeschlossen (440 von 483 entfernt)
- Medical Fact Checker implementiert und verbessert
- Fakten-Extraktion mit Medikament+Dosierung (z.B. "Ramipril 5 mg")
- _FACT_CHECK_SOURCES Ordnerstruktur erstellt

## Offene Aufgaben
- [ ] Quellen in _FACT_CHECK_SOURCES sortieren
- [ ] RAG-Index mit bereinigten Daten aufbauen
- [ ] Antwort-Generierung fur alle Fragen starten

## Technologie-Stack
- Python 3.11+
- pypdf fur PDF-Verarbeitung
- Perplexity API fur medizinische Web-Suche
- FAISS/ChromaDB fur Vector Store (geplant)
