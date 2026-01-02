"""Münster KP Yield Analysis

Option A: Use ONLY Münster-specific sources (by filename patterns).
Excludes MASTER_* documents from frequency counting.

Outputs:
- _OUTPUT/yield_muenster/yield_topics.csv + .json
- _OUTPUT/yield_muenster/yield_question_patterns.csv + .json
- _OUTPUT/yield_muenster/trend_2024_to_2025.csv + .json
- _OUTPUT/yield_muenster/yield_topics_2025_only.csv + .json

Notes:
- This is a heuristic NLP/statistics pipeline (German text).
- It is designed to be robust across multiple semi-structured sources.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


RECENCY_WEIGHTS_DEFAULT = {
    2025: 1.00,
    2024: 0.55,
    2023: 0.30,
    2022: 0.17,
    2021: 0.10,
    2020: 0.06,
}


MUNSTER_NAME_KEYS = [
    "münster",
    "muenster",
    "kp münster",
    "kp_muenster",
    "protokolle_kp_muenster",
    "kp muenster",
]


DATE_PATTERNS = [
    # 26.03.2025
    re.compile(r"\b(?P<d>\d{1,2})\.(?P<m>\d{1,2})\.(?P<y>20\d{2})\b"),
    # 2025-03-26
    re.compile(r"\b(?P<y>20\d{2})-(?P<m>\d{1,2})-(?P<d>\d{1,2})\b"),
]


STOPWORDS_DE = {
    # German function words

    "der",
    "die",
    "das",
    "und",
    "oder",
    "aber",
    "ich",
    "wir",
    "sie",
    "er",
    "es",
    "ein",
    "eine",
    "einer",
    "eines",
    "einem",
    "den",
    "dem",
    "des",
    "zu",
    "zum",
    "zur",
    "mit",
    "auf",
    "in",
    "im",
    "am",
    "an",
    "von",
    "für",
    "fuer",
    "bei",
    "dass",
    "daß",
    "auch",
    "nicht",
    "nur",
    "noch",
    "wie",
    "was",
    "war",
    "ist",
    "sind",
    "sein",
    "hat",
    "haben",
    "wurde",
    "werden",
    "kann",
    "können",
    "koennen",
    "soll",
    "sollen",
    "würde",
    "wuerde",
    "man",
    "mir",
    "mich",
    "ihm",
    "ihr",
    "ihre",
    "ihren",
    "ihres",
    "ihnen",
    "dann",
    "danach",
    "jetzt",
    "schon",
    "sehr",
    "mehr",
    "weniger",
    "ganz",
    "mal",
    "bitte",
    "ok",
    "okay",
    # very frequent but non-topic exam narration words
    "teil",
    "prüfer",
    "pruefer",
    "patient",
    "patientin",
    "fall",
    "thema",
    "diagnose",
    "verdacht",
    "verdachtsdiagnose",
    "symptom",
    "symptome",
    "befund",
    "befunde",
    "komplikation",
    "komplikationen",
    "therapie",
    "diagnostik",
    "anamnese",
    "untersuchung",
    "kommission",
    "fragen",
    "frage",
    "antwort",
    "antworten",
    "machen",
    "weiter",
    "gehen",
    "vorgehen",
    "zeigen",
    "sagen",
    "nennen",
    "wissen",
    "bekommen",
    "kommt",
    "habe",
    "hatte",
    "hatten",
    "wollte",
    "wollten",
    "wurde",
    "waren",
    "war",
}


TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]{2,}")


@dataclass
class TextDoc:
    source_path: str
    year: int | None
    text: str


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_munster_sources(repo_root: Path) -> list[Path]:
    cands: list[Path] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        name = p.name.lower()
        if any(k in name for k in MUNSTER_NAME_KEYS):
            if p.name.startswith("MASTER_"):
                continue
            if p.suffix.lower() in {".json", ".txt", ".md"}:
                cands.append(p)
    # De-duplicate (same file can appear via weird unicode normalizations)
    uniq = {}
    for p in cands:
        uniq[str(p)] = p
    return sorted(uniq.values())


def detect_year(text: str) -> int | None:
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                y = int(m.group("y"))
                if 2020 <= y <= 2025:
                    return y
            except Exception:
                pass
    # fallback: bare year mention
    m = re.search(r"\b(2020|2021|2022|2023|2024|2025)\b", text)
    if m:
        return int(m.group(1))
    return None


def iter_docs_from_processed_exam_questions(path: Path) -> Iterator[TextDoc]:
    data = json.loads(_safe_read_text(path))
    if not isinstance(data, dict):
        return
    txt = data.get("text")
    if not isinstance(txt, str) or not txt.strip():
        return
    # Split on obvious protocol headers to get better year detection
    chunks = re.split(r"\n(?=Prüfungsprotokoll|Pruefungsprotokoll|Protokoll\s+vom|Teil\s+\d+:)", txt)
    for i, ch in enumerate(chunks):
        ch = ch.strip()
        if len(ch) < 200:
            continue
        year = detect_year(ch)
        yield TextDoc(source_path=str(path), year=year, text=ch)


def iter_docs_from_reports_muenster(path: Path) -> Iterator[TextDoc]:
    data = json.loads(_safe_read_text(path))
    if not isinstance(data, dict):
        return
    reports = data.get("reports")
    if not isinstance(reports, list):
        return
    for rep in reports:
        if not isinstance(rep, dict):
            continue
        # try common keys
        text_parts = []
        for k in ["text", "content", "markdown", "report", "raw"]:
            v = rep.get(k)
            if isinstance(v, str) and v.strip():
                text_parts.append(v)
        if not text_parts:
            # sometimes: {'messages': [...]} -> join
            msgs = rep.get("messages")
            if isinstance(msgs, list):
                for m in msgs:
                    if isinstance(m, str):
                        text_parts.append(m)
                    elif isinstance(m, dict) and isinstance(m.get("text"), str):
                        text_parts.append(m["text"])
        text = "\n".join(text_parts).strip()
        if not text:
            continue
        year = None
        # report may have explicit date/year fields
        for k in ["year", "exam_year"]:
            if isinstance(rep.get(k), int):
                year = rep[k]
        if year is None:
            for k in ["date", "exam_date", "timestamp"]:
                if isinstance(rep.get(k), str):
                    year = detect_year(rep[k])
                    if year:
                        break
        if year is None:
            year = detect_year(text)
        yield TextDoc(source_path=str(path), year=year, text=text)


def iter_docs_from_chunk_json(path: Path) -> Iterator[TextDoc]:
    # Many chunk files are a list with one dict {'type': 'text', 'text': '```json\n[...]'}
    data = json.loads(_safe_read_text(path))
    if not isinstance(data, list) or not data:
        return
    item = data[0]
    if not isinstance(item, dict):
        return
    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return

    # Try to parse inner JSON from fenced block
    inner = None
    m = re.search(r"```json\s*(\[.*\])\s*```", text, flags=re.S)
    if m:
        inner = m.group(1)
    if inner:
        try:
            cases = json.loads(inner)
        except Exception:
            cases = None
        if isinstance(cases, list):
            for c in cases:
                if not isinstance(c, dict):
                    continue
                title = c.get("title")
                # include also chief complaints
                parts = []
                if isinstance(title, str):
                    parts.append(title)
                cc = c.get("chief_complaints")
                if isinstance(cc, list):
                    parts.extend([x for x in cc if isinstance(x, str)])
                text2 = "\n".join(parts).strip()
                if not text2:
                    continue
                # no reliable year per case -> mark None; caller may exclude from weighted yield but useful for vocabulary
                yield TextDoc(source_path=str(path), year=None, text=text2)
        return

    # fallback: treat as plain text
    year = detect_year(text)
    yield TextDoc(source_path=str(path), year=year, text=text)


def iter_docs_from_plaintext(path: Path) -> Iterator[TextDoc]:
    text = _safe_read_text(path)
    if not text.strip():
        return
    # Split into blocks by blank lines; keep larger blocks
    blocks = re.split(r"\n\s*\n+", text)
    for b in blocks:
        b = b.strip()
        if len(b) < 200:
            continue
        year = detect_year(b)
        yield TextDoc(source_path=str(path), year=year, text=b)


def load_munster_docs(repo_root: Path) -> list[TextDoc]:
    docs: list[TextDoc] = []
    sources = find_munster_sources(repo_root)
    for p in sources:
        # exclude MASTER_* and also avoid double-counting by excluding backups
        if "cases_bad_backup" in str(p):
            continue
        if p.name.startswith("MASTER_"):
            continue

        try:
            if p.name.endswith("_processed.json") and "EXAM_QUESTIONS" in str(p):
                docs.extend(list(iter_docs_from_processed_exam_questions(p)))
            elif p.name.startswith("reports_muenster_") and p.suffix.lower() == ".json":
                docs.extend(list(iter_docs_from_reports_muenster(p)))
            elif p.name.startswith("chunk_") and p.suffix.lower() == ".json":
                docs.extend(list(iter_docs_from_chunk_json(p)))
            elif p.suffix.lower() in {".txt", ".md"}:
                docs.extend(list(iter_docs_from_plaintext(p)))
            elif p.suffix.lower() == ".json":
                # generic JSON: try to find text fields by heuristics
                raw = json.loads(_safe_read_text(p))
                if isinstance(raw, dict) and isinstance(raw.get("text"), str):
                    docs.append(TextDoc(source_path=str(p), year=detect_year(raw["text"]), text=raw["text"]))
        except Exception:
            # keep robust: skip problematic files
            continue

    # remove empty and huge duplicates
    cleaned = []
    seen = set()
    for d in docs:
        t = d.text.strip()
        if len(t) < 50:
            continue
        key = (d.year, t[:500])
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(TextDoc(source_path=d.source_path, year=d.year, text=t))
    return cleaned


def normalize_token(token: str) -> str:
    token = token.strip("-_").lower()
    return token


def tokenize(text: str) -> list[str]:
    toks = [normalize_token(t) for t in TOKEN_RE.findall(text)]
    toks = [t for t in toks if t not in STOPWORDS_DE and len(t) >= 3]
    return toks


# Medical signal substrings/keywords to decide whether a token/phrase is likely a real medical topic
MEDICAL_TRIGGERS = [
    "itis",
    "ose",
    "om",
    "karzin",
    "fraktur",
    "infarkt",
    "sepsis",
    "pneumo",
    "embolie",
    "diabetes",
    "thyreo",
    "anäm",
    "anämie",
    "ileus",
    "kolitis",
    "divert",
    "append",
    "pank",
    "mening",
    "myokard",
    "arthritis",
    "insuffizienz",
    "thromb",
    "hyperthy",
    "hypothy",
    "khk",
    "lae",
    "copd",
    "asthma",
    "anaphyl",
    "hws",
    "tetra",
    "mtx",
]

# Allow some generic terms if they are commonly asked as standalone exam topics
MEDICAL_SINGLETON_WHITELIST = {
    "anämie",
    "diabetes",
    "diabetes mellitus",
    "hyperthyreose",
    "hypothyreose",
    "meningitis",
    "myokarditis",
    "herzinsuffizienz",
    "polytrauma",
    "pneumothorax",
    "appendizitis",
    "divertikulitis",
    "cholezystitis",
    "ced",
    "khk",
    "mi",
    "lare",
    "lae",
}


def _looks_medical_phrase(phrase: str) -> bool:
    p = phrase.lower()
    if p in MEDICAL_SINGLETON_WHITELIST:
        return True
    return any(t in p for t in MEDICAL_TRIGGERS)


def extract_topics(text: str) -> list[str]:
    topics: list[str] = []

    # Structured line: "002514b 22.02.2025 Sprunggelenkfraktur"
    for m in re.finditer(r"\b\d{6}[a-z]?\s+\d{2}\.\d{2}\.20\d{2}\s+([^\n\t]{3,120})", text):
        cand = m.group(1).strip(" -\t")
        cand = re.sub(r"\s+", " ", cand)
        if 3 <= len(cand) <= 120:
            topics.append(cand)

    # Markers: "Fall:" "Thema:" "Diagnose:" "Verdacht auf"
    for m in re.finditer(r"(?im)^(?:Fall|Thema|Diagnose|Verdacht(?:sdiagnose)?)\s*[:\-]\s*(.{3,120})$", text):
        cand = m.group(1).strip()
        cand = re.sub(r"\s+", " ", cand)
        topics.append(cand)

    # Frequent medical terms as 1-3 word noun phrases (very heuristic)
    toks = tokenize(text)
    # build bigrams/trigrams to capture e.g. "akute pancreatitis"
    for n in (1, 2, 3):
        for i in range(0, max(0, len(toks) - n + 1)):
            phrase = " ".join(toks[i : i + n])
            # filter overly generic
            if phrase in {"teil", "prüfer", "patient", "patientin", "diagnostik", "therapie"}:
                continue
            # keep if any medical-ish substring
            if _looks_medical_phrase(phrase):
                # reject too-generic single words unless whitelisted
                if n == 1 and phrase not in MEDICAL_SINGLETON_WHITELIST:
                    continue
                topics.append(phrase)

    # Normalize & de-dup + drop meta topics
    META_PREFIXES = (
        "bild ",
        "bild vom",
        "protokoll ",
        "protokoll vom",
        "über ",
        "ueber ",
        "einweisung ",
        "abdomen untersucht",
    )
    META_EXACT = {
        "Bild vom",
        "Protokoll vom",
        "Über anatomie",
        "Einweisung vom",
        "Abdomen untersucht",
    }

    out: list[str] = []
    seen: set[str] = set()
    for t in topics:
        t2 = t.strip().strip("•*- ")
        t2 = re.sub(r"\s+", " ", t2)
        if len(t2) < 4:
            continue
        # drop meta/narration artifacts
        low = t2.lower()
        if t2 in META_EXACT or low.startswith(META_PREFIXES):
            continue
        if low in {"welche komplikationen", "welche komplikation", "prognose", "anatomie"}:
            continue
        # capitalize nicely for output
        if low == t2:
            t2 = t2[0].upper() + t2[1:]
            low = t2.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(t2)
    return out


def extract_question_patterns(text: str) -> list[str]:
    patterns: list[str] = []

    # Questions ending with '?'
    for line in text.splitlines():
        line = line.strip()
        if "?" in line and len(line) <= 180:
            # keep only the question part
            q = line.split("?")[0].strip() + "?"
            q = re.sub(r"\s+", " ", q)
            if len(q) >= 8:
                patterns.append(q)

    # Common request patterns (no '?')
    for m in re.finditer(r"(?i)\b(wie gehen sie vor|was machen sie weiter|diagnostik|therapie|ddx|differentialdiagnosen|klassifikation|leitlinie|indikation|nebenwirkungen)\b.{0,80}", text):
        s = m.group(0)
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) >= 10:
            patterns.append(s)

    # De-dup
    out = []
    seen = set()
    for p in patterns:
        p2 = p.strip()
        if p2.lower() in seen:
            continue
        seen.add(p2.lower())
        out.append(p2)
    return out


def recency_weight(year: int | None, weights: dict[int, float]) -> float:
    if year is None:
        return 0.0
    return float(weights.get(year, 0.0))


def build_yield(
    docs: list[TextDoc],
    weights: dict[int, float],
) -> dict[str, Any]:
    topic_counts_by_year: dict[int, Counter[str]] = defaultdict(Counter)
    topic_weighted: Counter[str] = Counter()

    pattern_counts_by_year: dict[int, Counter[str]] = defaultdict(Counter)
    pattern_weighted: Counter[str] = Counter()

    for d in docs:
        y = d.year
        w = recency_weight(y, weights)
        # topics
        for t in extract_topics(d.text):
            if y is not None:
                topic_counts_by_year[y][t] += 1
            if w > 0:
                topic_weighted[t] += w
        # question patterns
        for p in extract_question_patterns(d.text):
            if y is not None:
                pattern_counts_by_year[y][p] += 1
            if w > 0:
                pattern_weighted[p] += w

    # 2025-only
    topics_2025 = topic_counts_by_year.get(2025, Counter())

    return {
        "topic_counts_by_year": {str(y): dict(c) for y, c in topic_counts_by_year.items()},
        "topic_weighted": dict(topic_weighted),
        "pattern_counts_by_year": {str(y): dict(c) for y, c in pattern_counts_by_year.items()},
        "pattern_weighted": dict(pattern_weighted),
        "topics_2025": dict(topics_2025),
    }


def classify_yield(sorted_items: list[tuple[str, float]]) -> dict[str, str]:
    # percentile-based classification
    n = len(sorted_items)
    if n == 0:
        return {}
    hi_cut = max(1, math.ceil(n * 0.15))
    med_cut = max(hi_cut + 1, math.ceil(n * 0.50))
    out: dict[str, str] = {}
    for i, (k, _v) in enumerate(sorted_items):
        if i < hi_cut:
            out[k] = "HIGH"
        elif i < med_cut:
            out[k] = "MEDIUM"
        else:
            out[k] = "LOW"
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to repo root (default: Medexamenai_migration_full_20251217_204617)",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: <repo-root>/_OUTPUT/yield_muenster)",
    )
    ap.add_argument("--weights", default=None, help="Optional JSON file with year->weight")
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    out_dir = Path(args.out_dir) if args.out_dir else repo_root / "_OUTPUT" / "yield_muenster"

    weights = dict(RECENCY_WEIGHTS_DEFAULT)
    if args.weights:
        w = json.loads(Path(args.weights).read_text(encoding="utf-8"))
        weights = {int(k): float(v) for k, v in w.items()}

    docs = load_munster_docs(repo_root)
    # Filter out docs without year for weighted scoring; but we keep them for vocabulary in the future.
    docs_with_year = [d for d in docs if d.year is not None]

    stats = {
        "docs_total": len(docs),
        "docs_with_year": len(docs_with_year),
        "weights": weights,
    }

    results = build_yield(docs_with_year, weights)

    # Prepare topic tables
    topic_weighted_items = sorted(results["topic_weighted"].items(), key=lambda x: (-x[1], x[0].lower()))
    topic_yield_class = classify_yield(topic_weighted_items)

    topic_rows = []
    for topic, score in topic_weighted_items:
        row = {
            "topic": topic,
            "weighted_score": round(float(score), 4),
            "yield": topic_yield_class.get(topic, ""),
        }
        for y in sorted(RECENCY_WEIGHTS_DEFAULT.keys()):
            row[str(y)] = results["topic_counts_by_year"].get(str(y), {}).get(topic, 0)
        topic_rows.append(row)

    # 2025-only
    topics_2025_items = sorted(results["topics_2025"].items(), key=lambda x: (-x[1], x[0].lower()))
    topics_2025_rows = [
        {"topic": t, "count_2025": c}
        for t, c in topics_2025_items
    ]

    # Question patterns
    pattern_items = sorted(results["pattern_weighted"].items(), key=lambda x: (-x[1], x[0].lower()))
    pattern_yield_class = classify_yield(pattern_items)

    pattern_rows = []
    for pat, score in pattern_items:
        row = {
            "pattern": pat,
            "weighted_score": round(float(score), 4),
            "yield": pattern_yield_class.get(pat, ""),
        }
        for y in sorted(RECENCY_WEIGHTS_DEFAULT.keys()):
            row[str(y)] = results["pattern_counts_by_year"].get(str(y), {}).get(pat, 0)
        pattern_rows.append(row)

    # Trend 2024->2025 (topics)
    c24 = Counter(results["topic_counts_by_year"].get("2024", {}))
    c25 = Counter(results["topic_counts_by_year"].get("2025", {}))
    all_topics = set(c24) | set(c25)
    trend_rows = []
    for t in sorted(all_topics):
        a = c24.get(t, 0)
        b = c25.get(t, 0)
        # simple delta and ratio
        ratio = (b + 1) / (a + 1)
        trend_rows.append(
            {
                "topic": t,
                "count_2024": a,
                "count_2025": b,
                "delta": b - a,
                "ratio_2025_to_2024": round(ratio, 4),
            }
        )
    trend_rows.sort(key=lambda r: (-r["delta"], -r["ratio_2025_to_2024"], r["topic"].lower()))

    # Write outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_metadata.json").write_text(
        json.dumps({"stats": stats}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_csv(
        out_dir / "yield_topics.csv",
        topic_rows,
        fieldnames=["topic", "yield", "weighted_score", "2020", "2021", "2022", "2023", "2024", "2025"],
    )
    (out_dir / "yield_topics.json").write_text(json.dumps(topic_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    write_csv(out_dir / "yield_topics_2025_only.csv", topics_2025_rows, fieldnames=["topic", "count_2025"])
    (out_dir / "yield_topics_2025_only.json").write_text(
        json.dumps(topics_2025_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_csv(
        out_dir / "yield_question_patterns.csv",
        pattern_rows,
        fieldnames=["pattern", "yield", "weighted_score", "2020", "2021", "2022", "2023", "2024", "2025"],
    )
    (out_dir / "yield_question_patterns.json").write_text(
        json.dumps(pattern_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_csv(
        out_dir / "trend_2024_to_2025.csv",
        trend_rows,
        fieldnames=["topic", "count_2024", "count_2025", "delta", "ratio_2025_to_2024"],
    )
    (out_dir / "trend_2024_to_2025.json").write_text(
        json.dumps(trend_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Print quick summary
    print("Docs total:", stats["docs_total"], "with year:", stats["docs_with_year"])
    print("Top 20 topics (weighted):")
    for t, s in topic_weighted_items[:20]:
        print(f"- {t}: {s:.2f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
