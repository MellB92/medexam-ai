#!/usr/bin/env python3
"""
MedExamAI: Konvertierung ins Pruefungsformat
============================================

Konvertiert Q&A ins 5-Punkte-Schema der Kenntnisprüfung.
Angepasst für MedExamAI aus Comet API.

Verwendung:
    python scripts/convert_to_exam_format.py --input _OUTPUT/cleaned_qa.json --output _OUTPUT/exam_format.json

Das 5-Punkte-Schema:
1. Definition & Klassifikation
2. Ätiologie & Pathophysiologie
3. Diagnostik
4. Therapie (mit Dosierungen!)
5. Rechtliche Aspekte
"""

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Projekt-Root zum Path hinzufügen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Zentrales Klassifikations-Modul importieren
from core.category_classifier import classify_medical_content, is_emergency

# ============================================================================
# MEDIZINISCHE REFERENZDATEN
# ============================================================================

KLASSIFIKATIONEN = {
    "herzinsuffizienz": "NYHA I-IV",
    "vorhofflimmern": "CHA2DS2-VASc",
    "pneumonie": "CRB-65 / CURB-65",
    "schenkelhalsfraktur": "Garden I-IV / Pauwels I-III",
    "sprunggelenk": "Weber A/B/C",
    "verbrennung": "Grad 1-3, Neunerregel",
    "schlaganfall": "NIHSS",
    "bewusstsein": "GCS (Glasgow Coma Scale)",
    "leberzirrhose": "Child-Pugh A/B/C",
    "niereninsuffizienz": "KDIGO G1-G5",
    "sepsis": "SOFA / qSOFA",
    "lungenembolie": "Wells-Score",
    "copd": "GOLD I-IV",
    "appendizitis": "Alvarado-Score",
    "pankreatitis": "Ranson / APACHE II",
    "diabetes": "HbA1c-Zielwerte",
}

STANDARD_DOSIERUNGEN = {
    "amoxicillin": "3x 1000mg p.o.",
    "metoprolol": "1-2x 47.5-95mg p.o.",
    "ramipril": "1x 2.5-10mg p.o.",
    "furosemid": "20-40mg i.v./p.o.",
    "heparin": "5000 IE s.c. (Prophylaxe) oder gewichtsadaptiert i.v.",
    "enoxaparin": "1x 40mg s.c. (Prophylaxe) oder 2x 1mg/kg (Therapie)",
    "paracetamol": "3-4x 1000mg p.o./i.v., max 4g/Tag",
    "ibuprofen": "3x 400-600mg p.o.",
    "morphin": "2.5-10mg i.v. titriert",
    "adrenalin": "1mg i.v. alle 3-5min (Reanimation)",
    "noradrenalin": "0.1-1 µg/kg/min i.v.",
    "prednisolon": "1mg/kg/Tag (Akut), dann Ausschleichen",
    "ceftriaxon": "1x 2g i.v.",
    "piperacillin/tazobactam": "3x 4.5g i.v.",
    "meropenem": "3x 1g i.v.",
    "vancomycin": "2x 1g i.v. (Spiegelkontrolle!)",
    "metformin": "2x 500-1000mg p.o.",
    "insulin": "Nach Schema, Start 0.5 IE/kg/Tag",
}

RECHTLICHE_ASPEKTE = {
    "aufklaerung": "§630e BGB - Aufklärungspflicht: Diagnose, Verlauf, Risiken, Alternativen",
    "einwilligung": "§630d BGB - Einwilligung vor Behandlung erforderlich",
    "dokumentation": "§630f BGB - Dokumentationspflicht in Patientenakte",
    "einsicht": "§630g BGB - Einsichtnahme in Patientenakte",
    "schweigepflicht": "§203 StGB - Ärztliche Schweigepflicht",
    "meldepflicht": "§6/§7 IfSG - Meldepflichtige Erkrankungen",
}

# ============================================================================
# SICHERHEITS-FUNKTIONEN
# ============================================================================


def safe_backup(filepath: str, backup_dir: str = "backups") -> Optional[str]:
    """Erstellt Backup vor Änderungen."""
    path = Path(filepath)
    if not path.exists():
        return None

    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"{path.stem}_{timestamp}{path.suffix}"

    import shutil
    shutil.copy2(path, backup_file)
    print(f"Backup erstellt: {backup_file}")

    return str(backup_file)


def safe_filter(original_count: int, filtered_count: int, operation: str) -> bool:
    """Prüft ob Filter zu viele Daten entfernt."""
    if original_count == 0:
        return True

    loss_percent = (1 - filtered_count / original_count) * 100

    if loss_percent > 90:
        print(f"KRITISCH: {operation} würde {loss_percent:.1f}% der Daten entfernen!")
        print(f"   Original: {original_count}, Nach Filter: {filtered_count}")
        print(f"   OPERATION ABGEBROCHEN!")
        return False
    elif loss_percent > 50:
        print(f"WARNUNG: {operation} entfernt {loss_percent:.1f}% der Daten")
        print(f"   Original: {original_count}, Nach Filter: {filtered_count}")

    return True


# ============================================================================
# DATENKLASSEN
# ============================================================================


@dataclass
class ExamQuestion:
    """Eine Frage im Prüfungsformat."""

    id: str
    frage: str
    patientenvorstellung: Optional[str] = None
    antwort: Dict = field(default_factory=dict)
    notfall_abcde: Optional[Dict] = None

    # Metadaten
    source: str = ""
    thema: str = ""
    kategorie: str = ""
    schwierigkeit: str = "mittel"

    # Enrichment-Flags
    needs_dose_enrichment: bool = False
    needs_classification_verification: bool = False
    needs_legal_enrichment: bool = False

    # Original für Vergleich
    original_answer: str = ""


# ============================================================================
# KONVERTIERUNGS-LOGIK
# ============================================================================


def detect_topic(text: str, source_file: str = "") -> Tuple[str, str]:
    """
    Erkennt Thema und Kategorie mittels zentralem Klassifikations-Modul.

    Verwendet core/category_classifier.py für präzise heuristische Analyse.
    """
    result = classify_medical_content(text, source_file)
    return result.topic, result.category


def is_emergency_case(text: str) -> bool:
    """Erkennt ob es ein Notfall ist mittels zentralem Klassifikations-Modul."""
    return is_emergency(text)


def extract_medications(text: str) -> List[str]:
    """Extrahiert erwähnte Medikamente."""
    found = []
    text_lower = text.lower()

    for med in STANDARD_DOSIERUNGEN.keys():
        if med in text_lower:
            found.append(med)

    return found


def create_abcde_schema() -> Dict:
    """Erstellt ABCDE-Schema Template für Notfälle."""
    return {
        "A_Airway": "Atemwege freimachen, Absaugen, Guedel-/Wendl-Tubus, ggf. Intubation",
        "B_Breathing": "O2-Gabe (15L/min über Maske), Ziel-SpO2 >94%, Auskultation, ggf. Beatmung",
        "C_Circulation": "2 großlumige Zugänge, Volumen (kristalloid), Monitoring (RR, HF, EKG)",
        "D_Disability": "GCS dokumentieren, Pupillen (Größe, Lichtreaktion), BZ messen",
        "E_Exposure": "Entkleiden, Ganzkörperinspektion, Temperatur, Wärmeerhalt",
    }


def create_5_point_answer(original_answer: str, frage: str, source_file: str = "") -> Tuple[Dict, Dict]:
    """
    Konvertiert eine Antwort ins 5-Punkte-Schema.

    Returns:
        (structured_answer, enrichment_flags)
    """
    text_lower = (original_answer + " " + frage).lower()
    thema, kategorie = detect_topic(text_lower, source_file)

    # Basis-Struktur
    answer = {
        "1_Definition_Klassifikation": "",
        "2_Aetiologie_Pathophysiologie": "",
        "3_Diagnostik": "",
        "4_Therapie": "",
        "5_Rechtlich": "",
    }

    flags = {
        "needs_dose_enrichment": False,
        "needs_classification_verification": False,
        "needs_legal_enrichment": False,
    }

    # Versuche vorhandene Struktur zu erkennen
    sections = {
        "definition": ["definition", "was ist", "bezeichnet", "versteht man"],
        "klassifikation": ["klassifikation", "stadien", "grad", "score", "einteilung"],
        "aetiologie": ["ursache", "ätiologie", "pathophysio", "entsteh", "risikofaktor"],
        "diagnostik": ["diagnostik", "untersuchung", "labor", "bildgebung", "anamnese"],
        "therapie": ["therapie", "behandlung", "medikament", "operation", "first-line"],
        "rechtlich": ["§", "bgb", "aufklärung", "einwilligung", "dokumentation", "recht"],
    }

    # Parse nach Abschnitten
    lines = original_answer.split('\n')
    current_section = None
    section_content = {k: [] for k in sections.keys()}

    for line in lines:
        line_lower = line.lower()

        for section, keywords in sections.items():
            if any(kw in line_lower for kw in keywords):
                current_section = section
                break

        if current_section and line.strip():
            section_content[current_section].append(line.strip())

    # Baue strukturierte Antwort
    if section_content["definition"] or section_content["klassifikation"]:
        answer["1_Definition_Klassifikation"] = " ".join(
            section_content["definition"] + section_content["klassifikation"]
        )
    else:
        # Füge relevante Klassifikation hinzu
        for condition, klassifikation in KLASSIFIKATIONEN.items():
            if condition in text_lower:
                answer["1_Definition_Klassifikation"] = f"Klassifikation: {klassifikation}"
                break
        if not answer["1_Definition_Klassifikation"]:
            answer["1_Definition_Klassifikation"] = f"[Definition von {thema} ergänzen]"
        flags["needs_classification_verification"] = True

    if section_content["aetiologie"]:
        answer["2_Aetiologie_Pathophysiologie"] = " ".join(section_content["aetiologie"])
    else:
        answer["2_Aetiologie_Pathophysiologie"] = "[Ätiologie ergänzen]"

    if section_content["diagnostik"]:
        answer["3_Diagnostik"] = " ".join(section_content["diagnostik"])
    else:
        answer["3_Diagnostik"] = "1. Anamnese, 2. Körperliche Untersuchung, 3. Labor, 4. Bildgebung"

    if section_content["therapie"]:
        therapie_text = " ".join(section_content["therapie"])
        answer["4_Therapie"] = therapie_text

        meds = extract_medications(therapie_text)
        if meds:
            dose_pattern = r'\d+\s*(mg|g|µg|IE|ml)'
            if not re.search(dose_pattern, therapie_text):
                flags["needs_dose_enrichment"] = True
                # Füge Standarddosierungen hinzu
                dose_hints = []
                for med in meds:
                    if med in STANDARD_DOSIERUNGEN:
                        dose_hints.append(f"{med.capitalize()}: {STANDARD_DOSIERUNGEN[med]}")
                if dose_hints:
                    answer["4_Therapie"] += "\n[Dosierungen: " + "; ".join(dose_hints) + "]"
    else:
        answer["4_Therapie"] = "[Therapie mit Dosierungen ergänzen]"
        flags["needs_dose_enrichment"] = True

    if section_content["rechtlich"]:
        answer["5_Rechtlich"] = " ".join(section_content["rechtlich"])
    else:
        answer["5_Rechtlich"] = (
            "§630d BGB (Einwilligung), §630e BGB (Aufklärung), §630f BGB (Dokumentation)"
        )
        flags["needs_legal_enrichment"] = True

    return answer, flags


def convert_qa_to_exam_format(qa: Dict, index: int) -> ExamQuestion:
    """Konvertiert ein Q&A-Paar ins Prüfungsformat."""

    # MedExamAI Format: 'question' und 'answer'
    frage = qa.get('question', qa.get('frage', ''))
    original_answer = qa.get('answer', qa.get('antwort', ''))
    source_file = qa.get('source_file', qa.get('source', ''))

    if isinstance(original_answer, dict):
        original_answer_text = json.dumps(original_answer, ensure_ascii=False)
    else:
        original_answer_text = str(original_answer) if original_answer else ""

    # Thema und Kategorie erkennen (Quelldatei hat Priorität!)
    thema, kategorie = detect_topic(frage + " " + original_answer_text, source_file)

    # 5-Punkte-Antwort erstellen
    structured_answer, flags = create_5_point_answer(original_answer_text, frage, source_file)

    # Prüfe auf Notfall
    is_emergency = is_emergency_case(frage + " " + original_answer_text)
    abcde = create_abcde_schema() if is_emergency else None

    # Patientenvorstellung generieren
    patientenvorstellung = None
    if "patient" in frage.lower() or "jährig" in frage.lower():
        patientenvorstellung = frage

    # ID generieren: Quelldatei_Index (z.B. "Rechtsmedizin_0001")
    if source_file:
        source_base = Path(source_file).stem
        question_id = f"{source_base}_{index:04d}"
    else:
        question_id = qa.get('id', f"Q{index:04d}")

    return ExamQuestion(
        id=question_id,
        frage=frage,
        patientenvorstellung=patientenvorstellung,
        antwort=structured_answer,
        notfall_abcde=abcde,
        source=source_file,
        thema=thema,
        kategorie=kategorie,
        schwierigkeit="mittel",
        needs_dose_enrichment=flags["needs_dose_enrichment"],
        needs_classification_verification=flags["needs_classification_verification"],
        needs_legal_enrichment=flags["needs_legal_enrichment"],
        original_answer=original_answer_text[:500],
    )


def convert_all(input_file: str, output_file: str, enrichment_file: str):
    """Konvertiert alle Q&A Paare."""

    print("\n" + "=" * 70)
    print("KONVERTIERUNG INS PRUEFUNGSFORMAT (5-Punkte-Schema)")
    print("=" * 70)

    input_path = Path(input_file)
    if not input_path.exists():
        print(f"FEHLER: Input-Datei nicht gefunden: {input_file}")
        return 1

    # Backup
    output_path = Path(output_file)
    if output_path.exists():
        safe_backup(output_file)

    # Laden
    print(f"\nLade: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # MedExamAI Format
    if isinstance(data, dict) and 'qa_pairs' in data:
        qa_pairs = data['qa_pairs']
    elif isinstance(data, list):
        qa_pairs = data
    else:
        qa_pairs = [data]

    print(f"   -> {len(qa_pairs)} Q&A Paare gefunden")

    # Nur Fragen mit Antworten konvertieren
    qa_with_answers = [q for q in qa_pairs if q.get('answer')]
    print(f"   -> {len(qa_with_answers)} haben Antworten (werden konvertiert)")

    # Konvertieren
    print("\nKonvertiere...")

    converted = []
    needs_enrichment = []

    for i, qa in enumerate(qa_with_answers):
        exam_q = convert_qa_to_exam_format(qa, i)
        converted.append(asdict(exam_q))

        if (
            exam_q.needs_dose_enrichment
            or exam_q.needs_classification_verification
            or exam_q.needs_legal_enrichment
        ):
            needs_enrichment.append({
                'id': exam_q.id,
                'frage': exam_q.frage[:100],
                'needs_dose_enrichment': exam_q.needs_dose_enrichment,
                'needs_classification_verification': exam_q.needs_classification_verification,
                'needs_legal_enrichment': exam_q.needs_legal_enrichment,
            })

        if (i + 1) % 500 == 0:
            print(f"   {i + 1}/{len(qa_with_answers)} verarbeitet...")

    # Sicherheitsprüfung
    if not safe_filter(len(qa_with_answers), len(converted), "Konvertierung"):
        print("Konvertierung abgebrochen!")
        return 1

    # Speichern - Hauptdatei
    print(f"\nSpeichere: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'metadata': {
                'created': datetime.now().isoformat(),
                'source_file': input_file,
                'total_questions': len(converted),
                'format': '5-Punkte-Schema Kenntnisprüfung',
                'version': '1.0-medexamai',
            },
            'questions': converted,
        }, f, ensure_ascii=False, indent=2)

    # Speichern - Enrichment-Liste
    print(f"Speichere Enrichment-Liste: {enrichment_file}")
    with open(enrichment_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total_needs_enrichment': len(needs_enrichment),
            'questions': needs_enrichment
        }, f, ensure_ascii=False, indent=2)

    # Statistik
    print("\n" + "-" * 70)
    print("STATISTIK")
    print("-" * 70)
    print(f"   Total konvertiert:              {len(converted)}")
    print(f"   Brauchen Dosierungs-Enrichment: {sum(1 for q in converted if q['needs_dose_enrichment'])}")
    print(f"   Brauchen Klassifikations-Check: {sum(1 for q in converted if q['needs_classification_verification'])}")
    print(f"   Brauchen Rechtliches:           {sum(1 for q in converted if q['needs_legal_enrichment'])}")
    print(f"   Notfall-Fälle (mit ABCDE):      {sum(1 for q in converted if q['notfall_abcde'])}")

    # Kategorien
    kategorien = {}
    for q in converted:
        kat = q['kategorie']
        kategorien[kat] = kategorien.get(kat, 0) + 1

    print(f"\n   Nach Kategorie:")
    for kat, count in sorted(kategorien.items(), key=lambda x: -x[1]):
        print(f"      {kat}: {count}")

    print("\n" + "=" * 70)
    print("KONVERTIERUNG ABGESCHLOSSEN")
    print("=" * 70)

    return 0


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Konvertiere Q&A ins 5-Punkte-Prüfungsformat',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiel:
    python scripts/convert_to_exam_format.py --input _OUTPUT/cleaned_qa.json

Das 5-Punkte-Schema:
    1. Definition & Klassifikation
    2. Ätiologie & Pathophysiologie
    3. Diagnostik
    4. Therapie (mit Dosierungen!)
    5. Rechtliche Aspekte
        """
    )
    parser.add_argument('--input', '-i', default='_OUTPUT/cleaned_qa.json', help='Input Q&A JSON')
    parser.add_argument('--output', '-o', default='_OUTPUT/exam_format.json', help='Output Datei')
    parser.add_argument('--enrichment', '-e', default='_OUTPUT/enrichment_needed.json', help='Enrichment-Liste')
    parser.add_argument('--dry-run', action='store_true', help='Nur analysieren, nicht speichern')

    args = parser.parse_args()

    if args.dry_run:
        print("DRY-RUN Modus - keine Dateien werden geschrieben")
        # TODO: Implement dry-run
        return 0

    return convert_all(args.input, args.output, args.enrichment)


if __name__ == '__main__':
    sys.exit(main())
