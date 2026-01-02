#!/usr/bin/env python3
"""
Phase 1, Schritt 1.4: Anki-Ready TSV analysieren
Extrahiert Tags aus _OUTPUT/anki_ready_20251221_004738.tsv
"""

import csv
import re
from pathlib import Path
from collections import Counter
from typing import Dict

def analyze_anki_tsv(tsv_file: Path) -> Dict:
    """Analysiert Anki-Ready TSV."""
    print(f"📥 Lese {tsv_file.name}...")
    
    result = {
        'tags': Counter(),
        'fachgebiete': Counter(),
        'total_cards': 0,
        'cards_with_tags': 0,
    }
    
    if not tsv_file.exists():
        return result
    
    try:
        with open(tsv_file, 'r', encoding='utf-8') as f:
            # TSV Format: Frage | Antwort | Tags | ...
            reader = csv.reader(f, delimiter='\t')
            
            for row_idx, row in enumerate(reader):
                if not row or len(row) < 3:
                    continue
                
                result['total_cards'] += 1
                
                # Tags sind normalerweise in Spalte 3 (Index 2)
                tags_str = row[2] if len(row) > 2 else ''
                
                if not tags_str:
                    continue
                
                result['cards_with_tags'] += 1
                
                # Parse Tags (Format: "tag1 tag2 tag3" oder "tag1::tag2")
                tags = re.split(r'[\s:]+', tags_str)
                
                for tag in tags:
                    tag = tag.strip()
                    if tag and tag != '':
                        # Entferne häufige Präfixe
                        tag_clean = tag.replace('#', '').replace('Ankizin_v5::', '').replace('Dellas::', '')
                        if tag_clean:
                            result['tags'][tag_clean] += 1
                            
                            # Fachgebiete erkennen
                            tag_lower = tag_clean.lower()
                            if 'innere' in tag_lower or 'kardiologie' in tag_lower:
                                result['fachgebiete']['innere_medizin'] += 1
                            elif 'chirurgie' in tag_lower:
                                result['fachgebiete']['chirurgie'] += 1
                            elif 'neurologie' in tag_lower:
                                result['fachgebiete']['neurologie'] += 1
                            elif 'gynäkologie' in tag_lower or 'gyn' in tag_lower:
                                result['fachgebiete']['gynäkologie'] += 1
                            elif 'pharmakologie' in tag_lower or 'pharm' in tag_lower:
                                result['fachgebiete']['pharmakologie'] += 1
                            elif 'radiologie' in tag_lower or 'röntgen' in tag_lower:
                                result['fachgebiete']['radiologie'] += 1
                            elif 'rechtsmedizin' in tag_lower:
                                result['fachgebiete']['rechtsmedizin'] += 1
                            elif 'strahlenschutz' in tag_lower:
                                result['fachgebiete']['strahlenschutz'] += 1
                            elif 'anästhesie' in tag_lower or 'notfall' in tag_lower:
                                result['fachgebiete']['anästhesie'] += 1
                            elif 'allgemeinmedizin' in tag_lower:
                                result['fachgebiete']['allgemeinmedizin'] += 1
                
                if (row_idx + 1) % 500 == 0:
                    print(f"  Verarbeitet: {row_idx + 1} Zeilen...")
    
    except Exception as e:
        print(f"⚠️  Fehler: {e}")
        import traceback
        traceback.print_exc()
    
    return {
        'tags': dict(result['tags'].most_common(50)),
        'fachgebiete': dict(result['fachgebiete'].most_common(20)),
        'statistics': {
            'total_cards': result['total_cards'],
            'cards_with_tags': result['cards_with_tags'],
            'unique_tags': len(result['tags']),
        },
    }


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    tsv_file = repo_root / '_OUTPUT' / 'anki_ready_20251221_004738.tsv'
    output_file = repo_root / '_OUTPUT' / 'muenster_themen_anki.json'
    
    print("🔍 Phase 1, Schritt 1.4: Anki-Ready TSV analysieren\n")
    
    if not tsv_file.exists():
        print(f"❌ Datei nicht gefunden: {tsv_file}")
        return
    
    result = analyze_anki_tsv(tsv_file)
    result['source'] = 'Anki-Ready TSV Analyse'
    
    # Speichere Ergebnis
    print(f"\n💾 Speichere {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ Anki-TSV Analyse abgeschlossen!")
    print(f"\n📊 Zusammenfassung:")
    print(f"  Gesamt Karten: {result['statistics']['total_cards']}")
    print(f"  Karten mit Tags: {result['statistics']['cards_with_tags']}")
    print(f"  Eindeutige Tags: {result['statistics']['unique_tags']}")
    
    print(f"\n🔝 Top 10 Tags:")
    for i, (tag, count) in enumerate(list(result['tags'].items())[:10], 1):
        print(f"  {i}. {tag}: {count}")
    
    print(f"\n🔝 Fachgebiete:")
    for fach, count in result['fachgebiete'].items():
        print(f"  - {fach}: {count}")


if __name__ == '__main__':
    main()

