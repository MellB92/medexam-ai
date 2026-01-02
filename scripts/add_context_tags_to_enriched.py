#!/usr/bin/env python3
"""
Phase 1 NEU: Context-Tags zu enriched TSVs HINZUFÜGEN (nicht ersetzen)

Liest enriched TSVs und fügt context:: Tags hinzu:
- context::found - Frage hat Kontext in Original-Datei
- context::not_found - Frage hat keinen Kontext
- context::followup - Frage ist eine Folgefrage (z.B. "Und dann?")

WICHTIG: Bestehende Tags werden BEIBEHALTEN!
"""

import argparse
import csv
import json
import re
import shutil
from pathlib import Path
from datetime import datetime

# Folgefrage-Muster (kontextlose Fragen)
FOLLOWUP_PATTERNS = [
    r'^und\s+(dann|was|wie|noch)\??$',
    r'^was\s+(noch|sonst|meinen sie)\??$',
    r'^wie\s+(noch|weiter|geht)\??$',
    r'^sonst\s+noch\s+was\??$',
    r'^noch\s+(was|etwas)\??$',
    r'^weiter\??$',
    r'^und\??$',
    r'^ja\s+und\??$',
    r'^ok\s+und\??$',
    r'^genau\s+und\??$',
]


def is_followup_question(question: str) -> bool:
    """Prüft ob eine Frage eine Folgefrage ist."""
    q = question.strip().lower()
    for pattern in FOLLOWUP_PATTERNS:
        if re.match(pattern, q, re.IGNORECASE):
            return True
    return False


def normalize_question(q: str) -> str:
    """Normalisiert eine Frage für Matching."""
    q = q.lower().strip()
    q = re.sub(r'[^\w\s]', '', q)
    q = re.sub(r'\s+', ' ', q)
    return q


def load_original_questions(path: str) -> dict:
    """Lädt Original-Fragen mit Kontext."""
    with open(path, 'r', encoding='utf-8') as f:
        blocks = json.load(f)

    # Index: normalisierte Frage -> hat Kontext
    question_context = {}

    for block in blocks:
        questions = block.get('questions', [])
        context = block.get('context', [])
        has_context = bool(context and any(c.strip() for c in context))

        for q in questions:
            if isinstance(q, str):
                norm = normalize_question(q)
                if norm:
                    question_context[norm] = has_context
            elif isinstance(q, dict):
                text = q.get('text', q.get('question', ''))
                norm = normalize_question(text)
                if norm:
                    question_context[norm] = has_context

    return question_context


def add_context_tag(existing_tags: str, context_tag: str) -> str:
    """Fügt context:: Tag zu bestehenden Tags hinzu (ohne Duplikate)."""
    tags = existing_tags.split()

    # Entferne alte context:: Tags falls vorhanden
    tags = [t for t in tags if not t.startswith('context::')]

    # Füge neuen context:: Tag hinzu
    tags.append(context_tag)

    return ' '.join(tags)


def process_enriched_tsv(input_path: str, output_path: str, original_questions: dict) -> dict:
    """Verarbeitet enriched TSV und fügt context:: Tags hinzu."""

    stats = {
        'total': 0,
        'context_found': 0,
        'context_not_found': 0,
        'context_followup': 0,
        'tags_preserved': True
    }

    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            rows.append(row)

    output_rows = []
    for row in rows:
        stats['total'] += 1

        if len(row) < 3:
            # Zeile ohne Tags - behalten wie sie ist
            output_rows.append(row)
            continue

        question = row[0]
        answer = row[1]
        existing_tags = row[2]

        # Bestimme context:: Tag
        if is_followup_question(question):
            context_tag = 'context::followup'
            stats['context_followup'] += 1
        else:
            norm_q = normalize_question(question)
            if norm_q in original_questions and original_questions[norm_q]:
                context_tag = 'context::found'
                stats['context_found'] += 1
            else:
                context_tag = 'context::not_found'
                stats['context_not_found'] += 1

        # Füge Tag hinzu (behalte alle anderen!)
        new_tags = add_context_tag(existing_tags, context_tag)

        output_rows.append([question, answer, new_tags])

    # Schreibe Output
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        for row in output_rows:
            writer.writerow(row)

    return stats


def main():
    parser = argparse.ArgumentParser(description='Füge context:: Tags zu enriched TSVs hinzu')
    parser.add_argument('--input', required=True, help='Input enriched TSV')
    parser.add_argument('--output', required=True, help='Output TSV mit context:: Tags')
    parser.add_argument('--original-questions', default='_EXTRACTED_FRAGEN/frage_bloecke_original.json',
                        help='Original-Fragen JSON für Kontext-Lookup')
    parser.add_argument('--backup', action='store_true', help='Erstelle Backup der Input-Datei')
    args = parser.parse_args()

    # Backup falls gewünscht
    if args.backup and Path(args.input).exists():
        backup_path = f"{args.input}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(args.input, backup_path)
        print(f"Backup erstellt: {backup_path}")

    # Lade Original-Fragen
    print(f"Lade Original-Fragen aus {args.original_questions}...")
    original_questions = load_original_questions(args.original_questions)
    print(f"  {len(original_questions)} Fragen mit Kontext-Info geladen")

    # Verarbeite TSV
    print(f"\nVerarbeite {args.input}...")
    stats = process_enriched_tsv(args.input, args.output, original_questions)

    print(f"\nErgebnis:")
    print(f"  Total: {stats['total']}")
    print(f"  context::found: {stats['context_found']}")
    print(f"  context::not_found: {stats['context_not_found']}")
    print(f"  context::followup: {stats['context_followup']}")
    print(f"\nOutput: {args.output}")


if __name__ == '__main__':
    main()
