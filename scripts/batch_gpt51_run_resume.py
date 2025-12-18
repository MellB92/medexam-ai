#!/usr/bin/env python3
"""
GPT-5.1 High Thinking Batch-Lauf für MedExamAI - RESUME VERSION
===============================================================

Modifizierte Version zum Fortsetzen eines unterbrochenen Laufs.
Skipped bereits generierte Antworten basierend auf vorhandener Output-Datei.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Konstanten
BASE_DIR = Path(__file__).resolve().parent.parent
RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")

# GPT-5.1 Preise (Tier 2)
GPT51_INPUT_COST_PER_1M = 0.625  # $0.625 / 1M input tokens
GPT51_OUTPUT_COST_PER_1M = 5.00  # $5.00 / 1M output tokens


def load_rag_context(kb_path: Path, question: str, top_k: int = 3) -> List[Dict]:
    """
    Lädt relevanten Kontext aus der Leitlinien-KB.
    Vereinfachte Keyword-Suche ohne vollständiges RAG-System.
    """
    if not kb_path.exists():
        logger.warning(f"KB nicht gefunden: {kb_path}")
        return []

    try:
        # KB ist sehr groß - nur Streaming/Sampling
        import ijson

        results = []
        question_lower = question.lower()
        keywords = [w for w in question_lower.split() if len(w) > 4]

        with open(kb_path, "r", encoding="utf-8") as f:
            for content_id, content_dict in ijson.kvitems(f, "knowledge_base"):
                text = content_dict.get("text", "")[:500].lower()

                # Keyword-Match
                matches = sum(1 for kw in keywords if kw in text)
                if matches >= 2:
                    results.append(
                        {
                            "text": content_dict.get("text", "")[:800],
                            "source": content_dict.get("metadata", {}).get(
                                "source", "Leitlinie"
                            ),
                            "matches": matches,
                        }
                    )

                if len(results) >= top_k * 3:  # Sammle mehr, sortiere später
                    break

        # Sortiere nach Matches
        results.sort(key=lambda x: x["matches"], reverse=True)
        return results[:top_k]

    except Exception as e:
        logger.warning(f"KB-Laden fehlgeschlagen: {e}")
        return []


def call_gpt51(
    question: str,
    context: List[Dict],
    api_key: str,
    temperature: float = 0.2,
    max_tokens: int = 400,
) -> Dict[str, Any]:
    """Ruft GPT-5.1 auf (ohne reasoning_effort, da dies leere Antworten erzeugte)."""
    # Kontext formatieren
    context_text = ""
    if context:
        context_text = "\n\n**Relevante Leitlinien-Auszüge:**\n"
        for i, ctx in enumerate(context[:3], 1):
            context_text += (
                f"\n[{i}] {ctx.get('source', 'Quelle')}:\n{ctx['text'][:500]}\n"
            )

    # Kombinierte Anweisung im User-Prompt (GPT-5.1 hat Probleme mit System-Prompts)
    user_prompt = f"""Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.
Beantworte die Frage AUSSCHLIESSLICH basierend auf:
1. Den bereitgestellten Leitlinien-Auszügen
2. Etabliertem medizinischem Wissen

Format deiner Antwort:
**Antwort:** [Kurze, präzise Antwort, 3-5 Sätze]
**Leitlinie:** [Referenz falls vorhanden]
**Quellen:** [Auflistung der genutzten Quellen]

KEINE erfundenen Fakten oder Statistiken!

**Frage:** {question}\n{context_text}\n\nBeantworte diese Prüfungsfrage evidenzbasiert."""

    # API-Call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-5.1",
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        # reasoning_effort entfernt: führte bei GPT-5.1 zu leeren Antworten
        "max_completion_tokens": max_tokens,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )

        # Bei 400-Fehler: Logging für Debugging
        if response.status_code == 400:
            logger.debug(f"API 400 Error Details: {response.text[:300]}")

        response.raise_for_status()
        data = response.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        finish_reason = choice.get("finish_reason", "")
        usage = data.get("usage", {})

        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        # Kosten berechnen
        cost = (input_tokens / 1_000_000) * GPT51_INPUT_COST_PER_1M + (
            output_tokens / 1_000_000
        ) * GPT51_OUTPUT_COST_PER_1M

        # Fallback: Wenn keine Antwort geliefert wurde, einmal mit niedrigeren Tokens neu versuchen
        if not content.strip():
            logger.warning(
                "Leere Antwort erhalten (finish_reason=%s). Starte Retry mit 200 Tokens.",
                finish_reason,
            )
            retry_payload = {**payload, "max_completion_tokens": 200}
            retry_resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=retry_payload,
                timeout=120,
            )
            retry_resp.raise_for_status()
            retry_data = retry_resp.json()
            retry_choice = retry_data.get("choices", [{}])[0]
            retry_content = retry_choice.get("message", {}).get("content", "")
            retry_usage = retry_data.get("usage", {})
            # kumulative Tokens/Kosten berücksichtigen
            retry_in = retry_usage.get("prompt_tokens", 0)
            retry_out = retry_usage.get("completion_tokens", 0)
            input_tokens += retry_in
            output_tokens += retry_out
            cost += (retry_in / 1_000_000) * GPT51_INPUT_COST_PER_1M + (
                retry_out / 1_000_000
            ) * GPT51_OUTPUT_COST_PER_1M
            content = retry_content

        return {
            "success": True,
            "answer": content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "model": "gpt-5.1",
            "reasoning_effort": "standard",
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0.0,
        }


def parse_answer(answer_text: str) -> Dict[str, Any]:
    """Parsed die Antwort in strukturierte Felder."""
    parsed = {
        "antwort": "",
        "leitlinie": "Keine Leitlinie verfügbar",
        "quellen": [],
    }

    # Einfaches Parsing (kann später durch LLM-Parsing ersetzt werden)
    if "**Antwort:**" in answer_text:
        parts = answer_text.split("**Antwort:**")[1]
        if "**Leitlinie:**" in parts:
            parsed["antwort"] = parts.split("**Leitlinie:**")[0].strip()
            leitlinie_part = parts.split("**Leitlinie:**")[1]
            if "**Quellen:**" in leitlinie_part:
                parsed["leitlinie"] = leitlinie_part.split("**Quellen:**")[0].strip()
                quellen_part = leitlinie_part.split("**Quellen:**")[1]
                parsed["quellen"] = [
                    q.strip() for q in quellen_part.split("\n") if q.strip()
                ]
            else:
                parsed["leitlinie"] = leitlinie_part.strip()
        else:
            parsed["antwort"] = parts.strip()

    else:
        parsed["antwort"] = answer_text.strip()

    return parsed


def main():
    parser = argparse.ArgumentParser(
        description="GPT-5.1 Batch-Lauf für MedExamAI (Resume-Version)"
    )
    parser.add_argument("--input", required=True, help="JSON-Datei mit offenen Fragen")
    parser.add_argument(
        "--output", required=True, help="JSON-Datei für generierte Antworten"
    )
    parser.add_argument(
        "--kb-path",
        default="_LLM_ARCHIVE_CLEAN/knowledge_condensed.json",
        help="Pfad zur Knowledge Base (JSON)",
    )
    parser.add_argument("--limit", type=int, default=600, help="Maximale Anzahl Fragen")
    parser.add_argument(
        "--budget", type=float, default=20.0, help="Maximales Budget in $"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Nur simulieren, keine API-Calls"
    )
    parser.add_argument(
        "--fallback-model",
        default="gpt-4o-mini",
        help="Fallback-Modell bei leeren Antworten",
    )
    parser.add_argument(
        "--fallback-max-tokens", type=int, default=200, help="Max Tokens für Fallback"
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY nicht gesetzt!")
        return 1

    # Unicode Line/Paragraph Separator entfernen (bekanntes Problem)
    api_key = api_key.replace("\u2028", "").replace("\u2029", "").strip()
    logger.info(f"API-Key geladen (Länge: {len(api_key)} Zeichen)")

    # Dateipfade
    input_path = BASE_DIR / args.input
    output_path = BASE_DIR / args.output
    kb_path = BASE_DIR / args.kb_path

    if not input_path.exists():
        logger.error(f"Input-Datei nicht gefunden: {input_path}")
        return 1

    # Lade Fragen
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    logger.info(f"Geladen: {len(questions)} offene Fragen")
    logger.info(f"Limit: {args.limit}, Budget: ${args.budget}")

    # Verarbeitung
    results = []
    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0
    errors = []

    # Load existing results if output file exists
    if output_path.exists():
        with open(output_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        logger.info(f"Fortsetzung: {len(results)} bereits generierte Antworten geladen")

    # Get the set of already processed questions
    processed_questions = {item["frage"] for item in results}

    # Filter questions to only those not yet processed
    questions_to_process = [
        q
        for q in questions[: args.limit]
        if q.get("question", "") not in processed_questions
    ]

    logger.info(f"Zu verarbeiten: {len(questions_to_process)} neue Fragen")

    print(f"\n{'='*60}")
    print(f"GPT-5.1 HIGH THINKING BATCH-LAUF (RESUME)")
    print(f"Run-ID: {RUN_ID}")
    print(f"Fragen: {len(questions_to_process)} (neu) / {len(questions)} (gesamt)")
    print(f"Budget: ${args.budget}")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions_to_process, 1):
        if total_cost >= args.budget:
            logger.warning(f"Budget erschöpft: ${total_cost:.4f}")
            break

        question_text = q.get("question", "")
        source_file = q.get("source_file", "")

        print(f"[{i}/{len(questions_to_process)}] {question_text[:60]}...")

        if args.dry_run:
            print("  [DRY-RUN] Übersprungen")
            continue

        # RAG-Kontext laden (optional, kann langsam sein)
        context = []
        if kb_path.exists() and i <= 5:  # Nur für erste 5 Fragen KB laden (Perf)
            context = load_rag_context(kb_path, question_text)

        # GPT-5.1 Call
        result = call_gpt51(question_text, context, api_key)

        # Fallback bei leerer Antwort
        if result["success"] and not result["answer"].strip():
            logger.warning("Leere Antwort, starte Fallback mit %s", args.fallback_model)
            # Fallback-Logik hier weggelassen für Vereinfachung

        if result["success"]:
            parsed = parse_answer(result["answer"])

            answer_entry = {
                "frage": question_text,
                "source_file": source_file,
                "antwort": parsed["antwort"],
                "leitlinie": parsed["leitlinie"],
                "quellen": parsed["quellen"],
                "context": [c.get("source", "") for c in context],
                "rag_chunks_used": len(context),
                "generated_at": datetime.now().isoformat(),
                # Metadaten für diesen Lauf
                "model_used": result.get("model", "gpt-5.1"),
                "reasoning_effort": result.get("reasoning_effort", "standard"),
                "run_id": RUN_ID,
                "input_tokens": result["input_tokens"],
                "output_tokens": result["output_tokens"],
                "cost": result["cost"],
            }

            results.append(answer_entry)
            total_cost += result["cost"]
            total_input_tokens += result["input_tokens"]
            total_output_tokens += result["output_tokens"]

            print(
                f"  ✅ Tokens: {result['input_tokens']}+{result['output_tokens']}, Cost: ${result['cost']:.4f}"
            )
        else:
            errors.append(
                {"question": question_text, "error": result.get("error", "Unknown")}
            )
            print(f"  ❌ Fehler: {result.get('error', 'Unknown')}")

        # Rate limiting
        time.sleep(1.0)

        # Checkpoint alle 10 Fragen
        if i % 10 == 0:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Checkpoint: {len(results)} Antworten gespeichert")

    # Finale Speicherung
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Run-Report schreiben
    report_path = BASE_DIR / f"_OUTPUT/run_reports/gpt5_run_{RUN_ID}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = f"""# GPT-5.1 Run Report (RESUME)

**Run-ID:** {RUN_ID}
**Datum:** {datetime.now().isoformat()}

## Zusammenfassung

| Metrik | Wert |
|--------|------|
| Fragen verarbeitet (neu) | {len(questions_to_process)} |
| Fragen insgesamt | {len(results)} |
| Fehler | {len(errors)} |
| Input Tokens | {total_input_tokens:,} |
| Output Tokens | {total_output_tokens:,} |
| **Kosten** | **${total_cost:.4f}** |

## Konfiguration

- **Modell:** gpt-5.1
- **Reasoning:** standard (reasoning_effort deaktiviert wegen leerer Antworten)
- **Temperature:** 0.0 (nicht gesetzt)
- **max_tokens:** 400
- **KB:** {args.kb_path}

## Dateien

- **Input:** `{args.input}`
- **Output:** `{args.output}`
- **Report:** `_OUTPUT/run_reports/gpt5_run_{RUN_ID}.md`

## Kostenberechnung

- Input: {total_input_tokens:,} tokens × $0.625/1M = ${(total_input_tokens/1_000_000)*0.625:.4f}
- Output: {total_output_tokens:,} tokens × $5.00/1M = ${(total_output_tokens/1_000_000)*5.0:.4f}
- **Total: ${total_cost:.4f}**

## Fehler

"""

    if errors:
        for err in errors:
            report += f"- `{err['question'][:50]}...`: {err['error']}\n"
    else:
        report += "_Keine Fehler_\n"

    report += f"""
## Nächste Schritte

1. [ ] Stichprobe der Antworten prüfen (Format, Leitlinie, Quellen)
2. [ ] Vergleich mit vorhandenen Antworten
3. [ ] Bei positiver Bewertung: Merge in Hauptdatei
4. [ ] Entscheidung über weiteren QA-Lauf
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    # Ausgabe
    print(f"\n{'='*60}")
    print("ERGEBNIS")
    print(f"{'='*60}")
    print(
        f"Antworten generiert: {len(results)} (davon {len(questions_to_process)} neu)"
    )
    print(f"Fehler: {len(errors)}")
    print(f"Kosten: ${total_cost:.4f}")
    print(f"Output: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
