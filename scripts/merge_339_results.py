#!/usr/bin/env python3
"""
Merge 339 regenerated answers into main evidenz_antworten.json
"""

import json
import shutil
from datetime import datetime
from pathlib import Path


def main():
    base_dir = Path(__file__).parent.parent

    # Pfade
    main_file = base_dir / "_OUTPUT" / "evidenz_antworten.json"
    regen_file = base_dir / "_OUTPUT" / "evidenz_antworten_regen_339.json"
    backup_file = base_dir / "_OUTPUT" / f"evidenz_antworten_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Prüfe ob regen-Datei existiert
    if not regen_file.exists():
        print(f"ERROR: Regen-Datei nicht gefunden: {regen_file}")
        return 1

    # Backup erstellen
    print(f"Erstelle Backup: {backup_file}")
    shutil.copy(main_file, backup_file)

    # Lade Dateien
    print(f"Lade Hauptdatei: {main_file}")
    with open(main_file, "r", encoding="utf-8") as f:
        main_data = json.load(f)

    print(f"Lade Regen-Datei: {regen_file}")
    with open(regen_file, "r", encoding="utf-8") as f:
        regen_data = json.load(f)

    print(f"\nHauptdatei: {len(main_data)} Einträge")
    print(f"Regen-Datei: {len(regen_data)} Einträge")

    # Erstelle Lookup für existierende Fragen
    existing_questions = {}
    for i, item in enumerate(main_data):
        frage = item.get("frage", "").strip()
        if frage:
            existing_questions[frage] = i

    # Merge: Nur neue hinzufügen, leere ersetzen
    added = 0
    replaced = 0
    skipped_empty = 0

    for regen_item in regen_data:
        frage = regen_item.get("frage", "").strip()
        antwort = regen_item.get("antwort", "").strip()

        # Skip wenn regen-Antwort leer
        if not antwort or len(antwort) < 50:
            skipped_empty += 1
            continue

        if frage in existing_questions:
            # Existiert bereits - prüfe ob wir ersetzen sollten
            idx = existing_questions[frage]
            existing_antwort = main_data[idx].get("antwort", "").strip()

            if not existing_antwort or len(existing_antwort) < 50:
                # Ersetze leere/kurze Antwort
                main_data[idx]["antwort"] = antwort
                main_data[idx]["leitlinie"] = regen_item.get("leitlinie", "")
                main_data[idx]["quellen"] = regen_item.get("quellen", [])
                main_data[idx]["regenerated_at"] = datetime.now().isoformat()
                main_data[idx]["regen_model"] = regen_item.get("model_used", "gpt-5.1")
                replaced += 1
        else:
            # Neue Frage hinzufügen
            main_data.append({
                "frage": frage,
                "source_file": regen_item.get("source_file", ""),
                "antwort": antwort,
                "leitlinie": regen_item.get("leitlinie", ""),
                "quellen": regen_item.get("quellen", []),
                "context": regen_item.get("context", []),
                "rag_chunks_used": regen_item.get("rag_chunks_used", 0),
                "generated_at": regen_item.get("generated_at", ""),
                "model_used": regen_item.get("model_used", ""),
                "run_id": regen_item.get("run_id", ""),
            })
            added += 1

    # Speichern
    print(f"\n=== Merge-Ergebnis ===")
    print(f"Hinzugefügt: {added}")
    print(f"Ersetzt: {replaced}")
    print(f"Übersprungen (leer): {skipped_empty}")
    print(f"Neue Gesamtzahl: {len(main_data)}")

    with open(main_file, "w", encoding="utf-8") as f:
        json.dump(main_data, f, ensure_ascii=False, indent=2)

    print(f"\nGespeichert in: {main_file}")
    print(f"Backup unter: {backup_file}")

    return 0


if __name__ == "__main__":
    exit(main())
