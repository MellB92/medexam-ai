#!/usr/bin/env python3
"""
Phase 1: Kontext-Fix für NeedsReview-Karten

Ziel:
- `review::missing_context` Tag nur bei echten Folgefragen behalten
- Kontext aus frage_bloecke_original.json anreichern
- Rest freigeben zum Lernen

Schritte:
1. Folgefragen identifizieren (is_followup_question Heuristik)
2. Kontext aus Original-Blöcken zuordnen
3. Tags aktualisieren
"""

import json
import re
import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher


def is_followup_question(text: str) -> bool:
    """
    Erkennt Folgefragen, die Kontext von vorherigen Fragen benötigen.
    Adaptiert aus scripts/generate_evidenz_answers.py
    """
    text_lower = text.lower().strip()

    # Patterns für Folgefragen (Pronominaladverbien)
    followup_patterns = [
        r"\bdamit\b",
        r"\bdavon\b",
        r"\bdarauf\b",
        r"\bdaran\b",
        r"\bdaraus\b",
        r"\bdafür\b",
        r"\bdagegen\b",
        r"\bdarüber\b",
        r"\bdarunter\b",
        r"\bdabei\b",
        r"\bdahin\b",
        r"\bdaher\b",
        r"\bdavor\b",
        r"\bdanach\b",
        r"\bdazwischen\b",
        r"^und\s+(was|wie|welche|warum)",  # "Und was..." am Satzanfang
        r"^was\s+noch\b",  # "Was noch..."
        r"^welche\s+weiteren?\b",  # "Welche weiteren..."
        r"^sonst\s+noch\b",  # "Sonst noch..."
        r"^noch\s+(was|etwas)\b",  # "Noch was/etwas..."
    ]

    for pattern in followup_patterns:
        if re.search(pattern, text_lower):
            return True

    # Sehr kurze Fragen (<30 Zeichen) sind oft Folgefragen
    if len(text) < 30:
        # Außer wenn sie medizinische Fachbegriffe enthalten
        medical_terms = [
            "diagnose", "therapie", "symptom", "medikament", "dosis",
            "nebenwirk", "indikation", "kontraind", "pathophysio",
            "ätiologie", "epidemio", "prognose", "definition",
            "klassifik", "stadium", "score", "skala", "labor",
            "bildgebung", "ekg", "röntgen", "ct", "mrt"
        ]
        if not any(term in text_lower for term in medical_terms):
            return True

    # Fragen die nur aus Pronomen bestehen
    pronoun_only = [
        r"^(was|wie|warum|wozu|wofür|weshalb|wieso)\s*\?*$",
        r"^und\s+(dann|jetzt|nun)\s*\?*$",
    ]
    for pattern in pronoun_only:
        if re.search(pattern, text_lower):
            return True

    return False


def normalize_question(q: str) -> str:
    """Normalisiert eine Frage für Vergleiche."""
    # HTML entfernen
    q = re.sub(r'<[^>]+>', '', q)
    # Mehrfache Whitespaces
    q = re.sub(r'\s+', ' ', q)
    # Lowercase und strip
    return q.lower().strip()


def find_context_for_question(
    question: str,
    original_blocks: List[Dict[str, Any]],
    threshold: float = 0.75
) -> Tuple[List[str], str, bool]:
    """
    Findet Kontext für eine Frage aus den Original-Blöcken.

    Returns: (context_list, source_file, found)
    """
    q_norm = normalize_question(question)
    best_match = None
    best_score = 0.0

    for block in original_blocks:
        questions = block.get("questions", [])
        context = block.get("context", [])
        source = block.get("source_file", "")

        for orig_q in questions:
            orig_norm = normalize_question(orig_q)
            # Schneller Check: Substring-Match
            if q_norm in orig_norm or orig_norm in q_norm:
                return context, source, True

            # Similarity-Check
            score = SequenceMatcher(None, q_norm, orig_norm).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = (context, source)

    if best_match:
        return best_match[0], best_match[1], True

    return [], "", False


def parse_tsv_line(line: str) -> Tuple[str, str, str]:
    """
    Parst eine TSV-Zeile und extrahiert Frage, Antwort und Tags.

    Returns: (question, answer_without_tags, tags_string)
    """
    parts = line.strip().split('\t')
    if len(parts) < 2:
        return "", "", ""

    question = parts[0]
    answer_with_tags = parts[1]

    # Tags extrahieren (am Ende, space-separiert)
    # Format: ...text<small>Quelle: xxx</small>\tfachgebiet::xxx review::xxx
    # oder: ...text\tfachgebiet::xxx review::xxx

    # Tags sind am Ende nach dem letzten HTML-Tag oder nach Tab
    tag_pattern = r'((?:[\w:]+::\S+\s*)+)$'
    match = re.search(tag_pattern, answer_with_tags)

    if match:
        tags = match.group(1).strip()
        answer = answer_with_tags[:match.start()].strip()
    else:
        tags = ""
        answer = answer_with_tags

    return question, answer, tags


def format_context_html(context: List[str]) -> str:
    """Formatiert Kontext als HTML für die Karte."""
    if not context:
        return ""

    context_text = " ".join(context[:3])  # Max 3 Kontext-Elemente
    if len(context_text) > 500:
        context_text = context_text[:500] + "..."

    return f'<b>Kontext:</b> {context_text}<br><br>'


def process_needs_review_cards(
    input_tsv: Path,
    original_blocks_file: Path,
    output_tsv: Path,
    report_file: Path
) -> Dict[str, Any]:
    """
    Hauptfunktion: Verarbeitet NeedsReview-Karten.
    """
    # Lade Original-Blöcke
    with original_blocks_file.open(encoding="utf-8") as f:
        original_blocks = json.load(f)

    print(f"Geladen: {len(original_blocks)} Original-Blöcke")

    # Statistiken
    stats = {
        "total": 0,
        "followup_true": 0,
        "followup_false": 0,
        "context_found": 0,
        "context_not_found": 0,
        "missing_context_kept": 0,
        "missing_context_removed": 0,
    }

    examples = {
        "followup_kept": [],  # Echte Folgefragen, missing_context behalten
        "context_added": [],  # Kontext hinzugefügt
        "no_context_available": [],  # Kein Kontext gefunden
    }

    output_lines = []

    with input_tsv.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter='\t')

        for row in reader:
            if len(row) < 2:
                continue

            stats["total"] += 1
            question = row[0]
            answer_with_tags = row[1]

            # Tags extrahieren
            tag_pattern = r'((?:[\w:-]+::\S+\s*)+)$'
            match = re.search(tag_pattern, answer_with_tags)

            if match:
                tags_str = match.group(1).strip()
                answer = answer_with_tags[:match.start()].strip()
            else:
                tags_str = ""
                answer = answer_with_tags

            tags = tags_str.split()

            # Ist es eine Folgefrage?
            is_followup = is_followup_question(question)

            if is_followup:
                stats["followup_true"] += 1
            else:
                stats["followup_false"] += 1

            # Kontext suchen
            context, source, found = find_context_for_question(question, original_blocks)

            if found:
                stats["context_found"] += 1
            else:
                stats["context_not_found"] += 1

            # Tags aktualisieren
            new_tags = [t for t in tags if not t.startswith("review::missing_context")
                       and not t.startswith("context::")]

            if is_followup:
                # Echte Folgefrage: missing_context behalten
                new_tags.append("review::missing_context")
                new_tags.append("context::followup_needs_block")
                stats["missing_context_kept"] += 1

                if len(examples["followup_kept"]) < 10:
                    examples["followup_kept"].append({
                        "question": question[:100],
                        "reason": "Folgefrage erkannt"
                    })
            else:
                # Keine Folgefrage: missing_context ENTFERNEN
                stats["missing_context_removed"] += 1

                if found and context:
                    # Kontext zum Antwort-Anfang hinzufügen
                    context_html = format_context_html(context)
                    answer = context_html + answer
                    new_tags.append("context::found")

                    if len(examples["context_added"]) < 10:
                        examples["context_added"].append({
                            "question": question[:100],
                            "context_preview": " ".join(context)[:100]
                        })
                else:
                    new_tags.append("context::not_found")

                    if len(examples["no_context_available"]) < 10:
                        examples["no_context_available"].append({
                            "question": question[:100]
                        })

            # Neue Zeile erstellen
            new_answer_with_tags = answer + "\t" + " ".join(new_tags)
            output_lines.append(f"{question}\t{new_answer_with_tags}")

    # Output schreiben
    with output_tsv.open("w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"Output geschrieben: {output_tsv}")

    # Report erstellen
    report = f"""# Phase 1: Kontext-Fix Report

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| Total Karten verarbeitet | {stats['total']} |
| Echte Folgefragen | {stats['followup_true']} ({100*stats['followup_true']/stats['total']:.1f}%) |
| Keine Folgefragen | {stats['followup_false']} ({100*stats['followup_false']/stats['total']:.1f}%) |
| Kontext gefunden | {stats['context_found']} |
| Kontext nicht gefunden | {stats['context_not_found']} |
| `missing_context` behalten | {stats['missing_context_kept']} |
| `missing_context` ENTFERNT | {stats['missing_context_removed']} |

## Ergebnis

**{stats['missing_context_removed']} Karten sind jetzt lernbar!** (vorher blockiert durch `missing_context`)

Nur {stats['missing_context_kept']} echte Folgefragen behalten den `review::missing_context` Tag.

## Beispiele: Echte Folgefragen (missing_context behalten)

"""
    for ex in examples["followup_kept"]:
        report += f"- **Frage:** {ex['question']}...\n  - Grund: {ex['reason']}\n"

    report += "\n## Beispiele: Kontext erfolgreich hinzugefügt\n\n"
    for ex in examples["context_added"]:
        report += f"- **Frage:** {ex['question']}...\n  - Kontext: {ex['context_preview']}...\n"

    report += "\n## Beispiele: Kein Kontext verfügbar\n\n"
    for ex in examples["no_context_available"]:
        report += f"- {ex['question']}...\n"

    with report_file.open("w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report geschrieben: {report_file}")

    return stats


def main():
    base_path = Path("/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617")

    input_tsv = base_path / "_OUTPUT" / "anki_all_gpt52_needs_review.tsv"
    original_blocks = base_path / "_EXTRACTED_FRAGEN" / "frage_bloecke_original.json"
    output_tsv = base_path / "_OUTPUT" / "anki_all_gpt52_needs_review_context_fixed.tsv"
    report_file = base_path / "_OUTPUT" / "phase1_context_fix_report.md"

    print("=" * 60)
    print("Phase 1: Kontext-Fix für NeedsReview-Karten")
    print("=" * 60)

    stats = process_needs_review_cards(
        input_tsv,
        original_blocks,
        output_tsv,
        report_file
    )

    print("\n" + "=" * 60)
    print("FERTIG!")
    print(f"  → {stats['missing_context_removed']} Karten jetzt lernbar")
    print(f"  → {stats['missing_context_kept']} echte Folgefragen behalten Tag")
    print("=" * 60)


if __name__ == "__main__":
    main()
