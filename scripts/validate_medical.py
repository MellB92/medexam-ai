#!/usr/bin/env python3
"""
MedExamAI Medical Validator Script
==================================

Validiert Q&A-Paare mit dem Medical Validation Layer.

Prüft:
- Dosierungen (gegen Referenzbereiche)
- ICD-10 Codes (Syntax, Geschlechts-Plausibilität)
- Laborwerte (Referenzbereiche, kritische Werte)
- Logische Konsistenz (Kontraindikationen, Geschlecht)

Output:
- Validierte Q&A-Paare -> _OUTPUT/validated/qa_validated.json
- Quarantäne-Liste -> _OUTPUT/validated/quarantine.json
- Validierungs-Report -> _OUTPUT/validated/validation_report.md

Autor: MedExamAI Team
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

# Parent-Verzeichnis zum Pfad hinzufügen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.medical_validator import (
    MedicalValidationLayer,
    ValidationResult,
    ValidationSeverity
)

logger = logging.getLogger(__name__)


class QAValidator:
    """Validiert Q&A-Paare mit dem Medical Validation Layer."""

    def __init__(self):
        self.validator = MedicalValidationLayer()
        self.validated: List[Dict[str, Any]] = []
        self.quarantined: List[Dict[str, Any]] = []
        self.stats = {
            "total": 0,
            "valid": 0,
            "quarantined": 0,
            "issues_by_type": {}
        }

    def validate_qa(self, qa_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validiert ein einzelnes Q&A-Paar.

        Args:
            qa_item: Q&A-Dictionary

        Returns:
            Q&A mit Validierungsergebnis
        """
        self.stats["total"] += 1

        # Text für Validierung zusammenbauen
        frage = qa_item.get("frage", "")
        antwort_parts = []

        # Antwort kann verschiedene Formate haben
        if "antwort" in qa_item:
            antwort = qa_item["antwort"]
            if isinstance(antwort, dict):
                for key, value in antwort.items():
                    if value:
                        antwort_parts.append(str(value))
            else:
                antwort_parts.append(str(antwort))
        else:
            # 5-Punkte-Schema Format
            for key in ["definition_klassifikation", "aetiologie_pathophysiologie",
                       "diagnostik", "therapie", "rechtliche_aspekte"]:
                if key in qa_item and qa_item[key]:
                    antwort_parts.append(qa_item[key])

        full_text = frage + "\n\n" + "\n\n".join(antwort_parts)

        # Patienteninfo extrahieren (falls vorhanden)
        patient_gender = None
        if "männlich" in full_text.lower() or "mann" in full_text.lower():
            patient_gender = "male"
        elif "weiblich" in full_text.lower() or "frau" in full_text.lower():
            patient_gender = "female"

        # Validierung durchführen
        result = self.validator.validate(
            text=full_text,
            patient_gender=patient_gender,
            source_file=qa_item.get("source_file")
        )

        # Issue-Typen zählen
        for issue in result.issues + result.warnings:
            issue_type = issue.code
            self.stats["issues_by_type"][issue_type] = \
                self.stats["issues_by_type"].get(issue_type, 0) + 1

        # Ergebnis hinzufügen
        qa_item["_validation"] = {
            "is_valid": result.is_valid,
            "confidence_score": result.confidence_score,
            "has_critical_issues": result.has_critical_issues,
            "has_errors": result.has_errors,
            "issues_count": len(result.issues),
            "warnings_count": len(result.warnings),
            "issues": [i.to_dict() for i in result.issues],
            "warnings": [w.to_dict() for w in result.warnings]
        }

        # Kategorisieren
        if result.has_critical_issues or result.has_errors:
            self.quarantined.append(qa_item)
            self.stats["quarantined"] += 1
        else:
            self.validated.append(qa_item)
            self.stats["valid"] += 1

        return qa_item

    def process_file(
        self,
        input_file: Path,
        progress_callback=None
    ) -> None:
        """
        Verarbeitet eine JSON-Datei mit Q&A-Paaren.

        Args:
            input_file: Pfad zur Input-JSON
            progress_callback: Optional callback(current, total)
        """
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Unterstütze verschiedene Formate
        if isinstance(data, dict) and "answers" in data:
            qa_items = data["answers"]
        elif isinstance(data, list):
            qa_items = data
        else:
            logger.error(f"Unbekanntes Format in {input_file}")
            return

        logger.info(f"Validiere {len(qa_items)} Q&A-Paare...")

        for i, item in enumerate(qa_items):
            if progress_callback:
                progress_callback(i + 1, len(qa_items))
            self.validate_qa(item)

    def save_results(
        self,
        output_dir: Path,
        include_report: bool = True
    ) -> Dict[str, Path]:
        """
        Speichert Validierungsergebnisse.

        Args:
            output_dir: Ausgabeverzeichnis
            include_report: Markdown-Report erstellen

        Returns:
            Dictionary mit Output-Pfaden
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        paths = {}

        # Validierte Q&A
        validated_file = output_dir / "qa_validated.json"
        with open(validated_file, 'w', encoding='utf-8') as f:
            json.dump({
                "validated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "count": len(self.validated),
                "items": self.validated
            }, f, ensure_ascii=False, indent=2)
        paths["validated"] = validated_file

        # Quarantäne
        if self.quarantined:
            quarantine_file = output_dir / "quarantine.json"
            with open(quarantine_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "quarantined_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "count": len(self.quarantined),
                    "items": self.quarantined
                }, f, ensure_ascii=False, indent=2)
            paths["quarantine"] = quarantine_file

        # Report
        if include_report:
            report_file = output_dir / "validation_report.md"
            self._write_report(report_file)
            paths["report"] = report_file

        return paths

    def _write_report(self, report_file: Path) -> None:
        """Schreibt Validierungs-Report."""
        lines = [
            "# Medical Validation Report",
            "",
            f"**Erstellt:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Zusammenfassung",
            "",
            f"| Metrik | Wert |",
            f"|--------|------|",
            f"| Gesamt geprüft | {self.stats['total']} |",
            f"| Validiert | {self.stats['valid']} ({self.stats['valid']*100//max(1,self.stats['total'])}%) |",
            f"| Quarantäne | {self.stats['quarantined']} ({self.stats['quarantined']*100//max(1,self.stats['total'])}%) |",
            "",
            "## Issues nach Typ",
            "",
        ]

        if self.stats["issues_by_type"]:
            lines.append("| Issue-Typ | Anzahl |")
            lines.append("|-----------|--------|")
            for issue_type, count in sorted(
                self.stats["issues_by_type"].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                lines.append(f"| {issue_type} | {count} |")
        else:
            lines.append("*Keine Issues gefunden*")

        lines.extend([
            "",
            "## Quarantäne-Einträge",
            "",
        ])

        if self.quarantined:
            for i, item in enumerate(self.quarantined[:20], 1):  # Max 20 zeigen
                frage = item.get("frage", "")[:100]
                validation = item.get("_validation", {})
                issues = validation.get("issues", [])

                lines.append(f"### {i}. {frage}...")
                lines.append("")
                lines.append(f"**Source:** {item.get('source_file', 'Unknown')}")
                lines.append(f"**Confidence:** {validation.get('confidence_score', 0):.2f}")
                lines.append("")

                if issues:
                    lines.append("**Issues:**")
                    for issue in issues[:5]:  # Max 5 Issues pro Eintrag
                        lines.append(f"- [{issue.get('severity', 'unknown').upper()}] {issue.get('message', '')}")
                lines.append("")

            if len(self.quarantined) > 20:
                lines.append(f"*... und {len(self.quarantined) - 20} weitere*")
        else:
            lines.append("*Keine Einträge in Quarantäne*")

        lines.extend([
            "",
            "## Validator-Statistiken",
            "",
            "```json",
            json.dumps(self.validator.get_statistics(), indent=2),
            "```",
            "",
            "---",
            "*Generiert von MedExamAI Medical Validation Layer*"
        ])

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        return {
            **self.stats,
            "validator_stats": self.validator.get_statistics()
        }


def load_config(path: Path) -> dict:
    """Lädt Konfiguration."""
    if not path.exists():
        raise FileNotFoundError(f"Config nicht gefunden: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML nicht installiert. Installieren mit: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validiert Q&A-Paare mit Medical Validation Layer"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config.yaml")
    )
    parser.add_argument(
        "--input",
        help="Input JSON. Default: _OUTPUT/qa_gold_standard.json"
    )
    parser.add_argument(
        "--output-dir",
        help="Output-Verzeichnis. Default: _OUTPUT/validated/"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Keinen Markdown-Report erstellen"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ausführliche Ausgabe"
    )

    args = parser.parse_args()

    # Logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Konfiguration laden
    config = load_config(Path(args.config))
    base = Path(args.config).resolve().parent

    # Pfade
    output_base = base / config.get("output_dir", "_OUTPUT")
    input_file = Path(args.input) if args.input else output_base / "qa_gold_standard.json"
    output_dir = Path(args.output_dir) if args.output_dir else output_base / "validated"

    if not input_file.exists():
        logger.error(f"Input-Datei nicht gefunden: {input_file}")
        return 1

    # Validator erstellen
    validator = QAValidator()

    # Fortschrittsanzeige
    def progress(current, total):
        print(f"\r⏳ Validiere: {current}/{total} ({current*100//total}%)", end="", flush=True)

    # Validierung durchführen
    print(f"\n🔬 Starte Medical Validation...")
    validator.process_file(input_file, progress_callback=progress)
    print()  # Newline nach Fortschritt

    # Ergebnisse speichern
    paths = validator.save_results(output_dir, include_report=not args.no_report)

    # Zusammenfassung
    stats = validator.get_statistics()
    print(f"\n✅ Validierung abgeschlossen!")
    print(f"   Geprüft: {stats['total']}")
    print(f"   Validiert: {stats['valid']} ({stats['valid']*100//max(1,stats['total'])}%)")
    print(f"   Quarantäne: {stats['quarantined']} ({stats['quarantined']*100//max(1,stats['total'])}%)")
    print(f"\n📁 Output:")
    for name, path in paths.items():
        print(f"   {name}: {path}")

    if stats["issues_by_type"]:
        print(f"\n⚠️  Top Issues:")
        for issue_type, count in sorted(
            stats["issues_by_type"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]:
            print(f"   {issue_type}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
