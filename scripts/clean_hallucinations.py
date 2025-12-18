#!/usr/bin/env python3
"""
Saubere Halluzinations-Entfernung für LLM_ARCHIVE.

Prinzip:
- ERKENNEN von Halluzinationen (Pattern-basiert)
- VERIFIZIEREN gegen Perplexity/RAG (nur Prüfung!)
- ENTFERNEN von Falschem (KEINE LLM-Generierung!)
- MARKIEREN von Unsicherem für manuelle Prüfung

Kein Chaos durch LLM-generierte Ersetzungen.
"""

import json
import re
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, asdict

# Füge Projektpfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class HallucinationReport:
    """Bericht über gefundene Halluzination"""
    text: str
    type: str
    severity: str
    line_number: int
    action: str  # "removed", "flagged", "kept"
    reason: str


# Halluzinations-Pattern
HALLUCINATION_PATTERNS = {
    "uncertainty": [
        (r'möglicherweise', 'medium'),
        (r'vermutlich', 'medium'),
        (r'ich (bin mir )?(nicht )?sicher', 'high'),
        (r'es könnte (sein|sich handeln)', 'medium'),
        (r'eventuell', 'low'),
    ],
    "ai_reference": [
        (r'als ki(-| )?modell', 'high'),
        (r'basierend auf meinem training', 'high'),
        (r'mein(e)? wissen(sbasis)?', 'high'),
        (r'ich wurde trainiert', 'high'),
        (r'als sprachmodell', 'high'),
    ],
    "knowledge_gap": [
        (r'ich (habe |besitze )?(keine|wenig) informationen', 'high'),
        (r'ich (weiß|kenne) (das |es )?(leider )?(nicht|nichts)', 'high'),
        (r'das (ist |liegt )?(außerhalb|jenseits) meines wissens', 'high'),
        (r'ich kann (das |diese frage )?(leider )?(nicht|keine) beantworten', 'high'),
    ],
    "speculation": [
        (r'ich vermute', 'high'),
        (r'ich nehme an', 'medium'),
        (r'ich glaube(?!,? dass)', 'medium'),
        (r'ich denke(?!,? dass)', 'medium'),
    ],
}

# Vage Antworten (nur Stichworte ohne Inhalt)
VAGUE_PATTERNS = [
    r'^[-•*]\s*\w+:\s*Definition,\s*(?:Ursachen|Ätiologie),\s*(?:Diagnostik|Diagnose),\s*Therapie\s*$',
    r'^[-•*]\s*\w+:\s*Definition,\s*Pathophysiologie,\s*Diagnostik,\s*Therapie\s*$',
]


class HallucinationCleaner:
    """Bereinigt Halluzinationen durch Entfernung (nicht Ersetzung)"""

    def __init__(self, severity_threshold: str = "medium"):
        """
        Args:
            severity_threshold: Minimaler Schweregrad zum Entfernen
                              "low" = alles entfernen
                              "medium" = medium + high entfernen
                              "high" = nur high entfernen
        """
        self.severity_threshold = severity_threshold
        self.severity_rank = {"low": 1, "medium": 2, "high": 3}
        self._compile_patterns()

    def _compile_patterns(self):
        """Kompiliert Regex-Pattern"""
        self.patterns = {}
        for h_type, patterns in HALLUCINATION_PATTERNS.items():
            self.patterns[h_type] = [
                (re.compile(p, re.IGNORECASE), s) for p, s in patterns
            ]

        self.vague_patterns = [
            re.compile(p, re.MULTILINE | re.IGNORECASE) for p in VAGUE_PATTERNS
        ]

    def find_hallucinations(self, text: str) -> List[Dict]:
        """Findet alle Halluzinationen im Text"""
        found = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            for h_type, patterns in self.patterns.items():
                for pattern, severity in patterns:
                    for match in pattern.finditer(line):
                        found.append({
                            "text": match.group(),
                            "type": h_type,
                            "severity": severity,
                            "line": line_num,
                            "line_content": line.strip(),
                            "start": match.start(),
                            "end": match.end(),
                        })

            # Prüfe auf vage Antworten
            for pattern in self.vague_patterns:
                if pattern.match(line):
                    found.append({
                        "text": line.strip(),
                        "type": "vague_answer",
                        "severity": "medium",
                        "line": line_num,
                        "line_content": line.strip(),
                        "start": 0,
                        "end": len(line),
                    })

        return found

    def clean_text(self, text: str) -> Tuple[str, List[HallucinationReport]]:
        """
        Entfernt Halluzinationen aus dem Text.

        Returns:
            (bereinigter_text, liste_von_reports)
        """
        hallucinations = self.find_hallucinations(text)
        threshold = self.severity_rank[self.severity_threshold]

        reports = []
        lines = text.split('\n')
        lines_to_remove = set()

        for h in hallucinations:
            severity_rank = self.severity_rank[h["severity"]]

            if severity_rank >= threshold:
                # Markiere Zeile zum Entfernen
                lines_to_remove.add(h["line"] - 1)  # 0-indexed
                action = "removed"
                reason = f"Halluzination ({h['type']}, {h['severity']})"
            else:
                action = "flagged"
                reason = f"Niedrige Priorität ({h['severity']})"

            reports.append(HallucinationReport(
                text=h["text"],
                type=h["type"],
                severity=h["severity"],
                line_number=h["line"],
                action=action,
                reason=reason,
            ))

        # Entferne markierte Zeilen
        cleaned_lines = [
            line for i, line in enumerate(lines)
            if i not in lines_to_remove
        ]

        # Bereinige mehrfache Leerzeilen
        cleaned_text = '\n'.join(cleaned_lines)
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)

        return cleaned_text.strip(), reports

    def process_file(self, filepath: Path, output_path: Optional[Path] = None) -> Dict:
        """
        Verarbeitet eine Datei.

        Returns:
            Dict mit Statistiken
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        cleaned, reports = self.clean_text(content)

        stats = {
            "file": filepath.name,
            "original_lines": len(content.split('\n')),
            "cleaned_lines": len(cleaned.split('\n')),
            "hallucinations_found": len(reports),
            "removed": sum(1 for r in reports if r.action == "removed"),
            "flagged": sum(1 for r in reports if r.action == "flagged"),
            "by_type": {},
            "by_severity": {"high": 0, "medium": 0, "low": 0},
            "reports": [asdict(r) for r in reports],
        }

        for report in reports:
            stats["by_type"][report.type] = stats["by_type"].get(report.type, 0) + 1
            stats["by_severity"][report.severity] += 1

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned)

        return stats, cleaned


def process_llm_archive(input_dir: Path, output_dir: Path,
                        severity: str = "medium") -> Dict:
    """
    Verarbeitet alle LLM_ARCHIVE Dateien.
    """
    cleaner = HallucinationCleaner(severity_threshold=severity)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_stats = {
        "timestamp": datetime.now().isoformat(),
        "severity_threshold": severity,
        "files_processed": 0,
        "total_hallucinations": 0,
        "total_removed": 0,
        "total_flagged": 0,
        "files": [],
    }

    # Finde alle MD-Dateien (ohne .md.md Duplikate)
    files = sorted([
        f for f in input_dir.glob("*.md")
        if not f.name.endswith(".md.md")
    ])

    print(f"Verarbeite {len(files)} Dateien...")
    print()

    for filepath in files:
        output_path = output_dir / filepath.name
        stats, _ = cleaner.process_file(filepath, output_path)

        total_stats["files_processed"] += 1
        total_stats["total_hallucinations"] += stats["hallucinations_found"]
        total_stats["total_removed"] += stats["removed"]
        total_stats["total_flagged"] += stats["flagged"]

        # Kurze Zusammenfassung ohne Details
        file_summary = {
            "name": stats["file"],
            "hallucinations": stats["hallucinations_found"],
            "removed": stats["removed"],
            "flagged": stats["flagged"],
        }
        total_stats["files"].append(file_summary)

        # Status ausgeben
        status = "✅" if stats["hallucinations_found"] == 0 else "🔧"
        print(f"  {status} {filepath.name}: {stats['removed']} entfernt, {stats['flagged']} markiert")

    return total_stats


def main():
    print("=" * 60)
    print("HALLUZINATIONS-BEREINIGUNG")
    print("=" * 60)
    print()
    print("Prinzip: ENTFERNEN, nicht Ersetzen!")
    print("Keine LLM-Generierung von neuem Inhalt.")
    print()

    input_dir = Path("_LLM_ARCHIVE")
    output_dir = Path("_LLM_ARCHIVE_CLEAN")

    if not input_dir.exists():
        print(f"❌ Verzeichnis nicht gefunden: {input_dir}")
        return 1

    # Verarbeite mit medium threshold (entfernt medium + high)
    stats = process_llm_archive(input_dir, output_dir, severity="medium")

    # Speichere Report
    report_path = output_dir / "_CLEANING_REPORT.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Verarbeitete Dateien:  {stats['files_processed']}")
    print(f"Halluzinationen:       {stats['total_hallucinations']}")
    print(f"  - Entfernt:          {stats['total_removed']}")
    print(f"  - Markiert:          {stats['total_flagged']}")
    print()
    print(f"Bereinigte Dateien:    {output_dir}/")
    print(f"Report:                {report_path}")

    # Zeige problematische Dateien
    problem_files = [f for f in stats["files"] if f["hallucinations"] > 0]
    if problem_files:
        print()
        print("DATEIEN MIT HALLUZINATIONEN:")
        for f in sorted(problem_files, key=lambda x: -x["removed"])[:10]:
            print(f"  {f['name']}: {f['removed']} entfernt")

    return 0


if __name__ == "__main__":
    sys.exit(main())
