#!/usr/bin/env python3
"""
Medexamenai - Cleanup Helper
===========================

Removes invalid entries from evidenz_antworten.json (e.g., missing/empty "frage").
Creates a timestamped backup before writing changes.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _is_missing_question(entry: dict[str, Any]) -> bool:
    return not (entry.get("frage") or "").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cleanup evidenz_antworten.json")
    parser.add_argument(
        "--input",
        default="_OUTPUT/evidenz_antworten.json",
        help="Input JSON file (list of Q&A dicts)",
    )
    parser.add_argument(
        "--output",
        default="_OUTPUT/evidenz_antworten.json",
        help="Output JSON file",
    )
    parser.add_argument(
        "--backup-dir",
        default="_OUTPUT/backups",
        help="Directory for timestamped backups",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only report what would change",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    backup_dir = Path(args.backup_dir)

    if not input_path.exists():
        raise SystemExit(f"Input not found: {input_path}")

    data = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Expected a JSON list at input")

    bad_indices = [i for i, entry in enumerate(data) if _is_missing_question(entry)]
    if not bad_indices:
        print("No cleanup needed (no entries with empty/missing 'frage').")
        return 0

    print(f"Found {len(bad_indices)} entries with empty/missing 'frage': {bad_indices}")

    cleaned = [entry for entry in data if not _is_missing_question(entry)]
    print(f"Entries: {len(data)} -> {len(cleaned)}")

    if args.dry_run:
        print("Dry-run: no files written.")
        return 0

    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{input_path.stem}_before_cleanup_{ts}.json"
    backup_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    output_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Backup written: {backup_path}")
    print(f"Cleaned file written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

