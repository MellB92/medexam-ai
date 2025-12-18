import json


def merge_datasets():
    original_path = "_OUTPUT/evidenz_antworten_gpt5_run_20251210_153531.json"
    regen_path = "_OUTPUT/evidenz_antworten_gpt5_regen_20251211_094845.json"
    output_path = "_OUTPUT/evidenz_antworten_merged_20251211.json"

    print(f"Loading original dataset from {original_path}...")
    with open(original_path, "r", encoding="utf-8") as f:
        original_data = json.load(f)

    print(f"Loading regenerated answers from {regen_path}...")
    with open(regen_path, "r", encoding="utf-8") as f:
        regen_data = json.load(f)

    print(f"Original dataset size: {len(original_data)}")
    print(f"Regenerated answers size: {len(regen_data)}")

    # Create a list of available regenerated items
    # We use a list to handle potential duplicates by consuming them
    regen_items = list(regen_data)

    merged_count = 0
    missing_indices = []

    # Identify indices that were empty in the original dataset
    empty_indices = [
        i
        for i, item in enumerate(original_data)
        if not item.get("antwort") or item.get("antwort") == ""
    ]
    print(f"Found {len(empty_indices)} empty answers in original dataset.")

    for idx in empty_indices:
        original_item = original_data[idx]

        # Find matching item in regen_data
        match_index = -1
        for i, regen_item in enumerate(regen_items):
            # Match by question and source file
            # Cleaning strings to ensure better matching (strip whitespace)
            q_orig = original_item.get("frage", "").strip()
            q_regen = regen_item.get("frage", "").strip()

            s_orig = original_item.get("source_file", "").strip()
            s_regen = regen_item.get("source_file", "").strip()

            if q_orig == q_regen and s_orig == s_regen:
                match_index = i
                break

        if match_index != -1:
            regen_item = regen_items.pop(match_index)

            # Update fields
            original_data[idx]["antwort"] = regen_item.get("antwort", "")
            original_data[idx]["leitlinie"] = regen_item.get("leitlinie", "")
            original_data[idx]["quellen"] = regen_item.get("quellen", [])
            original_data[idx]["context"] = regen_item.get("context", [])
            original_data[idx]["rag_chunks_used"] = regen_item.get("rag_chunks_used", 0)
            original_data[idx]["model_used"] = regen_item.get("model_used", "")
            original_data[idx]["generated_at"] = regen_item.get("generated_at", "")

            # Optional: Add a flag indicating it was regenerated
            original_data[idx]["was_regenerated"] = True

            merged_count += 1
        else:
            missing_indices.append(idx)
            # Handle missing answer (timeout case)
            # Only mark as failed if we truly can't find it.
            # Note: The one failed item might be among these.
            original_data[idx]["antwort"] = "Regeneration failed due to timeout error"
            original_data[idx]["regeneration_failed"] = True

    print(f"Successfully merged {merged_count} answers.")
    if missing_indices:
        print(f"Missing answers for indices: {missing_indices} (marked as failed)")

    if len(regen_items) > 0:
        print(f"Warning: {len(regen_items)} regenerated items were not used.")

    print(f"Saving merged dataset to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(original_data, f, indent=2, ensure_ascii=False)

    print("Done.")


if __name__ == "__main__":
    merge_datasets()
