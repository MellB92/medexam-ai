#!/usr/bin/env python3
"""
Debug single question to see raw response
"""
import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def debug_single_question():
    """Debug a single question"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set")
        return

    # Clean API key
    api_key = api_key.replace("\u2028", "").replace("\u2029", "").strip()

    # Test with the problematic question
    question = "Beidseitig Verletzung. Wie kann man es vermeiden?"

    user_prompt = f"""Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung.
Beantworte die Frage AUSSCHLIESSLICH basierend auf:
1. Den bereitgestellten Leitlinien-Auszügen
2. Etabliertem medizinischem Wissen

Format deiner Antwort:
**Antwort:** [Kurze, präzise Antwort, 3-5 Sätze]
**Leitlinie:** [Referenz falls vorhanden]
**Quellen:** [Auflistung der genutzten Quellen]

KEINE erfundenen Fakten oder Statistiken!

**Frage:** {question}

Beantworte diese Prüfungsfrage evidenzbasiert."""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "gpt-5.1",
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        # "reasoning_effort": "high",  # Commented out to test without reasoning
        "max_completion_tokens": 400,
    }

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        print("=== RAW RESPONSE ===")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"\n=== EXTRACTED CONTENT ===")
        print(f"Content: '{content}'")
        print(f"Content length: {len(content)}")

        # Test parsing
        from scripts.batch_gpt51_run import parse_answer

        parsed = parse_answer(content)
        print(f"\n=== PARSED RESULT ===")
        print(f"Antwort: '{parsed['antwort']}'")
        print(f"Leitlinie: '{parsed['leitlinie']}'")
        print(f"Quellen: {parsed['quellen']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    debug_single_question()
