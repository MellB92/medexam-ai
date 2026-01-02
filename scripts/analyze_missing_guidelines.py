#!/usr/bin/env python3
"""
Analysiert die Output-Antworten und identifiziert fehlende Leitlinien.

Dieser Script:
1. Lädt evidenz_antworten.json
2. Analysiert alle Leitlinien-Referenzen
3. Vergleicht mit vorhandenen PDFs in _BIBLIOTHEK
4. Erstellt einen Bericht über fehlende Leitlinien
5. Generiert eine Download-Liste für fehlende Leitlinien

Usage:
    python scripts/analyze_missing_guidelines.py [--output report.json]
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple
import argparse


# Bekannte Fachgesellschaften und ihre Domains
FACHGESELLSCHAFTEN = {
    "AWMF": {
        "name": "Arbeitsgemeinschaft der Wissenschaftlichen Medizinischen Fachgesellschaften",
        "url": "https://register.awmf.org/de/leitlinien",
        "priority": 1
    },
    "DGK": {
        "name": "Deutsche Gesellschaft für Kardiologie",
        "url": "https://leitlinien.dgk.org/",
        "priority": 1
    },
    "DGIM": {
        "name": "Deutsche Gesellschaft für Innere Medizin",
        "url": "https://www.dgim.de/",
        "priority": 1
    },
    "ESC": {
        "name": "European Society of Cardiology",
        "url": "https://www.escardio.org/Guidelines",
        "priority": 1
    },
    "DGHO": {
        "name": "Deutsche Gesellschaft für Hämatologie und Medizinische Onkologie",
        "url": "https://www.onkopedia.com/de",
        "priority": 1
    },
    "DVO": {
        "name": "Dachverband Osteologie",
        "url": "https://dv-osteologie.org/",
        "priority": 2
    },
    "KDIGO": {
        "name": "Kidney Disease: Improving Global Outcomes",
        "url": "https://kdigo.org/guidelines/",
        "priority": 2
    },
    "DGRh": {
        "name": "Deutsche Gesellschaft für Rheumatologie",
        "url": "https://dgrh.de/",
        "priority": 2
    },
    "DGE": {
        "name": "Deutsche Gesellschaft für Endokrinologie",
        "url": "https://www.endokrinologie.net/",
        "priority": 2
    },
    "DGN": {
        "name": "Deutsche Gesellschaft für Neurologie",
        "url": "https://dgn.org/leitlinien/",
        "priority": 1
    },
    "DEGAM": {
        "name": "Deutsche Gesellschaft für Allgemeinmedizin und Familienmedizin",
        "url": "https://www.degam.de/leitlinien",
        "priority": 2
    },
    "STIKO": {
        "name": "Ständige Impfkommission (Robert Koch-Institut)",
        "url": "https://www.rki.de/DE/Content/Kommissionen/STIKO/stiko_node.html",
        "priority": 1
    },
    "ERC": {
        "name": "European Resuscitation Council",
        "url": "https://www.erc.edu/",
        "priority": 1
    },
    "DGVS": {
        "name": "Deutsche Gesellschaft für Gastroenterologie, Verdauungs- und Stoffwechselkrankheiten",
        "url": "https://www.dgvs.de/",
        "priority": 2
    }
}

# Themen-Keywords für Kategorisierung
THEMEN_KEYWORDS = {
    "Kardiologie": ["herz", "kardio", "myokard", "koronar", "khk", "acs", "vhf", "herzinsuffizienz", "hypertonie", "aorten"],
    "Pneumologie": ["lunge", "pneumo", "copd", "asthma", "pneumonie", "atemweg", "respirat"],
    "Gastroenterologie": ["magen", "darm", "leber", "pankreas", "hepat", "gastro", "kolorektal", "ösophag"],
    "Neurologie": ["neuro", "schlaganfall", "epilepsie", "migräne", "hirn", "kopfschmerz", "meningitis"],
    "Onkologie": ["karzinom", "tumor", "krebs", "onko", "leukämie", "lymphom", "myelom"],
    "Infektiologie": ["infekt", "sepsis", "antibio", "hepatitis", "hiv", "tuberkulose"],
    "Endokrinologie": ["diabetes", "schilddrüse", "hyperthyreose", "hypothyreose", "endokrin"],
    "Nephrologie": ["niere", "nephro", "dialyse", "ckd", "niereninsuffizienz"],
    "Rheumatologie": ["rheuma", "arthritis", "gicht", "lupus", "vaskulitis"],
    "Unfallchirurgie": ["fraktur", "trauma", "polytrauma", "unfall", "verletzung"],
    "Notfallmedizin": ["notfall", "reanimation", "schock", "anaphylaxie"],
    "Intensivmedizin": ["intensiv", "beatmung", "sedierung", "sepsis"],
    "Hämatologie": ["anämie", "thrombozytopenie", "gerinnung", "transfusion"]
}


def load_answers(path: Path) -> List[dict]:
    """Lädt die Antworten-Datei."""
    if not path.exists():
        raise FileNotFoundError(f"Antwortdatei nicht gefunden: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_existing_pdfs(bibliothek_path: Path) -> Set[str]:
    """Findet alle vorhandenen PDF-Dateien in der Bibliothek."""
    pdfs = set()
    for pdf in bibliothek_path.rglob("*.pdf"):
        pdfs.add(pdf.name.lower())
        pdfs.add(pdf.stem.lower())
    return pdfs


def extract_guideline_refs(answers: List[dict]) -> Tuple[Counter, Counter]:
    """Extrahiert Leitlinien-Referenzen aus den Antworten."""
    pdf_refs = Counter()
    text_refs = Counter()

    for a in answers:
        ll = a.get("leitlinie", "")
        if not ll or ll in ("N/A", "Unbekannt", "Keine Leitlinie verfügbar"):
            continue

        if ll.endswith(".pdf"):
            pdf_refs[ll] += 1
        else:
            text_refs[ll] += 1

    return pdf_refs, text_refs


def categorize_by_society(text_refs: Counter) -> Dict[str, List[Tuple[str, int]]]:
    """Kategorisiert Leitlinien-Referenzen nach Fachgesellschaft."""
    society_refs = defaultdict(list)

    for ref, count in text_refs.items():
        assigned = False
        for society in FACHGESELLSCHAFTEN:
            if society.lower() in ref.lower():
                society_refs[society].append((ref, count))
                assigned = True
                break

        if not assigned:
            society_refs["OTHER"].append((ref, count))

    return dict(society_refs)


def categorize_by_topic(text_refs: Counter) -> Dict[str, List[Tuple[str, int]]]:
    """Kategorisiert Leitlinien-Referenzen nach Thema."""
    topic_refs = defaultdict(list)

    for ref, count in text_refs.items():
        ref_lower = ref.lower()
        assigned = False

        for topic, keywords in THEMEN_KEYWORDS.items():
            for kw in keywords:
                if kw in ref_lower:
                    topic_refs[topic].append((ref, count))
                    assigned = True
                    break
            if assigned:
                break

        if not assigned:
            topic_refs["Sonstige"].append((ref, count))

    return dict(topic_refs)


def generate_download_list(text_refs: Counter) -> List[dict]:
    """Generiert eine Liste von Leitlinien zum Download."""
    downloads = []

    # Extrahiere AWMF-Nummern
    awmf_pattern = re.compile(r"(\d{3}-\d{3})")

    for ref, count in text_refs.most_common():
        # Suche nach AWMF-Nummer
        awmf_match = awmf_pattern.search(ref)

        download_info = {
            "reference": ref[:200],  # Kürzen für Übersichtlichkeit
            "count": count,
            "awmf_number": awmf_match.group(1) if awmf_match else None,
            "priority": "high" if count >= 3 else "medium" if count >= 2 else "low",
            "url_suggestion": None
        }

        if awmf_match:
            awmf_num = awmf_match.group(1)
            download_info["url_suggestion"] = f"https://register.awmf.org/de/leitlinien/{awmf_num}"

        downloads.append(download_info)

    return downloads


def analyze_coverage(pdf_refs: Counter, existing_pdfs: Set[str]) -> Dict[str, List[str]]:
    """Analysiert die Abdeckung der referenzierten PDFs."""
    found = []
    missing = []

    for pdf_name in pdf_refs:
        pdf_lower = pdf_name.lower()
        stem = Path(pdf_name).stem.lower()

        if pdf_lower in existing_pdfs or stem in existing_pdfs:
            found.append(pdf_name)
        else:
            missing.append(pdf_name)

    return {"found": found, "missing": missing}


def main():
    parser = argparse.ArgumentParser(description="Analysiert fehlende Leitlinien")
    parser.add_argument("--output", "-o", default="_OUTPUT/missing_guidelines_report.json",
                        help="Ausgabedatei für den Bericht")
    parser.add_argument("--answers", default="_OUTPUT/evidenz_antworten.json",
                        help="Pfad zur Antworten-Datei")
    parser.add_argument("--bibliothek", default="_BIBLIOTHEK/Leitlinien",
                        help="Pfad zur Leitlinien-Bibliothek")
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent
    answers_path = base_path / args.answers
    bibliothek_path = base_path / args.bibliothek
    output_path = base_path / args.output

    print("=" * 60)
    print("LEITLINIEN-ANALYSE")
    print("=" * 60)

    # Lade Daten
    print(f"\nLade Antworten aus: {answers_path}")
    answers = load_answers(answers_path)
    print(f"  → {len(answers)} Antworten geladen")

    print(f"\nScanne Bibliothek: {bibliothek_path}")
    existing_pdfs = get_existing_pdfs(bibliothek_path)
    print(f"  → {len(existing_pdfs)} PDFs gefunden")

    # Analysiere Referenzen
    pdf_refs, text_refs = extract_guideline_refs(answers)
    print(f"\nLeitlinien-Referenzen:")
    print(f"  → {len(pdf_refs)} verschiedene PDF-Referenzen")
    print(f"  → {len(text_refs)} verschiedene Text-Referenzen (fehlende PDFs)")

    # Abdeckungsanalyse
    coverage = analyze_coverage(pdf_refs, existing_pdfs)
    print(f"\nPDF-Abdeckung:")
    print(f"  → {len(coverage['found'])} gefunden")
    print(f"  → {len(coverage['missing'])} fehlen")

    # Kategorisierung
    by_society = categorize_by_society(text_refs)
    by_topic = categorize_by_topic(text_refs)

    print(f"\nNach Fachgesellschaft:")
    for society, refs in sorted(by_society.items(), key=lambda x: -len(x[1])):
        if refs:
            print(f"  {society}: {len(refs)} Referenzen")

    print(f"\nNach Thema:")
    for topic, refs in sorted(by_topic.items(), key=lambda x: -len(x[1])):
        if refs:
            print(f"  {topic}: {len(refs)} Referenzen")

    # Download-Liste generieren
    download_list = generate_download_list(text_refs)
    high_priority = [d for d in download_list if d["priority"] == "high"]

    print(f"\n=== DOWNLOAD-EMPFEHLUNGEN ===")
    print(f"Hohe Priorität (≥3 Referenzen): {len(high_priority)}")
    for d in high_priority[:10]:
        ref = d["reference"][:60] + "..." if len(d["reference"]) > 60 else d["reference"]
        print(f"  [{d['count']}x] {ref}")
        if d["awmf_number"]:
            print(f"       → AWMF: {d['awmf_number']}")

    # Bericht erstellen
    report = {
        "summary": {
            "total_answers": len(answers),
            "answers_with_leitlinie": sum(pdf_refs.values()) + sum(text_refs.values()),
            "pdf_references": len(pdf_refs),
            "text_references": len(text_refs),
            "existing_pdfs": len(existing_pdfs),
            "coverage_found": len(coverage["found"]),
            "coverage_missing": len(coverage["missing"])
        },
        "by_society": {k: [(r, c) for r, c in v] for k, v in by_society.items()},
        "by_topic": {k: [(r, c) for r, c in v] for k, v in by_topic.items()},
        "coverage": coverage,
        "download_recommendations": download_list[:50],  # Top 50
        "fachgesellschaften": FACHGESELLSCHAFTEN
    }

    # Speichern
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ Bericht gespeichert: {output_path}")

    # Empfehlungen ausgeben
    print("\n" + "=" * 60)
    print("EMPFEHLUNGEN ZUR RAG-ERWEITERUNG")
    print("=" * 60)

    print("""
1. PRIORITÄT 1 - Fehlende Kernleitlinien:
   - ESC-Leitlinien (Vorhofflimmern, ACS, Herzinsuffizienz)
   - DVO-Leitlinie Osteoporose
   - KDIGO-Leitlinien (CKD, Diabetes bei CKD)
   - DGRh-Leitlinien (Rheumatoide Arthritis, Gicht)

2. PRIORITÄT 2 - Fachgesellschafts-Leitlinien:
   - DGHO/Onkopedia (Hämatologie)
   - DGE (Endokrinologie/Schilddrüse)
   - STIKO-Impfempfehlungen

3. Vorgehensweise:
   a) `scripts/fetch_guidelines_de.py` mit erweiterter Themenliste ausführen
   b) Manuell ESC/KDIGO-Leitlinien herunterladen (nicht AWMF)
   c) RAG-Index neu bauen mit erweiterten Quellen
   d) Antworten-Generierung für Fragen ohne Evidenz wiederholen
""")


if __name__ == "__main__":
    main()
