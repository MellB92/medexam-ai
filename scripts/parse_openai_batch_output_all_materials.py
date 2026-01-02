#!/usr/bin/env python3
"""Parse OpenAI batch output JSONL for the All-Materials QA/Polish pipeline.

Input: openai_batch_output.jsonl (downloaded from OpenAI batches)
Output:
- anki_all_gpt52.tsv (ready import)
- anki_all_gpt52_needs_review.tsv
- medgemma_validation_queue.jsonl
- perplexity_validation_queue.jsonl

Expected model output per request (strict JSON):
{front, back, tags, confidence, needs_review, review_reason, citations_minimal, notes}

Batch output JSONL shape differs across OpenAI versions. We implement tolerant extraction.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple


def anki_sanitize_field(value: str) -> str:
    """No newlines or tabs in fields; use <br> for line breaks."""
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\t", "    ")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    return s


def _append_citations_to_back(back_html: str, citations: Any) -> str:
    """
    Append minimal source citations to the back field (HTML-safe via <br>).
    Keeps it conservative: if already contains 'Quelle:' we don't append again.
    """
    back_html = back_html or ""
    if "Quelle:" in back_html or "Quelle :" in back_html:
        return back_html

    cites: List[str] = []
    if isinstance(citations, list):
        for c in citations:
            if isinstance(c, str) and c.strip():
                cites.append(c.strip())
    elif isinstance(citations, str) and citations.strip():
        cites.append(citations.strip())

    if not cites:
        return back_html

    # keep it short to avoid clutter
    cites = cites[:3]
    src = " | ".join(cites)
    return (back_html + f"<br><small>Quelle: {src}</small>").strip()


def _load_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _walk_strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None

    # Strip markdown fences if present
    if "```" in text:
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        else:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _extract_model_json(batch_line: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], str]:
    """Return (parsed_json, raw_text_for_debug)."""
    candidates: List[str] = []

    for key in ["response", "result", "data"]:
        if key in batch_line:
            candidates.extend(list(_walk_strings(batch_line[key])))

    # also scan full line
    candidates.extend(list(_walk_strings(batch_line)))

    # Prefer strings that look like the expected object
    for c in candidates:
        if "{" not in c or "}" not in c:
            continue
        parsed = _extract_json_from_text(c)
        if isinstance(parsed, dict) and "front" in parsed and "back" in parsed:
            return parsed, c

    for c in candidates:
        parsed = _extract_json_from_text(c)
        if isinstance(parsed, dict):
            return parsed, c

    return None, ""


def _risk_from_tags(tags: str) -> List[str]:
    t = tags or ""
    return [r for r in ["risk::dose", "risk::radiation", "risk::deadline", "risk::guideline"] if r in t]


def _route_queues(item: Dict[str, Any]) -> Tuple[bool, bool]:
    """Return (to_medgemma, to_perplexity)."""
    tags = item.get("tags", "") or ""
    rr = (item.get("review_reason", "") or "").lower()
    risks = _risk_from_tags(tags)

    to_medgemma = any(r in risks for r in ["risk::dose", "risk::radiation", "risk::deadline"]) or any(
        k in rr for k in ["dose", "dosis", "radiat", "strahl", "deadline", "frist"]
    )
    to_perplexity = ("risk::guideline" in risks) or any(k in rr for k in ["leitlinie", "guideline", "stiko", "awmf"])

    return to_medgemma, to_perplexity


def _as_queue_item(custom_id: str, item: Dict[str, Any], *, queue: str) -> Dict[str, Any]:
    return {
        "custom_id": custom_id,
        "queue": queue,
        "front": item.get("front", ""),
        "back": item.get("back", ""),
        "tags": item.get("tags", ""),
        "confidence": item.get("confidence", None),
        "needs_review": item.get("needs_review", None),
        "review_reason": item.get("review_reason", ""),
        "citations_minimal": item.get("citations_minimal", []),
        "notes": item.get("notes", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True, help="openai_batch_output.jsonl")
    parser.add_argument("--out-tsv", dest="out_tsv", required=True, help="anki_all_gpt52.tsv")
    parser.add_argument("--out-tsv-review", dest="out_tsv_review", required=True)
    parser.add_argument("--out-queues", dest="out_queues", required=True, help="Output folder for queue jsonl")
    parser.add_argument(
        "--out-report",
        default="",
        help="Optional: write all_materials_refinement_report.md (default: <out-queues>/all_materials_refinement_report.md)",
    )
    parser.add_argument("--debug-jsonl", default="", help="Optional: write parser debug jsonl")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_tsv = Path(args.out_tsv)
    out_tsv_review = Path(args.out_tsv_review)
    out_queues = Path(args.out_queues)
    out_queues.mkdir(parents=True, exist_ok=True)

    medgemma_q = out_queues / "medgemma_validation_queue.jsonl"
    perplexity_q = out_queues / "perplexity_validation_queue.jsonl"
    report_path = Path(args.out_report) if args.out_report else (out_queues / "all_materials_refinement_report.md")
    debug_path = Path(args.debug_jsonl) if args.debug_jsonl else None

    ok = 0
    needs_review = 0
    parse_errors = 0
    medgemma_count = 0
    perplexity_count = 0
    review_reasons: Dict[str, int] = {}

    with (
        out_tsv.open("w", encoding="utf-8", newline="") as f_ok,
        out_tsv_review.open("w", encoding="utf-8", newline="") as f_rev,
        medgemma_q.open("w", encoding="utf-8") as f_mg,
        perplexity_q.open("w", encoding="utf-8") as f_px,
    ):
        writer_ok = csv.writer(f_ok, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer_rev = csv.writer(f_rev, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

        f_dbg = debug_path.open("w", encoding="utf-8") if debug_path else None

        for line in _load_jsonl(in_path):
            custom_id = line.get("custom_id") or ""
            parsed, raw = _extract_model_json(line)

            if not parsed:
                parse_errors += 1
                if f_dbg:
                    f_dbg.write(
                        json.dumps({"custom_id": custom_id, "status": "parse_error", "raw": raw}, ensure_ascii=False)
                        + "\n"
                    )
                continue

            # Minimal sanity defaults
            parsed.setdefault("needs_review", False)
            parsed.setdefault("review_reason", "")
            parsed.setdefault("citations_minimal", ["unknown"])
            parsed.setdefault("notes", "")

            to_mg, to_px = _route_queues(parsed)
            if to_mg:
                medgemma_count += 1
                f_mg.write(json.dumps(_as_queue_item(custom_id, parsed, queue="medgemma"), ensure_ascii=False) + "\n")
            if to_px:
                perplexity_count += 1
                f_px.write(json.dumps(_as_queue_item(custom_id, parsed, queue="perplexity"), ensure_ascii=False) + "\n")

            front = anki_sanitize_field(parsed.get("front", ""))
            back = anki_sanitize_field(parsed.get("back", ""))
            back = _append_citations_to_back(back, parsed.get("citations_minimal"))
            tags = anki_sanitize_field(parsed.get("tags", ""))

            if bool(parsed.get("needs_review")):
                needs_review += 1
                rr_raw = (parsed.get("review_reason") or "").strip()
                if rr_raw:
                    review_reasons[rr_raw] = review_reasons.get(rr_raw, 0) + 1

                # add review hint tags
                rr = rr_raw.replace(" ", "_")[:60]
                if rr:
                    tags = (tags + f" qa::needs_review review::{rr}").strip()
                else:
                    tags = (tags + " qa::needs_review").strip()
                writer_rev.writerow([front, back, tags])
            else:
                ok += 1
                writer_ok.writerow([front, back, tags])

            if f_dbg:
                f_dbg.write(
                    json.dumps({"custom_id": custom_id, "status": "ok", "parsed": parsed}, ensure_ascii=False) + "\n"
                )

        if f_dbg:
            f_dbg.close()

    # Write report
    lines: List[str] = []
    lines.append("# All-Materials Refinement Report")
    lines.append("")
    lines.append(f"- OK cards: {ok}")
    lines.append(f"- Needs review: {needs_review}")
    lines.append(f"- Parse errors: {parse_errors}")
    lines.append(f"- MedGemma queue: {medgemma_count}")
    lines.append(f"- Perplexity queue: {perplexity_count}")
    lines.append("")
    if review_reasons:
        lines.append("## Top review reasons")
        for reason, cnt in sorted(review_reasons.items(), key=lambda x: (-x[1], x[0]))[:25]:
            lines.append(f"- {cnt}× {reason}")
        lines.append("")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote TSV: {out_tsv} ({ok})")
    print(f"Wrote needs_review TSV: {out_tsv_review} ({needs_review})")
    print(f"Wrote MedGemma queue: {medgemma_q} ({medgemma_count})")
    print(f"Wrote Perplexity queue: {perplexity_q} ({perplexity_count})")
    print(f"Wrote report: {report_path}")
    print(f"Parse errors: {parse_errors}")


if __name__ == "__main__":
    main()
