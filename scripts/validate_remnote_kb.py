#!/usr/bin/env python3
"""
Validiert (lokal, konservativ) die extrahierten RemNote-Notizen.

Ziel:
- RemNote als Wissensbasis nutzen, aber riskante Inhalte (Zahlen/Dosierungen/§) markieren.
- Ohne MedGemma/LLM: wir können NICHT "verified" behaupten, nur "needs_review" priorisieren.

Input:
- `_OUTPUT/remnote_merge/remnote_extracted_nodes.jsonl`

Output:
- `_OUTPUT/remnote_merge/remnote_nodes_validated.jsonl`
- `_OUTPUT/remnote_merge/remnote_validation_report.md`
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import importlib.util


# Kategorie-Regeln (analog zu eurer Lern-Priorität)
CATEGORY_RULES: list[tuple[str, re.Pattern[str]]] = [
    (
        "strahlenschutz",
        re.compile(
            r"(strahlenschutz|strlschv|euratom|alara|dosisgrenz|mSv|sievert|dosimeter|dosimetrie|"
            r"kontrollbereich|sperrbereich|fachkunde|sachkunde|röntgen.*(anfordern|fachkunde|sachkunde))",
            re.IGNORECASE,
        ),
    ),
    (
        "pharmakologie",
        re.compile(
            r"(dosierung|dosis|\bmg\b|µg|\bug\b|\bie\b|\biu\b|btm|btmvv|opioid|antibiotik|uaw|nebenwirkung|"
            r"rivaroxaban|xarelto|apixaban|eliquis|heparin|insulin|metformin|morphin|propofol)",
            re.IGNORECASE,
        ),
    ),
    (
        "rechtsmedizin",
        re.compile(
            r"(rechtsmedizin|leichenschau|todes(zeichen|art|ursache)?|obduktion|todesbescheinigung|"
            r"heilberg|berufsordnung|§\s*\d+|bgb|stgb|ifsg|meldepflicht)",
            re.IGNORECASE,
        ),
    ),
]


def classify(text: str) -> str:
    for name, rx in CATEGORY_RULES:
        if rx.search(text or ""):
            return name
    return "rest"


RISK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("legal_paragraph", re.compile(r"§\s*\d+", re.IGNORECASE)),
    ("dose_units", re.compile(r"\b\d+(?:[.,]\d+)?\s*(mg|g|µg|ug|ie|iu|ml)\b", re.IGNORECASE)),
    ("radiation_units", re.compile(r"\b\d+(?:[.,]\d+)?\s*(msv|sv)\b", re.IGNORECASE)),
    ("deadline", re.compile(r"\b(friste?n|innerhalb|tage|stunden)\b", re.IGNORECASE)),
]


def safe_backup_existing(path: Path) -> None:
    if not path.exists():
        return
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_{ts}")
    path.replace(backup)


def load_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def write_jsonl(path: Path, items: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="_OUTPUT/remnote_merge/remnote_extracted_nodes.jsonl")
    parser.add_argument("--out-jsonl", default="_OUTPUT/remnote_merge/remnote_nodes_validated.jsonl")
    parser.add_argument("--out-report", default="_OUTPUT/remnote_merge/remnote_validation_report.md")
    parser.add_argument("--max-items", type=int, default=0)
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    in_path = repo_root / args.input
    out_jsonl = repo_root / args.out_jsonl
    out_report = repo_root / args.out_report

    items = load_jsonl(in_path)
    if args.max_items and args.max_items > 0:
        items = items[: args.max_items]

    # Local validator (ohne `import core`, da core/__init__.py heavy imports triggert)
    validator = None
    validator_available = False
    validator_err = None
    try:
        mv_path = (repo_root / "core" / "medical_validator.py").resolve()
        spec = importlib.util.spec_from_file_location("_medical_validator_local", mv_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            MedicalValidationLayer = getattr(module, "MedicalValidationLayer")
            validator = MedicalValidationLayer()
            validator_available = True
    except Exception as e:
        validator_available = False
        validator_err = str(e)

    counts_status = Counter()
    counts_cat = Counter()
    counts_risk = Counter()
    needs_review_samples: list[dict] = []

    for it in items:
        text = (it.get("text") or "").strip()
        path_str = (it.get("path_str") or "").strip()
        blob = f"{path_str}\n{text}"

        category = classify(blob)
        counts_cat[category] += 1

        # Risk flags
        risk_flags: list[str] = []
        for name, rx in RISK_PATTERNS:
            if rx.search(blob):
                risk_flags.append(name)
                counts_risk[name] += 1

        # Local validation (dosages/labs/logic)
        local_meta: dict = {"available": validator_available}
        has_critical_or_error = False
        if validator_available and validator is not None and text:
            try:
                res = validator.validate(text, source_file="remnote")
                local_meta["is_valid"] = bool(res.is_valid)
                local_meta["confidence"] = float(getattr(res, "confidence_score", 0.0) or 0.0)
                local_meta["issues_count"] = len(getattr(res, "issues", []) or [])
                local_meta["warnings_count"] = len(getattr(res, "warnings", []) or [])
                # severity scan
                issues = getattr(res, "issues", []) or []
                severities = [getattr(i, "severity", None).value for i in issues if getattr(i, "severity", None)]
                local_meta["issue_severities"] = severities
                has_critical_or_error = any(s in {"error", "critical"} for s in severities)
            except Exception as e:
                local_meta["error"] = str(e)
        elif not validator_available:
            local_meta["error"] = locals().get("validator_err", "validator_unavailable")

        # QA Status (konservativ)
        qa_status = "unverified"
        if has_critical_or_error:
            qa_status = "needs_review"
        else:
            # harte Risk Gates: § / Dosierung / mSv → needs_review
            if any(f in {"legal_paragraph", "dose_units", "radiation_units"} for f in risk_flags):
                qa_status = "needs_review"

        it["category"] = category
        it["qa_status"] = qa_status
        it["risk_flags"] = risk_flags
        it["local_validation"] = local_meta

        counts_status[qa_status] += 1
        if qa_status == "needs_review" and len(needs_review_samples) < 30:
            needs_review_samples.append(
                {
                    "node_id": it.get("node_id"),
                    "path_str": path_str,
                    "text": text[:180],
                    "risk_flags": risk_flags,
                    "local_confidence": local_meta.get("confidence"),
                }
            )

    safe_backup_existing(out_jsonl)
    safe_backup_existing(out_report)
    write_jsonl(out_jsonl, items)

    # Report
    lines: list[str] = []
    lines.append("# RemNote Validation Report (lokal, konservativ)\n\n")
    lines.append(f"**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    lines.append(f"**Input:** `{in_path}`\n\n")
    lines.append(f"**Validator verfügbar:** {validator_available}\n\n")
    if validator_err:
        lines.append(f"**Validator-Fehler:** `{validator_err}`\n\n")
    lines.append("## QA Status\n\n")
    for k in ["needs_review", "unverified", "verified"]:
        if k in counts_status:
            lines.append(f"- **{k}**: {counts_status[k]}\n")
    lines.append("\n## Kategorien\n\n")
    for k in ["strahlenschutz", "pharmakologie", "rechtsmedizin", "rest"]:
        if k in counts_cat:
            lines.append(f"- **{k}**: {counts_cat[k]}\n")

    lines.append("\n## Risk Flags (Top)\n\n")
    for k, v in counts_risk.most_common(10):
        lines.append(f"- **{k}**: {v}\n")

    lines.append("\n---\n")
    lines.append("## Samples: needs_review (Top 30)\n\n")
    for s in needs_review_samples:
        lines.append(f"- `{s['node_id']}` | {s.get('path_str','')}\n")
        lines.append(f"  - risk: {', '.join(s.get('risk_flags') or [])}\n")
        lines.append(f"  - local_confidence: {s.get('local_confidence')}\n")
        lines.append(f"  - text: {s.get('text','')}\n")

    lines.append("\n---\n")
    lines.append("## Nächste Schritte (Validierung auf Projektstandard)\n\n")
    lines.append("- Für `needs_review`: MedGemma/RAG-Validierung + Zitate (AWMF/StrlSchV/BtMVV/IfSG etc.)\n")
    lines.append("- Erst nach externer Validierung: `qa_status=verified` setzen.\n")

    out_report.write_text("".join(lines), encoding="utf-8")
    print(f"✅ validated jsonl: {out_jsonl}")
    print(f"✅ report:         {out_report}")


if __name__ == "__main__":
    main()


