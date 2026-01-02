#!/usr/bin/env python3
"""
extract_ekg_images.py - Extrahiert Bilder aus medizinischen PDFs (EKG, Röntgen, etc.)

Dieses Skript liest PDFs aus einem Eingabeverzeichnis, konvertiert jede Seite
zu einem PNG-Bild und speichert diese in einem Ausgabeverzeichnis. Optional
kann OCR auf die Bilder angewendet werden.

Verwendung:
    python scripts/extract_ekg_images.py --input-dir _FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie --output-dir _OUTPUT/ekg_images --dpi 200

Argumente:
    --input-dir     Verzeichnis mit PDF-Dateien (Standard: _FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie)
    --output-dir    Zielverzeichnis für extrahierte Bilder (Standard: _OUTPUT/ekg_images)
    --dpi           Auflösung der extrahierten Bilder (Standard: 200)
    --pattern       Glob-Pattern für PDF-Dateien (Standard: *.pdf)
    --ocr           OCR auf Bilder anwenden (erfordert pytesseract)
    --verbose       Ausführliche Ausgabe

Ausgabe:
    - PNG-Bilder für jede Seite jeder PDF
    - extraction_manifest.json mit Metadaten zu allen extrahierten Bildern

Autor: Claude Code / MedExam AI Team
Datum: 2025-12-23
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# PyMuPDF für PDF-Verarbeitung
try:
    import fitz  # PyMuPDF
except ImportError:
    print("FEHLER: PyMuPDF nicht installiert. Bitte installieren mit: pip install PyMuPDF")
    sys.exit(1)

# Optional: OCR mit pytesseract
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def extract_images_from_pdf(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 200,
    apply_ocr: bool = False
) -> List[Dict]:
    """
    Extrahiert alle Seiten einer PDF als PNG-Bilder.

    Args:
        pdf_path: Pfad zur PDF-Datei
        output_dir: Zielverzeichnis für Bilder
        dpi: Auflösung (dots per inch)
        apply_ocr: OCR auf Bilder anwenden

    Returns:
        Liste von Dictionaries mit Metadaten zu extrahierten Bildern
    """
    extracted = []
    pdf_name = pdf_path.stem

    try:
        doc = fitz.open(pdf_path)
        logger.info(f"📄 Verarbeite: {pdf_path.name} ({len(doc)} Seiten)")

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Seite als Bild rendern
            # Zoom-Faktor berechnen: 72 DPI ist Standard, also zoom = dpi/72
            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)

            # Dateiname erstellen
            image_filename = f"{pdf_name}_page_{page_num + 1:03d}.png"
            image_path = output_dir / image_filename

            # Als PNG speichern
            pix.save(str(image_path))

            # Metadaten sammeln
            image_meta = {
                "source_pdf": str(pdf_path.name),
                "page_number": page_num + 1,
                "total_pages": len(doc),
                "image_path": str(image_path),
                "image_filename": image_filename,
                "width": pix.width,
                "height": pix.height,
                "dpi": dpi,
                "extracted_at": datetime.now().isoformat()
            }

            # Optional: OCR anwenden
            if apply_ocr and OCR_AVAILABLE:
                try:
                    img = Image.open(image_path)
                    ocr_text = pytesseract.image_to_string(img, lang='deu')
                    image_meta["ocr_text"] = ocr_text.strip()
                    image_meta["ocr_success"] = bool(ocr_text.strip())
                except Exception as e:
                    logger.warning(f"OCR fehlgeschlagen für {image_filename}: {e}")
                    image_meta["ocr_text"] = ""
                    image_meta["ocr_success"] = False

            extracted.append(image_meta)
            logger.debug(f"  ✓ Seite {page_num + 1}: {image_filename}")

        doc.close()
        logger.info(f"  → {len(extracted)} Bilder extrahiert")

    except Exception as e:
        logger.error(f"❌ Fehler bei {pdf_path.name}: {e}")

    return extracted


def find_pdf_files(input_dir: Path, pattern: str = "*.pdf") -> List[Path]:
    """
    Findet alle PDF-Dateien im angegebenen Verzeichnis.

    Args:
        input_dir: Suchverzeichnis
        pattern: Glob-Pattern (Standard: *.pdf)

    Returns:
        Liste von Pfaden zu PDF-Dateien
    """
    pdfs = list(input_dir.glob(pattern))

    # Auch in Unterverzeichnissen suchen
    pdfs.extend(input_dir.rglob(pattern))

    # Duplikate entfernen und sortieren
    pdfs = sorted(set(pdfs))

    return pdfs


def filter_ekg_pdfs(pdf_files: List[Path]) -> List[Path]:
    """
    Filtert PDFs nach EKG-relevanten Schlüsselwörtern im Dateinamen.

    Args:
        pdf_files: Liste aller PDF-Dateien

    Returns:
        Gefilterte Liste mit EKG-relevanten PDFs
    """
    ekg_keywords = [
        "ekg", "EKG", "Ekg",
        "rhythmus", "Rhythmus",
        "herzfrequenz", "Herzfrequenz",
        "kardiologie", "Kardiologie",
        "herz", "Herz",
        "elektrokardiogramm"
    ]

    filtered = []
    for pdf in pdf_files:
        name_lower = pdf.name.lower()
        if any(kw.lower() in name_lower for kw in ekg_keywords):
            filtered.append(pdf)

    return filtered


def main():
    parser = argparse.ArgumentParser(
        description="Extrahiert Bilder aus medizinischen PDFs (EKG, Röntgen, etc.)"
    )

    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("_FACT_CHECK_SOURCES/fachgebiete/innere_medizin/kardiologie"),
        help="Verzeichnis mit PDF-Dateien"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("_OUTPUT/ekg_images"),
        help="Zielverzeichnis für extrahierte Bilder"
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="Auflösung der extrahierten Bilder (Standard: 200)"
    )

    parser.add_argument(
        "--pattern",
        type=str,
        default="*.pdf",
        help="Glob-Pattern für PDF-Dateien (Standard: *.pdf)"
    )

    parser.add_argument(
        "--ocr",
        action="store_true",
        help="OCR auf Bilder anwenden (erfordert pytesseract)"
    )

    parser.add_argument(
        "--ekg-only",
        action="store_true",
        help="Nur PDFs mit EKG-Schlüsselwörtern im Namen verarbeiten"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ausführliche Ausgabe"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, was gemacht würde (keine Extraktion)"
    )

    args = parser.parse_args()

    # Logging-Level anpassen
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # OCR-Warnung
    if args.ocr and not OCR_AVAILABLE:
        logger.warning("⚠️  OCR angefordert, aber pytesseract nicht installiert!")
        logger.warning("    Installieren mit: pip install pytesseract pillow")
        args.ocr = False

    # Eingabeverzeichnis prüfen
    if not args.input_dir.exists():
        logger.error(f"❌ Eingabeverzeichnis nicht gefunden: {args.input_dir}")
        sys.exit(1)

    # PDF-Dateien finden
    logger.info(f"🔍 Suche PDFs in: {args.input_dir}")
    pdf_files = find_pdf_files(args.input_dir, args.pattern)

    if args.ekg_only:
        pdf_files = filter_ekg_pdfs(pdf_files)
        logger.info(f"   (gefiltert auf EKG-relevante Dateien)")

    if not pdf_files:
        logger.warning("⚠️  Keine PDF-Dateien gefunden!")
        sys.exit(0)

    logger.info(f"📚 Gefunden: {len(pdf_files)} PDF-Dateien")

    # Dry-Run: Nur anzeigen
    if args.dry_run:
        logger.info("\n🔎 DRY-RUN - Würde folgende Dateien verarbeiten:")
        for pdf in pdf_files:
            logger.info(f"   - {pdf.name}")
        sys.exit(0)

    # Ausgabeverzeichnis erstellen
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"📁 Ausgabeverzeichnis: {args.output_dir}")

    # Alle PDFs verarbeiten
    all_extracted = []
    stats = {
        "total_pdfs": len(pdf_files),
        "processed_pdfs": 0,
        "failed_pdfs": 0,
        "total_images": 0,
        "start_time": datetime.now().isoformat()
    }

    for pdf_path in pdf_files:
        extracted = extract_images_from_pdf(
            pdf_path=pdf_path,
            output_dir=args.output_dir,
            dpi=args.dpi,
            apply_ocr=args.ocr
        )

        if extracted:
            all_extracted.extend(extracted)
            stats["processed_pdfs"] += 1
            stats["total_images"] += len(extracted)
        else:
            stats["failed_pdfs"] += 1

    stats["end_time"] = datetime.now().isoformat()

    # Manifest speichern
    manifest = {
        "extraction_stats": stats,
        "settings": {
            "input_dir": str(args.input_dir),
            "output_dir": str(args.output_dir),
            "dpi": args.dpi,
            "ocr_enabled": args.ocr,
            "pattern": args.pattern
        },
        "images": all_extracted
    }

    manifest_path = args.output_dir / "extraction_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Zusammenfassung
    logger.info("\n" + "=" * 50)
    logger.info("📊 EXTRAKTION ABGESCHLOSSEN")
    logger.info("=" * 50)
    logger.info(f"   PDFs verarbeitet: {stats['processed_pdfs']}/{stats['total_pdfs']}")
    logger.info(f"   Bilder extrahiert: {stats['total_images']}")
    logger.info(f"   Fehlgeschlagen: {stats['failed_pdfs']}")
    logger.info(f"   Manifest: {manifest_path}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
