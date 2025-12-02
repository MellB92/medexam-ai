#!/usr/bin/env python3
"""
MedExamAI RAG Index Builder
============================

Baut den RAG-Index aus allen Leitlinien-PDFs auf.
Extrahiert Text, chunked, und generiert Embeddings.

Geschätzte Zeit: ~15-20 Min (lokal) oder ~5 Min (OpenAI)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import List, Generator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extrahiert Text aus einem PDF."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("pypdf nicht installiert: pip install pypdf")

    try:
        reader = PdfReader(str(pdf_path))
        text_parts = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(text)
            except Exception:
                continue
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.warning(f"Fehler beim Lesen von {pdf_path.name}: {e}")
        return ""


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100
) -> Generator[str, None, None]:
    """
    Teilt Text in überlappende Chunks.
    """
    if len(text) < chunk_size:
        if text.strip():
            yield text.strip()
        return

    # Split by paragraphs first
    paragraphs = text.split('\n\n')

    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                yield current_chunk.strip()
            current_chunk = para

            # If paragraph itself is too long, split it
            while len(current_chunk) > chunk_size:
                split_point = chunk_size - overlap
                yield current_chunk[:split_point].strip()
                current_chunk = current_chunk[split_point - overlap:]

    if current_chunk.strip():
        yield current_chunk.strip()


def process_leitlinien(
    leitlinien_dir: Path,
    chunk_size: int = 500,
    overlap: int = 100
) -> List[dict]:
    """
    Verarbeitet alle Leitlinien-PDFs und gibt Chunks zurück.
    """
    if not leitlinien_dir.exists():
        logger.error(f"Leitlinien-Verzeichnis nicht gefunden: {leitlinien_dir}")
        return []

    pdf_files = list(leitlinien_dir.rglob("*.pdf"))
    logger.info(f"Gefunden: {len(pdf_files)} Leitlinien-PDFs")

    all_chunks = []

    for i, pdf_path in enumerate(pdf_files, 1):
        rel_path = pdf_path.relative_to(leitlinien_dir)
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else "Allgemein"

        print(f"[{i}/{len(pdf_files)}] {pdf_path.name[:50]}...", end=" ")

        # Extract text
        text = extract_text_from_pdf(pdf_path)
        if not text:
            print("⚠️ Kein Text")
            continue

        # Chunk text
        chunks = list(chunk_text(text, chunk_size, overlap))
        print(f"✅ {len(chunks)} Chunks")

        for chunk in chunks:
            all_chunks.append({
                'text': chunk,
                'source': pdf_path.name,
                'category': category,
                'path': str(rel_path)
            })

    return all_chunks


def build_rag_index(chunks: List[dict], use_openai: bool = False) -> None:
    """
    Baut den RAG-Index aus den Chunks.
    """
    from core.rag_system import get_rag_system

    rag = get_rag_system(use_openai=use_openai)

    print(f"\n📊 Generiere Embeddings für {len(chunks)} Chunks...")
    print(f"   (OpenAI: {use_openai})")

    start_time = time.time()
    added = 0

    # Add in batches
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]

        for chunk in batch:
            texts = [chunk['text']]
            metadata = {
                'source': chunk['source'],
                'category': chunk['category'],
                'path': chunk['path']
            }

            count = rag.add_to_knowledge_base(
                texts=texts,
                source_module="leitlinien",
                source_tier="tier2_bibliothek",
                metadata=metadata
            )
            added += count

        progress = min(i + batch_size, len(chunks))
        elapsed = time.time() - start_time
        eta = (elapsed / progress) * (len(chunks) - progress) if progress > 0 else 0
        print(f"   [{progress}/{len(chunks)}] ETA: {eta:.0f}s")

    print(f"\n✅ {added} Einträge zum RAG-Index hinzugefügt")
    return rag


def main():
    parser = argparse.ArgumentParser(
        description="Baut RAG-Index aus Leitlinien-PDFs"
    )
    parser.add_argument(
        "--leitlinien-dir",
        default="_BIBLIOTHEK/Leitlinien",
        help="Pfad zu Leitlinien"
    )
    parser.add_argument(
        "--additional-dirs",
        nargs="*",
        default=[],
        help="Zusätzliche PDF-Verzeichnisse"
    )
    parser.add_argument(
        "--include-fact-check",
        action="store_true",
        help="Inkludiere _FACT_CHECK_SOURCES (exkl. _unsortiert, Input Bucket)"
    )
    parser.add_argument(
        "--output",
        default="_OUTPUT/rag_knowledge_base.json",
        help="Output-Pfad für Wissensbasis"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Chunk-Größe in Zeichen"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Überlappung zwischen Chunks"
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="OpenAI statt lokale Embeddings nutzen (schneller, kostet $)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    base_dir = Path(__file__).resolve().parent.parent
    leitlinien_dir = base_dir / args.leitlinien_dir

    # Sammle alle zu verarbeitenden Verzeichnisse
    all_dirs = [leitlinien_dir]

    # Zusätzliche Verzeichnisse
    for d in args.additional_dirs:
        all_dirs.append(base_dir / d)

    # Fact Check Sources (gefiltert)
    if args.include_fact_check:
        fcs_root = base_dir / "_FACT_CHECK_SOURCES"
        # Exkludiere unbrauchbare Verzeichnisse
        exclude_dirs = {
            "_unsortiert", "Input Bucket", "sprachkurs",
            "llm_analyse", "kenntnispruefung_admin", "vorklinik"
        }
        if fcs_root.exists():
            for subdir in fcs_root.iterdir():
                if subdir.is_dir() and subdir.name not in exclude_dirs:
                    all_dirs.append(subdir)

    print(f"\n🏗️  MedExamAI RAG Index Builder")
    print(f"   Verzeichnisse: {len(all_dirs)}")
    print(f"   Chunk-Size: {args.chunk_size}")
    print(f"   Overlap: {args.overlap}")

    # Process PDFs from all directories
    all_chunks = []
    for source_dir in all_dirs:
        if source_dir.exists():
            print(f"\n📚 Verarbeite: {source_dir.name}...")
            chunks = process_leitlinien(
                source_dir,
                args.chunk_size,
                args.overlap
            )
            all_chunks.extend(chunks)
            print(f"   → {len(chunks)} Chunks")

    chunks = all_chunks

    if not chunks:
        print("❌ Keine Chunks erstellt")
        return 1

    print(f"\n📊 Gesamt: {len(chunks)} Chunks aus Leitlinien")

    # Build index
    rag = build_rag_index(chunks, use_openai=args.use_openai)

    # Save
    output_path = base_dir / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rag.save_knowledge_base(str(output_path))

    print(f"\n💾 Wissensbasis gespeichert: {output_path}")

    # Stats
    stats = rag.get_statistics()
    print(f"\n📈 Statistiken:")
    print(f"   Einträge gesamt: {stats.get('total_entries', 0)}")
    print(f"   Module: {stats.get('by_module', {})}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
