#!/usr/bin/env python3
"""
Fachgebiet-Klassifikation und Medizinische Validierung

Nutzt OpenAI API direkt für:
1. Klassifikation nach 8 Fachgebieten
2. Dual-Source-Verifikation der Antworten
3. Inventar-Generierung nach Fachgebiet

Verwendung:
    PYTHONPATH=. .venv/bin/python3 scripts/classify_and_validate.py --classify
    PYTHONPATH=. .venv/bin/python3 scripts/classify_and_validate.py --validate --batch-size 20
    PYTHONPATH=. .venv/bin/python3 scripts/classify_and_validate.py --inventory
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional
from openai import OpenAI

# === KONFIGURATION ===
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "_OUTPUT"
INVENTORY_DIR = OUTPUT_DIR / "inventar_fachgebiet"

# 8 Kompakte Fachgebiete
FACHGEBIETE = [
    "Innere Medizin",
    "Chirurgie",
    "Neurologie",
    "Gynäkologie",
    "Pädiatrie",
    "Psychiatrie",
    "Notfallmedizin",
    "Sonstige"  # Rechtsmedizin, Pharmakologie, Radiologie, etc.
]

# OpenAI Client
client = OpenAI()  # Nutzt OPENAI_API_KEY aus Umgebung

# === KLASSIFIKATIONS-PROMPT ===
CLASSIFICATION_SYSTEM_PROMPT = """Du bist ein medizinischer Fachgebiet-Klassifikator für die deutsche Kenntnisprüfung.

AUFGABE: Ordne jede Frage EINEM der 8 Fachgebiete zu.

FACHGEBIETE:
1. Innere Medizin - Kardiologie, Pneumologie, Gastroenterologie, Endokrinologie, Nephrologie, Hämatologie, Infektiologie, Rheumatologie
2. Chirurgie - Allgemeinchirurgie, Unfallchirurgie, Viszeralchirurgie, Orthopädie, Urologie
3. Neurologie - Schlaganfall, Epilepsie, MS, Parkinson, Kopfschmerzen, Polyneuropathie
4. Gynäkologie - Schwangerschaft, Geburt, Gynäkologische Erkrankungen, Mammakarzinom
5. Pädiatrie - Kinderkrankheiten, Impfungen, Entwicklung, Neonatologie
6. Psychiatrie - Depression, Schizophrenie, Angststörungen, Sucht, Suizidalität
7. Notfallmedizin - ABCDE, Reanimation, Schock, Polytrauma, Intensivmedizin, Anästhesie
8. Sonstige - Rechtsmedizin, Pharmakologie, Radiologie, Dermatologie, Ophthalmologie, HNO, Ethik, Recht

AUSGABE-FORMAT (NUR JSON, keine Erklärung):
{"fachgebiet": "Innere Medizin", "subkategorie": "Kardiologie", "konfidenz": 95}
"""

CLASSIFICATION_USER_TEMPLATE = """Klassifiziere diese Frage:

FRAGE: {frage}
KONTEXT: {context}
LEITLINIE: {leitlinie}
"""

# === VALIDIERUNGS-PROMPT (angepasst) ===
VALIDATION_SYSTEM_PROMPT = """Du bist ein spezialisierter medizinischer Prüfungs-Validator für die deutsche Kenntnisprüfung.

AUFGABE:
- Validiere die KI-generierte Antwort
- Dual-Source-Verifikation (interne Wissensbasis + externe deutsche Quellen)
- Konfidenz-Optimierung mit Quellenangabe

SPRACHE: Alle Ausgaben auf Deutsch
QUELLEN: Nur deutsche/europäische medizinische Quellen

FRAGETYP-FORMATE:
- KLINISCH: Definition → Ätiologie → Diagnostik → Therapie (mit Dosierung!) → §630 BGB
- RECHTLICH: Rechtsgrundlage → Definition → Anwendung → Konsequenzen
- ETHISCH: Prinzip → Definition → Rechtlicher Rahmen → Anwendung
- FAKTISCH: Direktantwort (1-3 Sätze) + Quelle

AUSGABE-FORMAT:
```json
{
  "validiert": true/false,
  "fragetyp": "Klinisch/Rechtlich/Ethisch/Faktisch",
  "fachgebiet": "...",
  "original_konfidenz": 70,
  "neue_konfidenz": 90,
  "korrekturen": ["...", "..."],
  "verifizierte_antwort": "...",
  "kernpunkte": ["...", "..."],
  "quellen": [{"typ": "Leitlinie", "name": "AWMF XXX-XXX", "url": "awmf.org"}]
}
```

Wichtige Quellen:
- AWMF (awmf.org) - Leitlinien
- RKI (rki.de) - Infektionen, Impfungen
- Fachinfo.de - Dosierungen
- BÄK - Berufsrecht
"""

VALIDATION_USER_TEMPLATE = """Validiere diese Frage-Antwort:

FRAGE: {frage}
KONTEXT: {context}
ORIGINAL-ANTWORT: {antwort}
LEITLINIE: {leitlinie}
EVIDENZGRAD: {evidenzgrad}

Prüfe auf: Faktische Richtigkeit, Vollständigkeit, Quellenbeleg.
"""


def load_questions() -> list[dict]:
    """Lädt die Fragen aus evidenz_antworten.json"""
    path = OUTPUT_DIR / "evidenz_antworten.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sanitize_text(text: str) -> str:
    """Entfernt problematische Unicode-Zeichen."""
    if not text:
        return ""
    # Ersetze problematische Zeichen
    replacements = {
        '\u2028': ' ',  # Line separator
        '\u2029': ' ',  # Paragraph separator
        '\u00a0': ' ',  # Non-breaking space
        '\ufeff': '',   # BOM
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Nur ASCII-kompatible Zeichen behalten (plus deutsche Umlaute)
    return text.encode('utf-8', errors='ignore').decode('utf-8')


def classify_question(item: dict, model: str = "gpt-4o-mini") -> dict:
    """Klassifiziert eine einzelne Frage nach Fachgebiet."""
    prompt = CLASSIFICATION_USER_TEMPLATE.format(
        frage=sanitize_text(item.get("frage", ""))[:500],
        context=sanitize_text(item.get("context", ""))[:300],
        leitlinie=sanitize_text(item.get("leitlinie", ""))[:100]
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {
            "fachgebiet": result.get("fachgebiet", "Sonstige"),
            "subkategorie": result.get("subkategorie", ""),
            "konfidenz": result.get("konfidenz", 50)
        }
    except Exception as e:
        print(f"  ⚠️ Klassifikation fehlgeschlagen: {e}")
        return {"fachgebiet": "Sonstige", "subkategorie": "", "konfidenz": 0}


def validate_answer(item: dict, model: str = "gpt-4o") -> dict:
    """Validiert eine Antwort mit dem Validierungs-Prompt."""
    prompt = VALIDATION_USER_TEMPLATE.format(
        frage=item.get("frage", "")[:1000],
        context=item.get("context", "")[:500],
        antwort=item.get("antwort", "")[:2000],
        leitlinie=item.get("leitlinie", ""),
        evidenzgrad=item.get("evidenzgrad", "")
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"  ⚠️ Validierung fehlgeschlagen: {e}")
        return {"validiert": False, "fehler": str(e)}


def run_classification(
    model: str = "gpt-4o-mini",
    limit: Optional[int] = None,
    resume: bool = True
):
    """Führt die Fachgebiet-Klassifikation durch."""
    print(f"\n🏥 FACHGEBIET-KLASSIFIKATION mit {model}")
    print("=" * 60)

    questions = load_questions()
    print(f"Geladen: {len(questions)} Fragen")

    if limit:
        questions = questions[:limit]
        print(f"Limitiert auf: {limit} Fragen")

    # Checkpoint laden
    checkpoint_path = OUTPUT_DIR / "fachgebiet_klassifikation.json"
    classified = {}
    if resume and checkpoint_path.exists():
        with open(checkpoint_path, encoding="utf-8") as f:
            classified = {item["frage"]: item for item in json.load(f)}
        print(f"Checkpoint geladen: {len(classified)} bereits klassifiziert")

    results = list(classified.values())

    for i, item in enumerate(questions):
        frage = item.get("frage", "")
        if frage in classified:
            continue

        print(f"\r[{i+1}/{len(questions)}] Klassifiziere...", end="", flush=True)

        classification = classify_question(item, model)

        result = {
            "frage": frage,
            "source_file": item.get("source_file", ""),
            "fachgebiet": classification["fachgebiet"],
            "subkategorie": classification["subkategorie"],
            "konfidenz": classification["konfidenz"],
            "hat_antwort": bool(item.get("antwort", "").strip()),
            "leitlinie": item.get("leitlinie", "")
        }
        results.append(result)
        classified[frage] = result

        # Checkpoint alle 50 Fragen
        if len(results) % 50 == 0:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f" [Checkpoint bei {len(results)}]")

    # Finale Speicherung
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Statistik
    print("\n\n📊 KLASSIFIKATIONS-ERGEBNIS:")
    from collections import Counter
    stats = Counter(r["fachgebiet"] for r in results)
    for fg, count in stats.most_common():
        print(f"  {fg}: {count}")

    print(f"\n✅ Gespeichert: {checkpoint_path}")
    return results


def run_validation(
    model: str = "gpt-4o",
    batch_size: int = 20,
    fachgebiet: Optional[str] = None,
    resume: bool = True
):
    """Führt die Validierung durch."""
    print(f"\n✅ ANTWORT-VALIDIERUNG mit {model}")
    print("=" * 60)

    # Zuerst Klassifikation laden
    class_path = OUTPUT_DIR / "fachgebiet_klassifikation.json"
    if not class_path.exists():
        print("❌ Bitte zuerst --classify ausführen!")
        return

    with open(class_path, encoding="utf-8") as f:
        classifications = {c["frage"]: c for c in json.load(f)}

    # Fragen laden
    questions = load_questions()

    # Optional: Nach Fachgebiet filtern
    if fachgebiet:
        questions = [
            q for q in questions
            if classifications.get(q.get("frage", {}), {}).get("fachgebiet") == fachgebiet
        ]
        print(f"Gefiltert nach {fachgebiet}: {len(questions)} Fragen")

    # Checkpoint
    val_path = OUTPUT_DIR / "validierung_ergebnisse.json"
    validated = {}
    if resume and val_path.exists():
        with open(val_path, encoding="utf-8") as f:
            validated = {v["frage"]: v for v in json.load(f)}
        print(f"Checkpoint: {len(validated)} bereits validiert")

    results = list(validated.values())

    for i, item in enumerate(questions[:batch_size]):
        frage = item.get("frage", "")
        if frage in validated:
            continue

        print(f"\n[{i+1}/{min(len(questions), batch_size)}] {frage[:60]}...")

        validation = validate_answer(item, model)

        result = {
            "frage": frage,
            "fachgebiet": classifications.get(frage, {}).get("fachgebiet", "Sonstige"),
            **validation
        }
        results.append(result)
        validated[frage] = result

    # Speichern
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Gespeichert: {val_path}")
    return results


def generate_inventory():
    """Generiert das Inventar nach Fachgebiet als Markdown."""
    print("\n📋 INVENTAR-GENERIERUNG")
    print("=" * 60)

    # Klassifikation laden
    class_path = OUTPUT_DIR / "fachgebiet_klassifikation.json"
    if not class_path.exists():
        print("❌ Bitte zuerst --classify ausführen!")
        return

    with open(class_path, encoding="utf-8") as f:
        classifications = json.load(f)

    # Nach Fachgebiet gruppieren
    by_fachgebiet = {}
    for item in classifications:
        fg = item["fachgebiet"]
        if fg not in by_fachgebiet:
            by_fachgebiet[fg] = []
        by_fachgebiet[fg].append(item)

    # Inventar-Verzeichnis erstellen
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)

    # Haupt-Inventar
    main_md = f"""# Medizinisches Prüfungsinventar nach Fachgebiet

_Generiert: {datetime.now().isoformat()}_

## Übersicht

| Fachgebiet | Anzahl Fragen | Mit Antwort | Ohne Antwort |
|------------|---------------|-------------|--------------|
"""

    for fg in FACHGEBIETE:
        items = by_fachgebiet.get(fg, [])
        mit = sum(1 for i in items if i.get("hat_antwort"))
        ohne = len(items) - mit
        main_md += f"| **{fg}** | {len(items)} | {mit} | {ohne} |\n"

    main_md += f"\n**Gesamt:** {len(classifications)} Fragen\n\n---\n\n"

    # Pro Fachgebiet eine Datei
    for fg in FACHGEBIETE:
        items = by_fachgebiet.get(fg, [])
        if not items:
            continue

        fg_md = f"# {fg}\n\n"
        fg_md += f"_Anzahl: {len(items)} Fragen_\n\n"

        # Nach Subkategorie gruppieren
        by_sub = {}
        for item in items:
            sub = item.get("subkategorie", "Allgemein") or "Allgemein"
            if sub not in by_sub:
                by_sub[sub] = []
            by_sub[sub].append(item)

        for sub, sub_items in sorted(by_sub.items()):
            fg_md += f"## {sub} ({len(sub_items)})\n\n"
            for item in sub_items:
                status = "✅" if item.get("hat_antwort") else "❌"
                fg_md += f"- {status} {item['frage'][:100]}...\n"
            fg_md += "\n"

        # Speichern
        fg_file = INVENTORY_DIR / f"{fg.lower().replace(' ', '_')}.md"
        with open(fg_file, "w", encoding="utf-8") as f:
            f.write(fg_md)

        main_md += f"- [{fg}]({fg.lower().replace(' ', '_')}.md) ({len(items)} Fragen)\n"

    # Haupt-Inventar speichern
    main_file = INVENTORY_DIR / "README.md"
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(main_md)

    print(f"✅ Inventar erstellt: {INVENTORY_DIR}/")
    for fg in FACHGEBIETE:
        if by_fachgebiet.get(fg):
            print(f"  - {fg}: {len(by_fachgebiet[fg])} Fragen")


def main():
    parser = argparse.ArgumentParser(description="Fachgebiet-Klassifikation und Validierung")
    parser.add_argument("--classify", action="store_true", help="Klassifikation durchführen")
    parser.add_argument("--validate", action="store_true", help="Validierung durchführen")
    parser.add_argument("--inventory", action="store_true", help="Inventar generieren")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI Modell (default: gpt-4o-mini)")
    parser.add_argument("--limit", type=int, help="Max. Anzahl zu verarbeitender Fragen")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch-Größe für Validierung")
    parser.add_argument("--fachgebiet", help="Nur bestimmtes Fachgebiet validieren")
    parser.add_argument("--no-resume", action="store_true", help="Checkpoint ignorieren")

    args = parser.parse_args()

    if not any([args.classify, args.validate, args.inventory]):
        parser.print_help()
        print("\n\nBeispiele:")
        print("  --classify                    # Alle Fragen klassifizieren")
        print("  --classify --limit 100        # Nur 100 Fragen klassifizieren")
        print("  --validate --batch-size 20    # 20 Fragen validieren")
        print("  --inventory                   # Inventar nach Fachgebiet erstellen")
        return

    if args.classify:
        run_classification(
            model=args.model,
            limit=args.limit,
            resume=not args.no_resume
        )

    if args.validate:
        run_validation(
            model=args.model if "4o" in args.model else "gpt-4o",
            batch_size=args.batch_size,
            fachgebiet=args.fachgebiet,
            resume=not args.no_resume
        )

    if args.inventory:
        generate_inventory()


if __name__ == "__main__":
    main()
