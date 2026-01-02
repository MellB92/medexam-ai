#!/usr/bin/env python3
"""
Phase 1, Schritt 1.2: Yield-Report analysieren
Extrahiert Themen aus _OUTPUT/yield_muenster_v2/
"""

import json
import csv
import re
from pathlib import Path
from collections import Counter
from typing import Dict, List

def analyze_gap_priority(gap_file: Path) -> Dict:
    """Analysiert gap_priority.csv"""
    result = {
        'topics': {},
        'high_priority': [],
        'medium_priority': [],
        'low_priority': [],
        'statistics': {},
    }
    
    if not gap_file.exists():
        return result
    
    print(f"  Lese {gap_file.name}...")
    topics_by_priority = {'HIGH': [], 'MEDIUM': [], 'LOW': []}
    
    with open(gap_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            topic = row.get('topic', '').strip()
            priority = row.get('priority', '').strip()
            asked_score = float(row.get('asked_score', 0))
            coverage_score = float(row.get('coverage_score', 0))
            gap = float(row.get('gap', 0))
            
            if topic:
                result['topics'][topic] = {
                    'asked_score': asked_score,
                    'coverage_score': coverage_score,
                    'gap': gap,
                    'priority': priority,
                }
                
                topics_by_priority[priority].append({
                    'topic': topic,
                    'gap': gap,
                    'asked_score': asked_score,
                })
    
    # Sortiere nach Gap (absteigend)
    for priority in ['HIGH', 'MEDIUM', 'LOW']:
        topics_by_priority[priority].sort(key=lambda x: x['gap'], reverse=True)
        result[f'{priority.lower()}_priority'] = [
            t['topic'] for t in topics_by_priority[priority]
        ]
    
    result['statistics'] = {
        'total_topics': len(result['topics']),
        'high_count': len(result['high_priority']),
        'medium_count': len(result['medium_priority']),
        'low_count': len(result['low_priority']),
    }
    
    return result


def analyze_report_md(report_file: Path) -> Dict:
    """Analysiert report_muenster_yield.md"""
    result = {
        'fächer': [],
        'themen': [],
        'zitate': [],
    }
    
    if not report_file.exists():
        return result
    
    print(f"  Lese {report_file.name}...")
    
    try:
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extrahiere Fächer/Themen aus Überschriften
        fächer_pattern = r'^##+\s+(.+?)$'
        for match in re.finditer(fächer_pattern, content, re.MULTILINE):
            fach = match.group(1).strip()
            if fach and len(fach) < 100:  # Filtere zu lange Zeilen
                result['fächer'].append(fach)
        
        # Extrahiere Themen aus Listen
        themen_pattern = r'[-*]\s+(.+?)(?:\n|$)'
        for match in re.finditer(themen_pattern, content, re.MULTILINE):
            thema = match.group(1).strip()
            if thema and len(thema) < 200:
                result['themen'].append(thema)
        
        # Dedupliziere
        result['fächer'] = list(set(result['fächer']))[:30]
        result['themen'] = list(set(result['themen']))[:50]
        
    except Exception as e:
        print(f"  ⚠️  Fehler: {e}")
    
    return result


def analyze_learning_checklist(checklist_file: Path) -> Dict:
    """Analysiert learning_checklist_from_gaps.txt"""
    result = {
        'themen': [],
        'kategorien': {},
    }
    
    if not checklist_file.exists():
        return result
    
    print(f"  Lese {checklist_file.name}...")
    
    try:
        with open(checklist_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_category = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Kategorie erkennen (Überschrift)
            if line.startswith('#') or line.startswith('##'):
                current_category = line.lstrip('#').strip()
                if current_category:
                    result['kategorien'][current_category] = []
            elif current_category and line.startswith('-'):
                thema = line.lstrip('-').strip()
                if thema:
                    result['themen'].append(thema)
                    result['kategorien'][current_category].append(thema)
        
    except Exception as e:
        print(f"  ⚠️  Fehler: {e}")
    
    return result


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    yield_dir = repo_root / '_OUTPUT' / 'yield_muenster_v2'
    output_file = repo_root / '_OUTPUT' / 'muenster_themen_yield.json'
    
    print("🔍 Phase 1, Schritt 1.2: Yield-Report analysieren\n")
    
    result = {
        'source': 'Yield-Report Analyse',
        'gap_priority': {},
        'report_md': {},
        'learning_checklist': {},
        'statistics': {},
    }
    
    # 1. gap_priority.csv
    print("1️⃣ Analysiere gap_priority.csv...")
    gap_file = yield_dir / 'gap_priority.csv'
    result['gap_priority'] = analyze_gap_priority(gap_file)
    
    # 2. report_muenster_yield.md
    print("\n2️⃣ Analysiere report_muenster_yield.md...")
    report_file = yield_dir / 'report_muenster_yield.md'
    result['report_md'] = analyze_report_md(report_file)
    
    # 3. learning_checklist_from_gaps.txt
    print("\n3️⃣ Analysiere learning_checklist_from_gaps.txt...")
    checklist_file = yield_dir / 'learning_checklist_from_gaps.txt'
    result['learning_checklist'] = analyze_learning_checklist(checklist_file)
    
    # Statistik
    result['statistics'] = {
        'gap_priority_topics': result['gap_priority']['statistics']['total_topics'],
        'gap_priority_high': result['gap_priority']['statistics']['high_count'],
        'report_fächer': len(result['report_md']['fächer']),
        'report_themen': len(result['report_md']['themen']),
        'checklist_themen': len(result['learning_checklist']['themen']),
        'checklist_kategorien': len(result['learning_checklist']['kategorien']),
    }
    
    # Speichere Ergebnis
    print(f"\n💾 Speichere {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ Yield-Report Analyse abgeschlossen!")
    print(f"\n📊 Zusammenfassung:")
    print(f"  Gap Priority Topics: {result['statistics']['gap_priority_topics']}")
    print(f"  HIGH Priority: {result['statistics']['gap_priority_high']}")
    print(f"  Report Fächer: {result['statistics']['report_fächer']}")
    print(f"  Report Themen: {result['statistics']['report_themen']}")
    print(f"  Checklist Themen: {result['statistics']['checklist_themen']}")
    print(f"  Checklist Kategorien: {result['statistics']['checklist_kategorien']}")
    
    print(f"\n🔝 Top 5 HIGH Priority Topics:")
    for i, topic in enumerate(result['gap_priority']['high_priority'][:5], 1):
        topic_data = result['gap_priority']['topics'].get(topic, {})
        gap = topic_data.get('gap', 0)
        print(f"  {i}. {topic} (Gap: {gap:.1f})")


if __name__ == '__main__':
    main()

