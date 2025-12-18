#!/usr/bin/env python3
"""Bereitet die Review-Items für die Batch-Pipeline vor (ohne API-Calls).

Inputs (Default)
- `_OUTPUT/review_queue_*.json` (neueste)
- `_OUTPUT/needs_context_prepared_*.json` (neueste)
- `_BIBLIOTHEK/leitlinien_manifest.json` (lokale Leitlinien-PDFs)

Output (neu, Timestamp)
- `_OUTPUT/batch_input_prepared_<TS>.json`

Harte Constraints
- `_OUTPUT/evidenz_antworten.json` wird NICHT überschrieben.
- Keine Secrets in Logs.
- Keine inhaltlichen Rewrites in-place.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Repo-Root in sys.path, damit `core.*` importierbar ist.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.guideline_fetcher import detect_medical_themes, map_themes_to_societies
from core.medical_validator import MedicalValidationLayer, ValidationIssue

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"
BIB_DIR = PROJECT_ROOT / "_BIBLIOTHEK"


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _pick_latest(output_dir: Path, pattern: str) -> Path:
    candidates = sorted(
        output_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"Keine Dateien für Pattern: {pattern}")
    return candidates[0]


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


_REG_NR_RE = re.compile(
    r"(nvl-\d+[a-z]?|\d{3}-\d{3}[a-z]?|esc-[a-z]{2,}-\d{4})",
    flags=re.IGNORECASE,
)


def _title_from_file(path_str: str) -> str:
    name = Path(path_str).stem
    # Entferne leading Reg-Nr
    name = _REG_NR_RE.sub("", name).strip("_- ")
    return name.replace("_", " ").strip()


def _reg_nr_from_file(path_str: str) -> str:
    m = _REG_NR_RE.search(Path(path_str).name)
    return m.group(1) if m else ""


def _specialty_from_path(path_str: str) -> str:
    parts = Path(path_str).parts
    # Erwartung: Leitlinien/<Fach>/<Datei>.pdf
    if len(parts) >= 2:
        return str(parts[-2])
    return ""


@dataclass(frozen=True)
class GuidelineEntry:
    title: str
    file: str
    reg_nr: str
    specialty: str


def _load_leitlinien_manifest(path: Path) -> List[GuidelineEntry]:
    payload = _read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("leitlinien_manifest.json muss Objekt mit `items` sein")
    out: List[GuidelineEntry] = []
    for it in payload["items"]:
        if not isinstance(it, dict):
            continue
        file_path = str(it.get("file") or "").strip()
        if not file_path:
            continue
        out.append(
            GuidelineEntry(
                title=_title_from_file(file_path),
                file=file_path,
                reg_nr=_reg_nr_from_file(file_path),
                specialty=_specialty_from_path(file_path),
            )
        )
    return out


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def _rank_guidelines(
    keywords: List[str],
    guidelines: List[GuidelineEntry],
    *,
    limit: int,
) -> List[GuidelineEntry]:
    if not keywords or not guidelines:
        return []

    keys = [_norm(k) for k in keywords if _norm(k)]
    keys = list(dict.fromkeys(keys))  # dedupe, order-preserving

    scored: List[Tuple[float, GuidelineEntry]] = []
    for g in guidelines:
        hay = _norm(f"{g.file} {g.title} {g.specialty} {g.reg_nr}")
        score = 0.0
        for k in keys:
            if k and k in hay:
                score += 1.0
        # Bonus: Fachverzeichnis-Match
        for k in keys:
            if g.specialty and _norm(g.specialty) == k:
                score += 1.5
        if score > 0:
            scored.append((score, g))

    scored.sort(key=lambda t: (-t[0], t[1].file))
    return [g for _s, g in scored[:limit]]


def _issues_summary(issues: List[ValidationIssue]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i in issues[:20]:
        try:
            out.append(i.to_dict())
        except Exception:
            out.append({"code": "UNKNOWN", "message": str(i), "severity": "error"})
    return out


def _local_validation_dict(result: Any) -> Dict[str, Any]:
    # result ist ValidationResult
    issues = getattr(result, "issues", []) or []
    warnings = getattr(result, "warnings", []) or []

    issue_dicts = _issues_summary(list(issues))
    warn_dicts = _issues_summary(list(warnings))

    def has_error(prefix: str) -> bool:
        for it in issue_dicts:
            code = str(it.get("code") or "")
            if code.startswith(prefix):
                return True
        return False

    return {
        "is_valid": bool(getattr(result, "is_valid", False)),
        "confidence_score": float(getattr(result, "confidence_score", 0.0)),
        "dosierungen_ok": not has_error("DOSAGE_"),
        "laborwerte_ok": not has_error("LAB_"),
        "icd_ok": not has_error("ICD10_"),
        "issues": issue_dicts,
        "warnings": warn_dicts,
        "metadata": getattr(result, "metadata", {}) or {},
    }


def _complexity(
    priority: str,
    local_validation: Dict[str, Any],
    issue_count: int,
) -> str:
    pr = (priority or "").strip().lower()
    if pr == "high":
        return "high"
    if not local_validation.get("is_valid", True):
        return "high"
    if issue_count >= 4:
        return "medium"
    return "low"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bereitet Review-Items für Batch-Korrektur vor (lokal)."
    )
    parser.add_argument("--review-queue", default="", help="review_queue JSON")
    parser.add_argument(
        "--needs-context",
        default="",
        help="needs_context_prepared JSON",
    )
    parser.add_argument(
        "--leitlinien-manifest",
        default=str(BIB_DIR / "leitlinien_manifest.json"),
        help="leitlinien_manifest.json",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output JSON (default: _OUTPUT/batch_input_prepared_<TS>.json)",
    )
    parser.add_argument(
        "--limit-guidelines",
        type=int,
        default=5,
        help="Max. zugeordnete Leitlinien pro Item (default: 5)",
    )
    args = parser.parse_args()

    review_path = Path(args.review_queue) if args.review_queue else _pick_latest(
        OUTPUT_DIR,
        "review_queue_*.json",
    )
    needs_ctx_path = Path(args.needs_context) if args.needs_context else _pick_latest(
        OUTPUT_DIR,
        "needs_context_prepared_*.json",
    )
    manifest_path = Path(args.leitlinien_manifest)

    if not review_path.exists():
        raise SystemExit(f"Input fehlt: {review_path}")
    if not needs_ctx_path.exists():
        raise SystemExit(f"Input fehlt: {needs_ctx_path}")
    if not manifest_path.exists():
        raise SystemExit(f"Input fehlt: {manifest_path}")

    ts = _now_ts()
    out_path = Path(args.output) if args.output else OUTPUT_DIR / (
        f"batch_input_prepared_{ts}.json"
    )

    review_queue = _read_json(review_path)
    if not isinstance(review_queue, dict) or not isinstance(review_queue.get("items"), list):
        raise ValueError("review_queue muss Objekt mit `items` sein")

    needs_ctx = _read_json(needs_ctx_path)
    if not isinstance(needs_ctx, dict) or not isinstance(needs_ctx.get("items"), list):
        raise ValueError("needs_context_prepared muss Objekt mit `items` sein")

    ctx_map: Dict[int, Dict[str, Any]] = {}
    for it in needs_ctx["items"]:
        if not isinstance(it, dict):
            continue
        idx = _safe_int(it.get("index"))
        if idx is None:
            continue
        ctx_map[idx] = it

    guidelines = _load_leitlinien_manifest(manifest_path)
    validator = MedicalValidationLayer()

    prepared_items: List[Dict[str, Any]] = []

    for it in review_queue["items"]:
        if not isinstance(it, dict):
            continue
        idx = _safe_int(it.get("index"))
        if idx is None:
            continue

        study_status = str(it.get("study_status") or "").strip()
        frage_original = str(it.get("frage") or "").strip()
        fachgebiet = str(it.get("fachgebiet") or "").strip()
        source_file = str(it.get("source_file") or "").strip()
        antwort_original = str(it.get("antwort") or "").strip()

        ctx = ctx_map.get(idx) if study_status == "needs_context" else None

        frage = frage_original
        context_lines: List[str] = []
        source_page: Optional[int] = None
        source_path = ""
        match_method = ""
        ctx_conf = None

        if ctx:
            frage = str(ctx.get("frage_mit_kontext") or frage_original).strip()
            context_lines = ctx.get("context_lines", []) if isinstance(
                ctx.get("context_lines"), list
            ) else []
            source_page = _safe_int(ctx.get("source_page"))
            source_path = str(ctx.get("source_path") or "").strip()
            match_method = str(ctx.get("match_method") or "").strip()
            try:
                ctx_conf = float(ctx.get("confidence"))
            except Exception:
                ctx_conf = None

        issues_compact = str(it.get("issues_compact") or "").strip()
        issues_list = it.get("issues", [])
        if not isinstance(issues_list, list):
            issues_list = []

        # Theme-Erkennung nur aus Text (keine API)
        theme_input = " ".join([frage, issues_compact, fachgebiet]).strip()
        themes = detect_medical_themes(theme_input)
        society_scores = map_themes_to_societies(themes)

        theme_names = [t for t, _s in themes]
        keyword_pool = theme_names + list(society_scores.keys())
        if fachgebiet:
            keyword_pool.append(fachgebiet)

        top_guidelines = _rank_guidelines(
            keyword_pool,
            guidelines,
            limit=int(args.limit_guidelines),
        )
        zugeordnet = []
        for g in top_guidelines:
            zugeordnet.append(
                {
                    "titel": g.title,
                    "pfad": g.file,
                    "reg_nr": g.reg_nr,
                }
            )

        # Lokale Validierung (ohne LLM)
        val_res = validator.validate_qa_pair(
            question=frage,
            answer=antwort_original,
            source_file=source_file,
        )
        local_val = _local_validation_dict(val_res)

        priority = str(it.get("priority") or "").strip().lower() or "medium"
        komplexitaet = _complexity(priority, local_val, len(issues_list))

        prepared_items.append(
            {
                "id": f"evidenz_{idx}",
                "index": idx,
                "frage": frage,
                "frage_original": frage_original,
                "fachgebiet": fachgebiet,
                "source_file": source_file,
                "study_status": study_status,
                "priority": priority,
                "priority_reason": str(it.get("priority_reason") or "").strip(),
                "antwort_original": antwort_original,
                "issues": issues_list,
                "issues_compact": issues_compact,
                "optional_fix_snippet": str(it.get("optional_fix_snippet") or "").strip(),
                "suggested_sources": it.get("suggested_sources", []),
                "context": {
                    "has_context": bool(ctx),
                    "source_path": source_path,
                    "source_page": source_page,
                    "context_lines": context_lines,
                    "match_method": match_method,
                    "confidence": ctx_conf,
                },
                "detected_themes": [{"theme": t, "score": s} for t, s in themes],
                "society_scores": society_scores,
                "zugeordnete_leitlinien": zugeordnet,
                "lokale_validierung": local_val,
                "komplexitaet": komplexitaet,
            }
        )

    payload = {
        "generated_at": datetime.now().isoformat(),
        "source_review_queue": review_path.name,
        "source_needs_context_prepared": needs_ctx_path.name,
        "leitlinien_manifest": str(manifest_path.relative_to(PROJECT_ROOT)),
        "total_items": len(prepared_items),
        "items": prepared_items,
    }

    _write_json(out_path, payload)

    print("Batch-Input Vorbereitung abgeschlossen.")
    print(f"Input review_queue: {review_path.name}")
    print(f"Input needs_context: {needs_ctx_path.name}")
    print(f"Output: {out_path}")
    print(f"Items: {len(prepared_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


