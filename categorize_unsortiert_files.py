#!/usr/bin/env python3
"""
Codex Task: Kategorisierung der 940 unsortierten Dateien

Dieses Skript kategorisiert die Dateien im Ordner _FACT_CHECK_SOURCES/_unsortiert/
in drei Kategorien:
1. PRÜFUNGSPROTOKOLLE - Prüfungsberichte, Erfahrungsberichte, Fälle aus Kenntnisprüfungen
2. FAKTEN - Medizinisches Wissen, Leitlinien, Lehrbuch-Inhalte
3. SPRACHLICH/ADMINISTRATIVE - Deutsch-Lernmaterialien, administrative Formulare

Autor: Codex Agent
Datum: 2025-12-21
"""

import json
from collections import defaultdict
from pathlib import Path


def main():
    # Pfade definieren
    unsortiert_path = Path("_FACT_CHECK_SOURCES/_unsortiert")
    output_path = Path("_AGENT_WORK")
    output_path.mkdir(exist_ok=True)

    # Alle Dateien im unsortiert-Ordner finden
    files = [f for f in unsortiert_path.iterdir() if f.is_file()]
    print(f"Gefundene Dateien: {len(files)}")

    # Schlüsselwort-Listen für die drei Kategorien
    PROTOKOLL_KEYWORDS = [
        "kenntnisprüfung",
        "prüfung",
        "simulation",
        "fälle",
        "fall ",
        "protokoll",
        "fsp",
        "fachsprachprüfung",
        "düsseldorf",
        "münster",
        "anamnese",
        "arzt-arzt",
        "arztbrief",
        "dokumentation",
        "doku",
        "epikrise",
        "aufklärung",
        "übung",
        "lückentext",
        "lösung",
        "skript",
        "pp ",
        "ü1",
        "ü2",
        "ü3",
        "ü4",
        "ü5",
        "fb ",
        "transkript",
        "fragen",
        "antworten",
        "qs version",
        "kp-fälle",
        "prüfungssimulation",
        "beispiel dokumentation",
        "bewertungsbogen",
        "ausbildung",
        "stex",
        "medisim",
        "medizinrecht",
        "arzt-arzt-gespräch",
        "körperliche untersuchung",
        "patientenvorstellung",
        "gesprächstechniken",
        "aufklärung",
        "befund",
        "diagnose",
        "therapie",
        "befundbericht",
    ]

    FAKTEN_KEYWORDS = [
        "leitlinie",
        "s1_",
        "s2_",
        "s3_",
        "awmf",
        "prophylaxe",
        "therapie",
        "chirurgie",
        "innere",
        "anatomie",
        "physiologie",
        "pathologie",
        "schrauben",
        "naht",
        "ecg",
        "ekg",
        "mrt",
        "röntgen",
        "labor",
        "notfall",
        "hyperkaliämie",
        "hypokaliämie",
        "tetanus",
        "kompendium",
        "strahlen",
        "osteoporose",
        "vegetative",
        "endoskopie",
        "syndrom",
        "krankheiten",
        "medizinisches",
        "kompendium",
        "grundlagen",
        "diagnostik",
        "pharmakologie",
        "arzneimittel",
        "laborwerte",
        "symptome",
        "erkrankungen",
        "behandlung",
        "verlauf",
        "komplikationen",
        "risikofaktoren",
        "prävention",
        "anamnese",
        "befund",
        "diagnose",
        "therapie",
        "prognose",
        "komplikation",
        "komplikationen",
        "komplikation",
        "komplikationen",
        "komplikationen",
        "komplikationen",
        "komplikationen",
        "komplikationen",
        "komplikationen",
    ]

    SPRACHLICH_KEYWORDS = [
        "konjunktion",
        "präfix",
        "nominalisierung",
        "verbal",
        "grammatik",
        "anmeldung",
        "antrag",
        "formular",
        "bewerbung",
        "azav",
        "grundwortschatz",
        "sprach",
        "deutsch",
        "wortschatz",
        "vokabeln",
        "grammatik",
        "syntax",
        "satzbau",
        "wortarten",
        "verbformen",
        "adjektive",
        "substantive",
        "artikel",
        "pronomen",
        "adverbien",
        "präpositionen",
        "interjektionen",
    ]

    # Kategorisierungsfunktion
    def categorize_file(filename: str) -> str:
        lower = filename.lower()

        # Prüfungsprotokolle
        for kw in PROTOKOLL_KEYWORDS:
            if kw in lower:
                return "PROTOKOLLE"

        # Fakten
        for kw in FAKTEN_KEYWORDS:
            if kw in lower:
                return "FAKTEN"

        # Sprachlich/Admin
        for kw in SPRACHLICH_KEYWORDS:
            if kw in lower:
                return "SPRACHLICH"

        # Unsicher
        return "UNSICHER"

    # Deduplizierungsfunktion
    def get_base_name(filename: str) -> str:
        """Entfernt _1, _2, _1_1 Suffixe für Deduplizierung"""
        base = filename
        # Entferne _1, _2, _3 usw. am Ende
        while base.endswith(tuple([f"_{i}" for i in range(1, 10)])):
            base = base[:-2]
        # Entferne _1_1, _2_1 usw.
        while base.endswith(tuple([f"_{i}_1" for i in range(1, 10)])):
            base = base[:-4]
        return base

    # Kategorisierung durchführen
    results = {"PROTOKOLLE": [], "FAKTEN": [], "SPRACHLICH": [], "UNSICHER": []}

    # Für Deduplizierung
    categorized_files = defaultdict(list)

    for f in files:
        category = categorize_file(f.name)
        base_name = get_base_name(f.name)

        # Speichern für Deduplizierung
        categorized_files[category].append({"original_name": f.name, "base_name": base_name, "path": str(f)})

        results[category].append(f.name)

    # Deduplizierung durchführen
    deduplicated_results = {"PROTOKOLLE": [], "FAKTEN": [], "SPRACHLICH": [], "UNSICHER": []}

    for category, file_list in categorized_files.items():
        # Gruppieren nach Basisnamen
        base_groups = defaultdict(list)
        for file_info in file_list:
            base_groups[file_info["base_name"]].append(file_info)

        # Für jede Gruppe das längste Originalfile auswählen
        for base_name, group in base_groups.items():
            # Wähle das File mit dem längsten Namen (meist die vollständige Version)
            selected = max(group, key=lambda x: len(x["original_name"]))
            deduplicated_results[category].append(selected["original_name"])

    # Sortieren der Listen
    for category in deduplicated_results:
        deduplicated_results[category].sort()

    # Statistiken berechnen
    stats = {
        "total_files": len(files),
        "categorized_files": sum(len(files) for files in deduplicated_results.values()),
        "protokolle_count": len(deduplicated_results["PROTOKOLLE"]),
        "fakten_count": len(deduplicated_results["FAKTEN"]),
        "sprachlich_count": len(deduplicated_results["SPRACHLICH"]),
        "unsicher_count": len(deduplicated_results["UNSICHER"]),
        "deduplication_rate": f"{((len(files) - sum(len(files) for files in deduplicated_results.values())) / len(files) * 100):.1f}%",
    }

    # JSON-Report speichern
    report_data = {
        "statistics": stats,
        "categorized_files": deduplicated_results,
        "original_files": results,
        "categorization_rules": {
            "protokoll_keywords": PROTOKOLL_KEYWORDS,
            "fakten_keywords": FAKTEN_KEYWORDS,
            "sprachlich_keywords": SPRACHLICH_KEYWORDS,
        },
    }

    with open(output_path / "unsortiert_kategorisierung_report.json", "w", encoding="utf-8") as fp:
        json.dump(report_data, fp, indent=2, ensure_ascii=False)

    # Text-Report erstellen
    text_report = f"""# Kategorisierungs-Report für _FACT_CHECK_SOURCES/_unsortiert/

## Statistiken
- Gesamtanzahl Dateien: {stats["total_files"]}
- Kategorisierte Dateien: {stats["categorized_files"]}
- Deduplizierungsrate: {stats["deduplication_rate"]}

## Verteilung auf Kategorien
- PRÜFUNGSPROTOKOLLE: {stats["protokolle_count"]} Dateien
- FAKTEN: {stats["fakten_count"]} Dateien  
- SPRACHLICH/ADMINISTRATIVE: {stats["sprachlich_count"]} Dateien
- UNSICHER: {stats["unsicher_count"]} Dateien

## PRÜFUNGSPROTOKOLLE ({stats["protokolle_count"]} Dateien)
{chr(10).join(f"- {f}" for f in deduplicated_results["PROTOKOLLE"][:20])}
{f"... und {len(deduplicated_results['PROTOKOLLE']) - 20} weitere" if len(deduplicated_results["PROTOKOLLE"]) > 20 else ""}

## FAKTEN ({stats["fakten_count"]} Dateien)
{chr(10).join(f"- {f}" for f in deduplicated_results["FAKTEN"][:20])}
{f"... und {len(deduplicated_results['FAKTEN']) - 20} weitere" if len(deduplicated_results["FAKTEN"]) > 20 else ""}

## SPRACHLICH/ADMINISTRATIVE ({stats["sprachlich_count"]} Dateien)
{chr(10).join(f"- {f}" for f in deduplicated_results["SPRACHLICH"][:20])}
{f"... und {len(deduplicated_results['SPRACHLICH']) - 20} weitere" if len(deduplicated_results["SPRACHLICH"]) > 20 else ""}

## UNSICHER ({stats["unsicher_count"]} Dateien)
{chr(10).join(f"- {f}" for f in deduplicated_results["UNSICHER"][:20])}
{f"... und {len(deduplicated_results['UNSICHER']) - 20} weitere" if len(deduplicated_results["UNSICHER"]) > 20 else ""}

## Nächste Schritte
1. **Verschieben der Dateien:**
   - PROTOKOLLE → `_GOLD_STANDARD/unsortiert_protokolle/`
   - FAKTEN → `_FACT_CHECK_SOURCES/unsortiert_kategorisiert/`
   - SPRACHLICH → `_FACT_CHECK_SOURCES/unsortiert_sprachlich/`

2. **Deduplizieren:**
   ```bash
   fdupes -rdN _GOLD_STANDARD/unsortiert_protokolle/
   ```

3. **RAG-Index updaten:**
   - Nur FAKTEN-Dateien in den RAG-Index aufnehmen
   - PROTOKOLLE sind für Fragen-Extraktion, nicht für RAG
"""

    with open(output_path / "unsortiert_kategorisierung_report.md", "w", encoding="utf-8") as fp:
        fp.write(text_report)

    print("\n=== Kategorisierungs-Ergebnisse ===")
    print(f"PRÜFUNGSPROTOKOLLE: {stats['protokolle_count']} Dateien")
    print(f"FAKTEN: {stats['fakten_count']} Dateien")
    print(f"SPRACHLICH/ADMINISTRATIVE: {stats['sprachlich_count']} Dateien")
    print(f"UNSICHER: {stats['unsicher_count']} Dateien")
    print(f"\nReports gespeichert in: {output_path}")
    print("- JSON: unsortiert_kategorisierung_report.json")
    print("- Markdown: unsortiert_kategorisierung_report.md")


if __name__ == "__main__":
    main()
