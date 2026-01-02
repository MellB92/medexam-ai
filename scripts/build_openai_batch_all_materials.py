#!/usr/bin/env python3
"""Build OpenAI Batch JSONL input for the All-Materials QA/Polish pipeline.

Input: master_cards.jsonl produced by build_master_cards.py
Output: openai_batch_input.jsonl in OpenAI Batch format.

This script does NOT execute network operations.

Batch line format (OpenAI Batches API expectation):
{
  "custom_id": "...",
  "method": "POST",
  "url": "/v1/responses",
  "body": { ... }
}

Model strategy:
- primary model: gpt-5.2
- fallback model is recorded in metadata; actual fallback execution is handled by the operator.

Strict output: model must return raw JSON (no markdown fences).
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple


def _approx_tokens(s: str) -> int:
    # crude heuristic: ~4 chars/token
    return max(1, math.ceil(len(s) / 4))


def _load_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _risk_tags_from_text(text: str) -> List[str]:
    t = text.lower()
    risks: List[str] = []
    if any(k in t for k in ["sievert", "sv", "mgy", "strahlen", "röntgen", "roentgen", "ct", "dosis"]):
        risks.extend(["risk::radiation", "risk::dose"])
    if any(k in t for k in ["deadline", "frist", "ifsg", "meldung", "unverzüglich", "24 h", "48 h", "innerhalb"]):
        risks.append("risk::deadline")
    if any(k in t for k in ["leitlinie", "stiko", "awmf", "s3", "s2k", "guideline"]):
        risks.append("risk::guideline")
    return sorted(set(risks))


SYSTEM_PROMPT = (
    "Du bist ein medizinischer Experte und Didaktiker für die ärztliche Kenntnisprüfung Münster. "
    "Du arbeitest streng evidenzorientiert und markierst Unsicherheit klar."
)

STOPWORDS_DE = {
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "einer",
    "einem",
    "einen",
    "und",
    "oder",
    "aber",
    "sowie",
    "wie",
    "was",
    "welche",
    "welcher",
    "welches",
    "wann",
    "warum",
    "wieso",
    "wo",
    "mit",
    "ohne",
    "bei",
    "im",
    "in",
    "am",
    "an",
    "auf",
    "aus",
    "für",
    "von",
    "zum",
    "zur",
    "des",
    "den",
    "dem",
    "ist",
    "sind",
    "war",
    "wird",
    "werden",
    "kann",
    "können",
    "soll",
    "sollen",
    "bitte",
    "u",
    "ua",
    "z",
    "b",
}


def _tokenize(text: str) -> List[str]:
    toks = re.findall(r"[A-Za-zÄÖÜäöüß0-9]{2,}", (text or "").lower())
    return [t for t in toks if t not in STOPWORDS_DE]


def _safe_trunc(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _load_evidenz(path: Path) -> List[Dict[str, Any]]:
    """
    Load the local RAG knowledge base (evidenz_antworten_clean.json).
    Structure: list of dicts with keys like {frage, antwort, quellen, leitlinie, source_file, rag_chunks_used, ...}
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    return []


def _build_inverted_index(evidenz: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    inv: Dict[str, List[int]] = {}
    for i, e in enumerate(evidenz):
        q = str(e.get("frage") or "")
        a = str(e.get("antwort") or "")
        toks = _tokenize(q + " " + a[:600])
        for t in set(toks):
            inv.setdefault(t, []).append(i)
    return inv


def _retrieve_rag_snippets(
    *,
    query: str,
    evidenz: List[Dict[str, Any]],
    inv: Dict[str, List[int]],
    top_k: int,
    min_score: int,
    max_chars_total: int,
) -> Tuple[str, List[str]]:
    """
    Lightweight lexical retrieval against evidenz_antworten_clean.json.
    Returns (rag_context_text, suggested_citations).
    """
    q_toks = _tokenize(query)
    if not q_toks:
        return "", []

    scores: Dict[int, int] = {}
    for t in set(q_toks):
        for doc_id in inv.get(t, []):
            scores[doc_id] = scores.get(doc_id, 0) + 1

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    picked = [(d, s) for d, s in ranked if s >= min_score][:top_k]
    if not picked:
        return "", []

    lines: List[str] = []
    citations: List[str] = ["_OUTPUT/evidenz_antworten_clean.json"]
    budget = max_chars_total

    for idx, (doc_id, score) in enumerate(picked, 1):
        e = evidenz[doc_id]
        frage = _safe_trunc(str(e.get("frage") or ""), 220)
        antwort = _safe_trunc(str(e.get("antwort") or ""), 520)
        quellen = e.get("quellen") or []
        if isinstance(quellen, list):
            quellen_s = "; ".join([str(x) for x in quellen[:3] if x])[:320]
        else:
            quellen_s = str(quellen)[:320]
        leitlinie = _safe_trunc(str(e.get("leitlinie") or ""), 160)
        source_file = _safe_trunc(str(e.get("source_file") or ""), 160)

        block: List[str] = []
        block.append(f"[RAG {idx}] (score={score}) Frage: {frage}")
        if antwort:
            block.append(f"Antwort-Auszug: {antwort}")
        meta_parts: List[str] = []
        if leitlinie:
            meta_parts.append(f"Leitlinie: {leitlinie}")
        if quellen_s:
            meta_parts.append(f"Quellen: {quellen_s}")
        if source_file:
            meta_parts.append(f"source_file: {source_file}")
        if meta_parts:
            block.append(" | ".join(meta_parts))

        block_text = "\n".join(block).strip()
        if len(block_text) + 2 > budget:
            break
        lines.append(block_text)
        lines.append("")

        if quellen_s:
            citations.append(quellen_s)
        if source_file:
            citations.append(source_file)

    rag_text = "\n".join(lines).strip()
    # Deduplicate citations (keep order)
    seen = set()
    citations_uniq: List[str] = []
    for c in citations:
        c = (c or "").strip()
        if not c or c in seen:
            continue
        citations_uniq.append(c)
        seen.add(c)
    return rag_text, citations_uniq[:6]


def build_user_prompt(card: Dict[str, Any]) -> str:
    front = card.get("front", "")
    back = card.get("back", "")
    tags_raw = card.get("tags_raw", "")
    source_ref = card.get("source_ref", "")
    context_ref = card.get("context_ref", "")
    context_found = bool(card.get("context_found", True))
    rag_context = (card.get("_rag_context") or "").strip()
    rag_citations = card.get("_rag_citations") or []
    if not isinstance(rag_citations, list):
        rag_citations = []

    return (
        "Veredle diese Lernkarte für Anki nach den folgenden Regeln.\n\n"
        "KONTEXT-PFLICHT:\n"
        "- Setze review_reason='missing_context' NUR wenn context_found=false ODER die Frage ohne Fallkontext offensichtlich unverständlich ist (z.B. 'Und dann?', 'Was meinen Sie damit?').\n"
        "- Erfinde keine Quellen.\n\n"
        "RAG-KONTEXT (lokal, zur Faktensicherung; nutze ihn wenn passend):\n"
        + (rag_context + "\n\n" if rag_context else "(kein RAG-Kontext gefunden)\n\n")
        + (
            ("RAG-CITATIONS-SUGGESTED: " + "; ".join([str(x) for x in rag_citations[:4] if x]) + "\n\n")
            if rag_citations
            else ""
        )
        + "LÄNGEN-GUARDRAILS (um Token-Limits zu vermeiden):\n"
        "- back: maximal 12 Bulletpoints ODER maximal ~1200 Zeichen.\n"
        "- notes: maximal ~250 Zeichen.\n"
        "- Wenn etwas nicht sicher ist: kurz markieren (needs_review=true) statt lange auszuführen.\n\n"
        + "OUTPUT-FORMAT (STRICT JSON, KEINE Markdown-Fences):\n"
        "{\n"
        '  "front": "...",\n'
        '  "back": "...",\n'
        '  "tags": "...",\n'
        '  "confidence": 0.0,\n'
        '  "needs_review": false,\n'
        '  "review_reason": "",\n'
        '  "citations_minimal": ["..."],\n'
        '  "notes": ""\n'
        "}\n\n"
        "REGELN:\n"
        "- HTML: Zeilenumbrüche als <br> (keine echten Newlines in Feldern).\n"
        "- Tags: mindestens fachgebiet::<...> und ggf. risk::<dose|radiation|deadline|guideline>.\n"
        "- citations_minimal: min. 1 Eintrag, z.B. source_ref/context_ref oder RAG-CITATIONS-SUGGESTED.\n"
        "- Keine neuen Medien/externen Quellen integrieren.\n\n"
        f"context_found: {str(context_found).lower()}\n"
        f"source_ref: {source_ref}\n"
        f"context_ref: {context_ref}\n"
        f"tags_raw: {tags_raw}\n\n"
        f"ORIGINAL FRONT:\n{front}\n\n"
        f"ORIGINAL BACK:\n{back}\n"
    )


def build_batch_line(card: Dict[str, Any], *, model: str, fallback_model: str) -> Dict[str, Any]:
    risk_hints = _risk_tags_from_text(card.get("front", "") + "\n" + card.get("back", ""))

    body = {
        "model": model,
        # For reasoning-capable models (e.g., gpt-5.x), allow higher thinking effort.
        # If the model/endpoint doesn't support it, operator can rerun without this field.
        "reasoning": {"effort": card.get("_thinking_effort", "high")},
        # Reduce verbosity/variance to avoid truncation.
        "temperature": float(card.get("_temperature", 0.2)),
        "top_p": float(card.get("_top_p", 0.9)),
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(card)},
        ],
        # Hard cap to control cost; raise only for retry runs.
        "max_output_tokens": int(card.get("_max_output_tokens", 900)),
        # NOTE: Responses API uses `text.format` (not `response_format`).
        "text": {
            "verbosity": str(card.get("_text_verbosity", "low")),
            "format": {
                "type": "json_schema",
                "name": "anki_card_refinement",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "front",
                        "back",
                        "tags",
                        "confidence",
                        "needs_review",
                        "review_reason",
                        "citations_minimal",
                        "notes",
                    ],
                    "properties": {
                        "front": {"type": "string"},
                        "back": {"type": "string"},
                        "tags": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "needs_review": {"type": "boolean"},
                        "review_reason": {"type": "string"},
                        "citations_minimal": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                        "notes": {"type": "string"},
                    },
                },
            },
        },
        "metadata": {
            # NOTE: OpenAI expects metadata values to be strings (not arrays/objects).
            "card_id": str(card.get("card_id") or ""),
            "source_ref": str(card.get("source_ref") or ""),
            "context_ref": str(card.get("context_ref") or ""),
            "fallback_model": str(fallback_model or ""),
            "risk_hints": " ".join(risk_hints),
            "thinking_effort": str(card.get("_thinking_effort") or "high"),
        },
    }

    return {
        "custom_id": f"card::{card.get('card_id')}",
        "method": "POST",
        "url": "/v1/responses",
        "body": body,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--fallback-model", required=True)
    parser.add_argument("--budget-usd", type=float, default=0.0, help="Soft gate; estimation only")
    parser.add_argument(
        "--thinking-effort",
        default="high",
        help="Reasoning effort for gpt-5.x style models (low|medium|high).",
    )
    parser.add_argument(
        "--split-max-enqueued-tokens",
        type=int,
        default=0,
        help=(
            "If >0, split output into multiple JSONL files such that the estimated prompt token sum per file "
            "does not exceed this number (helps avoid OpenAI batch enqueued-token limits)."
        ),
    )
    parser.add_argument("--in", dest="in_path", required=True, help="master_cards.jsonl")
    parser.add_argument("--out", dest="out_path", required=True, help="openai_batch_input.jsonl")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of requests")
    parser.add_argument("--max-output-tokens", type=int, default=900, help="max_output_tokens per request")
    parser.add_argument("--temperature", type=float, default=0.2, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=0.9, help="Top-p sampling")
    parser.add_argument(
        "--text-verbosity",
        default="low",
        help="Responses API text verbosity (low|medium|high) to control length.",
    )
    parser.add_argument(
        "--rag-evidenz",
        default="_OUTPUT/evidenz_antworten_clean.json",
        help="Local RAG knowledge base (evidenz_antworten_clean.json).",
    )
    parser.add_argument("--rag-top-k", type=int, default=2, help="Top-K RAG snippets to include per card.")
    parser.add_argument("--rag-min-score", type=int, default=2, help="Min token-overlap score to include a RAG match.")
    parser.add_argument("--rag-max-chars", type=int, default=1400, help="Max chars of RAG context included per card.")
    args = parser.parse_args()

    in_path = Path(args.in_path)
    out_path = Path(args.out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    evid_path = Path(args.rag_evidenz)
    evidenz = _load_evidenz(evid_path)
    inv = _build_inverted_index(evidenz) if evidenz else {}

    total_est_tokens = 0
    total_cards = 0

    # Split mode bookkeeping
    split_max = int(args.split_max_enqueued_tokens or 0)
    part = 1
    part_est_tokens = 0
    part_cards = 0
    manifest: List[Dict[str, Any]] = []

    def part_path(n: int) -> Path:
        return out_path.with_name(f"{out_path.stem}_part{n:03d}{out_path.suffix}")

    def open_writer(path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        return path.open("w", encoding="utf-8")

    f_out = None
    current_out_path = out_path if split_max <= 0 else part_path(part)
    f_out = open_writer(current_out_path)

    try:
        for card in _load_jsonl(in_path):
            if card.get("excluded"):
                continue
            if args.limit and total_cards >= args.limit:
                break

            # Inject thinking effort into the card payload (keeps signature of build_batch_line simple)
            card["_thinking_effort"] = (args.thinking_effort or "high").strip().lower()
            card["_max_output_tokens"] = int(args.max_output_tokens or 900)
            card["_temperature"] = float(args.temperature)
            card["_top_p"] = float(args.top_p)
            card["_text_verbosity"] = (args.text_verbosity or "low").strip().lower()

            if evidenz:
                rag_text, rag_cits = _retrieve_rag_snippets(
                    query=str(card.get("front") or ""),
                    evidenz=evidenz,
                    inv=inv,
                    top_k=int(args.rag_top_k),
                    min_score=int(args.rag_min_score),
                    max_chars_total=int(args.rag_max_chars),
                )
                card["_rag_context"] = rag_text
                card["_rag_citations"] = rag_cits

            req_tokens = _approx_tokens(SYSTEM_PROMPT) + _approx_tokens(build_user_prompt(card))

            # Split before writing the next request if we'd exceed the per-file gate.
            if split_max > 0 and part_cards > 0 and (part_est_tokens + req_tokens) > split_max:
                f_out.close()
                manifest.append(
                    {
                        "part": part,
                        "path": str(current_out_path),
                        "requests": part_cards,
                        "est_prompt_tokens": part_est_tokens,
                    }
                )
                part += 1
                part_est_tokens = 0
                part_cards = 0
                current_out_path = part_path(part)
                f_out = open_writer(current_out_path)

            line = build_batch_line(card, model=args.model, fallback_model=args.fallback_model)
            f_out.write(json.dumps(line, ensure_ascii=False) + "\n")

            part_est_tokens += req_tokens
            part_cards += 1
            total_est_tokens += req_tokens
            total_cards += 1

        # Close final part and record it
        f_out.close()
        manifest.append(
            {
                "part": part,
                "path": str(current_out_path),
                "requests": part_cards,
                "est_prompt_tokens": part_est_tokens,
            }
        )
    finally:
        try:
            if f_out and not f_out.closed:
                f_out.close()
        except Exception:
            pass

    est_m_tokens = total_est_tokens / 1_000_000
    if split_max > 0:
        manifest_path = out_path.with_name(f"{out_path.stem}_manifest.json")
        manifest_path.write_text(
            json.dumps({"split_max_enqueued_tokens": split_max, "parts": manifest}, indent=2), encoding="utf-8"
        )
        print(f"Wrote batch inputs (split): {manifest_path}")
        print(f"Parts: {len(manifest)}")
        for p in manifest:
            print(f"  part{p['part']:03d}: requests={p['requests']} est_prompt_tokens={p['est_prompt_tokens']}")
    else:
        print(f"Wrote batch input: {out_path}")

    print(f"Requests: {total_cards}")
    print(f"Estimated prompt tokens: {total_est_tokens} (~{est_m_tokens:.3f}M)")
    if args.budget_usd:
        print(f"Budget gate (manual): ${args.budget_usd:.2f}")


if __name__ == "__main__":
    main()
