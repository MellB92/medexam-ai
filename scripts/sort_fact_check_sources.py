#!/usr/bin/env python3
"""
Sortiert Dateien in _FACT_CHECK_SOURCES nach Kategorie.

Umfassende Kategorisierung nach medizinischen Fachgebieten.
"""

import shutil
from pathlib import Path
from collections import Counter
import re

BASE_DIR = Path("_FACT_CHECK_SOURCES")
INPUT_DIR = BASE_DIR / "Input Bucket"

# Umfassende Kategorisierungsregeln nach Fachgebiet
CATEGORY_RULES = {
    # === LEITLINIEN ===
    "leitlinien": {
        "keywords": ["awmf", "leitlinie", "s1-", "s2-", "s3-", "nvl-", "guideline",
                    "empfehlung", "konsensus"],
        "extensions": [".pdf"],
    },

    # === PRUEFUNGSPROTOKOLLE ===
    "pruefungsprotokolle": {
        "keywords": ["kenntnisprüfung", "kenntnispruefung", "protokoll", "münster",
                    "muenster", "approbation", "kp-themen", "kp_", "kp 2",
                    "kp 1", "kp im", "fsp", "gleichwertigkeitsprüfung", "themen kp",
                    "fallkonzepte", "prüfungsvorbereitung", "pruefungsvorbereitung",
                    "staatsexamen", "hammerexamen", "m3", "m2 ", "m1 "],
        "extensions": [".pdf", ".docx", ".doc"],
    },

    # === KREUZMICH FRAGEN ===
    "kreuzmich": {
        "keywords": ["kreuzmich", "kreuz", "auswertung"],
        "extensions": [".pdf"],
        "path_match": "kreuzmich",
    },

    # === INNERE MEDIZIN (Unterkategorien) ===
    "fachgebiete/innere_medizin/kardiologie": {
        "keywords": ["kardio", "herz", "herzinsuffizienz", "myokard", "koronar",
                    "ekg", "arrhythm", "vorhof", "ventrikel", "klappen", "baldus",
                    "mitral", "aorten", "herzklappen", "acs", "stemi", "nstemi"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/gastroenterologie": {
        "keywords": ["gastro", "hepat", "leber", "pankrea", "darm", "magen",
                    "ced", "crohn", "colitis", "zirrhose", "hcc", "ösophag",
                    "oesophag", "ulkus", "gallenwege", "galle", "ogi-blutung"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/pneumologie": {
        "keywords": ["pneumo", "lunge", "copd", "asthma", "bronch", "respirat",
                    "pulmo", "thorax", "ards", "pneumonie", "tuberkulose"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/nephrologie": {
        "keywords": ["nephro", "niere", "dialyse", "glomerul", "aki", "ckd",
                    "hämaturie", "nephriti", "benzing", "proteinurie"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/endokrinologie": {
        "keywords": ["endokrin", "diabetes", "schilddrüse", "sd_", "thyroid",
                    "hypophyse", "nebenniere", "adipositas", "stoffwechsel",
                    "calcium", "knochenstoffwechsel", "pedp", "huttmann",
                    "hanssen", "faust", "bruening"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/haematologie_onkologie": {
        "keywords": ["onkolog", "hämat", "haemat", "leukäm", "leukaem", "lymphom",
                    "myelom", "krebs", "tumor", "cll", "aml", "hannek",
                    "thrombozyten", "mellinghoff", "borchmann", "zelltherapie"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/rheumatologie": {
        "keywords": ["rheuma", "arthritis", "autoimmun", "lupus", "vaskulitis",
                    "kollagenose", "sjögren", "skleroderm"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/innere_medizin/infektiologie": {
        "keywords": ["infekt", "sepsis", "antibio", "bakterie", "virus", "fieber",
                    "masern", "covid", "sars", "ebola", "rsv", "hiv", "aids",
                    "meningitis", "rybniker", "gruell", "rohde", "klein"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === CHIRURGIE ===
    "fachgebiete/chirurgie/allgemeinchirurgie": {
        "keywords": ["chirurg", "operation", "op-", "laparoskop", "viszeralchirurgie",
                    "appendek", "hernie", "cholezyst", "kolon", "rektum"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/chirurgie/unfallchirurgie": {
        "keywords": ["unfall", "trauma", "fraktur", "osteosynthese", "polytrauma",
                    "becken", "wirbelsäule", "extremität"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/chirurgie/orthopaedie": {
        "keywords": ["orthop", "gelenk", "hüfte", "knie", "schulter", "arthrose",
                    "endoprothes", "hws", "bws", "lws", "bandscheibe", "meniskus"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === NEUROLOGIE ===
    "fachgebiete/neurologie": {
        "keywords": ["neuro", "hirn", "zerebral", "epileps", "schlaganfall",
                    "parkinson", "demenz", "ms ", "multiple sklerose", "kopfschmerz",
                    "migräne", "polyneuropath", "stetefeld"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === PSYCHIATRIE ===
    "fachgebiete/psychiatrie": {
        "keywords": ["psychiatr", "depression", "schizophren", "bipolar", "angst",
                    "suizid", "psychos", "mani", "zwang"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === PAEDIATRIE ===
    "fachgebiete/paediatrie": {
        "keywords": ["pädiatr", "paediatr", "kinder", "säugling", "neonat",
                    "impf", "entwicklung", "kinderheilkunde"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === GYNAEKOLOGIE ===
    "fachgebiete/gynaekologie": {
        "keywords": ["gynäk", "gynaek", "geburt", "schwanger", "mamma", "ovar",
                    "uterus", "zervix", "endometri", "menstruat"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === UROLOGIE ===
    "fachgebiete/urologie": {
        "keywords": ["urolog", "prostata", "blase", "harnweg", "nierenstein",
                    "hoden", "penis", "inkontinenz"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === DERMATOLOGIE ===
    "fachgebiete/dermatologie": {
        "keywords": ["dermat", "haut", "ekzem", "psoriasis", "melanom", "akne",
                    "allergie", "urtikaria", "exanthem"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === HNO ===
    "fachgebiete/hno": {
        "keywords": ["hno", "ohr", "nase", "hals", "larynx", "pharynx", "tonsill",
                    "sinusitis", "otitis", "hörsturz", "schwindel", "tinnitus"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === AUGENHEILKUNDE ===
    "fachgebiete/augenheilkunde": {
        "keywords": ["augen", "ophthalm", "retina", "glaukom", "katarakt", "makula",
                    "konjunktiv", "kornea", "visus"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === ANAESTHESIE ===
    "fachgebiete/anaesthesie": {
        "keywords": ["anästhes", "anaesthes", "narkose", "intubat", "beatmung",
                    "sedierung", "schmerztherap", "intensiv"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === NOTFALLMEDIZIN ===
    "fachgebiete/notfallmedizin": {
        "keywords": ["notfall", "reanimation", "schock", "emergency", "cpr",
                    "rettung", "akut", "notfälle", "notfaelle"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === RADIOLOGIE ===
    "fachgebiete/radiologie": {
        "keywords": ["radiolog", "röntgen", "ct-", "ct_", "ctscan", "ct scan",
                    "computertomogra", "mrt-", "mrt_", "mrtscan", "mrt scan",
                    "magnetresonanz", "sonograph", "ultraschall",
                    "bildgebung", "kontrastmittel", "röntgenbild", "roentgen"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === PATHOLOGIE ===
    "fachgebiete/pathologie": {
        "keywords": ["patholog", "histolog", "zytolog", "biopsie", "autopsi",
                    "malign", "benign", "differenzierung"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === MIKROBIOLOGIE ===
    "fachgebiete/mikrobiologie": {
        "keywords": ["mikrobiolog", "bakteriolog", "virolog", "mykolog", "parasit",
                    "resistenz", "antibiogramm", "kultur"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === PHARMAKOLOGIE ===
    "fachgebiete/pharmakologie": {
        "keywords": ["pharmakolog", "arzneimittel", "medikament", "wirkstoff",
                    "nebenwirkung", "interaktion", "dosierung", "pharmakokinetik"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === RECHTSMEDIZIN ===
    "fachgebiete/rechtsmedizin": {
        "keywords": ["rechtsmedizin", "forensi", "leichenschau", "todesursache",
                    "vergiftung", "toxikolog", "gutachten"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === ALLGEMEINMEDIZIN ===
    "fachgebiete/allgemeinmedizin": {
        "keywords": ["allgemeinmedizin", "hausarzt", "praxis", "vorsorge",
                    "prävention", "impfung", "check-up"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === LABORMEDIZIN ===
    "fachgebiete/labormedizin": {
        "keywords": ["labor", "klinische_chemie", "blutwert", "referenzbereich",
                    "blutbild", "gerinnung", "elektrolyt"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === BIOCHEMIE / PHYSIOLOGIE (Vorklinik) ===
    "vorklinik/biochemie": {
        "keywords": ["biochem", "stoffwechsel", "enzym", "metabol"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "vorklinik/physiologie": {
        "keywords": ["physiolog", "kreislauf", "atmung", "verdauung"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === GENETIK / IMMUNOLOGIE ===
    "fachgebiete/genetik": {
        "keywords": ["genetik", "genom", "mutation", "erbkrank", "chromosom",
                    "humangenetik", "molekulargenetik"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },
    "fachgebiete/immunologie": {
        "keywords": ["immunolog", "antikörper", "immun", "allergi", "ige"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === GERIATRIE ===
    "fachgebiete/geriatrie": {
        "keywords": ["geriatr", "alter", "demenz", "sturz", "multimorbid",
                    "pflege", "frailty"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === PSYCHOSOMATIK ===
    "fachgebiete/psychosomatik": {
        "keywords": ["psychosomat", "somatoform", "funktionell", "schmerzstörung"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === ARBEITSMEDIZIN / SOZIALMEDIZIN ===
    "fachgebiete/arbeits_sozialmedizin": {
        "keywords": ["arbeitsmedizin", "sozialmedizin", "berufskrank", "gutachten",
                    "arbeitsunfähig", "rente"],
        "extensions": [".pdf", ".pptx", ".pages"],
    },

    # === NICHT MEDIZINISCH (ignorieren) ===
    "_skip_non_medical": {
        "keywords": ["sonos", "bedrock", "iam", "aws", "macbook", "iphone", "spotify",
                    "netflix", "youtube", "whatsapp", "telegram", "discord", "slack",
                    "github", "gitlab", "docker", "kubernetes", "jenkins", "terraform",
                    "audioausgabe", "bluetooth", "wifi", "wlan", "vpn", "ssh"],
        "extensions": [".pdf", ".docx", ".doc", ".txt", ".md"],
        "skip": True,  # Diese Dateien werden komplett ignoriert
    },

    # === DOKUMENT-TYPEN ===
    "notizen": {
        "keywords": [],
        "extensions": [".md", ".txt"],
    },
    "bilder": {
        "keywords": [],
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".webp"],
    },
    "dokumente": {
        "keywords": [],
        "extensions": [".doc", ".docx", ".odt", ".xlsx", ".xls", ".pages", ".numbers"],
    },
    "praesentationen": {
        "keywords": [],
        "extensions": [".pptx", ".ppt", ".key"],
    },
}


def categorize_file(filepath: Path) -> str:
    """Bestimmt die Kategorie einer Datei basierend auf Name, Extension und Pfad."""
    name_lower = filepath.name.lower()
    suffix_lower = filepath.suffix.lower()
    path_lower = str(filepath).lower()

    # Parent-Ordner Namen (für Ordner-basierte Kategorisierung)
    parent_names = [p.name.lower() for p in filepath.parents]

    # Ignoriere versteckte Dateien und System-Dateien
    if filepath.name.startswith(".") or filepath.name == "desktop.ini":
        return "_skip"

    # Ignoriere __pycache__ und ähnliche
    if "__pycache__" in path_lower or ".ds_store" in name_lower:
        return "_skip"

    # Prüfe spezifische Kategorien mit Keywords
    for category, rules in CATEGORY_RULES.items():
        keywords = rules.get("keywords", [])
        extensions = rules.get("extensions", [])
        path_match = rules.get("path_match", None)
        should_skip = rules.get("skip", False)

        # Pfad-Match (z.B. für Kreuzmich-Ordner) - nur in Parent-Ordnern suchen
        if path_match:
            if any(path_match in parent for parent in parent_names):
                if not extensions or suffix_lower in extensions:
                    return "_skip" if should_skip else category

        # Nur wenn Extension passt oder keine Extensions definiert
        if extensions and suffix_lower not in extensions:
            continue

        # Wenn Keywords definiert, müssen sie im DATEINAMEN matchen
        # (nicht im Pfad, um false positives wie "ct" in "FACT_CHECK" zu vermeiden)
        if keywords:
            if any(kw in name_lower for kw in keywords):
                return "_skip" if should_skip else category
        # Wenn keine Keywords, nur Extension-basiert
        elif not keywords and extensions and suffix_lower in extensions:
            return "_skip" if should_skip else category

    return "_unsortiert"


def get_file_hash(filepath: Path) -> str:
    """Berechnet MD5-Hash einer Datei."""
    import hashlib
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def sort_files(dry_run: bool = False):
    """Sortiert alle Dateien in die richtigen Ordner."""

    # Suche nach allen Input-Quellen (nicht nur Input Bucket)
    input_sources = [INPUT_DIR]

    # Füge weitere Quell-Ordner hinzu
    additional_sources = [
        BASE_DIR / "Kreuzmich Fragen und Auswertungen",
        BASE_DIR / "Innere Medizin I 2",
        BASE_DIR / "Innere Medizin II 2",
        BASE_DIR / "Innere Medizin II",
        BASE_DIR / "KF Fieber und Sepsis",
    ]

    for src in additional_sources:
        if src.exists():
            input_sources.append(src)

    # Erstelle Zielordner
    target_categories = set(CATEGORY_RULES.keys()) | {"_unsortiert"}
    for category in target_categories:
        target = BASE_DIR / category
        target.mkdir(parents=True, exist_ok=True)

    # Sammle existierende Dateien (Name -> Hash)
    existing_files = {}
    exclude_dirs = set(str(s) for s in input_sources)

    for target_dir in BASE_DIR.rglob("*"):
        if target_dir.is_file():
            # Skip wenn in einer Input-Quelle
            skip = False
            for exc in exclude_dirs:
                if str(target_dir).startswith(exc):
                    skip = True
                    break
            if not skip:
                file_hash = get_file_hash(target_dir)
                if file_hash:
                    existing_files[target_dir.name] = file_hash

    # Sammle Statistiken
    stats = Counter()
    moved_files = []
    skipped_duplicates = 0

    # Durchsuche alle Input-Quellen
    for input_source in input_sources:
        if not input_source.exists():
            continue

        for filepath in input_source.rglob("*"):
            if not filepath.is_file():
                continue

            category = categorize_file(filepath)

            if category == "_skip":
                continue

            # Pruefe auf Duplikate
            if filepath.name in existing_files:
                src_hash = get_file_hash(filepath)
                if src_hash and src_hash == existing_files[filepath.name]:
                    skipped_duplicates += 1
                    continue

            stats[category] += 1

            target_dir = BASE_DIR / category
            target_path = target_dir / filepath.name

            # Verhindere Ueberschreiben
            if target_path.exists():
                stem = filepath.stem
                suffix = filepath.suffix
                counter = 1
                while target_path.exists():
                    target_path = target_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

            moved_files.append((filepath, target_path, category))

    # Zeige Zusammenfassung
    print("=" * 70)
    print("SORTIERUNG ZUSAMMENFASSUNG")
    print("=" * 70)
    print()

    for category, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {category}: {count} Dateien")

    print()
    print(f"Gesamt: {sum(stats.values())} Dateien zu verschieben")
    print(f"Duplikate übersprungen: {skipped_duplicates}")
    print()

    if dry_run:
        print("[DRY RUN] Keine Dateien wurden verschoben.")
        print()
        print("Beispiele (erste 20):")
        for src, dst, cat in moved_files[:20]:
            print(f"  {src.name} -> {cat}/")
        return

    # Verschiebe Dateien
    print("Kopiere Dateien...")
    success = 0
    errors = 0
    for src, dst, cat in moved_files:
        try:
            shutil.copy2(src, dst)
            success += 1
        except Exception as e:
            print(f"  Fehler bei {src.name}: {e}")
            errors += 1

    print()
    print(f"Erfolgreich: {success}")
    if errors:
        print(f"Fehler: {errors}")
    print("Fertig!")


if __name__ == "__main__":
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("[DRY RUN MODE]")
        print()

    sort_files(dry_run=dry_run)
