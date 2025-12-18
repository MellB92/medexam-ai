# 🔴 CODEX: KOMPLETTER NEUSTART — ERST ANALYSIEREN, DANN HANDELN

## KONTEXT: WARUM WIR HIER SIND

Es gab **zwei Datenkatastrophen** in diesem Projekt:

1. **Erster Verlust:** 768 Q&A pairs verschwunden durch Pipeline-Crash
2. **Zweiter Verlust:** 3.170 "gerettete" Q&A sind **WERTLOS** — 99.7% stammen NICHT aus echten Prüfungsprotokollen

**Root Cause:** Niemand hat vor dem Arbeiten verstanden, wie das Projekt aufgebaut ist und welche Daten woher kommen.

**Deine erste Aufgabe:** NICHTS AUSFÜHREN. Erst ALLES verstehen.

---

# PHASE 0: VOLLSTÄNDIGE PROJEKT-ANALYSE

## 0.1 Verzeichnisstruktur dokumentieren

```bash
# Erstelle vollständige Übersicht
echo "=== PROJEKT-STRUKTUR ===" > PROJEKT_ANALYSE.md
echo "Erstellt: $(date)" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Hauptverzeichnisse
echo "## Hauptverzeichnisse" >> PROJEKT_ANALYSE.md
ls -la >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Alle Unterverzeichnisse (3 Ebenen tief)
echo "## Vollständiger Baum" >> PROJEKT_ANALYSE.md
find . -maxdepth 3 -type d | head -100 >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Alle Python-Dateien
echo "## Python-Dateien" >> PROJEKT_ANALYSE.md
find . -name "*.py" -type f >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Alle JSON-Dateien mit Größe
echo "## JSON-Dateien (mit Größe)" >> PROJEKT_ANALYSE.md
find . -name "*.json" -type f -exec ls -lh {} \; >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Alle Config-Dateien
echo "## Config-Dateien" >> PROJEKT_ANALYSE.md
find . -name "*.yaml" -o -name "*.yml" -o -name "*.toml" -o -name "*.ini" -o -name ".env*" 2>/dev/null >> PROJEKT_ANALYSE.md
```

## 0.2 Input-Verzeichnisse identifizieren

```bash
echo "## INPUT-ANALYSE" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Finde alle möglichen Input-Ordner
echo "### Alle 'Input' oder 'input' Ordner:" >> PROJEKT_ANALYSE.md
find . -type d -iname "*input*" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Speziell: Gold Standard
echo "### _GOLD_STANDARD Ordner:" >> PROJEKT_ANALYSE.md
find . -type d -name "*GOLD*" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Inhalt von Gold Standard
echo "### Inhalt _GOLD_STANDARD:" >> PROJEKT_ANALYSE.md
if [ -d "Input_Bucket/_GOLD_STANDARD" ]; then
    ls -la "Input_Bucket/_GOLD_STANDARD/" >> PROJEKT_ANALYSE.md
    echo "" >> PROJEKT_ANALYSE.md
    echo "Anzahl PDF: $(find 'Input_Bucket/_GOLD_STANDARD' -name '*.pdf' | wc -l)" >> PROJEKT_ANALYSE.md
    echo "Anzahl DOCX: $(find 'Input_Bucket/_GOLD_STANDARD' -name '*.docx' | wc -l)" >> PROJEKT_ANALYSE.md
else
    echo "❌ ORDNER NICHT GEFUNDEN!" >> PROJEKT_ANALYSE.md
fi
```

## 0.3 Alle Entry-Points finden

```bash
echo "" >> PROJEKT_ANALYSE.md
echo "## ENTRY-POINTS (Pipeline-Scripts)" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Suche nach main/run/pipeline Scripts
echo "### Haupt-Scripts:" >> PROJEKT_ANALYSE.md
for script in main.py run.py pipeline.py orchestrator.py; do
    find . -name "*${script}*" -type f >> PROJEKT_ANALYSE.md 2>/dev/null
done
echo "" >> PROJEKT_ANALYSE.md

# Scripts mit argparse (CLI-Tools)
echo "### Scripts mit CLI (argparse):" >> PROJEKT_ANALYSE.md
grep -l "argparse\|ArgumentParser" *.py scripts/*.py 2>/dev/null >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Scripts mit input-dir Parameter
echo "### Scripts mit --input-dir Parameter:" >> PROJEKT_ANALYSE.md
grep -l "input.dir\|input_dir" *.py scripts/*.py 2>/dev/null >> PROJEKT_ANALYSE.md
```

## 0.4 Bestehende Daten analysieren

```bash
echo "" >> PROJEKT_ANALYSE.md
echo "## BESTEHENDE Q&A DATEIEN" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

# Finde alle Q&A JSONs
for f in $(find . -name "*.json" -size +10k -type f); do
    echo "### Datei: $f" >> PROJEKT_ANALYSE.md
    echo "Größe: $(ls -lh "$f" | awk '{print $5}')" >> PROJEKT_ANALYSE.md
    
    # Prüfe Struktur
    if command -v python3 &> /dev/null; then
        python3 -c "
import json
with open('$f') as fp:
    try:
        data = json.load(fp)
        if isinstance(data, list):
            print(f'Typ: Liste mit {len(data)} Einträgen')
            if len(data) > 0:
                print(f'Erstes Element Keys: {list(data[0].keys())[:5]}')
                # Prüfe auf source-Feld
                sources = set()
                for item in data[:100]:
                    if 'source' in item:
                        sources.add(str(item['source'])[:50])
                if sources:
                    print(f'Source-Werte (Sample): {list(sources)[:3]}')
        elif isinstance(data, dict):
            print(f'Typ: Dict mit Keys: {list(data.keys())[:5]}')
    except Exception as e:
        print(f'Parse-Fehler: {e}')
" >> PROJEKT_ANALYSE.md 2>&1
    fi
    echo "" >> PROJEKT_ANALYSE.md
done
```

## 0.5 State-Files dokumentieren

```bash
echo "## STATE-FILES" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md

find . -name "*state*.json" -o -name "*progress*.json" -o -name "*checkpoint*.json" | while read f; do
    echo "### $f" >> PROJEKT_ANALYSE.md
    ls -la "$f" >> PROJEKT_ANALYSE.md
    head -50 "$f" >> PROJEKT_ANALYSE.md
    echo "" >> PROJEKT_ANALYSE.md
done
```

## 0.6 AUSGABE: Analyse-Report erstellen

```bash
echo "" >> PROJEKT_ANALYSE.md
echo "---" >> PROJEKT_ANALYSE.md
echo "## ZUSAMMENFASSUNG" >> PROJEKT_ANALYSE.md
echo "" >> PROJEKT_ANALYSE.md
echo "Analyse abgeschlossen: $(date)" >> PROJEKT_ANALYSE.md

cat PROJEKT_ANALYSE.md
```

**⚠️ STOP HIER UND WARTE AUF BESTÄTIGUNG**

Poste den vollständigen Inhalt von `PROJEKT_ANALYSE.md` und warte auf Anweisungen, bevor du weitermachst.

---

# PHASE 1: STRATEGIE ZUR PRÄVENTION VON DATENVERLUSTEN

Nach der Analyse implementiere diese Sicherheitsmechanismen:

## 1.1 Erstelle `safety_utils.py`

```python
#!/usr/bin/env python3
"""
SAFETY UTILITIES - Verhindert Datenverluste
MUSS vor jeder Pipeline-Operation importiert werden
"""

import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# =============================================================================
# KONFIGURATION
# =============================================================================

BACKUP_DIR = Path("backups")
GOLD_STANDARD_DIR = Path("Input_Bucket/_GOLD_STANDARD")
REQUIRED_GOLD_STANDARD_RATIO = 0.90  # 90%
MAX_ALLOWED_DATA_LOSS = 0.10  # 10%

# =============================================================================
# BACKUP-FUNKTIONEN
# =============================================================================

def create_timestamped_backup(file_path: Path, reason: str) -> Path:
    """Erstellt Backup mit Timestamp und Grund."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}_{timestamp}_{reason}{file_path.suffix}"
    backup_path = BACKUP_DIR / backup_name
    
    shutil.copy2(file_path, backup_path)
    
    # Log erstellen
    log_entry = {
        "timestamp": timestamp,
        "original": str(file_path),
        "backup": str(backup_path),
        "reason": reason,
        "size_bytes": file_path.stat().st_size,
        "checksum": _file_checksum(file_path)
    }
    
    log_file = BACKUP_DIR / "backup_log.json"
    logs = []
    if log_file.exists():
        logs = json.loads(log_file.read_text())
    logs.append(log_entry)
    log_file.write_text(json.dumps(logs, indent=2))
    
    print(f"✅ Backup erstellt: {backup_path}")
    return backup_path

def _file_checksum(path: Path) -> str:
    """MD5 Checksum einer Datei."""
    return hashlib.md5(path.read_bytes()).hexdigest()

# =============================================================================
# VALIDIERUNGS-FUNKTIONEN
# =============================================================================

def validate_input_source(input_dir: Path) -> bool:
    """
    🚨 KRITISCH: Prüft ob Input aus GOLD_STANDARD stammt.
    
    Returns:
        True wenn valide, False wenn nicht
    """
    input_dir = Path(input_dir).resolve()
    gold_dir = GOLD_STANDARD_DIR.resolve()
    
    # Muss _GOLD_STANDARD im Pfad haben
    if "_GOLD_STANDARD" not in str(input_dir):
        print(f"❌ FEHLER: Input-Verzeichnis enthält nicht '_GOLD_STANDARD'")
        print(f"   Gegeben: {input_dir}")
        print(f"   Erwartet: Pfad muss '_GOLD_STANDARD' enthalten")
        return False
    
    # Prüfe ob Verzeichnis existiert
    if not input_dir.exists():
        print(f"❌ FEHLER: Verzeichnis existiert nicht: {input_dir}")
        return False
    
    # Prüfe ob PDF/DOCX Dateien vorhanden
    pdfs = list(input_dir.glob("**/*.pdf"))
    docx = list(input_dir.glob("**/*.docx"))
    
    if len(pdfs) + len(docx) < 10:
        print(f"❌ FEHLER: Zu wenige Dateien in {input_dir}")
        print(f"   PDFs: {len(pdfs)}, DOCX: {len(docx)}")
        return False
    
    print(f"✅ Input validiert: {input_dir}")
    print(f"   PDFs: {len(pdfs)}, DOCX: {len(docx)}")
    return True

def validate_qa_gold_standard_ratio(qa_file: Path, gold_patterns: List[str] = None) -> Dict[str, Any]:
    """
    🚨 KRITISCH: Prüft wieviel % der Q&A aus Gold-Standard stammen.
    
    Returns:
        Dict mit Statistiken und pass/fail Status
    """
    if gold_patterns is None:
        gold_patterns = ["_GOLD_STANDARD", "Prüfungsprotokoll", "Examensprotokoll"]
    
    with open(qa_file) as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        return {"error": "Datei ist keine Liste", "passed": False}
    
    total = len(data)
    gold_count = 0
    non_gold_sources = []
    
    for item in data:
        source = str(item.get("source", ""))
        is_gold = any(pattern.lower() in source.lower() for pattern in gold_patterns)
        if is_gold:
            gold_count += 1
        else:
            if len(non_gold_sources) < 10:  # Sample
                non_gold_sources.append(source[:100])
    
    ratio = gold_count / total if total > 0 else 0
    passed = ratio >= REQUIRED_GOLD_STANDARD_RATIO
    
    result = {
        "total": total,
        "gold_standard": gold_count,
        "non_gold": total - gold_count,
        "ratio": ratio,
        "required_ratio": REQUIRED_GOLD_STANDARD_RATIO,
        "passed": passed,
        "non_gold_samples": non_gold_sources
    }
    
    if passed:
        print(f"✅ Gold-Standard-Ratio: {ratio:.1%} (≥{REQUIRED_GOLD_STANDARD_RATIO:.0%})")
    else:
        print(f"❌ Gold-Standard-Ratio: {ratio:.1%} (<{REQUIRED_GOLD_STANDARD_RATIO:.0%})")
        print(f"   Non-Gold Samples: {non_gold_sources[:3]}")
    
    return result

def safe_filter(original: List, filtered: List, operation_name: str) -> List:
    """
    🚨 KRITISCH: Verhindert >10% Datenverlust durch Filter.
    
    Raises:
        ValueError wenn zu viele Daten verloren gehen
    """
    if len(original) == 0:
        return filtered
    
    loss_ratio = 1 - (len(filtered) / len(original))
    
    if loss_ratio > MAX_ALLOWED_DATA_LOSS:
        raise ValueError(
            f"❌ STOPP: {operation_name} würde {loss_ratio:.1%} der Daten löschen!\n"
            f"   Original: {len(original)}\n"
            f"   Nach Filter: {len(filtered)}\n"
            f"   Max erlaubt: {MAX_ALLOWED_DATA_LOSS:.0%} Verlust\n"
            f"   → Operation abgebrochen. Prüfe Filter-Logik!"
        )
    
    print(f"✅ {operation_name}: {len(original)} → {len(filtered)} ({loss_ratio:.1%} Verlust, OK)")
    return filtered

# =============================================================================
# CHECKPOINT-SYSTEM
# =============================================================================

class CheckpointManager:
    """Speichert und lädt Pipeline-Checkpoints."""
    
    def __init__(self, checkpoint_dir: Path = Path("checkpoints")):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, name: str, data: Any, metadata: Dict = None):
        """Speichert Checkpoint mit Metadaten."""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "name": name,
            "data_count": len(data) if isinstance(data, (list, dict)) else None,
            "metadata": metadata or {},
            "data": data
        }
        
        path = self.checkpoint_dir / f"{name}.json"
        
        # Backup falls existiert
        if path.exists():
            create_timestamped_backup(path, "checkpoint_overwrite")
        
        path.write_text(json.dumps(checkpoint, indent=2, default=str))
        print(f"✅ Checkpoint gespeichert: {path}")
    
    def load(self, name: str) -> Optional[Any]:
        """Lädt Checkpoint falls vorhanden."""
        path = self.checkpoint_dir / f"{name}.json"
        if not path.exists():
            return None
        
        checkpoint = json.loads(path.read_text())
        print(f"✅ Checkpoint geladen: {name} ({checkpoint.get('data_count', '?')} Einträge)")
        return checkpoint.get("data")
    
    def list_checkpoints(self) -> List[str]:
        """Listet alle verfügbaren Checkpoints."""
        return [p.stem for p in self.checkpoint_dir.glob("*.json")]

# =============================================================================
# PIPELINE-WRAPPER
# =============================================================================

def safe_pipeline_start(input_dir: str, output_dir: str) -> bool:
    """
    🚨 MUSS vor jedem Pipeline-Start aufgerufen werden.
    
    Prüft:
    1. Input kommt aus _GOLD_STANDARD
    2. Output-Dir ist leer oder wird gebackupt
    3. Alle Voraussetzungen erfüllt
    
    Returns:
        True wenn Pipeline starten darf, False sonst
    """
    print("=" * 60)
    print("🛡️ SAFETY CHECK VOR PIPELINE-START")
    print("=" * 60)
    
    # 1. Input validieren
    if not validate_input_source(Path(input_dir)):
        print("\n❌ PIPELINE NICHT GESTARTET: Input-Validierung fehlgeschlagen")
        return False
    
    # 2. Output-Dir prüfen
    output_path = Path(output_dir)
    if output_path.exists() and any(output_path.iterdir()):
        print(f"\n⚠️ Output-Verzeichnis nicht leer: {output_dir}")
        # Backup erstellen
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUP_DIR / f"output_backup_{timestamp}"
        shutil.copytree(output_path, backup_path)
        print(f"✅ Backup erstellt: {backup_path}")
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("\n✅ ALLE CHECKS BESTANDEN - Pipeline darf starten")
    print("=" * 60)
    return True

# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    print("Safety Utils Test")
    print("-" * 40)
    
    # Test Input-Validierung
    validate_input_source(Path("Input_Bucket/_GOLD_STANDARD"))
    
    # Test Checkpoint
    cm = CheckpointManager()
    cm.save("test", [1, 2, 3], {"note": "test"})
    print(f"Checkpoints: {cm.list_checkpoints()}")
```

## 1.2 Erstelle `run_safe_pipeline.py`

```python
#!/usr/bin/env python3
"""
SAFE PIPELINE RUNNER
Wrapper für die Q&A-Pipeline mit allen Sicherheitsmechanismen
"""

import sys
import argparse
from pathlib import Path

# Safety Utils MUSS importiert werden
from safety_utils import (
    safe_pipeline_start,
    validate_qa_gold_standard_ratio,
    create_timestamped_backup,
    CheckpointManager
)

def main():
    parser = argparse.ArgumentParser(description="Safe Pipeline Runner")
    parser.add_argument("--input-dir", required=True, help="Input-Verzeichnis (MUSS _GOLD_STANDARD enthalten)")
    parser.add_argument("--output-dir", required=True, help="Output-Verzeichnis")
    parser.add_argument("--skip-safety", action="store_true", help="⚠️ Safety-Checks überspringen (NICHT EMPFOHLEN)")
    args = parser.parse_args()
    
    # 1. Safety Check
    if not args.skip_safety:
        if not safe_pipeline_start(args.input_dir, args.output_dir):
            print("\n❌ Abbruch: Safety-Check fehlgeschlagen")
            sys.exit(1)
    else:
        print("⚠️ WARNUNG: Safety-Checks übersprungen!")
    
    # 2. Pipeline importieren und starten
    # TODO: Hier den tatsächlichen Pipeline-Import einfügen
    # from complete_pipeline_orchestrator import run_pipeline
    # run_pipeline(args.input_dir, args.output_dir)
    
    print(f"\n🚀 Pipeline würde starten mit:")
    print(f"   Input:  {args.input_dir}")
    print(f"   Output: {args.output_dir}")
    
    # 3. Nach Pipeline: Validierung
    output_qa = Path(args.output_dir) / "generated_qa_llm.json"
    if output_qa.exists():
        result = validate_qa_gold_standard_ratio(output_qa)
        if not result["passed"]:
            print("\n❌ WARNUNG: Output hat nicht genug Gold-Standard-Anteil!")
            sys.exit(2)
    
    print("\n✅ Pipeline erfolgreich abgeschlossen")

if __name__ == "__main__":
    main()
```

---

# PHASE 2: NEUSTART DER PIPELINE

**NUR NACH ABSCHLUSS VON PHASE 0 UND 1**

## 2.1 Starte mit Safety-Wrapper

```bash
# Installiere Safety-Utils
cp safety_utils.py scripts/
cp run_safe_pipeline.py scripts/

# Starte Pipeline mit Safety-Checks
python scripts/run_safe_pipeline.py \
  --input-dir "Input_Bucket/_GOLD_STANDARD" \
  --output-dir "output_bucket/gold_standard_qa_safe"
```

## 2.2 Nach Pipeline: Verifizierung

```bash
python scripts/verify_gold_standard_origin.py \
  --qa-file "output_bucket/gold_standard_qa_safe/generated_qa_llm.json" \
  --output "output_bucket/gold_standard_qa_safe/verification_report.json"
```

**Erfolgskriterium:** ≥90% Gold-Standard-Anteil

---

# 📋 CHECKLISTE FÜR CODEX

## Phase 0: Analyse
- [ ] `PROJEKT_ANALYSE.md` erstellt
- [ ] Alle Input-Verzeichnisse dokumentiert
- [ ] `_GOLD_STANDARD` Ordner gefunden und verifiziert
- [ ] Alle Entry-Point-Scripts identifiziert
- [ ] Bestehende Q&A-Dateien analysiert
- [ ] **ANALYSE AN USER GEPOSTET UND AUF BESTÄTIGUNG GEWARTET**

## Phase 1: Safety-System
- [ ] `safety_utils.py` erstellt
- [ ] `run_safe_pipeline.py` erstellt
- [ ] Backup-System getestet
- [ ] Checkpoint-System getestet

## Phase 2: Pipeline
- [ ] Safety-Check bestanden
- [ ] Pipeline mit korrektem Input gestartet
- [ ] Verifizierung zeigt ≥90% Gold-Standard
- [ ] RAG Enrichment für ALLE Fragen durchgeführt

---

# 🛑 ABSOLUTE REGELN

1. **NIEMALS** Pipeline starten ohne `_GOLD_STANDARD` im Input-Pfad
2. **NIEMALS** Dateien löschen ohne Backup
3. **IMMER** Analyse-Report posten bevor du handelst
4. **IMMER** auf Bestätigung warten nach kritischen Schritten
5. **STOPP** sofort bei >10% Datenverlust durch Filter

---

**START MIT PHASE 0. POSTE DEN ANALYSE-REPORT. WARTE AUF ANWEISUNGEN.**
