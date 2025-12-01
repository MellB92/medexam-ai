#!/usr/bin/env python3
"""
MedExamAI Antwort-Generator
===========================

Generiert strukturierte Antworten für extrahierte Prüfungsfragen
unter Verwendung des RAG-Systems und der Leitlinien-Integration.

Features:
- 5-Punkte-Schema für alle Antworten
- RAG-basierte Kontextabfrage
- Leitlinien-Referenzierung
- Medical Validation
- Kosten-Tracking

Output-Format:
{
    "frage": "...",
    "antwort": {
        "definition_klassifikation": "...",
        "aetiologie_pathophysiologie": "...",
        "diagnostik": "...",
        "therapie": "...",
        "rechtliche_aspekte": "..."
    },
    "leitlinie": "AWMF S3-Leitlinie [Name] ([Jahr])",
    "evidenzgrad": "A/B/C",
    "source_tier": "gold_standard",
    "validation": {...}
}

Autor: MedExamAI Team
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None

# Parent-Verzeichnis zum Pfad hinzufügen für Imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.rag_system import MedicalRAGSystem, RAGConfig, get_rag_system
from core.guideline_fetcher import detect_medical_themes, fetch_guidelines_for_text
from core.medical_validator import MedicalValidationLayer, validate_medical_content

# Scientific Skills Integration (Claude Code's Built-in Skills)
try:
    from core.scientific_enrichment import ScientificEnrichmentPipeline, enrich_medical_question
    SCIENTIFIC_SKILLS_AVAILABLE = True
except ImportError:
    SCIENTIFIC_SKILLS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Budget- und Routing-Defaults (priorisiert)
BUDGET_ORDER = [
    ("REQUESTY", float(os.getenv("REQUESTY_BUDGET", "69.95"))),
    ("ANTHROPIC", float(os.getenv("ANTHROPIC_BUDGET", "37.62"))),
    ("AWS_BEDROCK", float(os.getenv("AWS_BEDROCK_BUDGET", "24.00"))),
    ("COMET_API", float(os.getenv("COMET_API_BUDGET", "8.65"))),
    ("PERPLEXITY", float(os.getenv("PERPLEXITY_BUDGET", "15.00"))),
    ("OPENROUTER", float(os.getenv("OPENROUTER_BUDGET", "5.78"))),
    ("OPENAI", float(os.getenv("OPENAI_BUDGET", "9.99"))),
]


# 5-Punkte-Antwort-Schema Template
ANSWER_TEMPLATE = """
**1. Definition/Klassifikation**
{definition}

**2. Ätiologie/Pathophysiologie**
{aetiologie}

**3. Diagnostik**
"Zunächst Anamnese und körperliche Untersuchung, dann..."
{diagnostik}

**4. Therapie**
{therapie}

**5. Rechtliche Aspekte**
{rechtlich}

**Leitlinie:** {leitlinie}
**Evidenzgrad:** {evidenzgrad}
"""


@dataclass
class GeneratedAnswer:
    """Strukturierte Antwort im 5-Punkte-Schema."""
    frage: str
    frage_block_id: Optional[str]
    source_file: Optional[str]
    source_tier: str

    # 5-Punkte-Schema
    definition_klassifikation: str
    aetiologie_pathophysiologie: str
    diagnostik: str
    therapie: str
    rechtliche_aspekte: str

    # Metadaten
    leitlinie: str
    evidenzgrad: str
    rag_context_sources: List[Dict[str, Any]]
    detected_themes: List[str]

    # Validation
    validation_score: float
    validation_issues: List[Dict[str, Any]]

    # Timestamps
    generated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_full_answer(self) -> str:
        """Formatiert die vollständige Antwort."""
        return ANSWER_TEMPLATE.format(
            definition=self.definition_klassifikation,
            aetiologie=self.aetiologie_pathophysiologie,
            diagnostik=self.diagnostik,
            therapie=self.therapie,
            rechtlich=self.rechtliche_aspekte,
            leitlinie=self.leitlinie,
            evidenzgrad=self.evidenzgrad
        )


class AnswerGenerator:
    """
    Generiert strukturierte Antworten für Prüfungsfragen.

    Nutzt:
    - RAG-System für Kontextabfrage
    - Leitlinien-Fetcher für Referenzen
    - Medical Validator für Qualitätsprüfung
    - Scientific Skills (biopython, bioservices, datacommons) für Anreicherung
    - Budget-Manager + Modell-Routing (Stub: keine Live-Calls ohne API)
    """

    def __init__(
        self,
        use_openai: bool = False,
        validate: bool = True,
        include_leitlinien: bool = True,
        use_scientific_skills: bool = True,
        dry_run: bool = True,
        budget_limit: float = 40.0
    ):
        self.rag = get_rag_system(use_openai=use_openai)
        self.validator = MedicalValidationLayer() if validate else None
        self.include_leitlinien = include_leitlinien
        self.dry_run = dry_run

        # Scientific Skills Integration
        self.use_scientific_skills = use_scientific_skills and SCIENTIFIC_SKILLS_AVAILABLE
        self.scientific_pipeline = None
        if self.use_scientific_skills:
            self.scientific_pipeline = ScientificEnrichmentPipeline()
            logger.info("Scientific Skills aktiviert: PubMed, ChEMBL, DataCommons")

        # Budget-Manager
        self.budget_limit = budget_limit
        self.cost_used = 0.0
        self.cost_log: List[Tuple[str, float, str]] = []  # (provider, cost, model)

        # Statistiken
        self.stats = {
            "total_generated": 0,
            "successful": 0,
            "failed": 0,
            "validation_passed": 0,
            "validation_failed": 0,
            "scientific_enrichments": 0
        }

        logger.info(f"AnswerGenerator initialisiert (OpenAI: {use_openai}, Validation: {validate}, ScientificSkills: {self.use_scientific_skills})")

    def load_questions(self, questions_file: Path) -> List[Dict[str, Any]]:
        """Lädt extrahierte Fragen aus JSON."""
        with open(questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Unterstütze beide Formate: einzelne Fragen und Blöcke
        questions = []
        for item in data:
            if "questions" in item:
                # Block-Format
                for q in item["questions"]:
                    questions.append({
                        "frage": q,
                        "block_id": item.get("block_id"),
                        "context": item.get("context", []),
                        "source_file": item.get("source_file"),
                        "source_tier": item.get("source_tier", "gold_standard")
                    })
            else:
                # Einzelfrage-Format
                questions.append({
                    "frage": item.get("frage", ""),
                    "block_id": None,
                    "context": [],
                    "source_file": item.get("source_file"),
                    "source_tier": item.get("source_tier", "gold_standard")
                })

        logger.info(f"{len(questions)} Fragen geladen")
        return questions

    def build_knowledge_base(self, questions: List[Dict[str, Any]]) -> None:
        """Baut Wissensbasis aus Fragen und Kontext auf."""
        texts = []
        for q in questions:
            texts.append(q["frage"])
            texts.extend(q.get("context", []))

        self.rag.add_to_knowledge_base(
            texts,
            source_module="gold_standard",
            source_tier="tier1_gold"
        )

        logger.info(f"Wissensbasis aufgebaut: {len(texts)} Einträge")

    def generate_answer_structure(
        self,
        question: str,
        context: List[str] = None
    ) -> Dict[str, str]:
        """
        Generiert Antwort-Struktur für eine Frage.

        Hinweis: In der Produktionsversion würde hier ein LLM verwendet werden.
        Diese MVP-Version generiert ein strukturiertes Template.
        """
        # Themen erkennen
        full_text = question + " " + " ".join(context or [])
        themes = detect_medical_themes(full_text, top_n=3)
        theme_list = [t[0] for t in themes]

        # RAG-Kontext abrufen
        rag_context = self.rag.get_context_for_question(question)

        # Leitlinien suchen wenn aktiviert
        guideline_info = ""
        evidenzgrad = "B"
        if self.include_leitlinien and themes:
            gl_result = fetch_guidelines_for_text(full_text, download=False)
            if gl_result["guidelines"]:
                gl = gl_result["guidelines"][0]
                guideline_info = f"AWMF {gl['registry_number']} - {gl['title']}"
                evidenzgrad = "A" if "S3" in gl["title"] else ("B" if "S2" in gl["title"] else "C")

        # Scientific Skills Enrichment (PubMed, ChEMBL, DataCommons)
        scientific_enrichments = []
        pubmed_references = []
        if self.use_scientific_skills and self.scientific_pipeline:
            enrichments = self.scientific_pipeline.enrich_question(question, theme_list)
            for enr in enrichments:
                scientific_enrichments.append({
                    "source": enr.source_skill,
                    "type": enr.data_type,
                    "data": enr.content,
                    "references": enr.references
                })
                # PubMed-Referenzen separat sammeln
                if enr.data_type == "pubmed":
                    pubmed_references.extend(enr.references)
            self.stats["scientific_enrichments"] += len(enrichments)

        # Strukturierte Antwort-Komponenten
        # In Produktion: LLM-generiert basierend auf Kontext
        if not self.dry_run:
            definition, aetiologie, diagnostik, therapie, rechtlich = self._generate_with_llm(
                question, context or [], rag_context.get("contexts", []), guideline_info, theme_list,
                scientific_enrichments=scientific_enrichments
            )
        else:
            definition = self._generate_definition_placeholder(question, theme_list)
            aetiologie = self._generate_aetiologie_placeholder(theme_list)
            diagnostik = self._generate_diagnostik_placeholder(theme_list)
            therapie = self._generate_therapie_placeholder(theme_list)
            rechtlich = self._generate_rechtlich_placeholder()

        return {
            "definition_klassifikation": definition,
            "aetiologie_pathophysiologie": aetiologie,
            "diagnostik": diagnostik,
            "therapie": therapie,
            "rechtliche_aspekte": rechtlich,
            "leitlinie": guideline_info or "Keine spezifische Leitlinie zugeordnet",
            "evidenzgrad": evidenzgrad,
            "themes": theme_list,
            "rag_sources": rag_context.get("sources", []),
            "scientific_enrichments": scientific_enrichments,
            "pubmed_references": pubmed_references
        }

    def _pick_model(self, question: str, therapy_bias: bool) -> Tuple[str, str, float]:
        """
        Wählt Provider/Modell nach Budget-Reihenfolge (Requesty → Anthropic → AWS → Comet → Perplexity → OpenRouter → OpenAI).
        Liefert (provider, model, est_cost_per_call). Kosten grob geschätzt.
        """
        if therapy_bias:
            candidates = [
                ("REQUESTY", "claude-sonnet-therapy", 0.03),
                ("ANTHROPIC", "claude-3-5-sonnet", 0.03),
                ("AWS_BEDROCK", "claude-3-5-sonnet", 0.03),
                ("COMET_API", "comet-therapy", 0.02),
                ("PERPLEXITY", "pplx-llama-3.1", 0.02),
                ("OPENROUTER", "llama-3.1-70b", 0.01),
                ("OPENAI", "gpt-4o-mini", 0.01),
            ]
        else:
            candidates = [
                ("REQUESTY", "claude-sonnet-lite", 0.015),
                ("ANTHROPIC", "claude-3-5-sonnet", 0.02),
                ("AWS_BEDROCK", "claude-3-5-sonnet", 0.02),
                ("COMET_API", "comet-general", 0.01),
                ("PERPLEXITY", "pplx-llama-3.1", 0.01),
                ("OPENROUTER", "llama-3.1-8b", 0.002),
                ("OPENAI", "gpt-4o-mini", 0.005),
            ]

        budget_map = dict(BUDGET_ORDER)
        for prov, model, cost in candidates:
            if self.cost_used + cost <= self.budget_limit and budget_map.get(prov, 0.0) > cost:
                return prov, model, cost
        # Fallback: günstigstes Modell
        return "OPENROUTER", "llama-3.1-8b", 0.002

    def _generate_with_llm(
        self,
        question: str,
        context: List[str],
        rag_contexts: List[str],
        guideline_info: str,
        themes: List[str],
        scientific_enrichments: List[Dict[str, Any]] = None,
    ) -> Tuple[str, str, str, str, str]:
        """
        LLM-Aufruf mit Budget-Tracking, Provider-Routing und Scientific Context via unified_api_client.
        """
        from core.unified_api_client import UnifiedAPIClient  # Lazy import

        therapy_bias = any(k in question.lower() for k in ["therapie", "behand", "dosis", "dosierung"])
        provider, model, est_cost = self._pick_model(question, therapy_bias)

        # Budgetcheck
        if self.cost_used + est_cost > self.budget_limit:
            raise RuntimeError("Budget-Limit erreicht")
        client = UnifiedAPIClient()
        prompt = self._build_prompt(question, context, rag_contexts, guideline_info, themes, scientific_enrichments)
        resp = client.complete(prompt=prompt, provider=provider, model=model)

        self.cost_used += est_cost
        self.cost_log.append((provider, est_cost, model))

        return (
            resp.get("definition_klassifikation") or self._generate_definition_placeholder(question, themes),
            resp.get("aetiologie_pathophysiologie") or self._generate_aetiologie_placeholder(themes),
            resp.get("diagnostik") or self._generate_diagnostik_placeholder(themes),
            resp.get("therapie") or self._generate_therapie_placeholder(themes),
            resp.get("rechtliche_aspekte") or self._generate_rechtlich_placeholder(),
        )

    def _build_prompt(
        self,
        question: str,
        context: List[str],
        rag_contexts: List[str],
        guideline_info: str,
        themes: List[str],
        scientific_enrichments: List[Dict[str, Any]] = None,
    ) -> str:
        scientific_context = ""
        if scientific_enrichments:
            lines = []
            for enr in scientific_enrichments:
                lines.append(json.dumps(enr, ensure_ascii=False))
            scientific_context = "\n".join(lines)
        ctx = "\n".join(context or [])
        rag = "\n".join(rag_contexts or [])
        theme_str = ", ".join(themes) if themes else "Allgemein"
        return (
            "Du bist ein deutscher Facharzt. Beantworte präzise, leitlinienkonform, ohne Halluzinationen.\n"
            f"Frage: {question}\n"
            f"Themen: {theme_str}\n"
            f"Leitlinie: {guideline_info or 'Keine spezifische Leitlinie'}\n"
            f"Kontext:\n{ctx}\n"
            f"RAG:\n{rag}\n"
            f"Wissenschaft:\n{scientific_context}\n"
            "Formatiere als JSON mit Schlüsseln: "
            "definition_klassifikation, aetiologie_pathophysiologie, diagnostik, therapie, rechtliche_aspekte. "
            "In 'therapie' immer Dosierungen (mg/kg oder mg), Frequenz, Dauer; bei Unsicherheit: 'unsicher, bitte prüfen'. "
            "In 'rechtliche_aspekte' knapp §630d/e/f BGB nennen."
        )

    def _generate_definition_placeholder(self, question: str, themes: List[str]) -> str:
        """Placeholder für Definition/Klassifikation."""
        if themes:
            return f"[Definition von {themes[0]} - In Produktion: LLM-generiert basierend auf Leitlinien]"
        return "[Definition - LLM-generiert]"

    def _generate_aetiologie_placeholder(self, themes: List[str]) -> str:
        """Placeholder für Ätiologie/Pathophysiologie."""
        return "[Ätiologie und Risikofaktoren - LLM-generiert basierend auf RAG-Kontext]"

    def _generate_diagnostik_placeholder(self, themes: List[str]) -> str:
        """Placeholder für Diagnostik."""
        return """
- Anamnese: [spezifische Fragen]
- Körperliche Untersuchung: [relevante Befunde]
- Labor: [spezifische Parameter]
- Bildgebung: [empfohlene Modalität]
- Spezielle Tests: [falls erforderlich]
[In Produktion: LLM-generiert mit konkreten Parametern]
        """.strip()

    def _generate_therapie_placeholder(self, themes: List[str]) -> str:
        """Placeholder für Therapie."""
        return """
- First-Line: [Medikament] [DOSIS in mg/kg]
- Second-Line: [Alternative]
- Bei Notfall: ABCDE-Schema
[In Produktion: LLM-generiert mit exakten Dosierungen aus Leitlinien]
        """.strip()

    def _generate_rechtlich_placeholder(self) -> str:
        """Placeholder für rechtliche Aspekte."""
        return """
- §630d BGB: Einwilligung erforderlich
- §630e BGB: Aufklärungspflicht
- §630f BGB: Dokumentationspflicht
        """.strip()

    def generate_answer(
        self,
        question_data: Dict[str, Any]
    ) -> Optional[GeneratedAnswer]:
        """
        Generiert vollständige Antwort für eine Frage.

        Args:
            question_data: Dictionary mit Frage und Metadaten

        Returns:
            GeneratedAnswer oder None bei Fehler
        """
        try:
            self.stats["total_generated"] += 1

            question = question_data.get("frage", "")
            if not question:
                logger.warning("Leere Frage übersprungen")
                self.stats["failed"] += 1
                return None

            # Antwort-Struktur generieren
            answer_data = self.generate_answer_structure(
                question,
                question_data.get("context", [])
            )

            # Validation wenn aktiviert
            validation_score = 1.0
            validation_issues = []
            if self.validator:
                full_answer = ANSWER_TEMPLATE.format(
                    definition=answer_data["definition_klassifikation"],
                    aetiologie=answer_data["aetiologie_pathophysiologie"],
                    diagnostik=answer_data["diagnostik"],
                    therapie=answer_data["therapie"],
                    rechtlich=answer_data["rechtliche_aspekte"],
                    leitlinie=answer_data["leitlinie"],
                    evidenzgrad=answer_data["evidenzgrad"]
                )
                result = self.validator.validate(full_answer)
                validation_score = result.confidence_score
                validation_issues = [i.to_dict() for i in result.issues + result.warnings]

                if result.is_valid:
                    self.stats["validation_passed"] += 1
                else:
                    self.stats["validation_failed"] += 1

            # GeneratedAnswer erstellen
            answer = GeneratedAnswer(
                frage=question,
                frage_block_id=question_data.get("block_id"),
                source_file=question_data.get("source_file"),
                source_tier=question_data.get("source_tier", "gold_standard"),
                definition_klassifikation=answer_data["definition_klassifikation"],
                aetiologie_pathophysiologie=answer_data["aetiologie_pathophysiologie"],
                diagnostik=answer_data["diagnostik"],
                therapie=answer_data["therapie"],
                rechtliche_aspekte=answer_data["rechtliche_aspekte"],
                leitlinie=answer_data["leitlinie"],
                evidenzgrad=answer_data["evidenzgrad"],
                rag_context_sources=answer_data["rag_sources"],
                detected_themes=answer_data["themes"],
                validation_score=validation_score,
                validation_issues=validation_issues,
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%S")
            )

            self.stats["successful"] += 1
            return answer

        except Exception as e:
            logger.error(f"Fehler bei Antwort-Generierung: {e}")
            self.stats["failed"] += 1
            return None

    def process_questions(
        self,
        questions: List[Dict[str, Any]],
        limit: Optional[int] = None,
        progress_callback=None
    ) -> List[GeneratedAnswer]:
        """
        Verarbeitet mehrere Fragen.

        Args:
            questions: Liste von Fragen
            limit: Maximale Anzahl zu verarbeiten
            progress_callback: Optional callback(current, total)

        Returns:
            Liste von GeneratedAnswer
        """
        if limit:
            questions = questions[:limit]

        answers = []
        for i, q in enumerate(questions):
            if progress_callback:
                progress_callback(i + 1, len(questions))

            answer = self.generate_answer(q)
            if answer:
                answers.append(answer)

        logger.info(f"Verarbeitet: {len(answers)}/{len(questions)} Fragen")
        return answers

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        stats = {
            **self.stats,
            "rag_statistics": self.rag.get_statistics()
        }
        if self.validator:
            stats["validation_statistics"] = self.validator.get_statistics()
        return stats


def load_config(path: Path) -> dict:
    """Lädt Konfiguration."""
    if not path.exists():
        raise FileNotFoundError(f"Config nicht gefunden: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML nicht installiert. Installieren mit: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generiert strukturierte Antworten für Prüfungsfragen"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parent.parent / "config.yaml")
    )
    parser.add_argument(
        "--input",
        help="Input JSON (Fragen). Default: _EXTRACTED_FRAGEN/frage_bloecke.json"
    )
    parser.add_argument(
        "--output",
        help="Output JSON. Default: _OUTPUT/qa_gold_standard.json"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximale Anzahl zu verarbeitender Fragen"
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="OpenAI für Embeddings verwenden"
    )
    parser.add_argument(
        "--no-validation",
        action="store_true",
        help="Medical Validation deaktivieren"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Kein LLM-Aufruf, nur Platzhalter (Default: False für produktive Läufe)"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=40.0,
        help="Budget-Limit (soft cap) für LLM-Aufrufe"
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
    extracted_dir = base / config.get("extracted_dir", "_EXTRACTED_FRAGEN")
    output_dir = base / config.get("output_dir", "_OUTPUT")
    output_dir.mkdir(parents=True, exist_ok=True)

    input_file = Path(args.input) if args.input else extracted_dir / "frage_bloecke.json"
    output_file = Path(args.output) if args.output else output_dir / "qa_gold_standard.json"

    if not input_file.exists():
        # Fallback auf echte_fragen.json
        input_file = extracted_dir / "echte_fragen.json"
        if not input_file.exists():
            logger.error(f"Keine Fragen gefunden in {extracted_dir}")
            return 1

    # Generator erstellen
    generator = AnswerGenerator(
        use_openai=args.use_openai,
        validate=not args.no_validation,
        include_leitlinien=True,
        dry_run=args.dry_run,
        budget_limit=args.budget
    )

    # Fragen laden
    questions = generator.load_questions(input_file)
    if not questions:
        logger.error("Keine Fragen geladen")
        return 1

    # Wissensbasis aufbauen
    generator.build_knowledge_base(questions)

    # Fortschrittsanzeige
    def progress(current, total):
        print(f"\r⏳ Verarbeite: {current}/{total} ({current*100//total}%)", end="", flush=True)

    # Antworten generieren
    print(f"\n🚀 Starte Antwort-Generierung für {len(questions)} Fragen...")
    answers = generator.process_questions(
        questions,
        limit=args.limit,
        progress_callback=progress
    )
    print()  # Newline nach Fortschritt

    # Ergebnisse speichern
    output_data = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_questions": len(questions),
        "total_answers": len(answers),
        "statistics": generator.get_statistics(),
        "answers": [a.to_dict() for a in answers]
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Zusammenfassung
    stats = generator.get_statistics()
    print(f"\n✅ Antwort-Generierung abgeschlossen!")
    print(f"   Fragen: {len(questions)}")
    print(f"   Antworten: {len(answers)}")
    print(f"   Erfolgreich: {stats['successful']}")
    print(f"   Fehlgeschlagen: {stats['failed']}")
    if not args.no_validation:
        print(f"   Validation bestanden: {stats['validation_passed']}")
        print(f"   Validation fehlgeschlagen: {stats['validation_failed']}")
    print(f"   Output: {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
