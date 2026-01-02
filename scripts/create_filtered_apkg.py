#!/usr/bin/env python3
"""
Phase 5: Gefilterte .apkg erstellen
Extrahiert nur Karten mit gematchten Tags und erstellt neue .apkg Dateien
"""

import json
import sqlite3
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Set, Dict, List
import re

def extract_media_references(flds: str) -> Set[str]:
    """Extrahiert Media-Referenzen aus Note-Feldern."""
    media_refs = set()
    
    # Anki Media-Format: <img src="filename.jpg"> oder [sound:filename.mp3]
    img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
    sound_pattern = r'\[sound:([^\]]+)\]'
    
    for match in re.finditer(img_pattern, flds):
        media_refs.add(match.group(1))
    
    for match in re.finditer(sound_pattern, flds):
        media_refs.add(match.group(1))
    
    return media_refs


def filter_notes_by_tags(db_path: Path, include_tags: List[str], deck_name: str) -> Dict:
    """Filtert Notes basierend auf Include-Tags."""
    print(f"  Filtere Notes in {db_path.name}...")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Normalisiere Include-Tags für Matching
    include_tags_normalized = set()
    for tag in include_tags:
        # Entferne Präfixe für Matching
        tag_clean = tag.replace('#', '').replace('Ankizin_v5::', '').replace('Pharmakologie_Dellas_x_AMBOSS_v0.81::', '')
        include_tags_normalized.add(tag_clean.lower())
        # Auch vollständiger Tag
        include_tags_normalized.add(tag.lower())
    
    # Hole alle Notes mit Tags
    cursor.execute("SELECT id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data FROM notes")
    all_notes = cursor.fetchall()
    
    print(f"    Total Notes: {len(all_notes)}")
    
    filtered_notes = []
    filtered_note_ids = set()
    all_media_refs = set()
    
    for note_row in all_notes:
        note_id, guid, mid, mod, usn, tags_str, flds, sfld, csum, flags, data = note_row
        
        if not tags_str:
            continue
        
        # Prüfe ob einer der Include-Tags im Tags-String vorkommt
        tags_lower = tags_str.lower()
        matched = False
        
        for include_tag in include_tags_normalized:
            if include_tag in tags_lower:
                matched = True
                break
        
        if matched:
            filtered_notes.append(note_row)
            filtered_note_ids.add(note_id)
            
            # Extrahiere Media-Referenzen
            if flds:
                media_refs = extract_media_references(flds)
                all_media_refs.update(media_refs)
    
    print(f"    Gefilterte Notes: {len(filtered_notes)}")
    print(f"    Media-Referenzen: {len(all_media_refs)}")
    
    # Hole Cards für gefilterte Notes
    cursor.execute("SELECT id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data FROM cards WHERE nid IN ({})".format(','.join('?' * len(filtered_note_ids))), list(filtered_note_ids))
    filtered_cards = cursor.fetchall()
    
    print(f"    Gefilterte Cards: {len(filtered_cards)}")
    
    conn.close()
    
    return {
        'notes': filtered_notes,
        'cards': filtered_cards,
        'note_ids': filtered_note_ids,
        'media_refs': all_media_refs,
    }


def create_filtered_database(original_db: Path, filtered_data: Dict, output_db: Path):
    """Erstellt gefilterte SQLite-Datenbank."""
    print(f"  Erstelle gefilterte Datenbank: {output_db.name}...")
    
    # Kopiere Original-Datenbank
    shutil.copy2(original_db, output_db)
    
    conn = sqlite3.connect(str(output_db))
    cursor = conn.cursor()
    
    # Lösche alle Notes die nicht gefiltert wurden
    if filtered_data['note_ids']:
        placeholders = ','.join('?' * len(filtered_data['note_ids']))
        cursor.execute(f"DELETE FROM notes WHERE id NOT IN ({placeholders})", list(filtered_data['note_ids']))
    else:
        cursor.execute("DELETE FROM notes")
    
    deleted_notes = cursor.rowcount
    print(f"    Gelöschte Notes: {deleted_notes}")
    
    # Lösche Cards die nicht zu gefilterten Notes gehören
    if filtered_data['note_ids']:
        placeholders = ','.join('?' * len(filtered_data['note_ids']))
        cursor.execute(f"DELETE FROM cards WHERE nid NOT IN ({placeholders})", list(filtered_data['note_ids']))
    else:
        cursor.execute("DELETE FROM cards")
    
    deleted_cards = cursor.rowcount
    print(f"    Gelöschte Cards: {deleted_cards}")
    
    # Lösche Revlog-Einträge für gelöschte Cards
    if filtered_data['cards']:
        card_ids = [card[0] for card in filtered_data['cards']]
        if card_ids:
            placeholders = ','.join('?' * len(card_ids))
            cursor.execute(f"DELETE FROM revlog WHERE cid NOT IN ({placeholders})", card_ids)
    
    conn.commit()
    conn.close()
    
    # VACUUM muss außerhalb der Transaktion ausgeführt werden
    conn = sqlite3.connect(str(output_db))
    cursor = conn.cursor()
    cursor.execute("VACUUM")
    conn.close()
    
    print(f"    ✅ Gefilterte DB erstellt ({output_db.stat().st_size / 1024 / 1024:.2f} MB)")


def create_filtered_apkg(source_apkg: Path, matched_tags_file: Path, output_apkg: Path, deck_name: str):
    """Erstellt gefilterte .apkg Datei."""
    print(f"\n📦 Erstelle gefilterte .apkg: {output_apkg.name}")
    
    # Lade Matched Tags
    with open(matched_tags_file, 'r', encoding='utf-8') as f:
        matched_data = json.load(f)
    
    include_tags = matched_data.get('include_tags', [])
    print(f"  Include-Tags: {len(include_tags)}")
    
    # Temporäres Verzeichnis
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Entpacke Original .apkg
        print(f"  Entpacke {source_apkg.name}...")
        with zipfile.ZipFile(source_apkg, 'r') as zip_ref:
            zip_ref.extractall(temp_path)
        
        # Finde Datenbank
        anki2_file = temp_path / 'collection.anki21'
        if not anki2_file.exists():
            anki2_file = temp_path / 'collection.anki2'
        
        if not anki2_file.exists():
            print(f"  ❌ Keine Datenbank gefunden!")
            return
        
        # Filtere Notes
        filtered_data = filter_notes_by_tags(anki2_file, include_tags, deck_name)
        
        if not filtered_data['notes']:
            print(f"  ⚠️  Keine Notes gefunden - überspringe")
            return
        
        # Erstelle gefilterte Datenbank
        filtered_db = temp_path / 'collection_filtered.anki21'
        create_filtered_database(anki2_file, filtered_data, filtered_db)
        
        # Kopiere gefilterte DB zurück
        if anki2_file.name == 'collection.anki21':
            anki2_file.unlink()
            shutil.copy2(filtered_db, anki2_file)
        else:
            # Erstelle .anki21 falls nur .anki2 vorhanden
            anki21_file = temp_path / 'collection.anki21'
            shutil.copy2(filtered_db, anki21_file)
        
        # Filtere Media-Dateien
        media_dir = temp_path / 'media'
        if media_dir.exists() and media_dir.is_dir():
            media_refs = filtered_data['media_refs']
            if media_refs:
                print(f"  Filtere Media-Dateien ({len(media_refs)} Referenzen)...")
                
                # Erstelle temporären Media-Ordner
                filtered_media_dir = temp_path / 'media_filtered'
                filtered_media_dir.mkdir()
                
                copied_count = 0
                for media_file in media_dir.iterdir():
                    if media_file.is_file() and media_file.name in media_refs:
                        shutil.copy2(media_file, filtered_media_dir / media_file.name)
                        copied_count += 1
                
                # Ersetze Media-Ordner
                shutil.rmtree(media_dir)
                filtered_media_dir.rename(media_dir)
                
                print(f"    Kopierte Media-Dateien: {copied_count}")
        
        # Erstelle neue .apkg
        print(f"  Erstelle {output_apkg.name}...")
        with zipfile.ZipFile(output_apkg, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            # Füge alle Dateien hinzu (außer der alten DB falls vorhanden)
            for file_path in temp_path.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to(temp_path)
                    # Überspringe alte .anki2 falls .anki21 vorhanden
                    if arc_name.name == 'collection.anki2' and (temp_path / 'collection.anki21').exists():
                        continue
                    zip_out.write(file_path, arc_name)
        
        print(f"  ✅ {output_apkg.name} erstellt ({output_apkg.stat().st_size / 1024 / 1024:.2f} MB)")


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    external_decks_dir = repo_root / '_EXTERNAL_DECKS'
    output_dir = repo_root / '_OUTPUT'
    
    print("🔍 Phase 5: Gefilterte .apkg erstellen\n")
    
    # Ankizin
    ankizin_apkg = external_decks_dir / 'ankizin' / '2025-06-29-Ankizin_v5_46729-notes_6022_Delete_with_media_fixed.apkg'
    ankizin_matched = output_dir / 'ankizin_matched_tags.json'
    ankizin_output = output_dir / 'Ankizin_KP_Muenster_filtered.apkg'
    
    if ankizin_apkg.exists() and ankizin_matched.exists():
        create_filtered_apkg(ankizin_apkg, ankizin_matched, ankizin_output, 'ankizin')
    else:
        print(f"❌ Ankizin: Dateien nicht gefunden")
    
    # Dellas
    dellas_apkg = external_decks_dir / 'dellas' / '2024-01-20-Dellas_x_Amboss_Pharmakologie_v0_81.apkg'
    dellas_matched = output_dir / 'dellas_matched_tags.json'
    dellas_output = output_dir / 'Dellas_KP_Muenster_filtered.apkg'
    
    if dellas_apkg.exists() and dellas_matched.exists():
        create_filtered_apkg(dellas_apkg, dellas_matched, dellas_output, 'dellas')
    else:
        print(f"❌ Dellas: Dateien nicht gefunden")
    
    print("\n✅ Phase 5 abgeschlossen!")
    
    # Statistik
    if ankizin_output.exists():
        print(f"\n📊 Ankizin gefiltert:")
        print(f"  Original: {ankizin_apkg.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"  Gefiltert: {ankizin_output.stat().st_size / 1024 / 1024:.2f} MB")
        reduction = (1 - ankizin_output.stat().st_size / ankizin_apkg.stat().st_size) * 100
        print(f"  Reduktion: {reduction:.1f}%")
    
    if dellas_output.exists():
        print(f"\n📊 Dellas gefiltert:")
        print(f"  Original: {dellas_apkg.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"  Gefiltert: {dellas_output.stat().st_size / 1024 / 1024:.2f} MB")
        reduction = (1 - dellas_output.stat().st_size / dellas_apkg.stat().st_size) * 100
        print(f"  Reduktion: {reduction:.1f}%")


if __name__ == '__main__':
    main()

