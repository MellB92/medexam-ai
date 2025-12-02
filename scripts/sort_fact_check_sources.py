#!/usr/bin/env python3
"""
Sortiert Dateien in _FACT_CHECK_SOURCES nach Kategorie.

Kategorien:
- leitlinien/     - AWMF-Leitlinien, S1/S2/S3, NVL
- vorlesungen/    - Uni-Vorlesungen nach Fachgebiet
- fachinformation/- Medikamenten-Infos
- notizen/        - Markdown-Notizen
- bilder/         - Medizinische Bilder
- _unsortiert/    - Nicht zuordenbar
"""

import shutil
from pathlib import Path
from collections import Counter
import re

BASE_DIR = Path("_FACT_CHECK_SOURCES")
INPUT_DIR = BASE_DIR / "Input Bucket"

# Kategorisierungsregeln
CATEGORY_RULES = {
    "leitlinien": {
        "keywords": ["awmf", "leitlinie", "s1-", "s2-", "s3-", "nvl-", "guideline"],
        "extensions": [".pdf"],
    },
    "vorlesungen/chirurgie": {
        "keywords": ["chirurg", "operation", "hernie", "trauma", "fraktur",
                    "osteosynthese", "hch", "viszeralchirurgie"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "vorlesungen/innere_medizin": {
        "keywords": ["innere", "gastro", "hepat", "kardio", "pneumo", "nephro",
                    "diabetes", "endokrin", "rheuma", "pedp", "ced", "zirrhose"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "vorlesungen/neurologie": {
        "keywords": ["neuro", "hirn", "zerebral", "epileps", "schlaganfall",
                    "parkinson", "demenz", "meningitis"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "vorlesungen/notfallmedizin": {
        "keywords": ["notfall", "reanimation", "schock", "akut", "emergency",
                    "cpr", "acs", "polytrauma"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "vorlesungen/ortho_unfall": {
        "keywords": ["ortho", "unfall", "fraktur", "gelenk", "wirbel", "hws",
                    "bws", "lws", "bandscheibe", "arthrose"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "notizen": {
        "keywords": [],  # Alle MD-Dateien
        "extensions": [".md", ".txt"],
    },
    "bilder": {
        "keywords": [],
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
    },
    "dokumente": {
        "keywords": [],
        "extensions": [".doc", ".docx", ".odt", ".xlsx"],
    },
}


def categorize_file(filepath: Path) -> str:
    """Bestimmt die Kategorie einer Datei."""
    name_lower = filepath.name.lower()
    suffix_lower = filepath.suffix.lower()

    # Ignoriere versteckte Dateien
    if filepath.name.startswith("."):
        return "_skip"

    # Prüfe spezifische Kategorien mit Keywords
    for category, rules in CATEGORY_RULES.items():
        keywords = rules.get("keywords", [])
        extensions = rules.get("extensions", [])

        # Nur wenn Extension passt oder keine Extensions definiert
        if extensions and suffix_lower not in extensions:
            continue

        # Wenn Keywords definiert, müssen sie matchen
        if keywords:
            if any(kw in name_lower for kw in keywords):
                return category
        # Wenn keine Keywords, nur Extension-basiert (für notizen, bilder, etc.)
        elif not keywords and extensions and suffix_lower in extensions:
            return category

    return "_unsortiert"


def get_file_hash(filepath: Path) -> str:
    """Berechnet MD5-Hash einer Datei."""
    import hashlib
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def sort_files(dry_run: bool = False):
    """Sortiert alle Dateien in die richtigen Ordner."""

    if not INPUT_DIR.exists():
        print(f"Input-Ordner nicht gefunden: {INPUT_DIR}")
        return

    # Erstelle Zielordner
    for category in list(CATEGORY_RULES.keys()) + ["_unsortiert"]:
        target = BASE_DIR / category
        target.mkdir(parents=True, exist_ok=True)

    # Sammle existierende Dateien (Name -> Hash)
    existing_files = {}
    for target_dir in BASE_DIR.rglob("*"):
        if target_dir.is_file() and not str(target_dir).startswith(str(INPUT_DIR)):
            try:
                existing_files[target_dir.name] = get_file_hash(target_dir)
            except:
                pass

    # Sammle Statistiken
    stats = Counter()
    moved_files = []
    skipped_duplicates = 0

    # Durchsuche alle Dateien
    for filepath in INPUT_DIR.rglob("*"):
        if not filepath.is_file():
            continue

        category = categorize_file(filepath)

        if category == "_skip":
            continue

        # Pruefe auf Duplikate
        if filepath.name in existing_files:
            try:
                src_hash = get_file_hash(filepath)
                if src_hash == existing_files[filepath.name]:
                    skipped_duplicates += 1
                    continue  # Datei existiert bereits identisch
            except:
                pass

        stats[category] += 1

        target_dir = BASE_DIR / category
        target_path = target_dir / filepath.name

        # Verhindere Ueberschreiben bei gleichem Namen aber anderem Inhalt
        if target_path.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            counter = 1
            while target_path.exists():
                target_path = target_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        moved_files.append((filepath, target_path, category))

    # Zeige Zusammenfassung
    print("=" * 60)
    print("SORTIERUNG ZUSAMMENFASSUNG")
    print("=" * 60)
    print()

    for category, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {category}: {count} Dateien")

    print()
    print(f"Gesamt: {sum(stats.values())} Dateien")
    print()

    if dry_run:
        print("[DRY RUN] Keine Dateien wurden verschoben.")
        print()
        print("Beispiele:")
        for src, dst, cat in moved_files[:10]:
            print(f"  {src.name} -> {cat}/")
        return

    # Verschiebe Dateien
    print("Verschiebe Dateien...")
    for src, dst, cat in moved_files:
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            print(f"  Fehler bei {src.name}: {e}")

    print()
    print("Fertig!")


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("[DRY RUN MODE]")
        print()

    sort_files(dry_run=dry_run)
