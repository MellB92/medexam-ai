#!/usr/bin/env python3
"""
Verifizierte AWMF Leitlinien URLs (Stand: Dezember 2024)
========================================================

Diese URLs wurden manuell verifiziert und funktionieren.
"""

# Basis-URL
BASE = "https://register.awmf.org/assets/guidelines"

# Verifizierte URLs - Format: (registry, title, specialty, url)
VERIFIED_GUIDELINES = [
    # === KARDIOLOGIE ===
    ("nvl-006", "Chronische Herzinsuffizienz", "Kardiologie",
     f"{BASE}/nvl-006l_S3_Chronische_Herzinsuffizienz_2023-12.pdf"),

    ("nvl-004", "Koronare Herzkrankheit", "Kardiologie",
     f"{BASE}/nvl-004l_S3_KHK_2022-09.pdf"),

    # === INFEKTIOLOGIE ===
    ("079-001", "Sepsis", "Infektiologie",
     f"{BASE}/079-001l_S3_Sepsis-Praevention-Diagnose-Therapie-Nachsorge_2025-07.pdf"),

    ("020-013", "Nosokomiale Pneumonie", "Pneumologie",
     f"{BASE}/020-013k_S3_Epidemiologie-Diagnostik-Therapie-erwachsener-Patienten-nosokomiale-Pneumonie__2024-03.pdf"),

    ("092-001", "Antibiotic Stewardship", "Infektiologie",
     f"{BASE}/092-001l_S3_Strategien_zur_Sicherung_rationaler_Antibiotika-Anwendung_im_Krankenhaus_2024-02.pdf"),

    # === DIABETES ===
    ("nvl-001", "Typ-2-Diabetes", "Diabetologie",
     f"{BASE}/nvl-001l_S3_Typ-2-Diabetes_2023-06.pdf"),

    # === PNEUMOLOGIE ===
    ("nvl-002", "Asthma", "Pneumologie",
     f"{BASE}/nvl-002l_S3_Asthma_2023-03.pdf"),

    ("nvl-003", "COPD", "Pneumologie",
     f"{BASE}/nvl-003l_S3_COPD_2022-08.pdf"),

    ("065-002", "Venenthrombose und Lungenembolie", "Pneumologie",
     f"{BASE}/065-002l_S2k_VTE_Venenthrombose-Lungenembolie_2023-03.pdf"),

    # === NEUROLOGIE ===
    ("030-140", "Schlaganfall Sekundärprophylaxe", "Neurologie",
     f"{BASE}/030-140l_S3_Schlaganfall-Sekundaerprophylaxe_2022-05.pdf"),

    # === PSYCHIATRIE ===
    ("nvl-005", "Depression", "Psychiatrie",
     f"{BASE}/nvl-005l_S3_Unipolare_Depression_2022-09.pdf"),

    # === ORTHOPÄDIE ===
    ("nvl-007", "Kreuzschmerz", "Orthopädie",
     f"{BASE}/nvl-007l_S3_Kreuzschmerz_2017-11.pdf"),

    # === CHIRURGIE ===
    ("088-004", "Appendizitis", "Chirurgie",
     f"{BASE}/088-004l_S3_Diagnostik-Therapie-Appendizitis_2024-12.pdf"),

    # === NOTFALLMEDIZIN ===
    ("001-012", "Analgesie Sedierung Beatmung", "Intensivmedizin",
     f"{BASE}/001-012l_S3_Analgesie-Sedierung-und-Delirmanagement-in-der-Intensivmedizin_2021-08_01.pdf"),

    ("061-025", "Anaphylaxie", "Notfallmedizin",
     f"{BASE}/061-025l_S2k_Akuttherapie-Praevention-Anaphylaxie_2021-12.pdf"),

    # === ONKOLOGIE (Leitlinienprogramm Onkologie) ===
    ("032-045OL", "Mammakarzinom", "Onkologie",
     f"{BASE}/032-045OLl_S3_Mammakarzinom_2021-06.pdf"),

    ("021-007OL", "Kolorektales Karzinom", "Onkologie",
     f"{BASE}/021-007OLl_S3_Kolorektales-Karzinom-KRK_2024-07.pdf"),

    ("020-007OL", "Lungenkarzinom", "Onkologie",
     f"{BASE}/020-007OLl_S3_Lungenkarzinom_2018-02.pdf"),

    ("043-022OL", "Prostatakarzinom", "Onkologie",
     f"{BASE}/043-022OLl_S3_Prostatakarzinom_2021-10.pdf"),
]

if __name__ == "__main__":
    import requests

    print("Verifiziere URLs...\n")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })

    ok = 0
    failed = 0

    for registry, title, specialty, url in VERIFIED_GUIDELINES:
        try:
            resp = session.head(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                print(f"✓ {registry}: {title}")
                ok += 1
            else:
                print(f"✗ {registry}: {title} ({resp.status_code})")
                failed += 1
        except Exception as e:
            print(f"✗ {registry}: {title} ({e})")
            failed += 1

    print(f"\nErgebnis: {ok}/{ok+failed} URLs funktionieren")
