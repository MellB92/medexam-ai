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

## Aktuelle Arbeit (Stand: 2025-12-04)

### Abgeschlossen
- [x] Halluzinations-Bereinigung (440 von 483 entfernt)
- [x] Medical Fact Checker implementiert
- [x] RAG-Index Build: 183.979 Einträge, 79.793 Embeddings gecached
- [x] Multi-Provider API-Chain (Anthropic, Requesty, OpenRouter)
- [x] Konfidenz-Validierungs-Pipeline
- [x] LLM-Review Workflow für ChatGPT vorbereitet

### In Arbeit
- [ ] Antwort-Generierung: ~786/2689 Fragen (29%) - läuft automatisch
- [ ] Kosten bisher: €2.29 (geschätzt €8-10 total)

### Nächste Schritte
- [ ] Qualitäts-Review der generierten Antworten
- [ ] Konfidenz-Optimierung via externen LLM (ChatGPT)

## Entwickler
**Soloentwickler**: Dagoberto (er/ihm)

## Jira-Board
https://xcorpiodbs.atlassian.net/jira/software/projects/MED/boards/7

## Technologie-Stack
- Python 3.11+
- pypdf fur PDF-Verarbeitung
- Perplexity API fur medizinische Web-Suche
- FAISS/ChromaDB fur Vector Store (geplant)
