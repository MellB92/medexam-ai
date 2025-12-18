#!/usr/bin/env python3
"""
Script to extract missing questions (empty answers) from the merged dataset
and prepare them for a final regeneration run.
"""

import json
import os


def main():
    input_file = "_OUTPUT/evidenz_antworten_merged_20251211.json"
    output_file = "_OUTPUT/missing_for_final_regen.json"

    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    missing_questions = []

    # Placeholder indicators from analyze_answers.py
    placeholder_indicators = [
        "",
        "Keine Antwort",
        "N/A",
        "Keine Frage vorhanden",
        "Keine Frage angegeben",
        "keine frage",
        "keine antwort",
        "kein inhalt",
        "keine",
        "unbekannt",
        "nicht bekannt",
        "k.a.",
        "k. a.",
        "entfällt",
        "n/a",
    ]

    for i, entry in enumerate(data):
        is_missing = False
        answer = entry.get("antwort")

        if answer is None:
            is_missing = True
        elif isinstance(answer, str):
            answer_clean = answer.strip()
            if not answer_clean:
                is_missing = True
            elif len(answer_clean) < 30:
                if answer_clean in placeholder_indicators or any(
                    indicator in answer_clean.lower()
                    for indicator in placeholder_indicators
                ):
                    is_missing = True

        if is_missing:
            # Prepare entry for batch_gpt51_run.py
            # It expects "question" and "source_file" keys
            missing_entry = {
                "question": entry.get("frage", ""),
                "source_file": entry.get("source_file", ""),
                "original_index": i,  # Keep track of original index for merging back
            }
            missing_questions.append(missing_entry)

    print(f"Found {len(missing_questions)} missing answers.")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(missing_questions, f, indent=2, ensure_ascii=False)

    print(f"Saved missing questions to {output_file}")


if __name__ == "__main__":
    main()
