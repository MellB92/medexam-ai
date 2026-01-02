#!/usr/bin/env python3
"""Download images from image_map.csv and store locally for Anki media.

Updates the map with local_file and status.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

import requests

EXT_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}

# Polite/default UA for downloads; some hosts may reject empty UA.
DEFAULT_USER_AGENT = "Medexamenai_Migration/1.0 (educational; https://github.com/MellB92/medexam-ai)"


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _pick_ext(url: str, content_type: str) -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext in EXT_BY_CONTENT_TYPE.values():
        return ext
    if content_type in EXT_BY_CONTENT_TYPE:
        return EXT_BY_CONTENT_TYPE[content_type]
    return ".jpg"


def _download(url: str, dest: Path) -> Tuple[bool, str]:
    try:
        with requests.get(url, stream=True, timeout=60, headers={"User-Agent": DEFAULT_USER_AGENT}) as resp:
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if not ctype.startswith("image/"):
                return False, f"bad_content_type:{ctype}"

            ext = _pick_ext(url, ctype)
            dest = dest.with_suffix(ext)
            dest.parent.mkdir(parents=True, exist_ok=True)

            with dest.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        return True, dest.name
    except Exception as e:
        return False, f"error:{e}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", dest="map_path", required=True, help="image_map.csv")
    parser.add_argument("--out-map", dest="out_map", required=True, help="image_map_with_files.csv")
    parser.add_argument("--media-dir", dest="media_dir", required=True, help="Output directory for images")
    parser.add_argument("--include-review", action="store_true", help="Download even if needs_review is set")
    args = parser.parse_args()

    map_path = Path(args.map_path)
    out_map = Path(args.out_map)
    media_dir = Path(args.media_dir)

    rows: List[Dict[str, str]] = []
    with map_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    downloaded = 0
    skipped = 0

    for row in rows:
        url = (row.get("image_url") or "").strip()
        needs_review = (row.get("needs_review") or "").strip().lower() in {"yes", "true", "1"}
        if not url:
            skipped += 1
            continue
        if needs_review and not args.include_review:
            skipped += 1
            continue

        base = _sha1(url)
        dest = media_dir / f"img_{base}"

        ok, info = _download(url, dest)
        if ok:
            row["local_file"] = info
            row["download_status"] = "ok"
            downloaded += 1
        else:
            row["download_status"] = info
            skipped += 1

    out_map.parent.mkdir(parents=True, exist_ok=True)
    with out_map.open("w", encoding="utf-8", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        if "download_status" not in fieldnames:
            fieldnames.append("download_status")
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Downloaded: {downloaded}")
    print(f"Skipped: {skipped}")
    print(f"Out map: {out_map}")
    print(f"Media dir: {media_dir}")


if __name__ == "__main__":
    main()
