# 🔄 NEUSTART-PLAN: Gold-Standard Pipeline

**Datum:** 2025-11-30
**Status:** Bereit zur Ausführung
**Priorität:** HÖCHSTE

---

## KLARE ANFORDERUNG

**NUR Q&As aus den 93 Gold-Standard PDFs sind wertvoll.**

Alle bisherigen 3.170 Q&As aus klinischen Fällen werden **NICHT** verwendet.

---

## 1. VORBEREITUNG

### Archivierung alter Daten

```bash
# Sicherheitskopie aller nicht-verwendbaren Daten
mkdir -p _ARCHIVE_NON_GOLD_STANDARD_20251130/
mv generated_qa_llm.json _ARCHIVE_NON_GOLD_STANDARD_20251130/
mv qa_enhanced_quality.json _ARCHIVE_NON_GOLD_STANDARD_20251130/ 2>/dev/null || true
mv qa_final_processed.json _ARCHIVE_NON_GOLD_STANDARD_20251130/ 2>/dev/null || true
mv kenntnisprufung_*.json _ARCHIVE_NON_GOLD_STANDARD_20251130/ 2>/dev/null || true

echo "✅ Alte Daten archiviert"
```

### Verzeichnis-Validierung

```bash
# Prüfe dass Gold-Standard Verzeichnis existiert
GOLD_DIR="Input Bucket/_GOLD_STANDARD"
if [ ! -d "$GOLD_DIR" ]; then
    echo "❌ FEHLER: $GOLD_DIR nicht gefunden!"
    exit 1
fi

# Zähle PDFs
PDF_COUNT=$(find "$GOLD_DIR" -name "*.pdf" | wc -l)
echo "✅ Gefunden: $PDF_COUNT PDFs in Gold-Standard"

# Erwarte 93 PDFs
if [ "$PDF_COUNT" -ne 93 ]; then
    echo "⚠️ WARNUNG: Erwartet 93 PDFs, gefunden: $PDF_COUNT"
fi
```

---

## 2. PIPELINE-AUSFÜHRUNG

### Phase 0: PDF → Clinical Cases (2-4 Stunden)

```bash
python complete_pipeline_orchestrator.py \
  --recursive \
  --input-dir "Input Bucket/_GOLD_STANDARD" \
  --output-dir "Output Bucket/gold_standard_cases" \
  --mode extract_only \
  --source-tag "GOLD_STANDARD"
```

**Erwartete Outputs:**
- `Output Bucket/gold_standard_cases/intermediate/` - Extrahierte Cases
- `Output Bucket/gold_standard_cases/MASTER_GOLD_CASES.json` - Alle Cases

**Validation:**
```bash
python -c "
import json
with open('Output Bucket/gold_standard_cases/MASTER_GOLD_CASES.json') as f:
    data = json.load(f)
    print(f'✅ Extrahiert: {len(data)} Clinical Cases')

    # Prüfe Quellen
    sources = set(case.get('source', '') for case in data)
    non_pdf = [s for s in sources if not s.endswith('.pdf')]

    if non_pdf:
        print(f'❌ FEHLER: Nicht-PDF Quellen gefunden: {non_pdf}')
    else:
        print(f'✅ Alle {len(sources)} Quellen sind PDFs')
"
```

---

### Phase 1: Cases → Q&A Generierung (1-2 Tage)

```bash
python complete_pipeline_orchestrator.py \
  --input-file "Output Bucket/gold_standard_cases/MASTER_GOLD_CASES.json" \
  --output-file "generated_qa_gold_standard.json" \
  --mode generate_qa \
  --provider aws_bedrock \
  --model claude-sonnet-4-5 \
  --budget 150 \
  --source-validation strict
```

**Parameter Erklärung:**
- `--source-validation strict` → Nur PDFs aus `_GOLD_STANDARD/` erlaubt
- `--budget 150` → Max $150 für AWS Bedrock
- `--model claude-sonnet-4-5` → Beste Qualität

**Erwartete Outputs:**
- `generated_qa_gold_standard.json` - 930-2.790 Q&A pairs
- `qa_generation_report.json` - Statistiken
- `qa_generation_errors.log` - Fehlerprotokoll

**Validation:**
```bash
python scripts/verify_gold_standard_sources.py \
  --input generated_qa_gold_standard.json \
  --gold-dir "Input Bucket/_GOLD_STANDARD" \
  --output verification_report_gold.json
```

**Erwartetes Ergebnis:**
```json
{
  "total": 1500,
  "gold_standard_count": 1500,
  "gold_standard_percentage": 100.0,
  "non_gold_count": 0,
  "verification_passed": true
}
```

**Bei Failure:**
```bash
# Wenn nicht 100% Gold-Standard
if [ $(jq '.gold_standard_percentage' verification_report_gold.json) != "100.0" ]; then
    echo "❌ PIPELINE GESTOPPT: Nicht alle Q&As aus Gold-Standard!"
    echo "Siehe: verification_report_gold.json"
    exit 1
fi
```

---

### Phase 2: Konvertierung → 5-Punkte-Schema (10 min)

```bash
python scripts/convert_to_exam_format.py \
  --input generated_qa_gold_standard.json \
  --output kenntnisprufung_gold_base.json \
  --enrichment enrichment_needed_gold.json
```

**Validation:**
```bash
python -c "
import json
with open('kenntnisprufung_gold_base.json') as f:
    data = json.load(f)

    # Prüfe 5-Punkte-Schema
    complete = [q for q in data['questions'] if all(
        q['antwort'].get(key) for key in [
            '1_definition_klassifikation',
            '2_aetiologie_pathophysiologie',
            '3_diagnostik',
            '4_therapie',
            '5_rechtlich'
        ]
    )]

    pct = len(complete) / len(data['questions']) * 100
    print(f'✅ {len(complete)}/{len(data[\"questions\"])} ({pct:.1f}%) mit vollständigem 5-Punkte-Schema')
"
```

---

### Phase 3: Perplexity Enrichment (2-3 Stunden)

```bash
python scripts/enrich_with_perplexity.py \
  --enrichment enrichment_needed_gold.json \
  --input kenntnisprufung_gold_base.json \
  --output kenntnisprufung_gold_enriched.json \
  --budget 5.0 \
  --cache perplexity_cache_gold.json \
  --prioritize tier_1,tier_2
```

**Validation:**
```bash
python -c "
import json
with open('kenntnisprufung_gold_enriched.json') as f:
    data = json.load(f)

    # Prüfe Dosierungen
    with_doses = [q for q in data['questions'] if q.get('dosierungen')]
    pct_doses = len(with_doses) / len(data['questions']) * 100

    # Prüfe Klassifikationen
    with_class = [q for q in data['questions'] if q.get('klassifikationen')]
    pct_class = len(with_class) / len(data['questions']) * 100

    print(f'✅ Dosierungen: {len(with_doses)}/{len(data[\"questions\"])} ({pct_doses:.1f}%)')
    print(f'✅ Klassifikationen: {len(with_class)}/{len(data[\"questions\"])} ({pct_class:.1f}%)')

    if pct_doses < 80:
        print(f'⚠️ WARNUNG: Nur {pct_doses:.1f}% mit Dosierungen (Ziel: >80%)')
"
```

---

### Phase 4: RAG Integration (30 min)

```bash
python scripts/integrate_guidelines.py \
  --input kenntnisprufung_gold_enriched.json \
  --output kenntnisprufung_gold_with_guidelines.json \
  --rag-config core/rag_config.json
```

**Validation:**
```bash
python -c "
import json
with open('kenntnisprufung_gold_with_guidelines.json') as f:
    data = json.load(f)

    # Prüfe AWMF Leitlinien
    with_awmf = [q for q in data['questions'] if q.get('quelle') and 'AWMF' in q['quelle']]
    pct = len(with_awmf) / len(data['questions']) * 100

    print(f'✅ AWMF Leitlinien: {len(with_awmf)}/{len(data[\"questions\"])} ({pct:.1f}%)')

    if pct < 100:
        print(f'⚠️ WARNUNG: Nicht alle Fragen haben AWMF Referenz')
"
```

---

### Phase 5: Goldstandard Validierung (1 Stunde)

```bash
python scripts/goldstandard_validator.py \
  --input kenntnisprufung_gold_with_guidelines.json \
  --goldstandard "Input Bucket/_GOLD_STANDARD/" \
  --output kenntnisprufung_GOLD_FINAL.json \
  --report validation_report_gold_final.md \
  --target-count 300 \
  --min-score 0.70
```

**Validation:**
```bash
cat validation_report_gold_final.md

python -c "
import json
with open('kenntnisprufung_GOLD_FINAL.json') as f:
    data = json.load(f)
    print(f'✅ FINAL: {len(data[\"questions\"])} Top-Qualität Fragen')

    # Verteilung prüfen
    by_specialty = {}
    for q in data['questions']:
        spec = q.get('specialty', 'Unknown')
        by_specialty[spec] = by_specialty.get(spec, 0) + 1

    print('\nVerteilung nach Fachgebiet:')
    for spec, count in sorted(by_specialty.items(), key=lambda x: -x[1]):
        pct = count / len(data['questions']) * 100
        print(f'  {spec}: {count} ({pct:.1f}%)')
"
```

---

## 3. QUALITÄTSKRITERIEN

### Erfolgskriterien

- ✅ **100% Gold-Standard:** Alle Q&As aus 93 PDFs
- ✅ **200-500 Top-Fragen:** Nach Qualitätsscore
- ✅ **80%+ mit Dosierungen:** Aus Perplexity
- ✅ **100% mit AWMF:** Leitlinien-Referenzen
- ✅ **Vollständiges 5-Punkte-Schema:** Alle Fragen

### Quality Score ≥ 0.70

```python
def calculate_quality_score(qa: dict) -> float:
    score = 0.0

    # 5-Punkte-Vollständigkeit (40%)
    if all(qa['antwort'].get(key) for key in [
        '1_definition_klassifikation',
        '2_aetiologie_pathophysiologie',
        '3_diagnostik',
        '4_therapie',
        '5_rechtlich'
    ]):
        score += 0.40

    # Dosierungen (15%)
    if qa.get('dosierungen') and len(qa['dosierungen']) > 0:
        score += 0.15

    # Klassifikationen mit Namen (15%)
    if qa.get('klassifikationen') and any('nach' in k.lower() for k in qa['klassifikationen']):
        score += 0.15

    # AWMF Leitlinie (15%)
    if qa.get('quelle') and 'AWMF' in qa['quelle']:
        score += 0.15

    # Goldstandard-Ähnlichkeit (15%)
    score += qa.get('goldstandard_similarity', 0) * 0.15

    return score
```

---

## 4. ZEITPLAN & KOSTEN

| Phase | Dauer | Kosten | Beschreibung |
|-------|-------|--------|--------------|
| 0. PDF → Cases | 2-4 Std | $0 | PDF-Extraktion (lokal) |
| 1. Cases → Q&A | 1-2 Tage | $80-150 | AWS Bedrock Generierung |
| 2. Konvertierung | 10 Min | $0 | 5-Punkte-Schema |
| 3. Perplexity | 2-3 Std | $5 | Dosierungen & Klassifikationen |
| 4. RAG | 30 Min | $0 | AWMF Leitlinien (lokal) |
| 5. Validierung | 1 Std | $0 | Goldstandard-Vergleich |
| **GESAMT** | **2-4 Tage** | **~$85-155** | **200-500 Top-Fragen** |

---

## 5. AUSFÜHRUNG

### Single Command (Empfohlen)

```bash
# Komplette Pipeline in einem Durchlauf
./run_gold_standard_pipeline.sh
```

**Inhalt von `run_gold_standard_pipeline.sh`:**
```bash
#!/bin/bash
set -e  # Stop on error

echo "🔄 NEUSTART: Gold-Standard Pipeline"
echo "Datum: $(date)"

# Phase 0: Archivierung
echo "\n📦 Phase 0: Archivierung alter Daten..."
mkdir -p _ARCHIVE_NON_GOLD_STANDARD_20251130/
mv generated_qa_llm.json _ARCHIVE_NON_GOLD_STANDARD_20251130/ 2>/dev/null || true

# Phase 1: PDF → Cases
echo "\n📄 Phase 1: PDF-Extraktion..."
python complete_pipeline_orchestrator.py \
  --recursive \
  --input-dir "Input Bucket/_GOLD_STANDARD" \
  --output-dir "Output Bucket/gold_standard_cases" \
  --mode extract_only \
  --source-tag "GOLD_STANDARD"

# Phase 2: Cases → Q&A
echo "\n🤖 Phase 2: Q&A Generierung..."
python complete_pipeline_orchestrator.py \
  --input-file "Output Bucket/gold_standard_cases/MASTER_GOLD_CASES.json" \
  --output-file "generated_qa_gold_standard.json" \
  --mode generate_qa \
  --provider aws_bedrock \
  --model claude-sonnet-4-5 \
  --budget 150 \
  --source-validation strict

# Validation
echo "\n✅ Validierung Gold-Standard Sources..."
python scripts/verify_gold_standard_sources.py \
  --input generated_qa_gold_standard.json \
  --gold-dir "Input Bucket/_GOLD_STANDARD" \
  --output verification_report_gold.json

# Prüfe 100%
GOLD_PCT=$(jq '.gold_standard_percentage' verification_report_gold.json)
if [ "$GOLD_PCT" != "100.0" ]; then
    echo "❌ FEHLER: Nur $GOLD_PCT% aus Gold-Standard!"
    exit 1
fi

# Phase 3: Konvertierung
echo "\n📝 Phase 3: 5-Punkte-Schema..."
python scripts/convert_to_exam_format.py \
  --input generated_qa_gold_standard.json \
  --output kenntnisprufung_gold_base.json \
  --enrichment enrichment_needed_gold.json

# Phase 4: Perplexity
echo "\n🔍 Phase 4: Perplexity Enrichment..."
python scripts/enrich_with_perplexity.py \
  --enrichment enrichment_needed_gold.json \
  --input kenntnisprufung_gold_base.json \
  --output kenntnisprufung_gold_enriched.json \
  --budget 5.0 \
  --cache perplexity_cache_gold.json

# Phase 5: RAG
echo "\n📚 Phase 5: RAG Integration..."
python scripts/integrate_guidelines.py \
  --input kenntnisprufung_gold_enriched.json \
  --output kenntnisprufung_gold_with_guidelines.json

# Phase 6: Validierung
echo "\n✅ Phase 6: Goldstandard Validierung..."
python scripts/goldstandard_validator.py \
  --input kenntnisprufung_gold_with_guidelines.json \
  --goldstandard "Input Bucket/_GOLD_STANDARD/" \
  --output kenntnisprufung_GOLD_FINAL.json \
  --report validation_report_gold_final.md \
  --target-count 300 \
  --min-score 0.70

echo "\n🎉 ABGESCHLOSSEN!"
echo "Output: kenntnisprufung_GOLD_FINAL.json"
cat validation_report_gold_final.md
```

---

## 6. BACKUP-STRATEGIE

### Vor Start

```bash
# Backup aller Gold-Standard PDFs
tar -czf BACKUP_GOLD_STANDARD_PDFS_$(date +%Y%m%d).tar.gz "Input Bucket/_GOLD_STANDARD/"

# Backup Pipeline-Code
tar -czf BACKUP_PIPELINE_CODE_$(date +%Y%m%d).tar.gz \
  scripts/ \
  core/ \
  providers/ \
  complete_pipeline_orchestrator.py
```

### Nach jeder Phase

```bash
# Automatisches Backup nach jedem Schritt
cp generated_qa_gold_standard.json \
   generated_qa_gold_standard_backup_$(date +%Y%m%d_%H%M%S).json
```

---

## 7. FEHLERBEHANDLUNG

### Wenn Pipeline fehlschlägt

```bash
# Check Logs
tail -n 100 pipeline_errors.log

# Check letzter State
cat qa_generation_report.json

# Neustart ab letztem Checkpoint
python complete_pipeline_orchestrator.py \
  --resume-from qa_generation_checkpoint.json
```

### Wenn Validierung fehlschlägt (<100% Gold-Standard)

```bash
# Analysiere Non-Gold Sources
jq '.details.source_analysis.non_gold_standard_samples' verification_report_gold.json

# Identifiziere Problem-Cases
python scripts/analyze_non_gold_sources.py \
  --input generated_qa_gold_standard.json \
  --output problem_sources.json

# STOPPE Pipeline - nicht fortfahren!
echo "❌ Pipeline gestoppt - repariere Source-Tracking"
```

---

## ZUSAMMENFASSUNG

**Klare Anforderung:**
- ✅ NUR Gold-Standard PDFs verwenden
- ❌ Keine klinischen Fälle aus anderen Quellen
- ✅ 100% Verifikation vor jedem Schritt

**Ergebnis:**
- 200-500 Top-Qualität Fragen
- 100% aus 93 Gold-Standard PDFs
- Validiert gegen KP Münster Protokolle

**Kosten:**
- ~$85-155 (AWS Bedrock + Perplexity)
- 2-4 Tage Rechenzeit

**Qualität > Quantität**

---

**Erstellt:** 2025-11-30
**Status:** Bereit zur Ausführung
**User-Freigabe:** Erforderlich vor Start
