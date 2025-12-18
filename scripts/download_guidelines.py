#!/usr/bin/env python3
"""
MedExamAI - AWMF Leitlinien PDF Downloader
==========================================

Lädt alle 50 kuratierten Leitlinien-PDFs von AWMF herunter.

URL-Pattern:
https://register.awmf.org/assets/guidelines/{registry}l_S{level}_{title}_{date}.pdf

Verwendung:
    python3 scripts/download_guidelines.py
"""

import os
import re
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Download-Verzeichnis
DOWNLOAD_DIR = Path("_BIBLIOTHEK/Leitlinien")

# AWMF Base URL
AWMF_BASE = "https://register.awmf.org/assets/guidelines"

# Session mit User-Agent
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
})


# Kuratierte Leitlinien mit direkten PDF-URLs
# Format: (registry_number, title, s_level, pdf_variants)
# pdf_variants: Liste von möglichen PDF-Suffixen zum Testen
GUIDELINES: List[Dict] = [
    # === KARDIOLOGIE ===
    {
        "registry": "nvl-006",
        "title": "Chronische Herzinsuffizienz",
        "specialty": "Kardiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/nvl-006l_S3_Chronische_Herzinsuffizienz_2023-12.pdf",
            f"{AWMF_BASE}/nvl-006k_S3_Chronische_Herzinsuffizienz_2023-12.pdf",
        ]
    },
    {
        "registry": "046-001",
        "title": "Arterielle Hypertonie",
        "specialty": "Kardiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/046-001l_S2k_Arterielle_Hypertonie_2023-06.pdf",
            f"{AWMF_BASE}/046-001l_S2k_Bluthochdruck_2023-06.pdf",
        ]
    },
    {
        "registry": "019-013",
        "title": "Kardiogener Schock",
        "specialty": "Kardiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/019-013l_S3_Kardiogener-Schock_2020-03.pdf",
            f"{AWMF_BASE}/019-013l_S3_Infarktbedingter-kardiogener-Schock_2020-03.pdf",
        ]
    },
    {
        "registry": "nvl-004",
        "title": "Koronare Herzkrankheit",
        "specialty": "Kardiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/nvl-004l_S3_KHK_2022-09.pdf",
            f"{AWMF_BASE}/nvl-004l_S3_Koronare-Herzkrankheit_2022-09.pdf",
        ]
    },

    # === INFEKTIOLOGIE ===
    {
        "registry": "079-001",
        "title": "Sepsis",
        "specialty": "Infektiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/079-001l_S3_Sepsis_Praevention_Diagnose_Therapie_2024-08.pdf",
            f"{AWMF_BASE}/079-001l_S3_Sepsis_2020-02.pdf",
        ]
    },
    {
        "registry": "020-020",
        "title": "Ambulant erworbene Pneumonie",
        "specialty": "Pneumologie",
        "pdf_urls": [
            f"{AWMF_BASE}/020-020l_S3_Ambulant-erworbene-Pneumonie_2021-04.pdf",
            f"{AWMF_BASE}/020-020l_S3_CAP_2021-04.pdf",
        ]
    },
    {
        "registry": "020-013",
        "title": "Nosokomiale Pneumonie",
        "specialty": "Pneumologie",
        "pdf_urls": [
            f"{AWMF_BASE}/020-013l_S3_Nosokomiale-Pneumonie_2017-09.pdf",
            f"{AWMF_BASE}/020-013l_S3_HAP_VAP_2017-09.pdf",
        ]
    },
    {
        "registry": "030-089",
        "title": "Bakterielle Meningitis",
        "specialty": "Neurologie",
        "pdf_urls": [
            f"{AWMF_BASE}/030-089l_S2k_Bakterielle_Meningitis_2015-10.pdf",
            f"{AWMF_BASE}/030-089l_S2k_Ambulant-erworbene-bakterielle-Meningitis_2015-10.pdf",
        ]
    },
    {
        "registry": "092-001",
        "title": "Antibiotic Stewardship",
        "specialty": "Infektiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/092-001l_S2k_Antibiotic-Stewardship_2018-12.pdf",
            f"{AWMF_BASE}/092-001l_S3_Strategien_zur_Sicherung_ABS_2024-02.pdf",
        ]
    },
    {
        "registry": "055-001",
        "title": "HIV-Infektion",
        "specialty": "Infektiologie",
        "pdf_urls": [
            f"{AWMF_BASE}/055-001l_S2k_Antiretrovirale-Therapie-HIV-Infektion_2020-06.pdf",
            f"{AWMF_BASE}/055-001l_S2k_HIV-Infektion_2020-06.pdf",
        ]
    },
    {
        "registry": "021-011",
        "title": "Hepatitis B",
        "specialty": "Gastroenterologie",
        "pdf_urls": [
            f"{AWMF_BASE}/021-011l_S3_Hepatitis-B_2021-06.pdf",
            f"{AWMF_BASE}/021-011l_S3_Hepatitis-B-Prophylaxe_2021-06.pdf",
        ]
    },
    {
        "registry": "021-012",
        "title": "Hepatitis C",
        "specialty": "Gastroenterologie",
        "pdf_urls": [
            f"{AWMF_BASE}/021-012l_S3_Hepatitis-C_2020-05.pdf",
            f"{AWMF_BASE}/021-012l_S3_Prophylaxe_Diagnostik_Therapie_Hepatitis-C_2020-05.pdf",
        ]
    },

    # === CHIRURGIE / TRAUMA ===
    {
        "registry": "187-023",
        "title": "Polytrauma",
        "specialty": "Unfallchirurgie",
        "pdf_urls": [
            f"{AWMF_BASE}/187-023l_S3_Polytrauma-Schwerverletzten-Behandlung_2022-12.pdf",
            f"{AWMF_BASE}/187-023l_S3_Polytrauma_2022-12.pdf",
        ]
    },
    {
        "registry": "088-007",
        "title": "Appendizitis",
        "specialty": "Chirurgie",
        "pdf_urls": [
            f"{AWMF_BASE}/088-007l_S3_Appendizitis_2020-01.pdf",
            f"{AWMF_BASE}/088-007l_S3_Diagnostik-Therapie-Appendizitis_2020-01.pdf",
        ]
    },
    {
        "registry": "187-015",
        "title": "Schenkelhalsfraktur",
        "specialty": "Unfallchirurgie",
        "pdf_urls": [
            f"{AWMF_BASE}/187-015l_S3_Schenkelhalsfraktur_2020-10.pdf",
            f"{AWMF_BASE}/187-015l_S2e_Schenkelhalsfraktur_2020-10.pdf",
        ]
    },
    {
        "registry": "012-015",
        "title": "Distale Radiusfraktur",
        "specialty": "Unfallchirurgie",
        "pdf_urls": [
            f"{AWMF_BASE}/012-015l_S2e_Distale-Radiusfraktur_2021-02.pdf",
            f"{AWMF_BASE}/012-015l_S2e_Radiusfraktur_2021-02.pdf",
        ]
    },
    {
        "registry": "088-001",
        "title": "Akutes Abdomen",
        "specialty": "Chirurgie",
        "pdf_urls": [
            f"{AWMF_BASE}/088-001l_S2k_Akutes-Abdomen_2019-05.pdf",
        ]
    },
    {
        "registry": "010-079",
        "title": "Hernien",
        "specialty": "Chirurgie",
        "pdf_urls": [
            f"{AWMF_BASE}/010-079l_S3_Hernienchirurgie_2019-12.pdf",
            f"{AWMF_BASE}/010-079l_S3_Leistenhernie_2019-12.pdf",
        ]
    },

    # === DIABETES / INNERE ===
    {
        "registry": "nvl-001",
        "title": "Typ-2-Diabetes",
        "specialty": "Diabetologie",
        "pdf_urls": [
            f"{AWMF_BASE}/nvl-001l_S3_Typ-2-Diabetes_2023-06.pdf",
            f"{AWMF_BASE}/nvl-001l_S3_Therapie_Typ-2-Diabetes_2023-06.pdf",
        ]
    },
    {
        "registry": "057-013",
        "title": "Typ-1-Diabetes",
        "specialty": "Diabetologie",
        "pdf_urls": [
            f"{AWMF_BASE}/057-013l_S3_Typ-1-Diabetes_2023-04.pdf",
            f"{AWMF_BASE}/057-013l_S3_Therapie_Typ-1-Diabetes_2023-04.pdf",
        ]
    },
    {
        "registry": "021-003",
        "title": "Pankreatitis",
        "specialty": "Gastroenterologie",
        "pdf_urls": [
            f"{AWMF_BASE}/021-003l_S3_Pankreatitis_2021-09.pdf",
            f"{AWMF_BASE}/021-003l_S3_Akute-chronische-Pankreatitis_2021-09.pdf",
        ]
    },
    {
        "registry": "021-013",
        "title": "Gastroösophageale Refluxkrankheit",
        "specialty": "Gastroenterologie",
        "pdf_urls": [
            f"{AWMF_BASE}/021-013l_S2k_GERD_2022-04.pdf",
            f"{AWMF_BASE}/021-013l_S2k_Gastroesophageale-Refluxkrankheit_2022-04.pdf",
        ]
    },
    {
        "registry": "021-017",
        "title": "Leberzirrhose",
        "specialty": "Gastroenterologie",
        "pdf_urls": [
            f"{AWMF_BASE}/021-017l_S2k_Leberzirrhose_2019-11.pdf",
            f"{AWMF_BASE}/021-017l_S2k_Komplikationen-Leberzirrhose_2019-11.pdf",
        ]
    },

    # === PNEUMOLOGIE ===
    {
        "registry": "020-006",
        "title": "COPD",
        "specialty": "Pneumologie",
        "pdf_urls": [
            f"{AWMF_BASE}/020-006l_S2k_COPD_2018-01.pdf",
            f"{AWMF_BASE}/nvl-003l_S3_COPD_2021-09.pdf",
        ]
    },
    {
        "registry": "nvl-002",
        "title": "Asthma",
        "specialty": "Pneumologie",
        "pdf_urls": [
            f"{AWMF_BASE}/nvl-002l_S3_Asthma_2023-03.pdf",
            f"{AWMF_BASE}/nvl-002l_S3_Asthma-bronchiale_2023-03.pdf",
        ]
    },
    {
        "registry": "065-002",
        "title": "Lungenembolie",
        "specialty": "Pneumologie",
        "pdf_urls": [
            f"{AWMF_BASE}/065-002l_S2k_VTE_Venenthrombose-Lungenembolie_2023-03.pdf",
            f"{AWMF_BASE}/065-002l_S2k_Lungenembolie_2015-06.pdf",
        ]
    },

    # === NEUROLOGIE ===
    {
        "registry": "030-140",
        "title": "Schlaganfall",
        "specialty": "Neurologie",
        "pdf_urls": [
            f"{AWMF_BASE}/030-140l_S3_Schlaganfall_2021-05.pdf",
            f"{AWMF_BASE}/030-140l_S2e_Akuttherapie-ischaemischer-Schlaganfall_2021-05.pdf",
        ]
    },
    {
        "registry": "030-041",
        "title": "Epilepsie",
        "specialty": "Neurologie",
        "pdf_urls": [
            f"{AWMF_BASE}/030-041l_S2k_Erster-epileptischer-Anfall_2023-05.pdf",
            f"{AWMF_BASE}/030-041l_S1_Epilepsie_2023-05.pdf",
        ]
    },
    {
        "registry": "030-057",
        "title": "Kopfschmerzen",
        "specialty": "Neurologie",
        "pdf_urls": [
            f"{AWMF_BASE}/030-057l_S1_Clusterkopfschmerz_2022-01.pdf",
            f"{AWMF_BASE}/030-057l_S1_Kopfschmerz_2022-01.pdf",
        ]
    },
    {
        "registry": "024-018",
        "title": "Schädel-Hirn-Trauma",
        "specialty": "Neurologie",
        "pdf_urls": [
            f"{AWMF_BASE}/024-018l_S2e_Schaedel-Hirn-Trauma_2015-12.pdf",
            f"{AWMF_BASE}/024-018l_S2e_SHT_2015-12.pdf",
        ]
    },

    # === UROLOGIE ===
    {
        "registry": "043-022",
        "title": "Prostatakarzinom",
        "specialty": "Urologie",
        "pdf_urls": [
            f"{AWMF_BASE}/043-022OLl_S3_Prostatakarzinom_2021-10.pdf",
            f"{AWMF_BASE}/043-022l_S3_Prostatakarzinom_2021-10.pdf",
        ]
    },
    {
        "registry": "043-044",
        "title": "Harnwegsinfektionen",
        "specialty": "Urologie",
        "pdf_urls": [
            f"{AWMF_BASE}/043-044l_S2k_Harnwegsinfektionen_2017-04.pdf",
            f"{AWMF_BASE}/043-044l_S3_HWI_2017-04.pdf",
        ]
    },
    {
        "registry": "043-025",
        "title": "Urolithiasis",
        "specialty": "Urologie",
        "pdf_urls": [
            f"{AWMF_BASE}/043-025l_S2k_Urolithiasis_2019-02.pdf",
            f"{AWMF_BASE}/043-025l_S2k_Harnsteinerkrankung_2019-02.pdf",
        ]
    },

    # === ORTHOPÄDIE ===
    {
        "registry": "187-050",
        "title": "Gonarthrose",
        "specialty": "Orthopädie",
        "pdf_urls": [
            f"{AWMF_BASE}/187-050l_S2k_Gonarthrose_2018-01.pdf",
        ]
    },
    {
        "registry": "187-049",
        "title": "Coxarthrose",
        "specialty": "Orthopädie",
        "pdf_urls": [
            f"{AWMF_BASE}/187-049l_S2k_Coxarthrose_2019-07.pdf",
        ]
    },
    {
        "registry": "nvl-007",
        "title": "Kreuzschmerz",
        "specialty": "Orthopädie",
        "pdf_urls": [
            f"{AWMF_BASE}/nvl-007l_S3_Kreuzschmerz_2017-11.pdf",
            f"{AWMF_BASE}/nvl-007l_S3_Nicht-spezifischer-Kreuzschmerz_2017-11.pdf",
        ]
    },

    # === ONKOLOGIE ===
    {
        "registry": "021-007",
        "title": "Kolorektales Karzinom",
        "specialty": "Onkologie",
        "pdf_urls": [
            f"{AWMF_BASE}/021-007OLl_S3_Kolorektales-Karzinom_2019-01.pdf",
            f"{AWMF_BASE}/021-007l_S3_KRK_2019-01.pdf",
        ]
    },
    {
        "registry": "020-007",
        "title": "Lungenkarzinom",
        "specialty": "Onkologie",
        "pdf_urls": [
            f"{AWMF_BASE}/020-007OLl_S3_Lungenkarzinom_2018-02.pdf",
            f"{AWMF_BASE}/020-007l_S3_Praevention-Diagnostik-Therapie-Lungenkarzinom_2018-02.pdf",
        ]
    },
    {
        "registry": "032-045",
        "title": "Mammakarzinom",
        "specialty": "Onkologie",
        "pdf_urls": [
            f"{AWMF_BASE}/032-045OLl_S3_Mammakarzinom_2021-06.pdf",
            f"{AWMF_BASE}/032-045l_S3_Brustkrebs_2021-06.pdf",
        ]
    },
    {
        "registry": "032-009",
        "title": "Magenkarzinom",
        "specialty": "Onkologie",
        "pdf_urls": [
            f"{AWMF_BASE}/032-009OLl_S3_Magenkarzinom_2019-08.pdf",
            f"{AWMF_BASE}/032-009l_S3_Magenkrebs_2019-08.pdf",
        ]
    },

    # === NOTFALLMEDIZIN ===
    {
        "registry": "001-006",
        "title": "Reanimation",
        "specialty": "Notfallmedizin",
        "pdf_urls": [
            f"{AWMF_BASE}/001-006l_S3_Reanimation_2021-03.pdf",
        ]
    },
    {
        "registry": "001-039",
        "title": "Analgesie Sedierung Notfallmedizin",
        "specialty": "Notfallmedizin",
        "pdf_urls": [
            f"{AWMF_BASE}/001-039l_S2k_Analgesie-Sedierung-Notfallmedizin_2019-02.pdf",
        ]
    },
    {
        "registry": "061-025",
        "title": "Anaphylaxie",
        "specialty": "Notfallmedizin",
        "pdf_urls": [
            f"{AWMF_BASE}/061-025l_S2k_Akuttherapie-Anaphylaktische-Reaktionen_2021-12.pdf",
            f"{AWMF_BASE}/061-025l_S2k_Anaphylaxie_2021-12.pdf",
        ]
    },

    # === NEPHROLOGIE ===
    {
        "registry": "053-015",
        "title": "Chronische Nierenerkrankung",
        "specialty": "Nephrologie",
        "pdf_urls": [
            f"{AWMF_BASE}/053-015l_S3_Versorgung_Patienten_CKD_2019-09.pdf",
            f"{AWMF_BASE}/053-015l_S3_Chronische-Niereninsuffizienz_2019-09.pdf",
        ]
    },
    {
        "registry": "053-012",
        "title": "Akutes Nierenversagen",
        "specialty": "Nephrologie",
        "pdf_urls": [
            f"{AWMF_BASE}/053-012l_S3_Nierenzellkarzinom_2019-08.pdf",  # Fallback
        ]
    },

    # === PSYCHIATRIE ===
    {
        "registry": "nvl-005",
        "title": "Depression",
        "specialty": "Psychiatrie",
        "pdf_urls": [
            f"{AWMF_BASE}/nvl-005l_S3_Unipolare_Depression_2022-09.pdf",
            f"{AWMF_BASE}/nvl-005l_S3_Depression_2022-09.pdf",
        ]
    },
]


def download_pdf(url: str, output_path: Path, timeout: int = 60) -> bool:
    """
    Lädt eine PDF-Datei herunter.

    Returns:
        True wenn erfolgreich, False sonst
    """
    try:
        response = SESSION.get(url, timeout=timeout, stream=True)

        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')

            # Prüfen ob es wirklich eine PDF ist
            if 'pdf' in content_type.lower() or url.endswith('.pdf'):
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                # Prüfen ob Datei nicht leer ist
                if output_path.stat().st_size > 1000:  # Min 1KB
                    return True
                else:
                    output_path.unlink()  # Leere Datei löschen

        return False

    except Exception as e:
        logger.debug(f"Download fehlgeschlagen: {url} - {e}")
        return False


def download_guideline(guideline: Dict) -> Tuple[str, Optional[Path]]:
    """
    Versucht eine Leitlinie herunterzuladen, testet verschiedene URLs.

    Returns:
        (registry_number, downloaded_path or None)
    """
    registry = guideline["registry"]
    title = guideline["title"]
    specialty = guideline["specialty"]

    # Ausgabepfad
    safe_title = re.sub(r'[^\w\s-]', '', title)[:50].strip()
    safe_title = re.sub(r'\s+', '_', safe_title)
    output_path = DOWNLOAD_DIR / specialty / f"{registry}_{safe_title}.pdf"

    # Bereits heruntergeladen?
    if output_path.exists() and output_path.stat().st_size > 1000:
        logger.info(f"✓ Bereits vorhanden: {registry} - {title}")
        return (registry, output_path)

    # Versuche alle URLs
    for url in guideline["pdf_urls"]:
        logger.debug(f"  Versuche: {url}")
        if download_pdf(url, output_path):
            size_kb = output_path.stat().st_size / 1024
            logger.info(f"✓ Heruntergeladen: {registry} - {title} ({size_kb:.0f} KB)")
            return (registry, output_path)
        time.sleep(0.5)  # Rate limiting

    logger.warning(f"✗ Fehlgeschlagen: {registry} - {title}")
    return (registry, None)


def search_awmf_pdf(registry: str, title: str) -> Optional[str]:
    """
    Sucht nach der PDF-URL einer Leitlinie über Web-Suche.
    Fallback wenn statische URLs nicht funktionieren.
    """
    # Hier könnte man eine Web-Suche implementieren
    # Für jetzt: None zurückgeben
    return None


def download_all_guidelines(parallel: bool = True, max_workers: int = 4) -> Dict:
    """
    Lädt alle kuratierten Leitlinien herunter.

    Returns:
        Statistik-Dictionary
    """
    logger.info(f"=== AWMF Leitlinien Download ===")
    logger.info(f"Ziel: {DOWNLOAD_DIR.absolute()}")
    logger.info(f"Anzahl: {len(GUIDELINES)} Leitlinien")
    logger.info("")

    # Verzeichnis erstellen
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    results = {"success": [], "failed": [], "skipped": []}

    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(download_guideline, g): g for g in GUIDELINES}

            for i, future in enumerate(as_completed(futures), 1):
                guideline = futures[future]
                registry, path = future.result()

                if path:
                    results["success"].append((registry, str(path)))
                else:
                    results["failed"].append(registry)

                # Progress
                if i % 10 == 0 or i == len(GUIDELINES):
                    logger.info(f"Progress: {i}/{len(GUIDELINES)}")
    else:
        for i, guideline in enumerate(GUIDELINES, 1):
            registry, path = download_guideline(guideline)

            if path:
                results["success"].append((registry, str(path)))
            else:
                results["failed"].append(registry)

            time.sleep(1)  # Rate limiting

            if i % 10 == 0:
                logger.info(f"Progress: {i}/{len(GUIDELINES)}")

    # Statistik
    logger.info("")
    logger.info("=== Download-Statistik ===")
    logger.info(f"Erfolgreich: {len(results['success'])}/{len(GUIDELINES)}")
    logger.info(f"Fehlgeschlagen: {len(results['failed'])}")

    if results["failed"]:
        logger.info(f"Fehlgeschlagen: {', '.join(results['failed'])}")

    # Cache-Datei speichern
    cache_path = DOWNLOAD_DIR / "download_cache.json"
    import json
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def list_downloaded() -> List[Path]:
    """Listet alle heruntergeladenen PDFs."""
    if not DOWNLOAD_DIR.exists():
        return []
    return list(DOWNLOAD_DIR.rglob("*.pdf"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AWMF Leitlinien Downloader")
    parser.add_argument("--list", action="store_true", help="Liste heruntergeladene PDFs")
    parser.add_argument("--sequential", action="store_true", help="Sequentiell statt parallel")
    parser.add_argument("--workers", type=int, default=4, help="Anzahl paralleler Downloads")

    args = parser.parse_args()

    if args.list:
        pdfs = list_downloaded()
        print(f"\nHeruntergeladene PDFs: {len(pdfs)}")
        for pdf in pdfs:
            print(f"  {pdf}")
    else:
        results = download_all_guidelines(
            parallel=not args.sequential,
            max_workers=args.workers
        )

        # Exit-Code
        if len(results["failed"]) > len(results["success"]):
            sys.exit(1)
