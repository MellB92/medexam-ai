#!/usr/bin/env python3
"""
Batch-Vorbereitung (v2) für Kontext-Reparatur von Fragen mit generischen Antworten.

Warum v2?
- v1 hat Chunks pro `source` **global gemerged** → hohe Gefahr von Fehlzuordnungen (falsche Diagnose/Kontext).
- v2 macht **Top-K Chunk Selection pro Frage** + speichert `match_confidence` als Quality-Signal.

Guardrails (Projektstandard):
- **Kein Halluzinieren**: `repaired_answer` baut ausschließlich auf extrahiertem Kontext auf (keine Leitlinien-Therapie).
- **Quality-Gate**: Kontext wird nur als `context_found` gesetzt, wenn der Match-Score hoch genug ist
  (oder ein manueller Override existiert).

Input:
- `_OUTPUT/kontext_fehlende_antworten.json`
- `_OUTPUT/evidenz_antworten.json`
- `_DERIVED_CHUNKS/CHUNKS/*.json`

Output (überschreibt):
- `_OUTPUT/batch_repair_input.jsonl`
- `_OUTPUT/batch_repair_instructions.md`
- `_OUTPUT/batch_repair_stats.json`
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Konfiguration
# -----------------------------

# Fragen ohne verwertbare Keywords (z.B. „Und dann?“) sind nicht zuverlässig matchbar.
MIN_KEYWORDS_FOR_MATCH = 2

# Max. Chunks pro Frage (Top-K Ranking)
TOP_K_CHUNKS = 3

# Match-Score Schwellen
SCORE_FOUND_MIN = 0.18
SCORE_PARTIAL_MIN = 0.10

# Manuelle Overrides: Index -> Chunk-Dateinamen (sehr spezifisch!)
MANUAL_CHUNK_OVERRIDES: dict[int, list[str]] = {
    1978: [
        "chunk_Kenntnisprufung Munster Protokolle 2025 new 2.docx_20.json",
        "chunk_Kenntnisprufung .pdf_162.json",
    ],
}


STOPWORDS_DE = {
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "einer",
    "eines",
    "und",
    "oder",
    "aber",
    "sowie",
    "ist",
    "sind",
    "war",
    "waren",
    "sein",
    "zu",
    "zum",
    "zur",
    "im",
    "in",
    "am",
    "an",
    "auf",
    "aus",
    "bei",
    "mit",
    "von",
    "für",
    "dass",
    "ich",
    "du",
    "er",
    "sie",
    "wir",
    "ihr",
    "was",
    "wie",
    "wo",
    "wann",
    "warum",
    "wieso",
    "welche",
    "welcher",
    "welches",
    "bitte",
    "genau",
    "noch",
    "auch",
    "jetzt",
    "dann",
    "zunächst",
    "erst",
    "mal",
    "frage",
    "antwort",
    "patient",
    "patientin",
}


MEDGEMMA_PATTERNS = {
    "bild": [
        r"bild|röntgen|ct|mrt|sono|ekg|ultraschall|radiolog|aufnahme",
        r"foto|abbildung|darstellung|befund.*bild",
    ],
    "dosis": [
        r"\d+\s*(mg|g|ml|µg|iu|einheiten)/\s*(tag|woche|monat|kg|dosis)",
        r"dosierung|dosis|applikation|gabe",
        r"\d+\s*x\s*\d+\s*(mg|g)",
    ],
    "grenzwert": [
        r"grenzwert|normalwert|referenz|cut.?off",
        r"<\s*\d+|>\s*\d+",
        r"über|unter.*(?:grenze|wert)",
    ],
    "klassifikation": [
        r"klassifikation|stadium|grad|typ\s+[ivx]+",
        r"garden|pauwels|ao|forrest|nyha|curb|fontaine|gold|child.?pugh",
    ],
}


# -----------------------------
# Normalisierung & Scoring
# -----------------------------


def _strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def normalize_for_match(s: str) -> str:
    s = s.lower()
    s = _strip_diacritics(s)
    s = re.sub(r"[^\w]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def normalize_source_key(source: str) -> str:
    name = Path(source).name
    name = re.sub(r"\.(pdf|docx|doc|txt|odt)$", "", name, flags=re.IGNORECASE)
    return normalize_for_match(name)


def chunk_file_to_source_key(chunk_file: Path) -> str:
    stem = chunk_file.stem
    if stem.lower().startswith("chunk_"):
        stem = stem[6:]
    stem = re.sub(r"_\d+$", "", stem)
    stem = re.sub(r"\.(pdf|docx|doc|txt|odt)$", "", stem, flags=re.IGNORECASE)
    return normalize_for_match(stem)


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-ZäöüÄÖÜß0-9]+", text.lower())
    kws: list[str] = []
    for t in tokens:
        if len(t) < 3:
            continue
        if t in STOPWORDS_DE:
            continue
        kws.append(t)

    # dedupe order-preserving
    seen = set()
    out = []
    for k in kws:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def chunk_to_search_text(chunk: Dict[str, Any]) -> str:
    # Plain-text chunks
    if isinstance(chunk.get("text"), str) and chunk["text"].strip():
        return chunk["text"]

    # Strukturierte Case-Chunks
    parts: list[str] = []
    for key in [
        "title",
        "patient_age",
        "patient_gender",
        "accident_mechanism",
        "chief_complaints",
        "physical_examination",
        "imaging_findings",
        "laboratory_findings",
        "suspected_diagnosis",
        "differential_diagnoses",
        "differentialdiagnosen",
        "diagnosis",
        "medications",
    ]:
        if key not in chunk:
            continue
        v = chunk.get(key)
        if isinstance(v, list):
            parts.append(" ".join(str(x) for x in v))
        elif v is not None:
            parts.append(str(v))
    return "\n".join(parts)


def score_question_to_chunk(question: str, chunk_text: str) -> float:
    q_kw = extract_keywords(question)
    if not q_kw:
        return 0.0

    chunk_norm = normalize_for_match(chunk_text)
    hits = 0
    for kw in q_kw:
        if normalize_for_match(kw) in chunk_norm:
            hits += 1

    overlap = hits / max(1, len(q_kw))

    q_short = question[:500].lower()
    c_short = chunk_text[:2000].lower()
    seq = SequenceMatcher(None, q_short, c_short).ratio()

    return 0.8 * overlap + 0.2 * seq


# -----------------------------
# Kontext-Extraktion
# -----------------------------


def _extract_patient_from_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    p = chunk.get("patient")
    if isinstance(p, dict):
        return {
            "alter": p.get("patient_age") or p.get("age"),
            "geschlecht": p.get("patient_gender") or p.get("gender"),
            "name": p.get("name"),
        }
    return {
        "alter": chunk.get("patient_age"),
        "geschlecht": chunk.get("patient_gender"),
        "name": None,
    }


def extract_context_from_chunk(chunk: Dict[str, Any]) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {
        "patient": {},
        "mechanism": None,
        "klinik": [],
        "befunde": {"bildgebung": [], "labor": []},
        "diagnose": None,
        "differentialdiagnosen": [],
        "medikation": [],
        "text_excerpt": "",
    }

    # Patient
    patient = _extract_patient_from_chunk(chunk)
    g = patient.get("geschlecht")
    if isinstance(g, str):
        gl = g.strip().lower()
        if gl in {"m", "male", "mann", "männlich"}:
            patient["geschlecht"] = "m"
        elif gl in {"w", "f", "female", "frau", "weiblich"}:
            patient["geschlecht"] = "w"
    ctx["patient"] = {k: v for k, v in patient.items() if v}

    # Mechanismus
    ctx["mechanism"] = (
        chunk.get("accident_mechanism")
        or chunk.get("mechanism")
        or chunk.get("unfallmechanismus")
    )

    # Klinik
    for field in [
        "chief_complaints",
        "leitsymptome",
        "symptoms",
        "physical_examination",
        "körperliche_untersuchung",
        "vital_signs",
        "vitalparameter",
    ]:
        v = chunk.get(field)
        if isinstance(v, list):
            ctx["klinik"].extend([str(x) for x in v if str(x).strip()])
        elif isinstance(v, str) and v.strip():
            ctx["klinik"].append(v.strip())

    # Befunde
    img = chunk.get("imaging_findings")
    if isinstance(img, list):
        ctx["befunde"]["bildgebung"].extend([str(x) for x in img if str(x).strip()])
    elif isinstance(img, str) and img.strip():
        ctx["befunde"]["bildgebung"].append(img.strip())

    lab = chunk.get("laboratory_findings")
    if isinstance(lab, list):
        ctx["befunde"]["labor"].extend([str(x) for x in lab if str(x).strip()])
    elif isinstance(lab, str) and lab.strip():
        ctx["befunde"]["labor"].append(lab.strip())

    # Medikation
    meds = chunk.get("medications")
    if isinstance(meds, list):
        ctx["medikation"].extend([str(x) for x in meds if str(x).strip()])
    elif isinstance(meds, str) and meds.strip():
        ctx["medikation"].append(meds.strip())

    # Diagnose
    diag = chunk.get("suspected_diagnosis") or chunk.get("diagnosis") or chunk.get("verdachtsdiagnose")
    if isinstance(diag, list) and diag:
        ctx["diagnose"] = str(diag[0])
    elif isinstance(diag, str) and diag.strip():
        ctx["diagnose"] = diag.strip()

    # DD
    dd = chunk.get("differential_diagnoses") or chunk.get("differentialdiagnosen") or []
    if isinstance(dd, list):
        ctx["differentialdiagnosen"] = [str(x) for x in dd if str(x).strip()]
    elif isinstance(dd, str) and dd.strip():
        ctx["differentialdiagnosen"] = [dd.strip()]

    # Text-Fallback (Auszug + primitive Dx/DD)
    txt = chunk.get("text")
    if isinstance(txt, str) and txt.strip():
        t = txt.strip()
        ctx["text_excerpt"] = t[:900]

        if not ctx.get("diagnose"):
            m = re.search(
                r"(?:verdachtsdiagnose|v\\.?d\\.?|diagnose)\\s*[:\\-]\\s*([^\\n]{3,120})",
                t,
                re.IGNORECASE,
            )
            if m:
                ctx["diagnose"] = m.group(1).strip()

        if not ctx.get("differentialdiagnosen"):
            m = re.search(r"(?:dd|differenzialdiagnosen?)\\s*[:\\-]\\s*([^\\n]{3,200})", t, re.IGNORECASE)
            if m:
                ctx["differentialdiagnosen"] = [x.strip() for x in re.split(r"[,;/]", m.group(1)) if x.strip()]

        if not ctx["patient"].get("alter"):
            age_match = re.search(r"(\\d{1,3})\\s*(?:jahre|j\\.|j\\b)", t, re.IGNORECASE)
            if age_match:
                ctx["patient"]["alter"] = age_match.group(1)

        if not ctx["patient"].get("geschlecht"):
            if re.search(r"\\b(patientin|frau|weiblich)\\b", t, re.IGNORECASE):
                ctx["patient"]["geschlecht"] = "w"
            elif re.search(r"\\b(patient|mann|männlich)\\b", t, re.IGNORECASE):
                ctx["patient"]["geschlecht"] = "m"

    # Dedupe helper
    def _dedupe(lst: list[str]) -> list[str]:
        seen = set()
        out = []
        for x in lst:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    ctx["klinik"] = _dedupe(ctx["klinik"])
    ctx["befunde"]["bildgebung"] = _dedupe(ctx["befunde"]["bildgebung"])
    ctx["befunde"]["labor"] = _dedupe(ctx["befunde"]["labor"])
    ctx["medikation"] = _dedupe(ctx["medikation"])
    ctx["differentialdiagnosen"] = _dedupe(ctx["differentialdiagnosen"])

    return ctx


def categorize_context(context: Dict[str, Any], best_score: float) -> str:
    patient = context.get("patient", {})
    has_patient = bool(patient.get("alter") or patient.get("geschlecht"))
    has_mechanism = bool(context.get("mechanism"))
    has_klinik = len(context.get("klinik", [])) > 0
    befunde = context.get("befunde", {})
    has_befunde = bool(befunde.get("bildgebung") or befunde.get("labor"))
    has_diagnose = bool(context.get("diagnose"))
    has_text = bool(context.get("text_excerpt"))

    if best_score >= SCORE_FOUND_MIN:
        score = sum([has_patient, has_mechanism, has_klinik, has_befunde, has_diagnose]) + (0.5 if has_text else 0)
        return "context_found" if score >= 3 else "partial_context"

    if best_score >= SCORE_PARTIAL_MIN:
        score = sum([has_patient, has_mechanism, has_klinik, has_befunde, has_diagnose]) + (0.5 if has_text else 0)
        return "partial_context" if score >= 2 else "no_context"

    return "no_context"


def check_medgemma_relevant(frage: str, antwort: str, context: Dict[str, Any]) -> bool:
    combined_text = f"{frage} {antwort}".lower()
    for patterns in MEDGEMMA_PATTERNS.values():
        for pattern in patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
    if context.get("befunde", {}).get("bildgebung"):
        return True
    return False


def build_repaired_answer(context: Dict[str, Any]) -> str:
    """
    Konservativ: nur Kontext-Ausleitung, keine Leitlinien-Therapie/Medikationsbehauptungen.
    """
    lines: list[str] = []

    dx = context.get("diagnose")
    if dx:
        lines.append(f"**Verdachtsdiagnose:** {dx}")

    dd = context.get("differentialdiagnosen") or []
    if dd:
        lines.append("\n**Differenzialdiagnosen:**")
        for i, d in enumerate(dd[:6], 1):
            lines.append(f"{i}. {d}")

    bef = context.get("befunde", {})
    img = bef.get("bildgebung") or []
    lab = bef.get("labor") or []
    if img:
        lines.append("\n**Bildgebung (Auszug):** " + "; ".join(img[:3]))
    if lab:
        lines.append("\n**Labor (Auszug):** " + "; ".join(lab[:3]))

    meds = context.get("medikation") or []
    if meds:
        lines.append("\n**Medikation im Fall (Auszug):** " + "; ".join(meds[:5]))

    if context.get("text_excerpt") and not (dx or dd or img or lab or meds):
        lines.append("**Kontext-Auszug:**\n" + context["text_excerpt"])

    lines.append("\n**QA:** Kontext rekonstruiert – medizinische Details bitte leitlinien-/medgemma-validieren.")
    return "\n".join(lines).strip()


def build_template_answer(original_antwort_preview: str) -> str:
    return (
        "**Hinweis:** Diese Karte hat keinen verlässlichen Fallkontext im Repo.\n\n"
        "**Template (Prüfungsantwort-Struktur):**\n"
        "1) Definition/Klassifikation\n"
        "2) Pathophysiologie/Ätiologie\n"
        "3) Diagnostik (Schritte, Red Flags)\n"
        "4) Therapie (inkl. Dosierungen – *nur nach Leitlinienvalidierung*)\n"
        "5) Rechtliches/Organisation (falls relevant)\n\n"
        f"**Original-Antwort (Preview):** {original_antwort_preview[:300]}{'...' if len(original_antwort_preview) > 300 else ''}\n"
    )


# -----------------------------
# Chunk Index / Load / Select
# -----------------------------


def build_chunk_index(chunk_dir: Path) -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = defaultdict(list)
    for chunk_file in chunk_dir.glob("*.json"):
        key = chunk_file_to_source_key(chunk_file)
        if key:
            idx[key].append(chunk_file)
    return dict(idx)


def load_chunks_from_files(chunk_files: list[Path]) -> list[tuple[str, Dict[str, Any]]]:
    out: list[tuple[str, Dict[str, Any]]] = []
    for p in chunk_files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, dict):
                    out.append((p.name, obj))
        elif isinstance(data, dict):
            out.append((p.name, data))
    return out


def select_top_chunks(
    frage: str,
    candidates: list[tuple[str, Dict[str, Any]]],
    manual_files: Optional[list[str]] = None,
) -> tuple[list[dict], float]:
    if manual_files:
        mf = set(manual_files)
        filtered = [(fn, ch) for (fn, ch) in candidates if fn in mf]
        if filtered:
            top = [{"chunk_file": fn, "score": 1.0, "chunk": ch} for fn, ch in filtered][:TOP_K_CHUNKS]
            return top, 1.0

    if len(extract_keywords(frage)) < MIN_KEYWORDS_FOR_MATCH:
        return [], 0.0

    scored: list[dict] = []
    for fn, ch in candidates:
        txt = chunk_to_search_text(ch)
        if not txt.strip():
            continue
        s = score_question_to_chunk(frage, txt)
        scored.append({"chunk_file": fn, "score": s, "chunk": ch})

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:TOP_K_CHUNKS]
    best = float(top[0]["score"]) if top else 0.0
    return top, best


def merge_contexts(contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "patient": {},
        "mechanism": None,
        "klinik": [],
        "befunde": {"bildgebung": [], "labor": []},
        "diagnose": None,
        "differentialdiagnosen": [],
        "medikation": [],
        "text_excerpt": "",
    }

    for ctx in contexts:
        if ctx.get("patient"):
            for k, v in ctx["patient"].items():
                if v and not merged["patient"].get(k):
                    merged["patient"][k] = v

        if ctx.get("mechanism") and not merged["mechanism"]:
            merged["mechanism"] = ctx["mechanism"]

        merged["klinik"].extend(ctx.get("klinik", []))
        merged["befunde"]["bildgebung"].extend(ctx.get("befunde", {}).get("bildgebung", []))
        merged["befunde"]["labor"].extend(ctx.get("befunde", {}).get("labor", []))
        merged["medikation"].extend(ctx.get("medikation", []))

        if ctx.get("diagnose") and not merged["diagnose"]:
            merged["diagnose"] = ctx["diagnose"]

        merged["differentialdiagnosen"].extend(ctx.get("differentialdiagnosen", []))

        if len(ctx.get("text_excerpt", "")) > len(merged.get("text_excerpt", "")):
            merged["text_excerpt"] = ctx.get("text_excerpt", "")

    def _dedupe(lst: list[str]) -> list[str]:
        seen = set()
        out = []
        for x in lst:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    merged["klinik"] = _dedupe(merged["klinik"])
    merged["befunde"]["bildgebung"] = _dedupe(merged["befunde"]["bildgebung"])
    merged["befunde"]["labor"] = _dedupe(merged["befunde"]["labor"])
    merged["medikation"] = _dedupe(merged["medikation"])
    merged["differentialdiagnosen"] = _dedupe(merged["differentialdiagnosen"])

    return merged


# -----------------------------
# Main
# -----------------------------


def main() -> None:
    repo_root = Path(__file__).parent.parent
    issues_file = repo_root / "_OUTPUT" / "kontext_fehlende_antworten.json"
    evidenz_file = repo_root / "_OUTPUT" / "evidenz_antworten.json"
    chunk_dir = repo_root / "_DERIVED_CHUNKS" / "CHUNKS"
    output_dir = repo_root / "_OUTPUT"

    print("📥 Lade Inputs...")
    issues = json.loads(issues_file.read_text(encoding="utf-8"))
    evidenz_data = json.loads(evidenz_file.read_text(encoding="utf-8"))

    evidenz_index: dict[int, dict] = {}
    for i, item in enumerate(evidenz_data):
        if isinstance(item, dict):
            evidenz_index[i] = item

    print(f"✅ Issues: {len(issues)}")
    print(f"✅ Evidenz-Items: {len(evidenz_index)}")

    print("🧭 Baue Chunk-Index...")
    chunk_index = build_chunk_index(chunk_dir)
    print(f"✅ Chunk-Index Keys: {len(chunk_index)}")

    source_cache: dict[str, list[tuple[str, Dict[str, Any]]]] = {}
    batch_items: list[dict] = []
    stats = defaultdict(int)

    for n, issue in enumerate(issues, 1):
        original_index = issue["index"]
        frage = issue["frage"]
        source = issue["source"]

        antwort_full = issue.get("antwort_preview", "")
        if original_index in evidenz_index:
            full_item = evidenz_index[original_index]
            antwort_full = full_item.get("antwort", "") or full_item.get("answer", "") or antwort_full

        source_key = normalize_source_key(source)

        if source_key not in source_cache:
            chunk_files = chunk_index.get(source_key, [])
            source_cache[source_key] = load_chunks_from_files(chunk_files)

        candidates = list(source_cache[source_key])

        # Manual overrides: Kandidaten ggf. ergänzen
        manual_files = MANUAL_CHUNK_OVERRIDES.get(original_index)
        if manual_files:
            extra_paths = [chunk_dir / fn for fn in manual_files if (chunk_dir / fn).exists()]
            extra = load_chunks_from_files(extra_paths)
            seen = {(fn, normalize_for_match(chunk_to_search_text(ch)[:200])) for fn, ch in candidates}
            for fn, ch in extra:
                k = (fn, normalize_for_match(chunk_to_search_text(ch)[:200]))
                if k not in seen:
                    candidates.append((fn, ch))
                    seen.add(k)

        top_chunks, best_score = select_top_chunks(frage, candidates, manual_files=manual_files)
        contexts = [extract_context_from_chunk(t["chunk"]) for t in top_chunks]
        merged_context = merge_contexts(contexts) if contexts else {}

        context_status = categorize_context(merged_context or {}, best_score)
        stats[f"status_{context_status}"] += 1

        medgemma_relevant = check_medgemma_relevant(frage, antwort_full, merged_context or {})
        if medgemma_relevant:
            stats["medgemma_relevant"] += 1

        if context_status == "context_found":
            repair_status = "repaired"
            repaired_answer = build_repaired_answer(merged_context)
            stats["repaired"] += 1
        else:
            repair_status = "template"
            repaired_answer = build_template_answer(antwort_full)
            stats["template"] += 1

        batch_items.append(
            {
                "id": f"repair_{original_index:05d}",
                "original_index": original_index,
                "original_frage": frage,
                "original_antwort": antwort_full[:500] + ("..." if len(antwort_full) > 500 else ""),
                "source": source,
                "context_status": context_status,
                "match_confidence": round(float(best_score), 4),
                "candidate_chunks_count": len(candidates),
                "matched_chunks_count": len(top_chunks),
                "selected_chunks": [
                    {"chunk_file": t["chunk_file"], "score": round(float(t["score"]), 4)} for t in top_chunks
                ],
                "extracted_context": merged_context,
                "medgemma_relevant": medgemma_relevant,
                "repair_status": repair_status,
                "repaired_answer": repaired_answer,
            }
        )

        if n % 25 == 0:
            print(f"  … verarbeitet {n}/{len(issues)}")

    # Outputs
    out_jsonl = output_dir / "batch_repair_input.jsonl"
    with open(out_jsonl, "w", encoding="utf-8") as f:
        for item in batch_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    stats_payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(batch_items),
        "status": {
            "context_found": stats["status_context_found"],
            "partial_context": stats["status_partial_context"],
            "no_context": stats["status_no_context"],
        },
        "repair": {"repaired": stats["repaired"], "template": stats["template"]},
        "medgemma_relevant": stats["medgemma_relevant"],
        "thresholds": {
            "min_keywords_for_match": MIN_KEYWORDS_FOR_MATCH,
            "top_k_chunks": TOP_K_CHUNKS,
            "score_found_min": SCORE_FOUND_MIN,
            "score_partial_min": SCORE_PARTIAL_MIN,
        },
        "manual_overrides": {str(k): v for k, v in MANUAL_CHUNK_OVERRIDES.items()},
    }

    out_stats = output_dir / "batch_repair_stats.json"
    out_stats.write_text(json.dumps(stats_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    out_md = output_dir / "batch_repair_instructions.md"
    out_md.write_text(
        f"""# Batch-Reparatur Anleitung (v2)

**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Gesamt:** {len(batch_items)} Fragen

---

## 📊 Statistik

| Kategorie | Anzahl | Anteil |
|-----------|--------|--------|
| **context_found** | {stats['status_context_found']} | {stats['status_context_found']/len(batch_items)*100:.1f}% |
| **partial_context** | {stats['status_partial_context']} | {stats['status_partial_context']/len(batch_items)*100:.1f}% |
| **no_context** | {stats['status_no_context']} | {stats['status_no_context']/len(batch_items)*100:.1f}% |
| **repaired (fallbasiert)** | {stats['repaired']} | {stats['repaired']/len(batch_items)*100:.1f}% |
| **template** | {stats['template']} | {stats['template']/len(batch_items)*100:.1f}% |
| **medgemma_relevant** | {stats['medgemma_relevant']} | {stats['medgemma_relevant']/len(batch_items)*100:.1f}% |

---

## ✅ Qualitäts-Guardrails (wichtig)

- Pro Frage werden nur die **Top-{TOP_K_CHUNKS}** relevantesten Chunks genutzt.
- `match_confidence` ist pro Frage gespeichert (0–1). **Niedrig = Review nötig.**
- `repaired_answer` ist **konservativ**: nur Kontext-Ausleitung, keine Leitlinien-Therapie ohne Validierung.

---

## 🔥 Nächste Schritte

1. Import in Anki über TSV (`anki_repaired_*.tsv`)
2. Karten mit `medgemma_relevant` priorisieren (Bilder/Dosis/Grenzwerte).
3. Bei „komisch“ wirkenden Karten: `match_confidence` prüfen und ggf. manuell korrigieren.

---

## 📁 Dateien

- `_OUTPUT/batch_repair_input.jsonl`
- `_OUTPUT/batch_repair_stats.json`
- `_OUTPUT/batch_repair_instructions.md`
""",
        encoding="utf-8",
    )

    print("\n✅ v2 Batch-Reparatur vorbereitet")
    print(f"  - {out_jsonl}")
    print(f"  - {out_stats}")
    print(f"  - {out_md}")
    print("\n📌 Hinweis: Antworten sind noch NICHT leitlinienvalidiert (siehe QA-Zeile pro Karte).")


if __name__ == "__main__":
    main()


