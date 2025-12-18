#!/usr/bin/env python3
"""
Script to extract empty answers from the regeneration file
and prepare them for a new regeneration run.
"""

import json


def main():
    # Input: The regeneration file that contains empty answers
    input_file = "_OUTPUT/evidenz_antworten_gpt5_regen_20251211_094845.json"

    # Output: File with only the empty answers for regeneration
    output_file = "_OUTPUT/empty_answers_for_regen.json"

    print(f"Reading {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    empty_answers = []

    # Placeholder indicators
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
        is_empty = False
        answer = entry.get("antwort")

        if answer is None:
            is_empty = True
        elif isinstance(answer, str):
            answer_clean = answer.strip()
            if not answer_clean:
                is_empty = True
            elif len(answer_clean) < 30:
                if answer_clean in placeholder_indicators or any(
                    indicator in answer_clean.lower()
                    for indicator in placeholder_indicators
                ):
                    is_empty = True

        if is_empty:
            # Prepare entry for batch_gpt51_run.py
            # It expects "question" and "source_file" keys
            empty_entry = {
                "question": entry.get("frage", ""),
                "source_file": entry.get("source_file", ""),
                "original_index": i,  # Keep track of original index
            }
            empty_answers.append(empty_entry)

    print(f"Found {len(empty_answers)} empty answers in regeneration file.")
    print(f"Total entries in regeneration file: {len(data)}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(empty_answers, f, indent=2, ensure_ascii=False)

    print(f"Saved empty answers to {output_file}")

    # Also create a summary file
    summary = {
        "total_entries_in_regen_file": len(data),
        "empty_answers_found": len(empty_answers),
        "empty_indices": [entry["original_index"] for entry in empty_answers],
        "regen_file": input_file,
        "output_file": output_file,
    }

    summary_file = "_OUTPUT/empty_answers_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Saved summary to {summary_file}")


if __name__ == "__main__":
    main()
