#!/usr/bin/env python3
"""
Erstellt eine priorisierte Validierungs-Queue aus RemNote-Notizen.

Input:
- `_OUTPUT/remnote_merge/remnote_nodes_validated.jsonl` (von `scripts/validate_remnote_kb.py`)

Output:
- `_OUTPUT/remnote_merge/remnote_needs_review_queue.jsonl`
- `_OUTPUT/remnote_merge/remnote_needs_review_queue_report.md`

Ziel:
- Alles, was lokal als `qa_status=needs_review` markiert ist, wird sortiert:
  1) Strahlenschutz
  2) Pharmakologie
  3) Rechtsmedizin
  4) Rest
- innerhalb Kategorie: riskanter (mSv/StrlSchV/Dosierungen/§) zuerst.

Hinweis:
Dieses Script macht *keine* externe Validierung, sondern bereitet nur die Queue vor.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


CATEGORY_ORDER = {
    "strahlenschutz": 0,
    "pharmakologie": 1,
    "rechtsmedizin": 2,
    "rest": 3,
}

# Kleinere Zahl = höhere Priorität
RISK_ORDER = {
    "radiation_units": 0,
    "legal_paragraph": 1,
    "dose_units": 2,
    "deadline": 3,
}


def load_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def safe_backup_existing(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    path.replace(backup)


def primary_risk_rank(risk_flags: List[str]) -> int:
    if not risk_flags:
        return 99
    return min(RISK_ORDER.get(f, 90) for f in risk_flags)


def build_medgemma_prompt(item: Dict[str, Any]) -> str:
    """
    Prompt für text-only Notizvalidierung.
    Output-Format ist bewusst simpel (robust gegen parsing issues).
    """
    path_str = (item.get("path_str") or "").strip()
    text = (item.get("text") or "").strip()
    category = (item.get("category") or "rest").strip()
    risk_flags = item.get("risk_flags") or []
    risk_flags_str = ", ".join(risk_flags) if risk_flags else "none"

    return (
        "Du bist Prüfer für die deutsche ärztliche Kenntnisprüfung Münster.\n\n"
        "Aufgabe: Validiere die folgende Notiz. Wenn Zahlen/Dosierungen/Paragraphen vorkommen, "
        "prüfe sie streng. Wenn du es ohne sichere Evidenz nicht bestätigen kannst, markiere NEEDS_REVIEW.\n\n"
        "Output-Format (exakt so):\n"
        "QA_VERDICT: VERIFIED oder NEEDS_REVIEW\n"
        "NOTES:\n"
        "- [kurz: was ist korrekt?]\n"
        "- [kurz: was ist unklar/falsch?]\n"
        "CORRECTED_VERSION:\n"
        "[korrigierte Notiz (kurz, prüfungsorientiert) ODER 'unchanged']\n\n"
        f"KATEGORIE: {category}\n"
        f"RISK_FLAGS: {risk_flags_str}\n"
        f"PFAD: {path_str}\n"
        "NOTIZ:\n"
        f"{text}\n"
    )


def sort_key(item: Dict[str, Any]) -> Tuple[int, int, int]:
    category = (item.get("category") or "rest").strip()
    cat_rank = CATEGORY_ORDER.get(category, 99)
    risk_rank = primary_risk_rank(item.get("risk_flags") or [])
    # längere Notizen zuerst (mehr Risiko/Info)
    length_rank = -len((item.get("text") or ""))
    return (cat_rank, risk_rank, length_rank)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="_OUTPUT/remnote_merge/remnote_nodes_validated.jsonl")
    parser.add_argument("--out-jsonl", default="_OUTPUT/remnote_merge/remnote_needs_review_queue.jsonl")
    parser.add_argument("--out-report", default="_OUTPUT/remnote_merge/remnote_needs_review_queue_report.md")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    in_path = repo_root / args.input
    out_jsonl = repo_root / args.out_jsonl
    out_report = repo_root / args.out_report

    items = load_jsonl(in_path)
    needs_review = [it for it in items if (it.get("qa_status") or "") == "needs_review"]
    needs_review.sort(key=sort_key)

    if args.limit and args.limit > 0:
        needs_review = needs_review[: args.limit]

    counts_cat = Counter((it.get("category") or "rest") for it in needs_review)
    counts_risk = Counter()
    for it in needs_review:
        for f in (it.get("risk_flags") or []):
            counts_risk[f] += 1

    # Write queue JSONL
    safe_backup_existing(out_jsonl)
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for rank, it in enumerate(needs_review, 1):
            record = {
                "queue_rank": rank,
                "node_id": it.get("node_id"),
                "category": it.get("category") or "rest",
                "risk_flags": it.get("risk_flags") or [],
                "path_str": it.get("path_str") or "",
                "text": it.get("text") or "",
                "export": it.get("export") or {},
                "local_validation": it.get("local_validation") or {},
                "medgemma_prompt": build_medgemma_prompt(it),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Report
    safe_backup_existing(out_report)
    lines: list[str] = []
    lines.append("# RemNote Needs-Review Queue\n\n")
    lines.append(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    lines.append(f"**Input:** `{in_path}`\n\n")
    lines.append(f"**Output:** `{out_jsonl}`\n\n")
    lines.append(f"**Queue-Länge:** {len(needs_review)}\n\n")

    lines.append("## Kategorien\n\n")
    for k in ["strahlenschutz", "pharmakologie", "rechtsmedizin", "rest"]:
        if counts_cat.get(k):
            lines.append(f"- **{k}**: {counts_cat[k]}\n")

    lines.append("\n## Risk Flags (Top)\n\n")
    for k, v in counts_risk.most_common(10):
        lines.append(f"- **{k}**: {v}\n")

    lines.append("\n---\n")
    lines.append("## Top 20 (Preview)\n\n")
    for it in needs_review[:20]:
        node_id = it.get("node_id")
        path_str = it.get("path_str") or ""
        cat = it.get("category") or "rest"
        risk = ", ".join(it.get("risk_flags") or [])
        text = (it.get("text") or "").strip().replace("\n", " ")
        if len(text) > 200:
            text = text[:200] + "…"
        lines.append(f"- `{node_id}` | **{cat}** | risk: {risk}\n")
        lines.append(f"  - {path_str}\n")
        lines.append(f"  - {text}\n")

    out_report.write_text("".join(lines), encoding="utf-8")

    print(f"✅ queue:  {out_jsonl} ({len(needs_review)} items)")
    print(f"✅ report: {out_report}")


if __name__ == "__main__":
    main()


