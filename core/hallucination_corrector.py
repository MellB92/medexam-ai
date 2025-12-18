#!/usr/bin/env python3
"""
Halluzinations-Korrektur-System mit Verifikation durch externe Quellen.

Verwendet:
1. Perplexity Web-Suche für aktuelle medizinische Informationen
2. RAG-System für verifizierte Quellen
3. Medizinische Validierung

Workflow:
1. Erkennung potenzieller Halluzinationen
2. Extraktion der medizinischen Behauptungen
3. Verifikation gegen externe Quellen
4. Korrektur oder Entfernung falscher Informationen
"""

import asyncio
import json
import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

# Füge Projektpfad hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.hallucination_filter import HallucinationFilter, HallucinationMatch


@dataclass
class MedicalClaim:
    """Eine medizinische Behauptung zum Verifizieren"""
    text: str
    topic: str
    claim_type: str  # "definition", "therapy", "diagnosis", "fact"
    context: str
    source_file: str = ""
    line_number: int = 0


@dataclass
class VerificationResult:
    """Ergebnis der Verifikation"""
    claim: MedicalClaim
    is_verified: bool
    confidence: float  # 0-1
    corrected_text: Optional[str]
    sources: List[str]
    explanation: str


class HallucinationCorrector:
    """Korrigiert Halluzinationen mit externen Quellen"""

    def __init__(self, use_web_search: bool = True, use_rag: bool = True):
        self.use_web_search = use_web_search
        self.use_rag = use_rag
        self.filter = HallucinationFilter(severity_threshold="medium")

        # Lade Web-Suche wenn verfügbar
        self.web_search = None
        if use_web_search:
            try:
                from core.web_search import WebSearch
                self.web_search = WebSearch()
            except ImportError:
                print("⚠️ Web-Suche nicht verfügbar")

        # Lade RAG wenn verfügbar
        self.rag = None
        if use_rag:
            try:
                from core.rag_system import RAGSystem
                self.rag = RAGSystem()
            except ImportError:
                print("⚠️ RAG-System nicht verfügbar")

    def extract_medical_claims(self, text: str) -> List[MedicalClaim]:
        """
        Extrahiert überprüfbare medizinische Behauptungen aus dem Text.
        """
        claims = []

        # Muster für verschiedene Behauptungstypen
        patterns = {
            "definition": [
                r'(?:ist|sind|bezeichnet|bedeutet)\s+(?:ein[e]?\s+)?(.+?)(?:\.|$)',
                r'(?:Definition|Beschreibung):\s*(.+?)(?:\.|$)',
            ],
            "therapy": [
                r'(?:Therapie|Behandlung|behandelt mit):\s*(.+?)(?:\.|$)',
                r'(?:wird |werden )?(?:behandelt|therapiert) mit (.+?)(?:\.|$)',
                r'(?:Medikament|Mittel der Wahl):\s*(.+?)(?:\.|$)',
            ],
            "diagnosis": [
                r'(?:Diagnose|Diagnostik|diagnostiziert durch):\s*(.+?)(?:\.|$)',
                r'(?:Labor|Bildgebung|Untersuchung):\s*(.+?)(?:\.|$)',
            ],
            "fact": [
                r'(\d+(?:\.\d+)?%?\s+(?:der|aller)\s+.+?)(?:\.|$)',
                r'(?:Häufigkeit|Inzidenz|Prävalenz):\s*(.+?)(?:\.|$)',
                r'(?:typisch|charakteristisch|pathognomonisch)\s+(?:ist|sind)\s+(.+?)(?:\.|$)',
            ],
        }

        # Erkenne Thema aus Kontext
        topic = self._detect_topic(text)

        for claim_type, type_patterns in patterns.items():
            for pattern in type_patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    claim_text = match.group(1).strip()
                    if len(claim_text) > 10:  # Mindestlänge
                        claims.append(MedicalClaim(
                            text=claim_text,
                            topic=topic,
                            claim_type=claim_type,
                            context=text[max(0, match.start()-100):match.end()+100],
                        ))

        return claims

    def _detect_topic(self, text: str) -> str:
        """Erkennt das medizinische Thema"""
        # Einfache Keyword-Erkennung
        topics = {
            "appendizitis": ["appendizitis", "blinddarm", "mcburney"],
            "pankreatitis": ["pankreatitis", "pankreas", "lipase"],
            "pneumonie": ["pneumonie", "lungenentzündung", "infiltrat"],
            "fraktur": ["fraktur", "bruch", "osteosynthese"],
            "ileus": ["ileus", "darmverschluss", "obstipation"],
            "gerd": ["gerd", "reflux", "sodbrennen", "ösophagitis"],
            "herzinsuffizienz": ["herzinsuffizienz", "nyha", "ejektionsfraktion"],
        }

        text_lower = text.lower()
        for topic, keywords in topics.items():
            if any(kw in text_lower for kw in keywords):
                return topic

        return "allgemein"

    async def verify_claim(self, claim: MedicalClaim) -> VerificationResult:
        """
        Verifiziert eine einzelne Behauptung gegen externe Quellen.
        """
        sources = []
        verified_info = []

        # 1. Web-Suche
        if self.web_search:
            try:
                query = f"{claim.topic} {claim.text} medizin deutsch"
                search_results = await self.web_search.search(query, max_results=3)

                for result in search_results:
                    sources.append(result.get("url", ""))
                    verified_info.append(result.get("content", ""))

            except Exception as e:
                print(f"  Web-Suche Fehler: {e}")

        # 2. RAG-System
        if self.rag:
            try:
                rag_results = self.rag.search(claim.text, top_k=3)
                for result in rag_results:
                    verified_info.append(result.get("content", ""))
            except Exception as e:
                print(f"  RAG Fehler: {e}")

        # 3. Vergleiche und bewerte
        confidence, corrected = self._evaluate_claim(claim, verified_info)

        return VerificationResult(
            claim=claim,
            is_verified=confidence > 0.7,
            confidence=confidence,
            corrected_text=corrected if confidence < 0.7 else None,
            sources=sources,
            explanation=f"Konfidenz: {confidence:.0%}" + (
                " - Korrektur empfohlen" if confidence < 0.7 else " - Verifiziert"
            ),
        )

    def _evaluate_claim(self, claim: MedicalClaim,
                        verified_info: List[str]) -> Tuple[float, Optional[str]]:
        """
        Bewertet eine Behauptung gegen verifizierte Informationen.

        Returns:
            (confidence, corrected_text)
        """
        if not verified_info:
            return 0.5, None  # Neutral wenn keine Quellen

        claim_lower = claim.text.lower()
        combined_info = " ".join(verified_info).lower()

        # Einfache Keyword-Übereinstimmung
        claim_words = set(re.findall(r'\w+', claim_lower))
        info_words = set(re.findall(r'\w+', combined_info))

        if not claim_words:
            return 0.5, None

        overlap = len(claim_words & info_words) / len(claim_words)

        # Wenn geringe Übereinstimmung, extrahiere korrekten Text
        corrected = None
        if overlap < 0.5:
            # Versuche relevanten Abschnitt zu extrahieren
            for info in verified_info:
                if claim.topic.lower() in info.lower():
                    # Extrahiere ersten relevanten Satz
                    sentences = info.split('.')
                    for sent in sentences:
                        if any(kw in sent.lower() for kw in claim_words):
                            corrected = sent.strip() + "."
                            break
                    if corrected:
                        break

        return overlap, corrected

    async def correct_file(self, filepath: Path) -> Dict[str, Any]:
        """
        Korrigiert Halluzinationen in einer Datei.

        Returns:
            Dict mit Statistiken und korrigiertem Inhalt
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"Verarbeite: {filepath.name}")

        # 1. Erkenne Halluzinationen
        matches = self.filter.detect(content)
        print(f"  Halluzinationen gefunden: {len(matches)}")

        if not matches:
            return {
                "file": filepath.name,
                "hallucinations_found": 0,
                "corrected": 0,
                "removed": 0,
                "content": content,
            }

        # 2. Extrahiere Behauptungen aus problematischen Stellen
        claims_to_verify = []
        for match in matches:
            # Erweitere Kontext
            start = max(0, match.start - 200)
            end = min(len(content), match.end + 200)
            context = content[start:end]

            claims = self.extract_medical_claims(context)
            for claim in claims:
                claim.source_file = filepath.name
            claims_to_verify.extend(claims)

        print(f"  Behauptungen zu verifizieren: {len(claims_to_verify)}")

        # 3. Verifiziere Behauptungen
        verified = 0
        corrected_count = 0
        removed_count = 0
        corrections = []

        for claim in claims_to_verify[:10]:  # Limitiere auf 10 pro Datei
            try:
                result = await self.verify_claim(claim)

                if result.is_verified:
                    verified += 1
                elif result.corrected_text:
                    corrections.append({
                        "original": claim.text,
                        "corrected": result.corrected_text,
                        "confidence": result.confidence,
                    })
                    corrected_count += 1
                else:
                    removed_count += 1

            except Exception as e:
                print(f"  Fehler bei Verifikation: {e}")

        # 4. Wende Korrekturen an
        corrected_content = content
        for corr in corrections:
            corrected_content = corrected_content.replace(
                corr["original"],
                corr["corrected"]
            )

        # 5. Entferne nicht verifizierbare Halluzinationen
        corrected_content, _ = self.filter.filter(corrected_content)

        return {
            "file": filepath.name,
            "hallucinations_found": len(matches),
            "claims_verified": verified,
            "corrected": corrected_count,
            "removed": removed_count,
            "corrections": corrections,
            "content": corrected_content,
        }


async def process_llm_archive(archive_dir: Path, output_dir: Path,
                               use_web: bool = True) -> Dict[str, Any]:
    """
    Verarbeitet alle LLM_ARCHIVE Dateien.
    """
    corrector = HallucinationCorrector(use_web_search=use_web)

    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "processed": 0,
        "total_hallucinations": 0,
        "total_corrected": 0,
        "total_removed": 0,
        "files": [],
    }

    # Finde alle MD-Dateien (ohne Duplikate)
    files = [f for f in archive_dir.glob("*.md") if not f.name.endswith(".md.md")]

    for filepath in files:
        result = await corrector.correct_file(filepath)

        # Speichere korrigierte Datei
        output_path = output_dir / filepath.name
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result["content"])

        stats["processed"] += 1
        stats["total_hallucinations"] += result["hallucinations_found"]
        stats["total_corrected"] += result["corrected"]
        stats["total_removed"] += result["removed"]
        stats["files"].append({
            "name": filepath.name,
            "hallucinations": result["hallucinations_found"],
            "corrected": result["corrected"],
            "removed": result["removed"],
        })

        print(f"  ✅ Gespeichert: {output_path.name}")

    return stats


# Synchroner Wrapper für CLI
def process_archive_sync(archive_dir: str, output_dir: str,
                         use_web: bool = True) -> Dict[str, Any]:
    """Synchroner Wrapper für async Funktion"""
    return asyncio.run(process_llm_archive(
        Path(archive_dir),
        Path(output_dir),
        use_web
    ))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Korrigiert Halluzinationen in LLM_ARCHIVE"
    )
    parser.add_argument("--input", "-i", type=Path, default=Path("_LLM_ARCHIVE"),
                        help="Eingabeverzeichnis")
    parser.add_argument("--output", "-o", type=Path, default=Path("_LLM_ARCHIVE_CLEAN"),
                        help="Ausgabeverzeichnis")
    parser.add_argument("--no-web", action="store_true",
                        help="Ohne Web-Suche (schneller, aber weniger genau)")

    args = parser.parse_args()

    print("=" * 60)
    print("HALLUZINATIONS-KORREKTUR")
    print("=" * 60)
    print()

    stats = process_archive_sync(
        str(args.input),
        str(args.output),
        use_web=not args.no_web
    )

    print()
    print("=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Verarbeitete Dateien: {stats['processed']}")
    print(f"Halluzinationen gefunden: {stats['total_hallucinations']}")
    print(f"Korrigiert: {stats['total_corrected']}")
    print(f"Entfernt: {stats['total_removed']}")
    print(f"Ausgabe: {args.output}")
