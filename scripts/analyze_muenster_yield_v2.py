"""Münster KP Yield Analysis v2

Getrennte Scores:
- asked_score: Nur Münster-Prüfungsquellen (was wurde wirklich gefragt?)
- coverage_score: Münster-bezogene Lern-/Notizquellen (was ist im Repo abgedeckt?)
- gap_priority: High asked_score aber niedrige coverage_score → Priorität fürs Lernen

Outputs:
- _OUTPUT/yield_muenster_v2/asked_yield_topics.csv + .json
- _OUTPUT/yield_muenster_v2/asked_yield_patterns.csv + .json
- _OUTPUT/yield_muenster_v2/coverage_topics.csv + .json
- _OUTPUT/yield_muenster_v2/gap_priority.csv + .json
- _OUTPUT/yield_muenster_v2/trend_2024_to_2025.csv + .json
- _OUTPUT/yield_muenster_v2/report_muenster_yield.md

Notes:
- NLP-Normalisierung mit Synonym-Mapping, Domain-Labels
- 2025-lastige Recency-Gewichtung
- Excludes MASTER_* documents from frequency counting
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime, timezone
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

# --- Gap single source of truth (SSoT) ---
# Keep the gap schema stable across runs.
GAP_FORMULA_ID = "asked_minus_coverage"
GAP_DEFINITION_TEXT = "gap = asked_score - coverage_score"
GAP_SCHEMA_VERSION = 1


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
    "der", "die", "das", "und", "oder", "aber", "ich", "wir", "sie", "er", "es",
    "ein", "eine", "einer", "eines", "einem", "den", "dem", "des",
    "zu", "zum", "zur", "mit", "auf", "in", "im", "am", "an", "von", "für", "fuer", "bei",
    "dass", "daß", "auch", "nicht", "nur", "noch", "wie", "was", "war", "ist", "sind", "sein",
    "hat", "haben", "wurde", "werden", "kann", "können", "koennen", "soll", "sollen",
    "würde", "wuerde", "man", "mir", "mich", "ihm", "ihr", "ihre", "ihren", "ihres", "ihnen",
    "dann", "danach", "jetzt", "schon", "sehr", "mehr", "weniger", "ganz", "mal", "bitte", "ok", "okay",
    # Exam narration words
    "teil", "prüfer", "pruefer", "patient", "patientin", "fall", "thema",
    "diagnose", "verdacht", "verdachtsdiagnose", "symptom", "symptome",
    "befund", "befunde", "komplikation", "komplikationen", "therapie", "diagnostik",
    "anamnese", "untersuchung", "kommission", "fragen", "frage", "antwort", "antworten",
    "machen", "weiter", "gehen", "vorgehen", "zeigen", "sagen", "nennen", "wissen",
    "bekommen", "kommt", "habe", "hatte", "hatten", "wollte", "wollten", "wurde", "waren", "war",
}


TOKEN_RE = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß\-]{2,}")


# Synonym-Mapping für Normalisierung
SYNONYM_MAP = {
    # --- Canonical topic merges ---
    # Pulmo
    "lungenembolie": "lungenarterienembolie",
    "pe": "lungenarterienembolie",
    "lae": "lungenarterienembolie",
    "lare": "lungenarterienembolie",
    "lungenarterienembolie": "lungenarterienembolie",

    # Cardio
    "mi": "myokardinfarkt",
    "myokardinfarkt": "myokardinfarkt",
    "vhf": "vorhofflimmern",
    "vorhofflimmern": "vorhofflimmern",

    # KHK/ACS merged bucket
    "khk": "khk/acs",
    "koronare herzkrankheit": "khk/acs",
    "acs": "khk/acs",
    "akutes koronarsyndrom": "khk/acs",

    # Resp
    "copd": "chronisch obstruktive lungenerkrankung",

    # GI/Immun
    "ced": "chronisch entzündliche darmerkrankung",
    "morbus crohn": "morbus crohn",

    # Law/pharm cross-cutting
    "btm": "btm (verschreibung)",
    "betäubungsmittel": "btm (verschreibung)",

    # Diagnostics
    "ekg": "elektrokardiogramm",

    # Scores / classifications
    "crb-65": "crb65",
    "curb-65": "curb65",
    "nyha": "nyha",
    "gold": "gold (copd)",
    "ao-klassifikation": "ao",
    "garden": "garden-klassifikation",
    "pauwels": "pauwels-klassifikation",
    "forrest": "forrest-klassifikation",
    "fontaine": "fontaine-klassifikation",
    "wagner": "wagner-klassifikation",

    # Meds (kept as-is)
    "mtx": "methotrexat",
    "ace": "ace-hemmer",
    "sartane": "at1-antagonisten",

    # Anatomy abbreviations
    "hws": "halswirbelsäule",
    "bws": "brustwirbelsäule",
    "lws": "lendenwirbelsäule",

    # Vascular
    "pavk": "periphere arterielle verschlusskrankheit",
    "tvt": "tiefe venenthrombose",
    "lufu": "lungenfunktion",
}


# Domain-Labels für Topics
DOMAIN_KEYWORDS = {
    "strahlenschutz": ["strahlenschutz", "dosimeter", "kontrollbereich", "sperrbereich", "mSv", "röntgen", "ionisierend"],
    "rechtsmedizin": ["rechtsmedizin", "leichenschau", "todesursache", "obduktion"],
    "recht": ["§630", "bgb", "aufklärung", "schweigepflicht", "patientenverfügung", "mutmaßlicher wille", "§218", "transplantation", "hirntod"],
    "pharmakologie": ["pharmakologie", "wirkmechanismus", "dosierung", "nebenwirkung", "indikation", "kontraindikation", "metformin", "thiamazol", "methotrexat", "adrenalin", "propofol", "opioide", "btm"],
    "notfall": ["notfall", "anaphylaxie", "abcde", "reanimation", "verbrennung", "tourniquet", "intraossär"],
    "chirurgie": ["chirurgie", "appendektomie", "cholezystektomie", "laparoskopie", "trokar", "osteosynthese", "fraktur", "kompartmentsyndrom"],
    "orthopädie": ["orthopädie", "fraktur", "luxation", "distorsion", "bandverletzung", "ao-klassifikation", "garden", "pauwels"],
    "innere": ["innere", "kardiologie", "pneumologie", "gastroenterologie", "endokrinologie", "nephrologie", "hämatologie", "infektologie"],
    "kardiologie": ["kardiologie", "herzinsuffizienz", "ekg", "infarkt", "vorhofflimmern", "nyha", "ace-hemmer", "betablocker"],
    "pneumologie": ["pneumologie", "pneumonie", "copd", "asthma", "crb-65", "gold"],
    "gastroenterologie": ["gastroenterologie", "hepatitis", "cholezystitis", "appendizitis", "divertikulitis", "ced", "h. pylori"],
    "endokrinologie": ["endokrinologie", "diabetes", "hyperthyreose", "hypothyreose", "cushing", "conn", "phäochromozytom"],
}


def normalize_synonym(term: str) -> str:
    """Normalize a term using explicit synonym mapping.

    IMPORTANT: We avoid substring matching (too many false positives like 'röntgenbild vom').
    """
    low = term.lower().strip()
    low = re.sub(r"\s+", " ", low)
    # direct mapping (exact)
    mapped = SYNONYM_MAP.get(low)
    if mapped is not None:
        return mapped
    # token-level mapping: map acronyms if the whole token matches
    tokens = low.split(" ")
    tokens2 = [SYNONYM_MAP.get(t, t) for t in tokens]
    return " ".join(tokens2)


def detect_domain(topic: str) -> list[str]:
    """Erkennt Domain(s) für ein Topic."""
    low = topic.lower()
    domains = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in low for kw in keywords):
            domains.append(domain)
    return domains if domains else ["unbekannt"]


@dataclass
class TextDoc:
    source_path: str
    year: int | None
    text: str
    source_type: str = "unknown"  # "asked" or "coverage"


def _safe_read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_asked_sources(repo_root: Path) -> list[Path]:
    """Findet Quellen für asked_score (Protokolle/Telegram-Reports)."""
    cands: list[Path] = []
    
    # Telegram-Reports
    tg_dir = repo_root / "_GOLD_STANDARD" / "telegram_reports_muenster"
    if tg_dir.exists():
        for p in tg_dir.glob("reports_muenster_*.json"):
            if not p.name.endswith("__new_questions.json"):  # Exclude derived files
                cands.append(p)
    
    # Gold-Standard Protokolle (TXT aus temp_batch_1)
    proc_dir = repo_root / "_PROCESSING" / "temp_batch_1"
    if proc_dir.exists():
        for p in proc_dir.glob("*.txt"):
            name_low = p.name.lower()
            # Nur Münster-Protokolle
            if any(k in name_low for k in MUNSTER_NAME_KEYS):
                if not p.name.startswith("MASTER_"):
                    cands.append(p)
    
    # Auch direkt aus _GOLD_STANDARD
    gold_dir = repo_root / "_GOLD_STANDARD"
    if gold_dir.exists():
        for p in gold_dir.rglob("*.txt"):
            name_low = p.name.lower()
            if any(k in name_low for k in MUNSTER_NAME_KEYS):
                if not p.name.startswith("MASTER_"):
                    cands.append(p)
    
    # Deduplicate
    uniq = {}
    for p in cands:
        uniq[str(p)] = p
    return sorted(uniq.values())


def find_coverage_sources(repo_root: Path) -> list[Path]:
    """Findet Quellen für coverage_score (Lern-/Notizquellen)."""
    cands: list[Path] = []
    
    # Münster Notes aus _DERIVED_CHUNKS
    notes_dir = repo_root / "_DERIVED_CHUNKS" / "KP Münster 2020 -2025"
    if notes_dir.exists():
        for p in notes_dir.rglob("*.md"):
            if not p.name.startswith("MASTER_"):
                cands.append(p)
    
    # Deduplicate
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


def _fallback_year_from_filename(path: Path) -> int | None:
    m = re.search(r"\b(2020|2021|2022|2023|2024|2025)\b", path.name)
    return int(m.group(1)) if m else None


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
        text_parts = []
        for k in ["raw_text", "text", "content", "markdown", "report"]:
            v = rep.get(k)
            if isinstance(v, str) and v.strip():
                text_parts.append(v)
        if not text_parts:
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
        if year is None:
            year = _fallback_year_from_filename(path)
        yield TextDoc(source_path=str(path), year=year, text=text, source_type="asked")


def _fallback_year_from_path(path: Path) -> int | None:
    m = re.search(r"\b(2020|2021|2022|2023|2024|2025)\b", str(path))
    return int(m.group(1)) if m else None


def _find_year_anchors_in_text(text: str) -> list[tuple[int, int]]:
    """
    Findet Jahr-Ankerzeilen im Format: \\d{6}[a-z]?\\s+\\d{2}\\.\\d{2}\\.(20\\d{2})
    Returns: Liste von (line_number, year) Tuples, sortiert nach Zeilennummer
    """
    anchors: list[tuple[int, int]] = []
    # Pattern für Ankerzeilen: 6-stellige ID, optionaler Buchstabe, Leerzeichen, Datum
    anchor_pattern = re.compile(r"^\d{6}[a-z]?\s+\d{2}\.\d{2}\.(20\d{2})", re.MULTILINE)
    
    for match in anchor_pattern.finditer(text):
        line_start = text[:match.start()].count('\n')
        year = int(match.group(1))
        if 2020 <= year <= 2025:
            anchors.append((line_start, year))
    
    # Sortiere nach Zeilennummer
    anchors.sort(key=lambda x: x[0])
    return anchors


def iter_docs_from_ord_file(path: Path, source_type: str = "asked") -> Iterator[TextDoc]:
    """
    Spezialisierte Funktion für ORD-Dateien (*_2020-2025_ORD.txt).
    Verwendet Jahr-Ankerzeilen für bessere Year-Inference.
    Returns: Iterator von TextDoc (Stats werden separat in load_asked_docs getrackt)
    """
    text = _safe_read_text(path)
    if not text.strip():
        return
    
    # Finde alle Jahr-Ankerzeilen
    anchors = _find_year_anchors_in_text(text)
    anchor_by_line = {line_num: year for line_num, year in anchors}
    
    # Split into blocks by blank lines
    blocks = re.split(r"\n\s*\n+", text)
    current_anchor_year: int | None = None
    
    for b in blocks:
        b = b.strip()
        if len(b) < 200:
            continue
        
        # Finde die Zeilennummer dieses Blocks im Originaltext
        block_start_in_text = text.find(b)
        if block_start_in_text == -1:
            continue
        block_start_line = text[:block_start_in_text].count('\n')
        
        # Prüfe ob dieser Block direkt ein Jahr hat
        year = detect_year(b)
        if year:
            current_anchor_year = year  # Update anchor für nachfolgende Blöcke
        else:
            # Suche nach dem letzten Anker vor diesem Block
            nearest_anchor_year = None
            for anchor_line, anchor_year in anchors:
                if anchor_line <= block_start_line:
                    nearest_anchor_year = anchor_year
                else:
                    break
            
            if nearest_anchor_year:
                year = nearest_anchor_year
                current_anchor_year = nearest_anchor_year
            else:
                # Fallback: verwende current_anchor_year wenn vorhanden
                if current_anchor_year:
                    year = current_anchor_year
                else:
                    # Fallback aus Filename (nur wenn einzelnes Jahr im Namen)
                    fallback_year = _fallback_year_from_path(path)
                    if fallback_year and ("2023" in path.name or "2024" in path.name or "2025" in path.name):
                        year = fallback_year
                    else:
                        year = None
        
        yield TextDoc(source_path=str(path), year=year, text=b, source_type=source_type)


def iter_docs_from_plaintext(path: Path, source_type: str = "asked") -> Iterator[TextDoc]:
    """
    Standard-Funktion für Plaintext-Dateien.
    Für ORD-Dateien wird iter_docs_from_ord_file verwendet.
    """
    # Prüfe ob es eine ORD-Datei ist
    if "_2020-2025_ORD" in path.name or path.name.endswith("_ORD.txt"):
        # Verwende spezialisierte ORD-Funktion
        for doc in iter_docs_from_ord_file(path, source_type):
            yield doc
        return
    
    text = _safe_read_text(path)
    if not text.strip():
        return
    fallback_year = _fallback_year_from_path(path)
    # Split into blocks by blank lines; keep larger blocks
    blocks = re.split(r"\n\s*\n+", text)
    for b in blocks:
        b = b.strip()
        if len(b) < 200:
            continue
        year = detect_year(b) or fallback_year
        yield TextDoc(source_path=str(path), year=year, text=b, source_type=source_type)


def load_asked_docs(repo_root: Path) -> tuple[list[TextDoc], dict[str, Any]]:
    """
    Lädt Dokumente für asked_score.
    Returns: (docs, year_inference_stats)
    """
    docs: list[TextDoc] = []
    sources = find_asked_sources(repo_root)
    
    year_inference_stats: dict[str, Any] = {
        "year_fallback_hits_total": 0,
        "year_fallback_hits_by_source": {},
        "year_anchor_based_inference": 0,
        "year_direct_detection": 0,
        "ord_file_stats": {},
    }
    
    for p in sources:
        if "cases_bad_backup" in str(p):
            continue
        if p.name.startswith("MASTER_"):
            continue
        
        try:
            if p.name.startswith("reports_muenster_") and p.suffix.lower() == ".json":
                for doc in iter_docs_from_reports_muenster(p):
                    docs.append(doc)
                    if doc.year is not None:
                        year_inference_stats["year_direct_detection"] += 1
            elif p.suffix.lower() == ".txt":
                # Prüfe ob ORD-Datei
                if "_2020-2025_ORD" in p.name or p.name.endswith("_ORD.txt"):
                    # Verwende spezialisierte ORD-Funktion
                    file_stats = {
                        "total_blocks": 0,
                        "blocks_with_direct_year": 0,
                        "blocks_with_anchor_year": 0,
                        "blocks_without_year": 0,
                    }
                    for doc in iter_docs_from_ord_file(p, source_type="asked"):
                        docs.append(doc)
                        file_stats["total_blocks"] += 1
                        if doc.year is not None:
                            # Prüfe ob Jahr direkt im Block gefunden wurde
                            if detect_year(doc.text):
                                file_stats["blocks_with_direct_year"] += 1
                                year_inference_stats["year_direct_detection"] += 1
                            else:
                                file_stats["blocks_with_anchor_year"] += 1
                                year_inference_stats["year_anchor_based_inference"] += 1
                        else:
                            file_stats["blocks_without_year"] += 1
                            year_inference_stats["year_fallback_hits_total"] += 1
                    
                    year_inference_stats["ord_file_stats"][p.name] = file_stats
                    year_inference_stats["year_fallback_hits_by_source"][p.name] = file_stats["blocks_with_anchor_year"]
                else:
                    # Standard Plaintext-Verarbeitung
                    for doc in iter_docs_from_plaintext(p, source_type="asked"):
                        docs.append(doc)
                        if doc.year is not None:
                            year_inference_stats["year_direct_detection"] += 1
                        else:
                            year_inference_stats["year_fallback_hits_total"] += 1
                            year_inference_stats["year_fallback_hits_by_source"][p.name] = \
                                year_inference_stats["year_fallback_hits_by_source"].get(p.name, 0) + 1
        except Exception:
            pass

    # Deduplicate
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
        cleaned.append(d)
    
    return cleaned, year_inference_stats


def load_coverage_docs(repo_root: Path) -> list[TextDoc]:
    """Lädt Dokumente für coverage_score."""
    docs: list[TextDoc] = []
    sources = find_coverage_sources(repo_root)
    
    for p in sources:
        if p.name.startswith("MASTER_"):
            continue
        
        try:
            if p.suffix.lower() == ".md":
                docs.extend(list(iter_docs_from_plaintext(p, source_type="coverage")))
        except Exception:
            continue
    
    # Deduplicate
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
        cleaned.append(d)
    return cleaned


def normalize_token(token: str) -> str:
    token = token.strip("-_").lower()
    return token


def tokenize(text: str) -> list[str]:
    toks = [normalize_token(t) for t in TOKEN_RE.findall(text)]
    toks = [t for t in toks if t not in STOPWORDS_DE and len(t) >= 3]
    return toks


MEDICAL_TRIGGERS = [
    "itis", "ose", "om", "karzin", "fraktur", "infarkt", "sepsis", "pneumo", "embolie",
    "diabetes", "thyreo", "anäm", "anämie", "ileus", "kolitis", "divert", "append",
    "pank", "mening", "myokard", "arthritis", "insuffizienz", "thromb", "hyperthy",
    "hypothy", "khk", "lae", "copd", "asthma", "anaphyl", "hws", "tetra", "mtx",
    "strahlenschutz", "dosimeter", "röntgen", "rechtsmedizin", "pharmakologie",
    "methotrexat", "adrenalin", "propofol", "btm", "verbrennung", "anaphylaxie",
]


MEDICAL_SINGLETON_WHITELIST = {
    "anämie", "diabetes", "diabetes mellitus", "hyperthyreose", "hypothyreose",
    "meningitis", "myokarditis", "herzinsuffizienz", "polytrauma", "pneumothorax",
    "appendizitis", "divertikulitis", "cholezystitis", "ced", "khk", "mi", "lare", "lae",
    "strahlenschutz", "rechtsmedizin", "pharmakologie", "anaphylaxie",
}


def _looks_medical_phrase(phrase: str) -> bool:
    p = phrase.lower()
    if p in MEDICAL_SINGLETON_WHITELIST:
        return True
    return any(t in p for t in MEDICAL_TRIGGERS)


META_TOPIC_RE = re.compile(
    r"(?i)\b(r\u00f6ntgenbild|roentgenbild|bild\s+gezeigt|bild\s+vom|zeigte\s+r\u00f6ntgenbild|beschreibung\s+r\u00f6ntgen|bildbeschreibung|bilder\s+gezeigt)\b"
)
RONTGEN_THORAX_RE = re.compile(r"(?i)\br\u00f6ntgen(?:\s*[- ]?thorax|\s+thorax)\b")


SCORE_TOKENS = {
    "wells",
    "wells-score",
    "geneva",
    "geneva-score",
    "crb65",
    "crb-65",
    "curb65",
    "curb-65",
    "nyha",
    "gold",
}

GLUE_TOKENS = {
    "kurz",
    "alles",
    "erzählt",
    "erzaehlt",
    "statt",
    "zwischen",
    "täglich",
    "taeglich",
    "ging",
    "macht",
    "weiter",
    "über",
    "ueber",
}


def _split_topic_if_score(topic: str) -> list[str]:
    toks = [t for t in re.split(r"\s+", topic.lower()) if t]
    if not toks:
        return []
    if any(t in GLUE_TOKENS for t in toks):
        return []
    # If we see a score token mixed into a topic phrase, split it out.
    scores = [t for t in toks if t in SCORE_TOKENS]
    if not scores:
        return [topic]
    rest = [t for t in toks if t not in SCORE_TOKENS]
    out = []
    if rest:
        out.append(" ".join(rest))
    for s in scores:
        out.append(s)
    return out


def extract_topics(text: str) -> list[str]:
    topics: list[str] = []

    # Normalize 'Röntgen Thorax' procedure to a single canonical topic
    if RONTGEN_THORAX_RE.search(text):
        topics.append("Röntgen-Thorax")
    
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
    
    # Frequent medical terms as 1-3 word noun phrases
    toks = tokenize(text)
    for n in (1, 2, 3):
        for i in range(0, max(0, len(toks) - n + 1)):
            phrase = " ".join(toks[i : i + n])
            if phrase in {"teil", "prüfer", "pruefer", "patient", "patientin", "diagnostik", "therapie"}:
                continue
            if _looks_medical_phrase(phrase):
                if n == 1 and phrase not in MEDICAL_SINGLETON_WHITELIST:
                    continue
                topics.append(phrase)

    # Normalize & de-dup + drop meta topics
    META_PREFIXES = (
        "bild ", "bild vom", "protokoll ", "protokoll vom", "über ", "ueber ",
        "einweisung ", "abdomen untersucht",
    )
    META_EXACT = {
        "Bild vom", "Protokoll vom", "Über anatomie", "Einweisung vom", "Abdomen untersucht",
    }
    
    out: list[str] = []
    seen: set[str] = set()
    for t in topics:
        t2 = t.strip().strip("•*- ")
        t2 = re.sub(r"\s+", " ", t2)
        if len(t2) < 4:
            continue
        low = t2.lower()
        if t2 in META_EXACT or low.startswith(META_PREFIXES):
            continue
        if low in {"welche komplikationen", "welche komplikation", "prognose", "anatomie"}:
                continue
        # Drop image narration topics aggressively
        if META_TOPIC_RE.search(t2):
            continue
        if any(k in low for k in ["röntgenbild", "roentgenbild", "bild gezeigt", "bild vom", "beschreibung röntgen", "bildbeschreibung", "bilder gezeigt"]):
            continue
        # Split out score tokens and drop glue/narration composites
        split_candidates = _split_topic_if_score(t2)
        if not split_candidates:
            continue
        # We process each candidate separately below.
        for cand in split_candidates:
            # Normalize via synonym mapping
            t2_normalized = normalize_synonym(cand)
            t2 = t2_normalized
            low = t2.lower()
            # De-duplicate repeated words
            t2 = re.sub(r"(?i)\b([a-zäöüß]{3,})\s+\1\b", r"\1", t2)
            low = t2.lower()
            # Capitalize nicely
            if low == t2:
                t2 = t2[0].upper() + t2[1:] if t2 else t2
                low = t2.lower()
            if low in seen:
                continue
            seen.add(low)
            out.append(t2)
        continue

        # Normalize via synonym mapping
        t2_normalized = normalize_synonym(t2)
        if t2_normalized != t2:
            t2 = t2_normalized
            low = t2.lower()
        # De-duplicate repeated words (e.g. 'rechtsmedizin rechtsmedizin')
        t2 = re.sub(r"(?i)\b([a-zäöüß]{3,})\s+\1\b", r"\1", t2)
        low = t2.lower()
        # Capitalize nicely
        if low == t2:
            t2 = t2[0].upper() + t2[1:] if t2 else t2
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
            q = line.split("?")[0].strip() + "?"
            q = re.sub(r"\s+", " ", q)
            if len(q) >= 8:
                patterns.append(q)
    
    # Common request patterns
    for m in re.finditer(r"(?i)\b(wie gehen sie vor|was machen sie weiter|diagnostik|therapie|ddx|differentialdiagnosen|klassifikation|leitlinie|indikation|nebenwirkungen|dosierung|strahlenschutz|kontrollbereich|sperrbereich|§630|aufklärung)\b.{0,80}", text):
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
    score_type: str = "asked",
) -> dict[str, Any]:
    """Baut Yield-Statistik auf. score_type: 'asked' oder 'coverage'."""
    topic_counts_by_year: dict[int, Counter[str]] = defaultdict(Counter)
    topic_weighted: Counter[str] = Counter()
    topic_domains: defaultdict[str, set[str]] = defaultdict(set)
    
    pattern_counts_by_year: dict[int, Counter[str]] = defaultdict(Counter)
    pattern_weighted: Counter[str] = Counter()
    
    for d in docs:
        y = d.year
        w = recency_weight(y, weights) if score_type == "asked" else 1.0  # coverage: keine Jahr-Gewichtung
        
        for t in extract_topics(d.text):
            # Normalize topic
            t_norm = normalize_synonym(t)
            domains = detect_domain(t_norm)
            
            if y is not None:
                topic_counts_by_year[y][t_norm] += 1
            if w > 0:
                topic_weighted[t_norm] += w
            topic_domains[t_norm].update(domains)
        
        for p in extract_question_patterns(d.text):
            if y is not None:
                pattern_counts_by_year[y][p] += 1
            if w > 0:
                pattern_weighted[p] += w
    
    # 2025-only (nur für asked_score relevant)
    topics_2025 = topic_counts_by_year.get(2025, Counter()) if score_type == "asked" else Counter()
    
    return {
        "topic_counts_by_year": {str(y): dict(c) for y, c in topic_counts_by_year.items()},
        "topic_weighted": dict(topic_weighted),
        "topic_domains": {k: list(v) for k, v in topic_domains.items()},
        "pattern_counts_by_year": {str(y): dict(c) for y, c in pattern_counts_by_year.items()},
        "pattern_weighted": dict(pattern_weighted),
        "topics_2025": dict(topics_2025),
    }


def classify_yield(sorted_items: list[tuple[str, float]]) -> dict[str, str]:
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


def compute_gap_priority(
    asked_scores: dict[str, float],
    coverage_scores: dict[str, float],
) -> list[dict[str, Any]]:
    """Compute gap priority using the central gap SSoT.

    SSoT:
      - formula_id: GAP_FORMULA_ID
      - definition: GAP_DEFINITION_TEXT
      - schema_version: GAP_SCHEMA_VERSION

    Output schema (stable):
      topic, asked_score, coverage_score, gap, priority
    """
    gap_rows: list[dict[str, Any]] = []
    for topic, asked_score in asked_scores.items():
        if asked_score <= 0:
            continue
        coverage_score = coverage_scores.get(topic, 0.0)
        # SSoT formula
        gap = asked_score - coverage_score

        gap_rows.append(
            {
                "topic": topic,
                "asked_score": round(float(asked_score), 4),
                "coverage_score": round(float(coverage_score), 4),
                "gap": round(float(gap), 4),
                "priority": "HIGH" if gap > asked_score * 0.5 else "MEDIUM" if gap > 0 else "LOW",
            }
        )

    gap_rows.sort(key=lambda r: (-r["gap"], -r["asked_score"], r["topic"].lower()))
    return gap_rows


def write_learning_checklist(
    out_path: Path,
    run_timestamp: str,
    gap_meta: dict[str, Any],
    asked_results: dict[str, Any],
    gap_rows: list[dict[str, Any]],
) -> None:
    """Write a reproducible learning checklist derived from in-memory results.

    Must not depend on gap_priority.csv schema.
    """

    # counts: asked_results["topic_counts_by_year"] has string years
    counts_2025 = asked_results.get("topic_counts_by_year", {}).get("2025", {})
    counts_2024 = asked_results.get("topic_counts_by_year", {}).get("2024", {})
    topic_domains = asked_results.get("topic_domains", {})

    def fmt_item(row: dict[str, Any]) -> str:
        topic = row["topic"]
        asked = row["asked_score"]
        cov = row["coverage_score"]
        gap = row["gap"]
        c25 = counts_2025.get(topic, 0)
        c24 = counts_2024.get(topic, 0)
        return f"[ ] {topic} | asked={asked:.4f} | coverage={cov:.4f} | gap={gap:.4f} | 2025={c25} 2024={c24}"

    # Domain buckets
    cross_domains = ["strahlenschutz", "recht", "rechtsmedizin", "pharmakologie"]
    by_domain: dict[str, list[dict[str, Any]]] = {d: [] for d in cross_domains}
    for r in gap_rows:
        doms = topic_domains.get(r["topic"], [])
        for d in cross_domains:
            if d in doms:
                by_domain[d].append(r)

    # Build file
    lines: list[str] = []
    lines.append("Münster KP – Lern-Checkliste (aus Gap-Prioritäten)")
    lines.append(f"Run timestamp (UTC): {run_timestamp}")
    lines.append(f"Gap formula_id: {gap_meta.get('formula_id')}")
    lines.append(f"Gap definition: {gap_meta.get('definition')}")
    lines.append("Hinweis: asked_score ist 2025-gewichtet (2025 dominiert).")
    lines.append("")

    lines.append("A) Querschnitt – MUSS SITZEN")
    lines.append("")
    for d in cross_domains:
        rows = sorted(by_domain.get(d, []), key=lambda x: (-x["gap"], -x["asked_score"]))[:10]
        if not rows:
            continue
        lines.append(f"{d.upper()}")
        for r in rows:
            lines.append("  " + fmt_item(r))
        lines.append("")

    # P1 noise filter for section B
    glue_tokens = {"kurz", "alles", "erzählt", "erzaehlt", "statt", "zwischen", "täglich", "taeglich", "ging", "macht", "weiter"}
    def is_noisy_topic(topic: str) -> bool:
        low = topic.lower()
        if any(tok in low.split() for tok in glue_tokens):
            return True
        if " statt " in low or " zwischen " in low or low.startswith("kurz "):
            return True
        return False

    lines.append("B) Klinische Kern-Algorithmen (Top 15 Gap-Ranking)")
    lines.append("")
    core = [r for r in gap_rows if not is_noisy_topic(r["topic"])][:15]
    for r in core:
        lines.append(fmt_item(r))
    lines.append("")

    lines.append("C) Praktische Sub-Checklisten (Querschnitt)")
    lines.append("")
    lines.append("Strahlenschutz: Kontroll-/Sperrbereich, ALARA, Dosisgrenzen, Schwangerschaft, Dokumentation")
    lines.append("Recht: BGB §630ff (Aufklärung/Einwilligung/Doku/Einsicht), Schweigepflicht, Notfall")
    lines.append("Rechtsmedizin: Leichenschau, Todeszeichen, Todesarten, Todesbescheinigung")
    lines.append("Pharmako: Notfallmeds, UAW/CI, BTM-Basics, typische Dosierungen (high-level)")
    lines.append("")

    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def generate_report(
    asked_results: dict[str, Any],
    coverage_results: dict[str, Any],
    gap_rows: list[dict[str, Any]],
    trend_rows: list[dict[str, Any]],
    stats: dict[str, Any],
) -> str:
    """Generiert einen Markdown-Report mit Lernprioritäten."""
    lines = []
    lines.append("# Münster KP Yield-Analyse - Lernprioritäten")
    lines.append("")
    lines.append(f"**Generiert (UTC):** {stats.get('run_timestamp', 'N/A')}")
    lines.append("")
    lines.append("## Zusammenfassung")
    lines.append("")
    lines.append(f"- **Asked-Quellen:** {stats.get('asked_docs_total', 0)} Dokumente")
    lines.append(f"- **Coverage-Quellen:** {stats.get('coverage_docs_total', 0)} Dokumente")
    lines.append("")
    
    # Top 20 High-Yield Topics
    asked_topics = sorted(asked_results["topic_weighted"].items(), key=lambda x: (-x[1], x[0].lower()))[:20]
    lines.append("## Top 20 High-Yield Topics (2025-gewichtet)")
    lines.append("")
    for i, (topic, score) in enumerate(asked_topics, 1):
        domains = asked_results["topic_domains"].get(topic, [])
        domain_str = f" [{', '.join(domains)}]" if domains else ""
        lines.append(f"{i}. **{topic}** (Score: {score:.2f}){domain_str}")
    lines.append("")
    
    # Querschnittsthemen
    lines.append("## Querschnittsthemen (müssen sitzen!)")
    lines.append("")
    cross_cutting = ["strahlenschutz", "rechtsmedizin", "recht", "pharmakologie", "notfall"]
    for domain in cross_cutting:
        domain_topics = [
            (t, s) for t, s in asked_results["topic_weighted"].items()
            if domain in asked_results["topic_domains"].get(t, [])
        ]
        if domain_topics:
            domain_topics.sort(key=lambda x: -x[1])
            lines.append(f"### {domain.capitalize()}")
            for topic, score in domain_topics[:10]:
                lines.append(f"- **{topic}** (Score: {score:.2f})")
            lines.append("")
    
    # Gap-Priority Top 20
    lines.append("## Gap-Priority: Hoch gefragt, aber wenig abgedeckt")
    lines.append("")
    for i, row in enumerate(gap_rows[:20], 1):
        lines.append(f"{i}. **{row['topic']}** (Gap: {row['gap']:.2f}, Asked: {row['asked_score']:.2f}, Coverage: {row['coverage_score']:.2f})")
    lines.append("")
    
    # Trends 2024→2025
    rising = [r for r in trend_rows if r["delta"] > 0][:10]
    if rising:
        lines.append("## Steigende Trends 2024→2025")
        lines.append("")
        for i, row in enumerate(rising, 1):
            lines.append(f"{i}. **{row['topic']}** (+{row['delta']}, Ratio: {row['ratio_2025_to_2024']:.2f})")
        lines.append("")
    
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Path to repo root",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (default: <repo-root>/_OUTPUT/yield_muenster_v2)",
    )
    ap.add_argument("--weights", default=None, help="Optional JSON file with year->weight")
    args = ap.parse_args()

    repo_root = Path(args.repo_root)
    out_dir = Path(args.out_dir) if args.out_dir else repo_root / "_OUTPUT" / "yield_muenster_v2"

    weights = dict(RECENCY_WEIGHTS_DEFAULT)
    if args.weights:
        w = json.loads(Path(args.weights).read_text(encoding="utf-8"))
        weights = {int(k): float(v) for k, v in w.items()}
    
    # Load documents
    print("Loading asked documents...")
    asked_docs, year_inference_stats = load_asked_docs(repo_root)
    asked_docs_with_year = [d for d in asked_docs if d.year is not None]
    
    print("Loading coverage documents...")
    coverage_docs = load_coverage_docs(repo_root)
    
    run_ts = datetime.now(timezone.utc).isoformat()
    stats = {
        "asked_docs_total": len(asked_docs),
        "asked_docs_with_year": len(asked_docs_with_year),
        "coverage_docs_total": len(coverage_docs),
        "weights": weights,
        "run_timestamp": run_ts,
        "year_inference": year_inference_stats,
    }

    gap_meta = {
        "formula_id": GAP_FORMULA_ID,
        "definition": GAP_DEFINITION_TEXT,
        "schema_version": GAP_SCHEMA_VERSION,
    }
    
    # Build yields
    print("Building asked_score...")
    asked_results = build_yield(asked_docs_with_year, weights, score_type="asked")
    
    print("Building coverage_score...")
    coverage_results = build_yield(coverage_docs, weights, score_type="coverage")
    
    # Prepare asked topic tables
    asked_topic_items = sorted(asked_results["topic_weighted"].items(), key=lambda x: (-x[1], x[0].lower()))
    asked_topic_yield_class = classify_yield(asked_topic_items)

    asked_topic_rows = []
    for topic, score in asked_topic_items:
        domains = asked_results["topic_domains"].get(topic, [])
        row = {
            "topic": topic,
            "weighted_score": round(float(score), 4),
            "yield": asked_topic_yield_class.get(topic, ""),
            "domains": ", ".join(domains) if domains else "unbekannt",
        }
        for y in sorted(RECENCY_WEIGHTS_DEFAULT.keys()):
            row[str(y)] = asked_results["topic_counts_by_year"].get(str(y), {}).get(topic, 0)
        asked_topic_rows.append(row)

    # 2025-only
    topics_2025_items = sorted(asked_results["topics_2025"].items(), key=lambda x: (-x[1], x[0].lower()))
    topics_2025_rows = [
        {"topic": t, "count_2025": c}
        for t, c in topics_2025_items
    ]

    # Coverage topic tables
    coverage_topic_items = sorted(coverage_results["topic_weighted"].items(), key=lambda x: (-x[1], x[0].lower()))
    coverage_topic_rows = []
    for topic, score in coverage_topic_items:
        domains = coverage_results["topic_domains"].get(topic, [])
        row = {
                "topic": topic,
            "coverage_score": round(float(score), 4),
            "domains": ", ".join(domains) if domains else "unbekannt",
        }
        coverage_topic_rows.append(row)
    
    # Gap priority
    gap_rows = compute_gap_priority(
        asked_results["topic_weighted"],
        coverage_results["topic_weighted"],
    )
    
    # Question patterns
    asked_pattern_items = sorted(asked_results["pattern_weighted"].items(), key=lambda x: (-x[1], x[0].lower()))
    asked_pattern_yield_class = classify_yield(asked_pattern_items)
    
    asked_pattern_rows = []
    for pat, score in asked_pattern_items:
        row = {
            "pattern": pat,
            "weighted_score": round(float(score), 4),
            "yield": asked_pattern_yield_class.get(pat, ""),
            }
        for y in sorted(RECENCY_WEIGHTS_DEFAULT.keys()):
            row[str(y)] = asked_results["pattern_counts_by_year"].get(str(y), {}).get(pat, 0)
        asked_pattern_rows.append(row)

    # Trend 2024->2025
    c24 = Counter(asked_results["topic_counts_by_year"].get("2024", {}))
    c25 = Counter(asked_results["topic_counts_by_year"].get("2025", {}))
    all_topics = set(c24) | set(c25)
    trend_rows = []
    for t in sorted(all_topics):
        a = c24.get(t, 0)
        b = c25.get(t, 0)
        ratio = (b + 1) / (a + 1)
        trend_rows.append({
                "topic": t,
                "count_2024": a,
                "count_2025": b,
                "delta": b - a,
                "ratio_2025_to_2024": round(ratio, 4),
        })
    trend_rows.sort(key=lambda r: (-r["delta"], -r["ratio_2025_to_2024"], r["topic"].lower()))

    # Write outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_metadata.json").write_text(
        json.dumps({"stats": stats, "gap": gap_meta}, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Asked yield topics
    write_csv(
        out_dir / "asked_yield_topics.csv",
        asked_topic_rows,
        fieldnames=["topic", "yield", "weighted_score", "domains", "2020", "2021", "2022", "2023", "2024", "2025"],
    )
    (out_dir / "asked_yield_topics.json").write_text(
        json.dumps(asked_topic_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2025-only
    write_csv(out_dir / "asked_yield_topics_2025_only.csv", topics_2025_rows, fieldnames=["topic", "count_2025"])
    (out_dir / "asked_yield_topics_2025_only.json").write_text(
        json.dumps(topics_2025_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Coverage topics
    write_csv(
        out_dir / "coverage_topics.csv",
        coverage_topic_rows,
        fieldnames=["topic", "coverage_score", "domains"],
    )
    (out_dir / "coverage_topics.json").write_text(
        json.dumps(coverage_topic_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Gap priority
    write_csv(
        out_dir / "gap_priority.csv",
        gap_rows,
        fieldnames=["topic", "asked_score", "coverage_score", "gap", "priority"],
    )
    (out_dir / "gap_priority.json").write_text(
        json.dumps(gap_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Asked patterns
    write_csv(
        out_dir / "asked_yield_patterns.csv",
        asked_pattern_rows,
        fieldnames=["pattern", "yield", "weighted_score", "2020", "2021", "2022", "2023", "2024", "2025"],
    )
    (out_dir / "asked_yield_patterns.json").write_text(
        json.dumps(asked_pattern_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    
    # Trend
    write_csv(
        out_dir / "trend_2024_to_2025.csv",
        trend_rows,
        fieldnames=["topic", "count_2024", "count_2025", "delta", "ratio_2025_to_2024"],
    )
    (out_dir / "trend_2024_to_2025.json").write_text(
        json.dumps(trend_rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Learning checklist (reproducible, in-memory)
    write_learning_checklist(
        out_dir / "learning_checklist_from_gaps.txt",
        run_timestamp=stats["run_timestamp"],
        gap_meta=gap_meta,
        asked_results=asked_results,
        gap_rows=gap_rows,
    )

    # Report
    report_md = generate_report(asked_results, coverage_results, gap_rows, trend_rows, stats)
    (out_dir / "report_muenster_yield.md").write_text(report_md, encoding="utf-8")
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Asked docs: {stats['asked_docs_total']} (with year: {stats['asked_docs_with_year']})")
    print(f"Coverage docs: {stats['coverage_docs_total']}")
    print(f"\nTop 20 asked topics (weighted):")
    for t, s in asked_topic_items[:20]:
        print(f"  - {t}: {s:.2f}")
    print(f"\nTop 10 gap priority:")
    for row in gap_rows[:10]:
        print(f"  - {row['topic']}: gap={row['gap']:.2f}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
