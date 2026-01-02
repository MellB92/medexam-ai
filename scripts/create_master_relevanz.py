#!/usr/bin/env python3
"""
Phase 2: Konsolidierte Themenliste erstellen
Kombiniert alle Ergebnisse aus Phase 1 zu muenster_relevanz_master.json
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set

def load_phase1_results(repo_root: Path) -> Dict:
    """Lädt alle Phase-1-Ergebnisse."""
    results = {}
    
    files = {
        'goldstandard': '_OUTPUT/muenster_themen_goldstandard.json',
        'yield': '_OUTPUT/muenster_themen_yield.json',
        'fragen': '_OUTPUT/muenster_themen_fragen.json',
        'anki': '_OUTPUT/muenster_themen_anki.json',
    }
    
    for name, file_path in files.items():
        full_path = repo_root / file_path
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                results[name] = json.load(f)
        else:
            print(f"⚠️  {name}: Datei nicht gefunden")
    
    return results


def consolidate_topics(data: Dict) -> Dict:
    """Konsolidiert Themen aus allen Quellen."""
    master = {
        'high_priority': [],
        'medium_priority': [],
        'low_priority': [],
        'keywords': [],
        'diagnosen': [],
        'medikamente': [],
        'verfahren': [],
        'fachgebiete': [],
        'klassifikationen': [],
    }
    
    # HIGH Priority aus Yield-Report
    if 'yield' in data and 'gap_priority' in data['yield']:
        yield_data = data['yield']['gap_priority']
        master['high_priority'] = yield_data.get('high_priority', [])[:50]
        master['medium_priority'] = yield_data.get('medium_priority', [])[:30]
        master['low_priority'] = yield_data.get('low_priority', [])[:20]
    
    # Keywords aus allen Quellen
    keywords_counter = Counter()
    
    # Aus Gold-Standard
    if 'goldstandard' in data:
        gs = data['goldstandard']
        if 'topics' in gs:
            for topic, count in gs['topics'].items():
                keywords_counter[topic] += count
    
    # Aus Yield-Report Topics
    if 'yield' in data and 'gap_priority' in data['yield']:
        yield_topics = data['yield']['gap_priority'].get('topics', {})
        for topic, info in yield_topics.items():
            if isinstance(info, dict):
                keywords_counter[topic] += info.get('gap', 0)
            else:
                keywords_counter[topic] += info
    
    master['keywords'] = [kw for kw, _ in keywords_counter.most_common(100)]
    
    # Diagnosen konsolidieren
    diagnosen_counter = Counter()
    
    if 'goldstandard' in data and 'diagnosen' in data['goldstandard']:
        for diag, count in data['goldstandard']['diagnosen'].items():
            diagnosen_counter[diag] += count
    
    if 'fragen' in data and 'diagnosen' in data['fragen']:
        for diag, count in data['fragen']['diagnosen'].items():
            diagnosen_counter[diag] += count
    
    master['diagnosen'] = [diag for diag, _ in diagnosen_counter.most_common(50)]
    
    # Medikamente konsolidieren
    medikamente_counter = Counter()
    
    if 'goldstandard' in data and 'medikamente' in data['goldstandard']:
        for med, count in data['goldstandard']['medikamente'].items():
            medikamente_counter[med] += count
    
    if 'fragen' in data and 'medikamente' in data['fragen']:
        for med, count in data['fragen']['medikamente'].items():
            medikamente_counter[med] += count
    
    master['medikamente'] = [med for med, _ in medikamente_counter.most_common(30)]
    
    # Verfahren konsolidieren
    verfahren_counter = Counter()
    
    if 'goldstandard' in data and 'verfahren' in data['goldstandard']:
        for verf, count in data['goldstandard']['verfahren'].items():
            verfahren_counter[verf] += count
    
    if 'fragen' in data and 'verfahren' in data['fragen']:
        for verf, count in data['fragen']['verfahren'].items():
            verfahren_counter[verf] += count
    
    master['verfahren'] = [verf for verf, _ in verfahren_counter.most_common(30)]
    
    # Fachgebiete konsolidieren
    fachgebiete_counter = Counter()
    
    if 'goldstandard' in data and 'fachgebiete' in data['goldstandard']:
        for fach, count in data['goldstandard']['fachgebiete'].items():
            fachgebiete_counter[fach] += count
    
    if 'fragen' in data and 'fachgebiete' in data['fragen']:
        for fach, count in data['fragen']['fachgebiete'].items():
            fachgebiete_counter[fach] += count
    
    if 'anki' in data and 'fachgebiete' in data['anki']:
        for fach, count in data['anki']['fachgebiete'].items():
            fachgebiete_counter[fach] += count
    
    master['fachgebiete'] = [fach for fach, _ in fachgebiete_counter.most_common(15)]
    
    # Klassifikationen
    klass_counter = Counter()
    
    if 'goldstandard' in data and 'klassifikationen' in data['goldstandard']:
        for klass, count in data['goldstandard']['klassifikationen'].items():
            klass_counter[klass] += count
    
    master['klassifikationen'] = [klass for klass, _ in klass_counter.most_common(15)]
    
    return master


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    output_file = repo_root / '_OUTPUT' / 'muenster_relevanz_master.json'
    
    print("🔍 Phase 2: Konsolidierte Themenliste erstellen\n")
    
    # Lade Phase-1-Ergebnisse
    print("📥 Lade Phase-1-Ergebnisse...")
    data = load_phase1_results(repo_root)
    
    print(f"✅ {len(data)} Quellen geladen")
    
    # Konsolidiere
    print("\n🔄 Konsolidiere Themen...")
    master = consolidate_topics(data)
    
    # Füge Metadaten hinzu
    master['metadata'] = {
        'sources': list(data.keys()),
        'high_priority_count': len(master['high_priority']),
        'medium_priority_count': len(master['medium_priority']),
        'low_priority_count': len(master['low_priority']),
        'keywords_count': len(master['keywords']),
        'diagnosen_count': len(master['diagnosen']),
        'medikamente_count': len(master['medikamente']),
        'verfahren_count': len(master['verfahren']),
        'fachgebiete_count': len(master['fachgebiete']),
        'klassifikationen_count': len(master['klassifikationen']),
    }
    
    # Speichere
    print(f"\n💾 Speichere {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master, f, ensure_ascii=False, indent=2)
    
    print("✅ Konsolidierung abgeschlossen!")
    print(f"\n📊 Zusammenfassung:")
    print(f"  HIGH Priority: {master['metadata']['high_priority_count']}")
    print(f"  MEDIUM Priority: {master['metadata']['medium_priority_count']}")
    print(f"  LOW Priority: {master['metadata']['low_priority_count']}")
    print(f"  Keywords: {master['metadata']['keywords_count']}")
    print(f"  Diagnosen: {master['metadata']['diagnosen_count']}")
    print(f"  Medikamente: {master['metadata']['medikamente_count']}")
    print(f"  Verfahren: {master['metadata']['verfahren_count']}")
    print(f"  Fachgebiete: {master['metadata']['fachgebiete_count']}")
    print(f"  Klassifikationen: {master['metadata']['klassifikationen_count']}")
    
    print(f"\n🔝 Top 10 HIGH Priority Topics:")
    for i, topic in enumerate(master['high_priority'][:10], 1):
        print(f"  {i}. {topic}")
    
    print(f"\n🔝 Top 5 Fachgebiete:")
    for i, fach in enumerate(master['fachgebiete'][:5], 1):
        print(f"  {i}. {fach}")


if __name__ == '__main__':
    main()

