# MedExamAI: Vollständiger Implementierungsplan
**Datum:** 2025-11-30
**Status:** Bereit für Implementierung
**Gesamtziel:** 200-300 prüfungskonforme Q&A-Fragen für Kenntnisprüfung März 2025

---

## Executive Summary

### ⚠️ KRITISCHE ÄNDERUNG (2025-11-30)

**Bestehende 3.170 Q&A pairs sind NICHT verwendbar:**
- ❌ Nur 11/3.170 (0.3%) aus Gold-Standard
- ❌ 99.7% aus Non-Gold-Standard Quellen (klinische Fälle)
- ❌ Quellen wie "Sinusbradykardie mit relevanten Pausen im EKG" (NICHT PDFs!)

**User-Anforderung (tausendmal kommuniziert):**
**NUR Q&As aus Gold-Standard PDFs sind wertvoll!**

### Neue Ausgangslage
- ✅ **Gold-Standard PDFs:** 93 PDFs in `Input Bucket/_GOLD_STANDARD/`
- ✅ **APIs integriert:** AWS Bedrock Claude Sonnet 4.5 für Generierung
- ✅ **RAG System:** ChromaDB mit AWMF Leitlinien
- ❌ **Bestehende Q&As:** NICHT verwendbar (falsche Quelle)
- ✅ **Pipeline:** Vorhanden (`complete_pipeline_orchestrator.py`)

### Problem
Kompletter **Neustart von Null** erforderlich mit Gold-Standard PDFs

### Lösung
**Vollständige Neugenerierung aus Gold-Standard PDFs:**

```
Phase 0: PDF-Verarbeitung → 93 PDFs extrahieren → Clinical Cases
Phase 1: Q&A-Generierung → AWS Bedrock → 930-2.790 Fragen
Phase 2: Perplexity → Dosierungen, Klassifikationen
Phase 3: RAG → AWMF Leitlinien-Referenzen
Phase 4: Validierung → Top 200-500 auswählen
```

**Zeitaufwand:** 2-4 Tage | **Kosten:** ~$80-150

---

## Phase 1: Basis-Konvertierung

### Input
- `Comet API_backup_20251129/qa_enhanced_quality.json`
- 3,170 Q&A pairs
- Aktuelles Format: `{question, answer, question_type, specialty, difficulty, ...}`

### Tool
**Existiert bereits:** `scripts/convert_to_exam_format.py` (535 Zeilen, produktionsreif)

### Ausführung
```bash
cd /Users/user/Documents/Pruefungsvorbereitung/Comet\ API

python scripts/convert_to_exam_format.py \
  --input "Comet API_backup_20251129/qa_enhanced_quality.json" \
  --output kenntnisprufung_base.json \
  --enrichment enrichment_needed.json
```

### Output
1. **`kenntnisprufung_base.json`** - Alle 3,170 im ExamQuestion Format:
   ```json
   {
     "id": "KP-001",
     "frage": "...",
     "patientenvorstellung": "...",
     "antwort": {
       "1_definition_klassifikation": "...",
       "2_aetiologie_pathophysiologie": "...",
       "3_diagnostik": "Zunächst Anamnese und KU, dann...",
       "4_therapie": "First-Line: ... [DOSIERUNG FEHLT]",
       "5_rechtlich": "§630 BGB: ..."
     },
     "thema": "Kardiologie",
     "kategorie": "Innere Medizin"
   }
   ```

2. **`enrichment_needed.json`** - Liste mit Flags:
   ```json
   [
     {
       "id": "KP-001",
       "needs_dose_enrichment": true,
       "medication": "Amoxicillin",
       "indication": "Pneumonie",
       "needs_classification_verification": true,
       "condition": "Herzinsuffizienz",
       "needs_legal_enrichment": false
     }
   ]
   ```

### Zeitaufwand
**~10 Minuten**

### Sicherheit
- Automatisches Backup VOR Konvertierung
- Validierung: Alle 3,170 müssen vorhanden sein
- Log: `pipeline_validation.log`

---

## Phase 2: Perplexity Enrichment

### Input
- `kenntnisprufung_base.json` (3,170 Fragen)
- `enrichment_needed.json` (Flags für Enrichment)

### Tool
**Zu modifizieren:** `scripts/enrich_with_perplexity.py`

**Neue Funktion hinzufügen:**
```python
def enrich_from_flags(enrichment_file: str, qa_file: str, budget: float = 5.0):
    """
    Flag-basiertes Enrichment mit Perplexity API

    Für jedes Entry mit Flags:
    - needs_dose_enrichment → Query: "Exakte Dosierung {medication} bei {indication}"
    - needs_classification_verification → Query: "{condition} Klassifikation mit Autorennamen"
    - needs_legal_enrichment → Query: "§630 BGB Aufklärungspflicht {context}"

    Budget Management:
    - Max $5 pro Session
    - Priorisierung: Tier-1 zuerst, dann Tier-2
    - Cache für identische Queries
    - Rate Limit: 20 req/min
    """
```

### Ausführung
```bash
python scripts/enrich_with_perplexity.py \
  --enrichment enrichment_needed.json \
  --input kenntnisprufung_base.json \
  --output kenntnisprufung_enriched.json \
  --budget 5.0 \
  --cache perplexity_cache.json
```

### Output
**`kenntnisprufung_enriched.json`** - 3,170 Fragen mit:
- Exakten Dosierungen (z.B. "Amoxicillin 3x1g p.o. für 5-7 Tage")
- Klassifikationen mit Namen (z.B. "NYHA-Klassifikation", "CHA2DS2-VASc")
- Rechtlichen Aspekten aus §630 BGB

### Zeitaufwand
**2-3 Stunden** (abhängig von API-Geschwindigkeit)

### Kosten
**~$5** (Perplexity API Budget)

### Sicherheit
- Backup VOR Enrichment
- Budget-Überwachung (Abort bei >$5)
- Cache-System (spart Kosten bei identischen Queries)
- Checkpoint alle 100 Fragen

---

## Phase 3: RAG Integration

### Input
- `kenntnisprufung_enriched.json` (3,170 Fragen)
- ChromaDB Index mit AWMF Leitlinien

### Tool
**Neu erstellen:** `scripts/integrate_guidelines.py` (~200 Zeilen)

**Funktionalität:**
```python
from core.guideline_recommender import GuidelineRecommender

def integrate_awmf_guidelines(qa_file: str, output_file: str):
    """
    RAG-basierte Leitlinien-Integration

    Für jede Frage:
    1. Thema extrahieren (aus 'thema' Feld)
    2. RAG: Relevante AWMF Leitlinie finden (top_k=3)
    3. Beste Leitlinie + Evidenzgrad hinzufügen
    4. Bei Therapie-Fragen: Empfehlungen aus Leitlinie

    ChromaDB:
    - Vector Store bereits indexiert
    - Embeddings: paraphrase-multilingual-mpnet-base-v2
    - Confidence Scoring für Relevanz
    """

    recommender = GuidelineRecommender()
    qa_data = json.load(open(qa_file))

    for qa in qa_data['questions']:
        topic = qa['thema']

        # RAG-Suche
        guidelines = recommender.recommend(
            topic=topic,
            specialty=qa.get('kategorie', ''),
            top_k=3
        )

        if guidelines:
            qa['quelle'] = guidelines[0]['title']
            qa['evidenzgrad'] = guidelines[0].get('evidence_level', 'N/A')
            qa['leitlinie_url'] = guidelines[0].get('url', '')

            # Therapie-Fragen: Empfehlungen
            if qa['question_type'] == 'therapy':
                qa['leitlinien_empfehlungen'] = recommender.get_recommendations(
                    guideline_id=guidelines[0]['id']
                )[:3]
```

### Ausführung
```bash
python scripts/integrate_guidelines.py \
  --input kenntnisprufung_enriched.json \
  --output kenntnisprufung_with_guidelines.json
```

### Output
**`kenntnisprufung_with_guidelines.json`** - 3,170 Fragen mit:
- AWMF Leitlinien-Referenz (z.B. "AWMF S3-Leitlinie Pneumonie 2021")
- Evidenzgrad (z.B. "Ia", "IIb")
- Leitlinien-URL
- Empfehlungen bei Therapie-Fragen

### Zeitaufwand
**~30 Minuten**

### Sicherheit
- Backup VOR Integration
- Validierung: Mindestens 80% sollten Leitlinie haben
- Fallback bei RAG-Fehler: "N/A" statt Crash

---

## Phase 4: Goldstandard-Validierung

### Input
- `kenntnisprufung_with_guidelines.json` (3,170 Fragen)
- `Input Bucket/_GOLD_STANDARD/` (93 PDFs)

### Tool
**Neu erstellen:** `scripts/goldstandard_validator.py` (~300 Zeilen)

**Funktionalität:**
```python
def validate_against_goldstandard(
    qa_file: str,
    goldstandard_dir: str,
    output_file: str,
    report_file: str,
    target_count: int = 250
):
    """
    3-Schritt Validierung:

    1. Goldstandard indexieren
       - 93 PDFs parsen (mit OCR für Scans)
       - Themen extrahieren
       - Fachgebiete klassifizieren

    2. Jede Frage validieren
       - Qualitätsscore berechnen (0.0-1.0)
       - Themen-Abdeckung prüfen
       - 5-Punkte-Vollständigkeit checken
       - Ähnlichkeit zu echten Prüfungsfragen

    3. Top-Fragen auswählen
       - Nach Score sortieren
       - Verteilung: Innere 30%, Chirurgie 20%, etc.
       - Balancierung: 40% Diagnostik, 30% Therapie, 30% Diff.diagnose
    """

    # Goldstandard indexieren
    goldstandard_index = index_goldstandard_pdfs(goldstandard_dir)

    # Validierung
    validation_results = []
    for qa in qa_data['questions']:
        score = calculate_quality_score(qa, goldstandard_index)
        validation_results.append({
            'id': qa['id'],
            'score': score,
            'coverage': check_topic_coverage(qa, goldstandard_index),
            'completeness': check_5_point_completeness(qa)
        })

    # Top-Auswahl
    top_questions = select_top_questions(
        validation_results,
        target_count=target_count,
        distribution={
            'Innere Medizin': 0.30,
            'Chirurgie': 0.20,
            'Neurologie': 0.10,
            'Gynäkologie': 0.10,
            'Sonstige': 0.30
        }
    )

    # Report
    create_validation_report(validation_results, report_file)
```

**Qualitätsscore-Berechnung:**
```python
def calculate_quality_score(qa: dict, goldstandard_index: dict) -> float:
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

    # Dosierungen vorhanden (15%)
    if qa.get('dosierungen') and len(qa['dosierungen']) > 0:
        score += 0.15

    # Klassifikationen mit Namen (15%)
    if qa.get('klassifikationen') and any('nach' in k.lower() for k in qa['klassifikationen']):
        score += 0.15

    # AWMF Leitlinie (15%)
    if qa.get('quelle') and 'AWMF' in qa['quelle']:
        score += 0.15

    # Goldstandard-Übereinstimmung (15%)
    score += qa.get('goldstandard_similarity', 0) * 0.15

    return score
```

### Ausführung
```bash
python scripts/goldstandard_validator.py \
  --input kenntnisprufung_with_guidelines.json \
  --goldstandard "Input Bucket/_GOLD_STANDARD/" \
  --output kenntnisprufung_FINAL.json \
  --report validation_report.md \
  --target-count 250
```

### Output
1. **`kenntnisprufung_FINAL.json`** - 200-300 Top-Qualität Fragen
   - Sortiert nach Qualitätsscore (≥0.70)
   - Balancierte Verteilung nach Fachgebiet
   - Vollständiges 5-Punkte-Schema

2. **`validation_report.md`** - Detaillierter Bericht:
   ```markdown
   # Validierungsbericht

   ## Übersicht
   - Geprüft: 3,170 Fragen
   - Ausgewählt: 250 Fragen (Top 7.9%)
   - Durchschnittsscore: 0.78

   ## Verteilung
   - Innere Medizin: 75 (30%)
   - Chirurgie: 50 (20%)
   - Neurologie: 25 (10%)
   - Gynäkologie: 25 (10%)
   - Sonstige: 75 (30%)

   ## Fehlende Themen
   - Strahlenschutz (nur 2 Fragen gefunden)
   - Rechtsmedizin (nur 3 Fragen gefunden)
   ```

### Zeitaufwand
**~1 Stunde** (PDF-Parsing ist intensiv)

### Sicherheit
- Backup VOR Validierung
- Validierung dass mindestens 200 Fragen übrig bleiben
- Report mit fehlenden Themen

---

## Phase 5: Sicherheitssystem

### Kritisch: Datenverlust-Prävention

**In ALLEN Scripts integrieren:**

```python
import shutil
from datetime import datetime
import json

def safe_backup(input_file: str) -> str:
    """Automatisches Backup VOR jeder Operation"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{input_file}_backup_{timestamp}.json"
    shutil.copy(input_file, backup_file)
    print(f"✅ Backup: {backup_file}")
    return backup_file

def safe_write(data: dict, output_file: str, original_file: str = None):
    """Sicheres Schreiben mit Validierung"""

    # 1. Prüfe Datenverlust
    if original_file:
        original_count = len(json.load(open(original_file))['questions'])
        new_count = len(data['questions'])
        loss_percent = ((original_count - new_count) / original_count) * 100

        if loss_percent > 10:
            print(f"⚠️ WARNUNG: {loss_percent:.1f}% Datenverlust!")
            response = input("Fortfahren? (yes/NO): ")
            if response.lower() != 'yes':
                print("❌ Abbruch")
                return False

    # 2. Validiere JSON
    try:
        json.dumps(data)
    except Exception as e:
        print(f"❌ JSON ungültig: {e}")
        return False

    # 3. Backup des Zielfiles
    if os.path.exists(output_file):
        safe_backup(output_file)

    # 4. Schreiben
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Geschrieben: {output_file} ({new_count} Einträge)")
    return True

def checkpoint_validation(step_name: str, input_count: int, output_count: int):
    """Logging jedes Verarbeitungsschritts"""
    loss = input_count - output_count
    loss_percent = (loss / input_count) * 100 if input_count > 0 else 0

    with open('pipeline_validation.log', 'a') as f:
        f.write(f"{datetime.now()} | {step_name} | {input_count} → {output_count} | -{loss_percent:.1f}%\n")

    if loss_percent > 30:
        print(f"⚠️ {step_name}: Hoher Datenverlust ({loss_percent:.1f}%)")
```

### GitHub Actions: Automatische Backups

**Datei:** `.github/workflows/daily-backup.yml`

```yaml
name: Daily Q&A Backup
on:
  schedule:
    - cron: '0 2 * * *'  # Täglich 2 Uhr
  workflow_dispatch:

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create backup
        run: |
          DATE=$(date +%Y%m%d)
          mkdir -p backups/qa_backup_$DATE/
          cp "Output Bucket"/*.json backups/qa_backup_$DATE/ || true
          cp kenntnisprufung*.json backups/qa_backup_$DATE/ || true

      - name: Commit backup
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add backups/
          git commit -m "chore: Daily Q&A backup $DATE" || echo "No changes"
          git push || echo "Nothing to push"
```

---

## Kompletter Ausführungsplan

### Vorbereitung
```bash
# Arbeitsverzeichnis
cd /Users/user/Documents/Pruefungsvorbereitung/Comet\ API

# Backup-Verzeichnis erstellen
mkdir -p BACKUP_30NOV
mkdir -p backups/$(date +%Y%m%d)

# Primäre Datenquelle sichern
cp "Comet API_backup_20251129/qa_enhanced_quality.json" BACKUP_30NOV/
```

### Schritt 1: Basis-Konvertierung (10 min)
```bash
python scripts/convert_to_exam_format.py \
  --input "Comet API_backup_20251129/qa_enhanced_quality.json" \
  --output kenntnisprufung_base.json \
  --enrichment enrichment_needed.json

# Validierung
python -c "import json; data=json.load(open('kenntnisprufung_base.json')); print(f'✅ {len(data[\"questions\"])} Fragen konvertiert')"
```

### Schritt 2: Perplexity Enrichment (2-3 Stunden)
```bash
python scripts/enrich_with_perplexity.py \
  --enrichment enrichment_needed.json \
  --input kenntnisprufung_base.json \
  --output kenntnisprufung_enriched.json \
  --budget 5.0 \
  --cache perplexity_cache.json

# Validierung
python -c "import json; data=json.load(open('kenntnisprufung_enriched.json')); enriched=sum(1 for q in data['questions'] if q.get('dosierungen')); print(f'✅ {enriched} Fragen enriched')"
```

### Schritt 3: RAG Integration (30 min)
```bash
python scripts/integrate_guidelines.py \
  --input kenntnisprufung_enriched.json \
  --output kenntnisprufung_with_guidelines.json

# Validierung
python -c "import json; data=json.load(open('kenntnisprufung_with_guidelines.json')); with_guidelines=sum(1 for q in data['questions'] if q.get('quelle')); print(f'✅ {with_guidelines} Fragen mit Leitlinien')"
```

### Schritt 4: Goldstandard-Validierung (1 Stunde)
```bash
python scripts/goldstandard_validator.py \
  --input kenntnisprufung_with_guidelines.json \
  --goldstandard "Input Bucket/_GOLD_STANDARD/" \
  --output kenntnisprufung_FINAL.json \
  --report validation_report.md \
  --target-count 250

# Report anzeigen
cat validation_report.md

# Final count
python -c "import json; data=json.load(open('kenntnisprufung_FINAL.json')); print(f'✅ FINAL: {len(data[\"questions\"])} Top-Qualität Fragen')"
```

### Schritt 5: Qualitätsprüfung
```bash
# Pipeline-Log prüfen
cat pipeline_validation.log

# Backups prüfen
ls -lh kenntnisprufung*_backup_*.json

# Final Backup
cp kenntnisprufung_FINAL.json "backups/$(date +%Y%m%d)/kenntnisprufung_FINAL_$(date +%H%M%S).json"
```

---

## Zeitplan & Ressourcen

### Gesamtzeit
- **Entwicklung:** 2-3 Stunden (neue Scripts erstellen)
- **Ausführung:** 4-5 Stunden (Pipeline laufen lassen)
- **GESAMT:** ~6-8 Stunden

### Kosten
- **Perplexity API:** ~$5
- **AWS Bedrock (Portkey):** Bereits vorhanden, keine neuen Kosten
- **GESAMT:** ~$5

### Kritische Dateien

**Zu erstellen:**
- `scripts/integrate_guidelines.py` (~200 Zeilen)
- `scripts/goldstandard_validator.py` (~300 Zeilen)
- `.github/workflows/daily-backup.yml` (~30 Zeilen)

**Zu modifizieren:**
- `scripts/enrich_with_perplexity.py` (Flag-basiertes Enrichment hinzufügen)
- `scripts/convert_to_exam_format.py` (safe_backup() integrieren)

**Input:**
- `Comet API_backup_20251129/qa_enhanced_quality.json` (3,170 QA)
- `Input Bucket/_GOLD_STANDARD/` (93 PDFs)

**Output:**
- `kenntnisprufung_FINAL.json` (200-300 Top-Fragen)
- `validation_report.md` (Qualitätsbericht)
- `pipeline_validation.log` (Checkpoint-Log)

---

## Definition of Done

### Technische Kriterien
- [ ] Alle 3,170 Q&A konvertiert ins 5-Punkte-Schema
- [ ] Mindestens 80% haben Dosierungen (aus Perplexity)
- [ ] 100% haben AWMF Leitlinien-Referenzen (aus RAG)
- [ ] Goldstandard-Validierung abgeschlossen
- [ ] 200-300 Top-Qualität Fragen ausgewählt (Score ≥0.70)
- [ ] Validation Report erstellt
- [ ] Alle Backups angelegt
- [ ] Pipeline-Log komplett
- [ ] GitHub Actions Workflow committed

### Qualitätskriterien
- [ ] Verteilung: Innere 30%, Chirurgie 20%, Neurologie 10%, Gynäkologie 10%, Sonstige 30%
- [ ] Balancierung: 40% Diagnostik, 30% Therapie, 30% Differentialdiagnose
- [ ] Alle Fragen haben vollständiges 5-Punkte-Schema
- [ ] Dosierungen mit exakten mg/kg Angaben
- [ ] Klassifikationen mit Namen (NYHA, Garden, CURB-65, etc.)
- [ ] §630 BGB in rechtlichen Aspekten
- [ ] AWMF Leitlinien mit Evidenzgrad

### Dokumentation
- [ ] Dieser Plan in Git committed
- [ ] Validation Report in Jira hochgeladen
- [ ] Pipeline-Log archiviert
- [ ] Forensik-Report (DATEN_FORENSIK_REPORT.md) erstellt

---

## Notfallplan

### Bei Datenverlust während Pipeline
1. STOP sofort
2. Prüfe letzte Backups: `ls -lt kenntnisprufung*_backup_*.json | head -5`
3. Restore from backup: `cp [backup_file] kenntnisprufung_[phase].json`
4. Pipeline ab letztem erfolgreichen Checkpoint neu starten
5. Incident in `pipeline_validation.log` dokumentieren

### Bei API-Fehlern (Perplexity/Portkey)
1. Cache prüfen: `perplexity_cache.json` enthält erfolgreich abgerufene Daten
2. Bei Budget-Überschreitung: Budget erhöhen oder später fortsetzen
3. Bei Rate-Limit: Warten (20 req/min Limit)
4. Fallback: Perplexity API Key wechseln (KEY_1 → KEY_2)

### Bei Qualitäts-Problemen
1. Validation Report analysieren
2. Fehlende Themen identifizieren
3. Manuelle Ergänzung notwendiger Fragen
4. Re-Validation durchführen

---

## Nächste Schritte nach Fertigstellung

### Export-Formate
1. **Anki-Karten:** Für Spaced Repetition
2. **PDF:** Für Druck
3. **JSON:** Für Lern-Apps
4. **Markdown:** Für menschliche Lesbarkeit

### Prüfungssimulation
1. Quiz-Modus mit Timer (20 min/Fall)
2. Randomisierte Fragen
3. Selbstbewertungs-System
4. Mock-Exams (80 Fragen)

### Kontinuierliche Verbesserung
1. Feedback-Loop für falsch beantwortete Fragen
2. Neue Leitlinien-Updates integrieren
3. Prüfungsprotokolle 2025 hinzufügen (wenn verfügbar)

---

**Erstellt:** 2025-11-30
**Version:** 1.0
**Autor:** Claude Code mit User Collaboration
**Plan-Datei:** `/Users/user/.claude/plans/dazzling-painting-nova.md`
**Forensik-Report:** `DATEN_FORENSIK_REPORT.md`
