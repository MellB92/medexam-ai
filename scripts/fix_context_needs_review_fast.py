#!/usr/bin/env python3
"""
Phase 1: Kontext-Fix für NeedsReview-Karten (OPTIMIERTE VERSION)

Strategie:
1. Index erstellen: normalisierte Fragen → (context, source)
2. Nur schnelles Lookup verwenden
3. Hauptziel: missing_context nur bei echten Folgefragen behalten
"""

import json
import re
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import defaultdict


def is_followup_question(text: str) -> Tuple[bool, str]:
    """
    Erkennt Folgefragen. Gibt (is_followup, reason) zurück.
    """
    text_lower = text.lower().strip()

    # Pattern 1: Pronominaladverbien
    pronominal = [
        (r"\bdamit\b", "Pronominaladverb 'damit'"),
        (r"\bdavon\b", "Pronominaladverb 'davon'"),
        (r"\bdarauf\b", "Pronominaladverb 'darauf'"),
        (r"\bdaran\b", "Pronominaladverb 'daran'"),
        (r"\bdaraus\b", "Pronominaladverb 'daraus'"),
        (r"\bdafür\b", "Pronominaladverb 'dafür'"),
        (r"\bdagegen\b", "Pronominaladverb 'dagegen'"),
        (r"\bdabei\b", "Pronominaladverb 'dabei'"),
        (r"\bdanach\b", "Pronominaladverb 'danach'"),
        (r"\bdavor\b", "Pronominaladverb 'davor'"),
    ]

    for pattern, reason in pronominal:
        if re.search(pattern, text_lower):
            return True, reason

    # Pattern 2: Typische Folgefragen-Starter
    starters = [
        (r"^und\s+(was|wie|welche|warum)", "'Und was/wie/welche...'"),
        (r"^was\s+noch\b", "'Was noch...'"),
        (r"^welche\s+weiteren?\b", "'Welche weiteren...'"),
        (r"^sonst\s+noch\b", "'Sonst noch...'"),
        (r"^noch\s+(was|etwas)\b", "'Noch was/etwas...'"),
        (r"^und\s+dann\b", "'Und dann...'"),
        (r"^dann\s*\?", "'Dann?'"),
    ]

    for pattern, reason in starters:
        if re.search(pattern, text_lower):
            return True, reason

    # Pattern 3: Nur Fragepronomen
    if re.match(r"^(was|wie|warum|wozu)\s*\?*$", text_lower):
        return True, "Nur Fragepronomen"

    # Pattern 4: Sehr kurze Fragen ohne medizinische Begriffe
    if len(text) < 25:
        medical_terms = [
            "diagnose", "therapie", "symptom", "medikament", "dosis",
            "nebenwirk", "indikation", "kontraind", "pathophysio",
            "ätiologie", "prognose", "definition", "klassifik",
            "stadium", "score", "labor", "ekg", "röntgen", "ct", "mrt",
            "impf", "virus", "bakter", "antib", "herz", "lunge", "niere",
            "leber", "tumor", "krebs", "schmerz", "blut", "zucker"
        ]
        if not any(term in text_lower for term in medical_terms):
            return True, f"Kurze Frage ohne med. Begriffe ({len(text)} Zeichen)"

    return False, ""


def normalize_for_index(text: str) -> str:
    """Normalisiert Text für Index-Lookup."""
    text = re.sub(r'<[^>]+>', '', text)  # HTML entfernen
    text = re.sub(r'[^\w\s]', '', text)  # Sonderzeichen entfernen
    text = re.sub(r'\s+', ' ', text)  # Whitespace normalisieren
    return text.lower().strip()


def build_question_index(original_blocks: List[Dict]) -> Dict[str, Tuple[List[str], str]]:
    """
    Baut einen Index: normalisierte Frage → (context, source_file)
    """
    index = {}

    for block in original_blocks:
        questions = block.get("questions", [])
        context = block.get("context", [])
        source = block.get("source_file", "")

        for q in questions:
            q_norm = normalize_for_index(q)
            if q_norm and len(q_norm) > 5:  # Nur sinnvolle Fragen
                index[q_norm] = (context, source)

                # Auch Varianten speichern (erste 50 Zeichen)
                if len(q_norm) > 50:
                    index[q_norm[:50]] = (context, source)

    return index


def find_context_fast(
    question: str,
    question_index: Dict[str, Tuple[List[str], str]]
) -> Tuple[List[str], str, bool]:
    """Schnelles Kontext-Lookup."""
    q_norm = normalize_for_index(question)

    # Exakter Match
    if q_norm in question_index:
        ctx, src = question_index[q_norm]
        return ctx, src, True

    # Prefix-Match (erste 50 Zeichen)
    if len(q_norm) > 50:
        prefix = q_norm[:50]
        if prefix in question_index:
            ctx, src = question_index[prefix]
            return ctx, src, True

    # Substring-Match in Index-Keys (begrenzt auf erste 1000)
    for key in list(question_index.keys())[:1000]:
        if q_norm in key or key in q_norm:
            ctx, src = question_index[key]
            return ctx, src, True

    return [], "", False


def format_context_html(context: List[str]) -> str:
    """Formatiert Kontext als HTML."""
    if not context:
        return ""

    context_text = " ".join(context[:3])
    if len(context_text) > 400:
        context_text = context_text[:400] + "..."

    # Escape HTML in context
    context_text = context_text.replace("<", "&lt;").replace(">", "&gt;")

    return f'<b>Kontext:</b> <i>{context_text}</i><br><br>'


def process_cards(input_tsv: Path, original_blocks_file: Path, output_tsv: Path) -> Dict[str, Any]:
    """Hauptverarbeitung."""

    # Lade Original-Blöcke und baue Index
    print("Lade Original-Blöcke...")
    with original_blocks_file.open(encoding="utf-8") as f:
        original_blocks = json.load(f)

    print(f"  → {len(original_blocks)} Blöcke geladen")

    print("Baue Fragen-Index...")
    question_index = build_question_index(original_blocks)
    print(f"  → {len(question_index)} Einträge im Index")

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
        "followup_kept": [],
        "context_added": [],
        "no_context": [],
    }

    output_lines = []

    print("Verarbeite Karten...")
    with input_tsv.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split('\t')
            if len(parts) < 2:
                continue

            stats["total"] += 1
            question = parts[0]
            answer_part = parts[1] if len(parts) > 1 else ""

            # Tags am Ende extrahieren
            # Format: Antwort<small>...</small>\ttag1 tag2 tag3
            # oder: Antwort\ttag1 tag2 tag3
            tag_match = re.search(r'((?:[\w:-]+::\S+\s*)+)$', answer_part)
            if tag_match:
                tags_str = tag_match.group(1).strip()
                answer = answer_part[:tag_match.start()].strip()
            else:
                tags_str = ""
                answer = answer_part

            tags = tags_str.split() if tags_str else []

            # Folgefrage prüfen
            is_followup, followup_reason = is_followup_question(question)

            if is_followup:
                stats["followup_true"] += 1
            else:
                stats["followup_false"] += 1

            # Kontext suchen
            context, source, found = find_context_fast(question, question_index)

            if found:
                stats["context_found"] += 1
            else:
                stats["context_not_found"] += 1

            # Tags aktualisieren
            new_tags = [t for t in tags
                       if not t.startswith("review::missing_context")
                       and not t.startswith("context::")]

            if is_followup:
                # Echte Folgefrage: Tag behalten
                new_tags.append("review::missing_context")
                new_tags.append("context::followup")
                stats["missing_context_kept"] += 1

                if len(examples["followup_kept"]) < 10:
                    examples["followup_kept"].append({
                        "q": question[:80],
                        "reason": followup_reason
                    })
            else:
                # Keine Folgefrage: Tag ENTFERNEN
                stats["missing_context_removed"] += 1

                if found and context:
                    context_html = format_context_html(context)
                    answer = context_html + answer
                    new_tags.append("context::found")

                    if len(examples["context_added"]) < 10:
                        examples["context_added"].append({
                            "q": question[:80],
                            "ctx": " ".join(context)[:80]
                        })
                else:
                    new_tags.append("context::not_found")

                    if len(examples["no_context"]) < 10:
                        examples["no_context"].append(question[:80])

            # Ausgabe zusammenbauen
            new_line = f"{question}\t{answer}\t{' '.join(new_tags)}"
            output_lines.append(new_line)

            if stats["total"] % 500 == 0:
                print(f"  → {stats['total']} Karten verarbeitet...")

    # Output schreiben
    print(f"Schreibe {len(output_lines)} Zeilen nach {output_tsv}...")
    with output_tsv.open("w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    return stats, examples


def main():
    base = Path("/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617")

    input_tsv = base / "_OUTPUT" / "anki_all_gpt52_needs_review.tsv"
    original_blocks = base / "_EXTRACTED_FRAGEN" / "frage_bloecke_original.json"
    output_tsv = base / "_OUTPUT" / "anki_all_gpt52_needs_review_context_fixed.tsv"
    report_file = base / "_OUTPUT" / "phase1_context_fix_report.md"

    print("=" * 60)
    print("Phase 1: Kontext-Fix für NeedsReview-Karten")
    print("=" * 60)

    stats, examples = process_cards(input_tsv, original_blocks, output_tsv)

    # Report erstellen
    report = f"""# Phase 1: Kontext-Fix Report

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| **Total Karten** | {stats['total']} |
| Echte Folgefragen | {stats['followup_true']} ({100*stats['followup_true']/max(1,stats['total']):.1f}%) |
| Keine Folgefragen | {stats['followup_false']} ({100*stats['followup_false']/max(1,stats['total']):.1f}%) |
| Kontext gefunden | {stats['context_found']} |
| Kontext nicht gefunden | {stats['context_not_found']} |

## Ergebnis

### ✅ **{stats['missing_context_removed']} Karten sind jetzt lernbar!**

Diese Karten hatten vorher `review::missing_context` und waren blockiert.

### ⚠️ {stats['missing_context_kept']} echte Folgefragen

Diese behalten den `review::missing_context` Tag, weil sie ohne Kontext keinen Sinn ergeben.

---

## Beispiele: Echte Folgefragen (Tag behalten)

| Frage | Grund |
|-------|-------|
"""
    for ex in examples["followup_kept"]:
        report += f"| {ex['q']}... | {ex['reason']} |\n"

    report += """
## Beispiele: Kontext erfolgreich hinzugefügt

| Frage | Kontext |
|-------|---------|
"""
    for ex in examples["context_added"]:
        report += f"| {ex['q']}... | {ex['ctx']}... |\n"

    report += """
## Beispiele: Kein Kontext verfügbar (trotzdem lernbar)

"""
    for ex in examples["no_context"]:
        report += f"- {ex}...\n"

    report += f"""
---

## Output-Datei

`{output_tsv}`

## Nächster Schritt

Diese Datei kann für Phase 2 (Pending-Validierung) verwendet werden.
"""

    with report_file.open("w", encoding="utf-8") as f:
        f.write(report)

    print("\n" + "=" * 60)
    print("FERTIG!")
    print(f"  ✅ {stats['missing_context_removed']} Karten jetzt lernbar")
    print(f"  ⚠️  {stats['missing_context_kept']} Folgefragen behalten Tag")
    print(f"  📄 Report: {report_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
