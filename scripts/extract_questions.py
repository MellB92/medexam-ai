#!/usr/bin/env python3
"""
Extracts *real* exam questions from Gold-Standard documents.
- No case hallucination
- Only lines/sentences that contain a literal question mark and start with typical interrogatives
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

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


@dataclass
class Question:
    frage: str
    source_file: str
    source_page: Optional[int]
    source_tier: str = "gold_standard"

    def asdict(self) -> dict:
        return {
            "frage": self.frage,
            "source_file": self.source_file,
            "source_page": self.source_page,
            "source_tier": self.source_tier,
        }


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    if yaml is None:
        raise RuntimeError("PyYAML not installed. Install with `pip install pyyaml`.")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def extract_from_pdf(pdf_path: Path) -> Iterable[Question]:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover
        raise RuntimeError("pypdf not installed. Install with `pip install pypdf`.") from None

    reader = PdfReader(str(pdf_path))
    for idx, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if not text.strip():
            continue
        yield from _extract_questions_from_text(text, pdf_path.name, page_number=idx + 1)


def extract_from_docx(docx_path: Path) -> Iterable[Question]:
    try:
        import docx
    except ImportError:  # pragma: no cover
        raise RuntimeError("python-docx not installed. Install with `pip install python-docx`.") from None

    doc = docx.Document(str(docx_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text]
    text = "\n".join(paragraphs)
    yield from _extract_questions_from_text(text, docx_path.name, page_number=None)


def _extract_questions_from_text(text: str, source_file: str, page_number: Optional[int]) -> Iterable[Question]:
    # Normalize whitespace
    cleaned = re.sub(r"[ \t]+", " ", text)
    # Split on question marks to avoid runaway spans
    chunks = cleaned.split("?")

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        # Re-attach question mark for storage
        candidate = f"{chunk}?"
        lower = candidate.lower()
        if not lower.startswith(QUESTION_STARTS):
            continue
        if len(candidate) < 8:  # too short to be meaningful
            continue
        yield Question(frage=candidate, source_file=source_file, source_page=page_number)


def discover_files(gold_dir: Path) -> List[Path]:
    exts = {".pdf", ".docx", ".txt"}
    files: List[Path] = []
    for p in gold_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract literal exam questions from Gold-Standard documents.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    parser.add_argument("--output", default=None, help="Output JSON path. Default: _EXTRACTED_FRAGEN/echte_fragen.json")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    base = Path(args.config).resolve().parent

    gold_dir = base / config.get("gold_dir", "_GOLD_STANDARD")
    extracted_dir = base / config.get("extracted_dir", "_EXTRACTED_FRAGEN")
    extracted_dir.mkdir(parents=True, exist_ok=True)
    output = Path(args.output) if args.output else extracted_dir / "echte_fragen.json"

    files = discover_files(gold_dir)
    questions: List[Question] = []
    seen = set()

    for f in files:
        if f.suffix.lower() == ".pdf":
            extractor = extract_from_pdf
        elif f.suffix.lower() == ".docx":
            extractor = extract_from_docx
        else:
            # Simple txt reader
            text = f.read_text(encoding="utf-8", errors="ignore")
            for q in _extract_questions_from_text(text, f.name, page_number=None):
                key = (q.frage, q.source_file, q.source_page)
                if key not in seen:
                    seen.add(key)
                    questions.append(q)
            continue

        try:
            for q in extractor(f):
                key = (q.frage, q.source_file, q.source_page)
                if key in seen:
                    continue
                seen.add(key)
                questions.append(q)
        except Exception as e:
            print(f"⚠️  Fehler bei {f}: {e}", file=sys.stderr)
            continue

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump([q.asdict() for q in questions], f, ensure_ascii=False, indent=2)

    print(f"✅ {len(questions)} Fragen extrahiert")
    print(f"   Quelle: {gold_dir}")
    print(f"   Output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
