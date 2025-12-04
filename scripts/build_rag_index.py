#!/usr/bin/env python3
"""
MedExamAI RAG Index Builder
============================

Baut den RAG-Index aus allen Leitlinien-PDFs auf.
Extrahiert Text, chunked, und generiert Embeddings.

Features:
- Checkpoint-Support: Kann bei Unterbrechung fortgesetzt werden
- Inkrementelles Speichern: Speichert nach jeder Datei
- Resume-Funktion: --resume Flag um fortzufahren

Geschätzte Zeit: ~15-20 Min (lokal) oder ~5 Min (OpenAI)
"""

import argparse
import gc
import hashlib
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Generator, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger(__name__)

# Checkpoint-Konfiguration
CHECKPOINT_DIR = Path(__file__).resolve().parent.parent / "_OUTPUT" / "rag_checkpoints"
CHECKPOINT_FILE = CHECKPOINT_DIR / "checkpoint.json"


def load_checkpoint() -> dict:
    """Lädt den letzten Checkpoint."""
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Laden des Checkpoints: {e}")
    return {"processed_files": [], "total_chunks": 0, "last_update": None}


def save_checkpoint(processed_files: List[str], total_chunks: int) -> None:
    """Speichert den aktuellen Checkpoint."""
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "processed_files": processed_files,
        "total_chunks": total_chunks,
        "last_update": datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, indent=2, ensure_ascii=False)


def clear_checkpoint() -> None:
    """Löscht den Checkpoint (für Neustart)."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("  Checkpoint gelöscht.")


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
    overlap: int = 100,
    skip_files: Optional[Set[str]] = None
) -> List[dict]:
    """
    Verarbeitet alle Leitlinien-PDFs und gibt Chunks zurück.

    Args:
        leitlinien_dir: Verzeichnis mit PDFs
        chunk_size: Chunk-Größe
        overlap: Überlappung
        skip_files: Set von bereits verarbeiteten Dateipfaden (für Resume)
    """
    if not leitlinien_dir.exists():
        logger.error(f"Leitlinien-Verzeichnis nicht gefunden: {leitlinien_dir}")
        return []

    skip_files = skip_files or set()
    pdf_files = list(leitlinien_dir.rglob("*.pdf"))
    logger.info(f"Gefunden: {len(pdf_files)} Leitlinien-PDFs")

    all_chunks = []
    skipped = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        rel_path = pdf_path.relative_to(leitlinien_dir)
        file_key = str(pdf_path)
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else "Allgemein"

        # Skip bereits verarbeitete Dateien
        if file_key in skip_files:
            skipped += 1
            continue

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
                'path': str(rel_path),
                '_file_key': file_key  # Für Checkpoint-Tracking
            })

    if skipped > 0:
        print(f"   (Übersprungen: {skipped} bereits verarbeitete Dateien)")

    return all_chunks


def _gather_pdf_files(directories: List[Path]) -> List[Tuple[Path, Path]]:
    """Sammelt alle PDF-Dateien aus den angegebenen Verzeichnissen."""
    pdf_files: List[Tuple[Path, Path]] = []
    for d in directories:
        if not d.exists():
            logger.warning(f"Verzeichnis nicht gefunden und wird übersprungen: {d}")
            continue
        for pdf_path in d.rglob("*.pdf"):
            pdf_files.append((pdf_path, d))

    # Deterministische Reihenfolge
    pdf_files.sort(key=lambda x: str(x[0]))
    return pdf_files


def build_rag_index_streaming(
    rag,
    pdf_files: List[Tuple[Path, Path]],
    skip_files: Set[str],
    output_path: Path,
    chunk_size: int,
    overlap: int,
    save_every: int = 50,
) -> int:
    """
    Baut den RAG-Index inkrementell pro PDF-Datei.
    Speichert häufig Checkpoints und den Embedding-Cache.
    """
    start_time = time.time()
    total_added = 0
    processed_files: Set[str] = set()
    files_since_save = 0
    total_files = len(pdf_files)
    total_to_process = len([pf for pf, _ in pdf_files if str(pf) not in skip_files])

    print(f"\n📊 Generiere Embeddings inkrementell für {total_to_process} aus {total_files} PDFs...")
    print(f"   Checkpoint alle {save_every} Dateien")

    processed_idx = 0
    for idx, (pdf_path, root_dir) in enumerate(pdf_files, 1):
        file_key = str(pdf_path)
        if file_key in skip_files:
            continue

        processed_idx += 1
        rel_path = pdf_path.relative_to(root_dir)
        category = rel_path.parts[0] if len(rel_path.parts) > 1 else root_dir.name

        print(f"[{processed_idx}/{total_to_process}] {pdf_path.name[:60]}...", end=" ")
        try:
            text = extract_text_from_pdf(pdf_path)
            if not text:
                print("⚠️ Kein Text")
                continue

            chunks = list(chunk_text(text, chunk_size, overlap))
            chunk_count = len(chunks)

            if not chunk_count:
                print("⚠️ Keine Chunks")
                continue

            added_here = 0
            for chunk in chunks:
                metadata = {
                    "source": pdf_path.name,
                    "category": category,
                    "path": str(rel_path)
                }
                try:
                    added_here += rag.add_to_knowledge_base(
                        texts=[chunk],
                        source_module="leitlinien",
                        source_tier="tier2_bibliothek",
                        metadata=metadata
                    )
                except Exception as e:  # noqa: BLE001
                    logger.warning(f"Fehler beim Hinzufügen eines Chunks aus {pdf_path.name}: {e}")
                    continue

            total_added += added_here
            processed_files.add(file_key)
            files_since_save += 1
            print(f"✅ {chunk_count} Chunks (+{added_here})")

        except Exception as e:  # noqa: BLE001
            logger.exception(f"Fehler beim Verarbeiten von {pdf_path.name}: {e}")
            continue

        # Checkpoint & Persistenz
        if files_since_save >= save_every:
            all_processed = list(skip_files | processed_files)
            save_checkpoint(all_processed, total_added)
            rag.save_knowledge_base(str(output_path))
            # Embedding-Cache persistieren, damit Embeddings bei Resume nicht neu berechnet werden
            try:
                rag.embedding_cache.save()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Embedding-Cache konnte nicht gespeichert werden: {e}")
            gc.collect()
            elapsed = time.time() - start_time
            print(f"   💾 Checkpoint gespeichert ({len(all_processed)} Dateien, {total_added} Einträge, {elapsed/60:.1f} min)")
            files_since_save = 0

    # Finaler Checkpoint
    if processed_files:
        all_processed = list(skip_files | processed_files)
        save_checkpoint(all_processed, total_added)
        rag.save_knowledge_base(str(output_path))
        try:
            rag.embedding_cache.save()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Embedding-Cache konnte nicht gespeichert werden: {e}")
        gc.collect()
        elapsed = time.time() - start_time
        print(f"   💾 Finaler Checkpoint ({len(all_processed)} Dateien, {total_added} Einträge, {elapsed/60:.1f} min)")

    print(f"\n✅ {total_added} Einträge zum RAG-Index hinzugefügt")
    return total_added


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
        "--device",
        default="auto",
        choices=["auto", "cpu", "mps", "cuda"],
        help="Gerät für lokale Embeddings (auto=SentenceTransformer-Standard)"
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="OpenAI statt lokale Embeddings nutzen (schneller, kostet $)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Fortsetzen vom letzten Checkpoint"
    )
    parser.add_argument(
        "--clear-checkpoint",
        action="store_true",
        help="Checkpoint löschen und von vorne beginnen"
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=50,
        help="Checkpoint nach X verarbeiteten Dateien speichern (default: 50)"
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
    output_path = base_dir / args.output

    # Checkpoint-Handling
    if args.clear_checkpoint:
        clear_checkpoint()
        print("   Checkpoint gelöscht - starte von vorne")

    # Lade Checkpoint wenn --resume
    skip_files: Set[str] = set()
    if args.resume:
        checkpoint = load_checkpoint()
        skip_files = set(checkpoint.get("processed_files", []))
        if skip_files:
            print(f"   ℹ️  Resume-Modus: {len(skip_files)} bereits verarbeitete Dateien übersprungen")
            print(f"   Letzter Checkpoint: {checkpoint.get('last_update', 'unbekannt')}")
        else:
            print("   ℹ️  Kein Checkpoint gefunden - starte von vorne")

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
    print(f"   Checkpoint alle: {args.save_every} Dateien")
    if args.resume:
        print(f"   Resume-Modus: AKTIV")
    print(f"   Device: {args.device}")

    # Alle PDF-Dateien einsammeln (deterministische Reihenfolge)
    pdf_files = _gather_pdf_files(all_dirs)
    if not pdf_files:
        print("❌ Keine PDFs gefunden")
        return 1

    # RAG-System initialisieren (mit Gerät-Konfiguration)
    from core.rag_system import get_rag_system, RAGConfig

    config = RAGConfig()
    config.embedding_device = args.device
    rag = get_rag_system(config=config, use_openai=args.use_openai)

    # Lade bestehende Wissensbasis wenn vorhanden
    if output_path.exists():
        try:
            rag.load_knowledge_base(str(output_path))
            stats = rag.get_statistics()
            print(f"   ℹ️  Bestehende Wissensbasis geladen: {stats.get('total_items', 0)} Einträge")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Konnte bestehende Wissensbasis nicht laden: {e}")

    # Build index mit inkrementellem Processing
    output_path.parent.mkdir(parents=True, exist_ok=True)
    added = build_rag_index_streaming(
        rag=rag,
        pdf_files=pdf_files,
        skip_files=skip_files,
        output_path=output_path,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        save_every=args.save_every
    )

    # Final save (falls nichts zu speichern, no-op)
    rag.save_knowledge_base(str(output_path))
    try:
        rag.embedding_cache.save()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Embedding-Cache konnte nicht gespeichert werden: {e}")
    print(f"\n💾 Wissensbasis gespeichert: {output_path}")

    # Stats
    stats = rag.get_statistics()
    print(f"\n📈 Statistiken:")
    print(f"   Einträge gesamt: {stats.get('total_items', 0)}")
    print(f"   Module: {stats.get('by_module', {})}")

    if added == 0 and skip_files:
        print("\n✅ Alle Dateien waren bereits verarbeitet (Checkpoint)")
    else:
        print(f"\n🎉 RAG-Index erfolgreich erstellt! (+{added} neue Einträge)")
        print(f"   Checkpoint bleibt erhalten für spätere Erweiterungen.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
