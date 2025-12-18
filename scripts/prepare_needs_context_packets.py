#!/usr/bin/env python3
"""Bereitet `needs_context`-Items für schnellen Review-Workflow auf.

Ziel
- Fokus ausschließlich auf `needs_context` (Kontext fehlt / Maybe).
- Kontext wird aus dem Goldstandard-Extrakt `_OUTPUT/fragen_mit_kontext.json`
  gezogen (inkl. `source_file`, `source_page`, Kontextblock).
- Es werden keine kanonischen Dateien überschrieben, insbesondere NICHT:
  `_OUTPUT/evidenz_antworten.json`.
- Keine inhaltliche Umschreibung von Antworten: Original-Antwort bleibt
  unverändert.

Outputs (immer neu, Timestamp)
1) `_OUTPUT/needs_context_prepared_<TS>.json`
   - nur sichere Matches (Kontext eindeutig gefunden)
   - enthält pro Item: index, frage_original, frage_mit_kontext, source_file,
     source_path, source_page, context_lines, match_method, confidence +
     Review-Felder (Antwort/Issues)
   - enthält zusätzlich `validation_md_stub`
     (Template-Skelett nach Agent-Briefing)
2) `_OUTPUT/needs_context_external_validation_<TS>.md`
   - Items, bei denen kein sicherer Kontext-Match möglich war
     (oder Quelle unklar)
   - für manuelle/externe Validierung

Hinweis
- Matching primär innerhalb derselben `source_file`.
- Fallback auf normalisierten Dateinamen nur, wenn eindeutig (sonst: als
  "offen" markieren).
- Fuzzy-Matching via Standardbibliothek `difflib`, aber konservativ: nur bei
  klaren Scores.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"
DEFAULT_GOLD_DIR = PROJECT_ROOT / "_GOLD_STANDARD"


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
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _unique_path(path: Path) -> Path:
    """Verhindert Überschreiben.

    Hängt _1, _2, ... an, falls Datei existiert.
    """
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    for i in range(1, 10_000):
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Konnte keinen freien Dateinamen finden für: {path}")


def _coerce_str(v: Any) -> str:
    return "" if v is None else str(v)


_LEADING_NOISE_RE = re.compile(
    r"^\s*(?:frage\s*:|f\s*:)?\s*",
    flags=re.IGNORECASE,
)
_LEADING_BULLETS_RE = re.compile(r"^\s*[-•*]+\s*")
_LEADING_NUMBER_RE = re.compile(r"^\s*\d+\.\s*")
_MULTI_WS_RE = re.compile(r"\s+")


def _norm_text(s: str) -> str:
    """Unicode-normalisierte, whitespace-kollabierte Vergleichsform."""
    t = unicodedata.normalize("NFKC", s or "")
    t = t.replace("\u00ad", "")  # Soft hyphen
    t = t.strip()
    t = _LEADING_BULLETS_RE.sub("", t)
    t = _LEADING_NUMBER_RE.sub("", t)
    t = _LEADING_NOISE_RE.sub("", t)
    t = _MULTI_WS_RE.sub(" ", t)
    t = t.strip().strip(" ?!.;:").strip()
    return t.casefold()


def _norm_file_key(name: str) -> str:
    """Robuster Schlüssel für Dateinamen (nur für Fallback, wenn eindeutig)."""
    base = unicodedata.normalize("NFKC", Path(name).name)
    base = base.casefold()
    base = re.sub(r"\(\d+\)", "", base)  # (1), (2) etc.
    base = re.sub(r"\s+", "", base)
    base = base.replace("_", "").replace("-", "")
    return base


@dataclass(frozen=True)
class ContextCandidate:
    source_file: str
    source_page: Optional[int]
    context_lines: List[str]
    block_id: str
    original: str
    reconstructed: str
    norm_original: str
    norm_reconstructed: str


def _safe_int(v: Any) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


def _load_context_index(
    context_json_path: Path,
) -> Dict[str, List[ContextCandidate]]:
    payload = _read_json(context_json_path)
    if not isinstance(payload, list):
        raise ValueError("fragen_mit_kontext.json muss eine Liste sein")

    index: Dict[str, List[ContextCandidate]] = {}
    for block in payload:
        if not isinstance(block, dict):
            continue
        source_file = _coerce_str(block.get("source_file")).strip()
        if not source_file:
            continue
        source_page = _safe_int(block.get("source_page"))
        block_id = _coerce_str(block.get("block_id")).strip()
        context = block.get("context")
        context_lines = []
        if isinstance(context, list):
            context_lines = [str(x) for x in context if str(x).strip()]

        questions = block.get("questions")
        if not isinstance(questions, list):
            continue
        for q in questions:
            if not isinstance(q, dict):
                continue
            original = _coerce_str(q.get("original")).strip()
            reconstructed = _coerce_str(q.get("reconstructed")).strip()
            if not original and not reconstructed:
                continue
            cand = ContextCandidate(
                source_file=source_file,
                source_page=source_page,
                context_lines=context_lines,
                block_id=block_id,
                original=original,
                reconstructed=reconstructed or original,
                norm_original=_norm_text(original),
                norm_reconstructed=_norm_text(reconstructed or original),
            )
            index.setdefault(source_file, []).append(cand)
    return index


def _pick_latest_review_queue(output_dir: Path) -> Path:
    candidates = sorted(
        output_dir.glob("review_queue_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError("Keine review_queue_*.json in _OUTPUT gefunden")
    return candidates[0]


def _threshold_for(q_norm: str) -> float:
    n = len(q_norm)
    if n < 20:
        return 1.0  # nur exakt
    if n < 50:
        return 0.95
    if n < 120:
        return 0.92
    return 0.90


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _best_match(
    q_norm: str,
    candidates: List[ContextCandidate],
) -> Tuple[Optional[ContextCandidate], str, float, str]:
    """Findet besten Match. Returns (candidate|None, method, score, note)."""
    if not q_norm or not candidates:
        return None, "", 0.0, "keine_kandidaten"

    # 1) Exakte Matches (Original/Reconstructed)
    exact: List[Tuple[ContextCandidate, str]] = []
    for c in candidates:
        if q_norm and q_norm == c.norm_original and c.norm_original:
            exact.append((c, "exact_original"))
        elif q_norm and q_norm == c.norm_reconstructed and c.norm_reconstructed:
            exact.append((c, "exact_reconstructed"))
    if exact:
        # deterministisch: Seite, dann block_id, dann längere reconstructed
        exact_sorted = sorted(
            exact,
            key=lambda t: (
                t[0].source_page if t[0].source_page is not None else 10**9,
                t[0].block_id,
                -len(t[0].reconstructed),
            ),
        )
        best, method = exact_sorted[0]
        note = "mehrfach_exakt" if len(exact_sorted) > 1 else ""
        return best, method, 1.0, note

    # 2) Konservatives Fuzzy-Matching
    thresh = _threshold_for(q_norm)
    if thresh >= 1.0:
        return None, "", 0.0, "zu_kurz_fuer_fuzzy"

    scored: List[Tuple[float, float, ContextCandidate, str]] = []
    for c in candidates:
        s1 = _similarity(q_norm, c.norm_original)
        s2 = _similarity(q_norm, c.norm_reconstructed)
        if s1 >= s2:
            scored.append((s1, s2, c, "fuzzy_original"))
        else:
            scored.append((s2, s1, c, "fuzzy_reconstructed"))

    scored.sort(
        key=lambda t: (
            -t[0],
            t[2].source_page if t[2].source_page is not None else 10**9,
            t[2].block_id,
        )
    )
    best_score, _alt, best, method = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if best_score < thresh:
        return None, "", best_score, f"unter_schwelle_{thresh:.2f}"

    # Ambiguität: wenn 2. fast gleich gut ist -> nicht auto-matchen
    if len(scored) > 1 and (best_score - second_score) < 0.02:
        return None, "", best_score, "mehrdeutig_fuzzy"

    return best, method, float(best_score), ""


def _guess_question_type(frage: str) -> str:
    """Grobe Heuristik gemäß Briefing (nur als Vorschlag)."""
    f = (frage or "").casefold()
    if any(
        k in f
        for k in [
            "§",
            "gesetz",
            "bgb",
            "stgb",
            "sgb",
            "pflicht",
            "meld",
            "btmg",
        ]
    ):
        return "Rechtlich"
    if any(k in f for k in ["ethik", "autonomie", "moral", "prinzip", "würde"]):
        return "Ethisch"
    if any(
        k in f
        for k in [
            "institution",
            "zuständig",
            "verfahren",
            "behörde",
            "wer trägt",
        ]
    ):
        return "Administrativ"
    if any(
        k in f
        for k in [
            "diagnose",
            "therapie",
            "behandlung",
            "dosis",
            "mg",
            "i.v",
            "p.o",
            "symptom",
        ]
    ):
        return "Klinisch"
    return "Faktisch"


def _validation_md_stub(
    *,
    index: int,
    frage_mit_kontext: str,
    source_file: str,
    source_page: Optional[int],
    source_path: str,
    antwort: str,
    issues_compact: str,
    question_type_guess: str,
) -> str:
    page_part = f", Seite {source_page}" if source_page is not None else ""
    q = frage_mit_kontext.strip() or "TODO: Frage"
    problem = issues_compact or "Kontext fehlt / unklar"
    return "\n".join(
        [
            f"## {index}. {q}",
            "",
            f"**Quelldatei:** (Goldstandard) {source_file}{page_part}",
            f"**Quelle (Pfad):** `{source_path}`",
            f"**Fragetyp (Vorschlag):** {question_type_guess}",
            "",
            "---",
            "",
            "### Original-Antwort",
            antwort.strip(),
            "",
            "**Original-Konfidenz:** n/a",
            f"**Original-Problem:** needs_context – {problem}",
            "",
            "---",
            "",
            "### Verifizierte Antwort",
            "",
            "[HIER das passende Format je Fragetyp einfügen – "
            "keine Halluzinationen, nur belegte Aussagen.]",
            "",
            "---",
            "",
            "### Prüfungsrelevante Kernpunkte",
            "- ✅ [Kernpunkt 1] → Quelle [1]",
            "- ✅ [Kernpunkt 2] → Quelle [2]",
            "- ✅ [Kernpunkt 3] → Quelle [1]",
            "",
            "---",
            "",
            "### Verwendete Quellen",
            "",
            "| Nr | Typ | Quelle | Zugriff |",
            "|----|-----|--------|---------|",
            "| [1] | Leitlinie | AWMF Reg.-Nr. XXX-XXX | awmf.org |",
            "| [2] | Fachinfo | Wirkstoff Fachinformation | fachinfo.de |",
            "| [3] | Institution | RKI - Thema | rki.de |",
            "",
            "---",
            "",
            "### Konfidenz-Analyse",
            "",
            "| Kriterium | Original | Verifiziert | Methode |",
            "|-----------|----------|-------------|---------|",
            "| Faktische Richtigkeit | n/a | ✅ Y% | RAG/Extern |",
            "| Quellenbeleg | n/a | ✅ Y% | Leitlinie |",
            "| Vollständigkeit | n/a | ✅ Y% | Format-Check |",
            "| **FINAL** | n/a | ✅ Y% | Dual-Source |",
            "",
            "---",
            "",
        ]
    )


def _find_source_path_rel(
    filename: str,
    gold_dir: Path,
    extra_roots: List[Path],
) -> str:
    """Gibt einen relativen Pfad (vom Repo-Root) zurück."""
    filename_clean = Path(filename).name
    p = gold_dir / filename_clean
    if p.exists():
        return str(p.relative_to(PROJECT_ROOT))

    # Fallback: gezielte Suche nur, wenn nicht im Gold-Dir
    for root in extra_roots:
        try:
            matches = list(root.rglob(filename_clean))
        except Exception:
            matches = []
        if matches:
            # deterministisch: kürzester Pfad
            best = sorted(matches, key=lambda x: (len(str(x)), str(x)))[0]
            try:
                return str(best.relative_to(PROJECT_ROOT))
            except Exception:
                return str(best)
    return ""


def _issue_hint(issues_compact: str, frage: str) -> str:
    t = (issues_compact or "").casefold()
    f = (frage or "").casefold()
    if (
        any(k in t for k in ["fehlendes bild", "bild", "symbol", "gezeigt"])
        or "bild" in f
    ):
        return (
            "Vermutlich fehlt ein Bild/Symbol/Tafel. "
            "Bitte im Goldstandard mit Bildkontext suchen."
        )
    if any(k in t for k in ["falldarstellung", "fall", "kontext"]) or any(
        k in f for k in ["dieser", "hier", "was noch"]
    ):
        return (
            "Vermutlich fehlt Fallvignette/Bezug. "
            "Bitte im Goldstandard an der Dialogstelle nachsehen."
        )
    return (
        "Kontext/Bezug unklar – bitte im Goldstandard nach der Dialogstelle " "suchen."
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Bereitet needs_context Items mit Goldstandard-Kontext auf "
            "(JSON + MD, ohne Rewrites)."
        )
    )
    parser.add_argument(
        "--review-queue",
        default="",
        help="Pfad zu review_queue_*.json (Default: neueste in _OUTPUT)",
    )
    parser.add_argument(
        "--context-json",
        default=str(DEFAULT_OUTPUT_DIR / "fragen_mit_kontext.json"),
        help="Pfad zu fragen_mit_kontext.json",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output-Verzeichnis (default: _OUTPUT)",
    )
    parser.add_argument(
        "--gold-dir",
        default=str(DEFAULT_GOLD_DIR),
        help="Goldstandard-Verzeichnis (default: _GOLD_STANDARD)",
    )
    parser.add_argument(
        "--extra-roots",
        default="",
        help=("Zusätzliche Suchwurzeln für source_file " "(CSV, getrennt durch Komma)"),
    )

    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.review_queue:
        review_queue_path = Path(args.review_queue)
    else:
        review_queue_path = _pick_latest_review_queue(out_dir)
    context_json_path = Path(args.context_json)
    gold_dir = Path(args.gold_dir)

    if not review_queue_path.exists():
        raise SystemExit(f"Input nicht gefunden: {review_queue_path}")
    if not context_json_path.exists():
        raise SystemExit(f"Input nicht gefunden: {context_json_path}")

    extra_roots: List[Path] = []
    if args.extra_roots.strip():
        extra_roots = [
            Path(x.strip()) for x in args.extra_roots.split(",") if x.strip()
        ]
    else:
        extra_roots = [
            PROJECT_ROOT / "_FACT_CHECK_SOURCES",
            PROJECT_ROOT / "_DOCS",
        ]

    ts = _now_ts()
    out_prepared = _unique_path(out_dir / f"needs_context_prepared_{ts}.json")
    out_external_md = _unique_path(
        out_dir / f"needs_context_external_validation_{ts}.md"
    )

    rq = _read_json(review_queue_path)
    if not isinstance(rq, dict) or not isinstance(rq.get("items"), list):
        raise ValueError("review_queue JSON muss ein Objekt mit `items: [...]` sein")

    context_index = _load_context_index(context_json_path)
    context_sources = set(context_index.keys())
    context_sources_norm_map: Dict[str, List[str]] = {}
    for s in context_sources:
        context_sources_norm_map.setdefault(_norm_file_key(s), []).append(s)

    needs_context_items = []
    for it in rq["items"]:
        if not isinstance(it, dict):
            continue
        if _coerce_str(it.get("study_status")).strip() != "needs_context":
            continue
        needs_context_items.append(it)

    matched: List[Dict[str, Any]] = []
    unmatched: List[Dict[str, Any]] = []

    for it in needs_context_items:
        idx_raw = _safe_int(it.get("index"))
        if idx_raw is None:
            continue
        idx = idx_raw
        frage_original = _coerce_str(it.get("frage")).strip()
        q_norm = _norm_text(frage_original)
        source_file = _coerce_str(it.get("source_file")).strip()

        # Kandidaten nach source_file
        candidates = context_index.get(source_file, [])
        source_match_note = ""

        if not candidates and source_file:
            # Fallback: normalisierter Dateiname, aber nur wenn eindeutig
            key = _norm_file_key(source_file)
            mapped = context_sources_norm_map.get(key, [])
            if len(mapped) == 1:
                candidates = context_index.get(mapped[0], [])
                source_match_note = f"source_file_fallback:{mapped[0]}"
            elif len(mapped) > 1:
                source_match_note = "source_file_fallback_ambiguous"

        best, method, score, note = _best_match(q_norm, candidates)

        issues_compact = _coerce_str(it.get("issues_compact")).strip()
        if not issues_compact:
            issues_compact = "Kontext fehlt (needs_context)"

        if best is None or not method:
            unmatched.append(
                {
                    "index": idx,
                    "frage": frage_original,
                    "fachgebiet": _coerce_str(it.get("fachgebiet")).strip(),
                    "source_file": source_file,
                    "antwort": _coerce_str(it.get("antwort")).strip(),
                    "issues_compact": issues_compact,
                    "hint": _issue_hint(issues_compact, frage_original),
                    "match_note": note or source_match_note or "kein_match",
                }
            )
            continue

        source_path = _find_source_path_rel(
            best.source_file,
            gold_dir,
            extra_roots,
        )
        question_type_guess = _guess_question_type(best.reconstructed or frage_original)
        md_stub = _validation_md_stub(
            index=idx,
            frage_mit_kontext=best.reconstructed or frage_original,
            source_file=best.source_file,
            source_page=best.source_page,
            source_path=source_path or best.source_file,
            antwort=_coerce_str(it.get("antwort")).strip(),
            issues_compact=issues_compact,
            question_type_guess=question_type_guess,
        )

        matched.append(
            {
                "index": idx,
                "frage_original": frage_original,
                "frage_mit_kontext": best.reconstructed or frage_original,
                "fachgebiet": _coerce_str(it.get("fachgebiet")).strip(),
                "source_file": best.source_file,
                "source_path": source_path,
                "source_page": best.source_page,
                "context_lines": best.context_lines,
                "match_method": method,
                "confidence": score,
                "match_note": " | ".join([x for x in [note, source_match_note] if x]),
                "review_queue_fields": {
                    "study_status": _coerce_str(it.get("study_status")).strip(),
                    "study_exclude_reason": _coerce_str(
                        it.get("study_exclude_reason")
                    ).strip(),
                    "verdict": _coerce_str(it.get("verdict")).strip(),
                    "issues_compact": issues_compact,
                    "issues": it.get("issues", []),
                    "suggested_sources": it.get("suggested_sources", []),
                    "optional_fix_snippet": _coerce_str(
                        it.get("optional_fix_snippet")
                    ).strip(),
                    "antwort": _coerce_str(it.get("antwort")).strip(),
                },
                "fragetyp_vorschlag": question_type_guess,
                "validation_md_stub": md_stub,
            }
        )

    # Output JSON (nur Matches)
    prepared_payload = {
        "zeitstempel": datetime.now().isoformat(),
        "quelle_review_queue": review_queue_path.name,
        "quelle_kontext": context_json_path.name,
        "counts": {
            "needs_context_total": len(needs_context_items),
            "matched": len(matched),
            "unmatched": len(unmatched),
        },
        "items": matched,
    }
    _write_json(out_prepared, prepared_payload)

    # Output MD (Unmatched)
    lines: List[str] = []
    lines.append(f"# needs_context – externe Validierung ({ts})")
    lines.append("")
    lines.append(f"Quelle Review-Queue: `{review_queue_path.name}`")
    lines.append(f"Quelle Kontext-Extrakt: `{context_json_path.name}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- needs_context gesamt: **{len(needs_context_items)}**")
    lines.append(f"- Kontext automatisch gefunden (sicher): **{len(matched)}**")
    lines.append(f"- Offen für manuelle Suche/Validierung: **{len(unmatched)}**")
    lines.append("")
    lines.append("Hinweis: Diese Liste enthält nur Items ohne sicheren Kontext-Match.")
    lines.append("")

    # Gruppieren nach source_file
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for it in unmatched:
        key = _coerce_str(it.get("source_file")).strip() or "unbekannt"
        by_source.setdefault(key, []).append(it)

    for src in sorted(by_source.keys()):
        group = sorted(
            by_source[src],
            key=lambda d: int(d.get("index") or 10**9),
        )
        if src != "unbekannt":
            src_path = _find_source_path_rel(src, gold_dir, extra_roots)
        else:
            src_path = ""
        lines.append(f"## Quelle: {src}")
        if src_path:
            lines.append(f"- Pfad: `{src_path}`")
        lines.append("")
        for it in group:
            idx2 = int(it.get("index") or 10**9)
            frage = _coerce_str(it.get("frage")).strip()
            antwort = _coerce_str(it.get("antwort")).strip()
            issues_c = _coerce_str(it.get("issues_compact")).strip()
            hint = _coerce_str(it.get("hint")).strip()
            note = _coerce_str(it.get("match_note")).strip()
            lines.append(f"### #{idx2}: {frage}")
            lines.append("")
            lines.append(f"- **Warum needs_context:** {issues_c}")
            if hint:
                lines.append(f"- **Hinweis:** {hint}")
            if note:
                lines.append(f"- **Match-Notiz:** {note}")
            lines.append("")
            lines.append("**Original-Antwort (unverändert):**")
            lines.append("")
            lines.append("```")
            lines.append(antwort)
            lines.append("```")
            lines.append("")

    _write_text(out_external_md, "\n".join(lines))

    # Logs (Deutsch)
    print("needs_context Aufbereitung abgeschlossen.")
    print(f"Input review_queue: {review_queue_path}")
    print(f"Input kontext: {context_json_path}")
    print(f"needs_context total: {len(needs_context_items)}")
    print(f"matched: {len(matched)}")
    print(f"unmatched: {len(unmatched)}")
    print(f"Output prepared JSON: {out_prepared}")
    print(f"Output external MD: {out_external_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
