#!/usr/bin/env python3
"""
Debug script to test simpler GPT-5.1 calls
"""
import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()


def test_simple_gpt51():
    """Test simpler GPT-5.1 calls"""
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

    # Try very simple prompts
    simple_tests = [
        {
            "name": "simple_english",
            "payload": {
                "model": "gpt-5.1",
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"},
                ],
                "max_completion_tokens": 50,
            },
        },
        {
            "name": "simple_german",
            "payload": {
                "model": "gpt-5.1",
                "messages": [
                    {"role": "user", "content": "Hallo, wie geht es dir?"},
                ],
                "max_completion_tokens": 50,
            },
        },
        {
            "name": "with_system",
            "payload": {
                "model": "gpt-5.1",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "What is 2+2?"},
                ],
                "max_completion_tokens": 10,
            },
        },
    ]

    for test in simple_tests:
        print(f"\n{'='*50}")
        print(f"Testing: {test['name']}")
        print(f"{'='*50}")

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=test["payload"],
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"Content: '{content}'")
            print(f"Content length: {len(content)}")
            print(
                f"Finish reason: {data.get('choices', [{}])[0].get('finish_reason', 'N/A')}"
            )

            # Check usage
            usage = data.get("usage", {})
            print(f"Usage: {usage}")

            time.sleep(2)

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    test_simple_gpt51()
