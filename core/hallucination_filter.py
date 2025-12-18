#!/usr/bin/env python3
"""
Halluzinations-Filter für medizinische Texte.

Erkennt und entfernt:
1. Unsichere Formulierungen ("möglicherweise", "ich vermute")
2. KI-Selbstreferenzen ("als KI-Modell", "basierend auf meinem Training")
3. Wissenslücken-Eingeständnisse ("ich weiß nicht", "keine Informationen")
4. Vage Antworten (nur Stichworte ohne Inhalt)

Kann verwendet werden für:
- Bereinigung bestehender Daten
- Validierung neuer LLM-Antworten
- Qualitätskontrolle im RAG-System
"""

import re
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class HallucinationType(Enum):
    """Typen von Halluzinationen/Qualitätsproblemen"""
    UNCERTAINTY = "uncertainty"           # Unsichere Formulierungen
    AI_REFERENCE = "ai_reference"         # KI-Selbstreferenzen
    KNOWLEDGE_GAP = "knowledge_gap"       # Wissenslücken
    VAGUE_ANSWER = "vague_answer"         # Vage Antworten
    SPECULATION = "speculation"           # Spekulation
    HEDGING = "hedging"                   # Abschwächende Sprache


@dataclass
class HallucinationMatch:
    """Gefundene Halluzination"""
    type: HallucinationType
    pattern: str
    text: str
    start: int
    end: int
    severity: str  # "high", "medium", "low"


# Halluzinations-Pattern mit Schweregrad
HALLUCINATION_PATTERNS: Dict[HallucinationType, List[Tuple[str, str]]] = {
    HallucinationType.UNCERTAINTY: [
        (r'möglicherweise', 'medium'),
        (r'wahrscheinlich(?! ist)', 'low'),  # "wahrscheinlich ist" ok für Diagnosen
        (r'vermutlich', 'medium'),
        (r'eventuell', 'low'),
        (r'ich (bin mir )?(nicht )?sicher', 'high'),
        (r'es könnte (sein|sich handeln)', 'medium'),
        (r'es ist (nicht )?klar', 'medium'),
    ],
    HallucinationType.AI_REFERENCE: [
        (r'als ki(-| )?modell', 'high'),
        (r'basierend auf meinem training', 'high'),
        (r'mein(e)? wissen(sbasis)?', 'high'),
        (r'ich wurde trainiert', 'high'),
        (r'in meinen trainingsdaten', 'high'),
        (r'als sprachmodell', 'high'),
        (r'ich bin ein(e)? (ki|künstliche intelligenz)', 'high'),
    ],
    HallucinationType.KNOWLEDGE_GAP: [
        (r'ich (habe |besitze )?(keine|wenig) informationen', 'high'),
        (r'ich (weiß|kenne) (das |es )?(leider )?(nicht|nichts)', 'high'),
        (r'das (ist |liegt )?(außerhalb|jenseits) meines wissens', 'high'),
        (r'ich kann (das |diese frage )?(leider )?(nicht|keine) beantworten', 'high'),
        (r'dazu (habe ich |fehlen mir )?(keine )?(informationen|daten)', 'high'),
        (r'mir (sind |ist )(keine |kein )?.*bekannt', 'medium'),
    ],
    HallucinationType.SPECULATION: [
        (r'ich vermute', 'high'),
        (r'ich nehme an', 'medium'),
        (r'ich glaube(?!,? dass)', 'medium'),  # "ich glaube, dass X" ist ok
        (r'ich denke(?!,? dass)', 'medium'),
        (r'es scheint( mir)?', 'low'),
        (r'anscheinend', 'low'),
    ],
    HallucinationType.HEDGING: [
        (r'im allgemeinen', 'low'),
        (r'in der regel', 'low'),
        (r'normalerweise', 'low'),
        (r'typischerweise', 'low'),
        (r'häufig(?! gestellte)', 'low'),  # "häufig gestellte Fragen" ok
        (r'meistens', 'low'),
        (r'oft(?!mals)', 'low'),
    ],
}

# Vage Antwort-Muster (nur Stichworte)
VAGUE_ANSWER_PATTERNS = [
    r'^[-•*]\s*\w+:\s*Definition,\s*(?:Ursachen|Ätiologie),\s*(?:Diagnostik|Diagnose),\s*Therapie\s*$',
    r'^[-•*]\s*\w+:\s*Definition,\s*Pathophysiologie,\s*Diagnostik,\s*Therapie\s*$',
    r'^[-•*]\s*(?:Definition|Ätiologie|Diagnostik|Therapie)\s*$',
]


class HallucinationFilter:
    """Filter für Halluzinationen in medizinischen Texten"""

    def __init__(self,
                 severity_threshold: str = "medium",
                 remove_sentences: bool = True,
                 preserve_medical_terms: bool = True):
        """
        Args:
            severity_threshold: Minimaler Schweregrad zum Entfernen ("low", "medium", "high")
            remove_sentences: Ganze Sätze entfernen statt nur Wörter
            preserve_medical_terms: Medizinische Fachbegriffe schützen
        """
        self.severity_threshold = severity_threshold
        self.remove_sentences = remove_sentences
        self.preserve_medical_terms = preserve_medical_terms

        # Severity-Rangfolge
        self.severity_rank = {"low": 1, "medium": 2, "high": 3}

        # Kompiliere Pattern
        self._compile_patterns()

    def _compile_patterns(self):
        """Kompiliert alle Regex-Pattern"""
        self.compiled_patterns: Dict[HallucinationType, List[Tuple[re.Pattern, str]]] = {}

        for h_type, patterns in HALLUCINATION_PATTERNS.items():
            self.compiled_patterns[h_type] = [
                (re.compile(pattern, re.IGNORECASE), severity)
                for pattern, severity in patterns
            ]

        self.vague_patterns = [
            re.compile(p, re.MULTILINE | re.IGNORECASE)
            for p in VAGUE_ANSWER_PATTERNS
        ]

    def detect(self, text: str) -> List[HallucinationMatch]:
        """
        Erkennt Halluzinationen im Text.

        Returns:
            Liste von HallucinationMatch Objekten
        """
        matches = []

        for h_type, patterns in self.compiled_patterns.items():
            for pattern, severity in patterns:
                for match in pattern.finditer(text):
                    matches.append(HallucinationMatch(
                        type=h_type,
                        pattern=pattern.pattern,
                        text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        severity=severity,
                    ))

        # Prüfe auf vage Antworten
        for pattern in self.vague_patterns:
            for match in pattern.finditer(text):
                matches.append(HallucinationMatch(
                    type=HallucinationType.VAGUE_ANSWER,
                    pattern=pattern.pattern,
                    text=match.group(),
                    start=match.start(),
                    end=match.end(),
                    severity="medium",
                ))

        return matches

    def filter(self, text: str) -> Tuple[str, List[HallucinationMatch]]:
        """
        Entfernt Halluzinationen aus dem Text.

        Returns:
            Tuple von (bereinigter_text, gefundene_halluzinationen)
        """
        matches = self.detect(text)

        # Filtere nach Schweregrad
        threshold_rank = self.severity_rank[self.severity_threshold]
        relevant_matches = [
            m for m in matches
            if self.severity_rank[m.severity] >= threshold_rank
        ]

        if not relevant_matches:
            return text, matches

        # Sortiere nach Position (rückwärts für sichere Entfernung)
        relevant_matches.sort(key=lambda m: m.start, reverse=True)

        cleaned_text = text

        for match in relevant_matches:
            if self.remove_sentences:
                # Entferne ganzen Satz
                sentence_start = self._find_sentence_start(cleaned_text, match.start)
                sentence_end = self._find_sentence_end(cleaned_text, match.end)
                cleaned_text = cleaned_text[:sentence_start] + cleaned_text[sentence_end:]
            else:
                # Entferne nur das Match
                cleaned_text = cleaned_text[:match.start] + cleaned_text[match.end:]

        # Bereinige mehrfache Leerzeichen/Zeilenumbrüche
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()

        return cleaned_text, matches

    def _find_sentence_start(self, text: str, pos: int) -> int:
        """Findet den Anfang des Satzes"""
        # Suche rückwärts nach Satzende oder Zeilenanfang
        sentence_ends = '.!?\n'
        i = pos - 1
        while i >= 0 and text[i] not in sentence_ends:
            i -= 1
        return i + 1

    def _find_sentence_end(self, text: str, pos: int) -> int:
        """Findet das Ende des Satzes"""
        sentence_ends = '.!?\n'
        i = pos
        while i < len(text) and text[i] not in sentence_ends:
            i += 1
        # Inkludiere das Satzzeichen
        if i < len(text):
            i += 1
        return i

    def get_quality_score(self, text: str) -> float:
        """
        Berechnet Qualitäts-Score (0-1, höher = besser).

        Returns:
            Score zwischen 0 und 1
        """
        matches = self.detect(text)

        if not matches:
            return 1.0

        # Gewichte nach Schweregrad
        penalty = 0.0
        for match in matches:
            if match.severity == "high":
                penalty += 0.2
            elif match.severity == "medium":
                penalty += 0.1
            else:  # low
                penalty += 0.05

        return max(0.0, 1.0 - penalty)

    def validate_answer(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Validiert eine LLM-Antwort auf Halluzinationen.

        Returns:
            Dict mit Validierungsergebnis
        """
        matches = self.detect(answer)
        quality_score = self.get_quality_score(answer)

        # Kategorisiere nach Typ
        by_type = {}
        for match in matches:
            type_name = match.type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append({
                "text": match.text,
                "severity": match.severity,
            })

        return {
            "is_valid": quality_score >= 0.7,
            "quality_score": quality_score,
            "hallucination_count": len(matches),
            "hallucinations_by_type": by_type,
            "recommendation": self._get_recommendation(quality_score, matches),
        }

    def _get_recommendation(self, score: float, matches: List[HallucinationMatch]) -> str:
        """Generiert Empfehlung basierend auf Analyse"""
        if score >= 0.9:
            return "Antwort ist von hoher Qualität."
        elif score >= 0.7:
            return "Antwort ist akzeptabel, aber enthält einige unsichere Formulierungen."
        elif score >= 0.5:
            return "Antwort sollte überarbeitet werden - zu viele Unsicherheiten."
        else:
            return "Antwort enthält zu viele Halluzinationen - neu generieren empfohlen."


def clean_file(filepath: str, output_path: Optional[str] = None,
               severity: str = "medium") -> Dict[str, Any]:
    """
    Bereinigt eine Datei von Halluzinationen.

    Args:
        filepath: Pfad zur Eingabedatei
        output_path: Pfad für bereinigte Ausgabe (optional)
        severity: Schwellenwert für Entfernung

    Returns:
        Dict mit Statistiken
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    filter_instance = HallucinationFilter(severity_threshold=severity)
    cleaned, matches = filter_instance.filter(content)

    stats = {
        "original_length": len(content),
        "cleaned_length": len(cleaned),
        "removed_chars": len(content) - len(cleaned),
        "hallucinations_found": len(matches),
        "by_type": {},
        "by_severity": {"high": 0, "medium": 0, "low": 0},
    }

    for match in matches:
        type_name = match.type.value
        stats["by_type"][type_name] = stats["by_type"].get(type_name, 0) + 1
        stats["by_severity"][match.severity] += 1

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned)

    return stats, cleaned


# CLI Interface
if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Halluzinations-Filter für medizinische Texte")
    parser.add_argument("input", type=Path, help="Eingabedatei oder -verzeichnis")
    parser.add_argument("--output", "-o", type=Path, help="Ausgabeverzeichnis")
    parser.add_argument("--severity", "-s", choices=["low", "medium", "high"],
                        default="medium", help="Schwellenwert")
    parser.add_argument("--report", "-r", action="store_true", help="Generiere Bericht")

    args = parser.parse_args()

    if args.input.is_file():
        files = [args.input]
    else:
        files = list(args.input.glob("*.md")) + list(args.input.glob("*.txt"))

    total_stats = {
        "files_processed": 0,
        "total_hallucinations": 0,
        "files_with_issues": [],
    }

    for filepath in files:
        print(f"Verarbeite: {filepath.name}")

        output_path = None
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            output_path = args.output / filepath.name

        stats, _ = clean_file(str(filepath), str(output_path) if output_path else None, args.severity)

        total_stats["files_processed"] += 1
        total_stats["total_hallucinations"] += stats["hallucinations_found"]

        if stats["hallucinations_found"] > 0:
            total_stats["files_with_issues"].append({
                "file": filepath.name,
                "count": stats["hallucinations_found"],
                "by_severity": stats["by_severity"],
            })

        print(f"  → {stats['hallucinations_found']} Halluzinationen entfernt")

    print()
    print(f"Gesamt: {total_stats['files_processed']} Dateien verarbeitet")
    print(f"Halluzinationen entfernt: {total_stats['total_hallucinations']}")

    if args.report:
        report_path = (args.output or Path(".")) / "hallucination_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(total_stats, f, ensure_ascii=False, indent=2)
        print(f"Bericht gespeichert: {report_path}")
