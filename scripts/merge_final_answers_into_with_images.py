#!/usr/bin/env python3
"""
Merge FINAL answers+tags into with_images TSVs, preserving images.

Goal:
- Output uses FINAL as canonical (answer contains validated Zwei-Quellen-Block, tags contain extern::* status)
- Inserts image block (<img ...> + image attribution lines) from with_images into FINAL answer
- Ensures extern::pending is NOT present in output
- Adds/keeps media::image tag when an image is present

Creates:
  _OUTPUT/with_images/anki_all_gpt52_with_images_FINAL.tsv
  _OUTPUT/with_images/anki_all_gpt52_needs_review_with_images_FINAL.tsv

Notes:
- We match rows by normalized question text.
- NeedsReview questions may contain a context prefix; we strip that for matching.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


CONTEXT_PREFIX_RE = re.compile(r"(?is)^\s*<b>\s*Kontext\s*:\s*</b>.*?(?:<br>\s*){2}")


def normalize_question(q: str) -> str:
    """
    Normalize question for matching across TSV variants.

    - strips a leading '<b>Kontext:</b> ... <br><br>' prefix
    - removes <img ...> (shouldn't exist in question but safe)
    - collapses whitespace
    - lowercases
    """
    q = CONTEXT_PREFIX_RE.sub("", q or "")
    q = re.sub(r"(?is)<img[^>]*>", "", q)
    q = re.sub(r"\s+", " ", q).strip().lower()
    return q


def extract_image_block(answer: str) -> Optional[str]:
    """
    Extract the image block from a with_images answer field.

    We take everything from the first '<img' to the end of the field.
    This preserves:
    - <img src="...">
    - any following attribution/source lines (e.g. Wikimedia license)

    Returns None if no image is present.
    """
    if not answer:
        return None
    idx = answer.lower().find("<img")
    if idx == -1:
        return None
    return answer[idx:].strip()


def insert_image_block_into_final_answer(final_answer: str, image_block: str) -> str:
    """
    Insert image_block into final_answer, ideally right before the Quellen <hr> block.
    If final_answer already contains an <img>, we keep it as-is to avoid duplicates.
    """
    if not image_block:
        return final_answer
    if "<img" in (final_answer or "").lower():
        return final_answer

    final_answer = final_answer or ""
    # Find sources block marker: <hr> ... <b>Quellen:</b>
    m = re.search(r"(?is)<hr>\s*(?:\r?\n\s*)?<b>\s*Quellen\s*:\s*</b>", final_answer)
    if not m:
        # Fallback: append at end
        return (final_answer.rstrip() + "<br><br>" + image_block.strip()).strip()

    insert_at = m.start()
    before = final_answer[:insert_at].rstrip()
    after = final_answer[insert_at:].lstrip()

    # Ensure spacing around the inserted block
    img = image_block.strip()
    if not img.lower().startswith("<br"):
        img = "<br>" + img
    if not img.lower().endswith("<br>"):
        img = img + "<br>"

    return (before + img + "<br>" + after).strip()


def normalize_tags(tags: str) -> str:
    tags = tags or ""
    # Split on whitespace only; keep as space-separated
    parts = [t for t in tags.split() if t]
    return " ".join(parts)


def remove_tag(tags: str, tag_to_remove: str) -> str:
    parts = [t for t in (tags or "").split() if t and t != tag_to_remove]
    return " ".join(parts)


def ensure_tag(tags: str, tag_to_add: str) -> str:
    parts = (tags or "").split()
    if tag_to_add in parts:
        return normalize_tags(tags)
    return normalize_tags((tags or "") + " " + tag_to_add)


@dataclass
class TSVRow:
    question: str
    answer: str
    tags: str


def read_tsv(path: Path) -> List[TSVRow]:
    rows: List[TSVRow] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                # Keep minimal rows (shouldn't happen)
                q = row[0] if row else ""
                rows.append(TSVRow(question=q, answer="", tags=""))
                continue
            q = row[0]
            a = row[1]
            t = row[2] if len(row) >= 3 else ""
            rows.append(TSVRow(question=q, answer=a, tags=t))
    return rows


def write_tsv(path: Path, rows: Iterable[TSVRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            writer.writerow([r.question, r.answer, r.tags])


def build_with_images_index(with_images_rows: List[TSVRow]) -> Dict[str, Tuple[Optional[str], str]]:
    """
    Map normalized_question -> (image_block_or_none, original_tags)
    """
    idx: Dict[str, Tuple[Optional[str], str]] = {}
    for r in with_images_rows:
        nq = normalize_question(r.question)
        img = extract_image_block(r.answer)
        idx[nq] = (img, r.tags or "")
    return idx


def merge_one(final_path: Path, with_images_path: Path, output_path: Path) -> Dict[str, int]:
    final_rows = read_tsv(final_path)
    with_images_rows = read_tsv(with_images_path)
    wi_index = build_with_images_index(with_images_rows)

    out_rows: List[TSVRow] = []
    matched = 0
    inserted_images = 0
    already_had_img = 0
    unmatched = 0

    for fr in final_rows:
        nq = normalize_question(fr.question)
        img_block: Optional[str] = None
        wi_tags = ""
        if nq in wi_index:
            img_block, wi_tags = wi_index[nq]
            matched += 1
        else:
            unmatched += 1

        new_answer = fr.answer
        if img_block:
            if "<img" in (fr.answer or "").lower():
                already_had_img += 1
            else:
                new_answer = insert_image_block_into_final_answer(fr.answer, img_block)
                inserted_images += 1

        # Tags: prefer FINAL tags, but ensure we don't leak extern::pending and keep media::image if image present
        new_tags = normalize_tags(fr.tags)
        new_tags = remove_tag(new_tags, "extern::pending")

        # If either source had an image, ensure media::image tag exists
        has_img_now = ("<img" in (new_answer or "").lower()) or (img_block is not None)
        if has_img_now:
            new_tags = ensure_tag(new_tags, "media::image")

        out_rows.append(TSVRow(question=fr.question, answer=new_answer, tags=new_tags))

    write_tsv(output_path, out_rows)

    # Count extern::pending occurrences in output tags (should be 0)
    pending_in_output = sum(1 for r in out_rows if "extern::pending" in (r.tags or "").split())

    return {
        "final_rows": len(final_rows),
        "with_images_rows": len(with_images_rows),
        "matched": matched,
        "unmatched": unmatched,
        "inserted_images": inserted_images,
        "already_had_img": already_had_img,
        "extern_pending_in_output": pending_in_output,
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge FINAL answers/tags into with_images TSVs (preserve images).")
    p.add_argument("--final-ok", default="_OUTPUT/anki_all_gpt52_FINAL.tsv")
    p.add_argument("--with-images-ok", default="_OUTPUT/with_images/anki_all_gpt52_with_images.tsv")
    p.add_argument("--out-ok", default="_OUTPUT/with_images/anki_all_gpt52_with_images_FINAL.tsv")

    p.add_argument("--final-needsreview", default="_OUTPUT/anki_all_gpt52_needs_review_FINAL.tsv")
    p.add_argument("--with-images-needsreview", default="_OUTPUT/with_images/anki_all_gpt52_needs_review_with_images.tsv")
    p.add_argument("--out-needsreview", default="_OUTPUT/with_images/anki_all_gpt52_needs_review_with_images_FINAL.tsv")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    base = Path(__file__).resolve().parent.parent

    print("=== Merge OK ===")
    ok_stats = merge_one(
        base / args.final_ok,
        base / args.with_images_ok,
        base / args.out_ok,
    )
    for k, v in ok_stats.items():
        print(f"{k}: {v}")

    print("\n=== Merge NeedsReview ===")
    nr_stats = merge_one(
        base / args.final_needsreview,
        base / args.with_images_needsreview,
        base / args.out_needsreview,
    )
    for k, v in nr_stats.items():
        print(f"{k}: {v}")

    if ok_stats["extern_pending_in_output"] or nr_stats["extern_pending_in_output"]:
        print("\n❌ ERROR: extern::pending still present in output tags.")
        return 2

    print("\n✅ Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


