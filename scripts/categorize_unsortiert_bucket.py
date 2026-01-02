#!/usr/bin/env python3
"""
Kategorisiert Dateien aus `_FACT_CHECK_SOURCES/_unsortiert/` in 3 Bucket-Typen:
1) Prüfungsprotokolle/Prüfungsmaterial → `_GOLD_STANDARD/unsortiert_protokolle/`
2) Fakten/medizinisches Wissen         → `_FACT_CHECK_SOURCES/unsortiert_kategorisiert/`
3) Sprachlich/Admin                    → `_FACT_CHECK_SOURCES/unsortiert_sprachlich/`

Erstellt immer einen JSON-Report in `_AGENT_WORK/`.
Optional (`--apply`) werden Dateien verschoben (default: dry-run).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:  # Optional: reuse existing broad categorizer to reduce UNSICHER
    from scripts.sort_fact_check_sources import categorize_file as _categorize_fact_check_file  # type: ignore
except Exception:  # pragma: no cover
    _categorize_fact_check_file = None


PROTOKOLLE_KEYWORDS = [
    # Reports / Protokolle / Exam prep
    "kenntnisprüfung",
    "kenntnispruefung",
    "prüfung",
    "pruefung",
    "protokoll",
    "protokolle",
    "kp ",
    "kp_",
    "kenntnis",
    "fachsprachprüfung",
    "fachsprachpruefung",
    "fsp",
    "approbation",
    "gleichwertigkeitsprüfung",
    "gleichwertigkeitspruefung",
    "simulation",
    "prüfungsvorbereitung",
    "pruefungsvorbereitung",
    # Typical exam artefacts
    "anamnese",
    "arztbrief",
    "dokumentation",
    "doku",
    "epikrise",
    "aufklärung",
    "aufklaerung",
    "patientenvorstellung",
    "arzt-arzt",
    "arzt arzt",
    "gespräch",
    "gespraech",
    "sätze",
    "saetze",
    "bewertungsbogen",
    "aufklärungsbogen",
    "aufklaerungsbogen",
    "aufklärungsbögen",
    "aufklaerungsboegen",
    "übung",
    "uebung",
    "fälle",
    "faelle",
    "prüfungsfall",
    "pruefungsfall",
    # Cities/regions often in filenames
    "münster",
    "muenster",
    "düsseldorf",
    "duesseldorf",
]

FAKTEN_KEYWORDS = [
    # Guidelines / evidence
    "leitlinie",
    "leitlinien",
    "awmf",
    "nvl",
    "guideline",
    "s1",
    "s2",
    "s3",
    # Clinical knowledge / topics
    "anatomie",
    "physiologie",
    "pathologie",
    "pharm",
    "pharmakologie",
    "notfall",
    "labor",
    "ekg",
    "ecg",
    "mrt",
    "röntgen",
    "roentgen",
    "ct",
    "sono",
    "sonographie",
    "ultraschall",
    "antibio",
    "antibiotik",
    "therapie",
    "diagnostik",
    "sepsis",
    "reanimation",
    # Common “knowledge base” docs in this project
    "themen",
    "fallkonzepte",
    "kompendium",
    "rechtsmedizin",
    "strahlenschutz",
    "begleitsymptom",
    "symptom",
    "beipackzettel",
    "darreichungsform",
    "schraube",
    "zugschraube",
    "osteoporose",
    "klinische",
    "notfälle",
    "notfaelle",
    "griffbereit",
    "chirurgie",
    "techniken",
]

SPRACHLICH_KEYWORDS = [
    "konjunktion",
    "konjunktionen",
    "präfix",
    "praefix",
    "nominalisierung",
    "grammatik",
    "deutsch",
    "verben",
    "verb",
    "artikel",
    "adjektiv",
    "lückentext",
    "lueckentext",
    "übersetzung",
    "uebersetzung",
    "anmeldung",
    "antrag",
    "formular",
    "bewerbung",
    "azav",
    "abkürzung",
    "abkuerzung",
    "begriffe",
    "gesundheitswesen",
    "sgb",
    "bgb",
    "stgb",
    "auszug",
]

# AWMF-style pattern like 003-001l_... (underscore is common)
AWMF_PATTERN = re.compile(r"(?:^|[^0-9A-Za-z])(\d{3}-\d{3}[a-z]?)(?=$|[^0-9A-Za-z])", re.IGNORECASE)
# DOS 8.3 filenames like 1SSILB~1.PDF or with added duplicate suffixes like 1SSILB~1_1.PDF
DOS_83_PATTERN = re.compile(r"^[0-9A-Z]{1,8}~[0-9]+(?:_[0-9]+)*(\..+)?$", re.IGNORECASE)


@dataclass(frozen=True)
class CategorizedFile:
    path: Path
    category: str
    reason: str
    size: int


def _casefold(s: str) -> str:
    # macOS filenames are often NFD (decomposed). Normalize to improve keyword matching.
    return unicodedata.normalize("NFKC", (s or "")).casefold()


def _strip_dupe_suffix(stem: str) -> str:
    """
    Normalisiert häufige Duplikat-Suffixe:
    - `_1`, `_2`, `_1_1`, ...
    - ` 2` (space-number)
    """
    s = stem
    s = re.sub(r"(?:_\d+)+$", "", s)
    s = re.sub(r"\s+\d+$", "", s)
    return s.strip()


def _first_page_text(pdf_path: Path, max_chars: int = 1200) -> str:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return ""
        txt = (reader.pages[0].extract_text() or "").strip()
        if len(txt) > max_chars:
            return txt[:max_chars]
        return txt
    except Exception:
        return ""


def categorize_path(path: Path, enable_content_fallback: bool = True) -> Tuple[str, str]:
    """
    Returns: (category, reason)
      category ∈ {"PROTOKOLLE","FAKTEN","SPRACHLICH","UNSICHER"}
    """
    name = path.name
    lower = _casefold(name)

    # JSON artefacts in this bucket are often question exports or knowledge blobs
    if path.suffix.lower() == ".json":
        if "kompendium" in lower:
            return "FAKTEN", "json:kompendium"
        if any(k in lower for k in ["protokoll", "fragen", "extrahierte", "telegram"]):
            return "PROTOKOLLE", "json:fragen/protokoll"
        return "UNSICHER", "json:unknown"

    # Filename patterns (fast)
    if AWMF_PATTERN.search(lower):
        return "FAKTEN", "filename:awmf_pattern"

    if DOS_83_PATTERN.match(name):
        # Usually Sprachkurs/grammatik scans; confirm via first-page text if possible.
        if enable_content_fallback and path.suffix.lower() == ".pdf":
            txt = _casefold(_first_page_text(path))
            if any(k in txt for k in ["konjunktion", "nominalisierung", "präfix", "praefix", "grammatik", "verb"]):
                return "SPRACHLICH", "content:sprachkurs_terms"
        return "SPRACHLICH", "filename:dos83"

    # Keyword routing (filename)
    for kw in PROTOKOLLE_KEYWORDS:
        if _casefold(kw) in lower:
            # Some keywords are ambiguous and better treated as knowledge base.
            if any(k in lower for k in ["themen", "fallkonzepte"]):
                return "FAKTEN", f"filename:kb_override({kw})"
            return "PROTOKOLLE", f"filename:keyword({kw})"

    for kw in SPRACHLICH_KEYWORDS:
        if _casefold(kw) in lower:
            return "SPRACHLICH", f"filename:keyword({kw})"

    for kw in FAKTEN_KEYWORDS:
        if _casefold(kw) in lower:
            return "FAKTEN", f"filename:keyword({kw})"

    # Reuse existing (broader) categorizer if available: map → 3 buckets.
    if _categorize_fact_check_file is not None:
        try:
            mapped = _categorize_fact_check_file(path)
        except Exception:
            mapped = None
        if mapped and mapped not in {"_unsortiert", "_skip"}:
            if mapped == "pruefungsprotokolle":
                return "PROTOKOLLE", f"sort_fact_check_sources:{mapped}"
            if mapped in {"sprachkurs", "kenntnispruefung_admin"}:
                return "SPRACHLICH", f"sort_fact_check_sources:{mapped}"
            return "FAKTEN", f"sort_fact_check_sources:{mapped}"

    # Content fallback for unknown PDFs
    if enable_content_fallback and path.suffix.lower() == ".pdf":
        txt_raw = _first_page_text(path)
        txt = _casefold(txt_raw)

        if any(k in txt for k in ["awmf", "leitlinie", "s3", "nvl", "guideline"]):
            return "FAKTEN", "content:guideline_terms"
        exam_strong = ["protokoll", "kenntnisprüfung", "kenntnispruefung", "prüfer", "pruefer", "teil 1", "teil 2", "teil1", "teil2", "fachsprachprüfung", "fsp"]
        exam_soft = ["prüfung", "pruefung"]
        if any(k in txt for k in exam_strong) or ("ich" in txt and any(k in txt for k in exam_soft)):
            return "PROTOKOLLE", "content:exam_terms"
        if any(k in txt for k in ["konjunktion", "nominalisierung", "grammatik", "präfix", "praefix", "verben"]):
            return "SPRACHLICH", "content:sprachkurs_terms"

    return "UNSICHER", "no_match"


def _safe_move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if not dst.exists():
        shutil.move(str(src), str(dst))
        return dst

    stem = src.stem
    suffix = src.suffix
    i = 1
    while True:
        cand = dst_dir / f"{stem}__dup{i}{suffix}"
        if not cand.exists():
            shutil.move(str(src), str(cand))
            return cand
        i += 1


def _render_markdown_report(payload: Dict[str, Any], sample_limit: int = 25) -> str:
    def _fmt_bool(v: Any) -> str:
        return "ja" if bool(v) else "nein"

    def _sample_list(items: List[str]) -> str:
        head = items[:sample_limit]
        out = "\n".join(f"- {x}" for x in head)
        if len(items) > sample_limit:
            out += f"\n... und {len(items) - sample_limit} weitere"
        return out or "- (leer)"

    generated_at = str(payload.get("generated_at", ""))
    source_dir = str(payload.get("source_dir", ""))
    mode = str(payload.get("mode", ""))
    content_fallback = payload.get("content_fallback", False)
    counts: Dict[str, int] = payload.get("counts", {}) or {}
    categorized_files: Dict[str, List[str]] = payload.get("categorized_files", {}) or {}
    duplicates_by_basename: Dict[str, List[str]] = payload.get("duplicates_by_basename", {}) or {}
    moves: List[Dict[str, str]] = payload.get("moves", []) or []

    total_files = sum(int(v) for v in counts.values()) if counts else 0

    lines: List[str] = []
    lines.append("# Kategorisierungs-Report: `_FACT_CHECK_SOURCES/_unsortiert/`")
    lines.append("")
    lines.append("## Statistiken")
    lines.append(f"- Generated: {generated_at}")
    lines.append(f"- Quelle: `{source_dir}`")
    lines.append(f"- Mode: `{mode}`")
    lines.append(f"- Content-Fallback (PDF first-page): {_fmt_bool(content_fallback)}")
    lines.append(f"- Gesamtanzahl Dateien: {total_files}")
    lines.append(f"- Duplikat-Gruppen (basename): {len(duplicates_by_basename)}")
    if mode == "apply":
        lines.append(f"- Verschoben: {len(moves)}")
    lines.append("")

    lines.append("## Verteilung auf Kategorien")
    for k in ["PROTOKOLLE", "FAKTEN", "SPRACHLICH", "UNSICHER"]:
        if k in counts:
            lines.append(f"- {k}: {counts.get(k, 0)} Dateien")
    lines.append("")

    for k in ["PROTOKOLLE", "FAKTEN", "SPRACHLICH", "UNSICHER"]:
        items = sorted(categorized_files.get(k, []) or [])
        lines.append(f"## {k} ({len(items)} Dateien)")
        lines.append(_sample_list(items))
        lines.append("")

    if duplicates_by_basename:
        # Show a small sample of the largest groups.
        top = sorted(duplicates_by_basename.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:25]
        lines.append("## Duplikate (Beispiel)")
        for base, names in top:
            show = ", ".join(sorted(names)[:10])
            suffix = f", ... (+{len(names) - 10})" if len(names) > 10 else ""
            lines.append(f"- `{base}`: {show}{suffix}")
        lines.append("")

    lines.append("## Nächste Schritte")
    lines.append("1. **UNSICHER** manuell sichten (insb. kryptische Dateinamen).")
    lines.append("2. Optional: echte Duplikate per Hash prüfen (basename-Gruppen sind nur Heuristik).")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Kategorisiert _FACT_CHECK_SOURCES/_unsortiert in 3 Buckets + Report")
    parser.add_argument(
        "--source-dir",
        default="_FACT_CHECK_SOURCES/_unsortiert",
        help="Quelle der unsortierten Dateien (default: _FACT_CHECK_SOURCES/_unsortiert)",
    )
    parser.add_argument(
        "--protokolle-dir",
        default="_GOLD_STANDARD/unsortiert_protokolle",
        help="Zielordner für Prüfungsprotokolle (default: _GOLD_STANDARD/unsortiert_protokolle)",
    )
    parser.add_argument(
        "--fakten-dir",
        default="_FACT_CHECK_SOURCES/unsortiert_kategorisiert",
        help="Zielordner für Fakten (default: _FACT_CHECK_SOURCES/unsortiert_kategorisiert)",
    )
    parser.add_argument(
        "--sprachlich-dir",
        default="_FACT_CHECK_SOURCES/unsortiert_sprachlich",
        help="Zielordner für sprachliche/admin Dateien (default: _FACT_CHECK_SOURCES/unsortiert_sprachlich)",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Pfad für JSON-Report (default: _AGENT_WORK/unsortiert_kategorisierung_report_<TS>.json)",
    )
    parser.add_argument(
        "--report-md",
        default="",
        help="Pfad für Markdown-Report (default: same as --report but .md)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Dateien verschieben (default: dry-run)",
    )
    parser.add_argument(
        "--no-content-fallback",
        action="store_true",
        help="Nur anhand Dateiname klassifizieren (schneller, aber mehr UNSICHER)",
    )
    args = parser.parse_args()

    source_dir = PROJECT_ROOT / args.source_dir
    if not source_dir.exists():
        raise SystemExit(f"Source dir not found: {source_dir}")

    protokolle_dir = PROJECT_ROOT / args.protokolle_dir
    fakten_dir = PROJECT_ROOT / args.fakten_dir
    sprach_dir = PROJECT_ROOT / args.sprachlich_dir

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(args.report) if args.report else PROJECT_ROOT / "_AGENT_WORK" / f"unsortiert_kategorisierung_report_{ts}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    enable_content_fallback = not bool(args.no_content_fallback)

    files = [p for p in sorted(source_dir.iterdir()) if p.is_file()]

    categorized: List[CategorizedFile] = []
    duplicates_by_basename: Dict[str, List[str]] = {}
    by_category: Dict[str, List[str]] = {k: [] for k in ["PROTOKOLLE", "FAKTEN", "SPRACHLICH", "UNSICHER"]}

    for p in files:
        cat, reason = categorize_path(p, enable_content_fallback=enable_content_fallback)
        categorized.append(
            CategorizedFile(path=p, category=cat, reason=reason, size=p.stat().st_size)
        )
        by_category[cat].append(p.name)
        base = _strip_dupe_suffix(p.stem)
        duplicates_by_basename.setdefault(base, []).append(p.name)

    duplicates_by_basename = {k: v for k, v in duplicates_by_basename.items() if len(v) > 1}

    counts: Dict[str, int] = {}
    for cf in categorized:
        counts[cf.category] = counts.get(cf.category, 0) + 1

    moves: List[Dict[str, str]] = []
    if args.apply:
        for cf in categorized:
            if cf.category == "PROTOKOLLE":
                dst = _safe_move(cf.path, protokolle_dir)
                moves.append({"src": str(cf.path), "dst": str(dst), "category": cf.category})
            elif cf.category == "FAKTEN":
                dst = _safe_move(cf.path, fakten_dir)
                moves.append({"src": str(cf.path), "dst": str(dst), "category": cf.category})
            elif cf.category == "SPRACHLICH":
                dst = _safe_move(cf.path, sprach_dir)
                moves.append({"src": str(cf.path), "dst": str(dst), "category": cf.category})
            else:
                # UNSICHER stays in place for manual triage
                continue

    payload: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_dir": str(source_dir),
        "targets": {
            "PROTOKOLLE": str(protokolle_dir),
            "FAKTEN": str(fakten_dir),
            "SPRACHLICH": str(sprach_dir),
        },
        "mode": "apply" if args.apply else "dry_run",
        "content_fallback": enable_content_fallback,
        "counts": counts,
        "categorized_files": {k: sorted(v) for k, v in by_category.items()},
        "files": [
            {
                "name": cf.path.name,
                "size": cf.size,
                "category": cf.category,
                "reason": cf.reason,
            }
            for cf in categorized
        ],
        "duplicates_by_basename": duplicates_by_basename,
        "moves": moves,
    }

    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = Path(args.report_md) if args.report_md else None
    if md_path is None and report_path.suffix.lower() == ".json":
        md_path = report_path.with_suffix(".md")
    if md_path is not None:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(_render_markdown_report(payload), encoding="utf-8")

    # Console summary
    print("=" * 70)
    print("UNSORTIERT KATEGORISIERUNG")
    print("=" * 70)
    print(f"Quelle: {source_dir}")
    print(f"Mode: {'APPLY (move)' if args.apply else 'DRY-RUN'}")
    print(f"Content fallback: {enable_content_fallback}")
    print()
    for k in sorted(counts.keys()):
        print(f"  {k}: {counts[k]}")
    print()
    print(f"Report: {report_path}")
    if md_path is not None:
        print(f"Report (MD): {md_path}")
    print(f"Duplikat-Gruppen (basename): {len(duplicates_by_basename)}")
    if args.apply:
        print(f"Moved: {len(moves)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
