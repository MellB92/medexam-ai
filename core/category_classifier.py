#!/usr/bin/env python3
"""
MedExamAI: Heuristische Kategorie-Klassifikation
=================================================

Zentrales Modul für die Kategorisierung medizinischer Fragen.
Verwendet gewichtetes Scoring für robuste Klassifikation.

Verwendung:
    from core.category_classifier import classify_medical_content, MedicalCategory

    result = classify_medical_content(
        text="Patient mit Herzinsuffizienz NYHA III...",
        source_file="Protokolle_KP.pdf"
    )
    print(result.category)  # "Innere Medizin"
    print(result.confidence)  # 0.85
"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class MedicalCategory(Enum):
    """Medizinische Fachgebiete für die Kenntnisprüfung."""

    INNERE_MEDIZIN = "Innere Medizin"
    CHIRURGIE = "Chirurgie"
    UNFALLCHIRURGIE_ORTHOPAEDIE = "Unfallchirurgie/Orthopädie"
    NEUROLOGIE = "Neurologie"
    NOTFALLMEDIZIN = "Notfallmedizin"
    PAEDIATRIE = "Pädiatrie"
    GYNAEKOLOGIE = "Gynäkologie/Geburtshilfe"
    PSYCHIATRIE = "Psychiatrie"
    RECHTSMEDIZIN = "Rechtsmedizin"
    DERMATOLOGIE = "Dermatologie"
    HNO = "HNO"
    UROLOGIE = "Urologie"
    AUGENHEILKUNDE = "Augenheilkunde"
    ANAESTHESIE = "Anästhesie"
    RADIOLOGIE = "Radiologie"
    ALLGEMEINMEDIZIN = "Allgemeinmedizin"


@dataclass
class ClassificationResult:
    """Ergebnis der Kategorie-Klassifikation."""

    category: str
    topic: str
    confidence: float
    all_scores: Dict[str, float]
    matched_keywords: Dict[str, List[str]]
    source_detected: bool  # True wenn aus Quelldatei erkannt


# Gewichtete Keywords für jede Kategorie
# Gewichtung: 3 = sehr spezifisch, 2 = spezifisch, 1 = allgemein
CATEGORY_KEYWORDS: Dict[str, Dict[str, int]] = {
    "Innere Medizin": {
        # Kardiologie
        "herzinsuffizienz": 3, "myokardinfarkt": 3, "vorhofflimmern": 3,
        "angina pectoris": 3, "herzrhythmusstörung": 2, "ekg": 1,
        "hypertonie": 2, "blutdruck": 1, "kardiomyopathie": 3,
        "herzinfarkt": 3, "stemi": 3, "nstemi": 3, "acs": 2,
        "herzklappenfehler": 3, "endokarditis": 3, "perikarditis": 3,
        "thoraxschmerz": 2, "brustschmerz": 2, "angina": 2,
        "koronarsyndrom": 3, "koronare herzkrankheit": 3, "khk": 2,
        # Pneumologie
        "pneumonie": 3, "copd": 3, "asthma": 2, "lungenembolie": 3,
        "ateminsuffizienz": 2, "bronchitis": 2, "lungenfibrose": 3,
        "pleuraerguss": 3, "pneumothorax": 2, "ards": 3,
        # Gastroenterologie
        "pankreatitis": 3, "hepatitis": 3, "leberzirrhose": 3,
        "gerd": 2, "ulkus": 2, "ösophagus": 2, "kolitis": 2,
        "cholezystitis": 2, "ikterus": 2, "aszites": 3,
        "gastrointestinal": 2, "blutung": 1, "hämatemesis": 3,
        # Nephrologie
        "niereninsuffizienz": 3, "dialyse": 3, "glomerulonephritis": 3,
        "proteinurie": 2, "harnwegsinfekt": 2, "pyelonephritis": 3,
        "akutes nierenversagen": 3, "chronische nierenerkrankung": 3,
        # Hämatologie/Onkologie
        "anämie": 2, "leukämie": 3, "lymphom": 3, "thrombozytopenie": 2,
        "gerinnungsstörung": 2, "antikoagulation": 2, "thrombose": 2,
        "tumormarker": 2, "chemotherapie": 2,
        # Rheumatologie
        "rheuma": 2, "arthritis": 2, "lupus": 3, "vaskulitis": 3,
        "kollagenose": 3, "spondylitis": 3, "gicht": 2,
        # Endokrinologie
        "diabetes": 2, "schilddrüse": 2, "hyperthyreose": 3, "hypothyreose": 3,
        "nebenniere": 2, "cushing": 3, "addison": 3, "phäochromozytom": 3,
        "hypophyse": 2, "akromegalie": 3,
        # Infektiologie
        "sepsis": 3, "fieber": 1, "antibiotika": 1, "infektion": 1,
        "bakteriämie": 3, "multiresistent": 2, "mrsa": 2,
    },

    "Chirurgie": {
        "appendizitis": 3, "appendektomie": 3, "cholezystektomie": 3,
        "hernie": 3, "ileus": 3, "peritonitis": 3, "laparotomie": 3,
        "op-indikation": 2, "operation": 1, "chirurgisch": 2,
        "resektion": 2, "anastomose": 3, "drainage": 2,
        "wundheilung": 2, "naht": 2, "inzision": 2,
        "kolektomie": 3, "gastrektomie": 3, "laparoskopie": 2,
        "akutes abdomen": 3, "divertikulitis": 3, "sigma": 2,
        "stoma": 2, "adhäsion": 2, "bridenileus": 3,
    },

    "Unfallchirurgie/Orthopädie": {
        "fraktur": 3, "luxation": 3, "trauma": 2, "unfall": 2,
        "osteosynthese": 3, "reposition": 3, "gips": 2,
        "clavicula": 3, "humerus": 3, "radius": 2, "femur": 3,
        "tibia": 2, "sprunggelenk": 3, "schulter": 2, "knie": 2,
        "wirbelsäule": 2, "bandscheibe": 3, "arthrose": 3,
        "osteoporose": 3, "skoliose": 3, "prothese": 2,
        "röntgen": 1, "ct": 1, "bildgebung": 1,
        "weber": 2, "ao-klassifikation": 3, "garden": 3,
        "schenkelhalsfraktur": 3, "distale radiusfraktur": 3,
        "polytrauma": 2, "becken": 2, "beckenfraktur": 3,
        "kreuzband": 3, "meniskus": 3, "rotatorenmanschette": 3,
    },

    "Neurologie": {
        "schlaganfall": 3, "apoplex": 3, "tia": 3, "ischämie": 2,
        "epilepsie": 3, "krampfanfall": 3, "parkinson": 3,
        "demenz": 3, "alzheimer": 3, "multiple sklerose": 3,
        "kopfschmerz": 2, "migräne": 3, "meningitis": 3,
        "hirndruck": 3, "hirnblutung": 3, "liquor": 2,
        "lähmung": 2, "parese": 2, "sensibilitätsstörung": 2,
        "bewusstlosigkeit": 2, "koma": 2, "gcs": 2,
        "hirnnerven": 2, "polyneuropathie": 3, "myasthenie": 3,
        "guillain-barré": 3, "radikulopathie": 3,
        "nihss": 3, "lyse": 2, "thrombektomie": 2,
    },

    "Notfallmedizin": {
        "reanimation": 3, "cpr": 3, "herzstillstand": 3,
        "schock": 3, "polytrauma": 3, "bewusstlos": 2,
        "anaphylaxie": 3, "intoxikation": 3, "vergiftung": 3,
        "atemstillstand": 3, "notarzt": 2, "rettungsdienst": 2,
        "abcde": 3, "triage": 2, "monitoring": 1,
        "defibrillation": 3, "adrenalin": 2, "beatmung": 2,
        "notfall": 2, "akut": 1, "lebensbedrohlich": 2,
        "kreislaufstillstand": 3, "kammerflimmern": 3,
    },

    "Pädiatrie": {
        "kind": 2, "säugling": 3, "neugeborenes": 3, "neonatologie": 3,
        "pädiatrisch": 3, "kinderarzt": 2, "impfung": 2,
        "fieberkrampf": 3, "wachstum": 2, "entwicklung": 1,
        "stillen": 2, "u-untersuchung": 3,
        "kinderkrankheit": 3, "exanthem": 2, "kawasaki": 3,
        "apgar": 3, "frühgeburt": 3, "reifgeborenes": 2,
    },

    "Gynäkologie/Geburtshilfe": {
        "schwanger": 3, "geburt": 3, "sectio": 3, "kaiserschnitt": 3,
        "präeklampsie": 3, "eklampsie": 3, "gestose": 3,
        "mastitis": 3, "zervix": 2, "uterus": 2, "ovar": 2,
        "menstruation": 2, "kontrazeption": 2, "wehen": 3,
        "ctg": 3, "ultraschall": 1, "fruchtwasser": 3,
        "plazenta": 3, "extrauteringravidität": 3, "abort": 3,
        "myom": 3, "endometriose": 3, "mammakarzinom": 2,
    },

    "Psychiatrie": {
        "depression": 3, "schizophrenie": 3, "psychose": 3,
        "suizid": 3, "suizidalität": 3, "bipolar": 3,
        "angststörung": 3, "panikattacke": 3, "zwang": 2,
        "persönlichkeitsstörung": 3, "demenz": 2, "delir": 2,
        "psychiatrisch": 2, "psychopharmaka": 2,
        "antidepressiva": 3, "neuroleptika": 3, "lithium": 3,
        "manie": 3, "halluzination": 3, "wahn": 3,
        "unterbringung": 2, "psychbkg": 3, "einweisung": 2,
    },

    "Rechtsmedizin": {
        "leichenschau": 3, "totenschein": 3, "obduktion": 3,
        "rechtsmedizin": 3, "forensisch": 3, "todesart": 3,
        "todesursache": 3, "todesbescheinigung": 3,
        "gewalt": 2, "misshandlung": 2, "verletzungsmuster": 3,
        "blutalkohol": 2, "toxikologie": 2,
        "natürlicher tod": 3, "nicht natürlicher tod": 3,
        "ungeklärter tod": 3, "totenfleck": 3, "totenstarre": 3,
        "leichenerscheinung": 3, "aufklärungspflicht": 2,
    },

    "Dermatologie": {
        "hautveränderung": 3, "exanthem": 3, "ekzem": 3,
        "psoriasis": 3, "dermatitis": 3, "urtikaria": 3,
        "melanom": 3, "basaliom": 3, "akne": 2,
        "neurodermitis": 3, "erysipel": 3, "zoster": 3,
        "mykose": 2, "candidose": 2, "allergie": 1,
    },

    "HNO": {
        "hno": 3, "otitis": 3, "sinusitis": 3, "tonsillitis": 3,
        "schwerhörigkeit": 3, "schwindel": 2, "vertigo": 3,
        "epistaxis": 3, "hörsturz": 3, "larynx": 2,
        "pharyngitis": 3, "adenoide": 3, "cholesteatom": 3,
        "trommelfell": 3, "mittelohr": 3, "innenohr": 3,
    },

    "Urologie": {
        "harnverhalt": 3, "prostata": 3, "hoden": 3,
        "nierenstein": 3, "urolithiasis": 3, "harnleiter": 2,
        "blase": 2, "inkontinenz": 2, "katheter": 2,
        "prostatakarzinom": 3, "psa": 2, "hodentorsion": 3,
        "zystitis": 3, "hämaturie": 3, "hydronephrose": 3,
    },

    "Augenheilkunde": {
        "auge": 2, "sehstörung": 3, "glaukom": 3, "katarakt": 3,
        "retina": 3, "netzhaut": 3, "konjunktivitis": 3,
        "visus": 2, "fundoskopie": 3,
        "makuladegeneration": 3, "diabetische retinopathie": 3,
        "uveitis": 3, "iritis": 3, "keratitis": 3,
    },

    "Anästhesie": {
        "narkose": 3, "anästhesie": 3, "intubation": 3,
        "sedierung": 3, "analgesie": 2, "regionalanästhesie": 3,
        "spinalanästhesie": 3, "periduralanästhesie": 3,
        "propofol": 3, "fentanyl": 2, "relaxierung": 3,
        "prämedikation": 3, "postoperativ": 2,
        "maligne hyperthermie": 3, "asa-klassifikation": 3,
    },

    "Radiologie": {
        "radiologie": 3, "kontrastmittel": 3, "strahlung": 2,
        "mrt": 2, "ct-befund": 3, "röntgenaufnahme": 2,
        "strahlenschutz": 3, "dosimetrie": 3,
        "angiographie": 3, "interventionell": 2,
    },
}


# Mapping von Quelldateinamen zu Kategorien
SOURCE_FILE_MAPPINGS: Dict[str, str] = {
    "rechtsmedizin": "Rechtsmedizin",
    "innere": "Innere Medizin",
    "chirurgie": "Chirurgie",
    "neurologie": "Neurologie",
    "notfall": "Notfallmedizin",
    "pädiatrie": "Pädiatrie",
    "paediatrie": "Pädiatrie",
    "gynäkologie": "Gynäkologie/Geburtshilfe",
    "gynaekologie": "Gynäkologie/Geburtshilfe",
    "geburtshilfe": "Gynäkologie/Geburtshilfe",
    "psychiatrie": "Psychiatrie",
    "orthopädie": "Unfallchirurgie/Orthopädie",
    "orthopadie": "Unfallchirurgie/Orthopädie",
    "unfallchirurgie": "Unfallchirurgie/Orthopädie",
    "traumatologie": "Unfallchirurgie/Orthopädie",
    "dermatologie": "Dermatologie",
    "haut": "Dermatologie",
    "urologie": "Urologie",
    "kardiologie": "Innere Medizin",
    "pneumologie": "Innere Medizin",
    "gastroenterologie": "Innere Medizin",
    "nephrologie": "Innere Medizin",
    "endokrinologie": "Innere Medizin",
    "hämatologie": "Innere Medizin",
    "onkologie": "Innere Medizin",
    "rheumatologie": "Innere Medizin",
    "hno": "HNO",
    "augenheilkunde": "Augenheilkunde",
    "ophthalmologie": "Augenheilkunde",
    "anästhesie": "Anästhesie",
    "anaesthesie": "Anästhesie",
    "radiologie": "Radiologie",
    "pathologie": "Allgemeinmedizin",  # Keine eigene Kategorie für KP
    "mikrobiologie": "Innere Medizin",
    "pharmakologie": "Allgemeinmedizin",
    "allgemeinmedizin": "Allgemeinmedizin",
}


def detect_category_from_source(source_file: str) -> Optional[str]:
    """
    Erkennt Kategorie aus dem Quelldateinamen.

    Args:
        source_file: Pfad oder Name der Quelldatei

    Returns:
        Erkannte Kategorie oder None
    """
    if not source_file:
        return None

    source_lower = source_file.lower()

    for key, kategorie in SOURCE_FILE_MAPPINGS.items():
        if key in source_lower:
            return kategorie

    return None


# Negative Keywords: Schließen eine Kategorie aus, wenn gefunden
NEGATIVE_KEYWORDS: Dict[str, List[str]] = {
    "Notfallmedizin": ["chronisch", "langzeit", "ambulant", "prophylaxe"],
    "Pädiatrie": ["erwachsen", "geriatrisch", "65-jährig", "70-jährig", "80-jährig"],
    "Rechtsmedizin": ["lebend", "therapie", "behandlung"],
}


# Exklusive Phrasen: Wenn gefunden, direkte Zuordnung (höchste Priorität)
EXCLUSIVE_PHRASES: Dict[str, str] = {
    # Rechtsmedizin - sehr spezifisch
    "totenschein ausstellen": "Rechtsmedizin",
    "leichenschau durchführen": "Rechtsmedizin",
    "todesbescheinigung": "Rechtsmedizin",
    "sichere todeszeichen": "Rechtsmedizin",
    "unsichere todeszeichen": "Rechtsmedizin",
    "todesart feststellen": "Rechtsmedizin",
    "natürlicher tod": "Rechtsmedizin",
    "nicht natürlicher tod": "Rechtsmedizin",

    # Notfallmedizin
    "cpr durchführen": "Notfallmedizin",
    "reanimation einleiten": "Notfallmedizin",
    "abcde-schema": "Notfallmedizin",
    "advanced life support": "Notfallmedizin",
    "basic life support": "Notfallmedizin",

    # Gynäkologie
    "spontangeburt": "Gynäkologie/Geburtshilfe",
    "vaginale entbindung": "Gynäkologie/Geburtshilfe",
    "kaiserschnitt indikation": "Gynäkologie/Geburtshilfe",
    "schwangerschaftsvorsorge": "Gynäkologie/Geburtshilfe",

    # Psychiatrie
    "suizidalität abklären": "Psychiatrie",
    "psychotische symptome": "Psychiatrie",
    "zwangseinweisung": "Psychiatrie",
    "unterbringung nach psychkg": "Psychiatrie",

    # Orthopädie/Unfallchirurgie
    "ao-klassifikation": "Unfallchirurgie/Orthopädie",
    "weber-klassifikation": "Unfallchirurgie/Orthopädie",
    "garden-klassifikation": "Unfallchirurgie/Orthopädie",
    "pauwels-klassifikation": "Unfallchirurgie/Orthopädie",
    "osteosynthese indikation": "Unfallchirurgie/Orthopädie",
}


# ICD-10 Präfixe für Kategorien
ICD_PREFIXES: Dict[str, str] = {
    "I": "Innere Medizin",  # Kreislaufsystem
    "J": "Innere Medizin",  # Atmungssystem
    "K": "Innere Medizin",  # Verdauungssystem (auch Chirurgie möglich)
    "N": "Urologie",  # Urogenitalsystem
    "O": "Gynäkologie/Geburtshilfe",  # Schwangerschaft
    "P": "Pädiatrie",  # Perinatalperiode
    "F": "Psychiatrie",  # Psychische Störungen
    "G": "Neurologie",  # Nervensystem
    "S": "Unfallchirurgie/Orthopädie",  # Verletzungen
    "T": "Notfallmedizin",  # Vergiftungen, Verletzungen
    "L": "Dermatologie",  # Haut
    "H": "Augenheilkunde",  # Auge und Ohr (H00-H59 Auge)
    "M": "Unfallchirurgie/Orthopädie",  # Muskel-Skelett
    "C": "Innere Medizin",  # Neubildungen (Onkologie)
    "D": "Innere Medizin",  # Blut/Immunsystem
    "E": "Innere Medizin",  # Endokrine/Stoffwechsel
    "A": "Innere Medizin",  # Infektionskrankheiten
    "B": "Innere Medizin",  # Infektionskrankheiten
}


def detect_icd_codes(text: str) -> List[Tuple[str, str]]:
    """
    Erkennt ICD-10 Codes im Text und gibt Kategorie-Hinweise.

    Returns:
        Liste von (ICD-Code, vermutete Kategorie)
    """
    # ICD-10 Pattern: Buchstabe + 2 Ziffern (+ optional . + weitere Ziffern)
    icd_pattern = r'\b([A-TV-Z]\d{2}(?:\.\d{1,2})?)\b'
    matches = re.findall(icd_pattern, text.upper())

    results = []
    for code in matches:
        prefix = code[0]
        category = ICD_PREFIXES.get(prefix, "Allgemeinmedizin")
        results.append((code, category))

    return results


def detect_drug_patterns(text: str) -> Optional[str]:
    """
    Erkennt Medikamentenmuster und gibt Kategorie-Hinweise.
    """
    text_lower = text.lower()

    # Kardiovaskuläre Medikamente
    cardio_drugs = ["betablocker", "ace-hemmer", "at1-blocker", "diuretikum",
                    "amiodaron", "digitalis", "nitrat", "antikoagul"]
    if any(d in text_lower for d in cardio_drugs):
        return "Innere Medizin"

    # Psychiatrische Medikamente
    psych_drugs = ["antidepressiv", "neuroleptik", "ssri", "lithium",
                   "benzodiazepin", "antipsychoti"]
    if any(d in text_lower for d in psych_drugs):
        return "Psychiatrie"

    # Notfallmedikamente
    emergency_drugs = ["adrenalin", "noradrenalin", "atropin", "naloxon",
                       "amiodaron bei reanimation"]
    if any(d in text_lower for d in emergency_drugs):
        return "Notfallmedizin"

    # Anästhetika
    anaesthesia_drugs = ["propofol", "sevofluran", "desfluran", "isofluran",
                         "rocuronium", "succinylcholin", "remifentanil"]
    if any(d in text_lower for d in anaesthesia_drugs):
        return "Anästhesie"

    return None


def detect_clinical_context(text: str) -> Dict[str, float]:
    """
    Erkennt klinischen Kontext für bessere Kategorisierung.

    Returns:
        Dict mit Kontext-Hinweisen und Gewichtungen
    """
    text_lower = text.lower()
    context = {}

    # Notfall-Kontext
    emergency_context = [
        "sofort", "notfall", "akut", "lebensbedrohlich", "bewusstlos",
        "rettungsdienst", "schockraum", "intensivstation"
    ]
    if sum(1 for kw in emergency_context if kw in text_lower) >= 2:
        context["Notfallmedizin"] = 3.0

    # Operativer Kontext
    surgical_context = [
        "op-indikation", "operativ", "laparoskop", "minimalinvasiv",
        "postoperativ", "präoperativ", "narkose"
    ]
    if sum(1 for kw in surgical_context if kw in text_lower) >= 2:
        context["Chirurgie"] = 2.0

    # Ambulanter vs. stationärer Kontext
    if "ambulant" in text_lower and "hausarzt" in text_lower:
        context["Allgemeinmedizin"] = 2.0

    # Pädiatrischer Kontext (Altersangaben)
    paed_patterns = [
        r'\b(\d{1,2})\s*(monate?|monat)\s*alt',
        r'\b(\d{1,2})\s*(jahre?|jährig)',
        r'säugling', r'kleinkind', r'schulkind', r'jugendlich'
    ]
    for pattern in paed_patterns:
        match = re.search(pattern, text_lower)
        if match:
            if "monate" in text_lower or "säugling" in text_lower:
                context["Pädiatrie"] = 4.0
            elif match.groups():
                try:
                    age = int(match.group(1))
                    if age < 18:
                        context["Pädiatrie"] = 3.0
                except (ValueError, IndexError):
                    pass

    # Geriatrischer Kontext
    if any(kw in text_lower for kw in ["geriatrisch", "pflegeheim", "multimorbid"]):
        context["Innere Medizin"] = 1.5

    return context


def heuristic_category_analysis(text: str) -> Tuple[str, str, float, Dict[str, float], Dict[str, List[str]]]:
    """
    Präzise heuristische Analyse zur Kategorie-Erkennung.

    Verwendet:
    1. Exklusive Phrasen (höchste Priorität)
    2. ICD-Code Erkennung
    3. Medikamenten-Pattern
    4. Klinischer Kontext
    5. Gewichtetes Keyword-Scoring
    6. Negative Keywords zur Ausschlussprüfung

    Args:
        text: Zu analysierender Text (Frage + Antwort)

    Returns:
        (topic, category, confidence, all_scores, matched_keywords)
    """
    text_lower = text.lower()

    # SCHRITT 1: Exklusive Phrasen prüfen (höchste Priorität)
    for phrase, kategorie in EXCLUSIVE_PHRASES.items():
        if phrase in text_lower:
            return phrase, kategorie, 1.0, {kategorie: 10.0}, {kategorie: [phrase]}

    # SCHRITT 2: Berechne Basis-Score für jede Kategorie
    scores: Dict[str, float] = {}
    matched_keywords: Dict[str, List[str]] = {}

    for kategorie, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        found_keywords = []
        for keyword, weight in keywords.items():
            if keyword in text_lower:
                # Prüfe auf exakte Wortgrenzen für kurze Keywords
                if len(keyword) <= 4:
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, text_lower):
                        score += weight
                        found_keywords.append(keyword)
                else:
                    score += weight
                    found_keywords.append(keyword)
        if score > 0:
            scores[kategorie] = score
            matched_keywords[kategorie] = found_keywords

    # SCHRITT 3: ICD-Code Bonus
    icd_matches = detect_icd_codes(text)
    for code, kategorie in icd_matches:
        scores[kategorie] = scores.get(kategorie, 0) + 2.0
        if kategorie not in matched_keywords:
            matched_keywords[kategorie] = []
        matched_keywords[kategorie].append(f"ICD:{code}")

    # SCHRITT 4: Medikamenten-Pattern Bonus
    drug_category = detect_drug_patterns(text)
    if drug_category:
        scores[drug_category] = scores.get(drug_category, 0) + 1.5

    # SCHRITT 5: Klinischer Kontext Bonus
    context_scores = detect_clinical_context(text)
    for kategorie, bonus in context_scores.items():
        scores[kategorie] = scores.get(kategorie, 0) + bonus

    # SCHRITT 6: Negative Keywords - reduziere Score
    for kategorie, neg_keywords in NEGATIVE_KEYWORDS.items():
        if kategorie in scores:
            for neg_kw in neg_keywords:
                if neg_kw in text_lower:
                    scores[kategorie] = scores[kategorie] * 0.5  # Halbiere Score
                    break

    if not scores:
        return "allgemein", "Allgemeinmedizin", 0.0, {}, {}

    # Wähle Kategorie mit höchstem Score
    best_kategorie = max(scores, key=scores.get)
    best_score = scores[best_kategorie]

    # Confidence: Verhältnis zum zweitbesten Score (verbesserte Formel)
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and sorted_scores[1] > 0:
        # Abstand zum Zweiten + Verhältnis
        diff = best_score - sorted_scores[1]
        ratio = diff / best_score if best_score > 0 else 0
        # Bonus für hohen absoluten Score
        absolute_bonus = min(best_score / 20.0, 0.3)
        confidence = min(ratio + absolute_bonus, 1.0)
    else:
        confidence = 1.0

    # Bestes Keyword als Thema (nach Gewicht sortiert)
    if best_kategorie in matched_keywords and matched_keywords[best_kategorie]:
        category_kw = CATEGORY_KEYWORDS.get(best_kategorie, {})
        sorted_kw = sorted(
            matched_keywords[best_kategorie],
            key=lambda k: category_kw.get(k, 0),
            reverse=True
        )
        thema = sorted_kw[0]
    else:
        thema = best_kategorie.lower()

    return thema, best_kategorie, confidence, scores, matched_keywords


def classify_medical_content(
    text: str,
    source_file: str = "",
    min_confidence: float = 0.0
) -> ClassificationResult:
    """
    Klassifiziert medizinischen Inhalt in eine Fachkategorie.

    Verwendet eine zweistufige Strategie:
    1. Quelldatei-Erkennung (wenn verfügbar und eindeutig)
    2. Heuristische Textanalyse mit gewichtetem Keyword-Scoring

    Args:
        text: Zu klassifizierender Text (Frage, Antwort oder beides)
        source_file: Optionaler Quelldateiname für zusätzlichen Kontext
        min_confidence: Minimale Confidence für Klassifikation (sonst Allgemeinmedizin)

    Returns:
        ClassificationResult mit Kategorie, Confidence und Details

    Example:
        >>> result = classify_medical_content("Patient mit STEMI und kardiogenem Schock")
        >>> print(result.category)
        'Innere Medizin'
        >>> print(result.confidence)
        0.75
    """
    # PRIORITÄT 1: Quelldatei prüfen
    source_kategorie = detect_category_from_source(source_file)
    if source_kategorie:
        # Extrahiere Thema aus Quelldatei
        source_base = Path(source_file).stem.lower()
        thema = re.sub(r'[\(\)\d\s]+', '', source_base).strip()
        if not thema:
            thema = source_kategorie.lower()

        # Trotzdem heuristische Analyse für matched_keywords
        _, _, _, all_scores, matched_keywords = heuristic_category_analysis(text)

        return ClassificationResult(
            category=source_kategorie,
            topic=thema,
            confidence=1.0,  # Quelldatei = hohe Confidence
            all_scores=all_scores,
            matched_keywords=matched_keywords,
            source_detected=True
        )

    # PRIORITÄT 2: Heuristische Analyse
    thema, kategorie, confidence, all_scores, matched_keywords = heuristic_category_analysis(text)

    # Confidence-Schwelle prüfen
    if confidence < min_confidence:
        kategorie = "Allgemeinmedizin"
        thema = "allgemein"

    return ClassificationResult(
        category=kategorie,
        topic=thema,
        confidence=confidence,
        all_scores=all_scores,
        matched_keywords=matched_keywords,
        source_detected=False
    )


def get_all_categories() -> List[str]:
    """Gibt alle verfügbaren Kategorien zurück."""
    return list(CATEGORY_KEYWORDS.keys()) + ["Allgemeinmedizin"]


def add_custom_keywords(category: str, keywords: Dict[str, int]) -> None:
    """
    Fügt benutzerdefinierte Keywords zu einer Kategorie hinzu.

    Args:
        category: Name der Kategorie
        keywords: Dict mit Keyword -> Gewicht
    """
    if category not in CATEGORY_KEYWORDS:
        CATEGORY_KEYWORDS[category] = {}
    CATEGORY_KEYWORDS[category].update(keywords)


# Convenience-Funktionen für häufige Anwendungsfälle
def is_emergency(text: str) -> bool:
    """Prüft ob der Text einen Notfall beschreibt."""
    result = classify_medical_content(text)
    return result.category == "Notfallmedizin" or any(
        kw in text.lower() for kw in [
            "reanimation", "herzstillstand", "bewusstlos",
            "anaphylaxie", "schock", "akut"
        ]
    )


def get_category_keywords(category: str) -> Dict[str, int]:
    """Gibt die Keywords für eine Kategorie zurück."""
    return CATEGORY_KEYWORDS.get(category, {})


if __name__ == "__main__":
    # Test
    test_cases = [
        ("Patient mit Herzinsuffizienz NYHA III und Vorhofflimmern", ""),
        ("Clavikulafraktur nach Fahrradsturz, Röntgen zeigt...", ""),
        ("Leichenschau durchführen, Totenschein ausstellen", ""),
        ("Was ist die Widerspruchslösung?", "Rechtsmedizin (1).pdf"),
        ("55-jähriger Patient mit akutem Thoraxschmerz", "Kenntnisprüfung.pdf"),
    ]

    print("=" * 70)
    print("TEST: Heuristische Kategorie-Klassifikation")
    print("=" * 70)

    for text, source in test_cases:
        result = classify_medical_content(text, source)
        print(f"\nText: {text[:50]}...")
        print(f"Quelle: {source or '(keine)'}")
        print(f"  → Kategorie: {result.category}")
        print(f"  → Thema: {result.topic}")
        print(f"  → Confidence: {result.confidence:.2f}")
        print(f"  → Aus Quelle: {result.source_detected}")
        if result.matched_keywords:
            top_cat = max(result.all_scores, key=result.all_scores.get) if result.all_scores else None
            if top_cat:
                print(f"  → Keywords ({top_cat}): {result.matched_keywords.get(top_cat, [])[:5]}")
