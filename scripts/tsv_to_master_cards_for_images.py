#!/usr/bin/env python3
"""
Convert Anki TSV exports (front/back/tags) into a master_cards-like JSONL for the images pipeline.

Why:
- `apply_images_to_tsv.py` matches cards via a SHA1 hash computed from the *final TSV text* (front+back).
- After OpenAI refinement, front/back changed vs. original `master_cards.jsonl`.
- This helper ensures the image candidate detection + mapping uses the exact same texts that will be updated.

Output JSONL schema (minimal):
{
  "card_id": "...",
  "front": "...",
  "back": "...",
  "tags_raw": "...",
  "source_ref": "path/to/file.tsv"
}
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _norm_text(s: str) -> str:
    s = s or ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _compute_card_id(front: str, back: str) -> str:
    front_n = _norm_text(front)
    back_n = _norm_text(back)
    return _sha1(front_n.lower() + "\n" + back_n.lower())


def iter_tsv_rows(path: Path) -> Iterable[List[str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue
            yield row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tsv-glob", required=True, help='Glob for TSVs, e.g. "_OUTPUT/anki_all_gpt52*.tsv"')
    parser.add_argument("--out", required=True, help="Output JSONL path")
    parser.add_argument("--limit", type=int, default=0, help="Limit total cards (0=all)")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    seen: Dict[str, str] = {}
    written = 0
    read_rows = 0
    matched_files = 0

    with out_path.open("w", encoding="utf-8") as f_out:
        for tsv_path in sorted(Path().glob(args.tsv_glob)):
            matched_files += 1
            for row in iter_tsv_rows(tsv_path):
                read_rows += 1
                if len(row) < 2:
                    continue
                front = row[0]
                back = row[1]
                tags_raw = row[2] if len(row) > 2 else ""

                front_n = _norm_text(front)
                back_n = _norm_text(back)
                if not front_n or not back_n:
                    continue

                card_id = _compute_card_id(front_n, back_n)
                if card_id in seen:
                    continue
                seen[card_id] = str(tsv_path)

                out = {
                    "card_id": card_id,
                    "front": front_n,
                    "back": back_n,
                    "tags_raw": (tags_raw or "").strip(),
                    "source_ref": str(tsv_path),
                }
                f_out.write(json.dumps(out, ensure_ascii=False) + "\n")
                written += 1

                if args.limit and written >= args.limit:
                    break
            if args.limit and written >= args.limit:
                break

    print(f"TSV files matched: {matched_files}")
    print(f"Rows read: {read_rows}")
    print(f"Cards written: {written}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()



