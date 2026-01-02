#!/usr/bin/env python3
"""
Phase 4: Intelligentes Matching
Matcht muenster_relevanz_master.json gegen Ankizin/Dellas Tags
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set
from difflib import SequenceMatcher

# Übersetzungs-Mapping (Deutsch ↔ Englisch/Alternative)
TRANSLATION_MAP = {
    'strahlenschutz': ['radiation', 'radiation_protection', 'dosimetry', 'radiology'],
    'röntgen': ['x-ray', 'xray', 'radiology', 'imaging'],
    'pharmakologie': ['pharmacology', 'pharm', 'medication', 'drug'],
    'rechtsmedizin': ['forensic', 'forensics', 'legal_medicine'],
    'innere_medizin': ['internal_medicine', 'internal', 'cardiology', 'pneumology'],
    'chirurgie': ['surgery', 'surgical'],
    'neurologie': ['neurology', 'neurological'],
    'gynäkologie': ['gynecology', 'gyn', 'obstetrics'],
    'anästhesie': ['anesthesia', 'anaesthesia', 'intensive_care'],
    'radiologie': ['radiology', 'imaging', 'x-ray'],
    'diabetes': ['diabetes', 'diabetic'],
    'herzinsuffizienz': ['heart_failure', 'cardiac_failure'],
    'appendizitis': ['appendicitis'],
    'anämie': ['anemia', 'anaemia'],
    'hyperthyreose': ['hyperthyroidism'],
    'hypothyreose': ['hypothyroidism'],
    'pneumonie': ['pneumonia'],
    'fraktur': ['fracture'],
    'infarkt': ['infarction', 'mi', 'myocardial_infarction'],
}

# Fachgebiet-Mapping
FACHGEBIET_MAP = {
    'innere_medizin': ['innere', 'internal', 'kardiologie', 'cardiology', 'pneumologie', 'pneumology', 
                       'gastroenterologie', 'gastroenterology', 'nephrologie', 'nephrology',
                       'endokrinologie', 'endocrinology', 'hämatologie', 'hematology'],
    'chirurgie': ['chirurgie', 'surgery', 'unfallchirurgie', 'trauma', 'viszeralchirurgie', 'visceral',
                  'gefäßchirurgie', 'vascular'],
    'neurologie': ['neurologie', 'neurology', 'neuro'],
    'gynäkologie': ['gynäkologie', 'gynecology', 'gyn', 'obstetrics', 'geburtshilfe'],
    'anästhesie': ['anästhesie', 'anesthesia', 'intensivmedizin', 'intensive_care', 'notfallmedizin', 'emergency'],
    'radiologie': ['radiologie', 'radiology', 'bildgebung', 'imaging', 'röntgen', 'x-ray', 'ct', 'mrt', 'sono'],
    'rechtsmedizin': ['rechtsmedizin', 'forensic', 'forensics', 'legal'],
    'pharmakologie': ['pharmakologie', 'pharmacology', 'pharm', 'medikamente', 'medication', 'drug'],
    'strahlenschutz': ['strahlenschutz', 'radiation', 'dosimetry', 'kontrollbereich'],
    'allgemeinmedizin': ['allgemeinmedizin', 'general', 'family_medicine', 'praxis'],
}


def normalize_tag(tag: str) -> str:
    """Normalisiert Tag für Matching."""
    # Entferne Präfixe
    tag = tag.replace('#', '').replace('Ankizin_v5::', '').replace('Pharmakologie_Dellas_x_AMBOSS_v0.81::', '')
    
    # Normalisiere zu lowercase
    tag = tag.lower()
    
    # Ersetze Sonderzeichen
    tag = re.sub(r'[^\w\s]', ' ', tag)
    tag = re.sub(r'\s+', '_', tag)
    
    return tag.strip('_')


def extract_tag_parts(tag: str) -> List[str]:
    """Extrahiert alle Teile eines hierarchischen Tags."""
    parts = []
    
    # Split nach ::
    if '::' in tag:
        parts.extend(tag.split('::'))
    else:
        parts.append(tag)
    
    # Normalisiere alle Teile
    normalized_parts = []
    for part in parts:
        normalized = normalize_tag(part)
        if normalized:
            normalized_parts.append(normalized)
    
    return normalized_parts


def similarity_score(str1: str, str2: str) -> float:
    """Berechnet Ähnlichkeits-Score zwischen zwei Strings."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def match_topic_to_tags(topic: str, tags: List[str], translation_map: Dict) -> List[Tuple[str, float, str]]:
    """Matcht ein Topic gegen eine Liste von Tags."""
    matches = []
    
    topic_normalized = normalize_tag(topic)
    topic_parts = topic_normalized.split('_')
    
    # Übersetzungen für Topic
    topic_variants = [topic_normalized]
    if topic_normalized in translation_map:
        topic_variants.extend([normalize_tag(t) for t in translation_map[topic_normalized]])
    
    for tag in tags:
        tag_normalized = normalize_tag(tag)
        tag_parts = extract_tag_parts(tag)
        
        best_score = 0.0
        match_type = 'none'
        
        # 1. Exaktes Matching
        if topic_normalized == tag_normalized:
            best_score = 1.0
            match_type = 'exact'
        elif topic_normalized in tag_normalized or tag_normalized in topic_normalized:
            best_score = 0.9
            match_type = 'substring'
        
        # 2. Varianten-Matching
        for variant in topic_variants:
            if variant == tag_normalized:
                best_score = max(best_score, 0.95)
                match_type = 'variant_exact'
            elif variant in tag_normalized or tag_normalized in variant:
                best_score = max(best_score, 0.85)
                match_type = 'variant_substring'
        
        # 3. Teilwort-Matching (z.B. "innere_medizin" ↔ "innere" oder "kardiologie")
        for topic_part in topic_parts:
            if len(topic_part) > 3:  # Ignoriere sehr kurze Teile
                for tag_part in tag_parts:
                    if topic_part == tag_part:
                        best_score = max(best_score, 0.8)
                        match_type = 'part_exact'
                    elif topic_part in tag_part or tag_part in topic_part:
                        score = similarity_score(topic_part, tag_part)
                        if score > 0.7:
                            best_score = max(best_score, score * 0.75)
                            match_type = 'part_similar'
        
        # 4. Fuzzy-Matching
        fuzzy_score = similarity_score(topic_normalized, tag_normalized)
        if fuzzy_score > 0.7 and fuzzy_score > best_score:
            best_score = fuzzy_score * 0.7  # Etwas niedriger gewichtet
            match_type = 'fuzzy'
        
        # 5. Hierarchie-Matching (z.B. "Innere::Kardiologie" enthält "kardiologie")
        for tag_part in tag_parts:
            if len(tag_part) > 3:
                for topic_part in topic_parts:
                    if topic_part in tag_part or tag_part in topic_part:
                        score = similarity_score(topic_part, tag_part)
                        if score > 0.75:
                            best_score = max(best_score, score * 0.8)
                            match_type = 'hierarchy'
        
        if best_score >= 0.6:  # Threshold
            matches.append((tag, best_score, match_type))
    
    # Sortiere nach Score (absteigend)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches


def match_fachgebiet_to_tags(fachgebiet: str, tags: List[str], fachgebiet_map: Dict) -> List[Tuple[str, float]]:
    """Matcht ein Fachgebiet gegen Tags."""
    matches = []
    
    keywords = fachgebiet_map.get(fachgebiet, [fachgebiet])
    
    for tag in tags:
        tag_normalized = normalize_tag(tag)
        tag_parts = extract_tag_parts(tag)
        
        best_score = 0.0
        
        for keyword in keywords:
            keyword_normalized = normalize_tag(keyword)
            
            # Exakt oder Substring
            if keyword_normalized == tag_normalized:
                best_score = max(best_score, 1.0)
            elif keyword_normalized in tag_normalized or tag_normalized in keyword_normalized:
                best_score = max(best_score, 0.85)
            
            # In Tag-Parts suchen
            for tag_part in tag_parts:
                if keyword_normalized == tag_part:
                    best_score = max(best_score, 0.9)
                elif keyword_normalized in tag_part or tag_part in keyword_normalized:
                    best_score = max(best_score, 0.75)
        
        if best_score >= 0.7:
            matches.append((tag, best_score))
    
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    master_file = repo_root / '_OUTPUT' / 'muenster_relevanz_master.json'
    ankizin_tags_file = repo_root / '_OUTPUT' / 'ankizin_alle_tags.json'
    dellas_tags_file = repo_root / '_OUTPUT' / 'dellas_alle_tags.json'
    
    print("🔍 Phase 4: Intelligentes Matching\n")
    
    # Lade Daten
    print("📥 Lade Daten...")
    with open(master_file, 'r', encoding='utf-8') as f:
        master = json.load(f)
    
    with open(ankizin_tags_file, 'r', encoding='utf-8') as f:
        ankizin_data = json.load(f)
    
    with open(dellas_tags_file, 'r', encoding='utf-8') as f:
        dellas_data = json.load(f)
    
    ankizin_tags = ankizin_data.get('unique_tags', [])
    dellas_tags = dellas_data.get('unique_tags', [])
    
    print(f"✅ Master: {len(master['high_priority'])} HIGH Priority Topics")
    print(f"✅ Ankizin: {len(ankizin_tags)} Tags")
    print(f"✅ Dellas: {len(dellas_tags)} Tags")
    
    # Matche für beide Decks
    results = {}
    
    for deck_name, tags_list in [('ankizin', ankizin_tags), ('dellas', dellas_tags)]:
        print(f"\n🎯 Matche {deck_name.upper()}...")
        
        matched_tags = defaultdict(lambda: {'score': 0.0, 'match_type': '', 'matched_topics': []})
        
        # 1. HIGH Priority Topics matchen
        print(f"  1️⃣ HIGH Priority Topics...")
        for topic in master['high_priority'][:100]:  # Top 100 für Performance
            matches = match_topic_to_tags(topic, tags_list, TRANSLATION_MAP)
            for tag, score, match_type in matches[:5]:  # Top 5 Matches pro Topic
                if matched_tags[tag]['score'] < score:
                    matched_tags[tag]['score'] = score
                    matched_tags[tag]['match_type'] = match_type
                matched_tags[tag]['matched_topics'].append({
                    'topic': topic,
                    'score': score,
                    'match_type': match_type,
                })
        
        # 2. Keywords matchen
        print(f"  2️⃣ Keywords...")
        for keyword in master['keywords'][:50]:  # Top 50
            matches = match_topic_to_tags(keyword, tags_list, TRANSLATION_MAP)
            for tag, score, match_type in matches[:3]:
                if matched_tags[tag]['score'] < score:
                    matched_tags[tag]['score'] = score
                    matched_tags[tag]['match_type'] = match_type
                matched_tags[tag]['matched_topics'].append({
                    'topic': keyword,
                    'score': score,
                    'match_type': match_type,
                })
        
        # 3. Fachgebiete matchen
        print(f"  3️⃣ Fachgebiete...")
        for fach in master['fachgebiete']:
            matches = match_fachgebiet_to_tags(fach, tags_list, FACHGEBIET_MAP)
            for tag, score in matches[:5]:
                if matched_tags[tag]['score'] < score:
                    matched_tags[tag]['score'] = score
                    matched_tags[tag]['match_type'] = 'fachgebiet'
                matched_tags[tag]['matched_topics'].append({
                    'topic': fach,
                    'score': score,
                    'match_type': 'fachgebiet',
                })
        
        # 4. Diagnosen matchen
        print(f"  4️⃣ Diagnosen...")
        for diag in master['diagnosen'][:30]:
            matches = match_topic_to_tags(diag, tags_list, TRANSLATION_MAP)
            for tag, score, match_type in matches[:3]:
                if matched_tags[tag]['score'] < score:
                    matched_tags[tag]['score'] = score
                    matched_tags[tag]['match_type'] = match_type
                matched_tags[tag]['matched_topics'].append({
                    'topic': diag,
                    'score': score,
                    'match_type': match_type,
                })
        
        # Konvertiere zu Dict und sortiere
        matched_dict = {}
        for tag, data in matched_tags.items():
            matched_dict[tag] = {
                'score': data['score'],
                'match_type': data['match_type'],
                'matched_topics': sorted(data['matched_topics'], key=lambda x: x['score'], reverse=True)[:5],
            }
        
        # Sortiere nach Score
        sorted_matches = sorted(matched_dict.items(), key=lambda x: x[1]['score'], reverse=True)
        
        # Kategorisiere: Include / Exclude
        include_tags = []
        exclude_tags = []
        match_confidence = {}
        
        # Threshold: Score >= 0.7 → Include
        for tag, data in sorted_matches:
            score = data['score']
            match_confidence[tag] = score
            
            if score >= 0.7:
                include_tags.append(tag)
            elif score < 0.5:
                # Prüfe ob Tag eindeutig nicht-relevant ist
                tag_lower = tag.lower()
                exclude_keywords = ['delete', 'duplicate', 'update', 'credit', 'projekt', 'universität', 'göttingen']
                if any(kw in tag_lower for kw in exclude_keywords):
                    exclude_tags.append(tag)
        
        results[deck_name] = {
            'include_tags': include_tags,
            'exclude_tags': exclude_tags,
            'match_confidence': match_confidence,
            'statistics': {
                'total_matched_tags': len(matched_dict),
                'include_count': len(include_tags),
                'exclude_count': len(exclude_tags),
                'high_confidence': len([t for t, s in match_confidence.items() if s >= 0.8]),
                'medium_confidence': len([t for t, s in match_confidence.items() if 0.7 <= s < 0.8]),
                'low_confidence': len([t for t, s in match_confidence.items() if s < 0.7]),
            },
        }
        
        print(f"  ✅ {len(include_tags)} Include-Tags, {len(exclude_tags)} Exclude-Tags")
        print(f"  ✅ {results[deck_name]['statistics']['high_confidence']} High-Confidence Matches")
    
    # Speichere Ergebnisse
    print(f"\n💾 Speichere Ergebnisse...")
    
    for deck_name in ['ankizin', 'dellas']:
        output_file = repo_root / '_OUTPUT' / f'{deck_name}_matched_tags.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results[deck_name], f, ensure_ascii=False, indent=2)
        print(f"✅ {output_file.name}")
    
    print("\n✅ Phase 4 abgeschlossen!")
    
    # Zusammenfassung
    print(f"\n📊 Zusammenfassung:")
    for deck_name in ['ankizin', 'dellas']:
        stats = results[deck_name]['statistics']
        print(f"\n{deck_name.upper()}:")
        print(f"  Include-Tags: {stats['include_count']}")
        print(f"  Exclude-Tags: {stats['exclude_count']}")
        print(f"  High-Confidence: {stats['high_confidence']}")
        print(f"  Medium-Confidence: {stats['medium_confidence']}")
        print(f"  Low-Confidence: {stats['low_confidence']}")
    
    print(f"\n🔝 Top 10 Include-Tags (Ankizin):")
    for i, tag in enumerate(results['ankizin']['include_tags'][:10], 1):
        score = results['ankizin']['match_confidence'].get(tag, 0)
        print(f"  {i}. {tag[:80]}... (Score: {score:.2f})")
    
    print(f"\n🔝 Top 10 Include-Tags (Dellas):")
    for i, tag in enumerate(results['dellas']['include_tags'][:10], 1):
        score = results['dellas']['match_confidence'].get(tag, 0)
        print(f"  {i}. {tag[:80]}... (Score: {score:.2f})")


if __name__ == '__main__':
    main()

