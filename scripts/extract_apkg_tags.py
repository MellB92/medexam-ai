#!/usr/bin/env python3
"""
Phase 3: Ankizin/Dellas Tag-Struktur analysieren
Entpackt .apkg Dateien und extrahiert alle Tags aus collection.anki2
"""

import json
import sqlite3
import zipfile
import tempfile
import shutil
from pathlib import Path
from collections import Counter
from typing import Dict, List, Set
import re

def extract_tags_from_anki2(db_path: Path) -> Dict:
    """Extrahiert Tags aus collection.anki2 SQLite-Datenbank."""
    print(f"  Lese {db_path.name}...")
    
    result = {
        'tags': Counter(),
        'total_notes': 0,
        'notes_with_tags': 0,
        'unique_tags': set(),
    }
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Prüfe Tabellen-Struktur
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"    Tabellen gefunden: {', '.join(tables)}")
        
        # Tags aus notes Tabelle extrahieren
        if 'notes' in tables:
            cursor.execute("SELECT COUNT(*) FROM notes")
            result['total_notes'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT tags FROM notes")
            for row in cursor.fetchall():
                tags_str = row[0] if row[0] else ''
                
                if not tags_str:
                    continue
                
                result['notes_with_tags'] += 1
                
                # Parse Tags (Format: "tag1 tag2 tag3" oder "tag1::tag2")
                # Anki speichert Tags als Leerzeichen-getrennte Liste
                tags = tags_str.split()
                
                for tag in tags:
                    tag = tag.strip()
                    if tag:
                        # Entferne mögliche Präfixe
                        tag_clean = tag.replace('#', '')
                        result['tags'][tag_clean] += 1
                        result['unique_tags'].add(tag_clean)
        
        conn.close()
        
    except Exception as e:
        print(f"    ⚠️  Fehler beim Lesen der Datenbank: {e}")
        import traceback
        traceback.print_exc()
    
    return result


def extract_apkg(apkg_path: Path, output_dir: Path) -> Dict:
    """Entpackt .apkg Datei und extrahiert Tags."""
    print(f"\n📦 Entpacke {apkg_path.name}...")
    
    result = {
        'source_file': str(apkg_path),
        'tags': Counter(),
        'total_notes': 0,
        'notes_with_tags': 0,
        'unique_tags': [],
        'media_files': [],
    }
    
    # Temporäres Verzeichnis für Entpackung
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        try:
            # .apkg ist ein ZIP-Archiv
            with zipfile.ZipFile(apkg_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            # Suche collection.anki21 (neueres Format, hat die echten Daten)
            # Fallback auf collection.anki2 falls .anki21 nicht existiert
            anki2_file = temp_path / 'collection.anki21'
            
            if not anki2_file.exists():
                anki2_file = temp_path / 'collection.anki2'
            
            if not anki2_file.exists():
                print(f"    ❌ Keine Anki-Datenbank gefunden")
                return result
            
            print(f"    Verwende: {anki2_file.name}")
            
            # Extrahiere Tags
            tags_data = extract_tags_from_anki2(anki2_file)
            result['tags'] = tags_data['tags']
            result['total_notes'] = tags_data['total_notes']
            result['notes_with_tags'] = tags_data['notes_with_tags']
            result['unique_tags'] = sorted(list(tags_data['unique_tags']))
            
            # Media-Dateien auflisten
            media_dir = temp_path / 'media'
            if media_dir.exists() and media_dir.is_dir():
                result['media_files'] = [f.name for f in media_dir.iterdir() if f.is_file()]
            
        except zipfile.BadZipFile:
            print(f"    ❌ {apkg_path.name} ist keine gültige ZIP-Datei")
        except Exception as e:
            print(f"    ⚠️  Fehler beim Entpacken: {e}")
            import traceback
            traceback.print_exc()
    
    return result


def analyze_tag_hierarchy(tags: List[str]) -> Dict:
    """Analysiert Tag-Hierarchie (z.B. "Innere::Kardiologie")."""
    hierarchy = {
        'root_tags': Counter(),
        'hierarchical_tags': [],
        'depth_stats': Counter(),
    }
    
    for tag in tags:
        # Prüfe auf Hierarchie (:: als Trennzeichen)
        if '::' in tag:
            parts = tag.split('::')
            hierarchy['hierarchical_tags'].append(tag)
            hierarchy['root_tags'][parts[0]] += 1
            hierarchy['depth_stats'][len(parts)] += 1
        else:
            hierarchy['root_tags'][tag] += 1
            hierarchy['depth_stats'][1] += 1
    
    return {
        'root_tags': dict(hierarchy['root_tags'].most_common(30)),
        'hierarchical_count': len(hierarchy['hierarchical_tags']),
        'max_depth': max(hierarchy['depth_stats'].keys()) if hierarchy['depth_stats'] else 0,
        'depth_distribution': dict(hierarchy['depth_stats']),
    }


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    external_decks_dir = repo_root / '_EXTERNAL_DECKS'
    output_dir = repo_root / '_OUTPUT'
    
    print("🔍 Phase 3: Ankizin/Dellas Tag-Struktur analysieren\n")
    
    # Finde .apkg Dateien
    ankizin_apkg = external_decks_dir / 'ankizin' / '2025-06-29-Ankizin_v5_46729-notes_6022_Delete_with_media_fixed.apkg'
    dellas_apkg = external_decks_dir / 'dellas' / '2024-01-20-Dellas_x_Amboss_Pharmakologie_v0_81.apkg'
    
    results = {}
    
    # Ankizin analysieren
    if ankizin_apkg.exists():
        print("1️⃣ Analysiere Ankizin...")
        ankizin_result = extract_apkg(ankizin_apkg, output_dir)
        ankizin_result['hierarchy'] = analyze_tag_hierarchy(ankizin_result['unique_tags'])
        results['ankizin'] = ankizin_result
        
        print(f"✅ Ankizin:")
        print(f"   Total Notes: {ankizin_result['total_notes']}")
        print(f"   Notes mit Tags: {ankizin_result['notes_with_tags']}")
        print(f"   Eindeutige Tags: {len(ankizin_result['unique_tags'])}")
        print(f"   Hierarchische Tags: {ankizin_result['hierarchy']['hierarchical_count']}")
        print(f"   Max Tiefe: {ankizin_result['hierarchy']['max_depth']}")
    else:
        print(f"❌ Ankizin .apkg nicht gefunden: {ankizin_apkg}")
    
    # Dellas analysieren
    if dellas_apkg.exists():
        print("\n2️⃣ Analysiere Dellas...")
        dellas_result = extract_apkg(dellas_apkg, output_dir)
        dellas_result['hierarchy'] = analyze_tag_hierarchy(dellas_result['unique_tags'])
        results['dellas'] = dellas_result
        
        print(f"✅ Dellas:")
        print(f"   Total Notes: {dellas_result['total_notes']}")
        print(f"   Notes mit Tags: {dellas_result['notes_with_tags']}")
        print(f"   Eindeutige Tags: {len(dellas_result['unique_tags'])}")
        print(f"   Hierarchische Tags: {dellas_result['hierarchy']['hierarchical_count']}")
        print(f"   Max Tiefe: {dellas_result['hierarchy']['max_depth']}")
    else:
        print(f"❌ Dellas .apkg nicht gefunden: {dellas_apkg}")
    
    # Speichere Ergebnisse
    print(f"\n💾 Speichere Ergebnisse...")
    
    # Ankizin Tags
    if 'ankizin' in results:
        ankizin_output = output_dir / 'ankizin_alle_tags.json'
        with open(ankizin_output, 'w', encoding='utf-8') as f:
            json.dump({
                'source': 'Ankizin .apkg Analyse',
                'tags': dict(results['ankizin']['tags'].most_common(100)),
                'unique_tags': results['ankizin']['unique_tags'],
                'hierarchy': results['ankizin']['hierarchy'],
                'statistics': {
                    'total_notes': results['ankizin']['total_notes'],
                    'notes_with_tags': results['ankizin']['notes_with_tags'],
                    'unique_tags_count': len(results['ankizin']['unique_tags']),
                },
            }, f, ensure_ascii=False, indent=2)
        print(f"✅ {ankizin_output.name}")
    
    # Dellas Tags
    if 'dellas' in results:
        dellas_output = output_dir / 'dellas_alle_tags.json'
        with open(dellas_output, 'w', encoding='utf-8') as f:
            json.dump({
                'source': 'Dellas .apkg Analyse',
                'tags': dict(results['dellas']['tags'].most_common(100)),
                'unique_tags': results['dellas']['unique_tags'],
                'hierarchy': results['dellas']['hierarchy'],
                'statistics': {
                    'total_notes': results['dellas']['total_notes'],
                    'notes_with_tags': results['dellas']['notes_with_tags'],
                    'unique_tags_count': len(results['dellas']['unique_tags']),
                },
            }, f, ensure_ascii=False, indent=2)
        print(f"✅ {dellas_output.name}")
    
    print("\n✅ Phase 3 abgeschlossen!")
    
    # Zusammenfassung
    if 'ankizin' in results:
        print(f"\n🔝 Top 10 Ankizin Tags:")
        for i, (tag, count) in enumerate(results['ankizin']['tags'].most_common(10), 1):
            print(f"  {i}. {tag}: {count}")
    
    if 'dellas' in results:
        print(f"\n🔝 Top 10 Dellas Tags:")
        for i, (tag, count) in enumerate(results['dellas']['tags'].most_common(10), 1):
            print(f"  {i}. {tag}: {count}")


if __name__ == '__main__':
    main()

