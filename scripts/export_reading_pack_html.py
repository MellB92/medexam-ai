#!/usr/bin/env python3
"""
Export offline HTML reading packs for case blocks with local images.

Inputs:
  - TSVs with (front, back, tags)
  - Blocks JSON with context[] + questions[] + source_file + block_id

Outputs:
  - _OUTPUT/reading_pack/01_cases_flat.html
  - _OUTPUT/reading_pack/02_cases_by_fachgebiet.html
  - _OUTPUT/reading_pack/media_images/ (only referenced images)
  - _OUTPUT/reading_pack/report.md
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import shutil
import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


IMG_SRC_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")


@dataclass
class Card:
    question: str
    answer_html: str
    tags_raw: str
    tags: List[str]
    source: str
    norm: str
    norm_ascii: str


@dataclass
class Block:
    block_id: str
    source_file: str
    context: List[str]
    questions: List[str]
    year: Optional[int]
    matches: List["Match"]
    unmatched_questions: List[str]
    fachgebiet_tags: List[str]
    risk_tags: List[str]
    qa_tags: List[str]
    priority: int


@dataclass
class Match:
    question_raw: str
    card: Optional[Card]
    match_type: str


def _strip_diacritics(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _clean_quotes(text: str) -> str:
    return (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("„", '"')
        .replace("’", "'")
        .replace("‘", "'")
        .replace("–", "-")
        .replace("—", "-")
    )


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _normalize_question(text: str) -> str:
    if not text:
        return ""
    t = html.unescape(text)
    t = _clean_quotes(t)
    t = _strip_html(t)
    t = t.strip()
    # Remove common prefixes
    t = re.sub(r"^\s*(frage|prüfungsfrage|f|q|question)\s*[:\-\u2013]\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*kontext\s*[:\-\u2013]\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^\s*\d+\s*[\)\.\-:]\s*", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _normalize_key(text: str, *, ascii_only: bool = False) -> str:
    t = _normalize_question(text).lower()
    t = re.sub(r"[^0-9a-zA-ZäöüÄÖÜß]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    if ascii_only:
        t = _strip_diacritics(t)
        t = re.sub(r"[^0-9a-zA-Z]+", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
    return t


def _token_key(norm: str) -> str:
    toks = norm.split()
    if len(toks) >= 2:
        return f"{toks[0]} {toks[1]}"
    if toks:
        return toks[0]
    return ""


def _parse_tags(tags_raw: str) -> List[str]:
    tags = re.split(r"[\s,]+", (tags_raw or "").strip())
    return [t for t in tags if t]


def _extract_tags(tags: Sequence[str], prefix: str) -> List[str]:
    return sorted({t for t in tags if t.startswith(prefix)})


def _priority_from_tags(tags: Sequence[str]) -> int:
    tag_set = set(tags)
    if "risk::dose" in tag_set:
        return 0
    if "risk::radiation" in tag_set:
        return 1
    if "risk::guideline" in tag_set:
        return 2
    if "qa::needs_review" in tag_set:
        return 3
    return 4


def _infer_year_from_texts(texts: Iterable[str]) -> Optional[int]:
    years: List[int] = []
    for t in texts:
        if not t:
            continue
        for match in YEAR_RE.findall(t):
            try:
                years.append(int(match))
            except ValueError:
                continue
    if not years:
        return None
    return max(years)


def _infer_year(block: Dict[str, Any]) -> Optional[int]:
    candidates: List[str] = []
    for key in ("source_file", "block_id", "source_page"):
        val = block.get(key)
        if isinstance(val, str) and val.strip():
            candidates.append(val)
    for item in block.get("context") or []:
        if isinstance(item, str):
            candidates.append(item)
    for item in block.get("questions") or block.get("fragen") or []:
        if isinstance(item, str):
            candidates.append(item)
    return _infer_year_from_texts(candidates)


def _load_tsv(path: Path) -> List[Card]:
    cards: List[Card] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue
            question = row[0].strip()
            answer = row[1].strip()
            tags_raw = row[2].strip() if len(row) > 2 else ""
            tags = _parse_tags(tags_raw)
            norm = _normalize_key(question)
            norm_ascii = _normalize_key(question, ascii_only=True)
            cards.append(
                Card(
                    question=question,
                    answer_html=answer,
                    tags_raw=tags_raw,
                    tags=tags,
                    source=str(path),
                    norm=norm,
                    norm_ascii=norm_ascii,
                )
            )
    return cards


def _build_card_index(cards: Sequence[Card]) -> Tuple[Dict[str, List[int]], Dict[str, List[int]], Dict[str, List[int]]]:
    by_norm: Dict[str, List[int]] = {}
    by_norm_ascii: Dict[str, List[int]] = {}
    by_token_key: Dict[str, List[int]] = {}
    for idx, card in enumerate(cards):
        if card.norm:
            by_norm.setdefault(card.norm, []).append(idx)
            key = _token_key(card.norm)
            if key:
                by_token_key.setdefault(key, []).append(idx)
        if card.norm_ascii:
            by_norm_ascii.setdefault(card.norm_ascii, []).append(idx)
    return by_norm, by_norm_ascii, by_token_key


def _best_fuzzy_match(
    norm: str,
    norm_ascii: str,
    cards: Sequence[Card],
    candidates: Sequence[int],
    threshold: float = 0.92,
) -> Optional[int]:
    from difflib import SequenceMatcher

    best_idx = None
    best_score = 0.0
    for idx in candidates:
        card = cards[idx]
        score = SequenceMatcher(None, norm, card.norm).ratio() if norm and card.norm else 0.0
        if score < threshold and norm_ascii and card.norm_ascii:
            score = SequenceMatcher(None, norm_ascii, card.norm_ascii).ratio()
        if score > best_score:
            best_score = score
            best_idx = idx
    if best_idx is not None and best_score >= threshold:
        return best_idx
    return None


def _match_question(
    question: str,
    cards: Sequence[Card],
    by_norm: Dict[str, List[int]],
    by_norm_ascii: Dict[str, List[int]],
    by_token_key: Dict[str, List[int]],
    used_in_block: Set[int],
) -> Tuple[Optional[Card], Optional[int], str]:
    norm = _normalize_key(question)
    norm_ascii = _normalize_key(question, ascii_only=True)
    if norm in by_norm:
        for idx in by_norm[norm]:
            if idx not in used_in_block:
                used_in_block.add(idx)
                return cards[idx], idx, "exact"
        return cards[by_norm[norm][0]], by_norm[norm][0], "exact"
    if norm_ascii in by_norm_ascii:
        for idx in by_norm_ascii[norm_ascii]:
            if idx not in used_in_block:
                used_in_block.add(idx)
                return cards[idx], idx, "ascii"
        return cards[by_norm_ascii[norm_ascii][0]], by_norm_ascii[norm_ascii][0], "ascii"

    key = _token_key(norm)
    candidates = by_token_key.get(key, [])
    if not candidates and norm:
        # fallback to all cards if key is empty
        candidates = list(range(len(cards)))
    fuzzy_idx = _best_fuzzy_match(norm, norm_ascii, cards, candidates)
    if fuzzy_idx is not None:
        used_in_block.add(fuzzy_idx)
        return cards[fuzzy_idx], fuzzy_idx, "fuzzy"
    return None, None, "unmatched"


def _rewrite_img_src(answer_html: str, image_set: Set[str]) -> str:
    def repl(match: re.Match) -> str:
        src = match.group(1)
        basename = os.path.basename(src)
        if basename:
            image_set.add(basename)
        return match.group(0).replace(src, f"media_images/{basename}")

    return IMG_SRC_RE.sub(repl, answer_html)


def _collect_blocks(
    blocks: Sequence[Dict[str, Any]],
    cards: Sequence[Card],
    by_norm: Dict[str, List[int]],
    by_norm_ascii: Dict[str, List[int]],
    by_token_key: Dict[str, List[int]],
) -> Tuple[List[Block], Set[int], List[str]]:
    matched_cards: Set[int] = set()
    unmatched_questions_global: List[str] = []
    processed_blocks: List[Block] = []

    for block in blocks:
        block_id = str(block.get("block_id") or "")
        source_file = str(block.get("source_file") or "")
        context = [str(x) for x in (block.get("context") or block.get("kontext") or []) if str(x).strip()]
        q_raw = block.get("questions") or block.get("fragen") or []
        questions = [str(x) for x in q_raw if str(x).strip()]
        year = _infer_year(block)

        used_in_block: Set[int] = set()
        matches: List[Match] = []
        unmatched_questions: List[str] = []

        for q in questions:
            card, idx, match_type = _match_question(
                q, cards, by_norm, by_norm_ascii, by_token_key, used_in_block
            )
            matches.append(Match(question_raw=q, card=card, match_type=match_type))
            if card is None:
                unmatched_questions.append(q)
                unmatched_questions_global.append(q)
            else:
                if idx is not None:
                    matched_cards.add(idx)

        all_tags: List[str] = []
        for m in matches:
            if m.card:
                all_tags.extend(m.card.tags)

        fachgebiet_tags = _extract_tags(all_tags, "fachgebiet::")
        risk_tags = _extract_tags(all_tags, "risk::")
        qa_tags = _extract_tags(all_tags, "qa::")
        priority = _priority_from_tags(all_tags) if all_tags else 5

        processed_blocks.append(
            Block(
                block_id=block_id,
                source_file=source_file,
                context=context,
                questions=questions,
                year=year,
                matches=matches,
                unmatched_questions=unmatched_questions,
                fachgebiet_tags=fachgebiet_tags,
                risk_tags=risk_tags,
                qa_tags=qa_tags,
                priority=priority,
            )
        )

    return processed_blocks, matched_cards, unmatched_questions_global


def _sort_blocks(blocks: List[Block]) -> List[Block]:
    def sort_key(block: Block) -> Tuple[int, int, str, str]:
        year = block.year if block.year is not None else -1
        return (-year, block.priority, block.source_file, block.block_id)

    return sorted(blocks, key=sort_key)


def _build_html_header(title: str) -> str:
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, Helvetica, Arial, sans-serif;
      margin: 24px;
      background: #f7f7f5;
      color: #1d1d1f;
    }}
    h1, h2, h3 {{
      margin-top: 1.2em;
    }}
    .toc {{
      background: #fff;
      border: 1px solid #ddd;
      padding: 12px 16px;
      border-radius: 8px;
    }}
    details {{
      background: #fff;
      border: 1px solid #e1e1e1;
      border-radius: 8px;
      margin: 10px 0;
      padding: 8px 12px;
    }}
    summary {{
      cursor: pointer;
      font-weight: 600;
    }}
    .meta {{
      font-size: 0.9em;
      color: #555;
      margin: 6px 0 12px;
    }}
    .tags {{
      font-size: 0.85em;
      color: #444;
      margin: 6px 0 12px;
    }}
    .tag {{
      display: inline-block;
      margin-right: 6px;
      padding: 2px 6px;
      border-radius: 6px;
      background: #eef2f7;
    }}
    .context {{
      margin: 10px 0 12px;
      padding: 10px 12px;
      background: #f9f9fb;
      border-left: 3px solid #d0d7de;
    }}
    .qa {{
      margin: 8px 0 18px;
      padding: 10px 12px;
      border-left: 3px solid #e0e0e0;
    }}
    .qa h4 {{
      margin: 0 0 8px;
    }}
    .answer {{
      margin: 6px 0;
    }}
    .unmatched {{
      color: #a00;
      font-style: italic;
    }}
    .footer {{
      margin-top: 32px;
      font-size: 0.9em;
      color: #444;
      background: #fff;
      border: 1px solid #ddd;
      padding: 12px 16px;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
"""


def _build_html_footer() -> str:
    return "</body></html>"


def _format_tag_list(tags: Sequence[str]) -> str:
    if not tags:
        return "<span class=\"tag\">none</span>"
    return " ".join(f"<span class=\"tag\">{html.escape(t)}</span>" for t in tags)


def _block_summary_text(block: Block) -> str:
    year = block.year if block.year is not None else "unknown"
    return f"[{year}] {block.source_file} ({len(block.questions)} Fragen)"


def _block_suffix(block: Block) -> str:
    base = block.block_id or block.source_file or "block"
    h = hashlib.sha1(base.encode("utf-8", errors="ignore")).hexdigest()
    return h[:10]


def _question_anchor(question: str, suffix: str) -> str:
    base = _normalize_key(question, ascii_only=True) or "question"
    base = re.sub(r"[^0-9a-zA-Z]+", "-", base).strip("-")
    return f"q-{base}-{suffix}"


def _render_blocks(blocks: Sequence[Block], image_set: Set[str]) -> str:
    html_parts: List[str] = []
    for block in blocks:
        summary = _block_summary_text(block)
        block_suffix = _block_suffix(block)
        html_parts.append("<details>")
        html_parts.append(f"<summary>{html.escape(summary)}</summary>")
        meta = f"Quelle: {block.source_file} | Jahr: {block.year if block.year is not None else 'unknown'}"
        html_parts.append(f"<div class=\"meta\">{html.escape(meta)}</div>")
        html_parts.append("<div class=\"tags\">")
        html_parts.append(f"Fachgebiet: {_format_tag_list(block.fachgebiet_tags)}<br>")
        html_parts.append(f"Risiko: {_format_tag_list(block.risk_tags)}<br>")
        html_parts.append(f"QA: {_format_tag_list(block.qa_tags)}")
        html_parts.append("</div>")

        if block.context:
            html_parts.append("<div class=\"context\">")
            for ctx in block.context:
                html_parts.append(f"<p>{html.escape(ctx)}</p>")
            html_parts.append("</div>")

        for q_idx, match in enumerate(block.matches, start=1):
            anchor = _question_anchor(match.question_raw, f"{block_suffix}-{q_idx}")
            html_parts.append("<div class=\"qa\">")
            html_parts.append(f"<h4 id=\"{anchor}\">Q: {html.escape(match.question_raw)}</h4>")
            if match.card:
                answer = _rewrite_img_src(match.card.answer_html, image_set)
                html_parts.append(f"<div class=\"answer\">{answer}</div>")
                if match.card.tags_raw:
                    html_parts.append(f"<div class=\"tags\">Tags: {html.escape(match.card.tags_raw)}</div>")
            else:
                html_parts.append("<div class=\"answer unmatched\">Keine gematchte Karte gefunden.</div>")
            html_parts.append("</div>")

        html_parts.append("</details>")
    return "\n".join(html_parts)


def _render_toc_by_year(blocks: Sequence[Block]) -> str:
    by_year: Dict[str, int] = {}
    for block in blocks:
        year = str(block.year) if block.year is not None else "unknown"
        by_year[year] = by_year.get(year, 0) + 1
    items = []
    for year in sorted(by_year.keys(), reverse=True):
        anchor = f"year-{year}"
        items.append(f"<li><a href=\"#{anchor}\">{html.escape(year)} ({by_year[year]})</a></li>")
    return "<ul>" + "".join(items) + "</ul>"


def _render_toc_by_fachgebiet(groups: Dict[str, List[Block]]) -> str:
    items = []
    for fach in sorted(groups.keys()):
        anchor = f"fach-{fach.replace('::', '-').replace('/', '-')}"
        items.append(f"<li><a href=\"#{anchor}\">{html.escape(fach)} ({len(groups[fach])})</a></li>")
    return "<ul>" + "".join(items) + "</ul>"


def _write_flat_html(out_path: Path, blocks: Sequence[Block], image_set: Set[str]) -> None:
    parts: List[str] = []
    parts.append(_build_html_header("Reading Pack - Fallketten (chronologisch)"))
    parts.append("<h1>Reading Pack - Fallketten (chronologisch)</h1>")
    parts.append("<div class=\"toc\">")
    parts.append("<strong>Inhaltsverzeichnis</strong><br>")
    parts.append("Tipp: Browser-Suche (Cmd/Ctrl+F) nutzen.<br>")
    parts.append(_render_toc_by_year(blocks))
    parts.append("</div>")

    # Group by year headings for readability
    current_year = None
    for block in blocks:
        year = str(block.year) if block.year is not None else "unknown"
        if year != current_year:
            current_year = year
            parts.append(f"<h2 id=\"year-{year}\">{html.escape(year)}</h2>")
        parts.append(_render_blocks([block], image_set))

    parts.append(_render_readme())
    parts.append(_build_html_footer())
    out_path.write_text("\n".join(parts), encoding="utf-8")


def _write_by_fachgebiet_html(out_path: Path, groups: Dict[str, List[Block]], image_set: Set[str]) -> None:
    parts: List[str] = []
    parts.append(_build_html_header("Reading Pack - Nach Fachgebiet"))
    parts.append("<h1>Reading Pack - Nach Fachgebiet</h1>")
    parts.append("<div class=\"toc\">")
    parts.append("<strong>Inhaltsverzeichnis</strong><br>")
    parts.append("Tipp: Browser-Suche (Cmd/Ctrl+F) nutzen.<br>")
    parts.append(_render_toc_by_fachgebiet(groups))
    parts.append("</div>")

    for fach in sorted(groups.keys()):
        anchor = f"fach-{fach.replace('::', '-').replace('/', '-')}"
        parts.append(f"<h2 id=\"{anchor}\">{html.escape(fach)}</h2>")
        parts.append(_render_blocks(groups[fach], image_set))

    parts.append(_render_readme())
    parts.append(_build_html_footer())
    out_path.write_text("\n".join(parts), encoding="utf-8")


def _choose_best_card(cards: Sequence[Card]) -> Optional[Card]:
    """
    Pick a representative card for a deduplicated question group.

    Preference order (best first):
    - has risk::dose / risk::radiation / risk::guideline
    - has extern::verified
    - longer answer_html (more informative)
    """
    if not cards:
        return None

    def score(card: Card) -> Tuple[int, int, int]:
        tags = set(card.tags)
        pr = _priority_from_tags(card.tags)
        ext_verified = 0 if "extern::verified" in tags else 1
        # longer is better -> negative for sorting ascending
        length = -len(card.answer_html or "")
        return (pr, ext_verified, length)

    return sorted(cards, key=score)[0]


def _build_dedup_index(blocks: Sequence[Block]) -> Dict[str, Dict[str, Any]]:
    """
    Build a deduplicated index: normalized question key -> aggregate info.

    Each entry contains:
      - question_display: original question text (first seen)
      - years: set of years across occurrences
      - occurrences: list of {year, source_file, context, match_type}
      - cards: list of Card objects (may include duplicates across blocks)
      - tags_agg: set of tags
    """
    idx: Dict[str, Dict[str, Any]] = {}
    for block in blocks:
        year = block.year
        for m in block.matches:
            q = m.question_raw
            key = _normalize_key(q, ascii_only=True) or _normalize_key(q) or q.strip().lower()
            entry = idx.setdefault(
                key,
                {
                    "question_display": q,
                    "years": set(),
                    "occurrences": [],
                    "cards": [],
                    "tags": set(),
                },
            )
            if year is not None:
                entry["years"].add(year)
            entry["occurrences"].append(
                {
                    "year": year,
                    "source_file": block.source_file,
                    "context": block.context,
                    "match_type": m.match_type,
                }
            )
            if m.card:
                entry["cards"].append(m.card)
                entry["tags"].update(m.card.tags)
    return idx


def _write_dedup_questions_html(out_path: Path, blocks: Sequence[Block], image_set: Set[str]) -> None:
    """
    Write deduplicated view: each question once, with all contexts/sources below.
    """
    idx = _build_dedup_index(blocks)

    # Turn into list with sorting keys
    items: List[Tuple[str, Dict[str, Any]]] = list(idx.items())

    def max_year(entry: Dict[str, Any]) -> int:
        years = entry.get("years") or set()
        if years:
            return max(years)
        # If no explicit year, try infer from source strings
        candidates = []
        for occ in entry.get("occurrences", []):
            candidates.append(str(occ.get("source_file") or ""))
        y = _infer_year_from_texts(candidates)
        return y if y is not None else -1

    def priority(entry: Dict[str, Any]) -> int:
        tags = list(entry.get("tags") or [])
        return _priority_from_tags(tags) if tags else 5

    def sort_key(item: Tuple[str, Dict[str, Any]]) -> Tuple[int, int, int, str]:
        key, entry = item
        y = max_year(entry)
        pr = priority(entry)
        freq = len(entry.get("occurrences") or [])
        return (-y, pr, -freq, entry.get("question_display", key))

    items_sorted = sorted(items, key=sort_key)

    parts: List[str] = []
    parts.append(_build_html_header("Reading Pack - Deduplizierte Fragen"))
    parts.append("<h1>Reading Pack - Deduplizierte Fragen</h1>")
    parts.append("<div class=\"toc\">")
    parts.append("<strong>Hinweis</strong><br>")
    parts.append("Jede Frage wird nur einmal angezeigt. Darunter sind alle Quellen/Blöcke (mit Kontext) aufgeführt.<br>")
    parts.append("Tipp: Browser-Suche (Cmd/Ctrl+F) nutzen.<br>")
    parts.append("</div>")

    for _, entry in items_sorted:
        q = str(entry.get("question_display") or "")
        occs = entry.get("occurrences") or []
        years = entry.get("years") or set()
        y = max(years) if years else _infer_year_from_texts([str(o.get("source_file") or "") for o in occs]) or "unknown"
        tags = sorted(entry.get("tags") or [])
        fach = _extract_tags(tags, "fachgebiet::")
        risk = _extract_tags(tags, "risk::")
        qa = _extract_tags(tags, "qa::")
        pr = _priority_from_tags(tags) if tags else 5

        cards: List[Card] = entry.get("cards") or []
        best = _choose_best_card(cards)

        parts.append("<details>")
        parts.append(f"<summary>[{html.escape(str(y))}] {html.escape(q)} ({len(occs)}×)</summary>")
        parts.append(f"<div class=\"meta\">Priorität: {pr} | Häufigkeit: {len(occs)}</div>")
        parts.append("<div class=\"tags\">")
        parts.append(f"Fachgebiet: {_format_tag_list(fach)}<br>")
        parts.append(f"Risiko: {_format_tag_list(risk)}<br>")
        parts.append(f"QA: {_format_tag_list(qa)}")
        parts.append("</div>")

        if best:
            answer = _rewrite_img_src(best.answer_html, image_set)
            parts.append("<div class=\"qa\">")
            parts.append("<h4>Antwort (repräsentativ)</h4>")
            parts.append(f"<div class=\"answer\">{answer}</div>")
            parts.append("</div>")
        else:
            parts.append("<div class=\"qa\"><div class=\"answer unmatched\">Keine gematchte Karte gefunden.</div></div>")

        # Occurrences list
        parts.append("<div class=\"qa\">")
        parts.append("<h4>Vorkommen / Kontexte</h4>")
        for i, occ in enumerate(occs, 1):
            src = str(occ.get("source_file") or "")
            oy = occ.get("year")
            mt = str(occ.get("match_type") or "")
            parts.append("<details>")
            parts.append(f"<summary>{html.escape(src)} | Jahr: {html.escape(str(oy) if oy is not None else 'unknown')} | match: {html.escape(mt)}</summary>")
            ctx = occ.get("context") or []
            if ctx:
                parts.append("<div class=\"context\">")
                for c in ctx:
                    parts.append(f"<p>{html.escape(str(c))}</p>")
                parts.append("</div>")
            parts.append("</details>")
        parts.append("</div>")

        parts.append("</details>")

    parts.append(_render_readme())
    parts.append(_build_html_footer())
    out_path.write_text("\n".join(parts), encoding="utf-8")


def _render_readme() -> str:
    return """<div class="footer">
<strong>README</strong>
<ul>
  <li>Diese HTML-Datei ist offline nutzbar. Bilder liegen im Ordner <code>media_images/</code>.</li>
  <li>Zum Oeffnen: Datei doppelklicken oder im Browser laden.</li>
  <li>Tags: <code>risk::dose</code> / <code>risk::radiation</code> / <code>risk::guideline</code> markieren Prioritaet.</li>
  <li><code>qa::needs_review</code> markiert Karten, die vor dem Lernen zu pruefen sind.</li>
</ul>
</div>"""


def _copy_images(media_src: Path, media_out: Path, image_set: Set[str]) -> List[str]:
    missing: List[str] = []
    media_out.mkdir(parents=True, exist_ok=True)
    for name in sorted(image_set):
        src = media_src / name
        dst = media_out / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, dst)
    return missing


def _write_report(
    out_path: Path,
    total_blocks: int,
    total_block_questions: int,
    matched_questions: int,
    total_cards: int,
    matched_cards: int,
    unmatched_cards: List[Card],
    unmatched_questions: List[str],
    missing_images: List[str],
) -> None:
    ratio = (matched_cards / total_cards) * 100 if total_cards else 0.0
    lines: List[str] = []
    lines.append("# Reading Pack Report")
    lines.append("")
    lines.append(f"- Blocks: {total_blocks}")
    lines.append(f"- Block questions: {total_block_questions}")
    lines.append(f"- Matched questions: {matched_questions}")
    lines.append(f"- Total cards (TSV): {total_cards}")
    lines.append(f"- Matched cards (unique): {matched_cards} ({ratio:.2f}%)")
    lines.append(f"- Unmatched cards: {len(unmatched_cards)}")
    lines.append(f"- Unmatched block questions: {len(unmatched_questions)}")
    lines.append(f"- Missing images: {len(missing_images)}")
    lines.append("")

    if ratio < 95.0:
        lines.append("> WARNING: Matched cards below 95%. Check unmatched lists.")
        lines.append("")

    if unmatched_cards:
        lines.append("## Unmatched cards (sample)")
        for card in unmatched_cards[:30]:
            lines.append(f"- {card.question}  [{card.tags_raw}]")
        lines.append("")

    if unmatched_questions:
        lines.append("## Unmatched block questions (sample)")
        for q in unmatched_questions[:30]:
            lines.append(f"- {q}")
        lines.append("")

    if missing_images:
        lines.append("## Missing images")
        for name in missing_images[:50]:
            lines.append(f"- {name}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ok", required=True, help="TSV with OK cards (with images)")
    parser.add_argument("--needsreview", required=True, help="TSV with needs_review cards (with images)")
    parser.add_argument("--blocks", required=True, help="JSON blocks file")
    parser.add_argument("--media-src", required=True, help="Source media_images directory")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    args = parser.parse_args()

    ok_path = Path(args.ok)
    needs_path = Path(args.needsreview)
    blocks_path = Path(args.blocks)
    media_src = Path(args.media_src)
    out_dir = Path(args.out_dir)

    for p in (ok_path, needs_path, blocks_path, media_src):
        if not p.exists():
            raise SystemExit(f"Missing input: {p}")

    out_dir.mkdir(parents=True, exist_ok=True)
    media_out = out_dir / "media_images"

    cards = _load_tsv(ok_path) + _load_tsv(needs_path)
    by_norm, by_norm_ascii, by_token_key = _build_card_index(cards)

    with blocks_path.open("r", encoding="utf-8") as f:
        blocks_data = json.load(f)
    if not isinstance(blocks_data, list):
        raise SystemExit("Blocks JSON must be a list of blocks.")

    blocks, matched_cards, unmatched_questions = _collect_blocks(
        blocks_data, cards, by_norm, by_norm_ascii, by_token_key
    )
    blocks_sorted = _sort_blocks(blocks)

    image_set: Set[str] = set()
    flat_html = out_dir / "01_cases_flat.html"
    _write_flat_html(flat_html, blocks_sorted, image_set)

    # Group by fachgebiet
    groups: Dict[str, List[Block]] = {}
    for block in blocks_sorted:
        fach_list = block.fachgebiet_tags or ["fachgebiet::unknown"]
        for fach in fach_list:
            groups.setdefault(fach, []).append(block)

    # Ensure same sorting inside each group
    for fach, items in groups.items():
        groups[fach] = _sort_blocks(items)

    by_fach_html = out_dir / "02_cases_by_fachgebiet.html"
    _write_by_fachgebiet_html(by_fach_html, groups, image_set)

    dedup_html = out_dir / "03_questions_dedup.html"
    _write_dedup_questions_html(dedup_html, blocks_sorted, image_set)

    missing_images = _copy_images(media_src, media_out, image_set)

    # Report
    total_blocks = len(blocks_sorted)
    total_block_questions = sum(len(b.questions) for b in blocks_sorted)
    matched_questions = total_block_questions - len(unmatched_questions)

    matched_cards_set = {idx for idx in matched_cards}
    unmatched_cards = [card for i, card in enumerate(cards) if i not in matched_cards_set]

    report_path = out_dir / "report.md"
    _write_report(
        report_path,
        total_blocks,
        total_block_questions,
        matched_questions,
        len(cards),
        len(matched_cards_set),
        unmatched_cards,
        unmatched_questions,
        missing_images,
    )

    print(f"Wrote: {flat_html}")
    print(f"Wrote: {by_fach_html}")
    print(f"Wrote: {report_path}")
    print(f"Media copied: {len(image_set) - len(missing_images)} (missing {len(missing_images)})")


if __name__ == "__main__":
    main()
