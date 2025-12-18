#!/usr/bin/env python3
"""Fehler-Agent: Backfill + Review-Queue für Lern-/Review-Workflows.

Ziel
- Erzeuge eine NEUE, verbesserte Arbeitsdatei für Lern-/Review-Workflows, ohne
  irgendeine kanonische Datei zu überschreiben.
- Fokus: "needs_review" (Problem) + "needs_context" (Maybe/Context)
  so aufbereiten, dass sie schnell abgearbeitet werden können.

Harte Constraints
- NICHT anfassen/überschreiben: _OUTPUT/evidenz_antworten.json
- Keine automatische inhaltliche Umschreibung von Antworten in-place.
- Keine Secrets loggen.
- Ausschließlich neue Output-Dateien mit Timestamp.

Inputs (Defaults)
- _OUTPUT/evidenz_antworten_enriched_for_srs_20251215_1529.json
- _OUTPUT/perplexity_problem_inventory_20251215_1529.csv
- _OUTPUT/perplexity_maybe_inventory_20251215_1529.csv
- _OUTPUT/perplexity_factcheck_sample_20251212_2008_patched_20251213_1820.json

Deliverables (alles neu, Timestamp)
1) _OUTPUT/evidenz_antworten_enriched_for_srs_fixed_<TS>.json
2) _OUTPUT/review_queue_<TS>.json
3) Optional: _OUTPUT/srs_cards_review_queue_<TS>.json

Hinweis zur Input-Struktur
- Einige Runs erzeugen eine Liste (list[dict]), andere ein Objekt
  mit `items: [...]`.
  Dieses Script unterstützt beides und schreibt die gleiche Top-Level-Struktur
  wie das Input-Artefakt.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"


@dataclass(frozen=True)
class Inputs:
    enriched_path: Path
    problem_inventory_path: Path
    maybe_inventory_path: Path
    factcheck_report_path: Path


_TAG_CLEAN_RE = re.compile(r"[^\w:.-]+", flags=re.UNICODE)


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _norm(text: str) -> str:
    return " ".join((text or "").strip().split()).lower()


def _coerce_str(v: Any) -> str:
    return "" if v is None else str(v)


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def _parse_enriched_payload(
    payload: Any,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str]:
    """Return (items, meta, top_level_kind)."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)], {}, "list"

    if isinstance(payload, dict):
        maybe_items = payload.get("items")
        if isinstance(maybe_items, list):
            meta = {k: v for k, v in payload.items() if k != "items"}
            items = [x for x in maybe_items if isinstance(x, dict)]
            return items, meta, "object"

    raise ValueError("Input enriched JSON muss Liste oder Objekt mit `items` sein")


def _load_inventory_csv(path: Path) -> Dict[int, Dict[str, str]]:
    """Lädt Inventory CSV.

    Erwartete Spalten:
    - index, fachgebiet, source_file, frage, issues, sources
    """
    out: Dict[int, Dict[str, str]] = {}
    if not path.exists():
        return out

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            idx = _safe_int(row.get("index"))
            if idx is None:
                continue
            out[idx] = {
                "index": str(idx),
                "fachgebiet": _coerce_str(row.get("fachgebiet")).strip(),
                "source_file": _coerce_str(row.get("source_file")).strip(),
                "frage": _coerce_str(row.get("frage")).strip(),
                "issues": _coerce_str(row.get("issues")).strip(),
                "sources": _coerce_str(row.get("sources")).strip(),
            }
    return out


def _load_factcheck_report(
    path: Path,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """Lädt den gepatchten Factcheck-Report.

    Erwartete Struktur:
    {
      "timestamp": ...,
      "results": [
        {
          "index_in_evidenz_antworten": int,
          "frage": str,
          "verdict": "ok"|"problem"|"maybe"|...,
          "issues": [...],
          "suggested_sources": [...],
          ...
        }
      ]
    }

    Returns:
      - by_index: index -> result
      - by_question_norm: norm(frage) -> result
    """
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Factcheck-Report muss ein JSON-Objekt sein")

    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("Factcheck-Report muss `results` als Liste enthalten")

    by_index: Dict[int, Dict[str, Any]] = {}
    by_q: Dict[str, Dict[str, Any]] = {}

    for r in results:
        if not isinstance(r, dict):
            continue
        idx = _safe_int(r.get("index_in_evidenz_antworten"))
        q = _coerce_str(r.get("frage")).strip()
        if idx is not None:
            by_index[idx] = r
        nq = _norm(q)
        if nq and nq not in by_q:
            by_q[nq] = r

    return by_index, by_q


def _classify_from_factcheck(fc: Optional[Dict[str, Any]]) -> Tuple[str, str]:
    """Return (study_status, study_exclude_reason)."""
    if not isinstance(fc, dict):
        return "unknown", "no_factcheck"

    verdict = _coerce_str(fc.get("verdict")).strip().lower()
    issues = fc.get("issues")
    issues_text = ""
    if isinstance(issues, list):
        issues_text = " ".join(str(x) for x in issues)
    issues_l = issues_text.lower()

    if verdict == "ok":
        return "ready", ""
    if verdict == "problem":
        return "needs_review", "factcheck_problem"
    if verdict == "maybe":
        # Heuristik: meist Kontext-/Bild-/Falldarstellung fehlt
        if any(k in issues_l for k in ["bild", "kontext", "falldarstellung"]):
            return "needs_context", "missing_context"
        if "kein parsebares json" in issues_l:
            return "unknown", "factcheck_non_json"
        return "needs_review", "factcheck_maybe"

    return "unknown", "factcheck_unknown"


def _factcheck_is_missing_or_unknown(fc: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(fc, dict):
        return True
    verdict = _coerce_str(fc.get("verdict")).strip().lower()
    return verdict in {"", "unknown", "n/a"}


def _merge_factcheck(
    *,
    existing_fc: Optional[Dict[str, Any]],
    report_fc: Dict[str, Any],
    report_file_name: str,
) -> Tuple[Dict[str, Any], bool]:
    """Merged factcheck dict. Returns (merged, changed)."""
    existing = existing_fc if isinstance(existing_fc, dict) else {}

    # Minimales Ziel-Schema (nicht übermäßig aufblasen)
    merged: Dict[str, Any] = dict(existing)

    # Report ist Source-of-Truth für Kernfelder
    core = {
        "verdict": report_fc.get("verdict"),
        "issues": report_fc.get("issues", []),
        "suggested_sources": report_fc.get("suggested_sources", []),
        "optional_fix_snippet": report_fc.get("optional_fix_snippet", ""),
        "warnings": report_fc.get("warnings", []),
        "meta": report_fc.get("meta", {}),
    }
    merged.update(core)

    # Provenienz
    merged.setdefault("report_file", report_file_name)

    changed = merged != existing
    return merged, changed


def _normalize_tag(tag: str) -> str:
    t = _coerce_str(tag).strip()
    if not t:
        return ""
    t = t.replace(",", " ")
    t = " ".join(t.split()).replace(" ", "_")
    t = _TAG_CLEAN_RE.sub("_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t


def _review_hints_text(fc: Dict[str, Any]) -> str:
    verdict = _coerce_str(fc.get("verdict")).strip()
    raw_issues = fc.get("issues")
    issues: List[Any] = raw_issues if isinstance(raw_issues, list) else []

    raw_sources = fc.get("suggested_sources")
    sources: List[Any] = raw_sources if isinstance(raw_sources, list) else []

    lines: List[str] = []
    lines.append("Review-Hinweise (nicht als Fakten übernehmen, nur Prüfliste)")
    if verdict:
        lines.append(f"Verdikt: {verdict}")

    if issues:
        lines.append("Probleme (Issues):")
        for it in issues:
            s = _coerce_str(it).strip()
            if s:
                lines.append(f"- {s}")

    if sources:
        lines.append("Empfohlene Quellen:")
        for s in sources:
            if not isinstance(s, dict):
                continue
            title = _coerce_str(s.get("title")).strip()
            url = _coerce_str(s.get("url")).strip()
            if title and url:
                lines.append(f"- {title}: {url}")
            elif url:
                lines.append(f"- {url}")
            elif title:
                lines.append(f"- {title}")

    return "\n".join(lines)


def _priority(entry: Dict[str, Any], fc: Dict[str, Any]) -> Tuple[str, str]:
    """Return (priority, reason)."""
    status = _coerce_str(entry.get("study_status")).strip().lower()
    fach = _coerce_str(entry.get("fachgebiet")).strip()
    frage = _coerce_str(entry.get("frage")).strip()

    raw_issues = fc.get("issues")
    issues: List[Any] = raw_issues if isinstance(raw_issues, list) else []
    issues_text = " ".join(_coerce_str(x) for x in issues)
    issues_l = issues_text.lower()
    frage_l = frage.lower()
    fach_l = fach.lower()

    # Kontext-Fälle sind i.d.R. niedrig priorisiert.
    if status == "needs_context":
        if any(
            k in issues_l
            for k in ["falsch", "kontraind", "dosis", "leitlinienfern", "gefähr"]
        ):
            return "medium", "Kontext fehlt, aber potenziell kritisch"
        return "low", "Kontext/Falldaten fehlen (needs_context)"

    # needs_review / problem
    legal_terms = ["gesetz", "bgb", "stgb", "sgb", "btmg", "pflicht", "recht"]
    legalish = any(k in frage_l for k in legal_terms) or ("rechtsmedizin" in fach_l)

    critical_issue = any(
        k in issues_l
        for k in [
            "falsch",
            "leitlinienfern",
            "kontraind",
            "dosis",
            "übersterb",
            "gefähr",
            "nicht korrekt",
        ]
    )

    if legalish:
        return "high", "rechtlich/berufsrechtlich besonders prüfungsrelevant"
    if critical_issue:
        return "high", "potenziell leitlinien-/sicherheitskritisch laut Issues"

    # Medizinische Kernkritikalität (grobe Heuristik)
    acute_terms = ["reanimation", "stemi", "acs", "anaphyl", "hyperkal", "insulin"]
    if any(k in frage_l for k in acute_terms):
        return "high", "akutmedizinisch/therapiekritisch"

    return "medium", "inhaltlich zu prüfen/zu präzisieren"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill Factcheck-Metadaten (Meaningful) + erzeugt review_queue "
            "JSON (optional: SRS Review-Cards)."
        )
    )
    parser.add_argument(
        "--enriched",
        default=str(
            DEFAULT_OUTPUT_DIR / "evidenz_antworten_enriched_for_srs_20251215_1529.json"
        ),
        help="Input enriched_for_srs JSON",
    )
    parser.add_argument(
        "--problem-inventory",
        default=str(
            DEFAULT_OUTPUT_DIR / "perplexity_problem_inventory_20251215_1529.csv"
        ),
        help="Input Review-Inventory CSV",
    )
    parser.add_argument(
        "--maybe-inventory",
        default=str(
            DEFAULT_OUTPUT_DIR / "perplexity_maybe_inventory_20251215_1529.csv"
        ),
        help="Input Context-Inventory CSV",
    )
    parser.add_argument(
        "--factcheck-report",
        default=str(
            DEFAULT_OUTPUT_DIR
            / "perplexity_factcheck_sample_20251212_2008_patched_20251213_1820.json"
        ),
        help="Gepatchter Factcheck-Report (Backfill-Quelle)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output-Verzeichnis (default: _OUTPUT)",
    )
    parser.add_argument(
        "--write-srs-review",
        action="store_true",
        help="Optional: zusätzlich srs_cards_review_queue_<TS>.json schreiben",
    )

    args = parser.parse_args()

    inputs = Inputs(
        enriched_path=Path(args.enriched),
        problem_inventory_path=Path(args.problem_inventory),
        maybe_inventory_path=Path(args.maybe_inventory),
        factcheck_report_path=Path(args.factcheck_report),
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if inputs.enriched_path.name == "evidenz_antworten.json":
        raise SystemExit(
            "Sicherheitsstopp: evidenz_antworten.json darf nicht als Input/Output dienen"
        )

    for p in [
        inputs.enriched_path,
        inputs.problem_inventory_path,
        inputs.maybe_inventory_path,
        inputs.factcheck_report_path,
    ]:
        if not p.exists():
            raise SystemExit(f"Input nicht gefunden: {p}")

    ts = _now_ts()

    out_fixed = out_dir / f"evidenz_antworten_enriched_for_srs_fixed_{ts}.json"
    out_review_queue = out_dir / f"review_queue_{ts}.json"
    out_srs_review = out_dir / f"srs_cards_review_queue_{ts}.json"

    # Load inputs
    enriched_payload = _read_json(inputs.enriched_path)
    items, meta, top_kind = _parse_enriched_payload(enriched_payload)

    inv_problem = _load_inventory_csv(inputs.problem_inventory_path)
    inv_maybe = _load_inventory_csv(inputs.maybe_inventory_path)

    fc_by_index, fc_by_q = _load_factcheck_report(inputs.factcheck_report_path)

    # Bestandsaufnahme (vorher)
    meaningful_total = 0
    meaningful_missing_fc_before = 0
    meaningful_unknown_status_before = 0

    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        if bool(e.get("is_meaningful")):
            meaningful_total += 1
            validation = e.get("validation")
            if isinstance(validation, dict):
                fc = validation.get("perplexity_factcheck")
            else:
                fc = None
            if _factcheck_is_missing_or_unknown(fc):
                meaningful_missing_fc_before += 1
            if _coerce_str(e.get("study_status")).strip().lower() == "unknown":
                meaningful_unknown_status_before += 1

    # Apply backfill + status consistency
    backfilled_by_index = 0
    backfilled_by_question = 0
    fc_changed_total = 0
    still_missing_fc_after = 0

    status_counts_after: Counter[str] = Counter()

    mismatches_problem = 0
    mismatches_maybe = 0

    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue

        validation = e.get("validation")
        if not isinstance(validation, dict):
            validation = {}
            e["validation"] = validation

        existing_fc = validation.get("perplexity_factcheck")

        # Backfill nur für meaningful
        if bool(e.get("is_meaningful")):
            report_fc = fc_by_index.get(i)
            used = "index"
            if report_fc is None:
                used = "question"
                report_fc = fc_by_q.get(_norm(_coerce_str(e.get("frage"))))

            if report_fc is not None:
                merged_fc, changed = _merge_factcheck(
                    existing_fc=existing_fc,
                    report_fc=report_fc,
                    report_file_name=inputs.factcheck_report_path.name,
                )
                validation["perplexity_factcheck"] = merged_fc
                if changed:
                    fc_changed_total += 1
                    if used == "index":
                        backfilled_by_index += 1
                    else:
                        backfilled_by_question += 1
            else:
                # Should not happen, aber konsistent bleiben
                if not isinstance(existing_fc, dict):
                    still_missing_fc_after += 1

        # Status-Konsistenz (für alle Einträge, wenn FC vorhanden)
        fc_current = validation.get("perplexity_factcheck")
        status, reason = _classify_from_factcheck(fc_current)
        e["study_status"] = status
        e["study_exclude_reason"] = reason

        status_counts_after[status] += 1

        # Inventory vs Verdict Konsistenz (nur meaningful/Review-Fälle)
        if bool(e.get("is_meaningful")) and isinstance(fc_current, dict):
            v = _coerce_str(fc_current.get("verdict")).strip().lower()
            if i in inv_problem and v != "problem":
                mismatches_problem += 1
            if i in inv_maybe and v != "maybe":
                mismatches_maybe += 1

    # Post-Check: alle meaningful sollten Factcheck haben
    meaningful_missing_fc_after = 0
    meaningful_unknown_verdict_after = 0
    meaningful_status_counts: Counter[str] = Counter()

    for i, e in enumerate(items):
        if not isinstance(e, dict) or not bool(e.get("is_meaningful")):
            continue
        validation = e.get("validation")
        if isinstance(validation, dict):
            fc = validation.get("perplexity_factcheck")
        else:
            fc = None
        if not isinstance(fc, dict):
            meaningful_missing_fc_after += 1
            continue
        verdict = _coerce_str(fc.get("verdict")).strip().lower()
        if verdict in {"", "unknown", "n/a"}:
            meaningful_unknown_verdict_after += 1
        meaningful_status_counts[_coerce_str(e.get("study_status"))] += 1

    # Build review_queue
    review_items: List[Dict[str, Any]] = []
    prio_counts: Counter[str] = Counter()

    for i, e in enumerate(items):
        if not isinstance(e, dict) or not bool(e.get("is_meaningful")):
            continue

        status = _coerce_str(e.get("study_status")).strip()
        if status not in {"needs_review", "needs_context"}:
            continue

        validation = e.get("validation")
        if isinstance(validation, dict):
            fc = validation.get("perplexity_factcheck")
        else:
            fc = None
        if not isinstance(fc, dict):
            continue

        priority, prio_reason = _priority(e, fc)
        prio_counts[priority] += 1

        inv_row = inv_problem.get(i) or inv_maybe.get(i) or {}

        raw_issues = fc.get("issues")
        issues_list: List[Any] = raw_issues if isinstance(raw_issues, list) else []

        raw_sources = fc.get("suggested_sources")
        sources_list: List[Any] = raw_sources if isinstance(raw_sources, list) else []

        review_items.append(
            {
                "index": i,
                "frage": _coerce_str(e.get("frage")).strip(),
                "fachgebiet": _coerce_str(e.get("fachgebiet")).strip()
                or inv_row.get("fachgebiet", ""),
                "source_file": _coerce_str(e.get("source_file")).strip()
                or inv_row.get("source_file", ""),
                "antwort": _coerce_str(e.get("antwort")).strip(),
                "study_status": status,
                "study_exclude_reason": _coerce_str(
                    e.get("study_exclude_reason")
                ).strip(),
                "verdict": _coerce_str(fc.get("verdict")).strip(),
                "issues": issues_list,
                "issues_compact": " | ".join(
                    [
                        _coerce_str(x).strip()
                        for x in issues_list
                        if _coerce_str(x).strip()
                    ][:5]
                ),
                "issues_compact_inventory": inv_row.get("issues", ""),
                "suggested_sources": sources_list,
                "sources_compact_inventory": inv_row.get("sources", ""),
                "optional_fix_snippet": _coerce_str(
                    fc.get("optional_fix_snippet")
                ).strip(),
                "priority": priority,
                "priority_reason": prio_reason,
                "factcheck_report": _coerce_str(fc.get("report_file")).strip()
                or inputs.factcheck_report_path.name,
            }
        )

    # sort: high -> medium -> low, dann index
    prio_order = {"high": 0, "medium": 1, "low": 2}

    def _review_sort_key(d: Dict[str, Any]) -> Tuple[int, int]:
        prio = _coerce_str(d.get("priority")).strip()
        prio_rank = prio_order.get(prio, 9)
        idx_val = _safe_int(d.get("index"))
        if idx_val is None:
            idx_val = 10**9
        return prio_rank, idx_val

    review_items.sort(key=_review_sort_key)

    review_payload = {
        "zeitstempel": datetime.now().isoformat(),
        "quelle_enriched": inputs.enriched_path.name,
        "quelle_factcheck": inputs.factcheck_report_path.name,
        "gesamt": len(review_items),
        "counts_priority": dict(prio_counts),
        "counts_study_status": {
            "needs_review": sum(
                1 for x in review_items if x.get("study_status") == "needs_review"
            ),
            "needs_context": sum(
                1 for x in review_items if x.get("study_status") == "needs_context"
            ),
        },
        "items": review_items,
    }

    # Optional SRS review cards
    if args.write_srs_review:
        cards: List[Dict[str, Any]] = []
        for it in review_items:
            idx = int(it["index"])
            fach = _coerce_str(it.get("fachgebiet")).strip()
            verdict = _coerce_str(it.get("verdict")).strip().lower()
            status = _coerce_str(it.get("study_status")).strip().lower()

            tags = [
                _normalize_tag(
                    f"fachgebiet:{fach}" if fach else "fachgebiet:unbekannt"
                ),
                _normalize_tag("source:medexamenai"),
                _normalize_tag("review_needed"),
                _normalize_tag(f"verdict:{verdict}" if verdict else "verdict:unknown"),
                _normalize_tag(f"status:{status}" if status else "status:unknown"),
            ]
            tags = sorted([t for t in tags if t])

            # Antwort: Original + klarer Review-Block
            answer = _coerce_str(it.get("antwort")).strip()
            fc = {
                "verdict": it.get("verdict"),
                "issues": it.get("issues"),
                "suggested_sources": it.get("suggested_sources"),
            }
            hints = _review_hints_text(fc)
            merged_answer = answer
            if hints:
                merged_answer = f"{answer}\n\n---\n{hints}"

            cards.append(
                {
                    "id": f"evidenz_{idx}",
                    "question": _coerce_str(it.get("frage")).strip(),
                    "answer": merged_answer,
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

        srs_payload = {
            "timestamp": datetime.now().isoformat(),
            "source": inputs.enriched_path.name,
            "total_cards": len(cards),
            "cards": cards,
        }
        _write_json(out_srs_review, srs_payload)

    # Write fixed enriched (gleiche Top-Level-Struktur wie Input)
    if top_kind == "list":
        fixed_payload: Any = items
    else:
        fixed_payload = dict(meta)
        # optionale Meta-Stats (hilfreich, aber klein)
        fixed_payload["fixed_at"] = datetime.now().isoformat()
        fixed_payload["fixed_from"] = inputs.enriched_path.name
        fixed_payload["counts_after"] = {
            "meaningful_total": meaningful_total,
            "meaningful_status": dict(meaningful_status_counts),
        }
        fixed_payload["items"] = items

    _write_json(out_fixed, fixed_payload)
    _write_json(out_review_queue, review_payload)

    # Ausgabe (Deutsch, keine Secrets)
    print("Backfill/Fix abgeschlossen.")
    print(f"Input enriched: {inputs.enriched_path.name}")
    print(f"Input Factcheck: {inputs.factcheck_report_path.name}")
    print(f"Meaningful total: {meaningful_total}")
    print(
        "Meaningful ohne/unklares Factcheck vorher: "
        f"{meaningful_missing_fc_before} "
        f"(unknown-status vorher: {meaningful_unknown_status_before})"
    )
    print(
        "Backfilled (FC geändert/gesetzt): "
        f"{fc_changed_total} "
        f"(via index: {backfilled_by_index}, via frage: {backfilled_by_question})"
    )
    print(
        f"Meaningful ohne Factcheck nachher: {meaningful_missing_fc_after} "
        f"(unknown verdict nachher: {meaningful_unknown_verdict_after})"
    )
    print(
        "Mismatches Inventory vs Verdict: "
        f"problem={mismatches_problem}, maybe={mismatches_maybe}"
    )
    print(f"Fixed enriched: {out_fixed}")
    print(f"Review queue: {out_review_queue} (items: {len(review_items)})")
    if args.write_srs_review:
        print(f"SRS review cards: {out_srs_review} (cards: {len(review_items)})")

    print("Meaningful study_status (nach Fix): " f"{dict(meaningful_status_counts)}")

    # Top 10 High-Priority
    top_high = [x for x in review_items if x.get("priority") == "high"]
    top_list = top_high[:10] if len(top_high) >= 10 else review_items[:10]

    def _short(s: str, n: int = 120) -> str:
        ss = " ".join((s or "").strip().split())
        return ss if len(ss) <= n else ss[: n - 1] + "…"

    print("Top 10 (nach Priorität):")
    for it in top_list:
        idx_val = _safe_int(it.get("index"))
        why = it.get("priority_reason")
        frage = _short(_coerce_str(it.get("frage")))
        print(f"- #{idx_val}: {frage} (Prio={it.get('priority')}; {why})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())




