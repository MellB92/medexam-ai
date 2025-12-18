#!/usr/bin/env python3
"""
Download der noch fehlenden Leitlinien.
Stand: Dezember 2024
"""

import os
import requests
from pathlib import Path

BASE = "https://register.awmf.org/assets/guidelines"

# Fehlende Leitlinien mit verifizierten URLs
REMAINING_GUIDELINES = [
    # Kreuzschmerz
    ("nvl-007", "Kreuzschmerz", "Orthopaedie",
     f"{BASE}/nvl-007l_S3_Kreuzschmerz_2017-03-abgelaufen.pdf"),

    # Kolorektales Karzinom - von Leitlinienprogramm Onkologie
    ("021-007OL", "Kolorektales_Karzinom", "Onkologie",
     "https://www.leitlinienprogramm-onkologie.de/fileadmin/user_upload/Downloads/Leitlinien/Kolorektales_Karzinom/LL_KRK_Langfassung_1.1.pdf"),

    # Magenkarzinom - neueste Version 2025
    ("032-009OL", "Magenkarzinom", "Onkologie",
     f"{BASE}/032-009OLl_S3_Magenkarzinom_Diagnostik_Therapie_Adenokarzinome_oesophagogastraler_Uebergang_2025-05.pdf"),

    # Analgesie Sedierung Intensiv - neueste Version 2025
    ("001-012", "Analgesie_Sedierung_Intensiv", "Intensivmedizin",
     f"{BASE}/001-012l_S3_Analgesie-Sedierung-Delirmanagement-in-der-Intensivmedizin-DAS_2025-08.pdf"),

    # Analgesie Sedierung Notfall - präklinisch (noch nicht verfügbar, registriert 001-039)
    # Skip - Leitlinie noch in Entwicklung

    # Akutes Nierenversagen - Nierenersatztherapie Intensivmedizin
    ("040-017", "Nierenersatztherapie_Intensivmedizin", "Nephrologie",
     f"{BASE}/040-017l_S3_Nierenersatztherapie-Intensivmedizin_2025-06.pdf"),

    # ESC ACS 2023
    ("ESC-ACS-2023", "Acute_Coronary_Syndromes", "Kardiologie",
     "https://www.uniklinik-ulm.de/fileadmin/default/09_Sonstige/Klinische-Chemie/Downloads/ehad191_supplementary_data_ESC_Guideline_ACS_2023.pdf"),

    # ESC AF 2024
    ("ESC-AF-2024", "Atrial_Fibrillation", "Kardiologie",
     "https://www.swiss-ablation.com/downloadbereich/dateien/2024ESC-compressed.pdf"),
]


def download_all():
    """Download alle fehlenden Leitlinien."""
    output_dir = Path("/Users/user/Documents/Medexamenai/_BIBLIOTHEK/Leitlinien")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    success = 0
    failed = []

    for registry, title, specialty, url in REMAINING_GUIDELINES:
        # Erstelle Fachgebiet-Ordner
        specialty_dir = output_dir / specialty
        specialty_dir.mkdir(parents=True, exist_ok=True)

        # Dateiname
        filename = f"{registry}_{title}.pdf"
        filepath = specialty_dir / filename

        # Skip wenn bereits vorhanden
        if filepath.exists():
            print(f"✓ {registry}: {title} (bereits vorhanden)")
            success += 1
            continue

        try:
            print(f"⬇ {registry}: {title}...", end=" ", flush=True)
            resp = session.get(url, timeout=120, allow_redirects=True)

            if resp.status_code == 200 and len(resp.content) > 1000:
                filepath.write_bytes(resp.content)
                size_mb = len(resp.content) / (1024 * 1024)
                print(f"OK ({size_mb:.1f} MB)")
                success += 1
            else:
                print(f"FEHLER ({resp.status_code})")
                failed.append((registry, title, url, resp.status_code))

        except Exception as e:
            print(f"FEHLER ({e})")
            failed.append((registry, title, url, str(e)))

    print(f"\n{'='*60}")
    print(f"Erfolgreich: {success}/{len(REMAINING_GUIDELINES)}")
    print(f"Fehlgeschlagen: {len(failed)}")

    if failed:
        print(f"\nFehlgeschlagene Downloads:")
        for registry, title, url, error in failed:
            print(f"  - {registry}: {title}")
            print(f"    Fehler: {error}")


if __name__ == "__main__":
    download_all()
