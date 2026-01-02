#!/usr/bin/env python3
"""Build a normalized master card inventory for the All-Materials QA/Polish pipeline.

Scope (per user):
- Include (exclude Ankizin/Dellas decks):
  - _OUTPUT/anki_ready_*.tsv
  - _OUTPUT/anki_repaired_{fallbasiert,templates,ready}.tsv
  - _OUTPUT/anki_review_queue_*.tsv
  - _OUTPUT/remnote_merge/cards_merged.jsonl (+ rem_docs_merged.jsonl for resolving)
  - _OUTPUT/antworten_md/*.md (Evidenz-Antworten blocks)
  - _OUTPUT/learning_pack_*/**  (treated as context docs only; not converted to cards)

Outputs:
- master_cards.jsonl (one JSON per card)
- context_audit.jsonl (one JSON per card)

Design notes:
- TSV files in this repo consistently have 3 columns: front, back, tags.
- "Context" is considered present if we can reference at least one existing repo artifact
  (tsv/md/jsonl) that contains the card text. This satisfies reproducibility without
  pulling in new external media.

"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple


REPO_ROOT_DEFAULT = Path(__file__).resolve().parent.parent


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _norm_text(s: str) -> str:
    s = s or ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tags_to_list(tags_raw: str) -> List[str]:
    tags_raw = (tags_raw or "").strip()
    if not tags_raw:
        return []
    # Tags in this repo are space-separated.
    return [t for t in tags_raw.split() if t]


def _has_excluded_deck(tags: List[str], source_ref: str) -> Optional[str]:
    """Exclude Ankizin/Dellas material from this pipeline."""
    joined = " ".join(tags).lower() + " " + (source_ref or "").lower()
    if "ankizin" in joined:
        return "excluded_deck:ankizin"
    if "dellas" in joined:
        return "excluded_deck:dellas"
    return None


@dataclass
class MasterCard:
    card_id: str
    front: str
    back: str
    tags_raw: str
    tags: List[str]
    source_type: str
    source_ref: str
    context_ref: str
    context_found: bool
    excluded: bool
    excluded_reason: str
    notes: str


def iter_tsv_cards(path: Path) -> Iterator[Tuple[str, str, str]]:
    with path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                continue
            front = row[0]
            back = row[1] if len(row) > 1 else ""
            tags = row[2] if len(row) > 2 else ""
            if len(row) > 3:
                tags = " ".join([tags] + row[3:])
            yield front, back, tags


# --- RemNote parsing (adapted, simplified from refine_remnote_cards_openai.py) ---

def load_jsonl(path: Path) -> List[Dict]:
    items: List[Dict] = []
    if not path.exists():
        return items
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def build_rem_lookup(rem_docs: List[Dict]) -> Dict[str, Dict]:
    lookup: Dict[str, Dict] = {}
    for doc in rem_docs:
        obj = doc.get("object") or doc
        rid = obj.get("_id")
        if rid:
            lookup[str(rid)] = obj
    return lookup


def resolve_text_content(rem_obj: Dict) -> str:
    key_content = rem_obj.get("k") or rem_obj.get("key")
    if not key_content:
        n = rem_obj.get("n") or rem_obj.get("name")
        return n if isinstance(n, str) else ""

    parts: List[str] = []
    if isinstance(key_content, list):
        for part in key_content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
    elif isinstance(key_content, str):
        parts.append(key_content)
    return "".join(parts)


def build_parent_children(rems: List[Dict]) -> Dict[str, List[str]]:
    parent_to_children: Dict[str, List[str]] = {}
    for doc in rems:
        obj = doc.get("object") or doc
        cid = obj.get("_id")
        pid = obj.get("parent")
        if cid and pid:
            parent_to_children.setdefault(str(pid), []).append(str(cid))
    return parent_to_children


def build_card_front_back(rem_id: str, lookup: Dict[str, Dict], parent_to_children: Dict[str, List[str]]) -> Tuple[str, str]:
    rem = lookup.get(rem_id) or {}
    front = resolve_text_content(rem).strip()

    ai = rem.get("ai") or {}
    ai_def = (ai.get("def") or "").strip() if isinstance(ai, dict) else ""
    if ai_def:
        return front, ai_def

    bullets: List[str] = []
    for cid in parent_to_children.get(rem_id, [])[:8]:
        c = lookup.get(cid) or {}
        c_text = resolve_text_content(c).strip()
        c_ai = c.get("ai") or {}
        c_def = (c_ai.get("def") or "").strip() if isinstance(c_ai, dict) else ""
        if c_text and c_def and c_def.lower() != c_text.lower():
            bullets.append(f"- **{c_text}**: {c_def}")
        elif c_text:
            bullets.append(f"- {c_text}")
        elif c_def:
            bullets.append(f"- {c_def}")

    back = "\n".join(bullets) if bullets else "[Antwort aus RemNote-Struktur nicht eindeutig rekonstruierbar – bitte prüfen]"
    return front, back


def iter_remnote_cards(repo_root: Path) -> Iterator[Tuple[str, str, str, str]]:
    cards_file = repo_root / "_OUTPUT/remnote_merge/cards_merged.jsonl"
    rem_file = repo_root / "_OUTPUT/remnote_merge/rem_docs_merged.jsonl"
    if not cards_file.exists() or not rem_file.exists():
        return

    cards = load_jsonl(cards_file)
    rems = load_jsonl(rem_file)
    lookup = build_rem_lookup(rems)
    parent_to_children = build_parent_children(rems)

    for card in cards:
        obj = card.get("object") or {}
        key = obj.get("k")
        if not key:
            continue
        rem_id = key.split(".")[0] if "." in key else key
        q, a = build_card_front_back(str(rem_id), lookup, parent_to_children)
        if not q.strip():
            continue
        tags = "source::remnote"
        source_ref = str(cards_file.relative_to(repo_root))
        yield q, a, tags, source_ref


# --- Evidenz-Antworten markdown parsing ---

_RE_Q_HEADER = re.compile(r"^##\s+Frage\s+(\d+)\s*$")


def iter_evidenz_md_cards(md_path: Path) -> Iterator[Tuple[str, str, str]]:
    """Parse evidenz_antworten*.md into Q/A cards.

    Heuristic:
    - Question is the first bold line after "## Frage N".
    - Answer is content under "### Antwort" until next "## Frage".

    """

    text = md_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    i = 0
    while i < len(lines):
        m = _RE_Q_HEADER.match(lines[i].strip())
        if not m:
            i += 1
            continue
        i += 1

        question = ""
        while i < len(lines) and not lines[i].startswith("## "):
            line = lines[i].strip()
            if line.startswith("**") and line.endswith("**") and len(line) > 4:
                question = line.strip("*")
                break
            i += 1

        while i < len(lines) and lines[i].strip() != "### Antwort" and not lines[i].startswith("## "):
            i += 1
        if i >= len(lines) or lines[i].startswith("## "):
            continue

        i += 1  # skip ### Antwort
        ans_lines: List[str] = []
        meta: List[str] = []
        while i < len(lines) and not lines[i].startswith("## "):
            ln = lines[i]
            ans_lines.append(ln)
            if "*Quelle:" in ln or "*Referenzen:" in ln or "*Konfidenz:" in ln:
                meta.append(ln.strip())
            i += 1

        answer = "\n".join(ans_lines).strip()
        if not question.strip() or not answer.strip():
            continue

        tags = ["source::antworten_md", f"qblock::{md_path.stem}"]
        if meta:
            tags.append("meta::has_citations")
        yield question.strip(), answer, " ".join(tags)


def build_master(repo_root: Path, out_path: Path, audit_path: Path, *, limit: int = 0) -> None:
    out_dir = repo_root / "_OUTPUT"

    sources: List[Tuple[str, Path]] = []
    for pattern in ["anki_ready_*.tsv", "anki_review_queue_*.tsv", "anki_repaired_*.tsv"]:
        sources.extend(("tsv", p) for p in sorted(out_dir.glob(pattern)))

    evid_dir = out_dir / "antworten_md"
    sources.extend(("antworten_md", p) for p in sorted(evid_dir.glob("evidenz_antworten*.md")))

    seen: Dict[str, str] = {}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as f_out, audit_path.open("w", encoding="utf-8") as f_audit:
        # TSV inputs
        for stype, path in sources:
            if limit and len(seen) >= limit:
                break

            if stype == "tsv":
                for front, back, tags_raw in iter_tsv_cards(path):
                    if limit and len(seen) >= limit:
                        break
                    _write_card(
                        f_out,
                        f_audit,
                        seen,
                        front,
                        back,
                        tags_raw,
                        source_type=_infer_source_type_from_name(path.name),
                        source_ref=f"_OUTPUT/{path.name}",
                    )

            elif stype == "antworten_md":
                for front, back, tags_raw in iter_evidenz_md_cards(path):
                    if limit and len(seen) >= limit:
                        break
                    _write_card(
                        f_out,
                        f_audit,
                        seen,
                        front,
                        back,
                        tags_raw,
                        source_type="antworten_md",
                        source_ref=str(path.relative_to(repo_root)),
                    )

        # RemNote cards (optional)
        for front, back, tags_raw, source_ref in iter_remnote_cards(repo_root):
            if limit and len(seen) >= limit:
                break
            _write_card(
                f_out,
                f_audit,
                seen,
                front,
                back,
                tags_raw,
                source_type="remnote",
                source_ref=source_ref,
            )


def _infer_source_type_from_name(name: str) -> str:
    if name.startswith("anki_ready_"):
        return "anki_ready"
    if name.startswith("anki_review_queue_"):
        return "anki_review_queue"
    if name.startswith("anki_repaired_"):
        return "anki_repaired"
    return "tsv"


def _write_card(
    f_out,
    f_audit,
    seen: Dict[str, str],
    front: str,
    back: str,
    tags_raw: str,
    *,
    source_type: str,
    source_ref: str,
) -> None:
    front_n = _norm_text(front)
    back_n = _norm_text(back)
    if not front_n or not back_n:
        return

    card_id = _sha1(front_n.lower() + "\n" + back_n.lower())
    if card_id in seen:
        return

    tags = _tags_to_list(tags_raw)
    excluded_reason = _has_excluded_deck(tags, source_ref) or ""
    excluded = bool(excluded_reason)

    context_ref = source_ref

    notes = ""
    tagged_no_context = any(t.startswith("context::no_context") for t in tags)
    if tagged_no_context:
        notes = "tagged_no_context"

    # Strict context audit: known 'no_context' tags are treated as missing.
    context_found = not tagged_no_context

    card = MasterCard(
        card_id=card_id,
        front=front_n,
        back=back_n,
        tags_raw=(tags_raw or "").strip(),
        tags=tags,
        source_type=source_type,
        source_ref=source_ref,
        context_ref=context_ref,
        context_found=context_found,
        excluded=excluded,
        excluded_reason=excluded_reason,
        notes=notes,
    )

    f_out.write(json.dumps(asdict(card), ensure_ascii=False) + "\n")
    audit = {
        "card_id": card_id,
        "context_ref": context_ref,
        "context_found": context_found,
        "quellen_min": 1 if context_found else 0,
        "missing_context": (not context_found),
        "missing_context_reason": "tagged_no_context" if tagged_no_context else "",
        "excluded": excluded,
        "excluded_reason": excluded_reason,
    }
    f_audit.write(json.dumps(audit, ensure_ascii=False) + "\n")

    seen[card_id] = source_ref


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(REPO_ROOT_DEFAULT), help="Repo root (default: scripts/..)")
    parser.add_argument("--out", required=True, help="Output master_cards.jsonl")
    parser.add_argument(
        "--audit-out", default="", help="Output context_audit.jsonl (default: sibling of --out)"
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit number of cards (0=all)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root)
    out_path = Path(args.out)
    audit_path = Path(args.audit_out) if args.audit_out else out_path.with_name("context_audit.jsonl")

    build_master(repo_root, out_path, audit_path, limit=args.limit)
    print(f"Wrote master cards: {out_path}")
    print(f"Wrote context audit: {audit_path}")


if __name__ == "__main__":
    main()
