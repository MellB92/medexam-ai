#!/usr/bin/env python3
"""
Content Classifier für MedExamAI
===============================

Klassifiziert medizinische Inhalte automatisch:
- Krankheitsbilder/Klinische Fälle → Strukturiertes Prüfungsformat
- Andere Themen (Ethik, Recht, Organisation) → Flexibles Format

Verwendet:
- Keyword-basierte Klassifikation
- Kontextanalyse
- ML-basierte Pattern-Erkennung (optional)
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class ContentType(Enum):
    """Typen medizinischer Inhalte"""

    DISEASE = "disease"  # Krankheitsbild/Klinischer Fall
    ETHICS = "ethics"  # Medizinethik
    LAW = "law"  # Recht/Medizinrecht
    ORGANIZATION = "organization"  # Organisation/Prozesse
    DIAGNOSIS = "diagnosis"  # Diagnostik
    THERAPY = "therapy"  # Therapie
    PREVENTION = "prevention"  # Prävention
    OTHER = "other"  # Sonstiges


@dataclass
class ClassificationResult:
    """Ergebnis der Klassifikation"""

    content_type: ContentType
    confidence: float
    indicators: List[str]  # Welche Keywords/Patterns gefunden wurden
    requires_structured_format: bool  # True = Prüfungsformat erforderlich
    suggested_template: str  # Template-Name


class MedicalContentClassifier:
    """
    Klassifiziert medizinische Inhalte basierend auf Keywords und Patterns.
    """

    def __init__(self):
        # Keywords für Krankheitsbilder (erfordern strukturiertes Format)
        self.disease_keywords = {
            # Symptome
            "symptome",
            "symptom",
            "beschwerden",
            "schmerzen",
            "fieber",
            "husten",
            "atemnot",
            "dyspnoe",
            "thoraxschmerz",
            "bauchschmerz",
            "kopfschmerz",
            # Diagnostik
            "diagnose",
            "diagnostik",
            "differentialdiagnose",
            "dd",
            "ddx",
            "labor",
            "bildgebung",
            "sonographie",
            "ct",
            "mrt",
            "röntgen",
            "ekg",
            "echo",
            "endoskopie",
            # Therapie
            "therapie",
            "behandlung",
            "medikation",
            "operation",
            "op",
            "intervention",
            "chemotherapie",
            "strahlentherapie",
            # Pathophysiologie
            "pathophysiologie",
            "pathogenese",
            "ätiologie",
            "ursache",
            "mechanismus",
            "entwicklung",
            # Klassifikationen
            "klassifikation",
            "staging",
            "grading",
            "schweregrad",
            "nyha",
            "child-pugh",
            "webber",
            "fontaine",
            "asa",
            # Krankheitsnamen (Beispiele)
            "infarkt",
            "insuffizienz",
            "krebs",
            "tumor",
            "fraktur",
            "pneumonie",
            "sepsis",
            "diabetes",
            "hypertonie",
        }

        # Keywords für andere Themen
        self.ethics_keywords = {
            "ethik",
            "moral",
            "autonomie",
            "würde",
            "einwilligung",
            "aufklärung",
            "patientenverfügung",
            "betreuung",
            "vorsorge",
            "widerspruch",
            "konflikt",
            "dilemma",
            "organspende",
            "verfügung",
        }

        self.law_keywords = {
            "gesetz",
            "recht",
            "verordnung",
            "paragraph",
            "§",
            "zustimmung",
            "widerspruch",
            "einwilligung",
            "haftung",
        }

        self.organization_keywords = {
            "ablauf",
            "protokoll",
            "koordination",
            "meldung",
            "organisation",
            "dso",
            "eurotransplant",
            "intensivtherapie",
            "entnahme",
        }

        # Patterns für strukturelle Erkennung
        self.disease_patterns = [
            r"\b(?:chronisch|akut|subakut)\b.*\b(?:erkrankung|syndrom|störung)\b",
            r"\b(?:diagnose|therapie|behandlung)\b.*\b(?:von|bei|für)\b",
            r"\b(?:symptome|zeichen|befunde)\b.*\b(?:von|bei)\b",
            r"\b(?:klassifikation|staging|einteilung)\b.*\b(?:nach|gemäß)\b",
        ]

    def classify_content(self, question: str, context: str = "") -> ClassificationResult:
        """
        Klassifiziert eine Frage/Kontext-Kombination.

        Args:
            question: Die Frage
            context: Zusätzlicher Kontext

        Returns:
            ClassificationResult mit Typ, Konfidenz und Template-Vorschlag
        """
        text = f"{question} {context}".lower()

        # Zähle Treffer für jede Kategorie
        scores = {
            ContentType.DISEASE: self._count_keywords(text, self.disease_keywords),
            ContentType.ETHICS: self._count_keywords(text, self.ethics_keywords),
            ContentType.LAW: self._count_keywords(text, self.law_keywords),
            ContentType.ORGANIZATION: self._count_keywords(text, self.organization_keywords),
        }

        # Prüfe Patterns für Krankheiten
        pattern_score = sum(1 for pattern in self.disease_patterns if re.search(pattern, text, re.IGNORECASE))
        scores[ContentType.DISEASE] += pattern_score * 2  # Patterns stärker gewichten

        # Bestimme Gewinner
        best_type = max(scores.keys(), key=lambda k: scores[k])
        total_score = sum(scores.values())

        if total_score == 0:
            # Fallback: Analysiere Frage-Struktur
            return self._classify_by_structure(question, context)

        confidence = scores[best_type] / max(1, total_score)

        # Bestimme Template
        requires_structured = best_type == ContentType.DISEASE
        template = self._get_template_for_type(best_type)

        indicators = []
        if scores[best_type] > 0:
            indicators = [f"{best_type.value}: {scores[best_type]} Treffer"]

        return ClassificationResult(
            content_type=best_type,
            confidence=confidence,
            indicators=indicators,
            requires_structured_format=requires_structured,
            suggested_template=template,
        )

    def _count_keywords(self, text: str, keywords: set) -> int:
        """Zählt Keyword-Treffer im Text"""
        return sum(1 for keyword in keywords if keyword in text)

    def _classify_by_structure(self, question: str, context: str) -> ClassificationResult:
        """Fallback-Klassifikation basierend auf Frage-Struktur"""
        question_lower = question.lower()

        # Prüfe auf typische Krankheitsfragen
        if any(word in question_lower for word in ["was ist", "wie behandelt", "welche symptome"]):
            return ClassificationResult(
                content_type=ContentType.DISEASE,
                confidence=0.5,
                indicators=["Strukturanalyse: Krankheitsfrage"],
                requires_structured_format=True,
                suggested_template="structured_medical",
            )

        # Default: Flexibles Format
        return ClassificationResult(
            content_type=ContentType.OTHER,
            confidence=0.3,
            indicators=["Fallback: Unklassifiziert"],
            requires_structured_format=False,
            suggested_template="flexible_answer",
        )

    def _get_template_for_type(self, content_type: ContentType) -> str:
        """Gibt Template-Name für Content-Type zurück"""
        templates = {
            ContentType.DISEASE: "structured_medical",
            ContentType.ETHICS: "ethics_discussion",
            ContentType.LAW: "legal_analysis",
            ContentType.ORGANIZATION: "organizational_process",
            ContentType.DIAGNOSIS: "diagnostic_pathway",
            ContentType.THERAPY: "treatment_protocol",
            ContentType.PREVENTION: "prevention_strategy",
            ContentType.OTHER: "flexible_answer",
        }
        return templates.get(content_type, "flexible_answer")

    def get_template_instructions(self, template_name: str) -> str:
        """Gibt Template-spezifische Instructions zurück"""
        templates = {
            "structured_medical": """
## 1) Definition/Klassifikation
## 2) Pathophysiologie/Ätiologie
## 3) Diagnostik (Schritte, Red Flags)
## 4) Therapie (inkl. Dosierungen – nur nach Leitlinienvalidierung)
## 5) Rechtliches/Organisation (falls relevant)
            """,
            "ethics_discussion": """
Beantworte ethische Fragen strukturiert:
- Beschreibe den ethischen Konflikt
- Nenne relevante Prinzipien (Autonomie, Benefizienz, Non-Malefizienz, Gerechtigkeit)
- Analysiere verschiedene Standpunkte
- Gib eine begründete Empfehlung
            """,
            "legal_analysis": """
Juristische Analyse:
- Zitierte Gesetze/Paragraphen
- Rechtliche Grundlagen
- Praktische Konsequenzen
- Fallbezogene Anwendung
            """,
            "organizational_process": """
Organisatorische Abläufe:
- Beteiligte Akteure
- Zeitliche Abläufe
- Zuständigkeiten
- Rechtliche Rahmenbedingungen
            """,
            "flexible_answer": """
Beantworte die Frage direkt und evidenzbasiert. Verwende Quellen und Leitlinien wo möglich.
            """,
        }

        return templates.get(template_name, templates["flexible_answer"])


# Convenience-Funktion für direkte Verwendung
def classify_medical_content(question: str, context: str = "") -> ClassificationResult:
    """
    Convenience-Funktion für die Klassifikation medizinischer Inhalte.

    Args:
        question: Die zu klassifizierende Frage
        context: Optionaler Kontext

    Returns:
        ClassificationResult mit allen Details
    """
    classifier = MedicalContentClassifier()
    return classifier.classify_content(question, context)


def get_template_for_content(question: str, context: str = "") -> Tuple[str, str]:
    """
    Gibt Template-Name und Instructions für eine Frage zurück.

    Returns:
        Tuple[template_name, template_instructions]
    """
    classifier = MedicalContentClassifier()
    result = classifier.classify_content(question, context)
    instructions = classifier.get_template_instructions(result.suggested_template)

    return result.suggested_template, instructions


# Beispiel-Nutzung
if __name__ == "__main__":
    # Test-Klassifikation
    test_cases = [
        ("Wie lässt sich dieser Widerspruch lösen?", "Organspende Patientenverfügung"),
        ("Was sind die Symptome einer Pneumonie?", ""),
        ("Welches Gesetz regelt die Organspende?", ""),
        ("Wie läuft die Hirntoddiagnostik ab?", ""),
    ]

    for question, context in test_cases:
        result = classify_medical_content(question, context)
        print(f"Frage: {question}")
        print(f"Typ: {result.content_type.value}")
        print(f"Konfidenz: {result.confidence:.2f}")
        print(f"Strukturiert: {result.requires_structured_format}")
        print(f"Template: {result.suggested_template}")
        print("---")
