#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scientific Skills Enrichment Module
====================================

Integriert Claude Code's Scientific Skills in die MedExamAI Pipeline.

Workflow:
1. Pharmakologie-Validierung (bioservices/datamol)
2. Epidemiologie-Daten (datacommons-client)
3. PubMed-Referenzen (biopython)
4. Parallele Verarbeitung (dask)

Autor: MedExamAI Team
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentResult:
    """Ergebnis einer Scientific Skills Anreicherung."""
    source_skill: str
    data_type: str  # 'pharmacology', 'epidemiology', 'pubmed', 'guideline'
    content: Dict[str, Any]
    confidence: float
    references: List[str] = field(default_factory=list)


class ScientificEnrichmentPipeline:
    """
    Pipeline für wissenschaftliche Datenanreicherung.

    Nutzt Claude Code's eingebaute Scientific Skills:
    - biopython: PubMed/NCBI-Queries
    - bioservices: ChEMBL, UniProt, KEGG
    - datacommons-client: Gesundheitsstatistiken
    - datamol: Molekül-Analyse
    """

    # Medikamenten-Keywords für Pharmakologie-Enrichment
    PHARMA_KEYWORDS = [
        'mg', 'dosis', 'dosierung', 'tablette', 'infusion',
        'antibiotik', 'antihypertensiv', 'analgetik', 'antikoagul',
        'betablocker', 'ace-hemmer', 'diuretik', 'insulin',
        'metformin', 'aspirin', 'heparin', 'marcumar', 'noak'
    ]

    # Epidemiologie-Keywords
    EPIDEMIOLOGY_KEYWORDS = [
        'prävalenz', 'inzidenz', 'mortalität', 'letalität',
        'risiko', 'häufigkeit', 'verbreitung', 'statistik'
    ]

    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialisiert Scientific Enrichment Pipeline.

        Args:
            cache_dir: Verzeichnis für Caching (optional)
        """
        self.cache_dir = cache_dir or Path(".scientific_cache")
        self.cache_dir.mkdir(exist_ok=True)

        # Verfügbarkeit der Skills tracken
        self.available_skills = self._check_available_skills()

        # Statistiken
        self.stats = {
            "total_enrichments": 0,
            "pharma_lookups": 0,
            "epidemiology_lookups": 0,
            "pubmed_queries": 0,
            "cache_hits": 0
        }

        logger.info(f"ScientificEnrichmentPipeline initialisiert. "
                   f"Verfügbare Skills: {list(self.available_skills.keys())}")

    def _check_available_skills(self) -> Dict[str, bool]:
        """Prüft welche Scientific Skills verfügbar sind."""
        skills = {}

        # Biopython für PubMed
        try:
            from Bio import Entrez
            skills['biopython'] = True
        except ImportError:
            skills['biopython'] = False

        # Bioservices für ChEMBL/UniProt
        try:
            import bioservices
            skills['bioservices'] = True
        except ImportError:
            skills['bioservices'] = False

        # Datacommons für Statistiken
        try:
            import datacommons
            skills['datacommons'] = True
        except ImportError:
            skills['datacommons'] = False

        # Datamol für Moleküle
        try:
            import datamol
            skills['datamol'] = True
        except ImportError:
            skills['datamol'] = False

        return skills

    def needs_pharma_enrichment(self, text: str) -> bool:
        """Prüft ob Text Pharmakologie-Anreicherung benötigt."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.PHARMA_KEYWORDS)

    def needs_epidemiology_enrichment(self, text: str) -> bool:
        """Prüft ob Text Epidemiologie-Daten benötigt."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.EPIDEMIOLOGY_KEYWORDS)

    def enrich_pharmacology(self, drug_name: str) -> Optional[EnrichmentResult]:
        """
        Reichert Medikamenten-Information an via bioservices/ChEMBL.

        Args:
            drug_name: Name des Medikaments

        Returns:
            EnrichmentResult mit Dosierungen, Interaktionen, etc.
        """
        if not self.available_skills.get('bioservices'):
            logger.warning("bioservices nicht verfügbar - Pharma-Enrichment übersprungen")
            return None

        self.stats["pharma_lookups"] += 1

        try:
            from bioservices import ChEMBL
            chembl = ChEMBL()

            # Suche nach Medikament
            results = chembl.search_molecule(drug_name)

            if not results:
                return None

            # Extrahiere relevante Daten
            mol_data = results[0] if isinstance(results, list) else results

            content = {
                "drug_name": drug_name,
                "chembl_id": mol_data.get("molecule_chembl_id"),
                "max_phase": mol_data.get("max_phase"),  # Zulassungsphase
                "molecular_weight": mol_data.get("molecule_properties", {}).get("mw_freebase"),
                "alogp": mol_data.get("molecule_properties", {}).get("alogp"),
                "indication_class": mol_data.get("indication_class"),
            }

            self.stats["total_enrichments"] += 1

            return EnrichmentResult(
                source_skill="bioservices/ChEMBL",
                data_type="pharmacology",
                content=content,
                confidence=0.9,
                references=[f"ChEMBL: {content.get('chembl_id')}"]
            )

        except Exception as e:
            logger.error(f"Pharma-Enrichment fehlgeschlagen für {drug_name}: {e}")
            return None

    def enrich_epidemiology(self, condition: str, country: str = "Germany") -> Optional[EnrichmentResult]:
        """
        Reichert Epidemiologie-Daten an via datacommons.

        Args:
            condition: Erkrankung/Zustand
            country: Land für Statistiken

        Returns:
            EnrichmentResult mit Prävalenz, Inzidenz, etc.
        """
        if not self.available_skills.get('datacommons'):
            logger.warning("datacommons nicht verfügbar - Epidemiologie-Enrichment übersprungen")
            return None

        self.stats["epidemiology_lookups"] += 1

        try:
            import datacommons as dc

            # Mapping von Erkrankungen zu Data Commons Variablen
            condition_mapping = {
                "diabetes": "Count_Person_Diabetes",
                "hypertonie": "Count_Person_Hypertension",
                "herzinsuffizienz": "Count_Person_HeartDisease",
                "copd": "Count_Person_ChronicObstructivePulmonaryDisease",
                "schlaganfall": "Count_Person_Stroke",
            }

            # Finde passende Variable
            var_name = None
            for key, var in condition_mapping.items():
                if key in condition.lower():
                    var_name = var
                    break

            if not var_name:
                return None

            # Country code für Deutschland
            place = "country/DEU" if country == "Germany" else f"country/{country}"

            # Abfrage
            data = dc.get_stat_value(place, var_name)

            if data:
                content = {
                    "condition": condition,
                    "country": country,
                    "statistic_type": var_name,
                    "value": data,
                    "unit": "persons"
                }

                self.stats["total_enrichments"] += 1

                return EnrichmentResult(
                    source_skill="datacommons",
                    data_type="epidemiology",
                    content=content,
                    confidence=0.85,
                    references=["Data Commons - Google"]
                )

        except Exception as e:
            logger.error(f"Epidemiologie-Enrichment fehlgeschlagen für {condition}: {e}")
            return None

        return None

    def search_pubmed(self, query: str, max_results: int = 3) -> Optional[EnrichmentResult]:
        """
        Sucht PubMed nach relevanten Studien via biopython.

        Args:
            query: Suchbegriff
            max_results: Maximale Anzahl Ergebnisse

        Returns:
            EnrichmentResult mit Studien-Referenzen
        """
        if not self.available_skills.get('biopython'):
            logger.warning("biopython nicht verfügbar - PubMed-Suche übersprungen")
            return None

        self.stats["pubmed_queries"] += 1

        try:
            from Bio import Entrez

            # NCBI erfordert Email
            Entrez.email = "medexamai@example.com"

            # Suche
            handle = Entrez.esearch(
                db="pubmed",
                term=f"{query} AND (guideline[pt] OR meta-analysis[pt] OR systematic review[pt])",
                retmax=max_results,
                sort="relevance"
            )
            record = Entrez.read(handle)
            handle.close()

            if not record.get("IdList"):
                return None

            # Details abrufen
            ids = record["IdList"]
            handle = Entrez.efetch(db="pubmed", id=ids, rettype="abstract", retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            articles = []
            for article in records.get("PubmedArticle", []):
                medline = article.get("MedlineCitation", {})
                article_data = medline.get("Article", {})

                articles.append({
                    "pmid": str(medline.get("PMID", "")),
                    "title": article_data.get("ArticleTitle", ""),
                    "journal": article_data.get("Journal", {}).get("Title", ""),
                    "year": article_data.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {}).get("Year", ""),
                })

            if articles:
                self.stats["total_enrichments"] += 1

                return EnrichmentResult(
                    source_skill="biopython/Entrez",
                    data_type="pubmed",
                    content={"query": query, "articles": articles},
                    confidence=0.95,
                    references=[f"PMID:{a['pmid']}" for a in articles]
                )

        except Exception as e:
            logger.error(f"PubMed-Suche fehlgeschlagen für {query}: {e}")
            return None

        return None

    def enrich_question(self, question: str, themes: List[str]) -> List[EnrichmentResult]:
        """
        Vollständige Anreicherung einer Frage.

        Args:
            question: Die Prüfungsfrage
            themes: Erkannte Themen

        Returns:
            Liste von EnrichmentResults
        """
        results = []

        # 1. Pharmakologie wenn relevant
        if self.needs_pharma_enrichment(question):
            # Extrahiere Medikamentennamen (vereinfacht)
            drugs = self._extract_drug_names(question)
            for drug in drugs[:2]:  # Max 2 Lookups
                result = self.enrich_pharmacology(drug)
                if result:
                    results.append(result)

        # 2. Epidemiologie wenn relevant
        if self.needs_epidemiology_enrichment(question):
            for theme in themes[:1]:  # Nur Haupt-Thema
                result = self.enrich_epidemiology(theme)
                if result:
                    results.append(result)

        # 3. PubMed für Leitlinien-Referenzen
        if themes:
            main_theme = themes[0]
            result = self.search_pubmed(f"{main_theme} treatment guidelines")
            if result:
                results.append(result)

        return results

    def _extract_drug_names(self, text: str) -> List[str]:
        """Extrahiert Medikamentennamen aus Text (vereinfacht)."""
        # Bekannte Medikamente
        known_drugs = [
            "metformin", "insulin", "aspirin", "heparin", "marcumar",
            "rivaroxaban", "apixaban", "metoprolol", "bisoprolol",
            "ramipril", "lisinopril", "amlodipin", "hydrochlorothiazid",
            "furosemid", "spironolacton", "prednisolon", "ibuprofen",
            "paracetamol", "metamizol", "morphin", "fentanyl"
        ]

        text_lower = text.lower()
        found = [drug for drug in known_drugs if drug in text_lower]
        return found

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken zurück."""
        return {
            **self.stats,
            "available_skills": self.available_skills
        }


# Convenience-Funktion für Pipeline-Integration
def enrich_medical_question(
    question: str,
    themes: List[str],
    cache_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Schnelle Anreicherung einer medizinischen Frage.

    Args:
        question: Die Frage
        themes: Erkannte Themen
        cache_dir: Cache-Verzeichnis

    Returns:
        Dict mit Anreicherungsdaten
    """
    pipeline = ScientificEnrichmentPipeline(cache_dir=cache_dir)
    results = pipeline.enrich_question(question, themes)

    return {
        "enrichments": [
            {
                "source": r.source_skill,
                "type": r.data_type,
                "data": r.content,
                "references": r.references
            }
            for r in results
        ],
        "statistics": pipeline.get_statistics()
    }


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)

    test_question = """
    Patient mit Diabetes mellitus Typ 2 kommt mit HbA1c von 9.2%.
    Aktuelle Therapie: Metformin 1000mg 2x täglich.
    Welche Therapieanpassung empfehlen Sie?
    """

    themes = ["Diabetes", "Endokrinologie"]

    print("Testing Scientific Enrichment Pipeline...")
    result = enrich_medical_question(test_question, themes)

    print(f"\nGefundene Anreicherungen: {len(result['enrichments'])}")
    for enr in result['enrichments']:
        print(f"  - {enr['type']} via {enr['source']}")
        print(f"    Referenzen: {enr['references']}")

    print(f"\nStatistiken: {result['statistics']}")
