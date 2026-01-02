#!/usr/bin/env python3
"""
Aufgabe 2 (v2): Gefilterte .apkg erstellen (strenger als v1).

Unterschiede zu v1:
- nutzt `_OUTPUT/*_matched_tags_v2.json`
- schreibt `_OUTPUT/*_KP_Muenster_filtered_v2.apkg`
- Tag-Matching: **exakt** (nicht substring), damit keine False-Positives durch Teilstrings entstehen
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List, Set


def normalize_tag(tag: str) -> str:
    tag = (tag or "").strip()
    tag = tag.replace("#", "")
    return tag.lower()


def clean_tag_prefix(tag: str) -> str:
    # Entferne bekannte Deck-Prefixe (für robustes Matching)
    return (
        tag.replace("Ankizin_v5::", "")
        .replace("Pharmakologie_Dellas_x_AMBOSS_v0.81::", "")
        .replace("Pharmakologie_Dellas_x_AMBOSS_v0.81", "")
        .strip()
    )


def parse_anki_tags(tags_str: str) -> Set[str]:
    """
    notes.tags ist i.d.R. ein String mit space-separierten Tags (Anki speichert oft führende/trailing spaces).
    """
    if not tags_str:
        return set()
    parts = [t for t in tags_str.strip().split() if t.strip()]
    return set(parts)


def extract_media_references(flds: str) -> Set[str]:
    """Extrahiert Media-Referenzen aus Note-Feldern."""
    media_refs = set()

    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    sound_pattern = r"\[sound:([^\]]+)\]"

    for match in re.finditer(img_pattern, flds or ""):
        media_refs.add(match.group(1))
    for match in re.finditer(sound_pattern, flds or ""):
        media_refs.add(match.group(1))

    return media_refs


def filter_notes_by_tags(db_path: Path, include_tags: List[str]) -> Dict:
    """Filtert Notes basierend auf Include-Tags (exakt)."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    include_norm: Set[str] = set()
    for t in include_tags:
        if not t:
            continue
        include_norm.add(normalize_tag(t))
        cleaned = clean_tag_prefix(t)
        if cleaned:
            include_norm.add(normalize_tag(cleaned))

    cursor.execute("SELECT id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data FROM notes")
    all_notes = cursor.fetchall()

    filtered_notes = []
    filtered_note_ids: Set[int] = set()
    all_media_refs: Set[str] = set()

    for note_row in all_notes:
        note_id, guid, mid, mod, usn, tags_str, flds, sfld, csum, flags, data = note_row
        if not tags_str:
            continue

        note_tags = parse_anki_tags(tags_str)
        # normalize for compare
        note_norm = {normalize_tag(t) for t in note_tags}
        note_norm |= {normalize_tag(clean_tag_prefix(t)) for t in note_tags if clean_tag_prefix(t)}

        if note_norm.isdisjoint(include_norm):
            continue

        filtered_notes.append(note_row)
        filtered_note_ids.add(note_id)
        all_media_refs.update(extract_media_references(flds or ""))

    # Cards für gefilterte Notes
    filtered_cards = []
    if filtered_note_ids:
        placeholders = ",".join("?" * len(filtered_note_ids))
        cursor.execute(
            f"SELECT id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data FROM cards WHERE nid IN ({placeholders})",
            list(filtered_note_ids),
        )
        filtered_cards = cursor.fetchall()

    conn.close()

    return {
        "notes": filtered_notes,
        "cards": filtered_cards,
        "note_ids": filtered_note_ids,
        "media_refs": all_media_refs,
    }


def create_filtered_database(original_db: Path, filtered_data: Dict, output_db: Path) -> None:
    """Erstellt gefilterte SQLite-Datenbank."""
    shutil.copy2(original_db, output_db)

    conn = sqlite3.connect(str(output_db))
    cursor = conn.cursor()

    if filtered_data["note_ids"]:
        placeholders = ",".join("?" * len(filtered_data["note_ids"]))
        cursor.execute(f"DELETE FROM notes WHERE id NOT IN ({placeholders})", list(filtered_data["note_ids"]))
        cursor.execute(f"DELETE FROM cards WHERE nid NOT IN ({placeholders})", list(filtered_data["note_ids"]))
    else:
        cursor.execute("DELETE FROM notes")
        cursor.execute("DELETE FROM cards")

    # Revlog cleanup (optional)
    if filtered_data["cards"]:
        card_ids = [card[0] for card in filtered_data["cards"]]
        if card_ids:
            placeholders = ",".join("?" * len(card_ids))
            cursor.execute(f"DELETE FROM revlog WHERE cid NOT IN ({placeholders})", card_ids)

    conn.commit()
    conn.close()

    # VACUUM außerhalb der Transaktion
    conn = sqlite3.connect(str(output_db))
    conn.execute("VACUUM")
    conn.close()


def create_filtered_apkg(source_apkg: Path, matched_tags_file: Path, output_apkg: Path) -> Dict[str, int]:
    """Erstellt gefilterte .apkg Datei."""
    with open(matched_tags_file, "r", encoding="utf-8") as f:
        matched = json.load(f)
    include_tags = matched.get("include_tags", []) or []

    stats = {"notes": 0, "cards": 0}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(source_apkg, "r") as z:
            z.extractall(tmp_path)

        # DB finden
        db = tmp_path / "collection.anki21"
        if not db.exists():
            db = tmp_path / "collection.anki2"
        if not db.exists():
            raise RuntimeError("Keine collection.anki21/anki2 in apkg gefunden.")

        filtered = filter_notes_by_tags(db, include_tags)
        stats["notes"] = len(filtered["notes"])
        stats["cards"] = len(filtered["cards"])
        if stats["notes"] == 0:
            raise RuntimeError("0 Notes nach Filter – prüfen include_tags_v2.")

        filtered_db = tmp_path / "collection_filtered.anki21"
        create_filtered_database(db, filtered, filtered_db)

        # ersetze DB
        if (tmp_path / "collection.anki21").exists():
            (tmp_path / "collection.anki21").unlink()
        shutil.copy2(filtered_db, tmp_path / "collection.anki21")

        # Hinweis: Media-Struktur kann je nach apkg variieren; wir übernehmen alle Files wie v1.
        # (Optionales media-filtering wäre möglich, ist aber riskant ohne Mapping-Datei.)

        # zip neu erstellen
        if output_apkg.exists():
            output_apkg.unlink()
        with zipfile.ZipFile(output_apkg, "w", zipfile.ZIP_DEFLATED) as z_out:
            for fp in tmp_path.rglob("*"):
                if fp.is_file():
                    arc = fp.relative_to(tmp_path)
                    # skip old .anki2 if .anki21 exists
                    if arc.name == "collection.anki2" and (tmp_path / "collection.anki21").exists():
                        continue
                    z_out.write(fp, arc)

    return stats


def main() -> None:
    repo_root = Path(__file__).parent.parent
    ext = repo_root / "_EXTERNAL_DECKS"
    out = repo_root / "_OUTPUT"

    ank_apkg = ext / "ankizin" / "2025-06-29-Ankizin_v5_46729-notes_6022_Delete_with_media_fixed.apkg"
    del_apkg = ext / "dellas" / "2024-01-20-Dellas_x_Amboss_Pharmakologie_v0_81.apkg"

    ank_tags = out / "ankizin_matched_tags_v2.json"
    del_tags = out / "dellas_matched_tags_v2.json"

    ank_out = out / "Ankizin_KP_Muenster_filtered_v2.apkg"
    del_out = out / "Dellas_KP_Muenster_filtered_v2.apkg"

    print("📦 Erstelle v2 gefilterte Decks...")

    if ank_apkg.exists() and ank_tags.exists():
        s = create_filtered_apkg(ank_apkg, ank_tags, ank_out)
        print(f"✅ Ankizin v2: {ank_out.name} | notes={s['notes']} | cards={s['cards']} | size={ank_out.stat().st_size/1024/1024:.2f} MB")
    else:
        print("❌ Ankizin Inputs fehlen.")

    if del_apkg.exists() and del_tags.exists():
        s = create_filtered_apkg(del_apkg, del_tags, del_out)
        print(f"✅ Dellas v2: {del_out.name} | notes={s['notes']} | cards={s['cards']} | size={del_out.stat().st_size/1024/1024:.2f} MB")
    else:
        print("❌ Dellas Inputs fehlen.")


if __name__ == "__main__":
    main()


