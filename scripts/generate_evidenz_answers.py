#!/usr/bin/env python3
"""
MedExamAI Evidenzbasierte Antwort-Generierung
==============================================

Generiert Antworten NUR für Fragen ohne existierende Gold Standard Antworten.
Nutzt RAG-System mit Leitlinien für evidenzbasierte Antworten.

WICHTIG: Keine halluzinierten Antworten! Alle Antworten müssen:
- Aus Leitlinien (AWMF, ESC, etc.) stammen
- Evidenzbasiert sein
- Mit Quellen belegt sein
"""

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.unified_api_client import BudgetExceededError
from core.enhanced_validation_pipeline import EnhancedValidationPipeline

# Parent-Verzeichnis zum Pfad hinzufügen für Imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

# Globale Validation Pipeline (wird in main() initialisiert)
_validation_pipeline: Optional[EnhancedValidationPipeline] = None


def get_validation_pipeline(rag_system=None, strict_mode: bool = True) -> EnhancedValidationPipeline:
    """Singleton-Zugriff auf die Validation Pipeline.

    STRICT MODE ist standardmäßig AKTIVIERT für maximale Fakten-Genauigkeit!
    """
    global _validation_pipeline
    if _validation_pipeline is None:
        _validation_pipeline = EnhancedValidationPipeline(
            rag_system=rag_system,
            log_dir=Path("_OUTPUT/validation_logs"),
            strict_mode=strict_mode
        )
        logger.info(f"EnhancedValidationPipeline initialisiert (STRICT MODE: {strict_mode})")
    return _validation_pipeline


@dataclass
class EvidenzAnswer:
    """Evidenzbasierte Antwort mit Quellenangaben."""
    frage: str
    source_file: str
    context: List[str]

    # Antwort
    antwort: str

    # Evidenz
    leitlinie: str
    evidenzgrad: str
    quellen: List[str]

    # Metadaten
    rag_chunks_used: int
    generated_at: str

    # Validierung (optional)
    validation: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def load_questions_with_context(
    questions_file: Path,
    original_blocks_file: Path
) -> List[Dict[str, Any]]:
    """
    Lädt unbeantwortete Fragen und reichert sie mit originalem Kontext an.
    """
    # Lade unbeantwortete Fragen
    with questions_file.open(encoding='utf-8') as f:
        unanswered = json.load(f)

    # Lade Original-Blöcke für Kontext
    with original_blocks_file.open(encoding='utf-8') as f:
        blocks = json.load(f)

    # Baue Index: source_file -> blocks
    block_index = {}
    for block in blocks:
        src = block.get('source_file', '')
        if src not in block_index:
            block_index[src] = []
        block_index[src].append(block)

    # Reichere Fragen mit Kontext an
    enriched = []
    for q in unanswered:
        question_text = q.get('question', '')
        source = q.get('source', '')

        # Finde passenden Kontext
        context = []
        if source in block_index:
            for block in block_index[source]:
                questions = block.get('questions', block.get('fragen', []))
                if question_text in questions:
                    context = block.get('context', [])
                    break

        enriched.append({
            'question': question_text,
            'source_file': source,
            'context': context
        })

    return enriched


def is_followup_question(text: str) -> bool:
    """
    Erkennt Folgefragen, die Kontext von vorherigen Fragen benötigen.
    Diese sollten mit den vorherigen Fragen als Block verarbeitet werden.
    """
    import re
    text_lower = text.lower().strip()

    # Patterns für Folgefragen
    followup_patterns = [
        r'\bdamit\b', r'\bdavon\b', r'\bdarauf\b', r'\bdaran\b', r'\bdaraus\b',
        r'\bdafür\b', r'\bdagegen\b', r'\bdarüber\b', r'\bdarunter\b',
        r'\bdabei\b', r'\bdazu\b', r'\bdahin\b', r'\bdaher\b',
        r'^was ist (damit|das|dies|dieses|diese|es)\s',
        r'^was bedeutet (das|dies|es)\s',
        r'^wann (braucht|macht|nimmt|gibt) man (das|dies|es)\b',
        r'^und (was|wie|wann|warum|wo)\b',
        r'^wie (genau|denn)\?*$',
        r'^warum (denn|das)\?*$',
    ]

    for pattern in followup_patterns:
        if re.search(pattern, text_lower):
            return True

    # Sehr kurze Fragen ohne medizinischen Begriff
    if len(text) < 35:
        if re.search(r'\b(das|dies|diese[rms]?|es)\b', text_lower):
            medical_terms = ['therapie', 'diagnose', 'symptom', 'medikament',
                           'behandlung', 'untersuchung', 'labor', 'blut',
                           'impfung', 'dosis', 'rezept']
            if not any(term in text_lower for term in medical_terms):
                return True

    return False


def load_question_blocks(
    questions_file: Path,
    original_blocks_file: Path
) -> List[Dict[str, Any]]:
    """
    Lädt unbeantwortete Fragen und gruppiert sie nach Original-Blöcken.
    Zusammenhängende Fragen (inkl. Folgefragen) bleiben zusammen.
    """
    with questions_file.open(encoding='utf-8') as f:
        unanswered = json.load(f)

    with original_blocks_file.open(encoding='utf-8') as f:
        blocks = json.load(f)

    unanswered_set = {q.get('question', '') for q in unanswered}

    question_blocks = []
    for block in blocks:
        block_questions = block.get('questions', block.get('fragen', []))
        context = block.get('context', [])
        source = block.get('source_file', '')

        # Finde unbeantwortete Fragen in diesem Block
        unanswered_in_block = [q for q in block_questions if q in unanswered_set]

        if unanswered_in_block:
            question_blocks.append({
                'questions': unanswered_in_block,
                'all_block_questions': block_questions,
                'context': context,
                'source_file': source,
                'block_id': block.get('block_id', '')
            })

    logger.info(f"Geladen: {len(question_blocks)} Blöcke mit "
                f"{sum(len(b['questions']) for b in question_blocks)} unbeantworteten Fragen")
    return question_blocks


def filter_answerable_questions(questions: List[Dict]) -> List[Dict]:
    """
    Filtert Fragen, die sinnvoll beantwortet werden können.
    Entfernt zu kurze oder unvollständige Fragen.
    """
    filtered = []
    skipped = 0

    for q in questions:
        text = q['question']
        context = q.get('context', [])

        # Mindestlänge
        if len(text) < 15:
            skipped += 1
            continue

        # Muss ein Fragezeichen haben oder mit W-Wort beginnen
        text_lower = text.lower()
        has_question_marker = (
            '?' in text or
            text_lower.startswith(('wie', 'was', 'welche', 'wann', 'wo',
                                   'warum', 'wer', 'woran', 'womit'))
        )
        if not has_question_marker:
            skipped += 1
            continue

        # Prüfe auf unvollständige Fragen (enden mit Komma, etc.)
        if text.rstrip().endswith((',', '...', ',,', '.')):
            # Aber nur wenn kein Kontext
            if not context:
                skipped += 1
                continue

        filtered.append(q)

    logger.info(f"Gefiltert: {len(filtered)} beantwortbar, {skipped} übersprungen")
    return filtered


def load_gold_standard_knowledge(base_dir: Path) -> List[Dict]:
    """
    Lädt die extrahierten Gold Standard Themen aus KP Münster.
    """
    kp_file = base_dir / "_EXTRACTED_FRAGEN/Q:A Paaren und Fällen/KP Münster 2020 -2025.md"
    if not kp_file.exists():
        return []

    knowledge = []
    content = kp_file.read_text(encoding='utf-8')

    # Parse topics (simplified - look for main sections)
    current_topic = None
    current_content = []

    for line in content.split('\n'):
        # Main topic (indented, with page number)
        if line.startswith('    - ') and not line.startswith('        '):
            if current_topic and current_content:
                knowledge.append({
                    'topic': current_topic,
                    'content': '\n'.join(current_content),
                    'source': 'KP Münster 2020-2025'
                })
            # Extract topic name
            topic_match = line.strip('- ').split()[0] if line.strip('- ') else None
            current_topic = line.strip('- ').rstrip('0123456789 ')
            current_content = []
        elif current_topic and line.strip():
            current_content.append(line.strip('- '))

    # Don't forget last topic
    if current_topic and current_content:
        knowledge.append({
            'topic': current_topic,
            'content': '\n'.join(current_content),
            'source': 'KP Münster 2020-2025'
        })

    return knowledge


def find_relevant_knowledge(
    question: str,
    knowledge_base: List[Dict],
    top_k: int = 3
) -> List[Dict]:
    """
    Findet relevante Wissenseinträge für eine Frage.
    Einfache Keyword-Suche (kein ML-basiertes Embedding nötig).
    """
    from difflib import SequenceMatcher

    question_lower = question.lower()
    scored = []

    for entry in knowledge_base:
        topic = entry['topic'].lower()
        content_preview = entry['content'][:500].lower()

        # Keyword-Matching
        score = 0

        # Topic match
        if topic in question_lower:
            score += 0.5
        for word in topic.split():
            if len(word) > 3 and word in question_lower:
                score += 0.2

        # Content keywords
        medical_keywords = [
            'therapie', 'diagnose', 'diagnostik', 'symptom',
            'ursache', 'ätiologie', 'behandlung', 'medikament',
            'fraktur', 'ruptur', 'entzündung', 'infektion'
        ]
        for kw in medical_keywords:
            if kw in question_lower and kw in content_preview:
                score += 0.15

        if score > 0.1:
            scored.append((score, entry))

    # Sort by score
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            'text': e['content'][:800],
            'source': f"{e['source']} - {e['topic']}",
            'score': s
        }
        for s, e in scored[:top_k]
    ]


def get_rag_context(
    question: str,
    context: List[str],
    rag_system,
    knowledge_base: List[Dict] = None,
    use_web_search: bool = False  # Default OFF - Perplexity ist teuer!
) -> List[Dict]:
    """
    Holt relevanten Kontext - erst aus Gold Standard, dann RAG, dann Web-Suche.
    """
    results = []

    # 1. Erst Gold Standard Knowledge
    if knowledge_base:
        gs_results = find_relevant_knowledge(question, knowledge_base, top_k=2)
        results.extend(gs_results)

    # 2. Dann RAG-System wenn verfügbar und nicht leer
    if rag_system:
        # NUR Frage für RAG-Suche verwenden (Context ist oft OCR-Müll)
        search_text = question

        try:
            # min_similarity=0.1 übergeben (Default ist 0.7 - viel zu hoch!)
            rag_results = rag_system.search(search_text, top_k=5, min_similarity=0.1)
            rag_hits = 0
            for r in rag_results:
                # Sekundärer Filter für Qualität
                if r.similarity_score > 0.15:
                    results.append({
                        'text': r.text,
                        'source': r.metadata.get('source', 'Leitlinie'),
                        'score': r.similarity_score
                    })
                    rag_hits += 1
            logger.info(f"RAG-Suche '{search_text[:50]}...': {rag_hits} Treffer")
        except Exception as e:
            logger.warning(f"RAG-Fehler: {e}")

    # 3. Web-Suche als Ergänzung (wenn RAG wenig liefert oder für aktuelle Themen)
    if use_web_search and len(results) < 2:
        try:
            from core.web_search import search_medical_web
            web_results = search_medical_web(question, max_results=1)
            for wr in web_results:
                results.append({
                    'text': wr['snippet'][:1000],
                    'source': 'Perplexity Web-Recherche',
                    'score': 0.9  # Hoher Score für Web-Ergebnisse
                })
            if web_results:
                logger.info(f"Web-Suche: {len(web_results)} Ergebnis(se)")
        except Exception as e:
            logger.warning(f"Web-Suche-Fehler: {e}")

    return results[:5]


def generate_answer_with_llm(
    question: str,
    context: List[str],
    rag_context: List[Dict],
    api_client,
    related_questions: List[str] = None,
    question_id: str = "unknown",
    validate: bool = True,
    preferred_provider: str = None,
    override_model: str = None,
) -> Dict[str, Any]:
    """
    Generiert eine evidenzbasierte Antwort mit LLM.
    Bei Folgefragen werden vorherige Fragen als Kontext mitgeschickt.
    Optionale Validierung durch EnhancedValidationPipeline.
    """
    # Baue Prompt mit Leitlinien-Kontext
    context_text = ""
    if rag_context:
        context_text = "\n\n**Relevante Leitlinien-Auszüge:**\n"
        for i, ctx in enumerate(rag_context[:3], 1):
            context_text += f"\n[{i}] {ctx['source']}:\n{ctx['text'][:500]}\n"

    exam_context = ""
    if context:
        exam_context = f"\n**Prüfungskontext:**\n{' '.join(context[:3])}\n"

    # NEU: Vorherige Fragen als Kontext für Folgefragen
    related_context = ""
    if related_questions and len(related_questions) > 0:
        related_context = "\n**Vorherige Fragen im selben Block (für Kontext):**\n"
        for i, rq in enumerate(related_questions, 1):
            related_context += f"  {i}. {rq}\n"

    system_prompt = """Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.
Beantworte die Frage AUSSCHLIESSLICH basierend auf:
1. Den bereitgestellten Leitlinien-Auszügen
2. Etabliertem medizinischem Wissen (keine Vermutungen!)

WICHTIG: Wenn "Vorherige Fragen" angegeben sind, beziehen sich Pronomen wie
"damit", "das", "diese" auf den Kontext dieser vorherigen Fragen!

Format:
- Kurze, präzise Antwort (3-5 Sätze max)
- Immer Leitlinie/Quelle angeben wenn vorhanden
- Bei Unsicherheit: "Keine sichere Antwort möglich" statt Halluzination

KEINE erfundenen Fakten oder Statistiken!"""

    user_prompt = f"""**Aktuelle Frage:** {question}
{related_context}
{exam_context}
{context_text}

Beantworte diese Prüfungsfrage evidenzbasiert."""

    try:
        result = api_client.chat_completion(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=800,
            temperature=0.1,  # Niedrig für faktische Antworten
            provider=preferred_provider,
            model=override_model,
        )

        raw_answer = result.get('response', '')
        validated_answer = raw_answer
        validation_metadata = {}

        # Optional: Validierung durch EnhancedValidationPipeline
        if validate and raw_answer:
            try:
                pipeline = get_validation_pipeline()
                validated_answer, validation_metadata = pipeline.validate_answer(
                    answer=raw_answer,
                    query=question,
                    question_id=question_id
                )
                logger.debug(f"Validierung für {question_id}: {validation_metadata.get('is_valid', 'N/A')}")
            except Exception as val_err:
                logger.warning(f"Validierung fehlgeschlagen: {val_err}")
                validation_metadata = {"error": str(val_err), "skipped": True}

        return {
            'success': True,
            'answer': validated_answer,
            'raw_answer': raw_answer if validated_answer != raw_answer else None,
            'provider': result.get('provider', 'unknown'),
            'model': result.get('model'),
            'usage': result.get('usage', {}),
            'cost': result.get('usage', {}).get('cost', 0.0),
            'meta': result.get('meta', {}),
            'validation': validation_metadata,
        }
    except BudgetExceededError:
        # Signal an den Aufrufer weiterreichen, damit das Budget respektiert wird
        raise
    except Exception as e:
        logger.error(f"LLM-Aufruf fehlgeschlagen: {e}")
        return {
            'success': False,
            'answer': '',
            'error': str(e)
        }


def extract_leitlinie_reference(answer: str, rag_context: List[Dict]) -> tuple:
    """
    Extrahiert Leitlinien-Referenz aus Antwort oder RAG-Kontext.
    """
    leitlinie = "Keine Leitlinie verfügbar"
    evidenzgrad = "N/A"

    if rag_context:
        # Nutze beste RAG-Quelle
        best_source = rag_context[0]['source']
        if 'AWMF' in best_source or 'Leitlinie' in best_source:
            leitlinie = best_source
            evidenzgrad = "Leitlinien-basiert"

    # Suche in Antwort nach Leitlinien-Referenz
    import re
    ll_match = re.search(r'(S[123]-Leitlinie|AWMF|Nationale VersorgungsLeitlinie)[^.]*', answer)
    if ll_match:
        leitlinie = ll_match.group(0)

    return leitlinie, evidenzgrad


def estimate_question_complexity(question: str, rag_context: List[Dict]) -> str:
    """
    Grobe Heuristik: high = komplex, medium = normal, low = simpel.
    Nutzt Länge, Fach-Keywords und dünnen RAG-Kontext.
    """
    text = question.lower()
    key_high = ["therapie", "dosierung", "leitlinie", "staging", "algorithmus", "kombination", "kontraindikation"]
    key_low = ["definition", "was ist", "kurz", "bedeutet"]

    score = 0
    if len(question) > 180:
        score += 2
    elif len(question) > 120:
        score += 1

    if any(k in text for k in key_high):
        score += 2
    if any(k in text for k in key_low):
        score -= 1

    # Dosierungs-Hinweise
    if any(token in text for token in [" mg", " g ", "ml", "dosis", "dosierung"]):
        score += 1

    # Wenn RAG-Kontext sehr knapp ist, ruhig günstiger versuchen
    if len(rag_context) <= 1:
        score -= 1

    if score >= 2:
        return "high"
    if score <= -1:
        return "low"
    return "medium"


def select_provider_model(complexity: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Wählt Provider/Modell nach Komplexität (Stand: Dez 2025):
    ALLE Requests gehen über REQUESTY als Router!

    - high: Claude Opus 4.5 Extended Thinking (beste Qualität für komplexe Fragen)
    - medium/low: GPT-5.1-mini High Thinking (günstig mit hoher Qualität)
    """
    complexity = complexity or "medium"

    # WICHTIG: Alles über Requesty routen für zentrale Kostenkontrolle
    if complexity == "high":
        # Claude Opus 4.5 für komplexe Fragen via Requesty
        return "requesty", "anthropic/claude-opus-4-5-20251101"

    # Low/Medium: GPT-5.1-mini mit High Thinking via Requesty
    return "requesty", "openai/gpt-5.1-mini-high"


def load_checkpoint(output_path: Path) -> Tuple[List[Dict], set]:
    """
    Lade existierende Antworten für Resume-Funktionalität.
    Returns: (existing_answers, answered_questions_set)
    """
    answered = set()
    existing = []

    if output_path.exists():
        try:
            with output_path.open('r', encoding='utf-8') as f:
                existing = json.load(f)

            # Erstelle Set aus bereits beantworteten Fragen
            for ans in existing:
                q = ans.get('frage', '')
                src = ans.get('source_file', '')
                # Eindeutiger Key: Frage + Quelle
                answered.add(f"{src}::{q}")

            logger.info(f"Checkpoint geladen: {len(existing)} bereits beantwortete Fragen")
        except Exception as e:
            logger.warning(f"Checkpoint konnte nicht geladen werden: {e}")

    return existing, answered


def save_checkpoint(output_path: Path, answers: List[Dict], block_idx: int, total_blocks: int):
    """
    Speichere Checkpoint nach jedem Block mit Fortschrittsinfo.
    """
    checkpoint_data = {
        'answers': answers,
        'progress': {
            'block_idx': block_idx,
            'total_blocks': total_blocks,
            'timestamp': datetime.now().isoformat(),
            'answered_count': len(answers)
        }
    }

    # Speichere Haupt-Output (nur Antworten)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)

    # Speichere detaillierten Checkpoint
    checkpoint_path = output_path.with_suffix('.checkpoint.json')
    with checkpoint_path.open('w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

    logger.debug(f"Checkpoint gespeichert: Block {block_idx}/{total_blocks}, {len(answers)} Antworten")


def main():
    parser = argparse.ArgumentParser(
        description="Generiere evidenzbasierte Antworten für unbeantwortete Fragen"
    )
    parser.add_argument(
        "--unanswered",
        default="_OUTPUT/fragen_ohne_antwort.json",
        help="JSON mit unbeantworteten Fragen"
    )
    parser.add_argument(
        "--blocks",
        default="_EXTRACTED_FRAGEN/frage_bloecke_dedupe.json",
        help="Original-Fragenblöcke für Kontext"
    )
    parser.add_argument(
        "--output",
        default="_OUTPUT/evidenz_antworten.json",
        help="Output JSON"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximale Anzahl zu generierender Antworten"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=5.0,
        help="Budget in EUR"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Keine echten API-Calls"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ausführliche Ausgabe"
    )
    parser.add_argument(
        "--web-search",
        action="store_true",
        default=False,
        help="Perplexity Web-Suche als Fallback aktivieren (TEUER! default: False)"
    )
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="Web-Suche deaktivieren"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume von letztem Checkpoint (default: True)"
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Neustart ohne Resume"
    )
    parser.add_argument(
        "--process-all",
        action="store_true",
        help="Verarbeite ALLE Fragen automatisch in Batches (100 pro Durchlauf)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch-Größe für --process-all (default: 100)"
    )
    args = parser.parse_args()

    # Handle --no-web-search flag
    if args.no_web_search:
        args.web_search = False

    # Handle --no-resume flag
    if args.no_resume:
        args.resume = False

    # Bei --process-all: automatisch Resume aktivieren und höheres Limit
    if args.process_all:
        args.resume = True
        args.limit = args.batch_size  # Limit pro Batch

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    base_dir = Path(__file__).resolve().parent.parent
    unanswered_path = base_dir / args.unanswered
    blocks_path = base_dir / args.blocks

    if not unanswered_path.exists():
        logger.error(f"Unbeantwortete Fragen nicht gefunden: {unanswered_path}")
        return 1

    # Bei --process-all: Äußere Schleife bis alle Fragen beantwortet
    if args.process_all:
        return run_all_batches(args, base_dir, unanswered_path, blocks_path)

    # Normaler Einzeldurchlauf
    return run_single_batch(args, base_dir, unanswered_path, blocks_path)


def run_all_batches(args, base_dir: Path, unanswered_path: Path, blocks_path: Path) -> int:
    """
    Verarbeitet ALLE Fragen automatisch in Batches.
    Läuft in einer Schleife bis keine neuen Fragen mehr übrig sind.
    """
    batch_num = 0
    total_cost = 0.0
    total_new_answers = 0

    print(f"\n{'='*60}")
    print(f"🚀 AUTOMATISCHE BATCH-VERARBEITUNG GESTARTET")
    print(f"   Batch-Größe: {args.batch_size}")
    print(f"   Budget pro Batch: €{args.budget}")
    print(f"{'='*60}")

    while True:
        batch_num += 1
        print(f"\n{'='*60}")
        print(f"📦 BATCH {batch_num} STARTET")
        print(f"{'='*60}")

        # Prüfe wie viele Fragen noch offen sind
        question_blocks = load_question_blocks(unanswered_path, blocks_path)
        total_remaining = sum(len(b['questions']) for b in question_blocks)

        # Lade bereits beantwortete aus Checkpoint
        output_path = base_dir / args.output
        existing, answered_questions = load_checkpoint(output_path)
        already_answered = len(existing)

        # Berechne effektiv noch offene Fragen
        open_questions = 0
        for block in question_blocks:
            for q in block['questions']:
                key = f"{block['source_file']}::{q}"
                if key not in answered_questions:
                    open_questions += 1

        print(f"\n📊 Status:")
        print(f"   ✅ Bereits beantwortet: {already_answered}")
        print(f"   ❓ Noch offen: {open_questions}")

        if open_questions == 0:
            print(f"\n🎉 ALLE FRAGEN BEANTWORTET!")
            print(f"   Total: {already_answered} Antworten")
            print(f"   Kosten gesamt: €{total_cost:.4f}")
            break

        # Führe Batch aus
        result = run_single_batch(args, base_dir, unanswered_path, blocks_path)

        # Nach dem Batch: Prüfe Fortschritt
        _, new_answered = load_checkpoint(output_path)
        new_count = len(new_answered) - already_answered

        if new_count == 0:
            print(f"\n⚠️  Keine neuen Antworten in diesem Batch.")
            print(f"   Mögliche Gründe: Budget erschöpft, API-Fehler")
            print(f"   Abbruch nach {batch_num} Batches.")
            break

        total_new_answers += new_count
        print(f"\n✅ Batch {batch_num} abgeschlossen: {new_count} neue Antworten")

        # Kurze Pause zwischen Batches
        print(f"\n⏳ Pause 2s vor nächstem Batch...")
        time.sleep(2)

    print(f"\n{'='*60}")
    print(f"📊 ZUSAMMENFASSUNG")
    print(f"   Batches: {batch_num}")
    print(f"   Neue Antworten: {total_new_answers}")
    print(f"{'='*60}")

    return 0


def run_single_batch(args, base_dir: Path, unanswered_path: Path, blocks_path: Path) -> int:
    """
    Führt einen einzelnen Batch-Durchlauf aus.
    """
    print(f"\n📚 Lade Fragen-Blöcke...")
    question_blocks = load_question_blocks(unanswered_path, blocks_path)
    total_questions = sum(len(b['questions']) for b in question_blocks)
    print(f"   {len(question_blocks)} Blöcke mit {total_questions} Fragen geladen")

    # ZUERST Checkpoint laden um bereits beantwortete Fragen zu kennen
    output_path = base_dir / args.output
    answered_questions = set()
    if args.resume:
        _, answered_questions = load_checkpoint(output_path)
        print(f"   Checkpoint: {len(answered_questions)} bereits beantwortet")

    # Limit auf UNBEANTWORTETE Fragen anwenden
    unanswered_counted = 0
    blocks_to_process = []
    for block in question_blocks:
        if unanswered_counted >= args.limit:
            break
        # Zähle nur unbeantwortete Fragen in diesem Block
        source = block['source_file']
        unanswered_in_block = sum(
            1 for q in block['questions']
            if f"{source}::{q}" not in answered_questions
        )
        if unanswered_in_block > 0:
            blocks_to_process.append(block)
            unanswered_counted += unanswered_in_block

    print(f"\n🎯 Verarbeite {len(blocks_to_process)} Blöcke mit ~{unanswered_counted} OFFENEN Fragen (Limit: {args.limit})")

    # Lade Gold Standard Wissensbasis
    print("\n📖 Lade Gold Standard Wissensbasis...")
    knowledge_base = load_gold_standard_knowledge(base_dir)
    print(f"   {len(knowledge_base)} Themen aus KP Münster geladen")

    # Initialisiere Systeme
    print("\n⚙️  Initialisiere RAG-System...")
    try:
        from core.rag_system import get_rag_system
        rag = get_rag_system(use_openai=False)

        # Lade gespeicherte Wissensbasis
        kb_path = base_dir / "_OUTPUT/rag_knowledge_base.json"
        if kb_path.exists():
            print(f"   Lade Wissensbasis: {kb_path}")
            rag.load_knowledge_base(str(kb_path))
            print(f"   {len(rag.knowledge_base)} Einträge geladen")
        else:
            logger.warning(f"Wissensbasis nicht gefunden: {kb_path}")

        print("   RAG-System bereit")

        # Initialisiere Validation Pipeline mit RAG-System (STRICT MODE)
        print("\n⚙️  Initialisiere Validation Pipeline (STRICT MODE)...")
        try:
            validation_pipeline = get_validation_pipeline(rag_system=rag, strict_mode=True)
            print("   ✅ Validation Pipeline mit RAG-System verbunden")
        except Exception as vp_err:
            logger.warning(f"Validation Pipeline Initialisierung fehlgeschlagen: {vp_err}")

    except Exception as e:
        logger.warning(f"RAG-System nicht verfügbar: {e}")
        rag = None

    print("\n⚙️  Initialisiere API-Client...")
    try:
        from core.unified_api_client import UnifiedAPIClient
        api_client = UnifiedAPIClient()
        print("   API-Client bereit")
    except Exception as e:
        logger.error(f"API-Client Fehler: {e}")
        return 1

    # Web-Suche Status
    if args.web_search:
        print("\n🌐 Perplexity Web-Suche: AKTIVIERT (Fallback für fehlende RAG-Treffer)")
    else:
        print("\n🌐 Perplexity Web-Suche: DEAKTIVIERT")

    # Generiere Antworten - Block für Block
    # (answered_questions und output_path bereits oben geladen)

    # Resume: Lade existierende Antworten-Liste für Speichern
    if args.resume:
        generated, _ = load_checkpoint(output_path)  # answered_questions bereits oben geladen
        if generated:
            print(f"\n📥 Resume: {len(generated)} bereits beantwortete Fragen geladen")
    else:
        generated = []

    cost_used = 0.0
    question_count = 0
    skipped_count = 0
    budget_hit = False

    print(f"\n🚀 Starte Generierung (Budget: €{args.budget})...\n")

    for block_idx, block in enumerate(blocks_to_process, 1):
        if cost_used >= args.budget or budget_hit:
            print(f"\n⚠️  Budget erschöpft (€{cost_used:.2f})")
            break

        block_questions = block['questions']
        all_questions = block['all_block_questions']
        context = block.get('context', [])
        source = block['source_file']

        print(f"\n📦 Block {block_idx}/{len(blocks_to_process)} ({len(block_questions)} Fragen)")

        # Verarbeite jede Frage im Block, mit vorherigen Fragen als Kontext
        block_had_new_questions = False
        for q_idx, question in enumerate(block_questions):
            question_count += 1

            if cost_used >= args.budget:
                break

            # Skip bereits beantwortete Fragen (Resume-Modus)
            question_key = f"{source}::{question}"
            if question_key in answered_questions:
                skipped_count += 1
                continue

            # Finde Position dieser Frage im Original-Block
            try:
                pos_in_block = all_questions.index(question)
            except ValueError:
                pos_in_block = 0

            # Vorherige Fragen im Block als Kontext (für Folgefragen)
            related_questions = all_questions[:pos_in_block] if pos_in_block > 0 else []
            block_had_new_questions = True

            # Markiere Folgefragen
            is_followup = is_followup_question(question)
            followup_marker = " [Folgefrage]" if is_followup else ""

            print(f"  [{question_count}] {question[:55]}...{followup_marker}")

            # RAG-Kontext holen (nutze alle Block-Fragen für bessere Suche)
            search_query = question
            if is_followup and related_questions:
                # Bei Folgefragen: Kombiniere mit vorheriger Frage für RAG
                search_query = f"{related_questions[-1]} {question}"

            rag_context = get_rag_context(search_query, context, rag, knowledge_base, use_web_search=args.web_search)

            if args.dry_run:
                print("      [DRY-RUN] Übersprungen")
                continue

            # Modellwahl nach Frage-Komplexität
            complexity = estimate_question_complexity(question, rag_context)
            provider_choice, model_choice = select_provider_model(complexity)
            print(f"      Modellwahl: {model_choice or 'auto'} ({provider_choice or 'auto'}, {complexity})")

            # Generiere Antwort MIT Kontext von vorherigen Fragen
            # Erstelle eindeutige question_id für Logging
            q_id = f"{source}_{pos_in_block}"
            try:
                result = generate_answer_with_llm(
                    question, context, rag_context, api_client,
                    related_questions=related_questions if is_followup else None,
                    question_id=q_id,
                    preferred_provider=provider_choice,
                    override_model=model_choice
                )
            except BudgetExceededError as e:
                print(f"      ⚠️ Budget erreicht: {e}")
                budget_hit = True
                break

            if result['success']:
                leitlinie, evidenzgrad = extract_leitlinie_reference(
                    result['answer'], rag_context
                )

                answer = EvidenzAnswer(
                    frage=question,
                    source_file=source,
                    context=context + related_questions,  # Speichere auch vorherige Fragen
                    antwort=result['answer'],
                    leitlinie=leitlinie,
                    evidenzgrad=evidenzgrad,
                    quellen=[ctx['source'] for ctx in rag_context[:3]],
                    rag_chunks_used=len(rag_context),
                    generated_at=datetime.now().isoformat(),
                    validation=result.get('validation')
                )
                generated.append(answer.to_dict())

                # Zeige Validierungs-Status
                val_meta = result.get('validation', {})
                if val_meta and not val_meta.get('skipped'):
                    is_valid = val_meta.get('is_valid', True)
                    confidence = val_meta.get('confidence', 0)
                    issues = val_meta.get('issues', [])
                    status_icon = "✓" if is_valid else "⚠"
                    print(f"      {status_icon} Validierung: {'OK' if is_valid else 'WARNUNG'} (Konfidenz: {confidence:.0%})")

                # Inkrementelles Speichern nach jeder Antwort
                save_checkpoint(output_path, generated, block_idx, len(blocks_to_process))

                # Frage als beantwortet markieren
                answered_questions.add(question_key)

                # Kosten tracken
                cost = result.get('cost')
                if cost is None:
                    usage = result.get('usage', {})
                    tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                    cost = tokens * 0.000003  # Fallback-Schätzung
                cost_used += float(cost or 0.0)

                print(f"      ✅ Beantwortet ({result['provider']})")
            else:
                print(f"      ❌ Fehler: {result.get('error', 'Unknown')}")

            # Rate limiting
            time.sleep(0.5)

        # Block-Ende: Checkpoint speichern wenn neue Fragen beantwortet wurden
        if block_had_new_questions:
            save_checkpoint(output_path, generated, block_idx, len(blocks_to_process))
            print(f"   💾 Checkpoint: {len(generated)} Antworten gespeichert")

        if budget_hit:
            break

    # Speichern
    output_path = base_dir / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open('w', encoding='utf-8') as f:
        json.dump(generated, f, ensure_ascii=False, indent=2)

    # Kosten-Report vom API-Client holen und speichern
    cost_report = api_client.get_cost_report()

    new_answers = len(generated) - (len(answered_questions) - skipped_count) if args.resume else len(generated)

    print(f"\n📊 ERGEBNIS:")
    print(f"   ✅ {len(generated)} Antworten total ({new_answers} neu generiert)")
    if skipped_count > 0:
        print(f"   ⏭️  {skipped_count} Fragen übersprungen (bereits beantwortet)")
    print(f"   📦 {len(blocks_to_process)} Blöcke verarbeitet")
    print(f"   💰 Kosten (lokal): €{cost_used:.4f}")
    print(f"   💰 Kosten (API-Client): ${cost_report['total_cost']:.4f}")
    print(f"   📝 Requests: {cost_report['total_requests']}")
    print(f"   💾 Gespeichert: {output_path}")

    # Kosten-Report in _OUTPUT speichern
    cost_report_path = base_dir / "_OUTPUT" / "cost_report.json"
    cost_report["run_timestamp"] = datetime.now().isoformat()
    cost_report["questions_processed"] = len(generated)
    cost_report["blocks_processed"] = len(blocks_to_process)
    with cost_report_path.open('w', encoding='utf-8') as f:
        json.dump(cost_report, f, ensure_ascii=False, indent=2)
    print(f"   📈 Kosten-Report: {cost_report_path}")

    # Provider-Aufschlüsselung
    if cost_report.get('provider_spend'):
        print("\n   Provider-Kosten:")
        for provider, spend in cost_report['provider_spend'].items():
            if spend > 0:
                print(f"      {provider}: ${spend:.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
