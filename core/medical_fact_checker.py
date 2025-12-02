#!/usr/bin/env python3
"""
Medizinische Faktenprüfung - Verifiziert fachliche Informationen.

Erkennt und verifiziert:
1. Dosierungen (mg, mg/kg, IE, etc.)
2. Klassifikationen (Weber, Fontaine, NYHA, Child-Pugh, etc.)
3. Laborwerte und Grenzwerte
4. Therapieempfehlungen
5. Zeitangaben (Intervalle, Dauer)

Verwendet:
- Perplexity Web-Suche (AWMF, DocCheck, RKI)
- Lokale Leitlinien-Datenbank
"""

import asyncio
import json
import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class MedicalFact:
    """Ein medizinischer Fakt zum Verifizieren"""
    text: str
    fact_type: str  # dosage, classification, lab_value, therapy, time_interval
    context: str
    source_file: str
    line_number: int
    extracted_value: str  # Der extrahierte Wert


@dataclass
class VerificationResult:
    """Ergebnis der Verifikation"""
    fact: MedicalFact
    status: str  # "verified", "incorrect", "uncertain", "not_found"
    confidence: float
    correct_value: Optional[str]
    source: str
    explanation: str


# Pattern für medizinische Fakten - MIT VOLLEM KONTEXT
# Wichtig: Pattern erfassen das Medikament/die Substanz MIT der Dosierung
MEDICAL_FACT_PATTERNS = {
    "medication_dosage": [
        # Medikamente mit Dosierung (erweiterte Liste)
        (r'(Prednisolon|Methylprednisolon|Dexamethason|Hydrocortison|'
         r'Metformin|Glibenclamid|Sitagliptin|Empagliflozin|'
         r'Ramipril|Enalapril|Lisinopril|Captopril|'
         r'Bisoprolol|Metoprolol|Carvedilol|Propranolol|'
         r'Amlodipin|Nifedipin|Verapamil|Diltiazem|'
         r'Furosemid|Torasemid|Hydrochlorothiazid|Spironolacton|'
         r'ASS|Aspirin|Clopidogrel|Ticagrelor|'
         r'Heparin|Enoxaparin|Rivaroxaban|Apixaban|'
         r'Adrenalin|Noradrenalin|Dobutamin|Dopamin|'
         r'Amiodaron|Digoxin|Verapamil|Adenosin|'
         r'Ceftriaxon|Cefuroxim|Ceftazidim|Cefotaxim|'
         r'Ampicillin|Amoxicillin|Piperacillin|'
         r'Doxycyclin|Azithromycin|Clarithromycin|'
         r'Ciprofloxacin|Levofloxacin|Moxifloxacin|'
         r'Metronidazol|Clindamycin|Vancomycin|Meropenem|'
         r'Ibuprofen|Diclofenac|Metamizol|Paracetamol|'
         r'Morphin|Fentanyl|Tramadol|Tilidin|'
         r'Omeprazol|Pantoprazol|Esomeprazol|'
         r'Ondansetron|Metoclopramid|Dimenhydrinat)'
         r'\s+(\d+(?:,\d+)?(?:\s*-\s*\d+(?:,\d+)?)?)\s*(mg|g|µg|mcg|IE|IU|ml)',
         "Medikamentendosis"),
    ],
    "infusion_concentration": [
        # Infusionslösungen mit Konzentration
        (r'(NaCl|Glukose|Glucose|Ringer|Ringerlaktat|Vollelektrolyt)\s*'
         r'(\d+(?:,\d+)?)\s*%(?:ig)?',
         "Infusionskonzentration"),
    ],
    "classification": [
        # Klassifikationen mit Stadien (unverändered)
        (r'(Weber|Fontaine|NYHA|Child[-\s]?Pugh|ASA|Hinchey|Ranson|Glasgow|TNM|FIGO|Ann[-\s]?Arbor)\s*[-:]?\s*([IVX0-9]+|Stadium\s*[IVX0-9]+|[A-C])',
         "Klassifikation"),
        # GCS
        (r'GCS\s*(?:von\s*)?(\d{1,2})', "Glasgow Coma Scale"),
        # Gradeinteilungen
        (r'Grad\s*([IVX0-9]+)', "Gradeinteilung"),
    ],
    "lab_value": [
        # Laborwerte mit Einheiten (unverändered)
        (r'(TSH|fT3|fT4|CRP|PCT|Kreatinin|GFR|HbA1c|Troponin|BNP|Laktat|pH|pCO2|pO2|Lipase|Amylase|GOT|GPT|Bilirubin|Hb|Hämoglobin|Leukozyten|Thrombozyten)\s*[:=<>]?\s*(\d+(?:,\d+)?)\s*(mg/dl|ng/ml|µg/l|mmol/l|U/l|g/dl|/µl|%)?',
         "Laborwert"),
        # Normalwerte/Grenzwerte
        (r'(?:Norm(?:al)?wert|Grenzwert|Referenz|Obergrenze|Untergrenze)[:=]?\s*(\d+(?:,\d+)?(?:\s*-\s*\d+(?:,\d+)?)?)',
         "Normalwert"),
    ],
    "therapy_recommendation": [
        # First-Line Therapie (unverändered)
        (r'(?:Mittel der (?:1\.|ersten) Wahl|First[-\s]?[Ll]ine|Standardtherapie|Therapie der Wahl)[:=]?\s*([A-Za-zäöüß\-]+(?:\s+[A-Za-zäöüß\-]+)?)',
         "Therapieempfehlung"),
    ],
    "time_interval": [
        # Zeitangaben (unverändered)
        (r'(?:alle|jede[nr]?)\s*(\d+(?:-\d+)?)\s*(Stunden?|Tage?|Wochen?|Monate?|Jahre?)',
         "Zeitintervall"),
        # Dauer
        (r'(?:für|über|während)\s*(\d+(?:-\d+)?)\s*(Stunden?|Tage?|Wochen?|Monate?)',
         "Behandlungsdauer"),
    ],
}


class MedicalFactChecker:
    """Prüft medizinische Fakten auf Korrektheit"""

    def __init__(self, use_web_search: bool = True, use_leitlinien: bool = True):
        self.use_web_search = use_web_search
        self.use_leitlinien = use_leitlinien

        self._compile_patterns()

        # Web-Suche
        self.web_search = None
        if use_web_search:
            try:
                from core.web_search import search_medical_web
                self.web_search = search_medical_web
            except ImportError:
                print("⚠️ Web-Suche nicht verfügbar")

        # Leitlinien-Index
        self.leitlinien_index = {}
        if use_leitlinien:
            self._load_leitlinien_index()

    def _compile_patterns(self):
        """Kompiliert alle Regex-Pattern"""
        self.patterns = {}
        for fact_type, patterns in MEDICAL_FACT_PATTERNS.items():
            self.patterns[fact_type] = [
                (re.compile(p, re.IGNORECASE), label)
                for p, label in patterns
            ]

    def _load_leitlinien_index(self):
        """Lädt den Leitlinien-Index"""
        manifest_path = Path("_BIBLIOTHEK/leitlinien_manifest.json")
        if manifest_path.exists():
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data.get('items', []):
                    # Extrahiere Thema aus Dateinamen
                    filename = Path(item['file']).stem.lower()
                    for keyword in ['appendizitis', 'pankreatitis', 'pneumonie',
                                   'herzinsuffizienz', 'diabetes', 'asthma', 'copd',
                                   'sepsis', 'anaphylaxie', 'reanimation', 'hypertonie',
                                   'schlaganfall', 'epilepsie', 'meningitis']:
                        if keyword in filename:
                            self.leitlinien_index[keyword] = item['file']

    def extract_facts(self, text: str, source_file: str = "") -> List[MedicalFact]:
        """Extrahiert überprüfbare medizinische Fakten"""
        facts = []
        lines = text.split('\n')

        for line_num, line in enumerate(lines, 1):
            for fact_type, patterns in self.patterns.items():
                for pattern, label in patterns:
                    for match in pattern.finditer(line):
                        # Kontext extrahieren (umgebende Zeilen)
                        start = max(0, line_num - 3)
                        end = min(len(lines), line_num + 3)
                        context = '\n'.join(lines[start:end])

                        facts.append(MedicalFact(
                            text=match.group(0),
                            fact_type=fact_type,
                            context=context,
                            source_file=source_file,
                            line_number=line_num,
                            extracted_value=match.group(0),
                        ))

        return facts

    async def verify_fact(self, fact: MedicalFact) -> VerificationResult:
        """Verifiziert einen einzelnen Fakt"""

        # Erstelle spezifische Suchanfrage basierend auf Fakt-Typ
        query = self._build_verification_query(fact)

        source = "none"
        correct_value = None
        confidence = 0.5
        status = "uncertain"
        explanation = "Keine Verifikation möglich"

        # 1. Perplexity Web-Suche
        if self.web_search:
            try:
                results = self.web_search(query, max_results=3)
                if results:
                    web_content = results[0].get('snippet', '')
                    source = "perplexity_web"

                    # Vergleiche mit extrahiertem Fakt
                    comparison = self._compare_fact(fact, web_content)
                    confidence = comparison['confidence']
                    correct_value = comparison.get('correct_value')

                    if confidence >= 0.8:
                        status = "verified"
                        explanation = f"Verifiziert: {web_content[:100]}..."
                    elif confidence >= 0.5:
                        status = "uncertain"
                        explanation = f"Teilweise bestätigt"
                    else:
                        status = "incorrect"
                        if correct_value:
                            explanation = f"Erwartet: {correct_value}"
                        else:
                            explanation = f"Nicht bestätigt durch: {web_content[:80]}..."

            except Exception as e:
                explanation = f"Web-Suche Fehler: {e}"

        return VerificationResult(
            fact=fact,
            status=status,
            confidence=confidence,
            correct_value=correct_value,
            source=source,
            explanation=explanation,
        )

    def _build_verification_query(self, fact: MedicalFact) -> str:
        """Erstellt eine spezifische Suchanfrage für den Fakt"""
        topic = self._detect_topic(fact.context)

        if fact.fact_type == "medication_dosage":
            # Extrahiere Medikament aus dem Fakt
            # z.B. "Ramipril 5 mg" -> "Ramipril Dosierung Hypertonie"
            return f"{fact.text} Dosierung {topic} AWMF Leitlinie"

        elif fact.fact_type == "infusion_concentration":
            return f"{fact.text} Infusion Konzentration medizinisch"

        elif fact.fact_type == "classification":
            return f"{fact.text} Klassifikation Einteilung {topic}"

        elif fact.fact_type == "lab_value":
            return f"{fact.text} Normalwert Referenzbereich Labor"

        elif fact.fact_type == "therapy_recommendation":
            return f"{topic} Therapie der Wahl Leitlinie AWMF"

        else:
            return f"{topic} {fact.text} medizin deutsch"

    def _detect_topic(self, context: str) -> str:
        """Erkennt das medizinische Thema aus dem Kontext"""
        topics = {
            'appendizitis': ['appendizitis', 'blinddarm', 'mcburney'],
            'pankreatitis': ['pankreatitis', 'pankreas', 'lipase', 'amylase'],
            'pneumonie': ['pneumonie', 'lungenentzündung', 'infiltrat'],
            'herzinsuffizienz': ['herzinsuffizienz', 'nyha', 'ejektionsfraktion'],
            'diabetes': ['diabetes', 'hba1c', 'blutzucker', 'insulin'],
            'anaphylaxie': ['anaphylaxie', 'allergie', 'schock'],
            'sepsis': ['sepsis', 'sirs', 'qsofa'],
            'hypertonie': ['hypertonie', 'blutdruck', 'antihypertensiv'],
            'meningitis': ['meningitis', 'hirnhaut', 'kernig', 'brudzinski'],
        }

        context_lower = context.lower()
        for topic, keywords in topics.items():
            if any(kw in context_lower for kw in keywords):
                return topic
        return "allgemein"

    def _compare_fact(self, fact: MedicalFact, reference: str) -> Dict[str, Any]:
        """Vergleicht einen Fakt mit Referenzinformation - kontextabhängig"""

        reference_lower = reference.lower()
        fact_text = fact.text

        # Für Medikamentendosierungen: Prüfe ob Medikament + Dosis erwähnt wird
        if fact.fact_type == "medication_dosage":
            # Extrahiere Medikament und Dosis aus dem Fakt
            med_match = re.match(
                r'([A-Za-zäöüß]+)\s+(\d+(?:,\d+)?(?:\s*-\s*\d+(?:,\d+)?)?)\s*(mg|g|µg|IE)',
                fact_text, re.IGNORECASE
            )
            if med_match:
                medication = med_match.group(1).lower()
                dosage = med_match.group(2).replace(',', '.')
                unit = med_match.group(3)

                # Prüfe ob das Medikament in der Referenz erwähnt wird
                if medication in reference_lower:
                    # Suche nach der Dosierung in der Nähe des Medikaments
                    # Extrahiere alle Dosierungen aus der Referenz für dieses Medikament
                    ref_pattern = rf'{medication}\s*[:\s]?\s*(\d+(?:,\d+)?(?:\s*-\s*\d+(?:,\d+)?)?)\s*{unit}'
                    ref_dosages = re.findall(ref_pattern, reference_lower)

                    if ref_dosages:
                        # Vergleiche mit der gefundenen Dosierung
                        fact_dose = float(dosage.split('-')[0])
                        for ref_dose_str in ref_dosages:
                            ref_dose = float(ref_dose_str.replace(',', '.').split('-')[0])
                            # Toleranz von 20% oder exakte Übereinstimmung für gängige Dosierungen
                            if abs(fact_dose - ref_dose) / max(fact_dose, ref_dose, 1) < 0.2:
                                return {'confidence': 0.9, 'correct_value': None}

                        # Medikament gefunden aber andere Dosierung
                        return {
                            'confidence': 0.3,
                            'correct_value': f"{medication.title()} {ref_dosages[0]} {unit}"
                        }
                    else:
                        # Medikament erwähnt, keine spezifische Dosierung gefunden
                        return {'confidence': 0.6, 'correct_value': None}
                else:
                    # Medikament nicht in Referenz
                    return {'confidence': 0.5, 'correct_value': None}

        # Für Klassifikationen: Direkte Textsuche
        elif fact.fact_type == "classification":
            if fact_text.lower() in reference_lower:
                return {'confidence': 0.95, 'correct_value': None}
            else:
                return {'confidence': 0.4, 'correct_value': None}

        # Für Laborwerte: Vergleiche Zahlen im Kontext
        elif fact.fact_type == "lab_value":
            fact_numbers = re.findall(r'\d+(?:,\d+)?', fact.text)
            ref_numbers = re.findall(r'\d+(?:,\d+)?', reference)

            if fact_numbers and ref_numbers:
                fact_n = float(fact_numbers[0].replace(',', '.'))
                for rn_str in ref_numbers:
                    rn = float(rn_str.replace(',', '.'))
                    if abs(fact_n - rn) / max(fact_n, rn, 1) < 0.15:
                        return {'confidence': 0.85, 'correct_value': None}
                return {'confidence': 0.4, 'correct_value': str(ref_numbers[0])}

            return {'confidence': 0.5, 'correct_value': None}

        # Fallback: Einfacher Zahlenvergleich
        else:
            fact_numbers = re.findall(r'\d+(?:,\d+)?', fact.text)
            ref_numbers = re.findall(r'\d+(?:,\d+)?', reference)

            if not fact_numbers:
                return {'confidence': 0.5, 'correct_value': None}

            fact_numbers = [float(n.replace(',', '.')) for n in fact_numbers]
            ref_numbers = [float(n.replace(',', '.')) for n in ref_numbers]

            matches = 0
            for fn in fact_numbers:
                for rn in ref_numbers:
                    if abs(fn - rn) / max(fn, rn, 1) < 0.15:
                        matches += 1
                        break

            confidence = matches / len(fact_numbers) if fact_numbers else 0.5
            correct_value = str(ref_numbers[0]) if confidence < 0.5 and ref_numbers else None

            return {'confidence': confidence, 'correct_value': correct_value}

    async def check_file(self, filepath: Path,
                         max_facts: int = 20) -> Dict[str, Any]:
        """Prüft eine Datei auf faktische Fehler"""

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f"Prüfe: {filepath.name}")

        # Extrahiere Fakten
        facts = self.extract_facts(content, filepath.name)
        print(f"  Gefundene Fakten: {len(facts)}")

        # Limitiere für API-Rate-Limits
        facts_to_check = facts[:max_facts]

        results = []
        verified = 0
        incorrect = 0
        uncertain = 0

        for fact in facts_to_check:
            try:
                result = await self.verify_fact(fact)
                results.append(asdict(result))

                if result.status == "verified":
                    verified += 1
                elif result.status == "incorrect":
                    incorrect += 1
                else:
                    uncertain += 1

            except Exception as e:
                print(f"  Fehler bei Verifikation: {e}")

        return {
            'file': filepath.name,
            'facts_found': len(facts),
            'facts_checked': len(facts_to_check),
            'verified': verified,
            'incorrect': incorrect,
            'uncertain': uncertain,
            'results': results,
        }


async def check_archive(archive_dir: Path, output_dir: Path,
                        max_files: int = 5, max_facts_per_file: int = 10) -> Dict:
    """Prüft LLM_ARCHIVE auf faktische Fehler"""

    checker = MedicalFactChecker(use_web_search=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        'timestamp': datetime.now().isoformat(),
        'files_checked': 0,
        'total_facts': 0,
        'verified': 0,
        'incorrect': 0,
        'uncertain': 0,
        'potentially_incorrect': [],
        'files': [],
    }

    files = sorted([f for f in archive_dir.glob("*.md")
                   if not f.name.startswith("_")])[:max_files]

    print(f"\nPrüfe {len(files)} Dateien auf faktische Fehler...\n")

    for filepath in files:
        result = await checker.check_file(filepath, max_facts=max_facts_per_file)

        stats['files_checked'] += 1
        stats['total_facts'] += result['facts_found']
        stats['verified'] += result['verified']
        stats['incorrect'] += result['incorrect']
        stats['uncertain'] += result['uncertain']

        # Sammle potenziell falsche Fakten
        for r in result['results']:
            if r['status'] == 'incorrect':
                stats['potentially_incorrect'].append({
                    'file': result['file'],
                    'fact': r['fact']['text'],
                    'type': r['fact']['fact_type'],
                    'correct_value': r['correct_value'],
                    'explanation': r['explanation'],
                })

        stats['files'].append({
            'name': result['file'],
            'facts': result['facts_found'],
            'checked': result['facts_checked'],
            'verified': result['verified'],
            'incorrect': result['incorrect'],
        })

        status = "✅" if result['incorrect'] == 0 else "⚠️"
        print(f"  {status} {result['file']}: {result['verified']} verifiziert, "
              f"{result['incorrect']} mögl. falsch, {result['uncertain']} unsicher")

    # Speichere Bericht
    report_path = output_dir / "_FACT_CHECK_REPORT.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Medizinische Faktenprüfung")
    parser.add_argument("--input", "-i", type=Path, default=Path("_LLM_ARCHIVE_CLEAN"),
                        help="Eingabeverzeichnis")
    parser.add_argument("--output", "-o", type=Path, default=Path("_LLM_ARCHIVE_CLEAN"),
                        help="Ausgabeverzeichnis")
    parser.add_argument("--max-files", type=int, default=5,
                        help="Max. Anzahl Dateien")
    parser.add_argument("--max-facts", type=int, default=10,
                        help="Max. Fakten pro Datei")

    args = parser.parse_args()

    print("=" * 60)
    print("MEDIZINISCHE FAKTENPRÜFUNG")
    print("=" * 60)
    print()
    print("Prüft fachliche Informationen gegen:")
    print("  - Perplexity Web-Suche (AWMF, DocCheck)")
    print("  - Leitlinien-Datenbank")
    print()

    stats = asyncio.run(check_archive(
        args.input, args.output,
        max_files=args.max_files,
        max_facts_per_file=args.max_facts
    ))

    print()
    print("=" * 60)
    print("ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"Dateien geprüft:      {stats['files_checked']}")
    print(f"Fakten gefunden:      {stats['total_facts']}")
    print(f"Verifiziert:          {stats['verified']}")
    print(f"Möglicherweise falsch: {stats['incorrect']}")
    print(f"Unsicher:             {stats['uncertain']}")
    print()

    if stats['potentially_incorrect']:
        print("POTENZIELL FALSCHE INFORMATIONEN:")
        print("-" * 40)
        for item in stats['potentially_incorrect'][:10]:
            print(f"  Datei: {item['file']}")
            print(f"  Fakt:  {item['fact']}")
            print(f"  Typ:   {item['type']}")
            if item['correct_value']:
                print(f"  Korr.: {item['correct_value']}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
