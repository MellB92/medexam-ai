#!/usr/bin/env python3
"""
Refine RemNote Flashcards with OpenAI (High-End Quality).

Dieses Skript:
1. Lädt rohe RemNote-Karten (cards_merged.jsonl) und ihre Quell-Texte (rem_docs_merged.jsonl).
2. Rekonstruiert den vollen Text (Frage/Antwort) aus den IDs.
3. Sendet jeden Batch an OpenAI (gpt-4o oder o1-preview), um:
    - Rechtschreibung/Grammatik zu korrigieren
    - Medizinische Plausibilität zu prüfen
    - Anki-gerecht zu formatieren (Markdown, Fettdruck)
    - Tags zu generieren
4. Exportiert direkt importierbares TSV für Anki.

Usage:
    python3 scripts/refine_remnote_cards_openai.py --model gpt-5.2 --budget 5.0
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

try:  # optional
    from dotenv import find_dotenv, load_dotenv  # type: ignore

    load_dotenv(find_dotenv(usecwd=True), override=True)
except Exception:
    pass

# Load env vars
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("❌ Error: OPENAI_API_KEY not found in environment.")
    sys.exit(1)

# Pricing (approximate for estimation)
PRICE_INPUT_1M = 5.00  # gpt-4o
PRICE_OUTPUT_1M = 15.00
EUR_USD_RATE = 0.95  # 1 USD = 0.95 EUR


class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        # o1-preview supports limited params (no system prompt in some versions, fixed temp)
        # We stick to standard chat format, adapting if model is o1
        is_o1 = self.model.startswith("o1")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if not is_o1:
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})
        else:
            # o1 often expects just user messages or combined prompt
            combined = f"{system_prompt}\n\n---\n\n{user_prompt}"
            messages.append({"role": "user", "content": combined})

        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens" if is_o1 else "max_tokens": max_tokens,
        }
        if not is_o1:
            payload["temperature"] = temperature

        try:
            r = requests.post(self.base_url, headers=headers, json=payload, timeout=120)
            if not r.ok:
                return {"error": f"HTTP {r.status_code}: {r.text}"}
            return r.json()
        except Exception as e:
            return {"error": str(e)}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    items = []
    if not path.exists():
        return items
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return items


def build_rem_lookup(rem_docs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Builds a map of _id -> Rem Object to resolve references."""
    lookup = {}
    for doc in rem_docs:
        # RemNote exports structure: sometimes nested in 'object'
        obj = doc.get("object") or doc
        rid = obj.get("_id")
        if rid:
            lookup[rid] = obj
    return lookup


def resolve_text_content(rem_obj: Dict[str, Any]) -> str:
    """
    Tries to reconstruct text from RemNote's complex delta/structure.
    This is a simplified heuristic.
    """
    # 1. Direct name/key check (RemNote often stores text in 'key' or 'name')
    # RemNote JSON is very cryptic (k, n, etc.). We look for string lists.

    # Heuristic: Often "key" (k) contains the text content as a list of strings/dicts
    key_content = rem_obj.get("k") or rem_obj.get("key")
    if not key_content:
        # Fallback to 'n' (name) if string
        n = rem_obj.get("n") or rem_obj.get("name")
        if isinstance(n, str):
            return n
        return ""

    text_parts = []
    if isinstance(key_content, list):
        for part in key_content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict):
                # Rich text object? e.g. {"text": "...", "b": true}
                if "text" in part:
                    text_parts.append(part["text"])
                elif "q" in part:  # Reference?
                    pass  # complex ref
    elif isinstance(key_content, str):
        text_parts.append(key_content)

    return "".join(text_parts)


def build_parent_children(rems: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    parent_to_children: Dict[str, List[str]] = {}
    for doc in rems:
        obj = doc.get("object") or doc
        cid = obj.get("_id")
        pid = obj.get("parent")
        if not cid or not pid:
            continue
        parent_to_children.setdefault(str(pid), []).append(str(cid))
    return parent_to_children


def build_card_front_back(
    rem_id: str,
    lookup: Dict[str, Any],
    parent_to_children: Dict[str, List[str]],
    *,
    max_children: int = 8,
) -> Tuple[str, str]:
    rem = lookup.get(rem_id) or {}
    front = resolve_text_content(rem).strip()

    # Preferred answer: AI definition if present
    ai = rem.get("ai") or {}
    ai_def = (ai.get("def") or "").strip() if isinstance(ai, dict) else ""
    if ai_def:
        back = ai_def
        return front, back

    # Fallback: children as bullet list
    child_ids = parent_to_children.get(rem_id, [])[:max_children]
    bullets: List[str] = []
    for cid in child_ids:
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

    if bullets:
        return front, "\n".join(bullets)

    # Last resort
    return front, "[Antwort aus RemNote-Struktur nicht eindeutig rekonstruierbar – bitte prüfen]"


def process_card(
    client: OpenAIClient,
    card: Dict[str, Any],
    lookup: Dict[str, Any],
    parent_to_children: Dict[str, List[str]],
    idx: int,
    total: int,
) -> Dict[str, Any]:
    obj = card.get("object") or {}
    key = obj.get("k")  # e.g. "REMID.f"
    if not key:
        return {"status": "skipped", "reason": "no_key"}

    rem_id = key.split(".")[0] if "." in key else key
    q_raw, a_raw = build_card_front_back(rem_id, lookup, parent_to_children)
    if not q_raw.strip():
        return {"status": "skipped", "reason": "empty_front"}

    system_prompt = "Du bist ein medizinischer Experte und Didaktiker für die ärztliche Kenntnisprüfung Münster."
    user_prompt = (
        "Analysiere diese Flashcard (Rohdaten aus RemNote) und liefere eine import-fertige Anki-Karte.\n\n"
        f"Original Front:\n{q_raw}\n\n"
        f"Original Back:\n{a_raw}\n\n"
        "Aufgabe:\n"
        "1) Korrigiere Sprache/Struktur.\n"
        "2) Prüfe grob auf Plausibilität; wenn unsicher: markiere low confidence.\n"
        "3) Formatiere für Anki (HTML erlaubt; nutze <br> für Zeilenumbrüche).\n"
        "4) Gib Tags: fachgebiet::<...> + optional risk::<dose|radiation|deadline>.\n\n"
        "Gib STRICT JSON zurück:\n"
        '{"front":"...","back":"...","tags":"tag1 tag2","confidence":0.0,"comment":"..."}'
    )

    t0 = time.time()
    resp = client.chat_completion(system_prompt, user_prompt, max_tokens=900, temperature=0.2)
    dt = time.time() - t0
    if "error" in resp:
        return {"status": "error", "error": resp["error"], "rem_id": rem_id, "latency": dt}

    content = (((resp.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    if not content:
        return {"status": "parse_error", "error": "empty_model_output", "rem_id": rem_id}

    if "```json" in content:
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in content:
        content = content.split("```", 1)[1].strip()

    try:
        data = json.loads(content)
        return {
            "status": "success",
            "rem_id": rem_id,
            "original_front": q_raw,
            "original_back": a_raw,
            "refined": data,
            "usage": resp.get("usage", {}) or {},
            "latency": dt,
        }
    except Exception as e:
        return {"status": "parse_error", "raw_response": content[:2000], "error": str(e), "rem_id": rem_id}


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-4o", help="OpenAI Model (gpt-4o, o1-preview)")
    parser.add_argument("--limit", type=int, default=0, help="Max cards to process (0=all)")
    parser.add_argument("--budget", type=float, default=5.0, help="Max budget in USD")
    parser.add_argument("--fallback-model", default="gpt-4o", help="Fallback model if primary is not available")
    args = parser.parse_args()

    # Files
    repo_root = Path("Medexamenai_migration_full_20251217_204617")  # Adjust if needed or use cwd
    if not repo_root.exists():
        repo_root = Path(".")

    cards_file = repo_root / "_OUTPUT/remnote_merge/cards_merged.jsonl"
    rem_file = repo_root / "_OUTPUT/remnote_merge/rem_docs_merged.jsonl"
    out_tsv = repo_root / "_OUTPUT/anki_remnote_gpt_optimized.tsv"
    out_report = repo_root / "_OUTPUT/remnote_refinement_report.md"

    if not cards_file.exists():
        print(f"❌ Input not found: {cards_file}")
        sys.exit(1)

    # Load Data
    print("📂 Loading data...")
    cards = load_jsonl(cards_file)
    rems = load_jsonl(rem_file)
    print(f"   Cards: {len(cards)}")
    print(f"   Rems:  {len(rems)}")

    if args.limit > 0:
        cards = cards[: args.limit]
        print(f"   Limit applied: {len(cards)}")

    lookup = build_rem_lookup(rems)
    parent_to_children = build_parent_children(rems)

    # Init Client
    client = OpenAIClient(api_key=OPENAI_API_KEY, model=args.model)

    # Process
    print(f"🚀 Starting refinement with {args.model}...")
    results = []
    total_cost = 0.0
    model_used = args.model

    for i, c in enumerate(cards, 1):
        res = process_card(client, c, lookup, parent_to_children, i, len(cards))
        # If model name isn't accepted, switch once to fallback
        if res.get("status") == "error" and "model" in str(res.get("error", "")).lower() and args.fallback_model:
            if model_used != args.fallback_model:
                print(f"\n⚠️ Model '{model_used}' not accepted by API. Falling back to '{args.fallback_model}'.")
                model_used = args.fallback_model
                client = OpenAIClient(api_key=OPENAI_API_KEY, model=model_used)
                res = process_card(client, c, lookup, parent_to_children, i, len(cards))

        results.append(res)

        usage = res.get("usage", {}) or {}
        cost = (float(usage.get("prompt_tokens", 0)) / 1_000_000 * PRICE_INPUT_1M) + (
            float(usage.get("completion_tokens", 0)) / 1_000_000 * PRICE_OUTPUT_1M
        )
        total_cost += cost

        if i % 5 == 0 or i == len(cards):
            print(f"\r✅ Processed: {i}/{len(cards)} | Est. Cost: ${total_cost:.4f}", end="", flush=True)

        if total_cost >= args.budget:
            print("\n⚠️ Budget limit reached. Stopping.")
            break

    print("\n💾 Saving results...")

    # Write TSV
    success_count = 0
    with open(out_tsv, "w", encoding="utf-8") as f:
        # Header (optional for Anki, but good for debug)
        # f.write("# Question\tAnswer\tTags\n")
        for r in results:
            if r["status"] == "success":
                d = r["refined"]
                front = d.get("front", "").replace("\n", "<br>").strip()
                back = d.get("back", "").replace("\n", "<br>").strip()
                tags = d.get("tags", "RemNote_Import")

                # Add validation tag
                tags += " pipeline::gpt_refinement"
                if d.get("confidence", 1) < 0.7:
                    tags += " qa::needs_review"

                if front and back:
                    f.write(f"{front}\t{back}\t{tags}\n")
                    success_count += 1

    # Write Report
    with open(out_report, "w", encoding="utf-8") as f:
        f.write("# RemNote Refinement Report\n")
        f.write(f"**Date:** {datetime.now()}\n")
        f.write(f"**Model:** {model_used}\n")
        f.write(f"**Cards Processed:** {len(results)}\n")
        f.write(f"**Success:** {success_count}\n")
        f.write(f"**Total Cost:** ${total_cost:.4f}\n\n")
        f.write("## Skipped/Errors\n")
        for r in results:
            if r["status"] != "success":
                f.write(f"- {r['status']}: {r.get('reason') or r.get('error')}\n")

    print(f"\n🎉 Done! Created {out_tsv} ({success_count} cards).")
    print(f"📄 Report: {out_report}")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nAborted.")
