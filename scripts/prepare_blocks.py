#!/usr/bin/env python3
"""
Bereitet Frage-Blöcke für die Antwort-Generierung vor.
- Lädt frage_bloecke.json
- Klassifiziert Themen (subject_classifier)
- Wählt Leitlinien (guideline_fetcher)
- Fügt RAG-Snippets an (rag_system)
- Speichert nach _OUTPUT/blocks_prepared.json
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml  # type: ignore

# lokale Imports
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.subject_classifier import classify_subject  # type: ignore
from core.guideline_fetcher import fetch_guidelines_for_text  # type: ignore
from core.rag_system import get_rag_system  # type: ignore


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config nicht gefunden: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def prepare_blocks(blocks: List[Dict[str, Any]], max_rag_sources: int = 3) -> List[Dict[str, Any]]:
    rag = get_rag_system(use_openai=False)
    prepared: List[Dict[str, Any]] = []

    # Wissen befüllen (Fragen + Kontext)
    for b in blocks:
        rag.add_to_knowledge_base(
            [b.get("questions", []), b.get("context", [])],
            source_module="gold_standard",
            source_tier="tier1_gold",
        )

    for b in blocks:
        text = " ".join(b.get("questions", [])) + " " + " ".join(b.get("context", []))
        subject = classify_subject(text) or "Allgemein"
        gl = fetch_guidelines_for_text(text, download=False)
        guideline = gl["guidelines"][0] if gl.get("guidelines") else {}
        rag_ctx = rag.get_context_for_question(text, top_k=max_rag_sources)

        prepared.append(
            {
                **b,
                "subject": subject,
                "guideline": guideline,
                "rag_snippets": rag_ctx.get("contexts", []),
                "rag_sources": rag_ctx.get("sources", []),
            }
        )
    return prepared


def main() -> int:
    parser = argparse.ArgumentParser(description="Bereitet Frage-Blöcke für die Antwort-Generierung vor.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--input", default=None, help="Eingabe: frage_bloecke.json")
    parser.add_argument("--output", default=None, help="Ausgabe: blocks_prepared.json")
    parser.add_argument("--rag-k", type=int, default=3, help="Anzahl RAG-Snippets pro Block")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    base = Path(args.config).resolve().parent
    extracted_dir = base / config.get("extracted_dir", "_EXTRACTED_FRAGEN")
    output_dir = base / config.get("output_dir", "_OUTPUT")
    output_dir.mkdir(parents=True, exist_ok=True)

    input_file = Path(args.input) if args.input else extracted_dir / "frage_bloecke.json"
    output_file = Path(args.output) if args.output else output_dir / "blocks_prepared.json"

    if not input_file.exists():
        raise FileNotFoundError(f"Eingabe fehlt: {input_file}")

    blocks = json.loads(input_file.read_text(encoding="utf-8"))
    prepared = prepare_blocks(blocks, max_rag_sources=args.rag_k)

    output_file.write_text(json.dumps(prepared, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ {len(prepared)} Blöcke vorbereitet → {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
