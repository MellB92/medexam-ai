#!/usr/bin/env python3
"""
Direkte GPT-4o-mini Batch-Generierung (ohne GPT-5.1 first).
Höheres max_tokens (800-1000), kein Skip bei <50 chars.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_kb(kb_path: str, top_k: int = 3) -> List[Dict]:
    """Lade Knowledge Base für Kontext."""
    try:
        if not Path(kb_path).exists():
            logger.warning(f"KB nicht gefunden: {kb_path}")
            return []

        with open(kb_path, "r", encoding="utf-8") as f:
            kb = json.load(f)

        # Einfache Auswahl der ersten top_k Einträge
        results = []
        for entry in kb[:top_k]:
            if isinstance(entry, dict) and "text" in entry:
                results.append(entry)
        return results

    except Exception as e:
        logger.warning(f"KB-Laden fehlgeschlagen: {e}")
        return []


def call_gpt4o_mini(
    question: str,
    context: List[Dict],
    api_key: str,
    max_tokens: int = 900,
) -> Dict[str, Any]:
    """Ruft GPT-4o-mini direkt auf."""

    # Kontext formatieren
    context_text = ""
    if context:
        context_text = "\n\n**Relevante Leitlinien-Auszüge:**\n"
        for i, ctx in enumerate(context[:3], 1):
            context_text += f"\n[{i}] {ctx.get('source', 'Quelle')}:\n{ctx['text'][:500]}\n"

    system_prompt = """Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.
    Beantworte Prüfungsfragen präzise und evidenzbasiert.
    Wenn der Fragetext mehrere Teilfragen oder Themen enthält (z.B. Prüfungsprotokoll-Dialoge),
    beantworte alle Teilfragen strukturiert (z.B. Teil 1/Teil 2) und trenne Themen klar.
    Wenn im Fragetext von "dieses Medikament" die Rede ist, aber kein Name genannt wird, erkläre
    die wahrscheinlichste Medikamentengruppe und nenne Beispiele (z.B. ...), statt eine einzelne
    Substanz als sicher vorauszusetzen.

    Format:
    **Antwort:** [Ausführliche, präzise Antwort]
    **Leitlinie:** [Referenz falls vorhanden]
    **Quellen:** [Auflistung der genutzten Quellen]

    WICHTIG: Gib IMMER eine vollständige Antwort. Keine erfundenen Fakten!"""

    user_prompt = f"""**Frage:** {question}
{context_text}

Beantworte diese Prüfungsfrage evidenzbasiert und ausführlich."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": max_tokens,
        "temperature": 0.3,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()

        answer = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})

        # Kosten berechnen (gpt-4o-mini: $0.15/1M input, $0.60/1M output)
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = (input_tokens * 0.15 + output_tokens * 0.60) / 1_000_000

        return {
            "answer": answer,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "model": "gpt-4o-mini",
            "finish_reason": data["choices"][0].get("finish_reason", "unknown"),
        }

    except Exception as e:
        logger.error(f"API-Fehler: {e}")
        return {"answer": "", "error": str(e), "cost": 0}


def main():
    parser = argparse.ArgumentParser(description="GPT-4o-mini direkte Batch-Generierung")
    parser.add_argument("--input", required=True, help="Input JSON mit Fragen")
    parser.add_argument("--output", required=True, help="Output JSON für Antworten")
    parser.add_argument("--kb-path", default="_OUTPUT/knowledge_base.json", help="Knowledge Base")
    parser.add_argument("--max-tokens", type=int, default=900, help="Max completion tokens")
    parser.add_argument("--limit", type=int, default=300, help="Max Fragen")
    parser.add_argument("--budget", type=float, default=10.0, help="Budget in USD")
    parser.add_argument("--dry-run", action="store_true", help="Nur simulieren")
    args = parser.parse_args()

    # API Key laden - OPENAI_API_KEY für api.openai.com
    # Lade aus .env (letzter Eintrag gewinnt)
    api_key = None
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    if len(key) > 20:  # Nur vollständige Keys akzeptieren
                        api_key = key

    # Clean up API key
    if api_key:
        api_key = api_key.replace("\u2028", "").replace("\u2029", "").strip()

    if not api_key:
        logger.error("Kein API-Key gefunden!")
        sys.exit(1)

    logger.info(f"API-Key geladen (Länge: {len(api_key)} Zeichen)")

    # Fragen laden
    with open(args.input, "r", encoding="utf-8") as f:
        questions = json.load(f)

    logger.info(f"Geladen: {len(questions)} Fragen")
    logger.info(f"Max Tokens: {args.max_tokens}, Budget: ${args.budget}")

    # Bereits generierte laden (für Resume)
    output_path = Path(args.output)
    existing = []
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
        logger.info(f"Resume: {len(existing)} bereits generiert")

    existing_questions = {e.get("frage", e.get("question", "")).strip().lower() for e in existing}

    # KB laden
    kb_context = load_kb(args.kb_path)

    # Generierung
    results = list(existing)
    total_cost = sum(e.get("cost", 0) for e in existing)
    errors = 0

    to_process = [q for q in questions if q.get("frage", q.get("question", "")).strip().lower() not in existing_questions]
    logger.info(f"Zu verarbeiten: {len(to_process)} Fragen")

    if args.dry_run:
        logger.info("DRY RUN - keine API-Calls")
        return

    for i, q in enumerate(to_process[:args.limit], 1):
        question_text = q.get("frage", q.get("question", ""))

        if total_cost >= args.budget:
            logger.warning(f"Budget erreicht: ${total_cost:.2f} >= ${args.budget}")
            break

        print(f"[{i}/{len(to_process)}] {question_text[:60]}...")

        result = call_gpt4o_mini(
            question=question_text,
            context=kb_context,
            api_key=api_key,
            max_tokens=args.max_tokens,
        )

        if result.get("error"):
            errors += 1
            logger.error(f"  Fehler: {result['error']}")
            continue

        answer = result["answer"]
        cost = result["cost"]
        total_cost += cost

        # Speichere ALLE Antworten (kein Skip bei <50 chars)
        entry = {
            "frage": question_text,
            "antwort": answer,
            "model": result.get("model", "gpt-4o-mini"),
            "tokens_in": result.get("input_tokens", 0),
            "tokens_out": result.get("output_tokens", 0),
            "cost": cost,
            "finish_reason": result.get("finish_reason", ""),
            "timestamp": datetime.now().isoformat(),
        }

        # Original-Felder übernehmen
        for key in ["source_file", "block_idx", "id"]:
            if key in q:
                entry[key] = q[key]

        results.append(entry)

        print(f"  ✅ Tokens: {result.get('input_tokens', 0)}+{result.get('output_tokens', 0)}, "
              f"Cost: ${cost:.4f}, Len: {len(answer)} chars")

        # Checkpoint alle 10 Fragen
        if i % 10 == 0:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Checkpoint: {len(results)} Antworten gespeichert")

        # Rate limiting
        time.sleep(0.3)

    # Final speichern
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("ERGEBNIS")
    print("=" * 60)
    print(f"Antworten generiert: {len(results)} (davon {len(results) - len(existing)} neu)")
    print(f"Fehler: {errors}")
    print(f"Kosten: ${total_cost:.4f}")
    print(f"Output: {output_path.absolute()}")


if __name__ == "__main__":
    main()
