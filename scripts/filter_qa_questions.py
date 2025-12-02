#!/usr/bin/env python3
"""
Filter für QA-Datensatz
=======================

Filtert problematische Fragen aus cleaned_qa.json:
- Zu kurze Fragen ohne Kontext
- Generische Fragen ohne medizinischen Bezug
- Antwort-Fragmente (falsch identifizierte Fragen)

Verwendet: Von generate_answers_incremental.py vor der Generierung
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Medizinische Keywords für Kontext-Check
MEDICAL_KEYWORDS = {
    'patient', 'therapie', 'diagnose', 'symptom', 'medikament',
    'behandlung', 'erkrankung', 'krankheit', 'untersuchung', 'befund',
    'operation', 'anamnese', 'prognose', 'indikation', 'kontraindikation',
    'dosierung', 'nebenwirkung', 'syndrom', 'fraktur', 'tumor',
    'infektion', 'entzündung', 'blutung', 'schmerz', 'fieber',
    'labor', 'röntgen', 'ct', 'mrt', 'ekg', 'ultraschall',
    'diabetes', 'hypertonie', 'herzinsuffizienz', 'pneumonie',
    'sepsis', 'anämie', 'antibioti', 'insulin', 'blutdruck',
    'leber', 'niere', 'herz', 'lunge', 'gehirn', 'magen', 'darm',
    'arzt', 'ärztin', 'pflege', 'klinik', 'station', 'notfall',
    'akut', 'chronisch', 'primär', 'sekundär', 'differenzial',
    'staging', 'klassifikation', 'score', 'leitlinie', 'evidenz',
    'tnm', 'child-pugh', 'meld', 'nyha', 'apache', 'sofa', 'qsofa',
    'präoperativ', 'postoperativ', 'perioperativ', 'intensiv',
    'elektrolyt', 'kalium', 'natrium', 'calcium', 'kreatinin',
    'hämoglobin', 'leukozyten', 'thrombozyten', 'crp', 'prokalzitonin',
}

# Generische Muster (ohne medizinischen Kontext problematisch)
GENERIC_PATTERNS = [
    r'^was machen sie\??$',
    r'^was tun sie\??$',
    r'^wie gehen sie vor\??$',
    r'^was ist zu tun\??$',
    r'^wie reagieren sie\??$',
    r'^was empfehlen sie\??$',
    r'^was schlagen sie vor\??$',
    r'^was ist ihre meinung\??$',
    r'^was denken sie\??$',
]

# Antwort-Fragment-Muster
ANSWER_FRAGMENT_PATTERNS = [
    r'^ja,?\s',
    r'^nein,?\s',
    r'^richtig[,.]',
    r'^falsch[,.]',
    r'^das ist',
    r'^dies ist',
    r'^es handelt sich',
    r'^bei .+ handelt es sich',
    r'^man sollte',
    r'^wichtig ist',
    r'^zunächst',
    r'^\d+\.\s+',  # Nummerierte Aufzählungen
]


def has_medical_context(text: str, case_context: str = None, topic: str = None) -> bool:
    """Prüft ob medizinischer Kontext vorhanden ist."""
    combined = f"{text} {case_context or ''} {topic or ''}".lower()

    for keyword in MEDICAL_KEYWORDS:
        if keyword in combined:
            return True
    return False


def is_too_short(question: str, min_length: int = 25) -> bool:
    """Prüft ob Frage zu kurz ist."""
    return len(question.strip()) < min_length


def is_generic_without_context(question: str) -> bool:
    """Prüft ob Frage generisch ohne Kontext ist."""
    q_lower = question.lower().strip()
    for pattern in GENERIC_PATTERNS:
        if re.match(pattern, q_lower, re.IGNORECASE):
            return True
    return False


def is_answer_fragment(text: str) -> bool:
    """Prüft ob Text ein Antwort-Fragment statt Frage ist."""
    t_lower = text.lower().strip()
    for pattern in ANSWER_FRAGMENT_PATTERNS:
        if re.match(pattern, t_lower, re.IGNORECASE):
            return True
    return False


def analyze_question(q: dict) -> dict:
    """
    Analysiert eine einzelne Frage und gibt Probleme zurück.

    Returns:
        {
            'skip_generation': bool,
            'skip_reason': str or None,
            'skip_category': str or None
        }
    """
    question = q.get('question', '')
    case_context = q.get('case_context', '')
    topic = q.get('topic', '')

    # Bereits beantwortet = nicht prüfen
    if q.get('answer'):
        return {'skip_generation': False, 'skip_reason': None, 'skip_category': None}

    # 1. Antwort-Fragment-Check (höchste Priorität)
    if is_answer_fragment(question):
        return {
            'skip_generation': True,
            'skip_reason': 'Antwort-Fragment statt Frage erkannt',
            'skip_category': 'antwort_fragment'
        }

    # 2. Zu kurz ohne medizinischen Kontext
    if is_too_short(question) and not has_medical_context(question, case_context, topic):
        return {
            'skip_generation': True,
            'skip_reason': f'Zu kurz ({len(question)} Zeichen) ohne medizinischen Kontext',
            'skip_category': 'zu_kurz_ohne_kontext'
        }

    # 3. Generisch ohne Kontext
    if is_generic_without_context(question) and not has_medical_context(question, case_context, topic):
        return {
            'skip_generation': True,
            'skip_reason': 'Generische Frage ohne medizinischen Kontext',
            'skip_category': 'generisch_ohne_kontext'
        }

    return {'skip_generation': False, 'skip_reason': None, 'skip_category': None}


def filter_qa_dataset(
    input_path: Path,
    output_path: Path = None,
    mark_only: bool = True,
    verbose: bool = False
) -> dict:
    """
    Filtert/markiert problematische Fragen im QA-Datensatz.

    Args:
        input_path: Pfad zur Input-JSON
        output_path: Pfad zur Output-JSON (default: überschreibt input)
        mark_only: True = markiert Fragen, False = entfernt sie
        verbose: Detaillierte Ausgabe

    Returns:
        Statistik-Dictionary
    """
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    qa_pairs = data.get('qa_pairs', [])

    stats = {
        'total': len(qa_pairs),
        'with_answer': 0,
        'skipped': defaultdict(list),
        'suitable_for_generation': 0,
        'filtered_at': datetime.now().isoformat()
    }

    filtered_pairs = []

    for i, q in enumerate(qa_pairs):
        if q.get('answer'):
            stats['with_answer'] += 1
            filtered_pairs.append(q)
            continue

        analysis = analyze_question(q)

        if analysis['skip_generation']:
            if mark_only:
                # Markiere die Frage
                q['skip_generation'] = True
                q['skip_reason'] = analysis['skip_reason']
                q['skip_category'] = analysis['skip_category']
                filtered_pairs.append(q)
            # Else: nicht hinzufügen (entfernen)

            stats['skipped'][analysis['skip_category']].append({
                'index': i,
                'question': q.get('question', '')[:80],
                'reason': analysis['skip_reason']
            })

            if verbose:
                print(f"  ⚠️  [{analysis['skip_category']}] {q.get('question', '')[:60]}...")
        else:
            stats['suitable_for_generation'] += 1
            filtered_pairs.append(q)

    # Update data
    if mark_only:
        data['qa_pairs'] = qa_pairs  # Original mit Markierungen
    else:
        data['qa_pairs'] = filtered_pairs

    # Metadata hinzufügen
    data['filter_metadata'] = {
        'filtered_at': stats['filtered_at'],
        'total_skipped': sum(len(v) for v in stats['skipped'].values()),
        'skip_categories': {k: len(v) for k, v in stats['skipped'].items()},
        'suitable_for_generation': stats['suitable_for_generation']
    }

    # Speichern
    output_path = output_path or input_path

    # Backup
    if output_path.exists():
        backup_path = output_path.with_suffix('.json.pre_filter_bak')
        import shutil
        shutil.copy(output_path, backup_path)
        print(f"Backup erstellt: {backup_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Filtert problematische Fragen aus QA-Datensatz')
    parser.add_argument('--input', default='_OUTPUT/cleaned_qa.json', help='Input JSON')
    parser.add_argument('--output', help='Output JSON (default: überschreibt input)')
    parser.add_argument('--remove', action='store_true', help='Entfernt statt markiert')
    parser.add_argument('--verbose', '-v', action='store_true', help='Detaillierte Ausgabe')
    parser.add_argument('--dry-run', action='store_true', help='Nur analysieren, nicht speichern')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Fehler: {input_path} nicht gefunden")
        return 1

    output_path = Path(args.output) if args.output else None

    print(f"\n{'='*60}")
    print("QA-FILTER: Problematische Fragen identifizieren")
    print(f"{'='*60}")
    print(f"Input: {input_path}")
    print(f"Modus: {'Entfernen' if args.remove else 'Markieren'}")
    print(f"{'='*60}\n")

    if args.dry_run:
        # Nur Analyse
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        qa_pairs = data.get('qa_pairs', [])
        categories = defaultdict(list)

        for q in qa_pairs:
            if q.get('answer'):
                continue
            analysis = analyze_question(q)
            if analysis['skip_generation']:
                categories[analysis['skip_category']].append(q.get('question', ''))

        print("ANALYSE (Dry-Run):\n")
        total_skip = 0
        for cat, questions in sorted(categories.items()):
            print(f"{cat}: {len(questions)}")
            total_skip += len(questions)
            if args.verbose:
                for q in questions[:5]:
                    print(f"  • {q[:70]}...")
                if len(questions) > 5:
                    print(f"  ... und {len(questions)-5} weitere")
            print()

        without_answer = sum(1 for q in qa_pairs if not q.get('answer'))
        print(f"{'='*60}")
        print(f"Gesamt: {len(qa_pairs)}")
        print(f"Ohne Antwort: {without_answer}")
        print(f"Würden übersprungen: {total_skip}")
        print(f"Geeignet für Generierung: {without_answer - total_skip}")
        return 0

    # Tatsächlich filtern
    stats = filter_qa_dataset(
        input_path,
        output_path,
        mark_only=not args.remove,
        verbose=args.verbose
    )

    print("\n" + "="*60)
    print("ERGEBNIS")
    print("="*60)
    print(f"Gesamt: {stats['total']}")
    print(f"Mit Antwort: {stats['with_answer']}")
    print(f"\nÜbersprungene Kategorien:")
    for cat, items in stats['skipped'].items():
        print(f"  • {cat}: {len(items)}")
    print(f"\nGeeignet für Generierung: {stats['suitable_for_generation']}")
    print(f"\nGespeichert: {output_path or input_path}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
