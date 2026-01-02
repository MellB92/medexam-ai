#!/usr/bin/env python3
"""Search the web for image candidates and build an image_map.csv.

Sources:
- Wikimedia Commons (license-aware, auto-select)
- Brave Search (optional, domain-limited; license may be unknown)

Outputs:
- image_search_results.jsonl (debug, optional)
- image_map.csv (one selected image per card; can be edited manually)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

import requests

WIKIMEDIA_API = "https://commons.wikimedia.org/w/api.php"
BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"

# Wikimedia requires a descriptive User-Agent (otherwise 403).
# See: https://meta.wikimedia.org/wiki/User-Agent_policy
DEFAULT_USER_AGENT = "Medexamenai_Migration/1.0 (educational; https://github.com/MellB92/medexam-ai)"

ALLOWED_LICENSE_SNIPPETS = [
    "CC BY",
    "CC BY-SA",
    "CC BY-NC",
    "CC BY-NC-SA",
    "CC0",
    "Public domain",
    "PD",
]

DOMAIN_LICENSE_MAP = {
    "radiopaedia.org": "CC BY-NC-SA 3.0",
}

DEFAULT_ALLOWED_DOMAINS = [
    "commons.wikimedia.org",
    "wikipedia.org",
    "radiopaedia.org",
]

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _license_ok(license_name: str) -> bool:
    if not license_name:
        return False
    for token in ALLOWED_LICENSE_SNIPPETS:
        if token.lower() in license_name.lower():
            return True
    return False


def _safe_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    h = dict(headers or {})
    h.setdefault("User-Agent", DEFAULT_USER_AGENT)
    resp = requests.get(url, params=params, headers=h, timeout=40)
    resp.raise_for_status()
    return resp.json()


def _wikimedia_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srnamespace": 6,  # File:
        "srlimit": max_results,
        "format": "json",
    }
    data = _safe_get(WIKIMEDIA_API, params=params)
    search_results = (data.get("query") or {}).get("search") or []
    titles = [r.get("title") for r in search_results if r.get("title")]
    if not titles:
        return []

    params = {
        "action": "query",
        "prop": "imageinfo",
        "titles": "|".join(titles[:max_results]),
        "iiprop": "url|extmetadata|size",
        "iiurlwidth": 1200,
        "format": "json",
    }
    data = _safe_get(WIKIMEDIA_API, params=params)
    pages = (data.get("query") or {}).get("pages") or {}

    results: List[Dict[str, Any]] = []
    for page in pages.values():
        title = page.get("title") or ""
        imageinfo = (page.get("imageinfo") or [{}])[0]
        if not imageinfo:
            continue

        ext = imageinfo.get("extmetadata") or {}
        license_name = _strip_html((ext.get("LicenseShortName") or {}).get("value") or "")
        if not license_name:
            license_name = _strip_html((ext.get("UsageTerms") or {}).get("value") or "")
        license_url = (ext.get("LicenseUrl") or {}).get("value") or ""
        attribution = _strip_html((ext.get("Attribution") or {}).get("value") or "")
        if not attribution:
            attribution = _strip_html((ext.get("Artist") or {}).get("value") or "")

        image_url = imageinfo.get("thumburl") or imageinfo.get("url") or ""
        page_url = imageinfo.get("descriptionurl") or ""

        result = {
            "provider": "wikimedia",
            "title": title,
            "image_url": image_url,
            "page_url": page_url,
            "license": license_name,
            "license_url": license_url,
            "attribution": attribution,
            "width": imageinfo.get("width"),
            "height": imageinfo.get("height"),
            "license_ok": _license_ok(license_name),
        }
        results.append(result)

    return results


def _extract_og_image(html: str) -> str:
    meta_patterns = [
        r"<meta[^>]+property=['\"]og:image['\"][^>]+content=['\"]([^'\"]+)['\"][^>]*>",
        r"<meta[^>]+name=['\"]twitter:image['\"][^>]+content=['\"]([^'\"]+)['\"][^>]*>",
        r"<link[^>]+rel=['\"]image_src['\"][^>]+href=['\"]([^'\"]+)['\"][^>]*>",
    ]
    for pat in meta_patterns:
        m = re.search(pat, html, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return ""


def _fetch_og_image(page_url: str) -> str:
    resp = requests.get(page_url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=40)
    resp.raise_for_status()
    html = resp.text
    img = _extract_og_image(html)
    if not img:
        return ""
    if img.startswith("/"):
        return urljoin(page_url, img)
    return img


def _is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
    if not url:
        return False
    netloc = urlparse(url).netloc.lower()
    for d in allowed_domains:
        if netloc.endswith(d.lower()):
            return True
    return False


def _brave_search(query: str, max_results: int, allowed_domains: List[str], sleep_s: float) -> List[Dict[str, Any]]:
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return []

    headers = {
        "X-Subscription-Token": api_key,
        "Accept": "application/json",
    }
    params = {
        "q": query,
        "count": max_results,
        "search_lang": "de",
        "safesearch": "moderate",
    }

    data = _safe_get(BRAVE_API_URL, params=params, headers=headers)
    results = []
    raw_results = []
    if isinstance(data.get("web"), dict):
        raw_results = data.get("web", {}).get("results", [])
    elif isinstance(data.get("results"), list):
        raw_results = data.get("results", [])

    for r in raw_results[:max_results]:
        url = r.get("url") or r.get("link") or ""
        if not url or not _is_allowed_domain(url, allowed_domains):
            continue

        image_url = ""
        try:
            image_url = _fetch_og_image(url)
        except Exception:
            image_url = ""

        if image_url and not image_url.lower().endswith(IMAGE_EXTS):
            # still allow if it looks like an image proxy
            if "image" not in image_url.lower():
                image_url = ""

        domain = urlparse(url).netloc.lower()
        license_name = ""
        for dom, lic in DOMAIN_LICENSE_MAP.items():
            if domain.endswith(dom):
                license_name = lic
                break

        results.append({
            "provider": "brave",
            "title": r.get("title") or "",
            "image_url": image_url,
            "page_url": url,
            "license": license_name or "unknown",
            "license_url": "",
            "attribution": "",
            "width": None,
            "height": None,
            "license_ok": _license_ok(license_name) if license_name else False,
        })

        if sleep_s:
            time.sleep(sleep_s)

    return results


def _pick_best(results: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], bool]:
    if not results:
        return None, False

    for r in results:
        if r.get("image_url") and r.get("license_ok"):
            return r, False

    for r in results:
        if r.get("image_url"):
            return r, True

    return None, False


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="in_path", required=True, help="image_candidates.jsonl")
    parser.add_argument("--out-results", dest="out_results", required=True, help="image_search_results.jsonl")
    parser.add_argument("--out-map", dest="out_map", required=True, help="image_map.csv")
    parser.add_argument("--providers", default="wikimedia", help="Comma-separated: wikimedia,brave")
    parser.add_argument("--max-results", type=int, default=5, help="Max results per provider")
    parser.add_argument("--allowed-domains", default=",".join(DEFAULT_ALLOWED_DOMAINS))
    parser.add_argument("--limit", type=int, default=0, help="Limit number of candidates")
    parser.add_argument("--sleep", type=float, default=0.0, help="Sleep between Brave page fetches")
    args = parser.parse_args()

    providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
    allowed_domains = [d.strip() for d in args.allowed_domains.split(",") if d.strip()]

    out_results = Path(args.out_results)
    out_map = Path(args.out_map)
    out_results.parent.mkdir(parents=True, exist_ok=True)
    out_map.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    selected = 0

    with out_results.open("w", encoding="utf-8") as f_results, out_map.open("w", encoding="utf-8", newline="") as f_map:
        writer = csv.writer(f_map)
        writer.writerow([
            "card_id",
            "source_ref",
            "image_type",
            "query",
            "provider",
            "image_url",
            "page_url",
            "license",
            "license_url",
            "attribution",
            "local_file",
            "needs_review",
        ])

        for cand in iter_jsonl(Path(args.in_path)):
            if args.limit and count >= args.limit:
                break
            count += 1

            query = cand.get("query") or ""
            results: List[Dict[str, Any]] = []

            if "wikimedia" in providers:
                try:
                    results.extend(_wikimedia_search(query, max_results=args.max_results))
                except Exception:
                    pass

            if "brave" in providers:
                try:
                    results.extend(_brave_search(query, args.max_results, allowed_domains, args.sleep))
                except Exception:
                    pass

            for r in results:
                f_results.write(json.dumps({"card_id": cand.get("card_id"), "query": query, "result": r}, ensure_ascii=False) + "\n")

            picked, needs_review = _pick_best(results)
            if picked:
                selected += 1
                writer.writerow([
                    cand.get("card_id"),
                    cand.get("source_ref", ""),
                    cand.get("image_type", ""),
                    query,
                    picked.get("provider", ""),
                    picked.get("image_url", ""),
                    picked.get("page_url", ""),
                    picked.get("license", ""),
                    picked.get("license_url", ""),
                    picked.get("attribution", ""),
                    "",
                    "yes" if needs_review else "",
                ])

    print(f"Candidates processed: {count}")
    print(f"Selected images: {selected}")
    print(f"Results: {out_results}")
    print(f"Map: {out_map}")


if __name__ == "__main__":
    main()
