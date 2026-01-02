## MedExam‑AI – Code‑Stand Übersicht (für externen Berater / ChatGPT)

**Scope:** Nur lesen & dokumentieren (keine Code‑Änderungen).  
**Workspace:** `/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617`  
**Stand:** 2025‑12‑23

---

## 1) Verzeichnisstruktur (Baum, max. Tiefe 3)

Legende (Markierung):
- **[RAG]**: RAG‑System / Index‑Build / KB‑Artefakte
- **[Embeddings]**: Embedding‑Modelle / Cache
- **[MedGemma]**: Vertex‑AI MedGemma Integration / Bildfragenliste
- **[Fragen]**: Prüfungsfragen, Dedupe, Klassifikation
- **[PDF]**: PDF‑Quellen (Leitlinien, Lehrmaterial, Attachments)

```
/Users/entropie/Documents/Medexamenai_Migration
├── _OUTPUT/
│   └── validation_logs/                       (leer)
├── checkpoints/
├── Medexamenai_migration_full_20251217_204617/  ← Hauptprojekt
│   ├── core/                                  [RAG][Embeddings][MedGemma]
│   ├── scripts/                               [RAG][Fragen][Validierung][Batch]
│   ├── _OUTPUT/                               [RAG][MedGemma]
│   │   ├── rag_knowledge_base.json             [RAG]  (2.6 GB)
│   │   ├── rag_checkpoints/checkpoint.json     [RAG]  (PDF‑Fortschritt)
│   │   ├── medgemma_bild_fragen.json           [MedGemma] (447 Bildfragen)
│   │   └── logs/                               (z.B. Regen‑Runs)
│   ├── _BIBLIOTHEK/                            [PDF]
│   │   └── Leitlinien/                         [PDF] (fachgebiet‑basiert)
│   ├── _FACT_CHECK_SOURCES/                    [PDF]
│   │   ├── fachgebiete/                        [PDF] (fachgebiet‑basiert)
│   │   ├── Chirurgie/                          [PDF] (Vorlesungen u.ä.)
│   │   └── Input Bucket/                       (vom RAG‑Build per Default ausgeschlossen)
│   ├── _GOLD_STANDARD/                         [PDF][Fragen] (Protokolle, Telegram‑Reports)
│   ├── _EXTRACTED_FRAGEN/                      [Fragen]
│   ├── _DERIVED_CHUNKS/
│   ├── _PROCESSING/
│   ├── _WISSENSBASIS/
│   ├── _DOCS/
│   ├── docs/
│   └── .github/workflows/                      (CI / AI‑Reviews / Backups)
└── spaced_repetition/                          (separates Mini‑Modul)
```

---

## 2) Wichtige Dateien & Konfigurationen

### 2.1 Zentrale Konfiguration / Abhängigkeiten

- **`config.yaml`** (`Medexamenai_migration_full_20251217_204617/config.yaml`): Projektpfade + RAG‑Parameter (Chunking, `top_k`, Cache‑Dir). Budget‑Snapshot inkl. `google_workspace_eur: 217.75`.
- **`requirements.txt`** (`.../requirements.txt`): Kernlibs für PDF‑Extraktion (`pypdf`), lokale Embeddings (`sentence-transformers`) und Provider‑Routing (`python-dotenv`, `requests`, `tenacity`). OCR ist nur als Kommentar vorgesehen (`pytesseract` auskommentiert).
- **`pyproject.toml`** (`.../pyproject.toml`): Ruff‑Lint‑Konfig (`target-version = py39`, Line‑Length 120).
- **`.env`** (**erwartet**, nicht im Repo sichtbar): Wird von `core/unified_api_client.py` via `python-dotenv` geladen. Mehrere Skripte lesen Keys ebenfalls aus `.env` oder ENV.
- **`.env.example`**: In Doku mehrfach erwähnt (z. B. `MCP_REGISTRY.md`), im Workspace **nicht auffindbar**.
- **Jupyter Notebooks (`*.ipynb`)**: Im Workspace **keine** gefunden.
- **Deploy/Migration‑Skripte (Shell)**:
  - `MIGRATION_KIT/` (mehrere `*.sh`): Migration/Upload‑Hilfen (historisch, kein Runtime‑Code).
  - `upload_chunks.sh` (Root): Upload‑Hilfsskript (Cloud‑Bezug; hier nicht ausgeführt).

### 2.2 RAG / Index / Embeddings (Core‑Implementierung)

- **`core/rag_system.py`**: RAG‑Runtime. Speichert Wissensbasis **als JSON** (kein externer Vector‑Store). Lokales Default‑Embedding: `paraphrase-multilingual-mpnet-base-v2` (768D). OpenAI‑Embeddings optional über Portkey/OpenRouter/OpenAI.
- **`scripts/build_rag_index.py`**: RAG‑Index‑Builder. Lädt PDFs, extrahiert Text via `pypdf`, chunked, erzeugt Embeddings (lokal oder OpenAI) und schreibt `_OUTPUT/rag_knowledge_base.json`. Checkpoints: `_OUTPUT/rag_checkpoints/checkpoint.json`.
- **Embedding‑Cache**: `core/rag_system.py` nutzt `EmbeddingCache(cache_dir=".embedding_cache")` und persistiert nach `.embedding_cache/embeddings.json`.

### 2.3 Prüfungsfragen / Dedupe / Datenbasis

- **`_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json`**: Kanonische Fragenbasis (laut Doku 4.556 eindeutige Fragen).  
- **`docs/PROJEKT_STRUKTUR.md`**: Definiert strikt „PRÜFUNGSPROTOKOLLE vs FAKTEN vs OUTPUT“. RAG soll nur aus FAKTEN (z. B. `_BIBLIOTHEK`, `_FACT_CHECK_SOURCES`) gebaut werden.

### 2.4 Deploy / CI / Workflows

- **`.github/workflows/ci.yml`**: CI‑Checks (Tests/Lint etc.).  
- **`.github/workflows/daily-backup.yml`**: Automatische Backups.  
- **`.github/workflows/ai-reviews.yml`, `codex-review.yml`**: AI‑Review‑Automatisierung.

### 2.5 MCP / Tooling

- **`mcp_config.json`**: MCP‑Server‑Setup (Filesystem/Git/SQLite/etc.). Enthält u. a. SQLite‑Pfad `_OUTPUT/medexam.db` (DB‑File kann existieren, ist hier nicht weiter ausgewertet).

---

## 2.6 `rag_knowledge_base.json`: Lage & Ladepfad

### Datei
- **Pfad:** `Medexamenai_migration_full_20251217_204617/_OUTPUT/rag_knowledge_base.json`  
- **Größe:** ~2.6 GB

### Erzeugung
- **Builder:** `scripts/build_rag_index.py`  
- **Checkpoint:** `.../_OUTPUT/rag_checkpoints/checkpoint.json` (Liste bereits verarbeiteter PDFs)

### Laden (Runtime)
- **Core‑Loader:** `core/rag_system.py` → `MedicalRAGSystem.load_knowledge_base(path)`  
- **Beispiel‑Nutzung:** `scripts/generate_evidenz_answers.py` lädt `base_dir / "_OUTPUT/rag_knowledge_base.json"` und ruft `rag.load_knowledge_base(...)` auf.

### Format (wichtig für Berater)
- JSON mit Top‑Level Keys:
  - **`knowledge_base`**: Mapping `content_id -> {text, embedding, metadata, source_module, source_tier, ...}`
  - **`statistics`**: Zähler (z. B. total_items/by_module/by_tier/cache_size/cost_summary)
  - **`saved_at`**

---

## 2.7 MedGemma: Fundstellen / Endpoint‑Verweise / GPU‑Hinweise

### Code‑Integration (Vertex AI)
- **`core/unified_api_client.py`**:
  - Provider‑Key **`medgemma`** ist vorhanden (Priority 8).
  - Aktivierung nur wenn **`GOOGLE_APPLICATION_CREDENTIALS`** gesetzt ist und auf eine existierende Datei zeigt.
  - Modell über **`MEDGEMMA_MODEL`** (Default: `med-gemma-7b`).
  - Budget über **`MEDGEMMA_BUDGET`** (Default: 217.75).
  - Call‑Implementierung: `vertexai.generative_models.GenerativeModel(cfg.model).generate_content(...)`.
  - **Hinweis:** Im Repo ist **keine explizite Vertex‑Region/Projekt‑Initialisierung** (`vertexai.init(project=..., location=...)`) sichtbar. Diese Konfiguration muss daher über Runtime‑Umgebung erfolgen (oder ergänzt werden).

### Dokumentation / Betriebsannahmen
- **`CODEX_HANDOVER_2025-12-01.md`** und **`_DOCS/CODEX_STATUS_REPORT.md`**:
  - MedGemma wird als **„A100, €217.75“** geführt.
  - „Vertex AI deaktiviert“ / „nur Credentials aktivieren wenn bereit“.

### Konfig/Budget‑Referenzen
- **`config.yaml`**: `budget.remaining.google_workspace_eur: 217.75`  
- **`MCP_REGISTRY.md`**: Provider‑Tabelle enthält **Google Workspace → `GOOGLE_APPLICATION_CREDENTIALS` → €217.75**.

### URL / Region / GPU
- **URL:** Im Code **keine** harte Endpoint‑URL (SDK‑basiert).  
- **Region:** Im Code **nicht** fest verdrahtet.  
- **GPU:** In Doku als **A100** referenziert, nicht als technische Konfiguration im Code.

---

## 3) PDF‑Probleme (Textextraktion fehlgeschlagen)

### Kontext: Wie wird extrahiert?
- `scripts/build_rag_index.py` nutzt **`pypdf.PdfReader`** und `page.extract_text()`.  
- PDFs ohne eingebetteten Text (gescannt) liefern **0 Zeichen**.  
- Verschlüsselte PDFs können zusätzliche Dependencies erfordern.

### Die 13 PDFs (im RAG‑Build „fehlend“ gegenüber Checkpoint)

Diese 13 Dateien sind **im PDF‑Scan enthalten**, aber **nicht** in `_OUTPUT/rag_checkpoints/checkpoint.json` als verarbeitet markiert.  
Ein Kurztest mit `pypdf` ergab **0 extrahierbare Zeichen** (erste Seiten), bzw. 1× Verschlüsselungs‑Fehler.

1. `.../_BIBLIOTHEK/Leitlinien/Sonstige/OTHER_Heilberufsgesetz_NRW_HeilBerG_64f2a3.pdf` (0 Zeichen)
2. `.../_FACT_CHECK_SOURCES/fachgebiete/chirurgie/unfallchirurgie/Grundwortschatz Traumatologie_1.pdf` (0 Zeichen)
3. `.../_FACT_CHECK_SOURCES/fachgebiete/chirurgie/unfallchirurgie/Grundwortschatz Traumatologie_2.pdf` (0 Zeichen)
4. `.../_FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie/EKG Befunde 1.pdf` (0 Zeichen)
5. `.../_FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie/EKG Befunde 2.pdf` (0 Zeichen)
6. `.../_FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie/EKG Befunde.pdf` (0 Zeichen)
7. `.../_FACT_CHECK_SOURCES/fachgebiete/labormedizin/Die Einheiten der Laborwerte.pdf` (0 Zeichen)
8. `.../_FACT_CHECK_SOURCES/fachgebiete/labormedizin/Laborzettel 1.pdf` (0 Zeichen)
9. `.../_FACT_CHECK_SOURCES/fachgebiete/pharmakologie/Einstieg Medikamente mit Aufgaben.pdf` (0 Zeichen)
10. `.../_FACT_CHECK_SOURCES/fachgebiete/pharmakologie/Pharmakologie-Amboss (2).pdf` (**Fehler:** `cryptography>=3.1 is required for AES algorithm`)
11. `.../_FACT_CHECK_SOURCES/fachgebiete/pharmakologie/Zusatzübungen Medikamente Lösungen.pdf` (0 Zeichen)
12. `.../_FACT_CHECK_SOURCES/fachgebiete/pharmakologie/Zusatzübungen Medikamente.pdf` (0 Zeichen)
13. `.../_FACT_CHECK_SOURCES/fachgebiete/rechtsmedizin/Beispiele Gutachten.pdf` (0 Zeichen)

### Gibt es bereits Bild-/OCR‑Extraktion (z. B. PyMuPDF)?
- **PyMuPDF/`fitz`**: Im Repo **keine** Nutzung gefunden.  
- **OCR:** In `requirements.txt` nur als **Option** (`pytesseract` auskommentiert). In `PROJECT_STATUS.md` wird OCR als Risiko/Idee erwähnt, aber ohne Implementierung.

---

## 4) Bildbezogene Fragen (447 / 222)

### Primäres Dataset
- **Datei:** `.../_OUTPUT/medgemma_bild_fragen.json`
- **Inhalt:** Liste mit **447** Bildfragen‑Einträgen plus Statistik.

### Kennzeichnung / Felder pro Eintrag
Jeder Eintrag in `bild_fragen` hat (konstant):
- **`frage_id`**, **`original_index`**
- **`frage_text`** (Frage)
- **`antwort_text`** (aktuelle Antwort / Draft)
- **`bild_typ`** (z. B. `EKG`, `Röntgen`, `CT`, `MRT`, `Sonographie`, `Sonstige`)
- **`medgemma_relevant`** (Bool)
- **`prioritaet`** (String, z. B. `hoch`, `mittel`)
- **`match_keyword`** (welcher Keyword‑Treffer zur Klassifikation führte)

### Statistik (aus Datei)
- **gesamt:** 447  
- **medgemma_relevant:** 310  
- **hohe_prioritaet:** 222  
- **nach_typ:** `EKG` 122, `Röntgen` 100, `CT` 73, `Sonographie` 26, `MRT` 15, `Sonstige` 111

---

## 5) Validierungs‑ und Batch‑Skripte (4.556 Fragen / Kosten‑Management)

### Validierung (lokal & extern)
- **`scripts/validate_medical.py`**: Lokaler „Medical Validation Layer“ (Dosierungen, ICD‑10, Laborwerte, Logik). Output nach `_OUTPUT/validated/` inkl. `validation_report.md`. Keine externen LLM‑Calls.
- **`scripts/validate_full_dataset.py`**: Relevanz‑Check „passt Antwort zur Frage“ via **OpenAI Chat Completions** (`gpt-4o-mini`). Hat `--budget`, `--batch-size` (Checkpoint‑Intervall) und `time.sleep(0.15)` (Rate‑Limit).
- **`scripts/batch_validate_with_perplexity.py`**: Web‑Faktencheck über **Perplexity API** (Resume via JSONL‑Checkpoint). Parameter u. a. `PERPLEXITY_API_BASE`, Key‑Rotation (Key_1/Key_2), `max_tokens`, `timeout`.

### Batch‑Korrektur / Review‑Artefakte
- **`scripts/batch_correct_with_reasoning.py`**: Batch‑Korrektur (UnifiedAPIClient) mit JSONL‑Checkpointing (`_OUTPUT/batch_corrected_<RUN_ID>_checkpoint.jsonl`).
- **`scripts/generate_evidenz_answers.py`**: Haupt‑Workflow zur evidenzbasierten Antwortgenerierung. Nutzt RAG‑KB (`_OUTPUT/rag_knowledge_base.json`), `UnifiedAPIClient`, Resume‑Mechanik und Budget‑Stop.
  - Defaults: `--unanswered _OUTPUT/fragen_ohne_antwort.json`, `--blocks _EXTRACTED_FRAGEN/frage_bloecke_dedupe.json`, `--batch-size 100`, `--budget 5.0` (EUR).
  - Hinweis: Die Doku im Repo priorisiert oft `frage_bloecke_dedupe_verifiziert.json` (4.556), das Script defaultet aber auf `frage_bloecke_dedupe.json`.

### Kosten‑/Budget‑Mechaniken (relevant für Berater)
- **Provider‑Budgets**: In `core/unified_api_client.py` als Defaults + ENV‑Overrides (`*_BUDGET`).
- **Session‑Budget**: `UnifiedAPIClient(max_cost=...)` möglich; plus BudgetMonitor (`core/token_budget_monitor.py`).
- **Script‑Budgets**: Mehrere Skripte haben `--budget` und Checkpoint/Resume‑Design (z. B. `generate_evidenz_answers.py`, `validate_full_dataset.py`).

---

## 6) Kurzfazit für die externe Planung

### RAG‑Index / Embeddings
- Der Default für **lokale Embeddings** ist bereits `paraphrase-multilingual-mpnet-base-v2` (768D) in `core/rag_system.py`.
- Der Index liegt als **JSON‑Wissensbasis** vor (`_OUTPUT/rag_knowledge_base.json`) plus `.embedding_cache`.

### MedGemma
- MedGemma ist als Provider im **UnifiedAPIClient** vorhanden (Vertex‑SDK).  
- Für produktive Nutzung fehlen im Repo sichtbar: **explizite Region/Projekt‑Initialisierung** und ein dedizierter Batch‑Runner, der gezielt `provider=medgemma` für die 447 Bildfragen fährt.

### PDF‑Extraktion
- Es gibt **13 PDFs** im Index‑Scan mit **0 Text** (bzw. 1× AES‑Verschlüsselung ohne `cryptography`).  
- Ein OCR/Bild‑Extraktions‑Fallback ist im Repo **noch nicht implementiert**.


