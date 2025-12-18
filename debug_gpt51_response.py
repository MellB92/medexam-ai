#!/usr/bin/env python3
"""
Debug script to examine GPT-5.1 response format
"""
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def test_gpt51_response():
    """Test GPT-5.1 API call to see actual response format"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set")
        return

    # Clean API key
    api_key = api_key.replace("\u2028", "").replace("\u2029", "").strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Test different configurations
    configs = [
        {
            "name": "reasoning_high",
            "payload": {
                "model": "gpt-5.1",
                "messages": [
                    {"role": "system", "content": "Du bist ein medizinischer Experte."},
                    {"role": "user", "content": "Was sind die Symptome von Diabetes?"},
                ],
                "reasoning_effort": "high",
                "max_completion_tokens": 200,
            },
        },
        {
            "name": "reasoning_high_with_temperature",
            "payload": {
                "model": "gpt-5.1",
                "messages": [
                    {"role": "system", "content": "Du bist ein medizinischer Experte."},
                    {"role": "user", "content": "Was sind die Symptome von Diabetes?"},
                ],
                "reasoning_effort": "high",
                "max_completion_tokens": 200,
                "temperature": 0.2,
            },
        },
        {
            "name": "no_reasoning",
            "payload": {
                "model": "gpt-5.1",
                "messages": [
                    {"role": "system", "content": "Du bist ein medizinischer Experte."},
                    {"role": "user", "content": "Was sind die Symptome von Diabetes?"},
                ],
                "max_completion_tokens": 200,
            },
        },
    ]

    for config in configs:
        print(f"\n{'='*50}")
        print(f"Testing: {config['name']}")
        print(f"{'='*50}")

        payload = config["payload"]

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

            print("\n=== EXTRACTED CONTENT ===")
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"Content: '{content}'")
            print(f"Content length: {len(content)}")
            print(
                f"Finish reason: {data.get('choices', [{}])[0].get('finish_reason', 'N/A')}"
            )

            # Check for any other fields that might contain content
            message = data.get("choices", [{}])[0].get("message", {})
            print(f"Message keys: {list(message.keys())}")
            for key, value in message.items():
                if key != "content" and value:
                    print(f"  {key}: {value}")

            # Check completion_tokens_details
            usage = data.get("usage", {})
            completion_details = usage.get("completion_tokens_details", {})
            print(f"Completion token details: {completion_details}")

            time.sleep(2)  # Rate limiting

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_gpt51_response()
