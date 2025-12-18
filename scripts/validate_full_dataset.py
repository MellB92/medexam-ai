#!/usr/bin/env python3
"""
Vollständige Qualitätsvalidierung aller Antworten.
Prüft ob Antwort zur Frage passt (Relevanz-Check).
Speichert Fortschritt für Resume-Fähigkeit.
"""

import json
import os
import re
import requests
import time
import argparse
from pathlib import Path
from datetime import datetime


def load_api_key():
    """Lade OpenAI API Key aus .env"""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"\'')
                    if len(key) > 20:
                        return key
    return None


def validate_answer_relevance(question: str, answer: str, api_key: str) -> dict:
    """Prüft ob die Antwort zur Frage passt."""

    # Kürze sehr lange Antworten
    answer_preview = answer[:2000] if len(answer) > 2000 else answer

    prompt = f"""Bewerte ob die Antwort zur medizinischen Prüfungsfrage passt.

FRAGE: {question}

ANTWORT: {answer_preview}

Bewerte 1-5:
1 = Antwort passt NICHT zur Frage (falsches Thema, Copy-Paste-Fehler, irrelevant)
2 = Nur teilweise relevant oder sehr unvollständig
3 = Relevant aber mit Mängeln
4 = Gut und relevant
5 = Ausgezeichnet

Antworte NUR:
SCORE: [1-5]
FEHLER: [Kurz wenn Score<=2, sonst "OK"]
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 100,
        "temperature": 0.0,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"]

        # Parse result
        score_match = re.search(r"SCORE:\s*(\d)", result)
        fehler_match = re.search(r"FEHLER:\s*(.+?)(?:\n|$)", result, re.IGNORECASE)

        return {
            "score": int(score_match.group(1)) if score_match else 0,
            "fehler": fehler_match.group(1).strip() if fehler_match else "",
        }
    except Exception as e:
        return {"score": 0, "fehler": f"API-Fehler: {e}"}


def main():
    parser = argparse.ArgumentParser(description="Vollständige Validierung")
    parser.add_argument("--input", default="_OUTPUT/evidenz_antworten.json")
    parser.add_argument("--output", default="_OUTPUT/validation_full_results.json")
    parser.add_argument("--checkpoint", default="_OUTPUT/validation_checkpoint.json")
    parser.add_argument(
        "--problematic-output",
        default="_OUTPUT/problematic_answers.json",
        help="Pfad für problematische Antworten (Score<=2)",
    )
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--budget", type=float, default=5.0, help="Budget in USD")
    args = parser.parse_args()

    # API Key
    api_key = load_api_key()
    if not api_key:
        print("Kein API Key gefunden!")
        return

    # Lade Daten
    data = json.load(open(args.input, encoding="utf-8"))
    print(f"Geladen: {len(data)} Antworten")

    # Lade Checkpoint falls vorhanden
    checkpoint_path = Path(args.checkpoint)
    validated = {}
    if checkpoint_path.exists():
        checkpoint = json.load(open(checkpoint_path, encoding="utf-8"))
        validated = {v["frage"]: v for v in checkpoint.get("results", [])}
        print(f"Checkpoint geladen: {len(validated)} bereits validiert")

    # Filtere bereits validierte
    to_validate = []
    for entry in data:
        frage = entry.get("frage", "")
        if frage and frage not in validated:
            to_validate.append(entry)

    print(f"Noch zu validieren: {len(to_validate)}")

    if not to_validate:
        print("Alle bereits validiert!")
        return

    # Validierung
    results = list(validated.values())
    problematic = []
    total_cost = 0.0

    # Kosten: gpt-4o-mini ~$0.00015/1K input, $0.0006/1K output
    # Pro Frage ca. 500 input + 50 output tokens = ~$0.0001
    estimated_cost_per_question = 0.0001

    for i, entry in enumerate(to_validate, 1):
        frage = entry.get("frage", "")
        antwort = entry.get("antwort", "")

        # Budget-Check
        if total_cost >= args.budget:
            print(f"\n⚠️ Budget erreicht: ${total_cost:.4f} >= ${args.budget}")
            break

        # Validiere
        validation = validate_answer_relevance(frage, antwort, api_key)
        total_cost += estimated_cost_per_question

        result = {
            "frage": frage,
            "score": validation["score"],
            "fehler": validation["fehler"],
        }
        results.append(result)

        if validation["score"] <= 2:
            problematic.append({
                "frage": frage,
                "antwort": antwort,
                "score": validation["score"],
                "fehler": validation["fehler"],
            })
            print(f"[{i}/{len(to_validate)}] ⚠️ Score {validation['score']}: {frage[:50]}...")
        elif i % 50 == 0:
            print(f"[{i}/{len(to_validate)}] ✅ Fortschritt... (${total_cost:.4f})")

        # Checkpoint alle 100
        if i % args.batch_size == 0:
            checkpoint_data = {
                "timestamp": datetime.now().isoformat(),
                "total_validated": len(results),
                "results": results,
                "problematic_count": len(problematic),
            }
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            print(f"  💾 Checkpoint: {len(results)} validiert, {len(problematic)} problematisch")

        # Rate limiting
        time.sleep(0.15)

    # Finale Ergebnisse
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_validated": len(results),
        "total_cost": total_cost,
        "results": results,
        "problematic": problematic,
        "summary": {
            "score_1": sum(1 for r in results if r["score"] == 1),
            "score_2": sum(1 for r in results if r["score"] == 2),
            "score_3": sum(1 for r in results if r["score"] == 3),
            "score_4": sum(1 for r in results if r["score"] == 4),
            "score_5": sum(1 for r in results if r["score"] == 5),
            "avg_score": sum(r["score"] for r in results) / len(results) if results else 0,
        }
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Speichere problematische separat für einfache Regenerierung
    if problematic:
        with open(args.problematic_output, "w", encoding="utf-8") as f:
            json.dump(problematic, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("VALIDIERUNGSERGEBNIS")
    print("=" * 60)
    print(f"Validiert: {len(results)} Antworten")
    print(f"Kosten: ${total_cost:.4f}")
    print(f"Durchschnittlicher Score: {output['summary']['avg_score']:.2f}/5")
    print(f"\nVerteilung:")
    print(f"  Score 1 (kritisch): {output['summary']['score_1']}")
    print(f"  Score 2 (problematisch): {output['summary']['score_2']}")
    print(f"  Score 3 (akzeptabel): {output['summary']['score_3']}")
    print(f"  Score 4 (gut): {output['summary']['score_4']}")
    print(f"  Score 5 (ausgezeichnet): {output['summary']['score_5']}")
    print(f"\nProblematische Antworten (Score 1-2): {len(problematic)}")
    print(f"Ergebnisse: {args.output}")
    if problematic:
        print(f"Problematische: {args.problematic_output}")
    else:
        print("Problematische: (keine)")


if __name__ == "__main__":
    main()
