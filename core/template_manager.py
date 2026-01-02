#!/usr/bin/env python3
"""
Template Manager für MedExamAI
=============================

Verwaltet verschiedene Antwort-Templates basierend auf Content-Type:
- Strukturiertes Prüfungsformat für Krankheiten
- Flexible Formate für andere Themen
- Automatische Template-Auswahl

Integration mit Content Classifier für automatische Template-Zuweisung.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from .content_classifier import ContentType, classify_medical_content


@dataclass
class AnswerTemplate:
    """Template für medizinische Antworten"""
    name: str
    description: str
    structure: List[str]  # Abschnittsnamen
    instructions: str    # Detaillierte Anweisungen
    examples: List[str]  # Beispielhafte Anwendungen
    required_sections: List[str]  # Pflichtabschnitte


class TemplateManager:
    """
    Verwaltet und wählt Templates basierend auf Content-Type aus.
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or Path(__file__).parent / "templates"
        self.templates: Dict[str, AnswerTemplate] = {}

        # Erstelle Standard-Templates
        self._create_default_templates()
        # Lade benutzerdefinierte Templates
        self._load_custom_templates()

    def _create_default_templates(self):
        """Erstellt die Standard-Templates"""

        # Strukturiertes Format für Krankheiten
        self.templates['structured_medical'] = AnswerTemplate(
            name='structured_medical',
            description='Strukturiertes Prüfungsformat für Krankheitsbilder und klinische Fälle',
            structure=[
                'Definition/Klassifikation',
                'Pathophysiologie/Ätiologie',
                'Diagnostik (Schritte, Red Flags)',
                'Therapie (inkl. Dosierungen – nur nach Leitlinienvalidierung)',
                'Rechtliches/Organisation (falls relevant)'
            ],
            instructions="""
            Beantworte die Frage im strukturierten Prüfungsformat für medizinische Krankheitsbilder.
            Jeder Abschnitt muss evidenzbasiert und mit Quellen belegt sein.

            ## 1) Definition/Klassifikation
            - Klare Definition der Erkrankung
            - Aktuelle Klassifikation nach Leitlinien
            - Epidemiologie (Prävalenz, Inzidenz)

            ## 2) Pathophysiologie/Ätiologie
            - Pathophysiologische Mechanismen
            - Risikofaktoren und Ursachen
            - Pathogenese

            ## 3) Diagnostik (Schritte, Red Flags)
            - Diagnostische Schritte und Algorithmen
            - Wichtige Red Flags und Differenzialdiagnosen
            - Empfohlene Untersuchungen

            ## 4) Therapie (inkl. Dosierungen – nur nach Leitlinienvalidierung)
            - Therapeutische Optionen nach Leitlinien
            - Dosierungen mit Evidenzgrad
            - Nebenwirkungen und Kontraindikationen

            ## 5) Rechtliches/Organisation (falls relevant)
            - Rechtliche Aspekte der Behandlung
            - Organisatorische Abläufe
            - Qualitätssicherung
            """,
            examples=[
                'Herzinsuffizienz',
                'Pneumonie',
                'Diabetes mellitus',
                'Akutes Koronarsyndrom'
            ],
            required_sections=['Definition/Klassifikation', 'Diagnostik', 'Therapie']
        )

        # Ethik-Template
        self.templates['ethics_discussion'] = AnswerTemplate(
            name='ethics_discussion',
            description='Strukturiertes Format für medizinethische Fragen',
            structure=[
                'Ethischer Konflikt',
                'Relevante ethische Prinzipien',
                'Verschiedene Standpunkte',
                'Empfehlung und Begründung'
            ],
            instructions="""
            Analysiere ethische Fragestellungen systematisch:

            ## Ethischer Konflikt
            - Beschreibe den ethischen Konflikt klar
            - Betroffene Personen/Gruppen
            - Entscheidungssituation

            ## Relevante ethische Prinzipien
            - Autonomie (Patientenselbstbestimmung)
            - Benefizienz (Wohltun)
            - Non-Malefizienz (Nichtschaden)
            - Gerechtigkeit (fairness)

            ## Verschiedene Standpunkte
            - Patientenperspektive
            - Ärztliche/therapeutische Perspektive
            - Gesellschaftliche/ethische Perspektive

            ## Empfehlung und Begründung
            - Klare Handlungsempfehlung
            - Evidenzbasierte Begründung
            - Alternative Optionen
            """,
            examples=[
                'Patientenverfügung vs. Organspende',
                'Sterbehilfe-Debatte',
                'Impfpflicht vs. individuelle Freiheit'
            ],
            required_sections=['Ethischer Konflikt', 'Empfehlung und Begründung']
        )

        # Rechtliches Template
        self.templates['legal_analysis'] = AnswerTemplate(
            name='legal_analysis',
            description='Juristische Analyse medizinischer Sachverhalte',
            structure=[
                'Rechtliche Grundlagen',
                'Gesetzliche Regelungen',
                'Praktische Anwendung',
                'Fallbeispiele'
            ],
            instructions="""
            Analysiere rechtliche Aspekte systematisch:

            ## Rechtliche Grundlagen
            - Zutreffende Gesetze und Paragraphen
            - Höchstrichterliche Rechtsprechung
            - Leitlinien und Richtlinien

            ## Gesetzliche Regelungen
            - Konkrete gesetzliche Vorgaben
            - Zuständigkeiten und Verfahren
            - Sanktionen bei Nichteinhaltung

            ## Praktische Anwendung
            - Klinische Umsetzung
            - Dokumentationspflichten
            - Haftungsrisiken

            ## Fallbeispiele
            - Relevante Urteile oder Fälle
            - Praktische Konsequenzen
            """,
            examples=[
                'Organspende-Gesetzgebung',
                'Arzt-Patienten-Verhältnis',
                'Aufklärungspflichten'
            ],
            required_sections=['Rechtliche Grundlagen', 'Gesetzliche Regelungen']
        )

        # Organisations-Template
        self.templates['organizational_process'] = AnswerTemplate(
            name='organizational_process',
            description='Organisatorische Abläufe und Prozesse',
            structure=[
                'Beteiligte Akteure',
                'Ablauf und Zeitplan',
                'Zuständigkeiten',
                'Qualitätssicherung'
            ],
            instructions="""
            Beschreibe organisatorische Prozesse klar strukturiert:

            ## Beteiligte Akteure
            - Zuständige Personen/Institutionen
            - Rollen und Verantwortlichkeiten
            - Kommunikationswege

            ## Ablauf und Zeitplan
            - Schritt-für-Schritt Ablauf
            - Zeitliche Rahmenbedingungen
            - Kritische Zeitpunkte

            ## Zuständigkeiten
            - Zuständige Stellen/Abteilungen
            - Eskalationspfade
            - Dokumentationspflichten

            ## Qualitätssicherung
            - Qualitätsstandards
            - Monitoring und Kontrolle
            - Verbesserungspotenziale
            """,
            examples=[
                'Organspende-Koordination',
                'Notfallversorgung',
                'Stationsabläufe'
            ],
            required_sections=['Ablauf und Zeitplan', 'Zuständigkeiten']
        )

        # Flexibles Template (Fallback)
        self.templates['flexible_answer'] = AnswerTemplate(
            name='flexible_answer',
            description='Flexibles Format für alle anderen Themen',
            structure=[],
            instructions="""
            Beantworte die Frage direkt, evidenzbasiert und nachvollziehbar.

            - Verwende klare, präzise Sprache
            - Belege Aussagen mit Quellen oder Leitlinien
            - Strukturiere die Antwort logisch
            - Berücksichtige den klinischen Kontext
            - Markiere Unsicherheiten klar
            """,
            examples=[
                'Faktenfragen',
                'Allgemeine medizinische Informationen',
                'Unklassifizierbare Fragen'
            ],
            required_sections=[]
        )

    def _load_custom_templates(self):
        """Lädt benutzerdefinierte Templates aus Dateien"""
        if not self.templates_dir.exists():
            return

        for template_file in self.templates_dir.glob("*.json"):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template = AnswerTemplate(**data)
                    self.templates[template.name] = template
            except Exception as e:
                print(f"Warnung: Konnte Template {template_file} nicht laden: {e}")

    def get_template_for_question(self, question: str, context: str = "") -> AnswerTemplate:
        """
        Wählt automatisch das passende Template basierend auf der Frage.

        Args:
            question: Die Frage
            context: Optionaler Kontext

        Returns:
            Das passende AnswerTemplate
        """
        # Klassifiziere die Frage
        result = classify_medical_content(question, context)

        # Hole Template
        template = self.templates.get(result.suggested_template)
        if not template:
            # Fallback auf flexibles Template
            template = self.templates['flexible_answer']

        return template

    def get_template_instructions(self, question: str, context: str = "") -> str:
        """
        Gibt die vollständigen Instructions für eine Frage zurück.

        Args:
            question: Die Frage
            context: Optionaler Kontext

        Returns:
            Formatierte Instructions für die KI
        """
        template = self.get_template_for_question(question, context)

        instructions = f"""
# Antwort-Template: {template.name}

{template.description}

{template.instructions}

## Wichtige Regeln:
- Antworte NUR auf Deutsch
- Verwende evidenzbasierte Informationen
- Zitiere Quellen und Leitlinien
- Markiere Unsicherheiten klar
- Halte dich an das vorgegebene Format

## Klassifikation dieser Frage:
- Content-Type: {classify_medical_content(question, context).content_type.value}
- Template gewählt: {template.name}
- Strukturiertes Format erforderlich: {classify_medical_content(question, context).requires_structured_format}
        """.strip()

        return instructions

    def list_available_templates(self) -> List[str]:
        """Gibt Liste aller verfügbaren Templates zurück"""
        return list(self.templates.keys())

    def get_template_details(self, template_name: str) -> Optional[AnswerTemplate]:
        """Gibt Details zu einem spezifischen Template zurück"""
        return self.templates.get(template_name)


# Convenience-Funktionen
def get_answer_template(question: str, context: str = "") -> str:
    """
    Convenience-Funktion: Gibt Template-Instructions für eine Frage zurück.

    Args:
        question: Die zu beantwortende Frage
        context: Optionaler Kontext

    Returns:
        Formatierte Template-Instructions für KI-Prompts
    """
    manager = TemplateManager()
    return manager.get_template_instructions(question, context)


def create_custom_template(name: str, description: str, structure: List[str],
                          instructions: str, examples: List[str] = None,
                          required_sections: List[str] = None) -> AnswerTemplate:
    """
    Erstellt ein benutzerdefiniertes Template.

    Args:
        name: Template-Name
        description: Beschreibung
        structure: Abschnittsstruktur
        instructions: Detaillierte Anweisungen
        examples: Beispielhafte Anwendungen
        required_sections: Pflichtabschnitte

    Returns:
        AnswerTemplate-Objekt
    """
    return AnswerTemplate(
        name=name,
        description=description,
        structure=structure or [],
        instructions=instructions,
        examples=examples or [],
        required_sections=required_sections or []
    )


# Beispiel-Nutzung
if __name__ == "__main__":
    # Test verschiedener Fragen
    test_questions = [
        ("Was sind die Symptome einer Herzinsuffizienz?", ""),
        ("Wie lässt sich dieser Widerspruch lösen?", "Organspende Patientenverfügung"),
        ("Welches Gesetz regelt die Organspende?", ""),
        ("Wie läuft die Hirntoddiagnostik ab?", "")
    ]

    manager = TemplateManager()

    for question, context in test_questions:
        print(f"\n=== Frage: {question} ===")

        # Klassifikation
        classification = classify_medical_content(question, context)
        print(f"Content-Type: {classification.content_type.value}")
        print(f"Template: {classification.suggested_template}")
        print(f"Strukturiert: {classification.requires_structured_format}")

        # Template-Instructions
        instructions = manager.get_template_instructions(question, context)
        print(f"\nInstructions (gekürzt):")
        print(instructions[:300] + "...")


# Export für andere Module
__all__ = ['TemplateManager', 'AnswerTemplate', 'get_answer_template', 'create_custom_template']

