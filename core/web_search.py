#!/usr/bin/env python3
"""
MedExamAI - Targeted Medical Web Search via Perplexity
======================================================

Lightweight wrapper to perform high-precision web searches using Perplexity's
online models directly. Returns structured snippets with evidence-based
medical information suitable for exam preparation.

Environment:
- PERPLEXITY_API_KEY: primary API key
- PERPLEXITY_API_KEY_2: fallback API key (optional)
- PERPLEXITY_MODEL (optional): default 'sonar' for balanced speed/quality

Notes:
- Perplexity provides real-time web search with citations
- Optimized for German medical exam questions (STIKO, AWMF, etc.)
- Supports dual API keys for higher rate limits
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

ALLOWED_DOMAINS_DEFAULT = [
    # Primary medical resources
    "flexikon.doccheck.com",
    "doccheck.com",
    # German guideline registry and societies
    "register.awmf.org",
    "awmf.org",
    "dgim.de",
    "rki.de",
    "pei.de",
]


def _call_perplexity(api_key: str, model_id: str, query: str) -> Optional[str]:
    """Make a single Perplexity API call."""
    system_prompt = (
        "Du bist ein medizinischer Recherche-Assistent für deutsche Prüfungsvorbereitung. "
        "Antworte präzise und evidenzbasiert. Nenne relevante Quellen (STIKO, AWMF, RKI, DocCheck). "
        "Antworte auf Deutsch."
    )
    user_prompt = (
        f"Beantworte folgende medizinische Prüfungsfrage kurz und präzise:\n\n{query}\n\n"
        "Gib die wichtigsten Fakten und nenne die Quellen."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
    }

    resp = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=payload,
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def search_medical_web(
    query: str,
    max_results: int = 5,
    allowed_domains: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Performs a web search using Perplexity's online model directly.

    Supports two API keys for failover/rate limit handling.

    Returns a list of dicts: {title, url, snippet, source}
    """
    model_id = model or os.getenv("PERPLEXITY_MODEL", "sonar")

    # Get both API keys
    api_key_1 = os.getenv("PERPLEXITY_API_KEY")
    api_key_2 = os.getenv("PERPLEXITY_API_KEY_2")

    if not api_key_1 and not api_key_2:
        logger.warning("Keine PERPLEXITY_API_KEY gesetzt - Web-Suche deaktiviert")
        return []

    # Try primary key first, then fallback
    api_keys = [k for k in [api_key_1, api_key_2] if k]

    for i, api_key in enumerate(api_keys):
        try:
            logger.debug(f"Versuche Perplexity API Key {i+1}...")
            content = _call_perplexity(api_key, model_id, query)

            if content:
                logger.info(f"Perplexity Web-Suche erfolgreich (Key {i+1})")
                return [{
                    "title": "Perplexity Web-Recherche",
                    "url": "https://perplexity.ai",
                    "snippet": content,
                    "source": "perplexity_web",
                }]

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.warning(f"Perplexity Key {i+1} Rate Limit erreicht, versuche nächsten...")
                continue
            elif e.response.status_code == 401:
                logger.warning(f"Perplexity Key {i+1} ungültig, versuche nächsten...")
                continue
            else:
                logger.error(f"Perplexity HTTP-Fehler (Key {i+1}): {e}")
                continue
        except Exception as e:
            logger.error(f"Perplexity Fehler (Key {i+1}): {e}")
            continue

    logger.error("Alle Perplexity API Keys fehlgeschlagen")
    return []


__all__ = ["search_medical_web", "ALLOWED_DOMAINS_DEFAULT"]
