#!/usr/bin/env python3
"""
Aufgabe B: Kontext-Reparatur der 126 Fragen
Repariert Fragen mit generischen Antworten durch Kontext-Extraktion aus Chunks
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

def normalize_source_name(source: str) -> str:
    """Normalisiert Source-Namen für Matching."""
    name = Path(source).name.lower()
    name = re.sub(r'\.(pdf|docx|doc|txt|odt)$', '', name)
    name = re.sub(r'\s+', '_', name)
    # Entferne häufige Präfixe
    name = re.sub(r'^(kenntnispruefung|kenntnisprufung|kp|protokoll|protokolle)_*', '', name)
    return name


def find_matching_chunks(source: str, chunk_dir: Path) -> List[Dict]:
    """Findet passende Chunks für eine Source-Datei (verbessertes Matching)."""
    normalized_source = normalize_source_name(source)
    matching_chunks = []
    
    # Suche in allen Chunks
    for chunk_file in chunk_dir.glob('*.json'):
        chunk_name = chunk_file.stem.lower()
        
        # Verschiedene Matching-Strategien
        matched = False
        
        # 1. Direktes Matching im Dateinamen
        if normalized_source in chunk_name:
            matched = True
        
        # 2. Teilstring-Matching (z.B. "muenster_protokolle_2025" in "kenntnisprufung_munster_protokolle_2025_new_2")
        source_parts = normalized_source.split('_')
        chunk_parts = chunk_name.split('_')
        
        # Prüfe ob mindestens 2 Teile übereinstimmen
        matches = sum(1 for part in source_parts if len(part) > 3 and any(part in cp for cp in chunk_parts))
        if matches >= 2:
            matched = True
        
        # 3. Prüfe spezifische Patterns
        if '2_5256178696217194970' in source.lower() or '2_5256178696217194970' in chunk_name:
            matched = True
        
        if matched:
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    if isinstance(chunk_data, list):
                        matching_chunks.extend(chunk_data)
                    elif isinstance(chunk_data, dict):
                        matching_chunks.append(chunk_data)
            except Exception as e:
                continue
    
    return matching_chunks


def extract_context_from_chunk(chunk: Dict) -> Dict[str, any]:
    """Extrahiert Kontext aus einem Chunk (verbesserte Version)."""
    context = {
        'patient': {},
        'mechanism': None,
        'klinik': [],
        'befunde': {'bildgebung': [], 'labor': []},
        'diagnose': None,
        'differentialdiagnosen': [],
        'text_preview': '',
    }
    
    # Patient-Info
    if 'patient' in chunk:
        p = chunk['patient']
        context['patient'] = {
            'alter': p.get('patient_age') or p.get('age'),
            'geschlecht': p.get('patient_gender') or p.get('gender'),
            'name': p.get('name'),
        }
    
    # Unfallmechanismus
    context['mechanism'] = (
        chunk.get('accident_mechanism') or
        chunk.get('mechanism') or
        chunk.get('unfallmechanismus')
    )
    
    # Klinik
    klinik_fields = [
        'chief_complaints', 'leitsymptome', 'symptoms',
        'physical_examination', 'körperliche_untersuchung',
        'vital_signs', 'vitalparameter',
    ]
    for field in klinik_fields:
        if field in chunk:
            value = chunk[field]
            if isinstance(value, list):
                context['klinik'].extend([str(v) for v in value])
            elif isinstance(value, str):
                context['klinik'].append(value)
    
    # Befunde
    if 'imaging_findings' in chunk:
        img = chunk['imaging_findings']
        if isinstance(img, list):
            context['befunde']['bildgebung'] = [str(i) for i in img]
        else:
            context['befunde']['bildgebung'] = [str(img)]
    
    if 'laboratory_findings' in chunk:
        lab = chunk['laboratory_findings']
        if isinstance(lab, list):
            context['befunde']['labor'] = [str(l) for l in lab]
        else:
            context['befunde']['labor'] = [str(lab)]
    
    # Diagnose
    diag = (
        chunk.get('suspected_diagnosis') or
        chunk.get('diagnosis') or
        chunk.get('verdachtsdiagnose')
    )
    if isinstance(diag, list) and diag:
        context['diagnose'] = str(diag[0])
    elif diag:
        context['diagnose'] = str(diag)
    
    # Differentialdiagnosen
    dd = (
        chunk.get('differential_diagnoses') or
        chunk.get('differentialdiagnosen') or
        []
    )
    if isinstance(dd, list):
        context['differentialdiagnosen'] = [str(d) for d in dd]
    elif dd:
        context['differentialdiagnosen'] = [str(dd)]
    
    # Text-Preview für Fallback
    if 'text' in chunk:
        text = str(chunk['text'])
        context['text_preview'] = text[:500] + ('...' if len(text) > 500 else '')
        
        # Fallback: Versuche Patient-Alter aus Text zu extrahieren
        if not context['patient'].get('alter'):
            age_match = re.search(r'(\d+)\s*(?:jahre|j\.|j\b)', text, re.IGNORECASE)
            if age_match:
                context['patient']['alter'] = age_match.group(1)
        
        # Fallback: Versuche Geschlecht aus Text zu extrahieren
        if not context['patient'].get('geschlecht'):
            if re.search(r'\b(mann|männlich|m\.|patient)\b', text, re.IGNORECASE):
                context['patient']['geschlecht'] = 'm'
            elif re.search(r'\b(frau|weiblich|w\.|patientin)\b', text, re.IGNORECASE):
                context['patient']['geschlecht'] = 'w'
    
    return context


def merge_contexts(contexts: List[Dict]) -> Dict:
    """Mergt mehrere Kontexte zu einem."""
    merged = {
        'patient': {},
        'mechanism': None,
        'klinik': [],
        'befunde': {'bildgebung': [], 'labor': []},
        'diagnose': None,
        'differentialdiagnosen': [],
        'text_preview': '',
    }
    
    for ctx in contexts:
        # Patient: nimm ersten vollständigen
        if ctx.get('patient') and not merged['patient']:
            merged['patient'] = ctx['patient']
        elif ctx.get('patient'):
            # Merge: nimm nicht-leere Werte
            for k, v in ctx['patient'].items():
                if v and not merged['patient'].get(k):
                    merged['patient'][k] = v
        
        # Mechanism: nimm ersten
        if ctx.get('mechanism') and not merged['mechanism']:
            merged['mechanism'] = ctx['mechanism']
        
        # Klinik: sammle alle
        merged['klinik'].extend(ctx.get('klinik', []))
        
        # Befunde: sammle alle
        merged['befunde']['bildgebung'].extend(ctx.get('befunde', {}).get('bildgebung', []))
        merged['befunde']['labor'].extend(ctx.get('befunde', {}).get('labor', []))
        
        # Diagnose: nimm erste
        if ctx.get('diagnose') and not merged['diagnose']:
            merged['diagnose'] = ctx['diagnose']
        
        # DD: sammle alle
        merged['differentialdiagnosen'].extend(ctx.get('differentialdiagnosen', []))
        
        # Text-Preview: nimm längsten
        if len(ctx.get('text_preview', '')) > len(merged['text_preview']):
            merged['text_preview'] = ctx['text_preview']
    
    # Dedupliziere Listen
    merged['klinik'] = list(dict.fromkeys(merged['klinik']))  # Behält Reihenfolge
    merged['differentialdiagnosen'] = list(dict.fromkeys(merged['differentialdiagnosen']))
    merged['befunde']['bildgebung'] = list(dict.fromkeys(merged['befunde']['bildgebung']))
    merged['befunde']['labor'] = list(dict.fromkeys(merged['befunde']['labor']))
    
    return merged


def categorize_context(context: Dict) -> str:
    """Kategorisiert Kontext-Qualität."""
    patient = context.get('patient', {})
    has_patient = bool(patient.get('alter') or patient.get('geschlecht'))
    has_mechanism = bool(context.get('mechanism'))
    has_klinik = len(context.get('klinik', [])) > 0
    befunde = context.get('befunde', {})
    has_befunde = bool(befunde.get('bildgebung') or befunde.get('labor'))
    has_diagnose = bool(context.get('diagnose'))
    has_text = bool(context.get('text_preview'))
    
    score = sum([
        has_patient,
        has_mechanism,
        has_klinik,
        has_befunde,
        has_diagnose,
        has_text * 0.5,  # Text ist weniger wertvoll als strukturierte Daten
    ])
    
    if score >= 4:
        return 'context_found'
    elif score >= 2:
        return 'partial_context'
    else:
        return 'no_context'


def generate_repaired_answer(item: Dict, context: Dict) -> str:
    """Generiert reparierte Antwort basierend auf Kontext."""
    frage = item['original_frage']
    original_antwort = item['original_antwort']
    
    # Spezialfall: Humerusfraktur-Frage
    if 'Verdachtsdiagnose' in frage and 'Differenzialdiagnosen' in frage:
        if context.get('diagnose') and 'humerus' in context['diagnose'].lower():
            return generate_humerusfraktur_answer(context)
    
    # Generische Reparatur für andere Fragen
    if context.get('diagnose'):
        return generate_generic_repaired_answer(frage, context, original_antwort)
    
    # Fallback: Template-Antwort
    return generate_template_answer(frage, original_antwort)


def generate_humerusfraktur_answer(context: Dict) -> str:
    """Generiert spezifische Antwort für Humerusfraktur-Frage."""
    patient = context.get('patient', {})
    mechanism = context.get('mechanism', '')
    diagnose = context.get('diagnose', '')
    dd = context.get('differentialdiagnosen', [])
    
    answer_parts = []
    
    # Verdachtsdiagnose
    if diagnose:
        answer_parts.append(f"**Verdachtsdiagnose:** {diagnose}")
    elif 'humerus' in mechanism.lower() or 'schulter' in mechanism.lower():
        answer_parts.append("**Verdachtsdiagnose:** Proximale Humerusfraktur links (subkapitale Humerusfraktur)")
    
    # Fallkontext
    if patient.get('alter') or mechanism:
        context_str = []
        if patient.get('alter'):
            context_str.append(f"{patient['alter']} Jahre")
        if patient.get('geschlecht'):
            context_str.append("männlich" if patient['geschlecht'] == 'm' else "weiblich")
        if mechanism:
            context_str.append(f"Unfallmechanismus: {mechanism}")
        if context_str:
            answer_parts.append(f"**Fallkontext:** {', '.join(context_str)}")
    
    # Differenzialdiagnosen
    if dd:
        answer_parts.append(f"**Differenzialdiagnosen:**")
        for i, d in enumerate(dd[:5], 1):
            answer_parts.append(f"{i}. {d}")
    else:
        answer_parts.append("**Differenzialdiagnosen:**")
        answer_parts.append("1. Klavikulafraktur")
        answer_parts.append("2. Skapulafraktur")
        answer_parts.append("3. Schultergelenkluxation mit Begleitfraktur")
        answer_parts.append("4. Rotatorenmanschettenruptur")
    
    # Begründung
    answer_parts.append("\n**Begründung:**")
    if mechanism:
        answer_parts.append(f"- Unfallmechanismus ({mechanism}) → Hochrasanztrauma")
    answer_parts.append("- Direkter Aufprall auf Schulter → typisch für proximale Humerusfraktur")
    if context.get('befunde', {}).get('bildgebung'):
        answer_parts.append("- Röntgen bestätigt Humerusfraktur")
    answer_parts.append("- pDMS intakt → keine Gefäßverletzung")
    answer_parts.append("- Motorik/Sensibilität intakt → keine Nervenverletzung")
    
    answer_parts.append("\n**Klassifikation:** Nach Neer-Klassifikation (1-4 Teile) oder AO-Klassifikation")
    
    return "\n".join(answer_parts)


def generate_generic_repaired_answer(frage: str, context: Dict, original_antwort: str) -> str:
    """Generiert generische reparierte Antwort mit Kontext."""
    answer_parts = []
    
    # Fallkontext einbauen
    if context.get('patient') or context.get('mechanism'):
        context_str = []
        patient = context.get('patient', {})
        if patient.get('alter'):
            context_str.append(f"{patient['alter']} Jahre")
        if patient.get('geschlecht'):
            context_str.append("männlich" if patient['geschlecht'] == 'm' else "weiblich")
        if context.get('mechanism'):
            context_str.append(f"Unfallmechanismus: {context['mechanism']}")
        if context_str:
            answer_parts.append(f"**Fallkontext:** {', '.join(context_str)}")
    
    # Diagnose
    if context.get('diagnose'):
        answer_parts.append(f"**Verdachtsdiagnose:** {context['diagnose']}")
    
    # Klinik
    if context.get('klinik'):
        answer_parts.append(f"**Klinik:** {', '.join(context['klinik'][:5])}")
    
    # Befunde
    befunde = context.get('befunde', {})
    if befunde.get('bildgebung'):
        answer_parts.append(f"**Bildgebung:** {', '.join(befunde['bildgebung'][:3])}")
    if befunde.get('labor'):
        answer_parts.append(f"**Labor:** {', '.join(befunde['labor'][:3])}")
    
    # Original-Antwort als Basis (falls sinnvoll)
    if original_antwort and len(original_antwort) > 100 and 'nicht möglich' not in original_antwort.lower():
        answer_parts.append(f"\n**Weitere Informationen:**\n{original_antwort[:300]}...")
    
    return "\n".join(answer_parts) if answer_parts else original_antwort


def generate_template_answer(frage: str, original_antwort: str) -> str:
    """Generiert Template-Antwort wenn kein Kontext verfügbar."""
    return f"""**Hinweis:** Diese Frage benötigt Fallkontext für eine konkrete Antwort.

**Generisches Vorgehen:**
{original_antwort[:200]}...

**Für Prüfung:** Immer strukturiert antworten:
1. Definition/Klassifikation
2. Ätiologie/Pathophysiologie  
3. Diagnostik (Schritt für Schritt)
4. Therapie (mit exakten Dosierungen)
5. Rechtliche Aspekte (§§)"""


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    batch_input_file = repo_root / '_OUTPUT' / 'batch_repair_input.jsonl'
    chunk_dir = repo_root / '_DERIVED_CHUNKS' / 'CHUNKS'
    output_dir = repo_root / '_OUTPUT'
    
    print("🔧 Aufgabe B: Kontext-Reparatur der 126 Fragen\n")
    
    # Lade Batch-Input
    print("📥 Lade batch_repair_input.jsonl...")
    items = []
    with open(batch_input_file, 'r', encoding='utf-8') as f:
        for line in f:
            items.append(json.loads(line))
    
    print(f"✅ {len(items)} Fragen geladen")
    
    # Verbesserte Kontext-Extraktion
    print("\n🔍 Verbesserte Kontext-Extraktion...")
    
    repaired_items = []
    stats = defaultdict(int)
    
    for idx, item in enumerate(items):
        source = item['source']
        original_index = item['original_index']
        
        # Suche Chunks (verbessertes Matching)
        chunks = find_matching_chunks(source, chunk_dir)
        
        # Extrahiere Kontext
        contexts = []
        for chunk in chunks:
            ctx = extract_context_from_chunk(chunk)
            contexts.append(ctx)
        
        # Merge Kontexte
        merged_context = merge_contexts(contexts) if contexts else {}
        
        # Kategorisiere
        context_status = categorize_context(merged_context)
        stats[f'status_{context_status}'] += 1
        
        # Update Item
        item['extracted_context'] = merged_context
        item['context_status'] = context_status
        item['matched_chunks_count'] = len(chunks)
        
        # Generiere reparierte Antwort
        if context_status in ['context_found', 'partial_context']:
            repaired_answer = generate_repaired_answer(item, merged_context)
            item['repaired_answer'] = repaired_answer
            item['repair_status'] = 'repaired'
            stats['repaired'] += 1
        else:
            item['repaired_answer'] = generate_template_answer(item['original_frage'], item['original_antwort'])
            item['repair_status'] = 'template'
            stats['template'] += 1
        
        repaired_items.append(item)
        
        if (idx + 1) % 20 == 0:
            print(f"  Verarbeitet: {idx + 1}/{len(items)}")
    
    print(f"\n✅ Kontext-Extraktion abgeschlossen")
    
    # Statistik
    print(f"\n📊 Statistik:")
    print(f"  context_found: {stats['status_context_found']}")
    print(f"  partial_context: {stats['status_partial_context']}")
    print(f"  no_context: {stats['status_no_context']}")
    print(f"  repaired: {stats['repaired']}")
    print(f"  template: {stats['template']}")
    
    # Speichere Ergebnisse
    print(f"\n💾 Speichere Ergebnisse...")
    
    # 1. Aktualisiertes batch_repair_input.jsonl
    output_file = output_dir / 'batch_repair_input.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in repaired_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"✅ {output_file.name} aktualisiert")
    
    # 2. Stats JSON
    stats_file = output_dir / 'batch_repair_stats.json'
    stats_data = {
        'total_questions': len(items),
        'statistics': dict(stats),
        'context_found_count': stats['status_context_found'],
        'partial_context_count': stats['status_partial_context'],
        'no_context_count': stats['status_no_context'],
        'repaired_count': stats['repaired'],
        'template_count': stats['template'],
    }
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats_data, f, ensure_ascii=False, indent=2)
    print(f"✅ {stats_file.name}")
    
    # 3. Aktualisierte Instructions
    instructions_file = output_dir / 'batch_repair_instructions.md'
    with open(instructions_file, 'r', encoding='utf-8') as f:
        instructions = f.read()
    
    # Füge aktualisierte Statistik hinzu
    updated_section = f"""
## 📊 Aktualisierte Statistik (nach verbesserter Kontext-Extraktion)

| Kategorie | Anzahl | Anteil |
|-----------|--------|--------|
| **context_found** | {stats['status_context_found']} | {stats['status_context_found']/len(items)*100:.1f}% |
| **partial_context** | {stats['status_partial_context']} | {stats['status_partial_context']/len(items)*100:.1f}% |
| **no_context** | {stats['status_no_context']} | {stats['status_no_context']/len(items)*100:.1f}% |
| **repaired** | {stats['repaired']} | {stats['repaired']/len(items)*100:.1f}% |
| **template** | {stats['template']} | {stats['template']/len(items)*100:.1f}% |

"""
    
    # Ersetze alte Statistik
    instructions = re.sub(r'## 📊 Statistik.*?## 🎯 Priorisierung', f'## 📊 Statistik{updated_section}## 🎯 Priorisierung', instructions, flags=re.DOTALL)
    
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(instructions)
    print(f"✅ {instructions_file.name} aktualisiert")
    
    # Zeige Beispiel-Reparatur
    print(f"\n🔝 Beispiel-Reparatur (Humerusfraktur):")
    for item in repaired_items:
        if 'Verdachtsdiagnose' in item['original_frage'] and 'Differenzialdiagnosen' in item['original_frage']:
            print(f"\nFrage: {item['original_frage'][:100]}...")
            print(f"Status: {item['context_status']}")
            print(f"Reparierte Antwort:")
            print(item['repaired_answer'][:300] + ('...' if len(item['repaired_answer']) > 300 else ''))
            break
    
    print("\n✅ Aufgabe B: Kontext-Reparatur abgeschlossen!")


if __name__ == '__main__':
    main()

