# 🛡️ MedExamAI: Sicherheit & Validierung

## Teil 1: Prävention (Nie wieder Datenverlust)

### 1.1 Automatische Backups VOR kritischen Operationen

```python
# In jeder Pipeline-Datei VOR Filter/Cleanup:

import shutil
from datetime import datetime

def safe_backup(filepath: str) -> str:
    """Erstellt Backup bevor Daten verändert werden."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backup erstellt: {backup_path}")
    return backup_path

def safe_filter(data: list, filter_func, name: str = "filter") -> list:
    """Filter mit Sicherheitsprüfung."""
    original_count = len(data)
    filtered = [d for d in data if filter_func(d)]
    filtered_count = len(filtered)
    
    loss_percent = (1 - filtered_count / original_count) * 100 if original_count > 0 else 0
    
    # 🚨 ALERT bei >50% Verlust
    if loss_percent > 50:
        print(f"⚠️ WARNUNG: {name} würde {loss_percent:.1f}% der Daten löschen!")
        print(f"   Original: {original_count} → Nach Filter: {filtered_count}")
        confirm = input("Fortfahren? (ja/nein): ")
        if confirm.lower() != "ja":
            raise ValueError(f"Filter abgebrochen: {loss_percent:.1f}% Datenverlust")
    
    # 🚨 STOPP bei >90% Verlust
    if loss_percent > 90:
        raise ValueError(f"🚫 KRITISCH: Filter würde {loss_percent:.1f}% löschen. Abgebrochen!")
    
    print(f"✅ {name}: {original_count} → {filtered_count} ({loss_percent:.1f}% entfernt)")
    return filtered
```

### 1.2 State-File Monitoring

```python
# state_monitor.py

import json
import os
from pathlib import Path

REQUIRED_STATE_FILES = [
    "consolidator_state.json",
    "extractor_state.json",
    "qa_extraction_progress.json"
]

def check_state_files(output_dir: str) -> dict:
    """Prüft ob alle State-Files existieren und valide sind."""
    results = {}
    
    for state_file in REQUIRED_STATE_FILES:
        path = Path(output_dir) / state_file
        
        if not path.exists():
            results[state_file] = {"status": "❌ FEHLT", "count": 0}
            continue
        
        try:
            with open(path) as f:
                data = json.load(f)
            
            # Prüfe ob Daten vorhanden
            count = len(data) if isinstance(data, list) else data.get("count", data.get("total", "?"))
            
            if count == 0:
                results[state_file] = {"status": "⚠️ LEER", "count": 0}
            else:
                results[state_file] = {"status": "✅ OK", "count": count}
                
        except json.JSONDecodeError:
            results[state_file] = {"status": "❌ KORRUPT", "count": 0}
    
    return results

def print_state_report(output_dir: str):
    """Zeigt State-File Status."""
    print("\n📊 STATE-FILE STATUS:")
    print("-" * 50)
    
    results = check_state_files(output_dir)
    
    for file, info in results.items():
        print(f"  {info['status']} {file}: {info['count']} Einträge")
    
    # Warnung wenn Probleme
    problems = [f for f, i in results.items() if "❌" in i["status"] or "⚠️" in i["status"]]
    if problems:
        print(f"\n🚨 PROBLEME: {', '.join(problems)}")
        return False
    
    print("\n✅ Alle State-Files OK")
    return True
```

### 1.3 Pre-Run Checklist (IMMER ausführen!)

```python
# pre_run_check.py

def pre_pipeline_checklist(config: dict) -> bool:
    """
    MUSS vor jedem Pipeline-Run ausgeführt werden!
    Aus Memory: "IMMER vor Pipeline-Runs Checkpoint-Pfade UND Output-Pfade EXPLIZIT bestätigen"
    """
    
    print("\n" + "="*60)
    print("🔍 PRE-RUN CHECKLIST")
    print("="*60)
    
    checks = []
    
    # 1. Pfade bestätigen
    print(f"\n📁 INPUT:  {config['input_path']}")
    print(f"📁 OUTPUT: {config['output_path']}")
    print(f"📁 BACKUP: {config['backup_path']}")
    
    confirm = input("\nSind diese Pfade korrekt? (ja/nein): ")
    checks.append(("Pfade bestätigt", confirm.lower() == "ja"))
    
    # 2. Backup existiert
    backup_exists = os.path.exists(config['backup_path'])
    checks.append(("Backup-Ordner existiert", backup_exists))
    
    # 3. State-Files prüfen
    state_ok = print_state_report(config['output_path'])
    checks.append(("State-Files OK", state_ok))
    
    # 4. Freier Speicherplatz
    import shutil
    total, used, free = shutil.disk_usage(config['output_path'])
    free_gb = free // (2**30)
    checks.append((f"Speicherplatz ({free_gb} GB frei)", free_gb > 5))
    
    # 5. Letzte Backup-Zeit
    # ... (optional)
    
    # Ergebnis
    print("\n" + "-"*60)
    print("CHECKLIST ERGEBNIS:")
    all_ok = True
    for name, ok in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")
        if not ok:
            all_ok = False
    
    if not all_ok:
        print("\n🚫 CHECKLIST FEHLGESCHLAGEN - Pipeline wird NICHT gestartet!")
        return False
    
    print("\n✅ Alle Checks bestanden - Pipeline kann starten")
    return True
```

---

## Teil 2: Input vs Output Validierung

### 2.1 Input-Output Mapping

```python
# validation/input_output_validator.py

import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

class InputOutputValidator:
    """
    Vergleicht Input-Bucket (Leitlinien) mit Output (Q&A pairs)
    um sicherzustellen, dass MedExamAI korrekt funktioniert.
    """
    
    def __init__(self, input_dir: str, output_file: str):
        self.input_dir = Path(input_dir)
        self.output_file = Path(output_file)
        
    def get_input_inventory(self) -> Dict[str, dict]:
        """Inventar aller Input-Dateien (Leitlinien)."""
        inventory = {}
        
        for ext in ["*.pdf", "*.docx", "*.txt", "*.md"]:
            for file in self.input_dir.rglob(ext):
                inventory[file.name] = {
                    "path": str(file),
                    "size_kb": file.stat().st_size // 1024,
                    "type": file.suffix
                }
        
        return inventory
    
    def get_output_by_source(self) -> Dict[str, List[dict]]:
        """Gruppiert Output Q&A pairs nach Quelldatei."""
        with open(self.output_file) as f:
            qa_pairs = json.load(f)
        
        by_source = defaultdict(list)
        
        for qa in qa_pairs:
            # Versuche Quelle zu extrahieren
            source = qa.get("source") or qa.get("quelle") or qa.get("metadata", {}).get("source") or "UNBEKANNT"
            by_source[source].append(qa)
        
        return dict(by_source)
    
    def validate(self) -> dict:
        """
        Hauptvalidierung: Input vs Output
        
        Returns:
            {
                "summary": {...},
                "coverage": {...},
                "issues": [...],
                "recommendations": [...]
            }
        """
        inputs = self.get_input_inventory()
        outputs = self.get_output_by_source()
        
        report = {
            "summary": {
                "input_files": len(inputs),
                "output_qa_pairs": sum(len(v) for v in outputs.values()),
                "unique_sources": len(outputs)
            },
            "coverage": {},
            "issues": [],
            "recommendations": []
        }
        
        # Coverage-Analyse
        for input_file in inputs:
            # Suche passende Outputs
            matching_outputs = []
            for source, qa_list in outputs.items():
                if input_file.lower() in source.lower() or source.lower() in input_file.lower():
                    matching_outputs.extend(qa_list)
            
            qa_count = len(matching_outputs)
            input_size = inputs[input_file]["size_kb"]
            
            # Erwartete Q&A pro KB (Heuristik: ~1-2 Q&A pro 10 KB)
            expected_min = input_size // 20
            expected_max = input_size // 5
            
            status = "✅ OK"
            if qa_count == 0:
                status = "❌ KEINE Q&A"
                report["issues"].append(f"Keine Q&A für: {input_file}")
            elif qa_count < expected_min:
                status = "⚠️ WENIG"
                report["issues"].append(f"Wenig Q&A für {input_file}: {qa_count} (erwartet: {expected_min}-{expected_max})")
            
            report["coverage"][input_file] = {
                "qa_count": qa_count,
                "expected_range": f"{expected_min}-{expected_max}",
                "status": status
            }
        
        # Unbekannte Quellen
        known_inputs = set(f.lower() for f in inputs.keys())
        for source in outputs:
            if source != "UNBEKANNT" and not any(inp in source.lower() for inp in known_inputs):
                report["issues"].append(f"Unbekannte Quelle in Output: {source}")
        
        # Empfehlungen
        if report["issues"]:
            report["recommendations"].append("Überprüfe Quellenangaben in der Pipeline")
            report["recommendations"].append("Führe Re-Processing für fehlende Leitlinien durch")
        
        return report
    
    def print_report(self):
        """Zeigt Validierungsbericht."""
        report = self.validate()
        
        print("\n" + "="*70)
        print("📊 INPUT/OUTPUT VALIDIERUNGSBERICHT")
        print("="*70)
        
        # Summary
        s = report["summary"]
        print(f"\n📁 Input-Dateien:     {s['input_files']}")
        print(f"📝 Output Q&A pairs:  {s['output_qa_pairs']}")
        print(f"🔗 Unique Sources:    {s['unique_sources']}")
        
        # Coverage
        print(f"\n{'─'*70}")
        print("COVERAGE PRO LEITLINIE:")
        print(f"{'─'*70}")
        print(f"{'Datei':<40} {'Q&A':<8} {'Erwartet':<12} {'Status':<10}")
        print(f"{'─'*70}")
        
        for file, data in report["coverage"].items():
            print(f"{file[:38]:<40} {data['qa_count']:<8} {data['expected_range']:<12} {data['status']:<10}")
        
        # Issues
        if report["issues"]:
            print(f"\n{'─'*70}")
            print("⚠️ PROBLEME:")
            for issue in report["issues"]:
                print(f"  • {issue}")
        
        # Recommendations
        if report["recommendations"]:
            print(f"\n💡 EMPFEHLUNGEN:")
            for rec in report["recommendations"]:
                print(f"  • {rec}")
        
        # Final Status
        print(f"\n{'='*70}")
        if not report["issues"]:
            print("✅ VALIDIERUNG BESTANDEN - MedExamAI funktioniert korrekt!")
        else:
            print(f"⚠️ {len(report['issues'])} Probleme gefunden - Überprüfung erforderlich")
        print(f"{'='*70}\n")
        
        return report
```

### 2.2 Schnell-Validierung (CLI)

```bash
#!/bin/bash
# validate_medexamai.sh

INPUT_BUCKET="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_BUCKET" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: ./validate_medexamai.sh <input_bucket_path> <output_qa_file>"
    exit 1
fi

echo "🔍 MedExamAI Validierung"
echo "========================"

# 1. Input zählen
INPUT_COUNT=$(find "$INPUT_BUCKET" -type f \( -name "*.pdf" -o -name "*.docx" \) | wc -l)
echo "📁 Input-Dateien: $INPUT_COUNT"

# 2. Output zählen
if [ -f "$OUTPUT_FILE" ]; then
    OUTPUT_COUNT=$(python3 -c "import json; print(len(json.load(open('$OUTPUT_FILE'))))")
    echo "📝 Output Q&A: $OUTPUT_COUNT"
else
    echo "❌ Output-Datei nicht gefunden: $OUTPUT_FILE"
    exit 1
fi

# 3. Ratio berechnen
RATIO=$(echo "scale=2; $OUTPUT_COUNT / $INPUT_COUNT" | bc)
echo "📊 Ratio Q&A/Input: $RATIO"

# 4. Bewertung
if (( $(echo "$RATIO < 10" | bc -l) )); then
    echo "⚠️ WARNUNG: Weniger als 10 Q&A pro Input-Datei"
elif (( $(echo "$RATIO > 100" | bc -l) )); then
    echo "⚠️ WARNUNG: Mehr als 100 Q&A pro Input-Datei (evtl. Duplikate?)"
else
    echo "✅ Ratio im erwarteten Bereich (10-100 Q&A pro Datei)"
fi
```

### 2.3 Qualitäts-Stichprobe

```python
# validation/quality_sample.py

import json
import random

def quality_sample_check(output_file: str, sample_size: int = 10) -> dict:
    """
    Prüft Stichprobe auf Prüfungsformat-Konformität.
    """
    with open(output_file) as f:
        qa_pairs = json.load(f)
    
    sample = random.sample(qa_pairs, min(sample_size, len(qa_pairs)))
    
    results = {
        "total_checked": len(sample),
        "format_issues": [],
        "missing_fields": defaultdict(int),
        "quality_scores": []
    }
    
    REQUIRED_FIELDS = {
        "frage": ["question", "frage", "text"],
        "antwort": ["answer", "antwort", "response"],
        "quelle": ["source", "quelle", "reference"]
    }
    
    QUALITY_CHECKS = {
        "hat_definition": lambda a: "definition" in a.lower() or "ist ein" in a.lower(),
        "hat_dosierung": lambda a: "mg" in a or "g/d" in a or "ml" in a,
        "hat_klassifikation": lambda a: "klassifikation" in a.lower() or "nach " in a.lower(),
        "hat_therapie": lambda a: "therapie" in a.lower() or "behandlung" in a.lower(),
    }
    
    for i, qa in enumerate(sample):
        # Feld-Prüfung
        for field_name, alternatives in REQUIRED_FIELDS.items():
            found = any(alt in qa for alt in alternatives)
            if not found:
                results["missing_fields"][field_name] += 1
        
        # Qualitäts-Prüfung
        answer = str(qa.get("answer", qa.get("antwort", "")))
        score = sum(1 for check, func in QUALITY_CHECKS.items() if func(answer))
        results["quality_scores"].append(score)
        
        if score < 2:
            results["format_issues"].append({
                "index": i,
                "frage": str(qa.get("question", qa.get("frage", "")))[:50],
                "score": score,
                "issue": "Weniger als 2 Qualitätskriterien erfüllt"
            })
    
    # Zusammenfassung
    avg_score = sum(results["quality_scores"]) / len(results["quality_scores"])
    results["average_quality"] = round(avg_score, 2)
    results["max_quality"] = max(results["quality_scores"])
    
    return results
```

---

## Teil 3: Automatisierungs-Setup

### 3.1 GitHub Action: Validierung bei jedem Push

```yaml
# .github/workflows/validate-qa-output.yml
name: Validate Q&A Output

on:
  push:
    paths:
      - 'output/*.json'
      - 'exports/*.json'
  pull_request:
    paths:
      - 'output/*.json'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run validation
        run: |
          python validation/input_output_validator.py \
            --input ./input_bucket \
            --output ./output/qa_enhanced_quality.json
      
      - name: Check quality sample
        run: |
          python validation/quality_sample.py \
            --file ./output/qa_enhanced_quality.json \
            --sample 20
      
      - name: Create Jira ticket on failure
        if: failure()
        env:
          JIRA_TOKEN: ${{ secrets.JIRA_TOKEN }}
        run: |
          curl -X POST "https://xcorpiodbs.atlassian.net/rest/api/3/issue" \
            -H "Authorization: Basic $JIRA_TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"fields":{"project":{"key":"KAN"},"summary":"🚨 Q&A Validierung fehlgeschlagen","issuetype":{"name":"Bug"}}}'
```

### 3.2 Jira Automation Rule

```json
{
  "name": "Alert on Data Loss",
  "trigger": {
    "type": "label_added",
    "label": "data-loss"
  },
  "actions": [
    {
      "type": "set_priority",
      "priority": "Highest"
    },
    {
      "type": "add_watchers",
      "watchers": ["admin"]
    },
    {
      "type": "send_notification",
      "channel": "email",
      "recipients": ["xcorpiodbs@gmail.com"]
    }
  ]
}
```

---

## Checkliste: Nach jedem Pipeline-Run

- [ ] `pre_pipeline_checklist()` vor Start ausführen
- [ ] State-Files nach Run prüfen
- [ ] Input/Output Validierung durchführen
- [ ] Stichproben-Qualitätsprüfung
- [ ] Backup erstellt und verifiziert
- [ ] Jira-Ticket mit Ergebnis kommentieren
