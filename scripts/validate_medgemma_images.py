#!/usr/bin/env python3
"""
validate_medgemma_images.py - Multimodale Validierung mit MedGemma und Bildern

Dieses Skript lädt bild-basierte Fragen aus medgemma_bild_fragen.json,
verknüpft sie mit den entsprechenden extrahierten Bildern und sendet
multimodale Anfragen an den MedGemma 27B Endpoint.

Verwendung:
    python scripts/validate_medgemma_images.py --batch-size 5 --budget 10.0

Argumente:
    --questions     Pfad zu medgemma_bild_fragen.json (Standard: _OUTPUT/medgemma_bild_fragen.json)
    --images-dir    Verzeichnis mit extrahierten Bildern (Standard: _OUTPUT/ekg_images)
    --output        Ausgabedatei für Ergebnisse (Standard: _OUTPUT/medgemma_image_responses.json)
    --batch-size    Anzahl Anfragen pro Batch (Standard: 5)
    --budget        Maximales Budget in EUR (Standard: 10.0)
    --filter-type   Nur bestimmte Bildtypen validieren (z.B. EKG, Röntgen)
    --dry-run       Nur anzeigen, was gemacht würde

Ausgabe:
    - medgemma_image_responses.json mit allen Antworten und Metadaten

Autor: Claude Code / MedExam AI Team
Datum: 2025-12-23
"""

import argparse
import base64
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Google Cloud AI Platform
try:
    from google.cloud import aiplatform
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False
    print("⚠️  google-cloud-aiplatform nicht installiert")

load_dotenv()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Kosten pro Token (geschätzt für MedGemma auf A100)
# Basiert auf ~$3.67/Stunde für A100, ~1000 Tokens/Sekunde
COST_PER_1K_INPUT = 0.0001   # $0.10 per 1M input tokens
COST_PER_1K_OUTPUT = 0.0004  # $0.40 per 1M output tokens


class MedGemmaImageValidator:
    """
    Validiert medizinische Fragen mit Bildern über MedGemma 27B Multimodal.
    """

    def __init__(
        self,
        project: str = None,
        region: str = None,
        endpoint_id: str = None,
        budget_eur: float = 10.0
    ):
        """
        Initialisiert den Validator.

        Args:
            project: Google Cloud Projekt ID
            region: Google Cloud Region
            endpoint_id: MedGemma Endpoint ID
            budget_eur: Maximales Budget in EUR
        """
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT", "medexamenai")
        self.region = region or os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.endpoint_id = endpoint_id or os.getenv("MEDGEMMA_ENDPOINT_ID")

        if not self.endpoint_id:
            raise ValueError("MEDGEMMA_ENDPOINT_ID nicht konfiguriert!")

        self.budget_eur = budget_eur
        self.total_cost = 0.0
        self.total_tokens = 0

        # Vertex AI initialisieren
        if VERTEX_AVAILABLE:
            aiplatform.init(project=self.project, location=self.region)
            self.endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{self.project}/locations/{self.region}/endpoints/{self.endpoint_id}"
            )
            logger.info(f"✅ MedGemma Endpoint verbunden: {self.endpoint.display_name}")
        else:
            self.endpoint = None
            logger.warning("⚠️  Vertex AI nicht verfügbar - Dry-Run Modus")

    def encode_image_base64(self, image_path: Path) -> Optional[str]:
        """
        Kodiert ein Bild als Base64-String.

        Args:
            image_path: Pfad zum Bild

        Returns:
            Base64-kodierter String oder None bei Fehler
        """
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"❌ Fehler beim Laden von {image_path}: {e}")
            return None

    def create_multimodal_request(
        self,
        question: str,
        image_base64: Optional[str] = None,
        image_url: Optional[str] = None,
        system_prompt: str = None
    ) -> Dict[str, Any]:
        """
        Erstellt eine multimodale Anfrage für MedGemma.

        Args:
            question: Die medizinische Frage
            image_base64: Base64-kodiertes Bild
            image_url: Öffentliche URL zum Bild
            system_prompt: Systemanweisung

        Returns:
            Dictionary mit der Anfrage-Struktur
        """
        if system_prompt is None:
            system_prompt = """Du bist ein erfahrener Prüfer für die deutsche ärztliche Kenntnisprüfung.
Analysiere das gezeigte medizinische Bild (falls vorhanden) und beantworte die Frage.
Gib eine präzise, evidenzbasierte Antwort mit:
1. Beschreibung der relevanten Befunde im Bild
2. Diagnose oder differentialdiagnostische Überlegungen
3. Therapieempfehlung gemäß aktueller Leitlinien"""

        # Nachrichten-Struktur
        user_content = [{"type": "text", "text": question}]

        # Bild hinzufügen (wenn vorhanden)
        if image_base64:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{image_base64}"}
            })
        elif image_url:
            user_content.append({
                "type": "image_url",
                "image_url": {"url": image_url}
            })

        return {
            "@requestFormat": "chatCompletions",
            "messages": [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}]
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            "max_tokens": 800
        }

    def validate_question(
        self,
        question_data: Dict,
        image_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Validiert eine einzelne Frage mit optionalem Bild.

        Args:
            question_data: Dictionary mit Frage-Metadaten
            image_path: Optionaler Pfad zum zugehörigen Bild

        Returns:
            Dictionary mit Antwort und Metadaten
        """
        result = {
            "frage_id": question_data.get("frage_id"),
            "bild_typ": question_data.get("bild_typ"),
            "original_frage": question_data.get("frage_text", "")[:500],
            "image_used": image_path is not None,
            "image_path": str(image_path) if image_path else None,
            "timestamp": datetime.now().isoformat()
        }

        # Budget-Check
        if self.total_cost >= self.budget_eur:
            result["error"] = "Budget erschöpft"
            result["success"] = False
            return result

        # Bild laden (falls vorhanden)
        image_base64 = None
        if image_path and image_path.exists():
            image_base64 = self.encode_image_base64(image_path)

        # Anfrage erstellen
        request = self.create_multimodal_request(
            question=question_data.get("frage_text", ""),
            image_base64=image_base64
        )

        # API-Aufruf
        if not self.endpoint:
            result["error"] = "Endpoint nicht verfügbar (Dry-Run)"
            result["success"] = False
            return result

        try:
            response = self.endpoint.predict(instances=[request])

            # Antwort parsen
            if isinstance(response.predictions, dict):
                choices = response.predictions.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    usage = response.predictions.get("usage", {})

                    result["medgemma_antwort"] = content
                    result["input_tokens"] = usage.get("prompt_tokens", 0)
                    result["output_tokens"] = usage.get("completion_tokens", 0)
                    result["total_tokens"] = usage.get("total_tokens", 0)

                    # Kosten berechnen
                    cost = (
                        result["input_tokens"] / 1000 * COST_PER_1K_INPUT +
                        result["output_tokens"] / 1000 * COST_PER_1K_OUTPUT
                    )
                    result["cost_usd"] = cost
                    result["success"] = True

                    # Tracking
                    self.total_cost += cost
                    self.total_tokens += result["total_tokens"]
                else:
                    result["error"] = "Keine Antwort erhalten"
                    result["success"] = False
            else:
                result["error"] = f"Unerwartetes Response-Format: {type(response.predictions)}"
                result["success"] = False

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            logger.error(f"❌ API-Fehler: {e}")

        return result

    def find_matching_image(
        self,
        question_data: Dict,
        images_dir: Path
    ) -> Optional[Path]:
        """
        Sucht das passende Bild zu einer Frage.

        Args:
            question_data: Frage-Metadaten
            images_dir: Verzeichnis mit Bildern

        Returns:
            Pfad zum passenden Bild oder None
        """
        # Versuche, Bild über Quelldatei zu finden
        source_pdf = question_data.get("source_pdf", "")
        if source_pdf:
            pdf_stem = Path(source_pdf).stem
            # Suche nach Bildern mit diesem Präfix
            matches = list(images_dir.glob(f"{pdf_stem}*.png"))
            if matches:
                return matches[0]  # Erstes passendes Bild

        return None


def load_questions(questions_path: Path) -> List[Dict]:
    """Lädt die bild-basierten Fragen."""
    with open(questions_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "bild_fragen" in data:
        return data["bild_fragen"]
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Multimodale Validierung mit MedGemma und Bildern"
    )

    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("_OUTPUT/medgemma_bild_fragen.json"),
        help="Pfad zu medgemma_bild_fragen.json"
    )

    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("_OUTPUT/ekg_images"),
        help="Verzeichnis mit extrahierten Bildern"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_OUTPUT/medgemma_image_responses.json"),
        help="Ausgabedatei für Ergebnisse"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Anzahl Anfragen pro Batch"
    )

    parser.add_argument(
        "--budget",
        type=float,
        default=10.0,
        help="Maximales Budget in EUR"
    )

    parser.add_argument(
        "--filter-type",
        type=str,
        choices=["EKG", "Röntgen", "CT", "MRT", "Sonographie", "Dermatologie"],
        help="Nur bestimmte Bildtypen validieren"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximale Anzahl zu validierender Fragen"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur anzeigen, was gemacht würde"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Ausführliche Ausgabe"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Fragen laden
    if not args.questions.exists():
        logger.error(f"❌ Fragen-Datei nicht gefunden: {args.questions}")
        sys.exit(1)

    logger.info(f"📂 Lade Fragen aus: {args.questions}")
    questions = load_questions(args.questions)

    # Nach Typ filtern
    if args.filter_type:
        questions = [q for q in questions if q.get("bild_typ") == args.filter_type]
        logger.info(f"   Gefiltert auf {args.filter_type}: {len(questions)} Fragen")

    # MedGemma-relevante Fragen bevorzugen
    questions = sorted(questions, key=lambda x: (
        not x.get("medgemma_relevant", False),
        x.get("prioritaet", "niedrig") != "hoch"
    ))

    # Limit anwenden
    if args.limit:
        questions = questions[:args.limit]

    logger.info(f"📊 Zu validierende Fragen: {len(questions)}")

    # Dry-Run
    if args.dry_run:
        logger.info("\n🔎 DRY-RUN - Würde folgende Fragen validieren:")
        for i, q in enumerate(questions[:10]):
            logger.info(f"   {i+1}. [{q.get('bild_typ')}] {q.get('frage_text', '')[:60]}...")
        if len(questions) > 10:
            logger.info(f"   ... und {len(questions) - 10} weitere")
        sys.exit(0)

    # Validator initialisieren
    try:
        validator = MedGemmaImageValidator(budget_eur=args.budget)
    except Exception as e:
        logger.error(f"❌ Initialisierung fehlgeschlagen: {e}")
        sys.exit(1)

    # Validierung durchführen
    results = []
    stats = {
        "total_questions": len(questions),
        "validated": 0,
        "with_image": 0,
        "errors": 0,
        "start_time": datetime.now().isoformat()
    }

    for i, question in enumerate(questions):
        # Budget-Check
        if validator.total_cost >= args.budget:
            logger.warning(f"⚠️  Budget erschöpft ({args.budget} EUR)")
            break

        # Passendes Bild suchen
        image_path = validator.find_matching_image(question, args.images_dir)
        if image_path:
            stats["with_image"] += 1

        # Validieren
        logger.info(f"[{i+1}/{len(questions)}] Validiere: {question.get('frage_id')}")
        result = validator.validate_question(question, image_path)
        results.append(result)

        if result.get("success"):
            stats["validated"] += 1
        else:
            stats["errors"] += 1

        # Batch-Pause (Rate-Limiting)
        if (i + 1) % args.batch_size == 0:
            logger.info(f"   💰 Bisherige Kosten: ${validator.total_cost:.4f}")
            time.sleep(1)  # Kurze Pause zwischen Batches

    stats["end_time"] = datetime.now().isoformat()
    stats["total_cost_usd"] = validator.total_cost
    stats["total_tokens"] = validator.total_tokens

    # Ergebnisse speichern
    output_data = {
        "validation_stats": stats,
        "settings": {
            "budget_eur": args.budget,
            "batch_size": args.batch_size,
            "filter_type": args.filter_type,
            "images_dir": str(args.images_dir)
        },
        "results": results
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    # Zusammenfassung
    logger.info("\n" + "=" * 50)
    logger.info("📊 VALIDIERUNG ABGESCHLOSSEN")
    logger.info("=" * 50)
    logger.info(f"   Validiert: {stats['validated']}/{stats['total_questions']}")
    logger.info(f"   Mit Bild: {stats['with_image']}")
    logger.info(f"   Fehler: {stats['errors']}")
    logger.info(f"   Kosten: ${stats['total_cost_usd']:.4f}")
    logger.info(f"   Tokens: {stats['total_tokens']}")
    logger.info(f"   Ausgabe: {args.output}")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
