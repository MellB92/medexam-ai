#!/usr/bin/env python3
"""
MedExamAI - Automatischer Leitlinien-Download via Perplexity
============================================================

Lädt fehlende Leitlinien-PDFs automatisch herunter basierend auf
der Analyse in missing_guidelines_report.json.

Features:
- Resume-fähig via JSONL-Checkpoint
- Duplikat-Erkennung gegen existierendes Manifest
- PDF-Validierung (Header-Check, Mindestgröße)
- Automatische Fachgebiet-Zuordnung
- Manifest-Aktualisierung mit Metadaten

Usage:
    # Dry-Run Test
    python scripts/fetch_missing_guidelines_perplexity.py --dry-run --limit 5

    # Vollständiger Download mit Resume
    python scripts/fetch_missing_guidelines_perplexity.py --resume --sleep 1.5

    # Nur bestimmte Gesellschaft
    python scripts/fetch_missing_guidelines_perplexity.py --society AWMF --limit 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

# Projekt-Setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.perplexity_pdf_finder import PerplexityPDFFinder

# Pfade
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"
BIBLIOTHEK_DIR = PROJECT_ROOT / "_BIBLIOTHEK" / "Leitlinien"
MANIFEST_PATH = PROJECT_ROOT / "_BIBLIOTHEK" / "leitlinien_manifest.json"
MISSING_REPORT = OUTPUT_DIR / "missing_guidelines_report.json"
CHECKPOINT_PATH = OUTPUT_DIR / "guideline_search_progress.jsonl"
RESULTS_PATH = OUTPUT_DIR / "guideline_search_results.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Session mit User-Agent
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 MedExamAI-GuidelineFetcher/1.0",
        "Accept": "application/pdf,*/*",
    }
)

# Nicht-downloadbare Referenzen (Gesetze, generische Verweise)
NOT_DOWNLOADABLE_PATTERNS = [
    r"^IfSG",  # Infektionsschutzgesetz
    r"^StGB",  # Strafgesetzbuch
    r"^BGB",  # Bürgerliches Gesetzbuch
    r"^SGB",  # Sozialgesetzbuch
    r"aktuelle Fassung",
    r"z\.?\s*B\.",  # z.B.
    r"Standardwissen",
    r"Lehrbuch",
    r"Musterberufsordnung",
    r"^Bundesgesetz",
]

# Fachgebiet-Keywords
SPECIALTY_KEYWORDS = {
    "Kardiologie": ["herz", "kardio", "infarkt", "arrhythmie", "vorhof", "esc"],
    "Neurologie": ["neuro", "schlaganfall", "epilepsie", "meningitis", "hirn"],
    "Infektiologie": ["infekt", "sepsis", "hepatitis", "hiv", "antibiot"],
    "Chirurgie": ["chirurg", "appendiz", "hernie", "abdom"],
    "Unfallchirurgie": ["trauma", "fraktur", "polytrauma", "unfall"],
    "Onkologie": ["karzinom", "krebs", "tumor", "malignom", "leukämie"],
    "Pneumologie": ["pneum", "lunge", "asthma", "copd", "atemweg"],
    "Gastroenterologie": ["gastro", "leber", "pankrea", "gallen"],
    "Urologie": ["urol", "prostata", "niere", "blase"],
    "Diabetologie": ["diabetes", "glukose", "insulin"],
    "Psychiatrie": ["psych", "depression", "sucht"],
    "Notfallmedizin": ["notfall", "reanima", "anaphylax"],
    "Rheumatologie": ["rheuma", "arthritis", "gicht"],
    "Endokrinologie": ["schilddrüse", "thyreoid", "hormon"],
    "Dermatologie": ["haut", "derma", "ekzem"],
    "Gynäkologie": ["gynäk", "endometri", "schwanger"],
    "Hämatologie": ["hämat", "blut", "anämie", "thromboz"],
}

# Gesellschafts-Fachgebiete
SOCIETY_SPECIALTIES = {
    "DGK": "Kardiologie",
    "ESC": "Kardiologie",
    "DGN": "Neurologie",
    "DGIM": "Innere",
    "DGVS": "Gastroenterologie",
    "DGU": "Urologie",
    "DGE": "Endokrinologie",
    "STIKO": "Impfungen",
    "DGHO": "Hämatologie",
    "DGRh": "Rheumatologie",
    "KDIGO": "Nephrologie",
    "DVO": "Osteologie",
    "ERC": "Notfallmedizin",
}


def load_missing_report() -> Dict[str, List]:
    """Lädt die by_society Struktur aus missing_guidelines_report.json."""
    if not MISSING_REPORT.exists():
        raise FileNotFoundError(f"Missing report nicht gefunden: {MISSING_REPORT}")

    with open(MISSING_REPORT, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("by_society", {})


def load_existing_manifest() -> Set[str]:
    """Lädt existierende Leitlinien-Namen aus Manifest."""
    if not MANIFEST_PATH.exists():
        return set()

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    names = set()
    for entry in data.get("files", []):
        name = entry.get("name", "")
        if name:
            names.add(name.lower())
            # Auch AWMF-Nummer extrahieren
            match = re.search(r"(\d{3}[-_]\d{3})", name)
            if match:
                names.add(match.group(1).replace("_", "-"))

    return names


def load_checkpoint() -> Dict[str, Dict]:
    """Lädt bereits verarbeitete Einträge aus Checkpoint."""
    done = {}
    if not CHECKPOINT_PATH.exists():
        return done

    with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                key = obj.get("guideline_ref", "").strip()
                if key:
                    done[key] = obj
            except json.JSONDecodeError:
                continue

    return done


def save_checkpoint(entry: Dict) -> None:
    """Speichert einen Eintrag in den Checkpoint."""
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def is_not_downloadable(ref: str) -> bool:
    """Prüft ob eine Referenz nicht downloadbar ist (Gesetz, generisch, etc.)."""
    for pattern in NOT_DOWNLOADABLE_PATTERNS:
        if re.search(pattern, ref, re.IGNORECASE):
            return True
    return False


def is_duplicate(ref: str, existing: Set[str]) -> bool:
    """Prüft ob eine Leitlinie bereits existiert."""
    ref_lower = ref.lower()

    # Direkter Match
    if ref_lower in existing:
        return True

    # AWMF-Nummer Match
    match = re.search(r"(\d{3}[-/]\d{3})", ref)
    if match:
        awmf_num = match.group(1).replace("/", "-")
        if awmf_num in existing:
            return True

    return False


def validate_pdf_url(url: str, timeout: int = 30) -> Tuple[bool, int, str]:
    """
    Validiert ob URL zu einer echten PDF führt.

    Returns:
        (is_valid, size_bytes, error_message)
    """
    try:
        # HEAD-Request für Metadaten
        resp = SESSION.head(url, timeout=timeout, allow_redirects=True)

        if resp.status_code != 200:
            return False, 0, f"HTTP {resp.status_code}"

        content_type = resp.headers.get("content-type", "").lower()
        content_length = int(resp.headers.get("content-length", 0))

        # PDF-Check
        if "pdf" not in content_type and not url.endswith(".pdf"):
            return False, 0, f"Kein PDF: {content_type}"

        # Mindestgröße (50KB)
        if content_length < 50_000:
            return False, content_length, f"Zu klein: {content_length} bytes"

        return True, content_length, ""

    except requests.RequestException as e:
        return False, 0, str(e)


def download_pdf(
    url: str, output_path: Path, timeout: int = 120
) -> Tuple[bool, str]:
    """
    Lädt PDF herunter.

    Returns:
        (success, error_message)
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        resp = SESSION.get(url, timeout=timeout, stream=True)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verifizieren
        if output_path.stat().st_size < 10_000:
            output_path.unlink()
            return False, "Download zu klein"

        # PDF-Magic-Bytes prüfen
        with open(output_path, "rb") as f:
            header = f.read(8)
            if not header.startswith(b"%PDF"):
                output_path.unlink()
                return False, "Keine gültige PDF"

        return True, ""

    except Exception as e:
        if output_path.exists():
            output_path.unlink()
        return False, str(e)


def determine_specialty(ref: str, society: str) -> str:
    """Bestimmt das Fachgebiet basierend auf Referenz und Gesellschaft."""
    ref_lower = ref.lower()

    for specialty, keywords in SPECIALTY_KEYWORDS.items():
        for kw in keywords:
            if kw in ref_lower:
                return specialty

    # Fallback nach Gesellschaft
    return SOCIETY_SPECIALTIES.get(society, "Sonstige")


def generate_filename(ref: str, metadata: Dict, society: str) -> str:
    """Generiert sicheren Dateinamen für PDF."""
    # AWMF-Nummer extrahieren
    awmf_match = re.search(r"(\d{3}[-/]\d{3})", ref)
    awmf_num = awmf_match.group(1).replace("/", "-") if awmf_match else ""

    # Titel bereinigen
    title = metadata.get("title") or ref
    safe_title = re.sub(r"[^\w\s\-äöüÄÖÜß]", "", title)[:50].strip()
    safe_title = re.sub(r"\s+", "_", safe_title)

    if awmf_num:
        return f"{awmf_num}_{safe_title}.pdf"
    else:
        # Hash für eindeutigen Namen
        hash_suffix = hashlib.md5(ref.encode()).hexdigest()[:6]
        return f"{society}_{safe_title}_{hash_suffix}.pdf"


def update_manifest(new_entry: Dict) -> None:
    """Fügt neuen Eintrag zum Manifest hinzu."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"generated": "", "count": 0, "files": []}

    manifest["files"].append(new_entry)
    manifest["count"] = len(manifest["files"])
    manifest["generated"] = datetime.now().isoformat()

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def process_guideline(
    ref: str,
    society: str,
    finder: PerplexityPDFFinder,
    existing: Set[str],
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Verarbeitet eine einzelne Leitlinien-Referenz.

    Returns:
        Checkpoint-Eintrag mit Status
    """
    entry: Dict[str, Any] = {
        "guideline_ref": ref,
        "society": society,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "pdf_url": None,
        "local_path": None,
        "error": None,
        "metadata": {},
    }

    # Nicht-downloadbar Check
    if is_not_downloadable(ref):
        entry["status"] = "not_applicable"
        entry["error"] = "Nicht downloadbar (Gesetz/generisch)"
        return entry

    # Duplikat-Check
    if is_duplicate(ref, existing):
        entry["status"] = "duplicate"
        return entry

    # Perplexity-Suche
    logger.info(f"Suche: {ref[:60]}...")
    result = finder.search_pdf_url(ref)

    if not result.success or not result.pdf_urls:
        entry["status"] = "not_found"
        entry["error"] = result.error or "Keine PDF-URL gefunden"
        entry["metadata"] = result.metadata
        return entry

    # URL-Validierung
    for url in result.pdf_urls[:3]:
        is_valid, size, err = validate_pdf_url(url)

        if not is_valid:
            logger.debug(f"URL ungültig: {url} - {err}")
            continue

        entry["pdf_url"] = url
        entry["metadata"] = result.metadata
        entry["metadata"]["size_bytes"] = size

        if dry_run:
            entry["status"] = "dry_run_ok"
            logger.info(f"[DRY-RUN] Würde laden: {url}")
            return entry

        # Download
        specialty = determine_specialty(ref, society)
        filename = generate_filename(ref, result.metadata, society)
        output_path = BIBLIOTHEK_DIR / specialty / filename

        success, dl_err = download_pdf(url, output_path)

        if success:
            entry["status"] = "downloaded"
            entry["local_path"] = str(output_path.relative_to(PROJECT_ROOT))

            # Manifest aktualisieren
            manifest_entry = {
                "file": entry["local_path"],
                "name": filename.replace(".pdf", ""),
                "size": output_path.stat().st_size,
                "mtime": datetime.now().isoformat(),
                "source": "perplexity",
                "awmf_number": result.metadata.get("awmf_number"),
                "search_ref": ref,
            }
            update_manifest(manifest_entry)

            logger.info(f"✓ Heruntergeladen: {filename}")
            return entry
        else:
            entry["error"] = dl_err

    entry["status"] = "download_failed"
    entry["error"] = entry.get("error") or "Alle URLs fehlgeschlagen"
    return entry


def main():
    parser = argparse.ArgumentParser(
        description="Download fehlender Leitlinien via Perplexity"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Fortsetzen von Checkpoint"
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Maximal N Leitlinien verarbeiten"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Nur suchen, nicht downloaden"
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Pause zwischen Anfragen (Sekunden)",
    )
    parser.add_argument("--model", default="sonar-pro", help="Perplexity-Modell")
    parser.add_argument(
        "--society", default="", help="Nur bestimmte Gesellschaft verarbeiten"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("LEITLINIEN-DOWNLOAD VIA PERPLEXITY")
    print("=" * 60)

    # Laden
    try:
        missing = load_missing_report()
    except FileNotFoundError as e:
        logger.error(str(e))
        logger.info("Führe zuerst scripts/analyze_missing_guidelines.py aus")
        return 1

    existing = load_existing_manifest()
    checkpoint = load_checkpoint() if args.resume else {}

    logger.info(f"Existierende Leitlinien: {len(existing)}")
    logger.info(f"Bereits verarbeitet: {len(checkpoint)}")

    # Finder initialisieren
    try:
        finder = PerplexityPDFFinder(model=args.model)
    except ValueError as e:
        logger.error(str(e))
        return 1

    # Alle Referenzen sammeln
    all_refs: List[Tuple[str, str, int]] = []
    for society, refs in missing.items():
        if args.society and society.upper() != args.society.upper():
            continue
        for ref_tuple in refs:
            if isinstance(ref_tuple, list):
                ref_name = ref_tuple[0]
                count = ref_tuple[1] if len(ref_tuple) > 1 else 1
            else:
                ref_name = str(ref_tuple)
                count = 1
            all_refs.append((ref_name, society, count))

    # Nach Häufigkeit sortieren (häufigste zuerst)
    all_refs.sort(key=lambda x: x[2], reverse=True)

    logger.info(f"Zu verarbeiten: {len(all_refs)} Referenzen")

    if args.dry_run:
        print("\n[DRY-RUN MODUS - Keine Downloads]\n")

    # Statistiken
    stats = {
        "downloaded": 0,
        "duplicate": 0,
        "not_found": 0,
        "not_applicable": 0,
        "failed": 0,
        "skipped": 0,
    }

    processed = 0
    for ref, society, count in all_refs:
        if args.limit and processed >= args.limit:
            break

        # Skip wenn bereits im Checkpoint
        if ref in checkpoint:
            stats["skipped"] += 1
            continue

        # Verarbeiten
        entry = process_guideline(ref, society, finder, existing, dry_run=args.dry_run)

        # Checkpoint speichern
        save_checkpoint(entry)

        # Statistik
        status = entry.get("status", "unknown")
        if status == "downloaded" or status == "dry_run_ok":
            stats["downloaded"] += 1
        elif status == "duplicate":
            stats["duplicate"] += 1
        elif status == "not_found":
            stats["not_found"] += 1
        elif status == "not_applicable":
            stats["not_applicable"] += 1
        else:
            stats["failed"] += 1

        processed += 1

        # Rate-Limiting
        if args.sleep > 0 and processed < len(all_refs):
            time.sleep(args.sleep)

        # Progress alle 10
        if processed % 10 == 0:
            logger.info(f"Progress: {processed}/{len(all_refs)} - {stats}")

    # Finale Ergebnisse speichern
    final = load_checkpoint()
    results = {
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
        "total_processed": len(final),
        "items": list(final.values()),
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"  Heruntergeladen:    {stats['downloaded']}")
    print(f"  Duplikate:          {stats['duplicate']}")
    print(f"  Nicht gefunden:     {stats['not_found']}")
    print(f"  Nicht anwendbar:    {stats['not_applicable']}")
    print(f"  Fehlgeschlagen:     {stats['failed']}")
    print(f"  Übersprungen:       {stats['skipped']}")
    print(f"\nErgebnisse: {RESULTS_PATH}")
    print(f"Checkpoint: {CHECKPOINT_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
