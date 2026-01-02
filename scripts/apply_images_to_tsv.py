#!/usr/bin/env python3
"""Apply local images to TSV exports and write new TSVs.

Adds <img src="..."> and a source line under the image.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from pathlib import Path
from typing import Dict, List


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


def anki_sanitize_field(value: str) -> str:
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\t", "    ")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    return s


def load_image_map(path: Path) -> Dict[str, Dict[str, str]]:
    mapping: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            card_id = (row.get("card_id") or "").strip()
            local_file = (row.get("local_file") or "").strip()
            if card_id and local_file:
                mapping[card_id] = row
    return mapping


def build_citation(row: Dict[str, str]) -> str:
    url = (row.get("page_url") or row.get("image_url") or "").strip()
    license_name = (row.get("license") or "").strip()
    attribution = (row.get("attribution") or "").strip()

    parts: List[str] = []
    if url:
        if license_name:
            parts.append(f"Quelle: {url} ({license_name})")
        else:
            parts.append(f"Quelle: {url}")
    if attribution:
        parts.append(f"Attribution: {attribution}")

    if not parts:
        return ""
    return "<br><small>" + " | ".join(parts) + "</small>"


def apply_images_to_tsv(tsv_path: Path, out_path: Path, mapping: Dict[str, Dict[str, str]], tag_suffix: str) -> Dict[str, int]:
    updated = 0
    skipped = 0
    total = 0

    out_path.parent.mkdir(parents=True, exist_ok=True)

    with tsv_path.open("r", encoding="utf-8") as f_in, out_path.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.reader(f_in, delimiter="\t")
        writer = csv.writer(f_out, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

        for row in reader:
            total += 1
            if not row:
                continue
            if len(row) < 2:
                writer.writerow(row)
                continue

            front = row[0]
            back = row[1]
            tags = row[2] if len(row) > 2 else ""
            rest = row[3:] if len(row) > 3 else []

            if "<img" in back:
                writer.writerow(row)
                skipped += 1
                continue

            card_id = _compute_card_id(front, back)
            if card_id not in mapping:
                writer.writerow(row)
                continue

            info = mapping[card_id]
            local_file = info.get("local_file", "")
            if not local_file:
                writer.writerow(row)
                continue

            citation = build_citation(info)
            back_new = back + f"<br><img src=\"{local_file}\">" + citation
            tags_new = (tags + " " + tag_suffix).strip() if tag_suffix else tags

            writer.writerow([front, back_new, tags_new] + rest)
            updated += 1

    return {"updated": updated, "skipped": skipped, "total": total}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", dest="map_path", required=True, help="image_map_with_files.csv")
    parser.add_argument("--tsv-glob", dest="tsv_glob", required=True, help="Glob for input TSVs")
    parser.add_argument("--out-dir", dest="out_dir", required=True, help="Output directory for TSVs")
    parser.add_argument("--tag", dest="tag", default="media::image", help="Tag to append")
    args = parser.parse_args()

    mapping = load_image_map(Path(args.map_path))
    out_dir = Path(args.out_dir)

    total_updated = 0
    total_skipped = 0
    total_rows = 0

    for tsv_path in sorted(Path().glob(args.tsv_glob)):
        out_name = tsv_path.stem + "_with_images.tsv"
        out_path = out_dir / out_name

        stats = apply_images_to_tsv(tsv_path, out_path, mapping, args.tag)
        total_updated += stats["updated"]
        total_skipped += stats["skipped"]
        total_rows += stats["total"]

        print(f"Wrote: {out_path} (updated={stats['updated']}, skipped={stats['skipped']})")

    print(f"Total rows: {total_rows}")
    print(f"Total updated: {total_updated}")
    print(f"Total skipped: {total_skipped}")


if __name__ == "__main__":
    main()
