# 🚨 CODEX: NEUSTART PIPELINE MIT GOLD-STANDARD INPUT

## SITUATION

Die Verifizierung (Aufgabe 0) ist **FEHLGESCHLAGEN**:

| Metrik | Ergebnis |
|--------|----------|
| Q&A aus Gold-Standard | **11 (0.3%)** |
| Q&A NICHT aus Gold-Standard | 3.159 (99.7%) |
| Erforderlicher Schwellenwert | ≥90% |
| **Status** | ❌ FAILED |

**Problem:** Die 3.170 "geretteten" Q&A pairs stammen NICHT aus echten Prüfungsprotokollen, sondern aus Leitlinien/Cases. Sie sind für die Kenntnisprüfung **WERTLOS**.

---

## DEINE AUFGABE

Starte die Q&A-Generierungs-Pipeline **NEU** mit dem korrekten Input-Verzeichnis.

### KRITISCHE PFADE

```
PROJEKT-ROOT: ~/Comet API/

KORREKTER INPUT (MUSS VERWENDET WERDEN):
  → Input_Bucket/_GOLD_STANDARD/
  → Enthält: 43 echte Prüfungsprotokolle (~1.450 Fragen)
  → Format: PDF/DOCX mit echten Prüfungsfragen

OUTPUT (NEU ERSTELLEN):
  → output_bucket/gold_standard_qa/

WERTLOSE DATEN (IGNORIEREN):
  → Comet API_backup_20251129/qa_enhanced_quality.json ← NICHT VERWENDEN!
  → generated_qa_llm.json ← NICHT VERWENDEN!
```

---

## SCHRITT 1: VERIFIZIERE INPUT

```bash
# Prüfe, dass Gold-Standard-Ordner existiert und Dateien enthält
ls -la "Input_Bucket/_GOLD_STANDARD/"

# Zähle Dateien
find "Input_Bucket/_GOLD_STANDARD/" -type f \( -name "*.pdf" -o -name "*.docx" \) | wc -l

# Erwartetes Ergebnis: ~43 Dateien
```

**STOP falls:**
- Ordner nicht existiert
- Weniger als 40 Dateien
- Keine PDF/DOCX Dateien

---

## SCHRITT 2: BACKUP VOR NEUSTART

```bash
# Sichere aktuellen Stand (falls etwas schief geht)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "backups/pre_gold_standard_run_${TIMESTAMP}"

# State-Files sichern
cp -v *_state.json "backups/pre_gold_standard_run_${TIMESTAMP}/" 2>/dev/null || echo "Keine State-Files"
cp -v output_bucket/*.json "backups/pre_gold_standard_run_${TIMESTAMP}/" 2>/dev/null || echo "Keine Output-JSONs"

echo "✅ Backup erstellt: backups/pre_gold_standard_run_${TIMESTAMP}/"
```

---

## SCHRITT 3: PIPELINE STARTEN

```bash
# Erstelle Output-Verzeichnis
mkdir -p "output_bucket/gold_standard_qa"

# Starte Pipeline mit KORREKTEM Input
python complete_pipeline_orchestrator.py \
  --recursive \
  --input-dir "Input_Bucket/_GOLD_STANDARD" \
  --output-dir "output_bucket/gold_standard_qa"
```

### FALLS `complete_pipeline_orchestrator.py` NICHT EXISTIERT:

Suche nach alternativen Entry-Points:
```bash
# Finde Pipeline-Scripts
find . -name "*.py" -exec grep -l "input.*dir\|pipeline\|orchestrat" {} \;

# Prüfe vorhandene Scripts
ls -la scripts/*.py
ls -la *.py
```

Mögliche Alternativen:
- `run_pipeline.py`
- `main.py`
- `scripts/extract_qa.py`
- `scripts/generate_qa.py`

---

## SCHRITT 4: VERIFIZIERUNG NACH PIPELINE-RUN

Nach Abschluss der Pipeline, führe erneut Verifizierung durch:

```bash
python scripts/verify_gold_standard_origin.py \
  --qa-file "output_bucket/gold_standard_qa/generated_qa_llm.json" \
  --gold-standard-dir "Input_Bucket/_GOLD_STANDARD" \
  --output "output_bucket/gold_standard_qa/verification_report.json"
```

### ERFOLGSKRITERIEN:

| Metrik | Erforderlich |
|--------|--------------|
| Gold-Standard-Anteil | **≥90%** |
| Q&A Paare | ≥1.000 (von ~1.450 Input-Fragen) |
| Source-Feld | Muss `_GOLD_STANDARD` referenzieren |

---

## SCHRITT 5: NACH ERFOLGREICHER VERIFIZIERUNG

Nur wenn Verifizierung ≥90% Gold-Standard zeigt:

### 5a. Konvertierung ins Prüfungsformat

```bash
python scripts/convert_to_exam_format.py \
  --input "output_bucket/gold_standard_qa/generated_qa_llm.json" \
  --output "output_bucket/gold_standard_qa/kenntnisprufung_formatted.json"
```

### 5b. RAG Enrichment (OBLIGATORISCH für ALLE Fragen)

```bash
python scripts/enrich_with_perplexity.py \
  --input "output_bucket/gold_standard_qa/kenntnisprufung_formatted.json" \
  --output "output_bucket/gold_standard_qa/kenntnisprufung_enriched.json"
```

### 5c. Medical Validation

```bash
python scripts/validate_medical_content.py \
  --input "output_bucket/gold_standard_qa/kenntnisprufung_enriched.json" \
  --output "output_bucket/gold_standard_qa/kenntnisprufung_validated.json"
```

---

## 🛡️ SICHERHEITSREGELN

1. **NIEMALS** Dateien aus `Comet API_backup_20251129/` als Quelle verwenden
2. **IMMER** Input aus `Input_Bucket/_GOLD_STANDARD/` nehmen
3. **BACKUP** vor jeder destruktiven Operation
4. **STOPP** bei Fehlern — nicht blind weitermachen
5. **VERIFIZIERUNG** nach jedem Pipeline-Run

---

## ❌ WAS SCHIEF GELAUFEN IST (KONTEXT)

1. Ursprüngliche Pipeline verwendete falschen Input (Leitlinien statt Prüfungsprotokolle)
2. 3.170 Q&A wurden generiert, aber aus FALSCHER Quelle
3. Rovo Dev hat Dateien "gerettet", aber nicht verifiziert woher sie stammen
4. Verifizierung zeigt: 99.7% sind NICHT aus echten Prüfungsprotokollen

**Lektion:** Input-Quelle ist KRITISCH. Nur `_GOLD_STANDARD/` enthält echte Prüfungsfragen.

---

## 📋 DEFINITION OF DONE

- [ ] Pipeline mit `--input-dir "Input_Bucket/_GOLD_STANDARD"` gestartet
- [ ] Pipeline erfolgreich abgeschlossen (keine Crashes)
- [ ] Verifizierung zeigt ≥90% Gold-Standard-Anteil
- [ ] ≥1.000 Q&A Paare generiert
- [ ] Alle Q&A haben Source-Feld mit `_GOLD_STANDARD`-Referenz
- [ ] RAG Enrichment für ALLE Fragen durchgeführt
- [ ] Finale Datei: `output_bucket/gold_standard_qa/kenntnisprufung_validated.json`

---

## BEI PROBLEMEN

1. **Pipeline-Script nicht gefunden:** Suche nach Entry-Point (siehe Schritt 3)
2. **AWS Bedrock Fehler:** Prüfe Credits und API-Keys
3. **Timeout/Crash:** Checkpoint-Files prüfen, von letztem Stand fortsetzen
4. **<90% Gold-Standard nach Run:** Input-Dir war falsch, prüfe Pfade

**Melde Status nach jedem Schritt.**
