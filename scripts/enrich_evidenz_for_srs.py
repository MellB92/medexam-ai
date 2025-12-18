#!/usr/bin/env python3
"""Enrich evidenz_antworten for downstream processing.

Pragmatisches Ziel
- evidenz_antworten.json bleibt UNVERÄNDERT.
- Wir erzeugen eine neue Datei, die für Sortierung in Fachgebieten und SRS
  nutzbar ist.

Input (Defaults)
- _OUTPUT/evidenz_antworten_with_perplexity_factcheck_20251213_1820.json
  (falls vorhanden), sonst _OUTPUT/evidenz_antworten.json
- _OUTPUT/full_data_with_fachgebiete.json (Frage -> Fachgebiet)
- _OUTPUT/meaningful_missing.json (Meaningful-Set, für Filter/Stats)

Output
- _OUTPUT/evidenz_antworten_enriched_for_srs_<YYYYMMDD_HHMM>.json
- _OUTPUT/perplexity_problem_inventory_<YYYYMMDD_HHMM>.csv
- _OUTPUT/perplexity_maybe_inventory_<YYYYMMDD_HHMM>.csv
- _OUTPUT/srs_cards_ready_<YYYYMMDD_HHMM>.json
  (SM-2 kompatibel: core/spaced_repetition.py)

Hinweis
- Keine Antworten werden umgeschrieben.
- \"problem\"/\"maybe\" werden als study_status markiert und standardmäßig
  nicht in SRS-Ready exportiert.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _norm(text: str) -> str:
    return " ".join((text or "").strip().split()).lower()


def _extract_question(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("frage") or item.get("question") or "").strip()
    return str(item).strip()


def _load_meaningful_set(path: Path) -> Set[str]:
    data = _read_json(path)
    if not isinstance(data, list):
        return set()

    s: Set[str] = set()
    for item in data:
        q = _extract_question(item)
        if q:
            s.add(_norm(q))
    return s


def _build_fachgebiet_map(
    full_data_with_fachgebiete: List[Dict[str, Any]],
) -> Dict[str, str]:
    q2f: Dict[str, str] = {}
    for block in full_data_with_fachgebiete:
        fach = str(block.get("fachgebiet") or "").strip()
        questions = block.get("questions")
        if not isinstance(questions, list):
            continue
        for q in questions:
            q_str = str(q).strip()
            nq = _norm(q_str)
            if not nq:
                continue
            # first wins (stable)
            if nq not in q2f:
                q2f[nq] = fach
    return q2f


def _get_factcheck(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    validation = entry.get("validation")
    if not isinstance(validation, dict):
        return None
    fc = validation.get("perplexity_factcheck")
    return fc if isinstance(fc, dict) else None


def _classify_study_status(fc: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """Return (study_status, exclude_reason).

    study_status:
    - ready
    - needs_review
    - needs_context
    - unknown
    """

    if not fc:
        return "unknown", "no_factcheck"

    verdict = str(fc.get("verdict") or "").strip().lower()
    issues = fc.get("issues")
    if isinstance(issues, list):
        issues_text = " ".join(str(x) for x in issues)
    else:
        issues_text = ""
    issues_text_l = issues_text.lower()

    if verdict == "ok":
        return "ready", ""
    if verdict == "problem":
        return "needs_review", "factcheck_problem"
    if verdict == "maybe":
        # heuristics: mostly missing context / images
        if any(k in issues_text_l for k in ["bild", "kontext", "falldarstellung"]):
            return "needs_context", "missing_context"
        if "kein parsebares json" in issues_text_l:
            return "unknown", "factcheck_non_json"
        return "needs_review", "factcheck_maybe"

    return "unknown", "factcheck_unknown"


def _csv_write(
    path: Path,
    rows: List[Dict[str, Any]],
    fieldnames: List[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _compact_issues(fc: Dict[str, Any], max_items: int = 5) -> str:
    issues = fc.get("issues")
    if not isinstance(issues, list):
        return ""
    items = [str(x).strip() for x in issues if str(x).strip()]
    return " | ".join(items[:max_items])


def _compact_sources(fc: Dict[str, Any], max_items: int = 3) -> str:
    sources = fc.get("suggested_sources")
    if not isinstance(sources, list):
        return ""
    out: List[str] = []
    for s in sources[:max_items]:
        if not isinstance(s, dict):
            continue
        title = str(s.get("title") or "").strip()
        url = str(s.get("url") or "").strip()
        if url and title:
            out.append(f"{title}: {url}")
        elif url:
            out.append(url)
        elif title:
            out.append(title)
    return " | ".join(out)


def _make_card_id(idx: int) -> str:
    return f"evidenz_{idx}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Enrich evidenz_antworten for Fachgebiete + SRS (no rewrites)")
    )
    parser.add_argument(
        "--input",
        default="",
        help=(
            "Input Q&A JSON (default: "
            "evidenz_antworten_with_perplexity_factcheck_* "
            "else evidenz_antworten.json)"
        ),
    )
    parser.add_argument(
        "--fachgebiete",
        default=str(OUTPUT_DIR / "full_data_with_fachgebiete.json"),
        help="full_data_with_fachgebiete.json",
    )
    parser.add_argument(
        "--meaningful",
        default=str(OUTPUT_DIR / "meaningful_missing.json"),
        help="meaningful list (for flags/filtering)",
    )
    parser.add_argument(
        "--export-srs",
        action="store_true",
        help="Export SRS-ready cards JSON",
    )
    parser.add_argument(
        "--meaningful-only",
        action="store_true",
        help="SRS export: only include meaningful questions",
    )
    args = parser.parse_args()

    # pick default input
    in_path: Path
    if args.input:
        in_path = Path(args.input)
    else:
        preferred = OUTPUT_DIR / (
            "evidenz_antworten_with_perplexity_factcheck_20251213_1820.json"
        )
        if preferred.exists():
            in_path = preferred
        else:
            in_path = OUTPUT_DIR / "evidenz_antworten.json"

    fach_path = Path(args.fachgebiete)
    meaningful_path = Path(args.meaningful)

    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}")
    if not fach_path.exists():
        raise SystemExit(f"Fachgebiete file not found: {fach_path}")

    ts = datetime.now().strftime("%Y%m%d_%H%M")

    data = _read_json(in_path)
    if not isinstance(data, list):
        raise SystemExit("Input JSON must be a list")

    fach_data = _read_json(fach_path)
    if not isinstance(fach_data, list):
        raise SystemExit("Fachgebiete JSON must be a list")

    meaningful_set: Set[str] = set()
    if meaningful_path.exists():
        meaningful_set = _load_meaningful_set(meaningful_path)

    q2fach = _build_fachgebiet_map(fach_data)

    enriched: List[Dict[str, Any]] = []

    counts: Dict[str, int] = {
        "ready": 0,
        "needs_review": 0,
        "needs_context": 0,
        "unknown": 0,
    }
    problem_rows: List[Dict[str, Any]] = []
    maybe_rows: List[Dict[str, Any]] = []

    for idx, entry in enumerate(data):
        if not isinstance(entry, dict):
            continue

        q = str(entry.get("frage") or entry.get("question") or "").strip()
        nq = _norm(q)

        fach = q2fach.get(nq, "")
        fc = _get_factcheck(entry)
        status, reason = _classify_study_status(fc)

        out = dict(entry)
        out["fachgebiet"] = fach
        if meaningful_set:
            out["is_meaningful"] = bool(nq and (nq in meaningful_set))
        else:
            out["is_meaningful"] = False
        out["study_status"] = status
        out["study_exclude_reason"] = reason

        enriched.append(out)
        counts[status] = counts.get(status, 0) + 1

        if fc and status == "needs_review":
            problem_rows.append(
                {
                    "index": idx,
                    "fachgebiet": fach,
                    "source_file": str(entry.get("source_file") or ""),
                    "frage": q,
                    "issues": _compact_issues(fc),
                    "sources": _compact_sources(fc),
                }
            )
        if fc and status == "needs_context":
            maybe_rows.append(
                {
                    "index": idx,
                    "fachgebiet": fach,
                    "source_file": str(entry.get("source_file") or ""),
                    "frage": q,
                    "issues": _compact_issues(fc),
                    "sources": _compact_sources(fc),
                }
            )

    out_json = OUTPUT_DIR / f"evidenz_antworten_enriched_for_srs_{ts}.json"
    _write_json(out_json, enriched)

    # inventories
    inv_problem = OUTPUT_DIR / f"perplexity_problem_inventory_{ts}.csv"
    inv_maybe = OUTPUT_DIR / f"perplexity_maybe_inventory_{ts}.csv"

    fields = [
        "index",
        "fachgebiet",
        "source_file",
        "frage",
        "issues",
        "sources",
    ]
    _csv_write(inv_problem, problem_rows, fields)
    _csv_write(inv_maybe, maybe_rows, fields)

    # SRS export
    if args.export_srs:
        cards: List[Dict[str, Any]] = []
        for idx, entry in enumerate(enriched):
            if not isinstance(entry, dict):
                continue
            if entry.get("study_status") != "ready":
                continue
            if args.meaningful_only and not entry.get("is_meaningful"):
                continue

            q = str(entry.get("frage") or "").strip()
            a = str(entry.get("antwort") or "").strip()
            fach = str(entry.get("fachgebiet") or "").strip()

            if not q or not a:
                continue

            tags: List[str] = []
            if fach:
                tags.append(f"fachgebiet:{fach}")
            tags.append("source:medexamenai")

            cards.append(
                {
                    "id": _make_card_id(idx),
                    "question": q,
                    "answer": a,
                    "question_type": "qa",
                    "specialty": fach,
                    "difficulty": "medium",
                    "tags": tags,
                    "easiness_factor": 2.5,
                    "interval": 0,
                    "repetitions": 0,
                    "next_review": None,
                    "last_review": None,
                    "total_reviews": 0,
                    "correct_reviews": 0,
                    "average_quality": 0.0,
                }
            )

        srs_out = OUTPUT_DIR / f"srs_cards_ready_{ts}.json"
        payload = {
            "timestamp": datetime.now().isoformat(),
            "source": str(out_json.name),
            "total_cards": len(cards),
            "cards": cards,
        }
        _write_json(srs_out, payload)

        print(f"Wrote enriched: {out_json}")
        print(f"Wrote inventory (problem): {inv_problem}")
        print(f"Wrote inventory (maybe): {inv_maybe}")
        print(f"Wrote SRS cards: {srs_out}")
        print(f"Counts: {counts}")
        print(f"Problem rows: {len(problem_rows)}")
        print(f"Maybe rows: {len(maybe_rows)}")
        print(f"SRS cards: {len(cards)}")
    else:
        print(f"Wrote enriched: {out_json}")
        print(f"Wrote inventory (problem): {inv_problem}")
        print(f"Wrote inventory (maybe): {inv_maybe}")
        print(f"Counts: {counts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
