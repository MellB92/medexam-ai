import json
import os
import glob

def find_file(filename, search_path="_GOLD_STANDARD"):
    # Simple walk to find the file
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)
    return None

try:
    with open("_OUTPUT/fragmente_relevant.json", "r") as f:
        data = json.load(f)
    
    batch = data[0:20]
    
    files_to_read = set()
    result = []
    
    for item in batch:
        source = item.get("source_file")
        path = find_file(source)
        files_to_read.add(path if path else f"MISSING: {source}")
        item["full_path"] = path
        result.append(item)
        
    print(json.dumps({"batch": result, "files": list(files_to_read)}, indent=2))

except Exception as e:
    print(f"Error: {e}")
