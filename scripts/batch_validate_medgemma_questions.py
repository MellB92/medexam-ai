#!/usr/bin/env python3
"""
batch_validate_medgemma_questions.py - Batch-Validierung aller MedGemma-relevanten Fragen

Dieses Skript validiert alle 310 MedGemma-relevanten Fragen aus medgemma_bild_fragen.json
durch den MedGemma 27B Endpoint. Es unterstützt Checkpointing für Wiederaufnahme,
Budget-Kontrolle und erzeugt detaillierte Validierungsberichte.

Verwendung:
    python scripts/batch_validate_medgemma_questions.py --budget 20.0 --batch-size 10

Argumente:
    --questions     Pfad zu medgemma_bild_fragen.json
    --output        Ausgabedatei (JSONL für Streaming)
    --budget        Maximales Budget in EUR
    --batch-size    Anfragen pro Batch (für Rate-Limiting)
    --resume        Von letztem Checkpoint fortsetzen
    --priority      Nur Fragen mit bestimmter Priorität (hoch, mittel, niedrig)
    --max-questions Maximale Anzahl zu validierender Fragen

Ausgabe:
    - medgemma_batch_validation.jsonl (eine Zeile pro validierter Frage)
    - medgemma_batch_validation_checkpoint.json (für Wiederaufnahme)
    - medgemma_batch_validation_summary.json (Zusammenfassung)

Autor: Claude Code / MedExam AI Team
Datum: 2025-12-23
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv

# Google Cloud AI Platform
try:
    from google.cloud import aiplatform
    VERTEX_AVAILABLE = True
except ImportError:
    VERTEX_AVAILABLE = False

load_dotenv()

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Kosten-Schätzung (A100 GPU)
COST_PER_1K_INPUT = 0.0001
COST_PER_1K_OUTPUT = 0.0004
EUR_USD_RATE = 1.05  # Ungefährer Wechselkurs


class BatchValidator:
    """
    Batch-Validierung von medizinischen Fragen mit MedGemma.
    """

    def __init__(
        self,
        project: str = None,
        region: str = None,
        endpoint_id: str = None,
        budget_eur: float = 20.0
    ):
        self.project = project or os.getenv("GOOGLE_CLOUD_PROJECT", "medexamenai")
        self.region = region or os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
        self.endpoint_id = endpoint_id or os.getenv("MEDGEMMA_ENDPOINT_ID")

        if not self.endpoint_id:
            raise ValueError("MEDGEMMA_ENDPOINT_ID nicht konfiguriert!")

        self.budget_eur = budget_eur
        self.budget_usd = budget_eur * EUR_USD_RATE
        self.total_cost_usd = 0.0
        self.total_tokens = 0
        self.validated_count = 0
        self.error_count = 0

        # Vertex AI initialisieren
        if VERTEX_AVAILABLE:
            aiplatform.init(project=self.project, location=self.region)
            self.endpoint = aiplatform.Endpoint(
                endpoint_name=f"projects/{self.project}/locations/{self.region}/endpoints/{self.endpoint_id}"
            )
            logger.info(f"✅ Verbunden mit: {self.endpoint.display_name}")
        else:
            self.endpoint = None
            logger.warning("⚠️  Vertex AI nicht verfügbar")

    def is_budget_available(self) -> bool:
        """Prüft, ob Budget verfügbar ist."""
        return self.total_cost_usd < self.budget_usd

    def get_system_prompt(self, bild_typ: str) -> str:
        """
        Gibt einen spezialisierten System-Prompt basierend auf Bildtyp zurück.
        WICHTIG: Direkter, aktionsorientierter Prompt ohne Meta-Beschreibungen.
        """
        base_prompt = """Du bist Prüfer für die deutsche ärztliche Kenntnisprüfung.

WICHTIG: Antworte DIREKT auf die Frage. Keine Einleitungen wie "Ich werde validieren..." oder "Okay, lass mich analysieren...".
Beginne sofort mit der medizinischen Antwort.

Format:
1. DIAGNOSE/BEFUND: [Direkte Antwort]
2. BEGRÜNDUNG: [2-3 Sätze mit Evidenz]
3. LEITLINIE: [Relevante AWMF/ESC/DGK Empfehlung]"""

        typ_prompts = {
            "EKG": """
Bei EKG-Fragen nenne direkt:
- Rhythmus (Sinusrhythmus, VHF, Flattern, etc.)
- Frequenz (Tachykard >100, Bradykard <60, Normofrequent)
- Auffälligkeiten (ST-Hebung → STEMI, verlängertes QT, Schenkelblock)
- Therapie gemäß ESC-Leitlinien""",

            "Röntgen": """
Bei Röntgen-Fragen beschreibe direkt:
- Befund (z.B. "Infiltrat rechts basal", "Kardiomegalie", "Pneumothorax links")
- Diagnose (z.B. "V.a. Pneumonie", "Herzinsuffizienz")
- Nächster Schritt (z.B. "Labor + Sputum", "CT bei Unklarheit")""",

            "CT": """
Bei CT-Fragen nenne direkt:
- Lokalisation und Morphologie des Befunds
- Wahrscheinlichste Diagnose
- Differentialdiagnosen (max. 2-3)""",

            "MRT": """
Bei MRT-Fragen beschreibe:
- Signalverhalten (T1/T2 hyper-/hypointens)
- Diagnose basierend auf Morphologie
- Klinische Konsequenz""",

            "Sonographie": """
Bei Sono-Fragen nenne direkt:
- Echogenität und Befund
- Diagnose (z.B. "Cholezystolithiasis", "Aszites")
- Therapieempfehlung""",

            "Dermatologie": """
Bei Derma-Fragen beschreibe:
- Effloreszenz (Papel, Pustel, Bläschen, etc.)
- Diagnose mit Begründung
- Therapie (lokal/systemisch)"""
        }

        if bild_typ in typ_prompts:
            return f"{base_prompt}\n{typ_prompts[bild_typ]}"
        return base_prompt

    def validate_single(self, question_data: Dict) -> Dict[str, Any]:
        """
        Validiert eine einzelne Frage.

        Args:
            question_data: Dictionary mit Frage-Metadaten

        Returns:
            Validierungs-Ergebnis
        """
        frage_id = question_data.get("frage_id", "unknown")
        bild_typ = question_data.get("bild_typ", "Sonstige")
        frage_text = question_data.get("frage_text", "")

        result = {
            "frage_id": frage_id,
            "bild_typ": bild_typ,
            "prioritaet": question_data.get("prioritaet", "niedrig"),
            "medgemma_relevant": question_data.get("medgemma_relevant", False),
            "original_frage": frage_text[:500],
            "timestamp": datetime.now().isoformat()
        }

        if not self.is_budget_available():
            result["error"] = "Budget erschöpft"
            result["success"] = False
            return result

        if not self.endpoint:
            result["error"] = "Endpoint nicht verfügbar"
            result["success"] = False
            return result

        # Anfrage erstellen
        system_prompt = self.get_system_prompt(bild_typ)

        request = {
            "@requestFormat": "chatCompletions",
            "messages": [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": system_prompt}]
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": frage_text}]
                }
            ],
            "max_tokens": 600
        }

        try:
            response = self.endpoint.predict(instances=[request])

            if isinstance(response.predictions, dict):
                choices = response.predictions.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    usage = response.predictions.get("usage", {})

                    input_tokens = usage.get("prompt_tokens", 0)
                    output_tokens = usage.get("completion_tokens", 0)

                    cost = (
                        input_tokens / 1000 * COST_PER_1K_INPUT +
                        output_tokens / 1000 * COST_PER_1K_OUTPUT
                    )

                    result.update({
                        "medgemma_antwort": content,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": usage.get("total_tokens", 0),
                        "cost_usd": cost,
                        "success": True
                    })

                    self.total_cost_usd += cost
                    self.total_tokens += result["total_tokens"]
                    self.validated_count += 1
                else:
                    result["error"] = "Keine Antwort erhalten"
                    result["success"] = False
                    self.error_count += 1
            else:
                result["error"] = "Unerwartetes Response-Format"
                result["success"] = False
                self.error_count += 1

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False
            self.error_count += 1
            logger.error(f"❌ Fehler bei {frage_id}: {e}")

        return result


def load_checkpoint(checkpoint_path: Path) -> Set[str]:
    """Lädt bereits verarbeitete Frage-IDs aus Checkpoint."""
    if not checkpoint_path.exists():
        return set()

    try:
        with open(checkpoint_path, "r") as f:
            data = json.load(f)
        return set(data.get("processed_ids", []))
    except Exception as e:
        logger.warning(f"⚠️  Checkpoint konnte nicht geladen werden: {e}")
        return set()


def save_checkpoint(checkpoint_path: Path, processed_ids: Set[str], stats: Dict):
    """Speichert Checkpoint für Wiederaufnahme."""
    data = {
        "processed_ids": list(processed_ids),
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }
    with open(checkpoint_path, "w") as f:
        json.dump(data, f, indent=2)


def load_questions(path: Path) -> List[Dict]:
    """Lädt Fragen aus JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "bild_fragen" in data:
        return data["bild_fragen"]
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Batch-Validierung aller MedGemma-relevanten Fragen"
    )

    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("_OUTPUT/medgemma_bild_fragen.json"),
        help="Pfad zu medgemma_bild_fragen.json"
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("_OUTPUT/medgemma_batch_validation.jsonl"),
        help="Ausgabedatei (JSONL)"
    )

    parser.add_argument(
        "--budget",
        type=float,
        default=20.0,
        help="Maximales Budget in EUR"
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Anfragen pro Batch"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Von letztem Checkpoint fortsetzen"
    )

    parser.add_argument(
        "--priority",
        type=str,
        choices=["hoch", "mittel", "niedrig"],
        help="Nur Fragen mit bestimmter Priorität"
    )

    parser.add_argument(
        "--medgemma-relevant-only",
        action="store_true",
        help="Nur MedGemma-relevante Fragen validieren"
    )

    parser.add_argument(
        "--max-questions",
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
        logger.error(f"❌ Nicht gefunden: {args.questions}")
        sys.exit(1)

    logger.info(f"📂 Lade Fragen: {args.questions}")
    questions = load_questions(args.questions)

    # Filter anwenden
    if args.medgemma_relevant_only:
        questions = [q for q in questions if q.get("medgemma_relevant", False)]

    if args.priority:
        questions = [q for q in questions if q.get("prioritaet") == args.priority]

    # Nach Priorität sortieren
    priority_order = {"hoch": 0, "mittel": 1, "niedrig": 2}
    questions = sorted(questions, key=lambda x: priority_order.get(x.get("prioritaet", "niedrig"), 3))

    logger.info(f"📊 Fragen nach Filterung: {len(questions)}")

    # Checkpoint laden
    checkpoint_path = args.output.with_suffix(".checkpoint.json")
    processed_ids = set()

    if args.resume and checkpoint_path.exists():
        processed_ids = load_checkpoint(checkpoint_path)
        logger.info(f"🔄 Resume: {len(processed_ids)} bereits verarbeitet")
        questions = [q for q in questions if q.get("frage_id") not in processed_ids]

    # Limit anwenden
    if args.max_questions:
        questions = questions[:args.max_questions]

    logger.info(f"📋 Zu validieren: {len(questions)} Fragen")

    # Dry-Run
    if args.dry_run:
        logger.info("\n🔎 DRY-RUN:")
        for i, q in enumerate(questions[:10]):
            logger.info(f"   {i+1}. [{q.get('prioritaet')}] [{q.get('bild_typ')}] {q.get('frage_id')}")
        if len(questions) > 10:
            logger.info(f"   ... und {len(questions) - 10} weitere")
        sys.exit(0)

    # Validator initialisieren
    try:
        validator = BatchValidator(budget_eur=args.budget)
    except Exception as e:
        logger.error(f"❌ Initialisierung fehlgeschlagen: {e}")
        sys.exit(1)

    # Ausgabedatei öffnen (Append-Modus für JSONL)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"

    stats = {
        "total_questions": len(questions),
        "validated": 0,
        "errors": 0,
        "skipped_budget": 0,
        "start_time": datetime.now().isoformat()
    }

    with open(args.output, mode, encoding="utf-8") as out_file:
        for i, question in enumerate(questions):
            frage_id = question.get("frage_id")

            # Budget-Check
            if not validator.is_budget_available():
                logger.warning(f"⚠️  Budget erschöpft bei Frage {i+1}")
                stats["skipped_budget"] = len(questions) - i
                break

            # Validieren
            logger.info(f"[{i+1}/{len(questions)}] {frage_id} ({question.get('bild_typ')})")
            result = validator.validate_single(question)

            # In JSONL schreiben
            out_file.write(json.dumps(result, ensure_ascii=False) + "\n")
            out_file.flush()

            # Tracking
            processed_ids.add(frage_id)
            if result.get("success"):
                stats["validated"] += 1
            else:
                stats["errors"] += 1

            # Checkpoint speichern (alle 10 Fragen)
            if (i + 1) % 10 == 0:
                save_checkpoint(checkpoint_path, processed_ids, stats)
                logger.info(f"   💰 Kosten: ${validator.total_cost_usd:.4f} / ${validator.budget_usd:.2f}")

            # Batch-Pause
            if (i + 1) % args.batch_size == 0:
                time.sleep(0.5)

    # Finale Stats
    stats["end_time"] = datetime.now().isoformat()
    stats["total_cost_usd"] = validator.total_cost_usd
    stats["total_cost_eur"] = validator.total_cost_usd / EUR_USD_RATE
    stats["total_tokens"] = validator.total_tokens

    # Zusammenfassung speichern
    summary_path = args.output.with_suffix(".summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # Finaler Checkpoint
    save_checkpoint(checkpoint_path, processed_ids, stats)

    # Ausgabe
    logger.info("\n" + "=" * 60)
    logger.info("📊 BATCH-VALIDIERUNG ABGESCHLOSSEN")
    logger.info("=" * 60)
    logger.info(f"   Validiert: {stats['validated']}/{stats['total_questions']}")
    logger.info(f"   Fehler: {stats['errors']}")
    logger.info(f"   Budget-Stop: {stats.get('skipped_budget', 0)}")
    logger.info(f"   Kosten: ${stats['total_cost_usd']:.4f} (€{stats['total_cost_eur']:.4f})")
    logger.info(f"   Tokens: {stats['total_tokens']}")
    logger.info(f"   Ausgabe: {args.output}")
    logger.info(f"   Summary: {summary_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
