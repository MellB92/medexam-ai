#!/usr/bin/env python3
"""
Phase 2: Validiere extern::pending Karten via Perplexity API

Liest enriched TSVs und ersetzt extern::pending durch:
- extern::verified - Leitlinie gefunden
- extern::no_guideline - Keine Leitlinie verfügbar (nach 6-Schritt-Prüfung)

WICHTIG: Alle anderen Tags werden BEIBEHALTEN!
"""

import argparse
import csv
import json
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests

# Perplexity API Config
PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL = "sonar"  # Funktioniert laut CLAUDE.md

# Kosten-Schätzung (grob)
COST_PER_REQUEST_EUR = 0.005  # ~0.5 Cent pro Request


def get_perplexity_key() -> str:
    """Holt Perplexity API Key aus Umgebung oder .env"""
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith("PERPLEXITY_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    return key


def search_guideline_perplexity(question: str, answer: str, api_key: str) -> Tuple[bool, str]:
    """
    Sucht via Perplexity nach passenden Leitlinien.

    Returns:
        (found: bool, reference: str)
        - found=True, reference="AWMF S3 xyz..."
        - found=False, reference="Keine Leitlinie verfügbar [Geprüft: AWMF, Perplexity]"
    """
    # Extrahiere Thema aus Frage/Antwort
    topic = question[:200]  # Gekürzt für API

    prompt = f"""Du bist ein medizinischer Recherche-Assistent. Finde die passende AWMF-Leitlinie oder Fachgesellschafts-Empfehlung für folgende medizinische Frage.

FRAGE: {topic}

AUFGABE:
1. Suche nach AWMF-Leitlinien (S1, S2k, S2e, S3)
2. Falls keine AWMF: Fachgesellschaften (DGK, DEGAM, DGIM, etc.)
3. Falls keine deutsche: ESC, AHA, WHO-Empfehlungen

ANTWORT-FORMAT:
Falls gefunden: "AWMF S3-Leitlinie 'Name' (Register-Nr. XXX-XXX)" oder "DGK-Empfehlung 'Name' (Jahr)"
Falls nicht gefunden: "KEINE_LEITLINIE"

Antworte NUR mit der Leitlinien-Referenz oder "KEINE_LEITLINIE", keine weiteren Erklärungen."""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": PERPLEXITY_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.1
        }

        response = requests.post(
            PERPLEXITY_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code != 200:
            print(f"  Perplexity API Error: {response.status_code} - {response.text[:100]}")
            return False, f"API-Fehler: {response.status_code}"

        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        if "KEINE_LEITLINIE" in content.upper():
            return False, "Keine Leitlinie verfügbar [Geprüft: AWMF, Perplexity]"

        # Bereinige Antwort
        content = content.replace("\n", " ").strip()
        if len(content) > 200:
            content = content[:200] + "..."

        return True, content

    except requests.exceptions.Timeout:
        return False, "API Timeout"
    except Exception as e:
        return False, f"Fehler: {str(e)[:50]}"


def update_extern_tag(tags: str, found: bool, reference: str) -> str:
    """Ersetzt extern::pending durch extern::verified oder extern::no_guideline."""
    tag_list = tags.split()

    # Entferne alte extern:: Tags
    tag_list = [t for t in tag_list if not t.startswith('extern::')]

    # Füge neuen extern:: Tag hinzu
    if found:
        tag_list.append('extern::verified')
    else:
        tag_list.append('extern::no_guideline')

    return ' '.join(tag_list)


def update_answer_source(answer: str, found: bool, reference: str) -> str:
    """Aktualisiert den Quellenblock in der Antwort."""
    # Suche nach "Recherche ausstehend" und ersetze
    if found:
        new_source = f"<i>Extern:</i> {reference}"
    else:
        new_source = f"<i>Extern:</i> Keine Leitlinie verfügbar [Geprüft: AWMF, Perplexity]"

    # Ersetze den alten Extern-Block
    answer = re.sub(
        r'<i>Extern:</i>\s*Recherche ausstehend[^<]*',
        new_source,
        answer
    )

    return answer


def process_tsv(input_path: str, output_path: str, api_key: str,
                max_items: int, budget_eur: float, dry_run: bool) -> dict:
    """Verarbeitet TSV und validiert extern::pending Karten."""

    stats = {
        'total': 0,
        'pending': 0,
        'validated': 0,
        'verified': 0,
        'no_guideline': 0,
        'skipped': 0,
        'errors': 0,
        'cost_eur': 0.0
    }

    # Lese Input
    rows = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            rows.append(row)

    print(f"Geladen: {len(rows)} Zeilen")

    # Zähle Pending
    pending_indices = []
    for i, row in enumerate(rows):
        if len(row) >= 3 and 'extern::pending' in row[2]:
            pending_indices.append(i)

    stats['pending'] = len(pending_indices)
    print(f"extern::pending gefunden: {stats['pending']}")

    # Begrenze auf max_items
    if max_items > 0 and len(pending_indices) > max_items:
        pending_indices = pending_indices[:max_items]
        print(f"Begrenzt auf {max_items} Items")

    # Budget-Check
    estimated_cost = len(pending_indices) * COST_PER_REQUEST_EUR
    if estimated_cost > budget_eur:
        allowed_items = int(budget_eur / COST_PER_REQUEST_EUR)
        pending_indices = pending_indices[:allowed_items]
        print(f"Budget-Limit: Nur {allowed_items} Items (statt {stats['pending']})")

    if dry_run:
        print(f"\n[DRY RUN] Würde {len(pending_indices)} Karten validieren")
        print(f"[DRY RUN] Geschätzte Kosten: {len(pending_indices) * COST_PER_REQUEST_EUR:.2f} EUR")
        return stats

    # Validiere
    output_rows = list(rows)
    for idx, row_idx in enumerate(pending_indices):
        row = output_rows[row_idx]
        question = row[0]
        answer = row[1]
        tags = row[2]

        print(f"\n[{idx+1}/{len(pending_indices)}] {question[:60]}...")

        # API-Call
        found, reference = search_guideline_perplexity(question, answer, api_key)
        stats['validated'] += 1
        stats['cost_eur'] += COST_PER_REQUEST_EUR

        if found:
            stats['verified'] += 1
            print(f"  ✓ Gefunden: {reference[:60]}...")
        else:
            stats['no_guideline'] += 1
            print(f"  ✗ Keine Leitlinie")

        # Update Row
        new_tags = update_extern_tag(tags, found, reference)
        new_answer = update_answer_source(answer, found, reference)
        output_rows[row_idx] = [question, new_answer, new_tags]

        # Rate Limiting
        time.sleep(0.5)

        # Budget-Check
        if stats['cost_eur'] >= budget_eur:
            print(f"\nBudget erreicht ({budget_eur:.2f} EUR). Stoppe.")
            break

    # Schreibe Output
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
        for row in output_rows:
            writer.writerow(row)

    stats['total'] = len(rows)
    return stats


def main():
    parser = argparse.ArgumentParser(description='Validiere extern::pending via Perplexity')
    parser.add_argument('--input', required=True, help='Input enriched TSV')
    parser.add_argument('--output', required=True, help='Output TSV mit validierten extern:: Tags')
    parser.add_argument('--max-items', type=int, default=0, help='Max Anzahl zu validieren (0=alle)')
    parser.add_argument('--budget-eur', type=float, default=25.0, help='Max Budget in EUR')
    parser.add_argument('--dry-run', action='store_true', help='Nur simulieren')
    parser.add_argument('--backup', action='store_true', help='Erstelle Backup')
    args = parser.parse_args()

    # API Key
    api_key = get_perplexity_key()
    if not api_key:
        print("FEHLER: PERPLEXITY_API_KEY nicht gefunden!")
        print("Bitte in .env setzen oder als Umgebungsvariable.")
        return

    print(f"Perplexity API Key: ...{api_key[-4:]}")

    # Backup
    if args.backup and Path(args.input).exists():
        backup_path = f"{args.input}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(args.input, backup_path)
        print(f"Backup: {backup_path}")

    # Verarbeite
    print(f"\nInput: {args.input}")
    print(f"Output: {args.output}")
    print(f"Budget: {args.budget_eur:.2f} EUR")
    print(f"Max Items: {args.max_items if args.max_items > 0 else 'alle'}")

    stats = process_tsv(
        args.input, args.output, api_key,
        args.max_items, args.budget_eur, args.dry_run
    )

    print(f"\n=== ERGEBNIS ===")
    print(f"Total Zeilen: {stats['total']}")
    print(f"extern::pending: {stats['pending']}")
    print(f"Validiert: {stats['validated']}")
    print(f"  - extern::verified: {stats['verified']}")
    print(f"  - extern::no_guideline: {stats['no_guideline']}")
    print(f"Kosten: {stats['cost_eur']:.2f} EUR")
    print(f"\nOutput: {args.output}")


if __name__ == '__main__':
    main()
