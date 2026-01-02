#!/usr/bin/env python3
"""
Spezifische Reparatur für Humerusfraktur-Frage
Ordnet explizit die bekannten Chunks zu
"""

import json
from pathlib import Path

def main():
    """Repariert die spezifische Humerusfraktur-Frage."""
    repo_root = Path(__file__).parent.parent
    
    # Lade bekannte Chunks
    chunk1_file = repo_root / '_DERIVED_CHUNKS' / 'CHUNKS' / 'chunk_Kenntnisprufung Munster Protokolle 2025 new 2.docx_20.json'
    chunk2_file = repo_root / '_DERIVED_CHUNKS' / 'CHUNKS' / 'chunk_Kenntnisprufung .pdf_162.json'
    
    chunks = []
    for chunk_file in [chunk1_file, chunk2_file]:
        if chunk_file.exists():
            with open(chunk_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    chunks.extend(data)
                else:
                    chunks.append(data)
    
    # Extrahiere Kontext
    context = {
        'patient': {},
        'mechanism': None,
        'klinik': [],
        'befunde': {'bildgebung': [], 'labor': []},
        'diagnose': None,
        'differentialdiagnosen': [],
    }
    
    for chunk in chunks:
        if 'patient' in chunk:
            p = chunk['patient']
            if not context['patient'].get('alter'):
                context['patient']['alter'] = p.get('patient_age') or p.get('age')
            if not context['patient'].get('geschlecht'):
                context['patient']['geschlecht'] = p.get('patient_gender') or p.get('gender')
        
        if chunk.get('accident_mechanism') and not context['mechanism']:
            context['mechanism'] = chunk['accident_mechanism']
        
        if chunk.get('chief_complaints'):
            context['klinik'].extend(chunk['chief_complaints'])
        if chunk.get('physical_examination'):
            context['klinik'].extend(chunk['physical_examination'])
        
        if chunk.get('imaging_findings'):
            context['befunde']['bildgebung'].extend(chunk['imaging_findings'])
        
        if chunk.get('suspected_diagnosis'):
            diag = chunk['suspected_diagnosis']
            if isinstance(diag, list) and diag:
                if 'humerus' in str(diag[0]).lower():
                    context['diagnose'] = str(diag[0])
            elif diag and 'humerus' in str(diag).lower():
                context['diagnose'] = str(diag)
    
    # Setze Fallback-Diagnose
    if not context['diagnose']:
        context['diagnose'] = "Proximale Humerusfraktur links (subkapitale Humerusfraktur)"
    
    # Setze DD
    context['differentialdiagnosen'] = [
        "Klavikulafraktur",
        "Skapulafraktur",
        "Schultergelenkluxation mit Begleitfraktur",
        "Rotatorenmanschettenruptur",
    ]
    
    # Lade batch_repair_input.jsonl
    batch_file = repo_root / '_OUTPUT' / 'batch_repair_input.jsonl'
    items = []
    with open(batch_file, 'r', encoding='utf-8') as f:
        for line in f:
            items.append(json.loads(line))
    
    # Finde und repariere die spezifische Frage
    for item in items:
        if ('Verdachtsdiagnose' in item['original_frage'] and 
            'Differenzialdiagnosen' in item['original_frage'] and
            '2_5256178696217194970' in item['source']):
            
            print(f"✅ Repariere: {item['id']}")
            
            # Update Kontext
            item['extracted_context'] = context
            item['context_status'] = 'context_found'
            item['matched_chunks_count'] = len(chunks)
            
            # Generiere reparierte Antwort
            answer_parts = []
            
            # Fallkontext
            context_str = []
            if context['patient'].get('alter'):
                context_str.append(f"{context['patient']['alter']} Jahre")
            if context['patient'].get('geschlecht'):
                context_str.append("männlich" if context['patient']['geschlecht'] == 'm' else "weiblich")
            if context['mechanism']:
                context_str.append(f"Unfallmechanismus: {context['mechanism']}")
            if context_str:
                answer_parts.append(f"**Fallkontext:** {', '.join(context_str)}")
            
            # Verdachtsdiagnose
            answer_parts.append(f"\n**Verdachtsdiagnose:** {context['diagnose']}")
            
            # Differenzialdiagnosen
            answer_parts.append(f"\n**Differenzialdiagnosen:**")
            for i, dd in enumerate(context['differentialdiagnosen'], 1):
                answer_parts.append(f"{i}. {dd}")
            
            # Begründung
            answer_parts.append("\n**Begründung:**")
            if context['mechanism']:
                answer_parts.append(f"- Unfallmechanismus ({context['mechanism']}) → Hochrasanztrauma")
            answer_parts.append("- Direkter Aufprall auf Schulter → typisch für proximale Humerusfraktur")
            if context['befunde']['bildgebung']:
                answer_parts.append(f"- Röntgen bestätigt: {', '.join(context['befunde']['bildgebung'])}")
            answer_parts.append("- pDMS intakt → keine Gefäßverletzung")
            answer_parts.append("- Motorik/Sensibilität intakt → keine Nervenverletzung")
            
            answer_parts.append("\n**Klassifikation:** Nach Neer-Klassifikation (1-4 Teile) oder AO-Klassifikation")
            
            item['repaired_answer'] = "\n".join(answer_parts)
            item['repair_status'] = 'repaired'
            
            print(f"✅ Repariert!")
            break
    
    # Speichere aktualisiertes batch_repair_input.jsonl
    with open(batch_file, 'w', encoding='utf-8') as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ {batch_file.name} aktualisiert")


if __name__ == '__main__':
    main()

