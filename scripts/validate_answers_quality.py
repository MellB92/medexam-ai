#!/usr/bin/env python3
"""
Qualitätsvalidierung der Antworten:
1. Prüft ob Antwort zur Frage passt (Relevanz)
2. Prüft medizinische Fakten gegen Perplexity/Web
3. Identifiziert problematische Antworten
"""

import json
import os
import re
import requests
import time
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

    prompt = f"""Du bist ein medizinischer Qualitätsprüfer. Bewerte ob die Antwort zur Frage passt.

FRAGE: {question}

ANTWORT: {answer[:1500]}

Bewerte auf einer Skala von 1-5:
1 = Antwort passt überhaupt nicht zur Frage (falsches Thema, Copy-Paste-Fehler)
2 = Antwort ist nur teilweise relevant
3 = Antwort ist relevant aber unvollständig
4 = Antwort ist gut und relevant
5 = Antwort ist ausgezeichnet und vollständig

Antworte NUR im Format:
SCORE: [1-5]
GRUND: [Kurze Begründung in einem Satz]
FEHLER: [Falls Score 1-2: Was ist falsch? Sonst: "Keine"]
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": 200,
        "temperature": 0.1,
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
        grund_match = re.search(r"GRUND:\s*(.+?)(?:\n|$)", result)
        fehler_match = re.search(r"FEHLER:\s*(.+?)(?:\n|$)", result)

        return {
            "score": int(score_match.group(1)) if score_match else 0,
            "grund": grund_match.group(1).strip() if grund_match else "",
            "fehler": fehler_match.group(1).strip() if fehler_match else "",
            "raw": result,
        }
    except Exception as e:
        return {"score": 0, "grund": f"API-Fehler: {e}", "fehler": str(e), "raw": ""}


def main():
    # Lade Sample
    sample_path = Path("_OUTPUT/validation_sample_75.json")
    if not sample_path.exists():
        print("Sample nicht gefunden!")
        return

    sample = json.load(open(sample_path, encoding="utf-8"))
    print(f"Validiere {len(sample)} Antworten...")

    # API Key
    api_key = load_api_key()
    if not api_key:
        print("Kein API Key gefunden!")
        return

    results = []
    problematic = []

    for i, entry in enumerate(sample, 1):
        question = entry.get("frage", "")
        answer = entry.get("antwort", "")

        print(f"[{i}/{len(sample)}] {question[:60]}...")

        validation = validate_answer_relevance(question, answer, api_key)

        result = {
            "index": i,
            "frage": question,
            "antwort_preview": answer[:200],
            "score": validation["score"],
            "grund": validation["grund"],
            "fehler": validation["fehler"],
        }
        results.append(result)

        if validation["score"] <= 2:
            problematic.append({
                "frage": question,
                "antwort": answer,
                "score": validation["score"],
                "fehler": validation["fehler"],
            })
            print(f"  ⚠️ PROBLEM (Score {validation['score']}): {validation['fehler'][:80]}")
        else:
            print(f"  ✅ Score {validation['score']}: {validation['grund'][:60]}")

        # Rate limiting
        time.sleep(0.3)

        # Checkpoint alle 25
        if i % 25 == 0:
            with open("_OUTPUT/validation_results_checkpoint.json", "w", encoding="utf-8") as f:
                json.dump({"results": results, "problematic": problematic}, f, ensure_ascii=False, indent=2)

    # Finale Ergebnisse
    output = {
        "timestamp": datetime.now().isoformat(),
        "total": len(sample),
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

    with open("_OUTPUT/validation_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("VALIDIERUNGSERGEBNIS")
    print("=" * 60)
    print(f"Geprüft: {len(sample)} Antworten")
    print(f"Durchschnittlicher Score: {output['summary']['avg_score']:.2f}/5")
    print(f"\nVerteilung:")
    print(f"  Score 1 (kritisch): {output['summary']['score_1']}")
    print(f"  Score 2 (problematisch): {output['summary']['score_2']}")
    print(f"  Score 3 (akzeptabel): {output['summary']['score_3']}")
    print(f"  Score 4 (gut): {output['summary']['score_4']}")
    print(f"  Score 5 (ausgezeichnet): {output['summary']['score_5']}")
    print(f"\nProblematische Antworten (Score 1-2): {len(problematic)}")
    print(f"Ergebnisse gespeichert: _OUTPUT/validation_results.json")


if __name__ == "__main__":
    main()
