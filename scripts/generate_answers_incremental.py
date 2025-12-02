#!/usr/bin/env python3
"""
Inkrementeller Antwort-Generator mit Qualitätskontrolle
========================================================

Verarbeitet Fragen in Gruppen (nach Topic) oder einzeln (isoliert)
und speichert nach jeder Gruppe/Frage.

Features:
- Gruppierung nach Topic für zusammenhängende Fragen
- Inkrementelles Speichern nach jeder Gruppe
- Qualitätskontrolle mit Mindest-Score
- Fortschritts-Tracking und Resume-Fähigkeit
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_answers import AnswerGenerator
from core.medical_validator import validate_generated_answer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def load_qa_data(input_file: Path) -> Dict[str, Any]:
    """Lädt die QA-Daten."""
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_qa_data(data: Dict[str, Any], output_file: Path) -> None:
    """Speichert die QA-Daten."""
    # Backup erstellen
    if output_file.exists():
        backup = output_file.with_suffix('.json.bak')
        output_file.rename(backup)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Gespeichert: {output_file}")


def group_questions_by_topic(qa_pairs: List[Dict]) -> Dict[str, List[Dict]]:
    """Gruppiert Fragen nach Topic."""
    groups = defaultdict(list)

    for q in qa_pairs:
        topic = q.get('topic', '') or '_isolated'
        groups[topic].append(q)

    return dict(groups)


def quality_check(answer: str, min_length: int = 100) -> bool:
    """Prüft die Qualität einer Antwort (Basis-Check)."""
    if not answer:
        return False
    if len(answer) < min_length:
        return False
    # Prüfe ob strukturiert (mindestens 2 Abschnitte)
    if answer.count('\n\n') < 1:
        return False
    return True


def enhanced_quality_check(
    question: str,
    answer: str,
    rag_context: str = None,
    rag_sources: list = None,
    min_score: float = 0.5
) -> tuple:
    """
    Erweiterte Qualitätsprüfung mit Halluzinations- und Fakten-Check.

    Returns:
        (passed, validation_result) - Ob bestanden + detailliertes Ergebnis
    """
    try:
        result = validate_generated_answer(
            question=question,
            answer=answer,
            rag_context=rag_context,
            rag_sources=rag_sources
        )

        passed = (
            result['validation_passed'] or
            result['overall_score'] >= min_score
        )

        return passed, result
    except Exception as e:
        logger.warning(f"Validierungsfehler: {e}")
        # Fallback auf Basis-Check
        return quality_check(answer, 100), {
            "validation_passed": quality_check(answer, 100),
            "overall_score": 0.5,
            "scores": {},
            "issues": [],
            "recommendation": "REVIEW"
        }


def main():
    parser = argparse.ArgumentParser(description='Inkrementeller Antwort-Generator')
    parser.add_argument('--input', default='_OUTPUT/cleaned_qa.json', help='Input JSON')
    parser.add_argument('--output', default='_OUTPUT/cleaned_qa.json', help='Output JSON (wird inkrementell aktualisiert)')
    parser.add_argument('--limit', type=int, help='Max. Anzahl Fragen')
    parser.add_argument('--topic', help='Nur bestimmtes Topic verarbeiten')
    parser.add_argument('--skip-isolated', action='store_true', help='Isolierte Fragen überspringen')
    parser.add_argument('--min-quality', type=int, default=100, help='Minimale Antwortlänge')
    parser.add_argument('--dry-run', action='store_true', help='Kein LLM-Aufruf')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_file = Path(args.input)
    output_file = Path(args.output)

    # Lade Daten
    logger.info(f"Lade: {input_file}")
    data = load_qa_data(input_file)
    qa_pairs = data.get('qa_pairs', [])

    # Zähle Status
    total = len(qa_pairs)
    with_answer = sum(1 for q in qa_pairs if q.get('answer'))
    without_answer = total - with_answer

    logger.info(f"Gesamt: {total}, Mit Antwort: {with_answer}, Ohne Antwort: {without_answer}")

    if without_answer == 0:
        logger.info("Alle Fragen haben bereits Antworten!")
        return 0

    # Gruppiere nach Topic
    groups = group_questions_by_topic(qa_pairs)
    logger.info(f"Topics: {len(groups)}")

    # Filter Topics
    if args.topic:
        if args.topic in groups:
            groups = {args.topic: groups[args.topic]}
        else:
            logger.error(f"Topic '{args.topic}' nicht gefunden!")
            return 1

    if args.skip_isolated and '_isolated' in groups:
        del groups['_isolated']

    # Initialisiere Generator (nur wenn nicht dry-run)
    generator = None
    if not args.dry_run:
        generator = AnswerGenerator(
            use_openai=False,
            validate=True,
            dry_run=False  # Wichtig: Live-Modus aktivieren
        )

    # Verarbeite Gruppen
    processed = 0
    failed = 0
    limit = args.limit or float('inf')

    # Sortiere Topics: Größere zuerst (effizienter für Kontext)
    sorted_topics = sorted(groups.items(), key=lambda x: -len(x[1]) if x[0] != '_isolated' else 0)

    for topic, questions in sorted_topics:
        if processed >= limit:
            break

        # Filtere nur Fragen ohne Antwort und ohne skip-Flag
        unanswered = [q for q in questions if not q.get('answer') and not q.get('skip_generation')]
        if not unanswered:
            continue

        is_isolated = (topic == '_isolated')
        group_name = f"Isoliert ({len(unanswered)})" if is_isolated else f"Topic: {topic} ({len(unanswered)})"

        logger.info(f"\n{'='*60}")
        logger.info(f"Verarbeite: {group_name}")
        logger.info(f"{'='*60}")

        # Für isolierte: einzeln verarbeiten und speichern
        # Für Topics: alle zusammen, dann speichern

        if is_isolated:
            # Einzeln verarbeiten
            for q in unanswered:
                if processed >= limit:
                    break

                question_text = q.get('question', '')
                logger.info(f"  → {question_text[:60]}...")

                if args.dry_run:
                    q['answer'] = f"[DRY-RUN] Antwort für: {question_text[:50]}"
                    processed += 1
                else:
                    try:
                        # Frage-Daten für Generator vorbereiten
                        question_data = {
                            "frage": question_text,
                            "context": [q.get('case_context', '')] if q.get('case_context') else [],
                            "block_id": None,
                            "source_file": q.get('source_file'),
                            "source_tier": q.get('source_tier', 'gold_standard')
                        }

                        # Generiere Antwort mit existierender Methode
                        result = generator.generate_answer(question_data)

                        if result:
                            answer_text = result.format_full_answer()
                            rag_context = result.rag_context if hasattr(result, 'rag_context') else None
                            rag_sources = result.rag_context_sources if hasattr(result, 'rag_context_sources') else None

                            # Erweiterte Validierung
                            passed, validation = enhanced_quality_check(
                                question=question_text,
                                answer=answer_text,
                                rag_context=rag_context,
                                rag_sources=rag_sources
                            )

                            if passed:
                                q['answer'] = answer_text
                                q['answer_metadata'] = {
                                    'generated_at': datetime.now().isoformat(),
                                    'leitlinie': result.leitlinie,
                                    'evidenzgrad': result.evidenzgrad,
                                    'source_tier': result.source_tier,
                                    'validation_score': result.validation_score,
                                    'rag_sources': rag_sources[:3] if rag_sources else [],
                                    'quality_validation': {
                                        'overall_score': validation.get('overall_score', 0),
                                        'hallucination_risk': validation.get('scores', {}).get('hallucination_risk', 0),
                                        'recommendation': validation.get('recommendation', 'UNKNOWN')
                                    }
                                }
                                processed += 1
                                rec = validation.get('recommendation', '?')
                                score = validation.get('overall_score', 0)
                                logger.info(f"    ✓ Antwort generiert ({len(answer_text)} Z, Score: {score:.2f}, {rec})")
                            else:
                                failed += 1
                                rec = validation.get('recommendation', 'REJECT')
                                issues = len(validation.get('issues', []))
                                logger.warning(f"    ✗ Validierung: {rec} ({issues} Issues)")
                        else:
                            failed += 1
                            logger.warning(f"    ✗ Keine Antwort generiert")
                    except Exception as e:
                        failed += 1
                        logger.error(f"    ✗ Fehler: {e}")

                # Speichere nach jeder isolierten Frage
                if processed % 1 == 0:  # Nach jeder Frage
                    save_qa_data(data, output_file)
        else:
            # Gruppiert verarbeiten
            group_processed = 0
            for q in unanswered:
                if processed >= limit:
                    break

                question_text = q.get('question', '')
                logger.info(f"  → {question_text[:60]}...")

                if args.dry_run:
                    q['answer'] = f"[DRY-RUN] Antwort für: {question_text[:50]}"
                    processed += 1
                    group_processed += 1
                else:
                    try:
                        # Frage-Daten für Generator vorbereiten
                        question_data = {
                            "frage": question_text,
                            "context": [q.get('case_context', '')] if q.get('case_context') else [],
                            "block_id": topic,
                            "source_file": q.get('source_file'),
                            "source_tier": q.get('source_tier', 'gold_standard')
                        }

                        # Generiere Antwort mit existierender Methode
                        result = generator.generate_answer(question_data)

                        if result:
                            answer_text = result.format_full_answer()
                            rag_context = result.rag_context if hasattr(result, 'rag_context') else None
                            rag_sources = result.rag_context_sources if hasattr(result, 'rag_context_sources') else None

                            # Erweiterte Validierung (wie bei isolierten Fragen)
                            passed, validation = enhanced_quality_check(
                                question=question_text,
                                answer=answer_text,
                                rag_context=rag_context,
                                rag_sources=rag_sources
                            )

                            if passed:
                                q['answer'] = answer_text
                                q['answer_metadata'] = {
                                    'generated_at': datetime.now().isoformat(),
                                    'topic': topic,
                                    'leitlinie': result.leitlinie,
                                    'evidenzgrad': result.evidenzgrad,
                                    'source_tier': result.source_tier,
                                    'validation_score': result.validation_score,
                                    'rag_sources': rag_sources[:3] if rag_sources else [],
                                    'quality_validation': {
                                        'overall_score': validation.get('overall_score', 0),
                                        'hallucination_risk': validation.get('scores', {}).get('hallucination_risk', 0),
                                        'recommendation': validation.get('recommendation', 'UNKNOWN')
                                    }
                                }
                                processed += 1
                                group_processed += 1
                                rec = validation.get('recommendation', '?')
                                score = validation.get('overall_score', 0)
                                logger.info(f"    ✓ Antwort generiert ({len(answer_text)} Z, Score: {score:.2f}, {rec})")
                            else:
                                failed += 1
                                rec = validation.get('recommendation', 'REJECT')
                                issues = len(validation.get('issues', []))
                                logger.warning(f"    ✗ Validierung: {rec} ({issues} Issues)")
                        else:
                            failed += 1
                            logger.warning(f"    ✗ Keine Antwort generiert")
                    except Exception as e:
                        failed += 1
                        logger.error(f"    ✗ Fehler: {e}")

            # Speichere nach jeder Topic-Gruppe
            if group_processed > 0:
                save_qa_data(data, output_file)
                logger.info(f"  → Gruppe '{topic}' gespeichert ({group_processed} Antworten)")

    # Finale Statistik
    logger.info(f"\n{'='*60}")
    logger.info("ZUSAMMENFASSUNG")
    logger.info(f"{'='*60}")
    logger.info(f"Verarbeitet: {processed}")
    logger.info(f"Fehlgeschlagen: {failed}")
    logger.info(f"Gesamt mit Antwort: {with_answer + processed}")
    logger.info(f"Verbleibend: {without_answer - processed}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
