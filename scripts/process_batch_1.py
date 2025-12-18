import json
import os
import re

# Load fragments
with open("_OUTPUT/fragmente_relevant.json", "r") as f:
    all_fragments = json.load(f)

batch = all_fragments[0:20]
results = []
unanswerable_count = 0

# Mapping from original filename to temp txt file
# 2_5256178696217194970.pdf -> _PROCESSING/temp_batch_1/2_5256178696217194970.txt
# Rechtsmedizin (1).pdf -> _PROCESSING/temp_batch_1/Rechtsmedizin (1).txt
# Kenntnisprüfung Münster Protokolle 2023.pdf -> _PROCESSING/temp_batch_1/Kenntnisprüfung Münster Protokolle 2023.txt

def get_txt_path(source_file):
    base = source_file
    if "Münster" in base or "Munster" in base: # Handle unicode issues simply
        # Find the actual file in the dir
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
    
    if not os.path.exists(txt_path):
        # Fallback for simple name
        txt_path = os.path.join("_PROCESSING/temp_batch_1", source.replace(".pdf", ".txt"))
        
    if not os.path.exists(txt_path):
        results.append({
            "index": batch.index(item),
            "status": "file_not_found",
            "original": original,
            "source": source
        })
        unanswerable_count += 1
        continue

    try:
        with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
        # Simple search
        # Normalize whitespace in content and original
        content_norm = " ".join(content.split())
        original_norm = " ".join(original.split())
        
        # Escape regex special characters in original string
        original_escaped = re.escape(original_norm)
        
        # Search with context
        match = re.search(f".{{0,300}}{original_escaped}.{{0,300}}", content_norm, re.IGNORECASE)
        
        if match:
            context = match.group(0)
            results.append({
                "index": batch.index(item),
                "status": "reconstructable",
                "source_file": source,
                "block_id": block_id,
                "original": original,
                "context": context,
                "new_question": f"RECONSTRUCT_ME: {original}" # Placeholder
            })
        else:
             results.append({
                "index": batch.index(item),
                "status": "unanswerable",
                "original": original,
                "source": source
            })
             unanswerable_count += 1

    except Exception as e:
        results.append({
            "index": batch.index(item),
            "status": "error",
            "error": str(e)
        })
        unanswerable_count += 1

output = {
    "results": results,
    "unanswerable_count": unanswerable_count,
    "batch_range": "0-19"
}

print(json.dumps(output, indent=2))
