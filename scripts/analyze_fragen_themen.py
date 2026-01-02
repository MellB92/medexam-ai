#!/usr/bin/env python3
"""
Phase 1, Schritt 1.3: Extrahierte Fragen analysieren
Extrahiert Themen aus _EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List

# Fachgebiete-Mapping
FACHGEBIETE = {
    'innere_medizin': ['innere', 'kardiologie', 'pneumologie', 'gastroenterologie', 'nephrologie', 'endokrinologie', 'hämatologie'],
    'chirurgie': ['chirurgie', 'unfallchirurgie', 'viszeralchirurgie', 'gefäßchirurgie'],
    'neurologie': ['neurologie', 'neurochirurgie'],
    'gynäkologie': ['gynäkologie', 'geburtshilfe'],
    'anästhesie': ['anästhesie', 'intensivmedizin', 'notfallmedizin'],
    'radiologie': ['radiologie', 'bildgebung', 'röntgen', 'ct', 'mrt', 'sono'],
    'rechtsmedizin': ['rechtsmedizin', 'forensik'],
    'pharmakologie': ['pharmakologie', 'medikamente', 'arzneimittel'],
    'strahlenschutz': ['strahlenschutz', 'dosimetrie', 'kontrollbereich'],
}

# Diagnosen-Patterns
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

# Medikamente-Patterns
MEDIKAMENTE_PATTERNS = [
    r'\bmetformin\b', r'\binsulin\b', r'\badrenalin\b', r'\bnaloxon\b',
    r'\bheparin\b', r'\bass\b', r'\bclopidogrel\b', r'\bwarfarin\b',
    r'\bamoxicillin\b', r'\bcefuroxim\b', r'\bciprofloxacin\b',
    r'\bmorphin\b', r'\bfentanyl\b', r'\bpropofol\b',
    r'\bthiamazol\b', r'\blevothyroxin\b', r'\bprednisolon\b',
    r'\bmethotrexat\b', r'\bmetoprolol\b', r'\bramipril\b',
]

# Verfahren-Patterns
VERFAHREN_PATTERNS = [
    r'röntgen', r'ct', r'mrt', r'sono', r'ultraschall', r'ekg', r'echo',
    r'appendektomie', r'cholezystektomie', r'hernien',
    r'reanimation', r'intubation', r'venenzugang',
    r'blutentnahme', r'labor', r'blutbild',
]


def extract_text_from_question(item: Dict) -> str:
    """Extrahiert Text aus einer Frage."""
    text_parts = []
    
    # Verschiedene mögliche Felder
    for key in ['frage', 'question', 'text', 'content', 'fragen']:
        if key in item:
            val = item[key]
            if isinstance(val, str):
                text_parts.append(val.lower())
            elif isinstance(val, list):
                text_parts.extend([str(v).lower() for v in val])
    
    # Auch aus Antwort extrahieren
    for key in ['antwort', 'answer']:
        if key in item:
            val = item[key]
            if isinstance(val, str):
                text_parts.append(val.lower())
    
    # Context-Feld
    if 'context' in item:
        ctx = item['context']
        if isinstance(ctx, list):
            text_parts.extend([str(c).lower() for c in ctx])
        elif isinstance(ctx, str):
            text_parts.append(ctx.lower())
    
    return ' '.join(text_parts)


def analyze_fragen(fragen_file: Path) -> Dict:
    """Analysiert extrahierte Fragen."""
    print(f"📥 Lade {fragen_file.name}...")
    
    with open(fragen_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Normalisiere zu Liste
    fragen = data if isinstance(data, list) else list(data.values())
    
    print(f"✅ {len(fragen)} Fragen geladen")
    
    stats = {
        'fachgebiete': Counter(),
        'diagnosen': Counter(),
        'medikamente': Counter(),
        'verfahren': Counter(),
        'klassifikationen': Counter(),
        'keywords': Counter(),
        'source_files': Counter(),
    }
    
    # Klassifikationen
    klassifikationen = [
        'garden', 'pauwels', 'ao', 'forrest', 'nyha', 'curb', 'fontaine',
        'gold', 'child-pugh', 'tmn', 'who', 'ecog', 'crb-65',
    ]
    
    print("🔍 Analysiere Fragen...")
    
    for idx, item in enumerate(fragen):
        if not isinstance(item, dict):
            continue
        
        # Fragen können in 'questions' Feld sein (Liste)
        questions_list = item.get('questions', [])
        if not questions_list:
            # Fallback: einzelne Frage
            text = extract_text_from_question(item)
            if text:
                questions_list = [text]
        
        if not questions_list:
            continue
        
        # Source-File
        source = item.get('source_file') or item.get('source') or 'unknown'
        stats['source_files'][source] += len(questions_list)
        
        # Analysiere jede Frage im Block
        for question_text in questions_list:
            if isinstance(question_text, dict):
                text = extract_text_from_question(question_text)
            else:
                text = str(question_text).lower()
            
            # Füge Context hinzu
            context = item.get('context', [])
            if isinstance(context, list):
                context_text = ' '.join([str(c).lower() for c in context])
            else:
                context_text = str(context).lower()
            
            combined_text = f"{text} {context_text}"
        
        # Fachgebiete
        for fach, keywords in FACHGEBIETE.items():
            for keyword in keywords:
                if keyword in text:
                    stats['fachgebiete'][fach] += 1
                    break
        
        # Diagnosen
        for pattern in DIAGNOSEN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                stats['diagnosen'][pattern] += 1
        
        # Medikamente
        for pattern in MEDIKAMENTE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                med_name = pattern.replace(r'\b', '').replace('\\', '')
                stats['medikamente'][med_name] += 1
        
        # Verfahren
        for pattern in VERFAHREN_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                stats['verfahren'][pattern] += 1
        
        # Klassifikationen
        for klass in klassifikationen:
            if re.search(rf'\b{klass}\b', text, re.IGNORECASE):
                stats['klassifikationen'][klass] += 1
        
        # Keywords (häufige medizinische Begriffe)
        keywords_pattern = r'\b(?:diagnose|therapie|symptom|befund|untersuchung|behandlung|indikation|kontraindikation|komplikation|dosis|dosierung|klassifikation|stadium|grad)\b'
        keywords_found = re.findall(keywords_pattern, text, re.IGNORECASE)
        for kw in keywords_found:
            stats['keywords'][kw.lower()] += 1
        
        if (idx + 1) % 1000 == 0:
            print(f"  Verarbeitet: {idx + 1}/{len(fragen)}")
    
    return {
        'fachgebiete': dict(stats['fachgebiete'].most_common(20)),
        'diagnosen': dict(stats['diagnosen'].most_common(30)),
        'medikamente': dict(stats['medikamente'].most_common(30)),
        'verfahren': dict(stats['verfahren'].most_common(20)),
        'klassifikationen': dict(stats['klassifikationen'].most_common(15)),
        'keywords': dict(stats['keywords'].most_common(20)),
        'source_files': dict(stats['source_files'].most_common(20)),
        'statistics': {
            'total_fragen': len(fragen),
            'fachgebiete_count': len(stats['fachgebiete']),
            'diagnosen_count': len(stats['diagnosen']),
            'medikamente_count': len(stats['medikamente']),
            'verfahren_count': len(stats['verfahren']),
        },
    }


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    fragen_file = repo_root / '_EXTRACTED_FRAGEN' / 'frage_bloecke_dedupe_verifiziert.json'
    output_file = repo_root / '_OUTPUT' / 'muenster_themen_fragen.json'
    
    print("🔍 Phase 1, Schritt 1.3: Extrahierte Fragen analysieren\n")
    
    if not fragen_file.exists():
        print(f"❌ Datei nicht gefunden: {fragen_file}")
        return
    
    result = analyze_fragen(fragen_file)
    result['source'] = 'Extrahierte Fragen Analyse'
    
    # Speichere Ergebnis
    print(f"\n💾 Speichere {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ Fragen-Analyse abgeschlossen!")
    print(f"\n📊 Zusammenfassung:")
    print(f"  Gesamt Fragen: {result['statistics']['total_fragen']}")
    print(f"  Fachgebiete: {result['statistics']['fachgebiete_count']}")
    print(f"  Diagnosen: {result['statistics']['diagnosen_count']}")
    print(f"  Medikamente: {result['statistics']['medikamente_count']}")
    print(f"  Verfahren: {result['statistics']['verfahren_count']}")
    
    print(f"\n🔝 Top 5 Fachgebiete:")
    for i, (fach, count) in enumerate(list(result['fachgebiete'].items())[:5], 1):
        print(f"  {i}. {fach}: {count}")
    
    print(f"\n🔝 Top 5 Diagnosen:")
    for i, (diag, count) in enumerate(list(result['diagnosen'].items())[:5], 1):
        print(f"  {i}. {diag}: {count}")


if __name__ == '__main__':
    main()

