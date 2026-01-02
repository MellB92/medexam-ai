#!/usr/bin/env python3
"""
Aufgabe 2 (v2): Strengeres Matching zwischen Münster-Relevanz und Anki-Tags.

Ziel:
- Lieber *weniger* Tags mit hoher Relevanz als "zu viel".
- Keine breiten/fuzzy Matches wie in v1 (nur high-confidence).
- Meta-Tags (z_Credit, !Delete, etc.) werden ausgeschlossen.

Inputs:
- `_OUTPUT/muenster_relevanz_master.json`
- `_OUTPUT/ankizin_alle_tags.json`
- `_OUTPUT/dellas_alle_tags.json`

Outputs:
- `_OUTPUT/ankizin_matched_tags_v2.json`
- `_OUTPUT/dellas_matched_tags_v2.json`
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


META_TAG_PATTERNS = [
    r"::z_credit::",
    r"::!delete",
    r"::!missing",
    r"::!markiere",
    r"^!delete",
    r"^z_credit",
]

PRECLINICAL_HINTS = [
    "vorklinik",
    "biochemie",
    "physiologie",
    "anatomie",
    "histologie",
]

# v2: nur Querschnitt/Fachbereiche, die explizit im KP-Fokus sind (nicht "alles Klinik")
CROSSCUTTING_TERMS = {
    "strahlenschutz",
    "pharmakologie",
    "rechtsmedizin",
    "notfallmedizin",
    "hygiene",
    "arbeitsmedizin",
    "radiologie",
}


def normalize(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = s.replace("#", "")
    # keep :: for hierarchy
    s = re.sub(r"[^a-z0-9:_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def tag_parts(tag: str) -> list[str]:
    t = tag or ""
    parts = t.split("::") if "::" in t else [t]
    return [normalize(p) for p in parts if normalize(p)]


def is_meta_tag(tag: str) -> bool:
    t = normalize(tag)
    for p in META_TAG_PATTERNS:
        if re.search(p, t):
            return True
    return False


def is_preclinical(tag: str) -> bool:
    t = normalize(tag)
    return any(h in t for h in PRECLINICAL_HINTS)


@dataclass
class Match:
    tag: str
    score: float
    matched_term: str
    match_type: str


def best_match(tag: str, terms: list[str]) -> Optional[Match]:
    """
    High-confidence matching only:
    - exact part match: 1.0
    - substring in part: 0.95 (min token len)
    - substring in full tag: 0.9
    """
    t_norm = normalize(tag)
    parts = tag_parts(tag)
    best: Optional[Match] = None

    for term in terms:
        term_n = normalize(term)
        if not term_n or len(term_n) < 4:
            continue

        # 1) exact part match
        if term_n in parts:
            m = Match(tag=tag, score=1.0, matched_term=term, match_type="part_exact")
            if best is None or m.score > best.score:
                best = m
            continue

        # 2) substring in any part (avoid tiny noise)
        for p in parts:
            if len(p) < 4:
                continue
            if term_n in p or p in term_n:
                if min(len(term_n), len(p)) >= 5:
                    m = Match(tag=tag, score=0.95, matched_term=term, match_type="part_substring")
                    if best is None or m.score > best.score:
                        best = m
                    break

        # 3) substring in full tag (boundary-ish)
        if best is None or best.score < 0.95:
            if re.search(rf"(^|::|_){re.escape(term_n)}(::|_|$)", t_norm):
                m = Match(tag=tag, score=0.9, matched_term=term, match_type="hierarchy_boundary")
                if best is None or m.score > best.score:
                    best = m

    return best


def build_terms(master: dict) -> dict:
    """
    Baut v2-Matching-Terme:
    - diagnoses/meds/procedures/classifications (robust)
    - plus allowed fachgebiete (inkl. hygiene/arbeitsmedizin/notfallmedizin)
    """
    content_terms: list[str] = []
    for k in ("diagnosen", "medikamente", "verfahren", "klassifikationen"):
        v = master.get(k) or []
        if isinstance(v, list):
            content_terms.extend([str(x) for x in v if str(x).strip()])

    # Nur cross-cutting / prüfungsrelevante Fachbegriffe (keine breit-klinischen Sammel-Tags)
    cross_terms = sorted(CROSSCUTTING_TERMS)

    # dedupe
    def dedupe(seq: list[str]) -> list[str]:
        seen = set()
        out: list[str] = []
        for t in seq:
            tn = normalize(t)
            if not tn or tn in seen:
                continue
            seen.add(tn)
            out.append(t)
        return out

    return {"content_terms": dedupe(content_terms), "cross_terms": dedupe(cross_terms)}


def should_include_tag(tag: str, match: Match) -> Tuple[bool, str]:
    """
    v2 Guardrails:
    - Exclude meta + preclinical
    - Avoid overly broad Fachgebiet-root tags, außer Strahlenschutz
    """
    if is_meta_tag(tag):
        return False, "meta_tag"
    if is_preclinical(tag):
        return False, "preclinical"

    parts = tag_parts(tag)
    last = parts[-1] if parts else ""

    # Avoid extremely broad tags like "...::Pharmakologie" / "...::Rechtsmedizin" / "...::Radiologie"
    # (diese ziehen sonst riesige Subdecks). Strahlenschutz ist klein genug, bleibt aber ebenfalls begrenzt.
    if last in CROSSCUTTING_TERMS:
        if len(parts) <= 4:
            return False, "too_broad_crosscutting_root"

    # High confidence threshold
    if match.score < 0.9:
        return False, "below_threshold"

    return True, "ok"


def run_for_deck(deck_name: str, tags: list[str], terms: list[str], cross_terms: list[str]) -> dict:
    include_tags: list[str] = []
    exclude_tags: list[dict] = []
    match_conf: Dict[str, float] = {}
    match_meta: Dict[str, dict] = {}

    for tag in tags:
        if not isinstance(tag, str) or not tag.strip():
            continue

        # quick exclusion
        if is_meta_tag(tag) or is_preclinical(tag):
            exclude_tags.append({"tag": tag, "reason": "meta_or_preclinical"})
            continue

        # Deck-spezifisches Scoping:
        # - Ankizin: bevorzugt KP/M3 Tags oder Querschnitt (Strahlenschutz/Pharmako/Rechtsmed/Notfall/Hygiene/Arbeitsmed)
        # - Dellas: Pharmakologie-Deck → Querschnitt-Wort "pharmakologie" ist trivial, daher NUR content_terms matchen
        t_norm = normalize(tag)
        if deck_name == "ankizin":
            if "kenntnispruefung" not in t_norm:
                # ohne KP-Signal nur die harten Querschnitte zulassen
                if not any(ct in t_norm for ct in ["strahlenschutz", "rechtsmedizin", "notfallmedizin", "hygiene", "arbeitsmedizin"]):
                    continue
        elif deck_name == "dellas":
            # Optional: nur "echte" Content/Chapter Tags, keine Credits
            if ("dellas_kapitel" not in t_norm) and ("amboss_bibliothek" not in t_norm) and ("wirkstoffe" not in t_norm):
                continue

        m = best_match(tag, terms)
        if not m:
            continue

        ok, reason = should_include_tag(tag, m)
        if not ok:
            exclude_tags.append({"tag": tag, "reason": reason, "matched_term": m.matched_term, "score": m.score})
            continue

        include_tags.append(tag)
        match_conf[tag] = round(float(m.score), 3)
        match_meta[tag] = {"matched_term": m.matched_term, "match_type": m.match_type}

    # stable sort: higher confidence first
    include_tags = sorted(include_tags, key=lambda t: (-match_conf.get(t, 0.0), t))

    return {
        "deck": deck_name,
        "include_tags": include_tags,
        "exclude_tags": exclude_tags,
        "match_confidence": match_conf,
        "match_meta": match_meta,
        "summary": {
            "unique_tags_total": len(tags),
            "include_tags": len(include_tags),
            "excluded_tags_logged": len(exclude_tags),
            "threshold": 0.9,
        },
    }


def main() -> None:
    repo_root = Path(__file__).parent.parent
    master_file = repo_root / "_OUTPUT" / "muenster_relevanz_master.json"
    ankizin_tags_file = repo_root / "_OUTPUT" / "ankizin_alle_tags.json"
    dellas_tags_file = repo_root / "_OUTPUT" / "dellas_alle_tags.json"

    with open(master_file, "r", encoding="utf-8") as f:
        master = json.load(f)
    term_sets = build_terms(master)
    content_terms: list[str] = term_sets["content_terms"]
    cross_terms: list[str] = term_sets["cross_terms"]

    with open(ankizin_tags_file, "r", encoding="utf-8") as f:
        ankizin_data = json.load(f)
    with open(dellas_tags_file, "r", encoding="utf-8") as f:
        dellas_data = json.load(f)

    ankizin_tags = ankizin_data.get("unique_tags", []) or []
    dellas_tags = dellas_data.get("unique_tags", []) or []

    ankizin_out = run_for_deck("ankizin", ankizin_tags, content_terms + cross_terms, cross_terms)
    # Dellas: KEIN "pharmakologie"-Term (sonst matcht alles). Nur content_terms.
    dellas_out = run_for_deck("dellas", dellas_tags, content_terms, cross_terms)

    out_a = repo_root / "_OUTPUT" / "ankizin_matched_tags_v2.json"
    out_d = repo_root / "_OUTPUT" / "dellas_matched_tags_v2.json"
    with open(out_a, "w", encoding="utf-8") as f:
        json.dump(ankizin_out, f, ensure_ascii=False, indent=2)
    with open(out_d, "w", encoding="utf-8") as f:
        json.dump(dellas_out, f, ensure_ascii=False, indent=2)

    print("✅ v2 matched tags geschrieben:")
    print(f"- {out_a} (include={ankizin_out['summary']['include_tags']})")
    print(f"- {out_d} (include={dellas_out['summary']['include_tags']})")


if __name__ == "__main__":
    main()


