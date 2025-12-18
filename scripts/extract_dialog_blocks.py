#!/usr/bin/env python3
"""
Extrahiert kontextuelle Frage-Blöcke aus den Gold-Standard-Dokumenten.

- Behält lokale Frage-Gruppen (Dialoge) zusammen
- Keine Case-Generierung; es wird nur das genommen, was im Dokument steht
- Unterstützt PDF (pypdf) und DOCX (python-docx)

Output: JSON-Liste von Blöcken mit Kontext und Fragen.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


# Heuristiken
QUESTION_PREFIXES = ("f:", "frage:", "f-", "f ")  # lower-case compare
QUESTION_STARTS = (
    "wie ",
    "was ",
    "welche ",
    "welcher ",
    "welches ",
    "wo ",
    "wann ",
    "woran ",
    "womit ",
    "wovon ",
    "wodurch ",
    "warum ",
    "wer ",
)
ANSWER_PREFIXES = ("a:", "antwort:", "a-")


@dataclass
class Block:
    block_id: str
    source_file: str
    source_page: Optional[int]
    source_tier: str
    context: List[str]
    questions: List[str]


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML not installed. Install with `pip install pyyaml`.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def is_question_line(line: str) -> bool:
    l = line.lower().strip()
    if not l:
        return False
    if any(l.startswith(p) for p in QUESTION_PREFIXES):
        return True
    if "?" in l and (l.startswith(QUESTION_STARTS) or l.startswith("f:") or l.startswith("frage")):
        return True
    # fallback: ends with ? and not an answer
    return l.endswith("?")


def is_answer_line(line: str) -> bool:
    l = line.lower().strip()
    return any(l.startswith(p) for p in ANSWER_PREFIXES)


def iter_pdf_lines(pdf_path: Path):
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        raise RuntimeError("pypdf not installed. Install with `pip install pypdf`.") from None

    reader = PdfReader(str(pdf_path))
    for page_idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        for line in text.splitlines():
            yield page_idx + 1, line


def iter_docx_lines(docx_path: Path):
    try:
        import docx
    except ImportError:  # pragma: no cover
        raise RuntimeError("python-docx not installed. Install with `pip install python-docx`.") from None

    doc = docx.Document(str(docx_path))
    for para in doc.paragraphs:
        yield None, para.text


def extract_blocks_from_lines(
    lines_with_page: List[tuple],
    source_file: str,
    source_tier: str = "gold_standard",
    max_context: int = 6,
) -> List[Block]:
    blocks: List[Block] = []
    context_buffer: List[str] = []
    current_questions: List[str] = []
    current_context_snapshot: List[str] = []
    current_page: Optional[int] = None
    block_counter = 0
    gap_non_question = 0

    for page, raw_line in lines_with_page:
        line = (raw_line or "").strip()
        if not line:
            gap_non_question += 1
            if current_questions and gap_non_question >= 1:
                # end block
                block_counter += 1
                blocks.append(
                    Block(
                        block_id=f"{source_file}__block_{block_counter}",
                        source_file=source_file,
                        source_page=current_page,
                        source_tier=source_tier,
                        context=current_context_snapshot,
                        questions=current_questions,
                    )
                )
                current_questions = []
                current_context_snapshot = []
                current_page = None
            continue

        gap_non_question = 0
        if is_answer_line(line):
            # answers are not part of question list; keep for context buffer
            context_buffer.append(line)
            context_buffer = context_buffer[-max_context:]
            continue

        if is_question_line(line):
            if not current_questions:
                # snapshot context at start of block
                current_context_snapshot = context_buffer[-max_context:]
                current_page = page
            current_questions.append(line)
            continue

        # non-question line: update context buffer; if currently in a block, allow one non-question without closing
        if current_questions:
            # keep as additional context but do not close immediately
            context_buffer.append(line)
            context_buffer = context_buffer[-max_context:]
            continue

        context_buffer.append(line)
        context_buffer = context_buffer[-max_context:]

    # flush last block
    if current_questions:
        block_counter += 1
        blocks.append(
            Block(
                block_id=f"{source_file}__block_{block_counter}",
                source_file=source_file,
                source_page=current_page,
                source_tier=source_tier,
                context=current_context_snapshot,
                questions=current_questions,
            )
        )

    return blocks


def discover_files(gold_dir: Path):
    exts = {".pdf", ".docx"}
    return [p for p in gold_dir.rglob("*") if p.is_file() and p.suffix.lower() in exts]


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrahiere kontextuelle Frage-Blöcke aus Gold-Standard-Dokumenten.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--output", default=None, help="Output JSON (Default: _EXTRACTED_FRAGEN/frage_bloecke.json)")
    parser.add_argument("--max-context", type=int, default=6, help="Anzahl Kontextzeilen, die mitgeführt werden")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    base = Path(args.config).resolve().parent
    gold_dir = base / config.get("gold_dir", "_GOLD_STANDARD")
    extracted_dir = base / config.get("extracted_dir", "_EXTRACTED_FRAGEN")
    extracted_dir.mkdir(parents=True, exist_ok=True)
    output = Path(args.output) if args.output else extracted_dir / "frage_bloecke.json"

    files = discover_files(gold_dir)
    all_blocks: List[Block] = []

    for f in files:
        if f.suffix.lower() == ".pdf":
            try:
                lines = list(iter_pdf_lines(f))
            except Exception as e:
                print(f"⚠️  PDF übersprungen ({f.name}): {e}", file=sys.stderr)
                continue
        else:  # docx
            try:
                lines = list(iter_docx_lines(f))
            except Exception as e:
                print(f"⚠️  DOCX übersprungen ({f.name}): {e}", file=sys.stderr)
                continue

        blocks = extract_blocks_from_lines(
            lines,
            source_file=f.name,
            source_tier="gold_standard",
            max_context=args.max_context,
        )
        all_blocks.extend(blocks)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump([asdict(b) for b in all_blocks], f, ensure_ascii=False, indent=2)

    print(f"✅ {len(all_blocks)} Frage-Blöcke extrahiert")
    print(f"   Quelle: {gold_dir}")
    print(f"   Output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
