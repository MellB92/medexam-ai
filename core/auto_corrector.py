#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG-Enhanced Automatic Medical Content Corrector
=================================================

Automatische Korrektur und Verbesserung medizinischer Inhalte mit:
- Multi-Source RAG Validation (Amboss, DocCheck, AWMF, PubMed, Europe PMC)
- Konsens-basierte Korrektur
- Evidence-Level Tracking
- Source Attribution
- Widerspruchs-Erkennung

Model: Claude Sonnet 4.5 + Premium RAG System
Autor: Entwickelt für Dr. Bobadilla Salazar
"""

import logging
import json
import re
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

# RAG System Import
try:
    from . import rag_sources
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logging.warning("RAG sources module not available - falling back to simple correction")

logger = logging.getLogger(__name__)


@dataclass
class CorrectionResult:
    """Ergebnis einer automatischen Korrektur mit RAG-Informationen"""
    original_text: str
    corrected_text: str
    changes_made: List[str] = field(default_factory=list)
    change_count: int = 0
    improvement_score: float = 0.0  # 0.0-1.0
    timestamp: str = ""
    success: bool = False
    error: Optional[str] = None
    model_used: str = "Claude Sonnet 4.5"
    
    # RAG-spezifische Felder
    rag_validation: Dict[str, Any] = field(default_factory=dict)
    sources_consulted: List[Dict] = field(default_factory=list)
    consensus_score: float = 0.0
    contradictions_found: int = 0
    evidence_level: str = "unknown"
    

@dataclass
class MedicalClaim:
    """Repräsentiert eine extrahierte medizinische Aussage"""
    text: str
    keywords: List[str]
    line_number: int
    confidence: float = 0.0
    validated: bool = False
    validation_sources: List[str] = field(default_factory=list)


class RAGEnhancedAutoCorrector:
    """
    RAG-Enhanced Automatischer Korrektor für medizinische Inhalte.
    
    Nutzt Multi-Source RAG für:
    - Faktische Validierung
    - Halluzination-Entfernung  
    - Konsens-basierte Korrektur
    - Leitlinien-Abgleich
    - Source Attribution
    """
    
    # Medical claim patterns für Extraktion
    CLAIM_PATTERNS = [
        r'(?:Therapie|Behandlung|Diagnose)(?:\s+(?:der|von|bei))?\s+\w+',
        r'\w+\s+(?:ist|sind|wird|werden)\s+(?:kontraindiziert|indiziert|empfohlen)',
        r'(?:Dosierung|Dosis):\s*[\d\.,]+\s*(?:mg|g|ml|IE)',
        r'(?:Nebenwirkungen?|UAW):\s+\w+',
        r'(?:Leitlinien?|Guideline):\s+\w+'
    ]
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 enable_rag: bool = True,
                 rag_sources_priority: Optional[List[str]] = None):
        """
        Initialize RAG-Enhanced AutoCorrector.
        
        Args:
            api_key: Optional API key für LLM
            enable_rag: RAG-Validierung aktivieren
            rag_sources_priority: Prioritäten-Liste der Quellen
        """
        self.api_key = api_key
        self.enable_rag = enable_rag and RAG_AVAILABLE
        
        # RAG System initialisieren
        if self.enable_rag:
            self.rag_system = rag_sources.MedicalRAGSystem()
            self.rag_sources_priority = rag_sources_priority or [
                'Amboss', 'DocCheck', 'AWMF', 'PubMed', 'Europe PMC'
            ]
            logger.info("✓ RAG-Enhanced AutoCorrector initialisiert")
            logger.info(f"  Quellen: {', '.join(self.rag_sources_priority)}")
        else:
            self.rag_system = None
            logger.warning("⚠️ RAG deaktiviert - nutze Fallback-Korrektur")
        
        # Statistiken
        self.correction_stats = {
            'total_corrections': 0,
            'successful': 0,
            'failed': 0,
            'rag_validations': 0,
            'claims_validated': 0,
            'claims_corrected': 0,
            'avg_improvement': 0.0,
            'avg_consensus_score': 0.0
        }
    
    # =========================================================================
    # MEDICAL CLAIM EXTRACTION
    # =========================================================================
    
    def extract_medical_claims(self, text: str) -> List[MedicalClaim]:
        """
        Extrahiert medizinische Aussagen aus Text für RAG-Validierung.
        
        Args:
            text: Dokumenttext
            
        Returns:
            Liste von MedicalClaim Objekten
        """
        claims: List[MedicalClaim] = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            if not line_stripped or len(line_stripped) < 10:
                continue
            
            # Suche nach Claim-Patterns
            for pattern in self.CLAIM_PATTERNS:
                matches = re.finditer(pattern, line_stripped, re.IGNORECASE)
                
                for match in matches:
                    claim_text = match.group(0)
                    
                    # Extrahiere Keywords aus Claim
                    keywords = self._extract_keywords_from_claim(claim_text)
                    
                    if keywords:
                        claim = MedicalClaim(
                            text=claim_text,
                            keywords=keywords,
                            line_number=line_num,
                            confidence=0.7  # Vereinfacht
                        )
                        claims.append(claim)
        
        logger.info(f"Extrahiert: {len(claims)} medizinische Claims zur Validierung")
        return claims
    
    def _extract_keywords_from_claim(self, claim_text: str) -> List[str]:
        """Extrahiert medizinische Keywords aus Claim"""
        # Entferne Stoppwörter
        stopwords = {'ist', 'sind', 'wird', 'werden', 'der', 'die', 'das', 'bei', 'von', 'zur', 'zum'}
        
        words = claim_text.split()
        keywords = [
            word.strip(',.;:!?')
            for word in words
            if len(word) > 3 and word.lower() not in stopwords
        ]
        
        return keywords[:5]  # Max 5 Keywords
    
    # =========================================================================
    # RAG-BASED VALIDATION
    # =========================================================================
    
    def validate_claim_with_rag(
        self,
        claim: MedicalClaim,
        max_sources_per_query: int = 2
    ) -> Dict[str, Any]:
        """
        Validiert einen medizinischen Claim gegen RAG-Quellen.
        
        Args:
            claim: MedicalClaim zu validieren
            max_sources_per_query: Max Quellen pro Keyword
            
        Returns:
            Validierungs-Ergebnis mit Konsens-Info
        """
        if not self.enable_rag:
            return {'validated': False, 'reason': 'RAG disabled'}
        
        validation_result = {
            'claim': claim.text,
            'validated': False,
            'consensus_score': 0.0,
            'sources': [],
            'contradictions': [],
            'recommendations': []
        }
        
        try:
            # Suche für jedes Keyword
            all_sources = []
            
            for keyword in claim.keywords[:3]:  # Limitiere auf 3 Keywords
                results = self.rag_system.search_all_sources(
                    query=keyword,
                    sources=self.rag_sources_priority,
                    max_per_source=max_sources_per_query
                )
                
                aggregated = self.rag_system.aggregate_sources(results)
                all_sources.extend(aggregated)
            
            if not all_sources:
                validation_result['reason'] = 'No sources found'
                return validation_result
            
            # Konsens-Analyse
            consensus = self.rag_system.detect_consensus(
                all_sources,
                claim.keywords[0] if claim.keywords else claim.text
            )
            
            # Widerspruchs-Erkennung
            contradictions = self.rag_system.detect_contradictions(all_sources)
            
            # Validierungs-Ergebnis
            validation_result.update({
                'validated': consensus['consensus_found'],
                'consensus_score': consensus['consensus_score'],
                'sources': [
                    {
                        'name': s.source_name,
                        'title': s.title,
                        'url': s.url,
                        'quality_score': s.quality_score,
                        'evidence_level': s.evidence_level
                    }
                    for s in all_sources[:5]  # Top 5
                ],
                'contradictions': contradictions,
                'best_evidence_level': consensus.get('best_evidence_level', 'unknown')
            })
            
            # Empfehlungen basierend auf Ergebnis
            if not consensus['consensus_found']:
                validation_result['recommendations'].append(
                    f"Claim '{claim.text}' konnte nicht durch Konsens validiert werden"
                )
            
            if contradictions:
                validation_result['recommendations'].append(
                    f"{len(contradictions)} Widersprüche zwischen Quellen gefunden"
                )
            
            self.correction_stats['rag_validations'] += 1
            self.correction_stats['claims_validated'] += 1
            
        except Exception as e:
            logger.error(f"RAG-Validierung fehlgeschlagen: {e}")
            validation_result['error'] = str(e)
        
        return validation_result
    
    # =========================================================================
    # DOCUMENT CORRECTION
    # =========================================================================
    
    def correct_document(
        self, 
        text: str, 
        filename: str = "",
        use_rag: bool = True,
        min_consensus_score: float = 0.5
    ) -> CorrectionResult:
        """
        Korrigiert ein medizinisches Dokument mit RAG-Validierung.
        
        Args:
            text: Zu korrigierender Text
            filename: Dateiname für Kontext
            use_rag: RAG-Validierung nutzen
            min_consensus_score: Minimaler Konsens für Validierung
            
        Returns:
            CorrectionResult mit korrigiertem Text und RAG-Informationen
        """
        if not text or len(text.strip()) < 50:
            return CorrectionResult(
                original_text=text,
                corrected_text=text,
                success=False,
                error="Text zu kurz für Korrektur"
            )
        
        result = CorrectionResult(
            original_text=text,
            corrected_text=text,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            # 1. Extrahiere medizinische Claims
            logger.info(f"🔍 Extrahiere medizinische Claims aus: {filename}")
            claims = self.extract_medical_claims(text)
            
            # 2. RAG-Validierung (falls aktiviert)
            validations = []
            if use_rag and self.enable_rag and claims:
                logger.info(f"🔬 Validiere {len(claims)} Claims mit RAG...")
                
                for i, claim in enumerate(claims[:10], 1):  # Limitiere auf 10 Claims
                    logger.debug(f"  [{i}/{min(len(claims), 10)}] Validiere: {claim.text[:50]}...")
                    validation = self.validate_claim_with_rag(claim)
                    validations.append(validation)
                    
                    # Update Claim mit Validierungsergebnis
                    claim.validated = validation['validated']
                    claim.validation_sources = [s['name'] for s in validation['sources']]
                
                # Berechne durchschnittlichen Konsens-Score
                consensus_scores = [v['consensus_score'] for v in validations if v.get('consensus_score', 0) > 0]
                avg_consensus = sum(consensus_scores) / len(consensus_scores) if consensus_scores else 0.0
                
                result.consensus_score = avg_consensus
                result.rag_validation = {
                    'claims_total': len(claims),
                    'claims_validated': sum(1 for v in validations if v['validated']),
                    'avg_consensus_score': avg_consensus,
                    'sources_used': list(set(s['name'] for v in validations for s in v.get('sources', [])))
                }
                
                logger.info(f"  ✓ RAG-Validierung abgeschlossen: {result.rag_validation['claims_validated']}/{len(claims)} Claims validiert")
                logger.info(f"  ✓ Durchschn. Konsens: {avg_consensus:.2f}")
            
            # 3. Generiere Korrekturen basierend auf Validierungen
            corrected_text, changes = self._apply_rag_corrections(
                text,
                claims,
                validations,
                min_consensus_score
            )
            
            result.corrected_text = corrected_text
            result.changes_made = changes
            result.change_count = len(changes)
            result.success = True
            
            # 4. Source Attribution hinzufügen
            if validations and use_rag:
                all_sources_used = []
                for v in validations:
                    for source in v.get('sources', []):
                        if source not in all_sources_used:
                            all_sources_used.append(source)
                
                result.sources_consulted = all_sources_used
                
                # Füge Quellenangaben am Ende hinzu
                if all_sources_used:
                    attribution = self._generate_source_attribution(all_sources_used)
                    result.corrected_text += f"\n\n{attribution}"
            
            # 5. Berechne Improvement Score
            result.improvement_score = self._calculate_improvement(text, corrected_text, validations)
            
            # Update Statistiken
            self.correction_stats['total_corrections'] += 1
            self.correction_stats['successful'] += 1
            
            if validations:
                self.correction_stats['avg_consensus_score'] = (
                    (self.correction_stats['avg_consensus_score'] * (self.correction_stats['rag_validations'] - len(validations)) +
                     sum(v['consensus_score'] for v in validations)) /
                    self.correction_stats['rag_validations']
                )
            
            logger.info(
                f"✅ Korrektur abgeschlossen: {filename} - "
                f"{result.change_count} Änderungen, "
                f"Improvement: {result.improvement_score:.2f}, "
                f"Konsens: {result.consensus_score:.2f}"
            )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            self.correction_stats['failed'] += 1
            logger.error(f"❌ Korrektur fehlgeschlagen für {filename}: {e}")
        
        return result
    
    def _apply_rag_corrections(
        self,
        text: str,
        claims: List[MedicalClaim],
        validations: List[Dict],
        min_consensus_score: float
    ) -> Tuple[str, List[str]]:
        """
        Wendet Korrekturen basierend auf RAG-Validierungen an.
        
        Args:
            text: Originaltext
            claims: Extrahierte Claims
            validations: RAG-Validierungsergebnisse
            min_consensus_score: Minimaler Konsens für Änderungen
            
        Returns:
            Tuple (corrected_text, changes_list)
        """
        corrected = text
        changes = []
        
        for claim, validation in zip(claims, validations):
            # Nur korrigieren wenn Konsens niedrig oder Widersprüche gefunden
            if not validation.get('validated') or validation.get('consensus_score', 0) < min_consensus_score:
                
                # Markiere problematischen Claim
                marker = f" [VALIDIERUNG ERFORDERLICH - Konsens: {validation.get('consensus_score', 0):.2f}]"
                
                if claim.text in corrected and marker not in corrected:
                    corrected = corrected.replace(
                        claim.text,
                        claim.text + marker,
                        1  # Nur erste Occurrence
                    )
                    changes.append(
                        f"Zeile {claim.line_number}: '{claim.text[:50]}...' - "
                        f"Niedriger Konsens ({validation.get('consensus_score', 0):.2f})"
                    )
                    self.correction_stats['claims_corrected'] += 1
            
            # Widersprüche markieren
            if validation.get('contradictions'):
                for contradiction in validation['contradictions']:
                    warning = f" [⚠️ WIDERSPRUCH: {contradiction['source1']} vs {contradiction['source2']}]"
                    
                    if claim.text in corrected and warning not in corrected:
                        corrected = corrected.replace(claim.text, claim.text + warning, 1)
                        changes.append(
                            f"Zeile {claim.line_number}: Widerspruch zwischen Quellen erkannt"
                        )
        
        # Zusätzlich: Halluzination-Phrasen entfernen (wie vorher)
        hallucination_phrases = [
            ('Es ist wichtig zu beachten, dass', ''),
            ('Zusammenfassend lässt sich sagen', ''),
            ('Im Allgemeinen gilt', ''),
        ]
        
        for phrase, replacement in hallucination_phrases:
            if phrase in corrected:
                corrected = corrected.replace(phrase, replacement)
                changes.append(f"Entfernt: '{phrase}'")
        
        if not changes:
            changes = ["Keine Korrekturen erforderlich - Alle Claims validiert"]
        
        return corrected, changes
    
    def _generate_source_attribution(self, sources: List[Dict]) -> str:
        """Generiert formatierte Quellenangaben"""
        lines = ["---", "## KONSULTIERTE QUELLEN", ""]
        
        for i, source in enumerate(sources[:10], 1):  # Max 10
            lines.append(
                f"{i}. **{source['name']}**: {source['title'][:100]}"
            )
            lines.append(
                f"   - Evidence Level: {source['evidence_level']} | "
                f"Quality: {source['quality_score']:.2f}"
            )
            lines.append(f"   - URL: {source['url']}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _calculate_improvement(
        self,
        original: str,
        corrected: str,
        validations: List[Dict]
    ) -> float:
        """
        Berechnet Verbesserungs-Score mit RAG-Informationen.
        
        Returns:
            Score (0.0-1.0)
        """
        # Basis-Score
        if len(corrected) < len(original) * 0.5:
            base_score = 0.3
        elif len(corrected) > len(original) * 1.5:
            base_score = 0.5
        else:
            char_diff = abs(len(corrected) - len(original))
            change_rate = char_diff / len(original) if original else 0
            
            if 0.05 < change_rate < 0.3:
                base_score = 0.8
            elif change_rate <= 0.05:
                base_score = 0.6
            else:
                base_score = 0.4
        
        # Bonus für hohen Konsens
        if validations:
            avg_consensus = sum(v.get('consensus_score', 0) for v in validations) / len(validations)
            rag_bonus = avg_consensus * 0.3  # Max 0.3 Bonus
            
            return min(1.0, base_score + rag_bonus)
        
        return base_score
    
    # =========================================================================
    # BATCH PROCESSING
    # =========================================================================
    
    def batch_correct(
        self, 
        documents: Dict[str, str],
        use_rag: bool = True
    ) -> Dict[str, CorrectionResult]:
        """
        Batch-Korrektur mehrerer Dokumente mit RAG.
        
        Args:
            documents: Dict {filename: text}
            use_rag: RAG-Validierung nutzen
            
        Returns:
            Dict {filename: CorrectionResult}
        """
        logger.info(f"🚀 Starte RAG-Enhanced Batch-Korrektur von {len(documents)} Dokumenten")
        
        results = {}
        for i, (filename, text) in enumerate(documents.items(), 1):
            logger.info(f"  [{i}/{len(documents)}] Korrigiere: {filename}")
            
            try:
                result = self.correct_document(text, filename, use_rag)
                results[filename] = result
                
                if i % 10 == 0:
                    logger.info(f"    Fortschritt: {i}/{len(documents)}")
                    
            except Exception as e:
                logger.error(f"  ❌ Fehler bei {filename}: {e}")
                results[filename] = CorrectionResult(
                    original_text=text,
                    corrected_text=text,
                    success=False,
                    error=str(e)
                )
        
        # Statistiken
        successful = sum(1 for r in results.values() if r.success)
        avg_improvement = (
            sum(r.improvement_score for r in results.values() if r.success) / successful
            if successful > 0 else 0.0
        )
        avg_consensus = (
            sum(r.consensus_score for r in results.values() if r.success and r.consensus_score > 0) / successful
            if successful > 0 else 0.0
        )
        
        logger.info("=" * 80)
        logger.info("✅ RAG-ENHANCED BATCH-KORREKTUR ABGESCHLOSSEN")
        logger.info(f"   Erfolgreich: {successful}/{len(results)}")
        logger.info(f"   Durchschn. Verbesserung: {avg_improvement:.2f}")
        logger.info(f"   Durchschn. Konsens: {avg_consensus:.2f}")
        logger.info("=" * 80)
        
        return results
    
    def get_statistics(self) -> Dict:
        """Gibt Korrektur-Statistiken zurück"""
        stats = self.correction_stats.copy()
        
        if self.enable_rag and self.rag_system:
            stats['rag_system_stats'] = self.rag_system.get_statistics()
        
        return stats


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def auto_correct_with_rag(
    text: str,
    use_rag: bool = True,
    rag_sources: Optional[List[str]] = None
) -> str:
    """
    Schnelle RAG-Enhanced Auto-Korrektur eines Textes.
    
    Args:
        text: Zu korrigierender Text
        use_rag: RAG-Validierung nutzen
        rag_sources: Optional spezifische Quellen
        
    Returns:
        Korrigierter Text
    """
    corrector = RAGEnhancedAutoCorrector(
        enable_rag=use_rag,
        rag_sources_priority=rag_sources
    )
    result = corrector.correct_document(text, use_rag=use_rag)
    return result.corrected_text if result.success else text


if __name__ == "__main__":
    # Demo
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 80)
    print("RAG-ENHANCED AUTO-CORRECTOR - DEMO")
    print("=" * 80)
    
    test_text = """
    Herzinsuffizienz Therapie:
    
    Bei akuter Herzinsuffizienz ist die Gabe von ACE-Hemmern kontraindiziert.
    Die Therapie sollte mit Betablockern beginnen.
    
    Dosierung: Metoprolol 50mg täglich.
    
    Wichtig: Alle Patienten sollten Aspirin erhalten.
    """
    
    print("\n📄 Original-Text:")
    print(test_text)
    print("\n" + "-" * 80)
    
    corrector = RAGEnhancedAutoCorrector(enable_rag=True)
    result = corrector.correct_document(test_text, "test.txt", use_rag=True)
    
    print("\n✅ Korrigierter Text:")
    print(result.corrected_text)
    
    print("\n📝 Änderungen:")
    for change in result.changes_made:
        print(f"  - {change}")
    
    print(f"\n📊 Scores:")
    print(f"  Improvement: {result.improvement_score:.2f}")
    print(f"  Konsens: {result.consensus_score:.2f}")
    
    if result.rag_validation:
        print(f"\n🔬 RAG-Validierung:")
        for key, value in result.rag_validation.items():
            print(f"  {key}: {value}")
    
    print(f"\n📚 Quellen ({len(result.sources_consulted)}):")
    for source in result.sources_consulted[:3]:
        print(f"  - {source['name']}: {source['title'][:50]}...")
    
    print("\n" + "=" * 80)