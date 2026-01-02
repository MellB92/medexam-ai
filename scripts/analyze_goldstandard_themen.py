#!/usr/bin/env python3
"""
Phase 1, Schritt 1.1: Gold-Standard analysieren
Extrahiert Themen/Fachgebiete aus _GOLD_STANDARD/ und speichert als JSON.
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Set
import csv

# Medizinische Fachgebiete (deutsch)
FACHGEBIETE = {
    'innere_medizin': ['innere', 'kardiologie', 'pneumologie', 'gastroenterologie', 'nephrologie', 'endokrinologie', 'hämatologie'],
    'chirurgie': ['chirurgie', 'unfallchirurgie', 'viszeralchirurgie', 'gefäßchirurgie', 'thoraxchirurgie'],
    'neurologie': ['neurologie', 'neurochirurgie'],
    'gynäkologie': ['gynäkologie', 'geburtshilfe', 'gynäkologisch'],
    'anästhesie': ['anästhesie', 'intensivmedizin', 'notfallmedizin'],
    'radiologie': ['radiologie', 'bildgebung', 'röntgen', 'ct', 'mrt', 'sono'],
    'rechtsmedizin': ['rechtsmedizin', 'forensik'],
    'pharmakologie': ['pharmakologie', 'medikamente', 'arzneimittel'],
    'strahlenschutz': ['strahlenschutz', 'dosimetrie', 'kontrollbereich'],
    'allgemeinmedizin': ['allgemeinmedizin', 'hausarzt', 'praxis'],
}

# Häufige Diagnosen/Themen aus Münster-Protokollen
DIAGNOSEN_PATTERNS = [
    r'appendizitis', r'cholezystitis', r'pankreatitis', r'divertikulitis',
    r'pneumonie', r'copd', r'lungenembolie', r'pneumothorax',
    r'herzinsuffizienz', r'infarkt', r'angina', r'vorhofflimmern',
    r'diabetes', r'hyperthyreose', r'hypothyreose', r'cushing',
    r'anämie', r'thrombozytopenie', r'leukämie',
    r'fraktur', r'luxation', r'kompartmentsyndrom', r'polytrauma',
    r'meningitis', r'schlaganfall', r'epilepsie',
    r'pyelonephritis', r'nierenversagen', r'nephrotisches_syndrom',
]

# Häufige Verfahren
VERFAHREN_PATTERNS = [
    r'röntgen', r'ct', r'mrt', r'sono', r'ultraschall', r'ekg', r'echo',
    r'appendektomie', r'cholezystektomie', r'hernien',
    r'reanimation', r'intubation', r'venenzugang',
    r'blutentnahme', r'labor', r'blutbild',
]

# Häufige Medikamente
MEDIKAMENTE_PATTERNS = [
    r'metformin', r'insulin', r'adrenalin', r'naloxon',
    r'heparin', r'ass', r'clopidogrel', r'warfarin',
    r'amoxicillin', r'cefuroxim', r'ciprofloxacin',
    r'morphin', r'fentanyl', r'propofol',
    r'thiamazol', r'levothyroxin', r'prednisolon',
]


def extract_from_chunks(chunk_dir: Path) -> Dict[str, Counter]:
    """Extrahiert Themen aus Derived Chunks."""
    stats = {
        'fachgebiete': Counter(),
        'diagnosen': Counter(),
        'verfahren': Counter(),
        'medikamente': Counter(),
        'klassifikationen': Counter(),
    }
    
    # Klassifikationen
    klassifikationen = [
        'garden', 'pauwels', 'ao', 'forrest', 'nyha', 'curb', 'fontaine',
        'gold', 'child-pugh', 'tmn', 'who', 'ecog',
    ]
    
    chunk_files = list(chunk_dir.glob('*.json'))
    print(f"  Analysiere {len(chunk_files)} Chunks...")
    
    for chunk_file in chunk_files[:500]:  # Limit für Performance
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Normalisiere zu Liste
            chunks = data if isinstance(data, list) else [data]
            
            for chunk in chunks:
                # Kombiniere alle Textfelder
                text_fields = []
                for key in ['text', 'title', 'suspected_diagnosis', 'diagnosis', 'chief_complaints']:
                    if key in chunk:
                        val = chunk[key]
                        if isinstance(val, str):
                            text_fields.append(val.lower())
                        elif isinstance(val, list):
                            text_fields.extend([str(v).lower() for v in val])
                
                combined_text = ' '.join(text_fields)
                
                # Fachgebiete
                for fach, keywords in FACHGEBIETE.items():
                    for keyword in keywords:
                        if keyword in combined_text:
                            stats['fachgebiete'][fach] += 1
                            break
                
                # Diagnosen
                for pattern in DIAGNOSEN_PATTERNS:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        stats['diagnosen'][pattern] += 1
                
                # Verfahren
                for pattern in VERFAHREN_PATTERNS:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        stats['verfahren'][pattern] += 1
                
                # Medikamente
                for pattern in MEDIKAMENTE_PATTERNS:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        stats['medikamente'][pattern] += 1
                
                # Klassifikationen
                for klass in klassifikationen:
                    if re.search(rf'\b{klass}\b', combined_text, re.IGNORECASE):
                        stats['klassifikationen'][klass] += 1
                        
        except Exception as e:
            continue
    
    return stats


def extract_from_yield_report(yield_dir: Path) -> Dict[str, Counter]:
    """Extrahiert Themen aus Yield-Report."""
    stats = {
        'topics': Counter(),
        'high_priority': [],
        'medium_priority': [],
        'low_priority': [],
    }
    
    # gap_priority.csv
    gap_file = yield_dir / 'gap_priority.csv'
    if gap_file.exists():
        print(f"  Lese {gap_file.name}...")
        with open(gap_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                topic = row.get('topic', '').strip()
                priority = row.get('priority', '').strip()
                gap = float(row.get('gap', 0))
                
                if topic:
                    stats['topics'][topic] += gap
                    
                    if priority == 'HIGH':
                        stats['high_priority'].append(topic)
                    elif priority == 'MEDIUM':
                        stats['medium_priority'].append(topic)
                    elif priority == 'LOW':
                        stats['low_priority'].append(topic)
    
    return stats


def extract_from_derived_chunks_muenster(muenster_dir: Path) -> Dict[str, Counter]:
    """Extrahiert Themen aus _DERIVED_CHUNKS/KP Münster 2020 -2025/."""
    stats = {
        'themen': Counter(),
        'dateien': [],
    }
    
    if not muenster_dir.exists():
        return stats
    
    print(f"  Analysiere {muenster_dir}...")
    
    # Durchsuche alle Markdown-Dateien
    for md_file in muenster_dir.rglob('*.md'):
        stats['dateien'].append(md_file.name)
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Extrahiere Themen aus Dateinamen und Inhalt
            filename_lower = md_file.stem.lower()
            
            # Fachgebiete aus Dateinamen
            for fach, keywords in FACHGEBIETE.items():
                for keyword in keywords:
                    if keyword in filename_lower:
                        stats['themen'][fach] += 1
                        break
            
            # Diagnosen aus Inhalt
            for pattern in DIAGNOSEN_PATTERNS:
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                if matches > 0:
                    stats['themen'][pattern] += matches
                    
        except Exception as e:
            continue
    
    return stats


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    goldstandard_dir = repo_root / '_GOLD_STANDARD'
    chunk_dir = repo_root / '_DERIVED_CHUNKS' / 'CHUNKS'
    yield_dir = repo_root / '_OUTPUT' / 'yield_muenster_v2'
    muenster_chunks_dir = repo_root / '_DERIVED_CHUNKS' / 'KP Münster 2020 -2025'
    output_file = repo_root / '_OUTPUT' / 'muenster_themen_goldstandard.json'
    
    print("🔍 Phase 1, Schritt 1.1: Gold-Standard analysieren\n")
    
    result = {
        'source': 'Gold-Standard Analyse',
        'timestamp': str(Path(__file__).stat().st_mtime),
        'fachgebiete': {},
        'diagnosen': {},
        'verfahren': {},
        'medikamente': {},
        'klassifikationen': {},
        'topics': {},
        'priorities': {
            'high': [],
            'medium': [],
            'low': [],
        },
        'statistics': {},
    }
    
    # 1. Aus Chunks extrahieren
    print("1️⃣ Extrahiere aus Derived Chunks...")
    chunk_stats = extract_from_chunks(chunk_dir)
    result['fachgebiete'] = dict(chunk_stats['fachgebiete'].most_common(20))
    result['diagnosen'] = dict(chunk_stats['diagnosen'].most_common(30))
    result['verfahren'] = dict(chunk_stats['verfahren'].most_common(20))
    result['medikamente'] = dict(chunk_stats['medikamente'].most_common(20))
    result['klassifikationen'] = dict(chunk_stats['klassifikationen'].most_common(15))
    
    # 2. Aus Yield-Report extrahieren
    print("\n2️⃣ Extrahiere aus Yield-Report...")
    yield_stats = extract_from_yield_report(yield_dir)
    result['topics'] = dict(yield_stats['topics'].most_common(50))
    result['priorities']['high'] = yield_stats['high_priority'][:30]
    result['priorities']['medium'] = yield_stats['medium_priority'][:20]
    result['priorities']['low'] = yield_stats['low_priority'][:10]
    
    # 3. Aus Münster-spezifischen Chunks extrahieren
    print("\n3️⃣ Extrahiere aus KP Münster Chunks...")
    muenster_stats = extract_from_derived_chunks_muenster(muenster_chunks_dir)
    result['muenster_themen'] = dict(muenster_stats['themen'].most_common(30))
    result['muenster_dateien'] = muenster_stats['dateien'][:20]
    
    # Statistik
    result['statistics'] = {
        'fachgebiete_count': len(result['fachgebiete']),
        'diagnosen_count': len(result['diagnosen']),
        'verfahren_count': len(result['verfahren']),
        'medikamente_count': len(result['medikamente']),
        'topics_count': len(result['topics']),
        'high_priority_count': len(result['priorities']['high']),
    }
    
    # Speichere Ergebnis
    print(f"\n💾 Speichere {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ Gold-Standard Analyse abgeschlossen!")
    print(f"\n📊 Zusammenfassung:")
    print(f"  Fachgebiete: {result['statistics']['fachgebiete_count']}")
    print(f"  Diagnosen: {result['statistics']['diagnosen_count']}")
    print(f"  Verfahren: {result['statistics']['verfahren_count']}")
    print(f"  Medikamente: {result['statistics']['medikamente_count']}")
    print(f"  Topics: {result['statistics']['topics_count']}")
    print(f"  HIGH Priority: {result['statistics']['high_priority_count']}")
    
    print(f"\n🔝 Top 5 HIGH Priority Topics:")
    for i, topic in enumerate(result['priorities']['high'][:5], 1):
        print(f"  {i}. {topic}")


if __name__ == '__main__':
    main()

