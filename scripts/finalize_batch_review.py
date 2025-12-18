#!/usr/bin/env python3
"""Finalisiert Batch-Review: merged corrected+validated und schreibt neue Outputs.

Inputs
- Base: `_OUTPUT/evidenz_antworten.json` (wird nur gelesen!)
- Corrected: `_OUTPUT/batch_corrected_*.json` (Default: neueste)
- Validated: `_OUTPUT/batch_validated_*.json` (Default: neueste)

Outputs (neu, Timestamp)
- `_OUTPUT/evidenz_antworten_updated_<TS>.json`  (niemals überschreiben!)
- `_OUTPUT/batch_review_report_<TS>.md`
- `_OUTPUT/batch_review_remaining_issues_<TS>.json`
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _pick_latest(output_dir: Path, pattern: str) -> Path:
    candidates = sorted(
        output_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"Keine Dateien für Pattern: {pattern}")
    return candidates[0]


def _run_id_from_name(name: str) -> str:
    m = re.match(r"batch_(?:corrected|validated)_(.+)\.json$", name)
    return m.group(1) if m else ""


def _as_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def _truncate(s: str, max_chars: int = 500) -> str:
    t = (s or "").strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1] + "…"


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalisiert Batch-Review Outputs.")
    parser.add_argument(
        "--base",
        default=str(OUTPUT_DIR / "evidenz_antworten.json"),
        help="Base JSON (nur lesen)",
    )
    parser.add_argument("--corrected", default="", help="batch_corrected JSON")
    parser.add_argument("--validated", default="", help="batch_validated JSON")
    parser.add_argument("--output", default="", help="Output updated evidenz JSON")
    args = parser.parse_args()

    base_path = Path(args.base)
    corrected_path = Path(args.corrected) if args.corrected else _pick_latest(
        OUTPUT_DIR, "batch_corrected_*.json"
    )
    validated_path = Path(args.validated) if args.validated else _pick_latest(
        OUTPUT_DIR, "batch_validated_*.json"
    )

    if not base_path.exists():
        raise SystemExit(f"Base fehlt: {base_path}")
    if not corrected_path.exists():
        raise SystemExit(f"Corrected fehlt: {corrected_path}")
    if not validated_path.exists():
        raise SystemExit(f"Validated fehlt: {validated_path}")

    ts = _now_ts()
    run_id = _run_id_from_name(corrected_path.name) or _run_id_from_name(
        validated_path.name
    )
    out_evidenz = Path(args.output) if args.output else OUTPUT_DIR / (
        f"evidenz_antworten_updated_{ts}.json"
    )
    out_report = OUTPUT_DIR / f"batch_review_report_{ts}.md"
    out_remaining = OUTPUT_DIR / f"batch_review_remaining_issues_{ts}.json"

    base = _read_json(base_path)
    if not isinstance(base, list):
        raise ValueError("Base evidenz_antworten.json muss Liste sein")

    corrected = _read_json(corrected_path)
    validated = _read_json(validated_path)
    if not isinstance(corrected, dict) or not isinstance(corrected.get("items"), list):
        raise ValueError("Corrected muss Objekt mit `items` sein")
    if not isinstance(validated, dict) or not isinstance(validated.get("items"), list):
        raise ValueError("Validated muss Objekt mit `items` sein")

    corr_map: Dict[str, Dict[str, Any]] = {}
    for it in corrected["items"]:
        if not isinstance(it, dict):
            continue
        rid = str(it.get("id") or "").strip()
        if rid:
            corr_map[rid] = it

    val_map: Dict[str, Dict[str, Any]] = {}
    for it in validated["items"]:
        if not isinstance(it, dict):
            continue
        rid = str(it.get("id") or "").strip()
        if rid:
            val_map[rid] = it

    counts = {"ok": 0, "maybe": 0, "problem": 0, "error": 0, "missing": 0}
    updated = 0
    total_cost = 0.0

    remaining: List[Dict[str, Any]] = []

    for rid, corr in corr_map.items():
        idx = _as_int(corr.get("index"))
        if idx is None or idx < 0 or idx >= len(base):
            counts["missing"] += 1
            remaining.append(
                {
                    "id": rid,
                    "index": corr.get("index"),
                    "reason": "index_out_of_range",
                }
            )
            continue

        korr = str(corr.get("antwort_korrigiert") or "").strip()
        meta = corr.get("__meta__", {}) if isinstance(corr.get("__meta__"), dict) else {}
        try:
            total_cost += float(meta.get("cost") or 0.0)
        except Exception:
            pass

        val = val_map.get(rid, {})
        verdict = str(val.get("verdict") or "maybe").strip().lower()
        if verdict not in {"ok", "maybe", "problem", "error"}:
            verdict = "maybe"
        counts[verdict] += 1

        # batch_review Metadata immer schreiben (auch bei problem/error)
        entry = base[idx]
        if not isinstance(entry, dict):
            continue
        v = entry.get("validation")
        if not isinstance(v, dict):
            v = {}
            entry["validation"] = v

        v["batch_review"] = {
            "run_id": run_id,
            "finalized_at": datetime.now().isoformat(),
            "verdict": verdict,
            "issues": val.get("issues", []) if isinstance(val.get("issues"), list) else [],
            "aktuelle_quellen": val.get("aktuelle_quellen", [])
            if isinstance(val.get("aktuelle_quellen"), list)
            else [],
            "empfehlung": str(val.get("empfehlung") or "").strip(),
            "llm": {
                "provider": meta.get("provider"),
                "model": meta.get("model"),
                "cost_usd": meta.get("cost", 0.0),
            },
        }

        # Update der Antwort nur wenn ok/maybe und korrigierte Antwort vorhanden
        if verdict in {"ok", "maybe"} and korr:
            entry["antwort"] = korr
            updated += 1
        else:
            remaining.append(
                {
                    "id": rid,
                    "index": idx,
                    "verdict": verdict,
                    "issues": val.get("issues", []) if isinstance(val.get("issues"), list) else [],
                    "empfehlung": str(val.get("empfehlung") or "").strip(),
                    "antwort_original": _truncate(str(corr.get("antwort_original") or "")),
                    "antwort_korrigiert": _truncate(korr),
                }
            )

    _write_json(out_evidenz, base)
    _write_json(
        out_remaining,
        {
            "generated_at": datetime.now().isoformat(),
            "run_id": run_id,
            "source_corrected": corrected_path.name,
            "source_validated": validated_path.name,
            "remaining_count": len(remaining),
            "items": remaining,
        },
    )

    report_lines = [
        "# Batch-Review Report",
        "",
        f"- Generated: `{datetime.now().isoformat()}`",
        f"- Run-ID: `{run_id}`",
        f"- Base (read-only): `{base_path.name}`",
        f"- Corrected: `{corrected_path.name}`",
        f"- Validated: `{validated_path.name}`",
        f"- Updated evidenz file: `{out_evidenz.name}`",
        f"- Remaining issues file: `{out_remaining.name}`",
        "",
        "## Summary",
        "",
        f"- Total corrected items: {len(corr_map)}",
        f"- Updated answers (ok/maybe + non-empty): {updated}",
        f"- Verdict counts: {counts}",
        f"- Total estimated LLM cost (correct stage): ~{total_cost:.2f} USD",
        "",
    ]
    _write_text(out_report, "\n".join(report_lines))

    print("Finalisierung abgeschlossen.")
    print(f"Updated evidenz: {out_evidenz}")
    print(f"Report: {out_report}")
    print(f"Remaining: {out_remaining} (n={len(remaining)})")
    print(f"Counts: {counts} | updated={updated} | cost≈{total_cost:.2f} USD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


