#!/usr/bin/env python3
"""
Option B: Clean up obviously wrong images in FINAL-with-images TSVs.

This script removes image blocks when they are clearly wrong, e.g. Wikimedia "File:"
links that point to non-image documents (PDF/DjVu/TIFF/etc.). Those often show
irrelevant content (e.g. botany scans) and destroy trust.

Inputs (defaults):
  _OUTPUT/with_images/anki_all_gpt52_with_images_FINAL.tsv
  _OUTPUT/with_images/anki_all_gpt52_needs_review_with_images_FINAL.tsv

Outputs:
  _OUTPUT/with_images/anki_all_gpt52_with_images_FINAL_clean_images.tsv
  _OUTPUT/with_images/anki_all_gpt52_needs_review_with_images_FINAL_clean_images.tsv
  _OUTPUT/with_images/clean_images_report.md

What it does:
  - Detects image blocks (<img ...> + attribution line) in answer HTML
  - Determines whether the block is "bad" using conservative heuristics:
      * Wikimedia File URL ends with .pdf/.djvu/.tif/.tiff/.ps/.eps (case-insensitive)
      * or referenced local media file is missing in --media-src
  - Removes the whole image block (keeps the validated <hr><b>Quellen</b> block intact)
  - Removes tag 'media::image' if no image remains in that note

NOTE:
  This is intentionally conservative. If you still see many wrong JPG images,
  we can add a stricter mode (keep images only for explicit image questions).
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


BAD_WIKIMEDIA_EXTS = (
    ".pdf",
    ".djvu",
    ".tif",
    ".tiff",
    ".ps",
    ".eps",
)


IMG_TAG_RE = re.compile(r'(?is)<img[^>]*\bsrc\s*=\s*"([^"]+)"[^>]*>')
URL_RE = re.compile(r"(?i)\bhttps?://[^\s<>\"]+")
HR_RE = re.compile(r"(?is)<hr>\s*(?:\r?\n\s*)?<b>\s*Quellen\s*:\s*</b>")


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
            q = row[0] if len(row) >= 1 else ""
            a = row[1] if len(row) >= 2 else ""
            t = row[2] if len(row) >= 3 else ""
            rows.append(TSVRow(question=q, answer=a, tags=t))
    return rows


def write_tsv(path: Path, rows: Iterable[TSVRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            writer.writerow([r.question, r.answer, r.tags])


def normalize_tags(tags: str) -> str:
    return " ".join([t for t in (tags or "").split() if t])


def remove_tag(tags: str, tag: str) -> str:
    return " ".join([t for t in (tags or "").split() if t and t != tag])


def has_any_img(answer: str) -> bool:
    return "<img" in (answer or "").lower()


def extract_first_img_src(answer: str) -> Optional[str]:
    m = IMG_TAG_RE.search(answer or "")
    if not m:
        return None
    return m.group(1).strip()


def extract_urls(text: str) -> List[str]:
    return [m.group(0) for m in URL_RE.finditer(text or "")]


def is_bad_wikimedia_url(url: str) -> bool:
    u = (url or "").lower()
    # Typical pattern: https://commons.wikimedia.org/wiki/File:Something.pdf
    return any(ext in u for ext in BAD_WIKIMEDIA_EXTS)


def find_image_block_span(answer: str) -> Optional[Tuple[int, int]]:
    """
    Returns (start_idx, end_idx) span to remove:
    - from first <img ...> to right before the Quellen <hr> block if present,
      otherwise to end of string.
    - also tries to eat a couple of preceding <br> to avoid leftover blank lines.
    """
    if not answer:
        return None
    lower = answer.lower()
    img_idx = lower.find("<img")
    if img_idx == -1:
        return None

    # Prefer cutting until the Quellen <hr> marker
    m_hr = HR_RE.search(answer, pos=img_idx)
    end = m_hr.start() if m_hr else len(answer)

    # Extend start backwards to include up to 3 <br> right before <img
    start = img_idx
    # Walk back over whitespace
    while start > 0 and answer[start - 1].isspace():
        start -= 1
    for _ in range(3):
        br_start = answer.rfind("<br", 0, start)
        if br_start == -1:
            break
        # Only eat it if it's very close (within 10 chars)
        if start - br_start > 10:
            break
        start = br_start
        while start > 0 and answer[start - 1].isspace():
            start -= 1

    return (start, end)


def should_remove_image(answer: str, media_src: Path) -> Tuple[bool, List[str]]:
    """
    Conservative reasons to remove:
      - Wikimedia URL indicates non-image doc types (.pdf/.djvu/...)
      - referenced local media file missing
    """
    reasons: List[str] = []
    if not has_any_img(answer):
        return (False, reasons)

    # Check local file exists
    src = extract_first_img_src(answer) or ""
    if src:
        # some answers might use relative paths already; accept basename
        basename = Path(src).name
        if not (media_src / basename).exists():
            reasons.append(f"missing_local_file:{basename}")

    # Check URLs near image (we scan the whole answer conservatively)
    urls = extract_urls(answer)
    bad_urls = [u for u in urls if "commons.wikimedia.org/wiki/file:" in u.lower() and is_bad_wikimedia_url(u)]
    if bad_urls:
        reasons.append("wikimedia_non_image_url")

    return (len(reasons) > 0, reasons)


def clean_one_file(input_path: Path, output_path: Path, media_src: Path) -> Dict[str, object]:
    rows = read_tsv(input_path)

    out_rows: List[TSVRow] = []
    total = 0
    had_img = 0
    removed_img = 0
    kept_img = 0
    removed_by_reason: Dict[str, int] = {}
    examples_removed: List[Tuple[str, List[str]]] = []

    for r in rows:
        total += 1
        answer = r.answer or ""
        tags = normalize_tags(r.tags)

        if has_any_img(answer):
            had_img += 1
            remove, reasons = should_remove_image(answer, media_src)
            if remove:
                span = find_image_block_span(answer)
                if span:
                    a2 = (answer[: span[0]] + answer[span[1] :]).strip()
                else:
                    a2 = answer
                tags2 = remove_tag(tags, "media::image")
                removed_img += 1
                for reason in reasons:
                    removed_by_reason[reason] = removed_by_reason.get(reason, 0) + 1
                if len(examples_removed) < 10:
                    examples_removed.append((r.question, reasons))
                out_rows.append(TSVRow(question=r.question, answer=a2, tags=tags2))
            else:
                kept_img += 1
                out_rows.append(TSVRow(question=r.question, answer=answer, tags=tags))
        else:
            out_rows.append(TSVRow(question=r.question, answer=answer, tags=tags))

    write_tsv(output_path, out_rows)

    return {
        "input": str(input_path),
        "output": str(output_path),
        "total_rows": total,
        "rows_with_img": had_img,
        "images_removed": removed_img,
        "images_kept": kept_img,
        "removed_by_reason": removed_by_reason,
        "examples_removed": examples_removed,
    }


def write_report(report_path: Path, stats_ok: Dict[str, object], stats_nr: Dict[str, object]) -> None:
    def fmt_dict(d: Dict[str, int]) -> str:
        if not d:
            return "- (keine)\n"
        lines = []
        for k, v in sorted(d.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- `{k}`: {v}")
        return "\n".join(lines) + "\n"

    def fmt_examples(examples: List[Tuple[str, List[str]]]) -> str:
        if not examples:
            return "- (keine)\n"
        out = []
        for q, reasons in examples:
            out.append(f"- **{q[:120]}**\n  - Gründe: {', '.join(reasons)}")
        return "\n".join(out) + "\n"

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# Clean Images Report (Option B)\n\n")
        f.write("Entfernt offensichtliche Fehl-Bilder (Wikimedia PDF/DjVu/etc.) aus FINAL-with-images TSVs.\n\n")

        for title, st in [("OK", stats_ok), ("NeedsReview", stats_nr)]:
            f.write(f"## {title}\n\n")
            f.write(f"- Input: `{st['input']}`\n")
            f.write(f"- Output: `{st['output']}`\n")
            f.write(f"- Rows: **{st['total_rows']}**\n")
            f.write(f"- Rows with `<img>`: **{st['rows_with_img']}**\n")
            f.write(f"- Images removed: **{st['images_removed']}**\n")
            f.write(f"- Images kept: **{st['images_kept']}**\n\n")
            f.write("### Removed by reason\n\n")
            f.write(fmt_dict(st.get("removed_by_reason", {})))  # type: ignore[arg-type]
            f.write("\n### Example removed items (up to 10)\n\n")
            f.write(fmt_examples(st.get("examples_removed", [])))  # type: ignore[arg-type]
            f.write("\n")

        f.write("## Next steps (Anki)\n\n")
        f.write("1) Importiere die `*_FINAL_clean_images.tsv` Dateien mit:\n")
        f.write("- ✅ `Allow HTML in fields`\n")
        f.write("- ✅ `Update existing notes when first field matches`\n")
        f.write("2) Dadurch werden die falschen Bildblöcke aus bestehenden Notizen entfernt.\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Remove obviously wrong images from FINAL-with-images TSVs.")
    p.add_argument("--ok", default="_OUTPUT/with_images/anki_all_gpt52_with_images_FINAL.tsv")
    p.add_argument("--needsreview", default="_OUTPUT/with_images/anki_all_gpt52_needs_review_with_images_FINAL.tsv")
    p.add_argument("--media-src", default="_OUTPUT/media_images")
    p.add_argument("--out-ok", default="_OUTPUT/with_images/anki_all_gpt52_with_images_FINAL_clean_images.tsv")
    p.add_argument("--out-needsreview", default="_OUTPUT/with_images/anki_all_gpt52_needs_review_with_images_FINAL_clean_images.tsv")
    p.add_argument("--report", default="_OUTPUT/with_images/clean_images_report.md")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    base = Path(__file__).resolve().parent.parent
    media_src = (base / args.media_src).resolve()

    ok_in = base / args.ok
    nr_in = base / args.needsreview
    ok_out = base / args.out_ok
    nr_out = base / args.out_needsreview
    report_path = base / args.report

    stats_ok = clean_one_file(ok_in, ok_out, media_src)
    stats_nr = clean_one_file(nr_in, nr_out, media_src)
    write_report(report_path, stats_ok, stats_nr)

    print(f"Wrote OK: {ok_out}")
    print(f"Wrote NeedsReview: {nr_out}")
    print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


