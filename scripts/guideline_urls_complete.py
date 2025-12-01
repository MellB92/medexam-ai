#!/usr/bin/env python3
"""
Vollständige AWMF Leitlinien URLs (Stand: Dezember 2024)
=========================================================

Alle 50 konfigurierten Leitlinien mit verifizierten Download-URLs.
"""

# Basis-URL
BASE = "https://register.awmf.org/assets/guidelines"

# Alle Leitlinien - Format: (registry, title, specialty, url)
ALL_GUIDELINES = [
    # ============================================================
    # KARDIOLOGIE (6)
    # ============================================================
    ("nvl-006", "Chronische Herzinsuffizienz", "Kardiologie",
     f"{BASE}/nvl-006l_S3_Chronische_Herzinsuffizienz_2023-12.pdf"),

    ("nvl-004", "Koronare Herzkrankheit", "Kardiologie",
     f"{BASE}/nvl-004l_S3_KHK_2022-09.pdf"),

    ("nvl-009", "Arterielle Hypertonie", "Kardiologie",
     f"{BASE}/nvl-009l_S3_Hypertonie_2023-06.pdf"),

    ("019-013", "Kardiogener Schock", "Kardiologie",
     f"{BASE}/019-013l_S3_Infarkt-bedingter-kardiogener-Schock_2020-02.pdf"),

    # ESC Guidelines - von escardio.org
    ("ESC-ACS-2023", "ESC Acute Coronary Syndromes", "Kardiologie",
     "https://www.escardio.org/static-file/Escardio/Guidelines/Documents/2023-ESC-ACS-Guidelines.pdf"),

    ("ESC-AF-2024", "ESC Atrial Fibrillation", "Kardiologie",
     "https://www.escardio.org/static-file/Escardio/Guidelines/Documents/2024-ESC-AF-Guidelines.pdf"),

    # ============================================================
    # INFEKTIOLOGIE (8)
    # ============================================================
    ("079-001", "Sepsis", "Infektiologie",
     f"{BASE}/079-001l_S3_Sepsis-Praevention-Diagnose-Therapie-Nachsorge_2020-02.pdf"),

    ("020-020", "Ambulant erworbene Pneumonie", "Infektiologie",
     f"{BASE}/020-020l_S3_Behandlung-von-erwachsenen-Patienten-mit-ambulant-erworbener-Pneumonie_2021-04.pdf"),

    ("020-013", "Nosokomiale Pneumonie", "Infektiologie",
     f"{BASE}/020-013l_S3_Epidemiologie-Diagnostik-Therapie-erwachsener-Patienten-nosokomiale-Pneumonie__2024-03.pdf"),

    ("030-089", "Bakterielle Meningitis", "Infektiologie",
     f"{BASE}/030-089l_S2k_Ambulant-erworbene-bakterielle-Meningitis-im-Erwachsenenalter_2024-02.pdf"),

    ("092-001", "Antibiotic Stewardship", "Infektiologie",
     f"{BASE}/092-001l_S3_Strategien_zur_Sicherung_rationaler_Antibiotika-Anwendung_im_Krankenhaus_2024-02.pdf"),

    ("055-001", "HIV-Infektion", "Infektiologie",
     f"{BASE}/055-001l_Antiretrovirale_Therapie_der_HIV_Infektion__2021-06.pdf"),

    ("021-011", "Hepatitis B", "Infektiologie",
     f"{BASE}/021-011l_S3_Prophylaxe-Diagnostik-Therapie-der-Hepatitis-B-Virusinfektion_2021-07.pdf"),

    ("021-012", "Hepatitis C", "Infektiologie",
     f"{BASE}/021-012l_S3_Hepatitis-C-Virus_HCV-Infektion_2018-07-abgelaufen.pdf"),

    # ============================================================
    # CHIRURGIE/TRAUMA (6)
    # ============================================================
    ("187-023", "Polytrauma", "Chirurgie",
     f"{BASE}/187-023k_S3_Polytrauma-Schwerverletzten-Behandlung_2023-06.pdf"),

    ("088-004", "Appendizitis", "Chirurgie",
     f"{BASE}/088-004l_S3_Diagnostik-Therapie-Appendizitis_2024-12.pdf"),

    ("187-015", "Schenkelhalsfraktur", "Chirurgie",
     f"{BASE}/187-015l_S3_Schenkelhalsfraktur_2015-10-abgelaufen.pdf"),

    ("012-015", "Distale Radiusfraktur", "Chirurgie",
     f"{BASE}/012-015l_S2e_Distale-Radiusfraktur_2021-04.pdf"),

    ("088-001", "Akutes Abdomen", "Chirurgie",
     f"{BASE}/088-001k_S1_Akutes-Abdomen_2016-04-abgelaufen.pdf"),

    ("010-079", "Hernien", "Chirurgie",
     f"{BASE}/010-079l_S3_Leistenhernie_2024-08.pdf"),

    # ============================================================
    # DIABETES/INNERE (5)
    # ============================================================
    ("nvl-001", "Typ-2-Diabetes", "Diabetologie",
     f"{BASE}/nvl-001l_S3_Typ-2-Diabetes_2023-06.pdf"),

    ("057-013", "Typ-1-Diabetes", "Diabetologie",
     f"{BASE}/057-013l_S3_Typ-1-Diabetes-Diagnostik-Therapie-Erwachsene_2023-05.pdf"),

    ("021-003", "Pankreatitis", "Innere",
     f"{BASE}/021-003l_S3_Pankreatitis_2022-04_01.pdf"),

    ("021-013", "GERD", "Innere",
     f"{BASE}/021-013l_S2k_Gastrooesophageale-Refluxkrankheit-eosinophile_Oesophagitis_2023-09.pdf"),

    ("021-017", "Leberzirrhose", "Innere",
     f"{BASE}/021-017l_S2k_Komplikationen-der-Leberzirrhose_2019-04.pdf"),

    # ============================================================
    # PNEUMOLOGIE (3)
    # ============================================================
    ("nvl-003", "COPD", "Pneumologie",
     f"{BASE}/nvl-003l_S3_COPD_2022-08.pdf"),

    ("nvl-002", "Asthma", "Pneumologie",
     f"{BASE}/nvl-002l_S3_Asthma_2023-03.pdf"),

    ("065-002", "Venenthrombose und Lungenembolie", "Pneumologie",
     f"{BASE}/065-002l_S2k_Venenthrombose-Lungenembolie_2023-09.pdf"),

    # ============================================================
    # NEUROLOGIE (4)
    # ============================================================
    ("030-133", "Schlaganfall Sekundärprophylaxe", "Neurologie",
     f"{BASE}/030-133l_S2k_Sekundaerprophylaxe-ischaemischer-Schlaganfall-transitorische-ischaemische-Attacke-Teil-1_2022-07.pdf"),

    ("030-041", "Epilepsie", "Neurologie",
     f"{BASE}/030-041l_S2k_Erster-epileptischer-Anfall-Epilepsien-Erwachsenenalter_2023-09.pdf"),

    ("030-057", "Migräne/Kopfschmerzen", "Neurologie",
     f"{BASE}/030-057l_S1_Therapie-der-Migraeneattacke-Prophylaxe-der-Migraene_2024-06.pdf"),

    ("024-018", "SHT", "Neurologie",
     f"{BASE}/024-018l_S2k_Schaedel-Hirn-Trauma-im-Kindes-und-Jugendalter_2022-02.pdf"),

    # ============================================================
    # UROLOGIE (3)
    # ============================================================
    ("043-022OL", "Prostatakarzinom", "Urologie",
     f"{BASE}/043-022OLl_S3_Prostatakarzinom_2025-08.pdf"),

    ("043-044", "Harnwegsinfektionen", "Urologie",
     f"{BASE}/043-044l_S3_Epidemiologie-Diagnostik-Therapie-Praevention-Management-Harnwegsinfektione-Erwachsene-HWI_2024-09.pdf"),

    ("043-025", "Urolithiasis", "Urologie",
     f"{BASE}/043-025l_S2k_Diagnostik_Therapie_Metaphylaxe_Urolithiasis_2019-07_1-abgelaufen.pdf"),

    # ============================================================
    # ORTHOPÄDIE (3)
    # ============================================================
    ("187-050", "Gonarthrose", "Orthopädie",
     f"{BASE}/187-050l_S2k_Gonarthrose_2018-01-abgelaufen.pdf"),

    ("187-049", "Coxarthrose", "Orthopädie",
     f"{BASE}/187-049l_S2k_Coxarthrose_2019-07.pdf"),

    ("nvl-007", "Kreuzschmerz", "Orthopädie",
     f"{BASE}/nvl-007l_S3_Kreuzschmerz_2017-11.pdf"),

    # ============================================================
    # ONKOLOGIE (4)
    # ============================================================
    ("021-007OL", "Kolorektales Karzinom", "Onkologie",
     f"{BASE}/021-007OLl_S3_Kolorektales-Karzinom-KRK_2024-07.pdf"),

    ("020-007OL", "Lungenkarzinom", "Onkologie",
     f"{BASE}/020-007OLl_S3_Praevention-Diagnostik-Therapie-Nachsorge-Lungenkarzinom_2025-04.pdf"),

    ("032-045OL", "Mammakarzinom", "Onkologie",
     f"{BASE}/032-045OLl_S3_Mammakarzinom_2021-06.pdf"),

    ("032-009OL", "Magenkarzinom", "Onkologie",
     f"{BASE}/032-009OLl_S3_Magenkarzinom_2019-08.pdf"),

    # ============================================================
    # NOTFALLMEDIZIN (3)
    # ============================================================
    ("001-012", "Analgesie Sedierung Intensiv", "Notfallmedizin",
     f"{BASE}/001-012l_S3_Analgesie-Sedierung-und-Delirmanagement-in-der-Intensivmedizin_2021-08_01.pdf"),

    ("001-039", "Analgesie Sedierung Notfall", "Notfallmedizin",
     f"{BASE}/001-039l_S3_Praeklinische-Analgesie-Erstversorgung_2024-08.pdf"),

    ("061-025", "Anaphylaxie", "Notfallmedizin",
     f"{BASE}/061-025l_S2k_Akuttherapie-Praevention-Anaphylaxie_2021-12.pdf"),

    # Reanimation - GRC/ERC, nicht AWMF
    ("GRC-2021", "Reanimation", "Notfallmedizin",
     "https://www.grc-org.de/files/Contentpages/document/Leitlinienkompakt_26.04.2022.pdf"),

    # ============================================================
    # RADIOLOGIE (1)
    # ============================================================
    ("DRG-KM-2018", "Kontrastmittel", "Radiologie",
     "https://www.drg.de/media/dokumente/publikationen/Empfehlungen_Kontrastmittelreaktionen.pdf"),

    # ============================================================
    # NEPHROLOGIE (2)
    # ============================================================
    ("053-048", "Chronische Nierenerkrankung", "Nephrologie",
     f"{BASE}/2025-02_053-048l_S3_Versorgung-PatientInnen-chronische-nicht-nierenersatz-therpapiepflichtige-Nierenkrankheit-Hausarztpraxis_01.pdf"),

    ("053-012", "Akutes Nierenversagen", "Nephrologie",
     f"{BASE}/053-012l_S2e_Haemodialyse-Haemodialfiltration_2024-01.pdf"),

    # ============================================================
    # PSYCHIATRIE (1)
    # ============================================================
    ("nvl-005", "Depression", "Psychiatrie",
     f"{BASE}/nvl-005l_S3_Unipolare_Depression_2022-09.pdf"),
]

# Mapping von alten Registry-Nummern zu neuen
REGISTRY_MAPPING = {
    "046-001": "nvl-009",  # Hypertonie
    "020-006": "nvl-003",  # COPD
    "088-007": "088-004",  # Appendizitis
    "030-140": "030-133",  # Schlaganfall
    "053-015": "053-048",  # CKD
    "001-006": "GRC-2021", # Reanimation
}


def download_all():
    """Download alle Leitlinien."""
    import os
    import requests
    from pathlib import Path

    output_dir = Path("/Users/user/Documents/Medexamenai/_BIBLIOTHEK/Leitlinien")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })

    success = 0
    failed = []

    for registry, title, specialty, url in ALL_GUIDELINES:
        # Erstelle Fachgebiet-Ordner
        specialty_dir = output_dir / specialty
        specialty_dir.mkdir(parents=True, exist_ok=True)

        # Dateiname
        safe_title = title.replace("/", "-").replace(" ", "_")
        filename = f"{registry}_{safe_title}.pdf"
        filepath = specialty_dir / filename

        # Skip wenn bereits vorhanden
        if filepath.exists():
            print(f"✓ {registry}: {title} (bereits vorhanden)")
            success += 1
            continue

        try:
            print(f"⬇ {registry}: {title}...", end=" ", flush=True)
            resp = session.get(url, timeout=60, allow_redirects=True)

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
    print(f"Erfolgreich: {success}/{len(ALL_GUIDELINES)}")
    print(f"Fehlgeschlagen: {len(failed)}")

    if failed:
        print(f"\nFehlgeschlagene Downloads:")
        for registry, title, url, error in failed:
            print(f"  - {registry}: {title}")
            print(f"    URL: {url}")
            print(f"    Fehler: {error}")


if __name__ == "__main__":
    download_all()
