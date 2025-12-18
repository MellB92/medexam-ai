#!/usr/bin/env python3
"""
Script to merge new regeneration results back into the original
regeneration file. This is a specialized merge for the empty answer
regeneration process.
"""

import json


def main():
    # Input files
    original_regen_file = "_OUTPUT/evidenz_antworten_gpt5_regen_20251211_094845.json"
    new_regen_results = "_OUTPUT/empty_answers_regen_results.json"
    output_file = "_OUTPUT/evidenz_antworten_gpt5_regen_20251211_merged.json"

    print(f"Loading original regeneration file from {original_regen_file}...")
    with open(original_regen_file, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    print(f"Loading new regeneration results from {new_regen_results}...")
    with open(new_regen_results, "r", encoding="utf-8") as f:
        new_results = json.load(f)

    print(f"Original regeneration file size: {len(original_data)}")
    print(f"New regeneration results size: {len(new_results)}")

    # Create a mapping of original_index to new answer for quick lookup
    new_answers_map = {}
    for result in new_results:
        original_index = result.get("original_index")
        if original_index is not None:
            new_answers_map[original_index] = result

    print(f"Found {len(new_answers_map)} new answers with original indices")

    # Merge the new answers back into the original regeneration file
    merged_count = 0
    missing_indices = []

    for i, original_item in enumerate(original_data):
        if i in new_answers_map:
            # Replace the empty answer with the new regeneration result
            new_item = new_answers_map[i]

            # Update all fields from the new regeneration
            original_data[i]["antwort"] = new_item.get("antwort", "")
            original_data[i]["leitlinie"] = new_item.get("leitlinie", "")
            original_data[i]["quellen"] = new_item.get("quellen", [])
            original_data[i]["context"] = new_item.get("context", [])
            original_data[i]["rag_chunks_used"] = new_item.get("rag_chunks_used", 0)
            original_data[i]["generated_at"] = new_item.get("generated_at", "")
            original_data[i]["model_used"] = new_item.get("model_used", "")
            original_data[i]["reasoning_effort"] = new_item.get("reasoning_effort", "")
            original_data[i]["run_id"] = new_item.get("run_id", "")
            original_data[i]["input_tokens"] = new_item.get("input_tokens", 0)
            original_data[i]["output_tokens"] = new_item.get("output_tokens", 0)
            original_data[i]["cost"] = new_item.get("cost", 0.0)

            # Add a flag indicating this was regenerated in the second pass
            original_data[i]["regen_pass_2"] = True

            merged_count += 1

    print(
        f"Successfully merged {merged_count} new answers "
        f"back into regeneration file"
    )

    # Check if any indices were supposed to be regenerated but weren't
    expected_indices = set(new_answers_map.keys())
    actual_merged_indices = set()
    for i, item in enumerate(original_data):
        if i in new_answers_map:
            actual_merged_indices.add(i)

    missing_indices = expected_indices - actual_merged_indices
    if missing_indices:
        print(
            f"Warning: Missing merged answers for indices: "
            f"{sorted(missing_indices)}"
        )

    print(f"Saving merged regeneration file to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(original_data, f, indent=2, ensure_ascii=False)

    print("Done.")

    # Create a summary
    summary = {
        "original_regen_file": original_regen_file,
        "new_regen_results": new_regen_results,
        "output_file": output_file,
        "original_size": len(original_data),
        "new_results_size": len(new_results),
        "merged_count": merged_count,
        "missing_indices": (sorted(missing_indices) if missing_indices else None),
    }

    summary_file = "_OUTPUT/merge_empty_regen_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"Saved merge summary to {summary_file}")


if __name__ == "__main__":
    main()
