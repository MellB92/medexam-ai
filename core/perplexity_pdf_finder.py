#!/usr/bin/env python3
"""
MedExamAI - Perplexity PDF Finder
=================================

Sucht nach PDF-Download-URLs für deutsche medizinische Leitlinien
via Perplexity Web-Suche.

Features:
- Optimierter System-Prompt für Leitlinien-PDFs
- JSON-Output für strukturierte Ergebnisse
- API-Key-Rotation für höhere Rate-Limits
- Retry-Logik mit Exponential Backoff

Environment:
- PERPLEXITY_API_KEY: Primärer API-Key
- PERPLEXITY_API_KEY_2: Fallback API-Key (optional)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class PDFSearchResult:
    """Ergebnis einer Perplexity-Suche nach einer Leitlinien-PDF."""

    guideline_name: str
    search_query: str
    pdf_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = "perplexity"
    searched_at: str = ""
    raw_response: str = ""
    success: bool = False
    error: Optional[str] = None


class PerplexityPDFFinder:
    """Sucht nach PDF-URLs für deutsche medizinische Leitlinien via Perplexity."""

    SYSTEM_PROMPT = """Du bist ein Experte für deutsche medizinische Leitlinien.

AUFGABE: Finde die offizielle PDF-Download-URL für die angegebene Leitlinie.

SUCHPRIORITÄT:
1. AWMF-Register (register.awmf.org/assets/guidelines/*.pdf)
2. Leitlinienprogramm Onkologie (leitlinienprogramm-onkologie.de)
3. Offizielle Fachgesellschaft-Websites (dgim.de, dgu.de, escardio.org, etc.)
4. Bundesbehörden (rki.de, bfarm.de)

OUTPUT FORMAT (STRICT JSON, keine Markdown-Codeblöcke):
{
    "pdf_urls": ["https://...", "..."],
    "awmf_number": "XXX-YYY" oder null,
    "title": "Vollständiger Titel",
    "version": "2023-XX",
    "society": "AWMF/DGIM/ESC/etc.",
    "confidence": "high/medium/low"
}

WICHTIG:
- Nur DIREKTE PDF-Links (*.pdf)
- Keine HTML-Seiten oder Landing-Pages
- Maximal 3 URL-Kandidaten
- Bei Unsicherheit: confidence="low"
- Antwort NUR als JSON, kein Text davor/danach"""

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        model: str = "sonar-pro",
        timeout: int = 60,
        max_retries: int = 3,
    ):
        """
        Initialisiert den PDF-Finder.

        Args:
            api_keys: Liste von Perplexity API-Keys (optional, aus ENV laden)
            model: Perplexity-Modell (default: sonar-pro)
            timeout: Request-Timeout in Sekunden
            max_retries: Maximale Retry-Versuche
        """
        self.api_keys = api_keys or self._load_api_keys()
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._key_index = 0

        if not self.api_keys:
            raise ValueError(
                "Keine Perplexity API-Keys gefunden. "
                "Setze PERPLEXITY_API_KEY oder PERPLEXITY_API_KEY_2"
            )

    def _load_api_keys(self) -> List[str]:
        """Lädt API-Keys aus Umgebungsvariablen."""
        keys = []
        k1 = os.getenv("PERPLEXITY_API_KEY")
        k2 = os.getenv("PERPLEXITY_API_KEY_2")
        if k1:
            keys.append(k1)
        if k2:
            keys.append(k2)
        return keys

    def _rotate_key(self) -> str:
        """Rotiert zwischen verfügbaren API-Keys."""
        key = self.api_keys[self._key_index % len(self.api_keys)]
        self._key_index += 1
        return key

    def _build_search_query(self, guideline_ref: str) -> str:
        """Erstellt optimierten Suchquery für Perplexity."""
        # AWMF-Nummer extrahieren falls vorhanden
        awmf_match = re.search(r"(\d{3}[-/]\d{3})", guideline_ref)

        if awmf_match:
            awmf_num = awmf_match.group(1).replace("/", "-")
            return f"AWMF Leitlinie {awmf_num} PDF Download register.awmf.org"

        # NVL-Nummer erkennen
        nvl_match = re.search(r"(nvl-\d{3})", guideline_ref, re.IGNORECASE)
        if nvl_match:
            nvl_num = nvl_match.group(1).lower()
            return f"Nationale VersorgungsLeitlinie {nvl_num} PDF Download AWMF"

        # Generischer Query - bereinigen
        clean_ref = re.sub(r"\([^)]*\)", "", guideline_ref)  # Klammern entfernen
        clean_ref = re.sub(r"[^\w\s\-äöüÄÖÜß]", " ", clean_ref)  # Sonderzeichen
        clean_ref = " ".join(clean_ref.split()[:8])  # Max 8 Wörter

        return f"{clean_ref} Leitlinie PDF Download Deutschland"

    def search_pdf_url(self, guideline_ref: str) -> PDFSearchResult:
        """
        Sucht nach der PDF-URL einer Leitlinie.

        Args:
            guideline_ref: Referenz zur Leitlinie (z.B. "AWMF 015-045" oder Titel)

        Returns:
            PDFSearchResult mit gefundenen URLs und Metadaten
        """
        query = self._build_search_query(guideline_ref)
        result = PDFSearchResult(
            guideline_name=guideline_ref,
            search_query=query,
            searched_at=datetime.now().isoformat(),
        )

        user_prompt = f"""Finde die offizielle PDF-Download-URL für:

LEITLINIE: {guideline_ref}

Suche auf: register.awmf.org, Fachgesellschaften, RKI, BfArM, escardio.org
Liefere NUR direkten PDF-Link (*.pdf), keine HTML-Seiten.

Antworte ausschließlich mit dem JSON-Objekt."""

        for attempt in range(self.max_retries):
            try:
                api_key = self._rotate_key()
                response = self._call_perplexity(api_key, user_prompt)

                result.raw_response = response
                parsed = self._parse_response(response)

                if parsed:
                    result.pdf_urls = parsed.get("pdf_urls", [])
                    result.metadata = {
                        "awmf_number": parsed.get("awmf_number"),
                        "title": parsed.get("title"),
                        "version": parsed.get("version"),
                        "society": parsed.get("society"),
                        "confidence": parsed.get("confidence", "low"),
                    }
                    result.success = len(result.pdf_urls) > 0

                    if result.success:
                        logger.debug(
                            f"Gefunden: {guideline_ref[:40]}... -> {len(result.pdf_urls)} URLs"
                        )
                    break

            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Rate limit erreicht, warte {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    continue
                result.error = str(e)
                logger.error(f"HTTP-Fehler: {e}")

            except requests.exceptions.RequestException as e:
                result.error = str(e)
                logger.error(f"Request-Fehler: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2**attempt)

            except Exception as e:
                result.error = str(e)
                logger.error(f"Unerwarteter Fehler: {e}")

        return result

    def _call_perplexity(self, api_key: str, user_prompt: str) -> str:
        """Führt Perplexity API-Call durch."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 800,
        }

        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _parse_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Extrahiert JSON aus Perplexity-Antwort."""
        if not text:
            return None

        # Code-Fences entfernen
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()

        # Versuche JSON zu parsen
        try:
            # Finde JSON-Objekt im Text
            json_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(text)
        except json.JSONDecodeError:
            # Regex-Fallback für PDF-URLs
            urls = re.findall(r"https?://[^\s\"'<>]+\.pdf", text)
            if urls:
                # Deduplizieren und validieren
                unique_urls = list(dict.fromkeys(urls))
                return {"pdf_urls": unique_urls[:3]}
            return None

    def search_batch(
        self,
        guidelines: List[str],
        delay: float = 1.0,
        progress_callback: Optional[callable] = None,
    ) -> List[PDFSearchResult]:
        """
        Sucht nach mehreren Leitlinien mit Delay zwischen Anfragen.

        Args:
            guidelines: Liste von Leitlinien-Referenzen
            delay: Pause zwischen Anfragen in Sekunden
            progress_callback: Optional - Callback(index, total, result)

        Returns:
            Liste von PDFSearchResult
        """
        results = []
        total = len(guidelines)

        for i, guideline in enumerate(guidelines):
            result = self.search_pdf_url(guideline)
            results.append(result)

            if progress_callback:
                progress_callback(i + 1, total, result)

            if i < total - 1 and delay > 0:
                time.sleep(delay)

        return results


# Convenience-Funktion
def find_guideline_pdf(guideline_ref: str, model: str = "sonar-pro") -> PDFSearchResult:
    """
    Einfache Funktion zum Finden einer Leitlinien-PDF.

    Args:
        guideline_ref: Referenz zur Leitlinie
        model: Perplexity-Modell

    Returns:
        PDFSearchResult
    """
    finder = PerplexityPDFFinder(model=model)
    return finder.search_pdf_url(guideline_ref)


if __name__ == "__main__":
    # Test
    import sys

    logging.basicConfig(level=logging.DEBUG)

    test_refs = [
        "AWMF 015-045_S2k_Endometriose_2020",
        "S3-Leitlinie Polytrauma (AWMF 187-023)",
        "ESC Guidelines Atrial Fibrillation 2024",
    ]

    ref = test_refs[0] if len(sys.argv) < 2 else sys.argv[1]
    print(f"\nSuche: {ref}")

    result = find_guideline_pdf(ref)
    print(f"Erfolg: {result.success}")
    print(f"URLs: {result.pdf_urls}")
    print(f"Metadaten: {result.metadata}")
    if result.error:
        print(f"Fehler: {result.error}")
