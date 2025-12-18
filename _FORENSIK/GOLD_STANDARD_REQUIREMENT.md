# ⚠️ KRITISCHE ANFORDERUNG: NUR GOLD-STANDARD Q&As

**Datum:** 2025-11-30
**Status:** VERBINDLICH
**Priorität:** HÖCHSTE

---

## KLARE ANFORDERUNG

**NUR Q&As aus den Gold-Standard PDFs sind wertvoll.**

Alle anderen Datenquellen sind für die Prüfungsvorbereitung **NICHT relevant**.

---

## GOLD-STANDARD QUELLE

**Verzeichnis:** `Input Bucket/_GOLD_STANDARD/`

**Inhalt:**
- 93 PDFs (255 MB)
- Prüfungsprotokolle: KP Münster 2020-2025
- Themenmaterialien: Fallkonzepte, Themen-Kataloge
- Spezialgebiete: Rechtsmedizin, Strahlenschutz

**Warum nur diese Quelle?**
- Echte Prüfungsfragen aus KP Münster
- Relevante Themen für Kenntnisprüfung März 2025
- Validierter Goldstandard

---

## ❌ NICHT-RELEVANTE DATENQUELLEN

Die folgenden Datenquellen sind **NICHT** für die Prüfungsvorbereitung zu verwenden:

### 1. Klinische Fälle (MASTER_LEARNING_CONTENT.json)
- ❌ 4.058 Clinical Cases
- ❌ 3.547 Chunks
- ❌ Quelle: Unbekannte klinische Fallsammlungen

### 2. Generierte Q&As aus Cases
- ❌ `generated_qa_llm.json` (3.170 pairs)
- ❌ `qa_enhanced_quality.json` (3.170 pairs)
- ❌ `qa_final_processed.json` (3.126 pairs)
- ❌ `generated_qa_from_cases_backup` (16.725 pairs)

**Grund:** Diese stammen NICHT aus den Gold-Standard PDFs!

### 3. Extrahierte Fragen
- ❌ `extrahierte_fragen.json` (44.615 items)

---

## ✅ AKTUELLER STATUS (2025-11-30)

**Verification Report zeigt:**
- 3.170 Q&A pairs in `generated_qa_llm.json`
- **NUR 11 aus Gold-Standard** (0.3%)
- **3.159 aus Non-Gold-Standard** (99.7%)

**Fazit:** Aktuelle Daten sind **NICHT verwendbar** für Prüfungsvorbereitung.

---

## 📋 ERFORDERLICHE MASSNAHME

**Von Null starten mit Gold-Standard PDFs:**

```bash
# Schritt 1: Alle nicht-relevanten Daten archivieren
mkdir -p _ARCHIVE_NON_GOLD_STANDARD/
mv generated_qa_llm.json _ARCHIVE_NON_GOLD_STANDARD/
mv qa_enhanced_quality.json _ARCHIVE_NON_GOLD_STANDARD/
mv qa_final_processed.json _ARCHIVE_NON_GOLD_STANDARD/

# Schritt 2: Neue Pipeline nur mit Gold-Standard PDFs starten
python complete_pipeline_orchestrator.py \
  --recursive \
  --input-dir "Input Bucket/_GOLD_STANDARD" \
  --output-dir "Output Bucket/gold_standard_qa" \
  --source-tag "GOLD_STANDARD"
```

**Erwartete Output:**
- Neue Q&A pairs **NUR** aus 93 Gold-Standard PDFs
- `source` Feld zeigt korrekten PDF-Namen
- 100% Gold-Standard Verifikation

---

## 🎯 QUALITÄTSKRITERIEN

**Eine Q&A ist NUR dann gültig, wenn:**

1. ✅ Quelle ist eine der 93 PDFs aus `_GOLD_STANDARD/`
2. ✅ `source` Feld enthält PDF-Namen (z.B. "KP_Münster_2023.pdf")
3. ✅ Thema ist relevant für Kenntnisprüfung
4. ✅ Format entspricht deutschem Prüfungsstandard

---

## 📊 ERWARTETE DATENMENGE

**Realistische Schätzung:**
- 93 PDFs × ~10-30 Fragen/PDF = **930-2.790 Fragen**
- Nach Qualitätsfilterung: **200-500 Top-Fragen**

**Wichtig:** Qualität > Quantität

---

## ⚠️ WARNUNG FÜR ZUKÜNFTIGE VERARBEITUNG

**JEDER Pipeline-Run muss validieren:**

```python
def validate_source_is_gold_standard(qa_pair: dict) -> bool:
    """
    Prüft ob Q&A aus Gold-Standard stammt
    """
    source = qa_pair.get('source', '')

    # Muss PDF-Namen enthalten
    if not source.endswith('.pdf'):
        return False

    # Muss in _GOLD_STANDARD/ Verzeichnis sein
    gold_standard_path = Path("Input Bucket/_GOLD_STANDARD")
    source_path = gold_standard_path / source

    if not source_path.exists():
        return False

    return True
```

**Bei Validierung-Failure:**
- ❌ Pipeline STOPPEN
- ⚠️ Warnung ausgeben
- 📋 Bericht erstellen

---

## 💾 BACKUP-STRATEGIE

**Vor jedem neuen Run:**
1. Backup aller Gold-Standard PDFs
2. Backup aller generierten Q&As (mit Timestamp)
3. Validierung dass Backup korrekt

**Nach jedem Run:**
1. Verifikation: 100% aus Gold-Standard
2. Quality-Check: Prüfungsrelevanz
3. Report: Statistiken und Qualitätsmetriken

---

## 📝 ZUSAMMENFASSUNG

**Die einzige Wahrheit:**
- ✅ Gold-Standard PDFs = Wertvoll
- ❌ Alle anderen Quellen = Nicht relevant

**Konsequenz:**
- Neu starten von Null ist **akzeptabel**
- Nur Gold-Standard Daten verwenden
- Qualität > Quantität

---

**Erstellt:** 2025-11-30
**Autor:** Claude Code
**Grund:** Klare Anforderung vom User dokumentieren
