# 🎯 CODEX MEGA-PROMPT: Verifizierung & Pipeline Completion

**Projekt:** MedExamAI  
**Priorität:** KRITISCH  
**Ziel:** Kenntnisprüfung März 2026

---

## 📂 DATEIPFADE (BEREITS BEKANNT!)

```
PROJEKT-ROOT: ~/Comet API/

Q&A DATEI (3.170 Paare):
  → Comet API_backup_20251129/qa_enhanced_quality.json (5.3 MB) ← VERWENDE DIESE!

GOLD STANDARD QUELLEN:
  → Input Bucket/_GOLD_STANDARD/ (43 Dateien, 1.450 echte Prüfungsfragen)

SCRIPTS VERZEICHNIS:
  → scripts/

OUTPUT:
  → output_bucket/
```

---

## ⚠️ KRITISCHE VORBEDINGUNG

**Bevor IRGENDETWAS anderes passiert, muss AUFGABE 0 abgeschlossen sein!**

Die 3.170 Q&A Paare MÜSSEN aus dem `_GOLD_STANDARD/` Ordner stammen.  
Wenn das NICHT der Fall ist → SOFORT STOPPEN und melden!

---

# 📋 AUFGABENÜBERSICHT

| Aufgabe | Beschreibung | Priorität | Abhängigkeit |
|---------|--------------|-----------|--------------|
| **0** | Verifizierung: Stammen Q&A aus Gold Standard? | 🔴 KRITISCH | Keine |
| **2** | Konvertierung ins Prüfungsformat (5-Punkte-Schema) | Hoch | Aufgabe 0 ✅ |
| **3** | RAG Enrichment (Perplexity+Portkey) | 🔴 **OBLIGATORISCH** | Aufgabe 2 ✅ |
| **4** | Gold Standard Validierung + Medical Validators | Hoch | Aufgabe 3 ✅ |
| **5** | Post-Mortem + Automatisierung | Mittel | Aufgabe 4 ✅ |

---

# 🔴 AUFGABE 0: VERIFIZIERUNG DER GOLD STANDARD HERKUNFT

## 0.1 Kontext

Die Pipeline hat 3.170 Q&A Paare generiert. Diese MÜSSEN aus echten Prüfungsprotokollen stammen:

```
Input_Bucket/_GOLD_STANDARD/  (43 Dateien)
├── Kenntnisprüfung Münster Protokolle 2023.docx
├── Kenntnisprüfung Münster Protokolle 2024.docx
├── Protokolle_KP_Muenster_2020-2025_SORTED.pdf
├── QE Rechtsmedizin.pdf
└── ... (weitere echte Prüfungsprotokolle)
```

**NICHT aus:**
- `Innere_Medizin/` (Lehrbücher, Leitlinien)
- `Sonstige/` (Hintergrundmaterial)
- Andere Tier-2 Quellen

## 0.2 Verifizierungs-Script

Erstelle `scripts/verify_gold_standard_origin.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Gold Standard Origin Verification
=============================================

Verifiziert, dass alle Q&A aus _GOLD_STANDARD/ stammen.

KRITISCH: Wenn Verifizierung fehlschlägt → Pipeline stoppen!
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict
from datetime import datetime
import re

# ============================================================================
# KONFIGURATION
# ============================================================================

# Pfade anpassen falls nötig
QA_FILE = "output_bucket/qa_enhanced_quality.json"  # Oder aktueller Pfad
BACKUP_QA_FILE = "~/Documents/Pruefungsvorbereitung/BACKUP_30NOV/qa_enhanced_quality.json"
GOLD_STANDARD_DIR = "Input_Bucket/_GOLD_STANDARD"
STATE_FILES = [
    "consolidator_state.json",
    "extractor_state.json", 
    "qa_extraction_progress.json"
]
LOG_DIR = "logs"

# Bekannte Gold Standard Dateinamen (zur Validierung)
EXPECTED_GOLD_STANDARD_PATTERNS = [
    r"[Kk]enntnispr[üu]fung",
    r"[Pp]rotokoll",
    r"[Mm][üu]nster",
    r"[Rr]echtsmedizin",
    r"_GOLD_STANDARD",
    r"[Ee]rfahrungsbericht",
    r"[Tt]hemen",
]


# ============================================================================
# VERIFIZIERUNGS-FUNKTIONEN
# ============================================================================

def load_qa_pairs(filepath: str) -> List[Dict]:
    """Lädt Q&A Paare aus JSON."""
    path = Path(filepath).expanduser()
    
    if not path.exists():
        print(f"⚠️  Datei nicht gefunden: {filepath}")
        return []
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle verschiedene Strukturen
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if 'qa_pairs' in data:
            return data['qa_pairs']
        elif 'questions' in data:
            return data['questions']
        else:
            return [data]
    
    return []


def analyze_sources(qa_pairs: List[Dict]) -> Dict:
    """Analysiert die Quellen aller Q&A Paare."""
    
    sources = defaultdict(int)
    missing_source = []
    gold_standard_count = 0
    non_gold_standard = []
    
    for i, qa in enumerate(qa_pairs):
        # Suche nach Source-Feld (verschiedene mögliche Namen)
        source = None
        for field in ['source', 'quelle', 'source_file', 'source_document', 
                      'source_case_title', 'file', 'filename', 'origin']:
            if field in qa and qa[field]:
                source = str(qa[field])
                break
        
        if not source:
            missing_source.append(i)
            continue
        
        sources[source] += 1
        
        # Prüfe ob aus Gold Standard
        is_gold = False
        for pattern in EXPECTED_GOLD_STANDARD_PATTERNS:
            if re.search(pattern, source, re.IGNORECASE):
                is_gold = True
                break
        
        if is_gold or '_GOLD_STANDARD' in source:
            gold_standard_count += 1
        else:
            non_gold_standard.append({
                'index': i,
                'source': source,
                'frage': qa.get('frage', qa.get('question', ''))[:100]
            })
    
    return {
        'total': len(qa_pairs),
        'sources': dict(sources),
        'unique_sources': len(sources),
        'missing_source_count': len(missing_source),
        'missing_source_indices': missing_source[:20],  # Erste 20
        'gold_standard_count': gold_standard_count,
        'non_gold_standard_count': len(non_gold_standard),
        'non_gold_standard_samples': non_gold_standard[:10]  # Erste 10
    }


def check_state_files() -> Dict:
    """Prüft State-Files auf Input-Quellen."""
    
    results = {}
    
    for state_file in STATE_FILES:
        path = Path(state_file)
        
        if not path.exists():
            # Suche in üblichen Verzeichnissen
            for search_dir in ['.', 'output_bucket', 'data', 'state']:
                alt_path = Path(search_dir) / state_file
                if alt_path.exists():
                    path = alt_path
                    break
        
        if not path.exists():
            results[state_file] = {'status': 'NOT_FOUND'}
            continue
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extrahiere relevante Infos
            input_sources = []
            
            # Suche nach Input-Pfaden
            for key in ['input_dir', 'input_path', 'source_dir', 'processed_files', 
                        'input_files', 'documents']:
                if key in data:
                    value = data[key]
                    if isinstance(value, str):
                        input_sources.append(value)
                    elif isinstance(value, list):
                        input_sources.extend([str(v) for v in value[:10]])
                    elif isinstance(value, dict):
                        input_sources.extend(list(value.keys())[:10])
            
            # Prüfe ob Gold Standard referenziert
            gold_standard_referenced = any(
                '_GOLD_STANDARD' in str(s) or 'GOLD_STANDARD' in str(s)
                for s in input_sources
            )
            
            results[state_file] = {
                'status': 'FOUND',
                'path': str(path),
                'input_sources': input_sources,
                'gold_standard_referenced': gold_standard_referenced
            }
            
        except Exception as e:
            results[state_file] = {
                'status': 'ERROR',
                'error': str(e)
            }
    
    return results


def check_logs_for_input_dir() -> List[str]:
    """Durchsucht Logs nach Input-Verzeichnis-Referenzen."""
    
    log_dir = Path(LOG_DIR)
    findings = []
    
    if not log_dir.exists():
        return ["Log-Verzeichnis nicht gefunden"]
    
    for log_file in log_dir.glob("*.log"):
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Suche nach Input-Dir Referenzen
            if '_GOLD_STANDARD' in content:
                findings.append(f"✅ {log_file.name}: _GOLD_STANDARD gefunden")
            
            if 'input-dir' in content or 'input_dir' in content:
                # Extrahiere die Zeile
                for line in content.split('\n'):
                    if 'input' in line.lower() and ('dir' in line.lower() or 'path' in line.lower()):
                        findings.append(f"📋 {log_file.name}: {line[:100]}")
                        break
                        
        except Exception as e:
            findings.append(f"⚠️ Fehler bei {log_file.name}: {e}")
    
    return findings if findings else ["Keine relevanten Log-Einträge gefunden"]


def sample_verification(qa_pairs: List[Dict], gold_standard_dir: str, sample_size: int = 5) -> List[Dict]:
    """
    Stichproben-Verifizierung: Sucht Fragen in den Gold Standard Dokumenten.
    
    HINWEIS: Dies ist eine vereinfachte Text-Suche.
    Für vollständige Verifizierung müssten die PDFs/DOCX geparst werden.
    """
    
    import random
    
    gold_dir = Path(gold_standard_dir)
    if not gold_dir.exists():
        return [{'error': f'Gold Standard Verzeichnis nicht gefunden: {gold_standard_dir}'}]
    
    # Wähle zufällige Samples
    samples = random.sample(qa_pairs, min(sample_size, len(qa_pairs)))
    
    results = []
    
    for qa in samples:
        frage = qa.get('frage', qa.get('question', ''))
        
        # Extrahiere Schlüsselwörter (erste 5 signifikante Wörter)
        words = [w for w in frage.split() if len(w) > 4][:5]
        
        result = {
            'frage': frage[:150],
            'keywords': words,
            'source_in_qa': qa.get('source', qa.get('quelle', 'NICHT ANGEGEBEN')),
            'verification': 'MANUAL_CHECK_REQUIRED'
        }
        
        results.append(result)
    
    return results


def generate_verification_report(qa_file: str = None) -> Dict:
    """Generiert vollständigen Verifizierungsbericht."""
    
    print("\n" + "="*70)
    print("🔍 GOLD STANDARD ORIGIN VERIFICATION")
    print("="*70)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'verification_passed': None,
        'critical_issues': [],
        'warnings': [],
        'details': {}
    }
    
    # 1. Lade Q&A Paare
    print("📥 Lade Q&A Paare...")
    
    qa_file = qa_file or QA_FILE
    qa_pairs = load_qa_pairs(qa_file)
    
    if not qa_pairs:
        qa_pairs = load_qa_pairs(BACKUP_QA_FILE)
        if qa_pairs:
            print(f"   → Aus Backup geladen: {BACKUP_QA_FILE}")
    
    if not qa_pairs:
        report['verification_passed'] = False
        report['critical_issues'].append("KEINE Q&A PAARE GEFUNDEN!")
        return report
    
    print(f"   → {len(qa_pairs)} Q&A Paare geladen")
    
    # 2. Analysiere Quellen
    print("\n📊 Analysiere Quellen...")
    source_analysis = analyze_sources(qa_pairs)
    report['details']['source_analysis'] = source_analysis
    
    print(f"   → Unique Sources: {source_analysis['unique_sources']}")
    print(f"   → Gold Standard: {source_analysis['gold_standard_count']}")
    print(f"   → Non-Gold Standard: {source_analysis['non_gold_standard_count']}")
    print(f"   → Missing Source: {source_analysis['missing_source_count']}")
    
    # 3. Prüfe State Files
    print("\n📋 Prüfe State Files...")
    state_check = check_state_files()
    report['details']['state_files'] = state_check
    
    for filename, result in state_check.items():
        status = result.get('status', 'UNKNOWN')
        gold_ref = result.get('gold_standard_referenced', False)
        print(f"   → {filename}: {status}", end='')
        if gold_ref:
            print(" ✅ Gold Standard referenziert")
        else:
            print()
    
    # 4. Prüfe Logs
    print("\n📝 Prüfe Logs...")
    log_findings = check_logs_for_input_dir()
    report['details']['log_findings'] = log_findings
    
    for finding in log_findings[:5]:
        print(f"   {finding}")
    
    # 5. Stichproben
    print("\n🎲 Stichproben-Verifizierung...")
    samples = sample_verification(qa_pairs, GOLD_STANDARD_DIR)
    report['details']['samples'] = samples
    
    for i, sample in enumerate(samples, 1):
        print(f"\n   Sample {i}:")
        print(f"   Frage: {sample['frage'][:80]}...")
        print(f"   Quelle: {sample['source_in_qa']}")
    
    # 6. BEWERTUNG
    print("\n" + "="*70)
    print("📊 BEWERTUNG")
    print("="*70)
    
    total = source_analysis['total']
    gold_count = source_analysis['gold_standard_count']
    non_gold_count = source_analysis['non_gold_standard_count']
    missing_count = source_analysis['missing_source_count']
    
    # Berechne Prozentsätze
    gold_percent = (gold_count / total * 100) if total > 0 else 0
    non_gold_percent = (non_gold_count / total * 100) if total > 0 else 0
    missing_percent = (missing_count / total * 100) if total > 0 else 0
    
    print(f"\n   Total Q&A:           {total}")
    print(f"   ✅ Gold Standard:     {gold_count} ({gold_percent:.1f}%)")
    print(f"   ❌ Non-Gold Standard: {non_gold_count} ({non_gold_percent:.1f}%)")
    print(f"   ⚠️  Missing Source:   {missing_count} ({missing_percent:.1f}%)")
    
    # Entscheidung
    if gold_percent >= 90:
        report['verification_passed'] = True
        print(f"\n   ✅ VERIFIZIERUNG BESTANDEN!")
        print(f"      {gold_percent:.1f}% der Q&A stammen aus Gold Standard")
    elif gold_percent >= 50:
        report['verification_passed'] = 'PARTIAL'
        report['warnings'].append(f"Nur {gold_percent:.1f}% aus Gold Standard - Prüfung empfohlen")
        print(f"\n   ⚠️  TEILWEISE VERIFIZIERT")
        print(f"      Nur {gold_percent:.1f}% aus Gold Standard")
        print(f"      MANUELLE PRÜFUNG EMPFOHLEN!")
    else:
        report['verification_passed'] = False
        report['critical_issues'].append(f"Nur {gold_percent:.1f}% aus Gold Standard!")
        print(f"\n   ❌ VERIFIZIERUNG FEHLGESCHLAGEN!")
        print(f"      Nur {gold_percent:.1f}% aus Gold Standard")
        print(f"      ⚠️  PIPELINE MUSS KORRIGIERT WERDEN!")
    
    # Non-Gold Standard Quellen auflisten
    if non_gold_count > 0:
        print(f"\n   Non-Gold Standard Quellen:")
        for source, count in source_analysis['sources'].items():
            is_gold = any(re.search(p, source, re.IGNORECASE) for p in EXPECTED_GOLD_STANDARD_PATTERNS)
            if not is_gold and '_GOLD_STANDARD' not in source:
                print(f"      ❌ {source}: {count} Q&A")
    
    print("\n" + "="*70)
    
    return report


def save_report(report: Dict, output_file: str = "verification_report.json"):
    """Speichert Bericht als JSON."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n💾 Bericht gespeichert: {output_file}")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Verifiziere Gold Standard Herkunft')
    parser.add_argument('--qa-file', '-i', help='Pfad zur Q&A JSON Datei')
    parser.add_argument('--output', '-o', default='verification_report.json', help='Output Report')
    
    args = parser.parse_args()
    
    report = generate_verification_report(args.qa_file)
    save_report(report, args.output)
    
    # Exit Code basierend auf Ergebnis
    if report['verification_passed'] == True:
        print("\n✅ EXIT 0 - Verifizierung bestanden")
        exit(0)
    elif report['verification_passed'] == 'PARTIAL':
        print("\n⚠️  EXIT 1 - Teilweise verifiziert, manuelle Prüfung nötig")
        exit(1)
    else:
        print("\n❌ EXIT 2 - Verifizierung fehlgeschlagen!")
        exit(2)
```

## 0.3 Ausführung

```bash
# 1. Navigiere zum Projekt
cd ~/comet-api  # oder korrekter Pfad

# 2. Führe Verifizierung aus
python scripts/verify_gold_standard_origin.py \
  --qa-file "output_bucket/qa_enhanced_quality.json" \
  --output "verification_report.json"

# ODER mit Backup-Datei
python scripts/verify_gold_standard_origin.py \
  --qa-file "~/Documents/Pruefungsvorbereitung/BACKUP_30NOV/qa_enhanced_quality.json"
```

## 0.4 Erwartete Ergebnisse

**✅ BESTANDEN (>=90% aus Gold Standard):**
→ Weiter mit Aufgabe 2

**⚠️ TEILWEISE (50-90%):**
→ Manuelle Stichprobe von 20 Fragen
→ Entscheide ob akzeptabel

**❌ FEHLGESCHLAGEN (<50%):**
→ **SOFORT STOPPEN!**
→ Pipeline muss mit korrektem Input-Dir neu gestartet werden:
```bash
python complete_pipeline_orchestrator.py \
  --recursive \
  --input-dir "Input_Bucket/_GOLD_STANDARD" \
  --output-dir "output_bucket/gold_standard_corrected"
```

## 0.5 Definition of Done - Aufgabe 0

- [ ] Verifizierungs-Script ausgeführt
- [ ] Report zeigt >=90% Gold Standard Herkunft
- [ ] Oder: Korrektur-Lauf gestartet und abgeschlossen
- [ ] Bericht an User: "Verifizierung bestanden/fehlgeschlagen"

---

# 📝 AUFGABE 2: KONVERTIERUNG INS PRÜFUNGSFORMAT

**Voraussetzung:** Aufgabe 0 bestanden (>=90% Gold Standard)

## 2.1 Das 5-Punkte-Antwortschema

Jede Antwort MUSS diese Struktur haben:

```json
{
  "1_definition_klassifikation": "Definition der Erkrankung. Klassifikation nach [NAME] (z.B. NYHA, Garden, CHA2DS2-VASc)",
  "2_aetiologie_pathophysiologie": "Ursachen und Mechanismus",
  "3_diagnostik": "Anamnese → Körperliche Untersuchung → Labor → Bildgebung",
  "4_therapie": "First-Line: [Medikament] [EXAKTE DOSIS mg/kg]. Second-Line: ...",
  "5_rechtlich": "§630d BGB (Einwilligung), §630e BGB (Aufklärung), §630f BGB (Dokumentation)"
}
```

**Bei Notfall zusätzlich ABCDE-Schema:**
```json
{
  "notfall_abcde": {
    "A_airway": "Freimachen, Guedel/Wendl",
    "B_breathing": "O2 15L/min, Ziel-SpO2 >94%",
    "C_circulation": "2 großlumige Zugänge, Volumen",
    "D_disability": "GCS, Pupillen, BZ",
    "E_exposure": "Entkleiden, Wärmeerhalt"
  }
}
```

## 2.2 Bekannte Klassifikationen (IMMER mit Namen!)

```python
KLASSIFIKATIONEN = {
    # Kardiologie
    "herzinsuffizienz": "NYHA I-IV",
    "vorhofflimmern_schlaganfall": "CHA2DS2-VASc Score",
    "vorhofflimmern_blutung": "HAS-BLED Score",
    "herzinfarkt_risiko": "GRACE Score",
    "brustschmerz": "HEART Score",
    
    # Pneumologie
    "pneumonie_ambulant": "CRB-65 / CURB-65",
    "pneumonie_stationaer": "PSI (Pneumonia Severity Index)",
    "lungenembolie": "Wells Score, Geneva Score",
    "copd": "GOLD Stadien I-IV",
    
    # Chirurgie/Orthopädie
    "schenkelhalsfraktur": "Garden I-IV, Pauwels I-III",
    "sprunggelenkfraktur": "Weber A/B/C",
    "aortenaneurysma": "Stanford A/B, DeBakey I-III",
    "appendizitis": "Alvarado Score",
    "verbrennung": "Grad 1-3, Neunerregel nach Wallace",
    
    # Neurologie
    "schlaganfall": "NIHSS, mRS (modified Rankin Scale)",
    "bewusstsein": "Glasgow Coma Scale (GCS)",
    "kopfschmerz": "ICHD-3 Klassifikation",
    
    # Gastroenterologie
    "leberzirrhose": "Child-Pugh A/B/C",
    "gi_blutung": "Rockall Score, Glasgow-Blatchford",
    "pankreatitis": "Ranson Kriterien, APACHE II",
    
    # Nephrologie
    "niereninsuffizienz": "KDIGO Stadien G1-G5",
    "aki": "RIFLE / AKIN Kriterien",
    
    # Onkologie
    "tumor_allgemein": "TNM Klassifikation",
    
    # Infektiologie
    "sepsis": "SOFA Score, qSOFA",
    "meningitis": "HICPAC Kriterien",
}
```

## 2.3 Konvertierungs-Script

Erstelle `scripts/convert_to_exam_format.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Konvertierung ins Prüfungsformat
===========================================

Konvertiert Q&A ins 5-Punkte-Schema der Kenntnisprüfung.
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from copy import deepcopy

# ============================================================================
# SICHERHEITS-FUNKTIONEN (aus vorherigem Prompt)
# ============================================================================

def safe_backup(filepath: str, backup_dir: str = "backups") -> str:
    """Erstellt Backup vor Änderungen."""
    path = Path(filepath)
    if not path.exists():
        return None
    
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"{path.stem}_{timestamp}{path.suffix}"
    
    import shutil
    shutil.copy2(path, backup_file)
    print(f"💾 Backup erstellt: {backup_file}")
    
    return str(backup_file)


def safe_filter(original_count: int, filtered_count: int, operation: str) -> bool:
    """
    Prüft ob Filter zu viele Daten entfernt.
    
    Returns:
        True wenn sicher, False wenn gefährlich
    """
    if original_count == 0:
        return True
    
    loss_percent = (1 - filtered_count / original_count) * 100
    
    if loss_percent > 90:
        print(f"🚨 KRITISCH: {operation} würde {loss_percent:.1f}% der Daten entfernen!")
        print(f"   Original: {original_count}, Nach Filter: {filtered_count}")
        print(f"   ⛔ OPERATION ABGEBROCHEN!")
        return False
    elif loss_percent > 50:
        print(f"⚠️  WARNUNG: {operation} entfernt {loss_percent:.1f}% der Daten")
        print(f"   Original: {original_count}, Nach Filter: {filtered_count}")
        # Weiter, aber warnen
    
    return True


# ============================================================================
# KLASSIFIKATIONEN & DOSIERUNGEN
# ============================================================================

KLASSIFIKATIONEN = {
    "herzinsuffizienz": "NYHA",
    "vorhofflimmern": "CHA2DS2-VASc",
    "pneumonie": "CRB-65",
    "schenkelhalsfraktur": "Garden/Pauwels",
    "sprunggelenk": "Weber",
    "verbrennung": "Grad 1-3, Neunerregel",
    "schlaganfall": "NIHSS",
    "bewusstsein": "GCS",
    "leberzirrhose": "Child-Pugh",
    "niereninsuffizienz": "KDIGO",
    "sepsis": "SOFA/qSOFA",
    "lungenembolie": "Wells",
    "copd": "GOLD",
}

# Häufige Medikamente mit Standarddosierungen
STANDARD_DOSIERUNGEN = {
    "amoxicillin": "3x 1000mg p.o.",
    "metoprolol": "1-2x 47.5-95mg p.o.",
    "ramipril": "1x 2.5-10mg p.o.",
    "furosemid": "20-40mg i.v./p.o.",
    "heparin": "5000 IE s.c. oder gewichtsadaptiert i.v.",
    "enoxaparin": "1x 40mg s.c. (Prophylaxe) oder 2x 1mg/kg (Therapie)",
    "paracetamol": "3-4x 1000mg p.o./i.v., max 4g/Tag",
    "ibuprofen": "3x 400-600mg p.o.",
    "morphin": "2.5-10mg i.v. titriert",
    "adrenalin": "1mg i.v. alle 3-5min (Reanimation)",
    "noradrenalin": "0.1-1 µg/kg/min i.v.",
    "prednisolon": "1mg/kg/Tag (Akut), Ausschleichen",
}

# Rechtliche Paragraphen
RECHTLICHE_ASPEKTE = {
    "aufklaerung": "§630e BGB - Aufklärungspflicht: Diagnose, Verlauf, Risiken, Alternativen",
    "einwilligung": "§630d BGB - Einwilligung vor Behandlung erforderlich",
    "dokumentation": "§630f BGB - Dokumentationspflicht in Patientenakte",
    "einsicht": "§630g BGB - Einsichtnahme in Patientenakte",
    "beweislast": "§630h BGB - Beweislast bei Behandlungsfehlern",
}


# ============================================================================
# KONVERTIERUNGS-LOGIK
# ============================================================================

@dataclass
class ExamQuestion:
    """Eine Frage im Prüfungsformat."""
    id: str
    frage: str
    patientenvorstellung: Optional[str] = None
    antwort: Dict = field(default_factory=dict)
    notfall_abcde: Optional[Dict] = None
    
    # Metadaten
    source: str = ""
    thema: str = ""
    kategorie: str = ""
    schwierigkeit: str = "mittel"
    
    # Enrichment-Flags
    needs_dose_enrichment: bool = False
    needs_classification_verification: bool = False
    needs_legal_enrichment: bool = False
    
    # Original für Vergleich
    original_answer: str = ""


def detect_topic(text: str) -> Tuple[str, str]:
    """Erkennt Thema und Kategorie aus dem Text."""
    
    text_lower = text.lower()
    
    # Kategorie-Mapping
    kategorien = {
        "Innere Medizin": ["herzinsuffizienz", "hypertonie", "diabetes", "pneumonie", 
                          "copd", "asthma", "anämie", "leukämie", "rheuma"],
        "Chirurgie": ["appendizitis", "fraktur", "hernie", "cholezystitis", 
                      "ileus", "peritonitis", "wunde", "naht"],
        "Neurologie": ["schlaganfall", "epilepsie", "parkinson", "demenz", 
                       "kopfschmerz", "migräne", "meningitis"],
        "Notfallmedizin": ["reanimation", "schock", "polytrauma", "intoxikation",
                          "anaphylaxie", "notfall"],
        "Pädiatrie": ["kind", "säugling", "neugeboren", "impf", "fieberkrampf"],
        "Gynäkologie": ["schwanger", "geburt", "sectio", "präeklampsie", "mastitis"],
        "Psychiatrie": ["depression", "schizophren", "suizid", "angst", "panik"],
        "Rechtsmedizin": ["leichenschau", "totenschein", "obduktion", "gewalt"],
    }
    
    for kategorie, keywords in kategorien.items():
        for kw in keywords:
            if kw in text_lower:
                return kw, kategorie
    
    return "allgemein", "Allgemeinmedizin"


def is_emergency_case(text: str) -> bool:
    """Erkennt ob es ein Notfall ist."""
    emergency_keywords = [
        "notfall", "reanimation", "schock", "bewusstlos", "atemstillstand",
        "herzstillstand", "polytrauma", "akut", "sofort", "notarzt",
        "intensiv", "anaphylax", "sepsis", "akutes abdomen"
    ]
    text_lower = text.lower()
    return any(kw in text_lower for kw in emergency_keywords)


def extract_medications(text: str) -> List[str]:
    """Extrahiert erwähnte Medikamente."""
    found = []
    text_lower = text.lower()
    
    for med in STANDARD_DOSIERUNGEN.keys():
        if med in text_lower:
            found.append(med)
    
    return found


def create_5_point_answer(original_answer: str, frage: str) -> Tuple[Dict, Dict]:
    """
    Konvertiert eine Antwort ins 5-Punkte-Schema.
    
    Returns:
        (structured_answer, enrichment_flags)
    """
    
    text_lower = (original_answer + " " + frage).lower()
    thema, kategorie = detect_topic(text_lower)
    
    # Basis-Struktur
    answer = {
        "1_definition_klassifikation": "",
        "2_aetiologie_pathophysiologie": "",
        "3_diagnostik": "",
        "4_therapie": "",
        "5_rechtlich": ""
    }
    
    flags = {
        "needs_dose_enrichment": False,
        "needs_classification_verification": False,
        "needs_legal_enrichment": False
    }
    
    # Versuche vorhandene Struktur zu erkennen und zu mappen
    sections = {
        "definition": ["definition", "was ist", "bezeichnet", "versteht man"],
        "klassifikation": ["klassifikation", "stadien", "grad", "score", "einteilung"],
        "aetiologie": ["ursache", "ätiologie", "pathophysio", "entsteh", "risikofaktor"],
        "diagnostik": ["diagnostik", "untersuchung", "labor", "bildgebung", "anamnese"],
        "therapie": ["therapie", "behandlung", "medikament", "operation", "first-line"],
        "rechtlich": ["§", "bgb", "aufklärung", "einwilligung", "dokumentation", "recht"]
    }
    
    # Parse original_answer nach Abschnitten
    lines = original_answer.split('\n')
    current_section = None
    section_content = {k: [] for k in sections.keys()}
    
    for line in lines:
        line_lower = line.lower()
        
        # Erkenne neuen Abschnitt
        for section, keywords in sections.items():
            if any(kw in line_lower for kw in keywords):
                current_section = section
                break
        
        if current_section and line.strip():
            section_content[current_section].append(line.strip())
    
    # Baue strukturierte Antwort
    if section_content["definition"] or section_content["klassifikation"]:
        answer["1_definition_klassifikation"] = " ".join(
            section_content["definition"] + section_content["klassifikation"]
        )
    else:
        # Placeholder
        answer["1_definition_klassifikation"] = f"[Definition von {thema} ergänzen]"
        flags["needs_classification_verification"] = True
    
    if section_content["aetiologie"]:
        answer["2_aetiologie_pathophysiologie"] = " ".join(section_content["aetiologie"])
    else:
        answer["2_aetiologie_pathophysiologie"] = "[Ätiologie ergänzen]"
    
    if section_content["diagnostik"]:
        answer["3_diagnostik"] = " ".join(section_content["diagnostik"])
    else:
        answer["3_diagnostik"] = "1. Anamnese, 2. Körperliche Untersuchung, 3. Labor, 4. Bildgebung"
    
    if section_content["therapie"]:
        therapie_text = " ".join(section_content["therapie"])
        answer["4_therapie"] = therapie_text
        
        # Prüfe ob Dosierungen vorhanden
        meds = extract_medications(therapie_text)
        if meds:
            # Prüfe ob Dosierungen angegeben
            dose_pattern = r'\d+\s*(mg|g|µg|IE|ml)'
            if not re.search(dose_pattern, therapie_text):
                flags["needs_dose_enrichment"] = True
    else:
        answer["4_therapie"] = "[Therapie mit Dosierungen ergänzen]"
        flags["needs_dose_enrichment"] = True
    
    if section_content["rechtlich"]:
        answer["5_rechtlich"] = " ".join(section_content["rechtlich"])
    else:
        answer["5_rechtlich"] = "§630d BGB (Einwilligung), §630e BGB (Aufklärung), §630f BGB (Dokumentation)"
        flags["needs_legal_enrichment"] = True
    
    # Klassifikation prüfen
    for condition, klassifikation in KLASSIFIKATIONEN.items():
        if condition in text_lower:
            if klassifikation.lower() not in answer["1_definition_klassifikation"].lower():
                flags["needs_classification_verification"] = True
                break
    
    return answer, flags


def create_abcde_schema() -> Dict:
    """Erstellt ABCDE-Schema Template für Notfälle."""
    return {
        "A_airway": "Atemwege freimachen, Absaugen, Guedel-/Wendl-Tubus, ggf. Intubation",
        "B_breathing": "O2-Gabe (15L/min über Maske), Ziel-SpO2 >94%, Auskultation, ggf. Beatmung",
        "C_circulation": "2 großlumige Zugänge, Volumen (kristalloid), Monitoring (RR, HF, EKG)",
        "D_disability": "GCS dokumentieren, Pupillen (Größe, Lichtreaktion), BZ messen",
        "E_exposure": "Entkleiden, Ganzkörperinspektion, Temperatur, Wärmeerhalt"
    }


def convert_qa_to_exam_format(qa: Dict, index: int) -> ExamQuestion:
    """Konvertiert ein Q&A-Paar ins Prüfungsformat."""
    
    frage = qa.get('frage', qa.get('question', ''))
    original_answer = qa.get('antwort', qa.get('answer', ''))
    
    if isinstance(original_answer, dict):
        # Bereits strukturiert - behalte bei
        original_answer_text = json.dumps(original_answer, ensure_ascii=False)
    else:
        original_answer_text = str(original_answer)
    
    # Thema und Kategorie erkennen
    thema, kategorie = detect_topic(frage + " " + original_answer_text)
    
    # 5-Punkte-Antwort erstellen
    structured_answer, flags = create_5_point_answer(original_answer_text, frage)
    
    # Prüfe auf Notfall
    is_emergency = is_emergency_case(frage + " " + original_answer_text)
    abcde = create_abcde_schema() if is_emergency else None
    
    # Patientenvorstellung generieren (falls nicht vorhanden)
    patientenvorstellung = None
    if "patient" in frage.lower() or "jährig" in frage.lower():
        patientenvorstellung = frage  # Frage enthält bereits Vorstellung
    
    return ExamQuestion(
        id=qa.get('id', f"Q{index:04d}"),
        frage=frage,
        patientenvorstellung=patientenvorstellung,
        antwort=structured_answer,
        notfall_abcde=abcde,
        source=qa.get('source', qa.get('quelle', '')),
        thema=thema,
        kategorie=kategorie,
        schwierigkeit="mittel",
        needs_dose_enrichment=flags["needs_dose_enrichment"],
        needs_classification_verification=flags["needs_classification_verification"],
        needs_legal_enrichment=flags["needs_legal_enrichment"],
        original_answer=original_answer_text[:500]  # Gekürzt für Vergleich
    )


def convert_all(input_file: str, output_file: str, enrichment_file: str):
    """Konvertiert alle Q&A Paare."""
    
    print("\n" + "="*70)
    print("📝 KONVERTIERUNG INS PRÜFUNGSFORMAT")
    print("="*70)
    
    # Backup
    if Path(output_file).exists():
        safe_backup(output_file)
    
    # Laden
    print(f"\n📥 Lade: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'qa_pairs' in data:
        qa_pairs = data['qa_pairs']
    elif isinstance(data, list):
        qa_pairs = data
    else:
        qa_pairs = [data]
    
    print(f"   → {len(qa_pairs)} Q&A Paare")
    
    # Konvertieren
    print("\n🔄 Konvertiere...")
    
    converted = []
    needs_enrichment = []
    
    for i, qa in enumerate(qa_pairs):
        exam_q = convert_qa_to_exam_format(qa, i)
        converted.append(asdict(exam_q))
        
        # Sammle die, die Enrichment brauchen
        if exam_q.needs_dose_enrichment or exam_q.needs_classification_verification or exam_q.needs_legal_enrichment:
            needs_enrichment.append({
                'id': exam_q.id,
                'frage': exam_q.frage[:100],
                'needs_dose_enrichment': exam_q.needs_dose_enrichment,
                'needs_classification_verification': exam_q.needs_classification_verification,
                'needs_legal_enrichment': exam_q.needs_legal_enrichment
            })
        
        if (i + 1) % 500 == 0:
            print(f"   {i + 1}/{len(qa_pairs)} verarbeitet...")
    
    # Sicherheitsprüfung
    if not safe_filter(len(qa_pairs), len(converted), "Konvertierung"):
        print("❌ Konvertierung abgebrochen!")
        return
    
    # Speichern - Hauptdatei
    print(f"\n💾 Speichere: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'created': datetime.now().isoformat(),
                'source_file': input_file,
                'total_questions': len(converted),
                'format': '5-Punkte-Schema Kenntnisprüfung'
            },
            'questions': converted
        }, f, ensure_ascii=False, indent=2)
    
    # Speichern - Enrichment-Liste
    print(f"💾 Speichere Enrichment-Liste: {enrichment_file}")
    with open(enrichment_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_needs_enrichment': len(needs_enrichment),
            'questions': needs_enrichment
        }, f, ensure_ascii=False, indent=2)
    
    # Statistik
    print("\n" + "-"*70)
    print("📊 STATISTIK")
    print("-"*70)
    print(f"   Total konvertiert:              {len(converted)}")
    print(f"   Brauchen Dosierungs-Enrichment: {sum(1 for q in converted if q['needs_dose_enrichment'])}")
    print(f"   Brauchen Klassifikations-Check: {sum(1 for q in converted if q['needs_classification_verification'])}")
    print(f"   Brauchen Rechtliches:           {sum(1 for q in converted if q['needs_legal_enrichment'])}")
    print(f"   Notfall-Fälle (mit ABCDE):      {sum(1 for q in converted if q['notfall_abcde'])}")
    
    # Kategorien
    kategorien = {}
    for q in converted:
        kat = q['kategorie']
        kategorien[kat] = kategorien.get(kat, 0) + 1
    
    print(f"\n   Nach Kategorie:")
    for kat, count in sorted(kategorien.items(), key=lambda x: -x[1]):
        print(f"      {kat}: {count}")
    
    print("\n" + "="*70)
    print("✅ KONVERTIERUNG ABGESCHLOSSEN")
    print("="*70)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Konvertiere Q&A ins Prüfungsformat')
    parser.add_argument('--input', '-i', required=True, help='Input Q&A JSON')
    parser.add_argument('--output', '-o', default='kenntnisprufung_formatted.json', help='Output Datei')
    parser.add_argument('--enrichment', '-e', default='enrichment_needed.json', help='Enrichment-Liste')
    
    args = parser.parse_args()
    
    convert_all(args.input, args.output, args.enrichment)
```

## 2.4 Ausführung

```bash
python scripts/convert_to_exam_format.py \
  --input "output_bucket/qa_enhanced_quality.json" \
  --output "output_bucket/kenntnisprufung_formatted.json" \
  --enrichment "output_bucket/enrichment_needed.json"
```

## 2.5 Definition of Done - Aufgabe 2

- [ ] Alle 3.170 Q&A ins 5-Punkte-Schema konvertiert
- [ ] Notfälle haben ABCDE-Schema
- [ ] Enrichment-Liste erstellt
- [ ] Statistik zeigt Kategorien-Verteilung

---

# 🤖 AUFGABE 3: RAG ENRICHMENT (PERPLEXITY + PORTKEY) — OBLIGATORISCH

**Voraussetzung:** Aufgabe 2 abgeschlossen

## ⚠️ WICHTIG: RAG Enrichment ist KEINE Option, sondern PFLICHT!

Jede Frage MUSS mit aktuellen Leitlinien-Informationen angereichert werden:
- **Dosierungen** → AWMF-Leitlinien
- **Klassifikationen** → Aktuelle Scores und Stadien
- **Rechtliche Aspekte** → §630 BGB

## 3.1 Zweck

Die `enrichment_needed.json` enthält Q&A die:
- Dosierungen brauchen
- Klassifikations-Verifizierung brauchen
- Rechtliche Ergänzung brauchen

## 3.2 Enrichment-Script

Erstelle `scripts/enrich_with_perplexity.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: RAG Enrichment mit Perplexity + Portkey
==================================================

Reichert Q&A mit fehlenden Informationen an:
- Dosierungen
- Klassifikationen
- Rechtliche Aspekte
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import requests

# ============================================================================
# KONFIGURATION
# ============================================================================

# API Keys (aus Environment)
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY", "")
PERPLEXITY_API_KEY_1 = os.getenv("PERPLEXITY_API_KEY_1", "")
PERPLEXITY_API_KEY_2 = os.getenv("PERPLEXITY_API_KEY_2", "")

# Rate Limiting
REQUESTS_PER_MINUTE = 20
REQUEST_DELAY = 3.0  # Sekunden

# Budget
MAX_REQUESTS = 500  # Pro Session
MAX_COST_USD = 5.0

# Cache
CACHE_FILE = "cache/perplexity_enrichment_cache.json"

# ============================================================================
# CACHE
# ============================================================================

class EnrichmentCache:
    """Einfacher JSON-Cache für Enrichment-Ergebnisse."""
    
    def __init__(self, cache_file: str):
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache = self._load()
    
    def _load(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _hash(self, query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()[:16]
    
    def get(self, query: str) -> Optional[str]:
        return self.cache.get(self._hash(query))
    
    def set(self, query: str, response: str):
        self.cache[self._hash(query)] = response
        self._save()


# ============================================================================
# PERPLEXITY CLIENT
# ============================================================================

class PerplexityClient:
    """Einfacher Perplexity API Client mit Fallback."""
    
    def __init__(self):
        self.keys = [k for k in [PERPLEXITY_API_KEY_1, PERPLEXITY_API_KEY_2] if k]
        self.current_key_index = 0
        self.request_count = 0
        self.cache = EnrichmentCache(CACHE_FILE)
        
        if not self.keys:
            print("⚠️  Keine Perplexity API Keys gefunden!")
            print("   Setze PERPLEXITY_API_KEY_1 und/oder PERPLEXITY_API_KEY_2")
    
    def _get_key(self) -> str:
        if not self.keys:
            return ""
        key = self.keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        return key
    
    def query(self, prompt: str, use_cache: bool = True) -> Optional[str]:
        """Führt Query aus."""
        
        # Budget prüfen
        if self.request_count >= MAX_REQUESTS:
            print(f"⚠️  Request-Limit erreicht ({MAX_REQUESTS})")
            return None
        
        # Cache prüfen
        if use_cache:
            cached = self.cache.get(prompt)
            if cached:
                print("   💾 Cache Hit")
                return cached
        
        # Rate Limiting
        time.sleep(REQUEST_DELAY)
        
        # Request
        api_key = self._get_key()
        if not api_key:
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "Du bist ein deutscher Facharzt. Antworte präzise und kurz nach aktueller Leitlinie."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result['choices'][0]['message']['content']
            
            self.request_count += 1
            self.cache.set(prompt, answer)
            
            return answer
            
        except Exception as e:
            print(f"   ❌ Fehler: {e}")
            return None


# ============================================================================
# ENRICHMENT QUERIES
# ============================================================================

def query_dosierung(client: PerplexityClient, medikament: str, indikation: str) -> Optional[str]:
    """Fragt Dosierung ab."""
    prompt = f"""Exakte Dosierung von {medikament} bei {indikation} nach aktueller AWMF-Leitlinie.

Antworte NUR mit:
- Erwachsene: [Dosis] [Frequenz]
- Kinder: [Dosis/kg] oder "nicht zugelassen"
- Max. Tagesdosis: [mg/Tag]
- Besonderheiten: [Niereninsuffizienz, Alter, etc.]"""
    
    return client.query(prompt)


def query_klassifikation(client: PerplexityClient, krankheit: str) -> Optional[str]:
    """Fragt Klassifikation ab."""
    prompt = f"""Welche Klassifikation(en) gibt es für {krankheit}?

Antworte NUR mit:
- Name: [z.B. NYHA, Garden, CHA2DS2-VASc]
- Stadien/Grade: [Auflistung mit Kriterien]
- Klinische Relevanz: [Therapiekonsequenz]"""
    
    return client.query(prompt)


def query_rechtlich(client: PerplexityClient, kontext: str) -> Optional[str]:
    """Fragt rechtliche Aspekte ab."""
    prompt = f"""Rechtliche Aspekte bei {kontext} in Deutschland.

Antworte NUR mit:
- §630d BGB: [Einwilligung - was relevant]
- §630e BGB: [Aufklärung - was relevant]  
- §630f BGB: [Dokumentation - was relevant]
- Besonderheiten: [Notfall, Minderjährige, etc.]"""
    
    return client.query(prompt)


# ============================================================================
# ENRICHMENT PIPELINE
# ============================================================================

def enrich_questions(
    enrichment_file: str,
    formatted_file: str,
    output_file: str,
    max_enrichments: int = None  # None = ALLE verarbeiten
):
    """Reichert Fragen an. ALLE Fragen müssen enriched werden!"""
    
    print("\n" + "="*70)
    print("🤖 RAG ENRICHMENT MIT PERPLEXITY (OBLIGATORISCH)")
    print("="*70)
    
    # Client
    client = PerplexityClient()
    
    # Laden
    print(f"\n📥 Lade Enrichment-Liste: {enrichment_file}")
    with open(enrichment_file, 'r', encoding='utf-8') as f:
        enrichment_data = json.load(f)
    
    needs_enrichment = enrichment_data.get('questions', [])
    print(f"   → {len(needs_enrichment)} Fragen brauchen Enrichment")
    
    print(f"\n📥 Lade formatierte Fragen: {formatted_file}")
    with open(formatted_file, 'r', encoding='utf-8') as f:
        formatted_data = json.load(f)
    
    questions = {q['id']: q for q in formatted_data.get('questions', [])}
    
    # Enrichment - ALLE Fragen verarbeiten
    print(f"\n🔄 Starte Enrichment für ALLE {len(needs_enrichment)} Fragen...")
    
    # Wenn max_enrichments None, verarbeite alle
    items_to_process = needs_enrichment if max_enrichments is None else needs_enrichment[:max_enrichments]
    total_items = len(items_to_process)
    
    enriched_count = 0
    errors = []
    
    for i, item in enumerate(items_to_process):
        q_id = item['id']
        
        if q_id not in questions:
            continue
        
        question = questions[q_id]
        frage_text = question.get('frage', '')
        
        print(f"\n[{i+1}/{total_items}] {q_id}")
        
        # Dosierung
        if item.get('needs_dose_enrichment'):
            print("   📋 Frage Dosierung ab...")
            # Extrahiere Medikament aus Frage/Antwort
            therapie = question.get('antwort', {}).get('4_therapie', '')
            if therapie and therapie != "[Therapie mit Dosierungen ergänzen]":
                result = query_dosierung(client, "Medikament", frage_text[:50])
                if result:
                    question['antwort']['4_therapie'] += f"\n\n[RAG-Enrichment]:\n{result}"
                    enriched_count += 1
        
        # Klassifikation
        if item.get('needs_classification_verification'):
            print("   📋 Frage Klassifikation ab...")
            result = query_klassifikation(client, frage_text[:50])
            if result:
                question['antwort']['1_definition_klassifikation'] += f"\n\n[Klassifikation]:\n{result}"
                enriched_count += 1
        
        # Rechtlich
        if item.get('needs_legal_enrichment'):
            print("   📋 Frage Rechtliches ab...")
            result = query_rechtlich(client, frage_text[:50])
            if result:
                question['antwort']['5_rechtlich'] = result
                enriched_count += 1
        
        # Budget prüfen
        if client.request_count >= MAX_REQUESTS:
            print(f"\n⚠️  Request-Limit erreicht!")
            break
    
    # Speichern
    print(f"\n💾 Speichere: {output_file}")
    
    formatted_data['questions'] = list(questions.values())
    formatted_data['metadata']['enriched'] = datetime.now().isoformat()
    formatted_data['metadata']['enrichment_count'] = enriched_count
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(formatted_data, f, ensure_ascii=False, indent=2)
    
    # Statistik
    print("\n" + "-"*70)
    print("📊 ENRICHMENT STATISTIK")
    print("-"*70)
    print(f"   API Requests:    {client.request_count}")
    print(f"   Enrichments:     {enriched_count}")
    print(f"   Cache Hits:      {len(client.cache.cache)}")
    print(f"   Fehler:          {len(errors)}")
    
    print("\n✅ ENRICHMENT ABGESCHLOSSEN")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='RAG Enrichment')
    parser.add_argument('--enrichment', '-e', required=True, help='Enrichment-Liste JSON')
    parser.add_argument('--formatted', '-f', required=True, help='Formatierte Fragen JSON')
    parser.add_argument('--output', '-o', default='kenntnisprufung_enriched.json', help='Output')
    parser.add_argument('--max', '-m', type=int, default=100, help='Max Enrichments')
    
    args = parser.parse_args()
    
    enrich_questions(
        args.enrichment,
        args.formatted,
        args.output,
        args.max
    )
```

## 3.3 Ausführung

```bash
# API Keys setzen
export PERPLEXITY_API_KEY_1="pplx-..."
export PERPLEXITY_API_KEY_2="pplx-..."  # Für höheren Durchsatz

# Enrichment starten - ALLE Fragen (kein max-Limit!)
python scripts/enrich_with_perplexity.py \
  --enrichment "output_bucket/enrichment_needed.json" \
  --formatted "output_bucket/kenntnisprufung_formatted.json" \
  --output "output_bucket/kenntnisprufung_enriched.json"

# HINWEIS: Bei großer Anzahl ggf. in Batches aufteilen wegen Rate Limits
```

## 3.4 Definition of Done - Aufgabe 3

- [ ] Perplexity Client funktioniert
- [ ] Cache funktioniert (keine doppelten Requests)
- [ ] **ALLE Fragen aus enrichment_needed.json wurden enriched** (nicht nur 100!)
- [ ] `kenntnisprufung_enriched.json` erstellt mit vollständigen Dosierungen, Klassifikationen, Rechtlichem

---

# 🛡️ AUFGABE 4: MEDICAL VALIDATION (4 Prüfer)

**Voraussetzung:** Aufgabe 3 abgeschlossen

## 4.1 Die 4 Prüfer

Erstelle `scripts/medical_validators.py` (vollständiger Code aus vorherigem Prompt, hier gekürzt):

```python
#!/usr/bin/env python3
"""
Medical Validation Layer - 4 Prüfer
"""

# [Vollständiger Code aus CODEX_MEGA_PROMPT_V3_KOMPLETT.md, Teil 3]
# Hier nur Zusammenfassung:

class DosageValidator:
    """💊 Prüft auf Über-/Unterdosierungen"""
    # Bekannte Grenzen für ~30 häufige Medikamente
    pass

class ICD10Validator:
    """📋 Prüft Geschlechts-/Alters-Inkonsistenzen"""
    pass

class LabValueValidator:
    """🧪 Prüft kritische Laborwerte"""
    pass

class LogicalConsistencyValidator:
    """🧠 Prüft Kontraindikationen"""
    pass

class MedicalValidationPipeline:
    """Führt alle 4 Prüfer aus"""
    pass
```

## 4.2 Ausführung

```bash
python scripts/medical_validators.py \
  --input "output_bucket/kenntnisprufung_enriched.json" \
  --output "output_bucket/validation_results.json"
```

## 4.3 Gold Standard Vergleich

Zusätzlich: Vergleiche mit echten Protokollen

```bash
python scripts/gold_standard_comparator.py \
  --gold "Input_Bucket/_GOLD_STANDARD" \
  --generated "output_bucket/kenntnisprufung_enriched.json" \
  --output "output_bucket/gold_comparison_report.json"
```

## 4.4 Definition of Done - Aufgabe 4

- [ ] Alle 4 Prüfer laufen durch
- [ ] Quarantäne-Liste erstellt (<5% der Fragen)
- [ ] Gold Standard Vergleich zeigt >80% Match
- [ ] Validation Report erstellt

---

# 📋 AUFGABE 5: POST-MORTEM & AUTOMATISIERUNG

## 5.1 Post-Mortem Bericht

Erstelle `docs/POST_MORTEM_DATENVERLUST_30NOV.md`:

```markdown
# Post-Mortem: Datenverlust-Vorfälle November 2025

## Timeline

| Datum | Vorfall | Impact | Root Cause |
|-------|---------|--------|------------|
| 29.11 | Erster Datenverlust | ~768 Q&A fehlten | Unklarer State |
| 30.11 | Zweiter Datenverlust | 16.725→2 Q&A | Aggressiver Tier-3 Filter |

## Root Cause Analysis

### Primäre Ursache
- Filter-Funktion ohne Sicherheitsprüfung
- Keine Validierung der Filter-Ergebnisse
- Fehlende Backups vor kritischen Operationen

### Beitragende Faktoren
- Komplexe Pipeline ohne Checkpoints
- Fehlende Alerts bei Datenverlust

## Korrekturmaßnahmen

1. **safe_filter()** Funktion implementiert
2. **safe_backup()** vor jeder Transformation
3. **State-Monitoring** für alle JSON-Dateien
4. **Pre-Run Checklist** obligatorisch

## Lessons Learned

1. IMMER Backup vor Änderungen
2. IMMER Validierung nach Filter
3. NIEMALS >50% Datenverlust ohne Alarm
4. Checkpoints in langen Pipelines
```

## 5.2 GitHub Action für automatische Backups

Erstelle `.github/workflows/backup-qa-data.yml`:

```yaml
name: Backup Q&A Data

on:
  push:
    paths:
      - 'output_bucket/*.json'
  schedule:
    - cron: '0 2 * * *'  # Täglich 2 Uhr UTC

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Create backup
        run: |
          TIMESTAMP=$(date +%Y%m%d_%H%M%S)
          mkdir -p backups/$TIMESTAMP
          cp output_bucket/*.json backups/$TIMESTAMP/ || true
          
      - name: Validate Q&A count
        run: |
          COUNT=$(python -c "import json; d=json.load(open('output_bucket/kenntnisprufung_enriched.json')); print(len(d.get('questions',[])))")
          echo "Q&A Count: $COUNT"
          if [ "$COUNT" -lt 3000 ]; then
            echo "⚠️ WARNING: Q&A count below 3000!"
            exit 1
          fi
```

## 5.3 Definition of Done - Aufgabe 5

- [ ] Post-Mortem Dokument erstellt
- [ ] GitHub Action committed
- [ ] Pre-commit Hook installiert
- [ ] Alle Sicherheitsmaßnahmen dokumentiert

---

# ✅ GESAMTE DEFINITION OF DONE

| Aufgabe | Kriterium | Erwartet |
|---------|-----------|----------|
| **0** | Verifizierung Gold Standard | >=90% |
| **2** | Fragen konvertiert | 3.170 |
| **2** | Im 5-Punkte-Schema | 100% |
| **3** | RAG Enrichments durchgeführt | **ALLE** (nicht nur Sample!) |
| **3** | Dosierungen vorhanden | 100% |
| **3** | Klassifikationen verifiziert | 100% |
| **3** | Cache funktioniert | ✅ |
| **4** | Medical Validation | <5% Quarantäne |
| **4** | Gold Standard Match | >80% |
| **5** | Post-Mortem | ✅ Erstellt |
| **5** | Automatisierung | ✅ GitHub Action |

---

# 🚀 STARTE JETZT

```bash
# === AUFGABE 0: VERIFIZIERUNG ===
python scripts/verify_gold_standard_origin.py \
  --qa-file "Comet API_backup_20251129/qa_enhanced_quality.json"

# Warte auf Ergebnis! Bei <90% → STOPP!

# === AUFGABE 2: KONVERTIERUNG ===
python scripts/convert_to_exam_format.py \
  --input "Comet API_backup_20251129/qa_enhanced_quality.json" \
  --output "output_bucket/kenntnisprufung_formatted.json"

# === AUFGABE 3: RAG ENRICHMENT (OBLIGATORISCH - ALLE FRAGEN!) ===
python scripts/enrich_with_perplexity.py \
  --enrichment "output_bucket/enrichment_needed.json" \
  --formatted "output_bucket/kenntnisprufung_formatted.json" \
  --output "output_bucket/kenntnisprufung_enriched.json"

# === AUFGABE 4: VALIDATION ===
python scripts/medical_validators.py \
  --input "output_bucket/kenntnisprufung_enriched.json"

# === AUFGABE 5: DOKUMENTATION ===
# Erstelle Post-Mortem und GitHub Action manuell

# === FINALE ===
echo "🎉 Pipeline abgeschlossen!"
```

---

**Berichte nach JEDER Aufgabe:**
1. Ergebnis (Erfolg/Fehlschlag)
2. Zahlen (wie viele verarbeitet)
3. Probleme (falls vorhanden)
4. Nächster Schritt

**KRITISCH: Aufgabe 0 MUSS zuerst bestanden werden!**
