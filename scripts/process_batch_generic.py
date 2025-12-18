import json
import os
import re
import sys

# Load fragments
with open("_OUTPUT/fragmente_relevant.json", "r") as f:
    all_fragments = json.load(f)

start_idx = int(sys.argv[1])
end_idx = int(sys.argv[2])
output_file = "_OUTPUT/fragmente_rekon_text.json"

batch = all_fragments[start_idx:end_idx]
results = []
unanswerable_count = 0

def get_txt_path(source_file):
    base = source_file
    if "Münster" in base or "Munster" in base:
        files = os.listdir("_PROCESSING/temp_batch_1")
        for f in files:
            if "Münster" in f or "Munster" in f:
                if f.endswith(".txt"):
                    return os.path.join("_PROCESSING/temp_batch_1", f)
    
    return os.path.join("_PROCESSING/temp_batch_1", source_file.replace(".pdf", ".txt"))

for item in batch:
    original = item["original"]
    source = item["source_file"]
    block_id = item.get("block_id", "")
    
    txt_path = get_txt_path(source)
    
    # Try to find the file if it wasn't mapped correctly
    if not os.path.exists(txt_path):
        # Check if we can find it by just the filename in the temp dir
        if os.path.exists(os.path.join("_PROCESSING/temp_batch_1", source.replace(".pdf", ".txt"))):
             txt_path = os.path.join("_PROCESSING/temp_batch_1", source.replace(".pdf", ".txt"))

    if not os.path.exists(txt_path):
        # Skip if file not found (we only copied a few)
        unanswerable_count += 1
        continue

    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        content_norm = " ".join(content.split())
        original_norm = " ".join(original.split())
        original_escaped = re.escape(original_norm)
        
        # Search with context (approx 300 chars)
        match = re.search(f".{{0,300}}{original_escaped}.{{0,300}}", content_norm, re.IGNORECASE)
        
        if match:
            context = match.group(0)
            results.append({
                "index": start_idx + batch.index(item),
                "status": "reconstructable",
                "source_file": source,
                "block_id": block_id,
                "original": original,
                "context": context
            })
        else:
             unanswerable_count += 1

    except Exception as e:
        print(f"Error processing {original}: {e}")
        unanswerable_count += 1

# Load existing results if file exists
existing_results = []
if os.path.exists(output_file):
    try:
        with open(output_file, "r") as f:
            existing_results = json.load(f)
    except:
        pass

# Append new results avoiding duplicates (by index)
existing_indices = {item["index"] for item in existing_results}
for res in results:
    if res["index"] not in existing_indices:
        existing_results.append(res)

# Sort by index
existing_results.sort(key=lambda x: x["index"])

with open(output_file, "w") as f:
    json.dump(existing_results, f, indent=2)

print(json.dumps({
    "batch_processed": len(batch),
    "reconstructable_found": len(results),
    "total_saved": len(existing_results),
    "unanswerable_in_batch": unanswerable_count
}, indent=2))