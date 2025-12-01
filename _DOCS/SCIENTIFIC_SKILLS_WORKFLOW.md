# Scientific Skills Workflow Integration

## Übersicht

Die Scientific Skills sind in die MedExamAI-Pipeline integriert und werden automatisch für relevante Fragen aktiviert.

## Workflow-Diagramm

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MedExamAI Answer Generation Pipeline             │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. FRAGE LADEN                                                     │
│     - Aus frage_bloecke.json (2.326 Blöcke)                        │
│     - Theme Detection (33 Themen)                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. RAG-KONTEXT ABRUFEN                                             │
│     - Embedding-basierte Suche                                      │
│     - Top-K relevante Chunks aus Gold-Standard                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. LEITLINIEN-MATCHING                                             │
│     - AWMF Registry Number                                          │
│     - Evidenzgrad (A/B/C)                                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. SCIENTIFIC SKILLS ENRICHMENT (NEU)                              │
│     ┌─────────────────┬────────────────┬───────────────────┐        │
│     │   biopython     │  bioservices   │  datacommons      │        │
│     │   (PubMed)      │  (ChEMBL)      │  (Statistiken)    │        │
│     └────────┬────────┴───────┬────────┴─────────┬─────────┘        │
│              │                │                  │                  │
│              ▼                ▼                  ▼                  │
│     ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐         │
│     │ Studien     │   │ Medikamente │   │ Prävalenz/      │         │
│     │ Guidelines  │   │ Dosierungen │   │ Inzidenz        │         │
│     │ Meta-Anal.  │   │ Interaktion │   │ Mortalität      │         │
│     └─────────────┘   └─────────────┘   └─────────────────┘         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. LLM-GENERIERUNG (mit Scientific Context)                        │
│     - 5-Punkte-Schema                                               │
│     - Budget-bewusstes Routing                                      │
│     - Scientific References im Prompt                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  6. MEDICAL VALIDATION                                              │
│     - Dosierung prüfen (gegen ChEMBL)                               │
│     - ICD-10 Codes                                                  │
│     - Laborwerte                                                    │
│     - Logik-Check                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  7. OUTPUT                                                          │
│     - JSON mit Antwort + Scientific References                      │
│     - Anki-Export (optional)                                        │
│     - Markdown-Export (optional)                                    │
└─────────────────────────────────────────────────────────────────────┘
```

## Aktivierungs-Trigger

### Pharmakologie-Enrichment (bioservices/ChEMBL)
Aktiviert wenn Frage enthält:
- `mg`, `dosis`, `dosierung`, `tablette`, `infusion`
- Medikamentenklassen: `antibiotik`, `betablocker`, `ace-hemmer`, etc.
- Konkrete Wirkstoffe: `metformin`, `aspirin`, `heparin`, etc.

**Output:**
```json
{
  "source": "bioservices/ChEMBL",
  "type": "pharmacology",
  "data": {
    "drug_name": "metformin",
    "chembl_id": "CHEMBL1431",
    "max_phase": 4,
    "molecular_weight": 129.17
  }
}
```

### Epidemiologie-Enrichment (datacommons)
Aktiviert wenn Frage enthält:
- `prävalenz`, `inzidenz`, `mortalität`, `letalität`
- `risiko`, `häufigkeit`, `verbreitung`, `statistik`

**Output:**
```json
{
  "source": "datacommons",
  "type": "epidemiology",
  "data": {
    "condition": "Diabetes",
    "country": "Germany",
    "value": 8200000,
    "unit": "persons"
  }
}
```

### PubMed-Enrichment (biopython)
Aktiviert für alle Fragen mit erkanntem Theme.
Sucht nach: `{theme} treatment guidelines`

**Output:**
```json
{
  "source": "biopython/Entrez",
  "type": "pubmed",
  "data": {
    "query": "Diabetes treatment guidelines",
    "articles": [
      {
        "pmid": "12345678",
        "title": "ESC Guidelines for Diabetes Management 2023",
        "journal": "European Heart Journal",
        "year": "2023"
      }
    ]
  }
}
```

## Verwendung

### CLI
```bash
# Mit Scientific Skills (Default)
python scripts/generate_answers.py --input _EXTRACTED_FRAGEN/frage_bloecke.json

# Ohne Scientific Skills
python scripts/generate_answers.py --no-scientific-skills

# Verbose für Enrichment-Details
python scripts/generate_answers.py --verbose
```

### Python API
```python
from scripts.generate_answers import AnswerGenerator

# Mit Scientific Skills
generator = AnswerGenerator(
    use_scientific_skills=True,
    validate=True
)

# Einzelne Frage anreichern
from core.scientific_enrichment import enrich_medical_question

result = enrich_medical_question(
    question="Welche Therapie bei Diabetes Typ 2?",
    themes=["Diabetes", "Endokrinologie"]
)

print(result["enrichments"])
```

## Abhängigkeiten installieren

```bash
# Core Scientific Skills
pip install biopython bioservices

# Optional für erweiterte Features
pip install datacommons-pandas datamol

# Alle auf einmal
pip install biopython bioservices datacommons-pandas
```

## Budget-Impact

Die Scientific Skills nutzen **kostenlose APIs**:
- PubMed/NCBI: Kostenlos (Entrez)
- ChEMBL: Kostenlos (EBI)
- Data Commons: Kostenlos (Google)

Keine API-Kosten, nur Rechenzeit für lokale Verarbeitung.

## Beispiel: Vollständiger Durchlauf

**Input-Frage:**
```
Patient mit Diabetes mellitus Typ 2 kommt mit HbA1c von 9.2%.
Aktuelle Therapie: Metformin 1000mg 2x täglich.
Welche Therapieanpassung empfehlen Sie?
```

**Scientific Enrichments:**
1. **ChEMBL** → Metformin: max_phase 4, MW 129.17
2. **DataCommons** → Diabetes DE: 8.2M Fälle
3. **PubMed** → "ESC Guidelines Diabetes 2023", PMID:xxxxx

**LLM-Kontext (zusätzlich zu RAG):**
```
--- Wissenschaftliche Referenzen ---
- ESC Guidelines for Diabetes Management 2023 (2023) PMID:xxxxx
- ChEMBL: metformin (Phase 4)
- Statistik: Diabetes: 8200000 Fälle
```

**Output:**
```json
{
  "frage": "Patient mit Diabetes mellitus Typ 2...",
  "antwort": {
    "definition_klassifikation": "...",
    "therapie": "Bei HbA1c >9% trotz Metformin-Monotherapie: Kombinationstherapie..."
  },
  "leitlinie": "AWMF 057-013 - NVL Diabetes Typ 2",
  "scientific_enrichments": [...],
  "pubmed_references": ["PMID:xxxxx"]
}
```
