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

## KRITISCHER WORKFLOW-STATUS (Stand: 2025-12-05 12:25 Uhr)

### ⚠️ DIESE INFO NICHT VERGESSEN BEI CONTEXT-KOMPRESSION:

**Fragen-Status:**
- Original: 9.633 Fragen aus Prüfungsprotokollen
- Nach Deduplizierung: **2.689 unique Fragen** (frage_bloecke_dedupe.json)
- Bereits beantwortet: **~1.743 Antworten** (65%)
- Noch offen: **~946 Fragen** (35%)

**Checkpoint-System:**
- Checkpoints sind eingerichtet mit `--resume` Flag
- Antworten in: `_OUTPUT/evidenz_antworten.json`
- Checkpoint-Backup: `_OUTPUT/evidenz_antworten.checkpoint.json`
- **NIE alle Fragen neu generieren!** Immer `--resume` verwenden!

### 🔧 LETZTE CODE-ÄNDERUNG VOR NEUSTART (2025-12-05)

**Problem**: Claude Opus 4.5 wurde direkt zur Anthropic API geroutet statt über Requesty.

**Lösung**: `select_provider_model()` in `scripts/generate_evidenz_answers.py` (Zeile 562-578) wurde gefixt:
- ALLE Requests gehen jetzt über **Requesty** Router
- High complexity: `("requesty", "anthropic/claude-opus-4-5-20251101")`
- Low/Medium: `("requesty", "openai/gpt-5.1-mini-high")`

**Nach Neustart testen mit:**
```bash
PYTHONPATH=. PYTHONUNBUFFERED=1 .venv/bin/python3 scripts/generate_evidenz_answers.py --limit 5 --budget 10.0 --resume 2>&1
```

Prüfen dass Output zeigt:
- `Modellwahl: openai/gpt-5.1-mini-high (requesty, medium)` für normale Fragen
- `Modellwahl: anthropic/claude-opus-4-5-20251101 (requesty, high)` für komplexe Fragen
- HTTP Requests gehen an `router.requesty.ai` (NICHT `api.anthropic.com`)

**Wenn Test erfolgreich**, restliche Fragen generieren:
```bash
PYTHONPATH=. PYTHONUNBUFFERED=1 .venv/bin/python3 scripts/generate_evidenz_answers.py --process-all --batch-size 100 --budget 50.0 --resume 2>&1
```

### Abgeschlossen
- [x] Halluzinations-Bereinigung (440 von 483 entfernt)
- [x] Fragen-Deduplizierung (9633 → 2689)
- [x] Medical Fact Checker implementiert
- [x] RAG-Index Build: 183.979 Einträge, 79.793 Embeddings gecached
- [x] Multi-Provider API-Chain (Anthropic, Requesty, OpenRouter)
- [x] Konfidenz-Validierungs-Pipeline
- [x] 1743 Antworten generiert (65% complete)
- [x] select_provider_model() gefixt für Requesty-Routing

### In Arbeit
- [ ] Test mit 5 Fragen über Requesty (nach Neustart)
- [ ] Restliche ~946 Fragen via Requesty beantworten

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
