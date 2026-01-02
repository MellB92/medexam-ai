#!/usr/bin/env python3
"""Build image candidate list from master_cards.jsonl.

Outputs JSONL with card_id, front/back, tags, image_type, query, and hints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


IMAGE_PATTERNS: List[Tuple[str, List[str]]] = [
    ("ekg", [
        r"\bekg\b",
        r"\becg\b",
        r"st[- ]?heb",
        r"st[- ]?elevation",
        r"qrs",
        r"qt[- ]?zeit",
        r"av[- ]?block",
        r"arrhythm",
        r"bradykard",
        r"tachykard",
        r"vorhofflimmer",
    ]),
    ("xray", [
        "r[o\u00f6]ntgen",
        r"\bx-?ray\b",
        r"\bxray\b",
        r"\bcxr\b",
        r"thorax",
        r"roentgen",
    ]),
    ("ct", [
        r"\bct\b",
        r"\bcct\b",
        r"ct-?angi",
        r"computertomograph",
    ]),
    ("mri", [
        r"\bmrt\b",
        r"\bmri\b",
        r"magnetresonanz",
    ]),
    ("ultrasound", [
        r"ultraschall",
        r"sonograph",
        r"\bsono\b",
        r"echokardiograph",
        r"\becho\b",
    ]),
]

TAG_HINTS = [
    ("ekg", ["ekg"]),
    ("xray", ["radiolog", "r\u00f6ntgen", "bildgebung", "roentgen"]),
    ("ct", ["ct"]),
    ("mri", ["mrt", "mri"]),
    ("ultrasound", ["sono", "ultraschall", "echo"]),
]


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


def _norm_text(s: str) -> str:
    s = s or ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", " ", text)


def _compute_card_id(front: str, back: str) -> str:
    front_n = _norm_text(front)
    back_n = _norm_text(back)
    return _sha1(front_n.lower() + "\n" + back_n.lower())


def _match_patterns(text: str, patterns: List[str]) -> List[str]:
    hits: List[str] = []
    for pat in patterns:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(pat)
    return hits


def detect_image_type(front: str, back: str, tags_raw: str) -> Tuple[Optional[str], List[str]]:
    text = f"{front}\n{back}".lower()
    tags = (tags_raw or "").lower()

    if "<img" in text:
        return None, []

    for image_type, patterns in IMAGE_PATTERNS:
        hits = _match_patterns(text, patterns)
        if hits:
            return image_type, hits

    for image_type, hints in TAG_HINTS:
        for h in hints:
            if h in tags:
                return image_type, [f"tag:{h}"]

    return None, []


def build_query(text: str, image_type: str) -> str:
    """
    Build a *search-friendly* query.

    Wikimedia searches in the File: namespace are very sensitive to long, question-like strings.
    We therefore generate short, imaging-oriented queries from keywords.
    """
    q = _norm_text(_strip_html(text))
    q = re.sub(r"^(f|frage|q)\s*[:\-]\s*", "", q, flags=re.IGNORECASE)
    q_low = q.lower()

    def toks(max_n: int = 6) -> List[str]:
        words = re.findall(r"[A-Za-zÄÖÜäöüß0-9]{3,}", q)
        return words[:max_n]

    if image_type == "xray":
        if "thorax" in q_low or "lungen" in q_low or "pleura" in q_low:
            return "chest x-ray"
        if any(k in q_low for k in ["hws", "c2", "dens", "odontoid", "axis"]):
            return "cervical spine x-ray"
        if "humerus" in q_low:
            return "humerus fracture x-ray"
        if any(k in q_low for k in ["radius", "ulna", "unterarm", "handgelenk", "ellenbogen"]):
            return "forearm fracture x-ray"
        if any(k in q_low for k in ["hüfte", "femur", "tibia", "fibula", "sprunggelenk", "knie"]):
            return "lower limb fracture x-ray"
        base = " ".join(toks(4)).strip()
        return (base + " x-ray").strip() if base else "x-ray"

    if image_type == "ekg":
        if "vorhofflimmer" in q_low:
            return "atrial fibrillation ECG"
        if any(k in q_low for k in ["st-heb", "st heb", "st-elevation", "st elevation"]):
            return "ST elevation ECG"
        if "av" in q_low and "block" in q_low:
            return "AV block ECG"
        if "qt" in q_low:
            return "long QT ECG"
        if any(k in q_low for k in ["qrs", "tachykard", "bradykard", "arrhythm"]):
            return "arrhythmia ECG"
        base = " ".join(toks(4)).strip()
        return (base + " ECG").strip() if base else "ECG"

    if image_type == "ct":
        if any(k in q_low for k in ["cct", "hirn", "schlaganfall", "blutung", "sah"]):
            return "head CT"
        if any(k in q_low for k in ["abdomen", "appendiz", "divertikul", "ileus"]):
            return "abdomen CT"
        if "ct-angi" in q_low or "ct angi" in q_low or "angiograph" in q_low:
            return "CT angiography"
        base = " ".join(toks(4)).strip()
        return (base + " CT").strip() if base else "CT"

    if image_type == "mri":
        if any(k in q_low for k in ["hirn", "gehirn"]):
            return "brain MRI"
        if any(k in q_low for k in ["knie", "menisk", "kreuzband"]):
            return "knee MRI"
        base = " ".join(toks(4)).strip()
        return (base + " MRI").strip() if base else "MRI"

    if image_type == "ultrasound":
        if any(k in q_low for k in ["echo", "echokardiograph"]):
            return "echocardiography ultrasound"
        if any(k in q_low for k in ["gallen", "cholezyst", "gallenstein"]):
            return "gallbladder ultrasound"
        if any(k in q_low for k in ["schwanger", "gravid", "woche"]):
            return "pregnancy ultrasound"
        base = " ".join(toks(4)).strip()
        return (base + " ultrasound").strip() if base else "ultrasound"

    base = " ".join(toks(5)).strip()
    return (base + " medical image").strip() if base else "medical image"


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True, help="master_cards.jsonl")
    parser.add_argument("--out", dest="out_path", required=True, help="image_candidates.jsonl")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of candidates (0=all)")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    count_in = 0
    count_out = 0

    with out_path.open("w", encoding="utf-8") as f_out:
        for card in iter_jsonl(in_path):
            count_in += 1
            front = card.get("front", "")
            back = card.get("back", "")
            tags_raw = card.get("tags_raw", "") or card.get("tags", "")

            image_type, hits = detect_image_type(front, back, tags_raw)
            if not image_type:
                continue

            card_id = card.get("card_id") or _compute_card_id(front, back)
            query = build_query(f"{front}\n{back}", image_type)

            out = {
                "card_id": card_id,
                "front": front,
                "back": back,
                "tags_raw": tags_raw,
                "source_ref": card.get("source_ref", ""),
                "image_type": image_type,
                "query": query,
                "hints": hits,
            }
            f_out.write(json.dumps(out, ensure_ascii=False) + "\n")
            count_out += 1

            if args.limit and count_out >= args.limit:
                break

    print(f"Read cards: {count_in}")
    print(f"Wrote candidates: {count_out}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
