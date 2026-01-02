#!/usr/bin/env python3
"""
Erweitert die Leitlinien-Bibliothek basierend auf der Output-Analyse.

Dieses Script:
1. Liest den Analyse-Bericht (missing_guidelines_report.json)
2. Identifiziert fehlende AWMF-Leitlinien
3. Lädt diese automatisch herunter
4. Aktualisiert das Manifest

Usage:
    python scripts/expand_guidelines.py [--dry-run] [--limit 10]
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import requests
from urllib.parse import urljoin
from datetime import datetime

# AWMF Leitlinien-Register URLs
AWMF_BASE_URL = "https://register.awmf.org"
AWMF_API_SEARCH = "https://register.awmf.org/api/v1/guidelines/search"

# Zusätzliche Leitlinien von anderen Quellen
ADDITIONAL_GUIDELINES = {
    # ESC Leitlinien (manuelle URLs)
    "ESC-Dyslipidaemia-2019": {
        "name": "ESC/EAS Guidelines for the management of dyslipidaemias",
        "url": "https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/Dyslipidaemias-Management-of",
        "manual": True
    },
    "ESC-HF-2021": {
        "name": "ESC Guidelines for the diagnosis and treatment of acute and chronic heart failure",
        "url": "https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/Acute-and-Chronic-Heart-Failure",
        "manual": True
    },
    # KDIGO Leitlinien
    "KDIGO-CKD-2024": {
        "name": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of CKD",
        "url": "https://kdigo.org/guidelines/ckd-evaluation-and-management/",
        "manual": True
    },
    # DVO Osteoporose
    "DVO-Osteoporose-2023": {
        "name": "DVO-Leitlinie Osteoporose 2023",
        "url": "https://dv-osteologie.org/osteoporose-leitlinien",
        "manual": True
    },
    # STIKO
    "STIKO-Impfkalender-2024": {
        "name": "STIKO Empfehlungen 2024",
        "url": "https://www.rki.de/DE/Content/Kommissionen/STIKO/Empfehlungen/Aktuelles/Impfkalender.html",
        "manual": True
    }
}

# Prioritäre AWMF-Nummern basierend auf Analyse
PRIORITY_AWMF = [
    # Rheumatologie
    "060-002",  # Rheumatoide Arthritis
    "060-025",  # Gichtarthritis
    # Endokrinologie
    "027-019",  # Hypothyreose
    "027-030",  # Hyperthyreose
    "174-002",  # Morbus Basedow
    # Gastroenterologie
    "021-016",  # Gastroösophageale Refluxkrankheit
    "021-008",  # Barrett-Ösophagus
    "021-027",  # Helicobacter pylori
    "021-025",  # Chronische Pankreatitis
    # Hämatologie
    "025-027",  # Diagnostik von Anämien
    "086-001",  # Heparin-induzierte Thrombozytopenie
    # Chirurgie
    "088-012",  # Akute Appendizitis
    "018-024",  # Leistenhernie
    # Notfallmedizin/Intensivmedizin
    "001-017",  # Delir
    "001-019",  # Intoxikationen
    # Orthopädie
    "033-004",  # Proximale Femurfraktur
    "012-022",  # Schenkelhalsfraktur
    # Dermatologie
    "013-048",  # Pruritus
    "013-001",  # Atopische Dermatitis
]


def search_awmf(awmf_number: str) -> Optional[Dict]:
    """Sucht eine Leitlinie im AWMF-Register."""
    try:
        # Formatiere Nummer
        if "-" not in awmf_number:
            awmf_number = f"{awmf_number[:3]}-{awmf_number[3:]}"

        url = f"{AWMF_BASE_URL}/de/leitlinien/{awmf_number}"
        headers = {"User-Agent": "MedExamAI-Guidelines-Fetcher/1.0"}

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Parse HTML für PDF-Link
            content = response.text

            # Suche nach PDF-Link
            pdf_pattern = re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE)
            pdf_matches = pdf_pattern.findall(content)

            if pdf_matches:
                # Bevorzuge vollständige Leitlinien
                for pdf_url in pdf_matches:
                    if "lang" not in pdf_url.lower() and "kurz" not in pdf_url.lower():
                        full_url = urljoin(AWMF_BASE_URL, pdf_url)
                        return {
                            "awmf_number": awmf_number,
                            "pdf_url": full_url,
                            "source": "AWMF"
                        }

                # Fallback: erstes PDF
                full_url = urljoin(AWMF_BASE_URL, pdf_matches[0])
                return {
                    "awmf_number": awmf_number,
                    "pdf_url": full_url,
                    "source": "AWMF"
                }

        return None
    except Exception as e:
        print(f"  ⚠ Fehler bei AWMF-Suche für {awmf_number}: {e}")
        return None


def download_pdf(url: str, output_path: Path) -> bool:
    """Lädt ein PDF herunter."""
    try:
        headers = {"User-Agent": "MedExamAI-Guidelines-Fetcher/1.0"}
        response = requests.get(url, headers=headers, timeout=60, stream=True)

        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"  ⚠ Download-Fehler: {e}")
        return False


def update_manifest(bibliothek_path: Path):
    """Aktualisiert das Leitlinien-Manifest."""
    manifest_path = bibliothek_path.parent / "leitlinien_manifest.json"

    pdfs = []
    for pdf in bibliothek_path.rglob("*.pdf"):
        stat = pdf.stat()
        pdfs.append({
            "file": str(pdf.relative_to(bibliothek_path.parent)),
            "name": pdf.stem,
            "size": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })

    manifest = {
        "generated": datetime.now().isoformat(),
        "count": len(pdfs),
        "files": sorted(pdfs, key=lambda x: x["file"])
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return len(pdfs)


def main():
    parser = argparse.ArgumentParser(description="Erweitert die Leitlinien-Bibliothek")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Nur anzeigen, was heruntergeladen würde")
    parser.add_argument("--limit", "-l", type=int, default=20,
                        help="Maximale Anzahl der Downloads")
    parser.add_argument("--report", default="_OUTPUT/missing_guidelines_report.json",
                        help="Pfad zum Analyse-Bericht")
    parser.add_argument("--output", default="_BIBLIOTHEK/Leitlinien",
                        help="Ausgabeverzeichnis für Leitlinien")
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent
    report_path = base_path / args.report
    output_path = base_path / args.output

    print("=" * 60)
    print("LEITLINIEN-ERWEITERUNG")
    print("=" * 60)

    # Lade Analyse-Bericht
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        print(f"\n✓ Analyse-Bericht geladen: {report_path}")
    else:
        print(f"\n⚠ Kein Analyse-Bericht gefunden: {report_path}")
        print("  Führe zuerst 'python scripts/analyze_missing_guidelines.py' aus")
        report = {"download_recommendations": []}

    # Sammle alle AWMF-Nummern
    awmf_to_download = set()

    # Aus Bericht
    for rec in report.get("download_recommendations", []):
        if rec.get("awmf_number"):
            awmf_to_download.add(rec["awmf_number"])

    # Prioritäre Leitlinien
    awmf_to_download.update(PRIORITY_AWMF)

    print(f"\n{len(awmf_to_download)} AWMF-Leitlinien identifiziert")

    # Prüfe vorhandene
    existing = set()
    for pdf in output_path.rglob("*.pdf"):
        # Extrahiere AWMF-Nummer aus Dateiname
        match = re.search(r"(\d{3}[-_]\d{3})", pdf.name)
        if match:
            existing.add(match.group(1).replace("_", "-"))

    to_download = awmf_to_download - existing
    print(f"  → {len(existing)} bereits vorhanden")
    print(f"  → {len(to_download)} zum Download")

    if args.dry_run:
        print("\n[DRY RUN] Würde folgende Leitlinien herunterladen:")
        for awmf in sorted(list(to_download)[:args.limit]):
            print(f"  - AWMF {awmf}")
        return

    # Download
    downloaded = 0
    failed = []

    print(f"\n=== Starte Download (max. {args.limit}) ===")
    for awmf in sorted(list(to_download)[:args.limit]):
        print(f"\n[{downloaded+1}/{min(len(to_download), args.limit)}] AWMF {awmf}")

        result = search_awmf(awmf)
        if result and result.get("pdf_url"):
            pdf_url = result["pdf_url"]
            filename = f"{awmf.replace('-', '-')}_{Path(pdf_url).stem}.pdf"
            output_file = output_path / filename

            print(f"  → Lade herunter: {pdf_url[:60]}...")
            if download_pdf(pdf_url, output_file):
                print(f"  ✓ Gespeichert: {output_file.name}")
                downloaded += 1
            else:
                failed.append(awmf)
        else:
            print(f"  ⚠ Kein PDF gefunden")
            failed.append(awmf)

        # Rate limiting
        time.sleep(1)

    # Manifest aktualisieren
    print(f"\n=== Aktualisiere Manifest ===")
    total_pdfs = update_manifest(output_path)
    print(f"  → {total_pdfs} PDFs in Bibliothek")

    # Zusammenfassung
    print("\n" + "=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Heruntergeladen: {downloaded}")
    print(f"Fehlgeschlagen: {len(failed)}")
    if failed:
        print(f"\nFehlgeschlagene AWMF-Nummern:")
        for awmf in failed:
            print(f"  - {awmf}")

    print(f"\n=== Manuelle Downloads erforderlich ===")
    for key, info in ADDITIONAL_GUIDELINES.items():
        print(f"\n{info['name']}:")
        print(f"  URL: {info['url']}")

    print("""
NÄCHSTE SCHRITTE:
1. Manuelle Leitlinien von ESC, KDIGO, DVO herunterladen
2. RAG-Index neu bauen:
   python scripts/build_rag_index.py --clear-checkpoint --include-web-sources
3. Antworten mit Evidenzlücken neu generieren
""")


if __name__ == "__main__":
    main()
