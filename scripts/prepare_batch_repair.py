#!/usr/bin/env python3
"""
Batch-Vorbereitung für Kontext-Reparatur von Fragen mit generischen Antworten.

Für jede Frage in kontext_fehlende_antworten.json:
- Suche passenden Chunk (über source_file matchen)
- Extrahiere Kontext: Patient, Mechanismus, Klinik, Befunde
- Kategorisiere: context_found / partial_context / no_context
- Markiere medgemma_relevant: true wenn Bilder/Dosierungen/Grenzwerte

Erstellt:
- _OUTPUT/batch_repair_input.jsonl
- _OUTPUT/batch_repair_instructions.md
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# MedGemma-Relevanz-Muster
MEDGEMMA_PATTERNS = {
    'bild': [
        r'bild|röntgen|ct|mrt|sono|ekg|ultraschall|radiolog|aufnahme',
        r'foto|abbildung|darstellung|befund.*bild',
    ],
    'dosis': [
        r'\d+\s*(mg|g|ml|µg|iu|einheiten)/\s*(tag|woche|monat|kg|dosis)',
        r'dosierung|dosis|applikation|gabe',
        r'\d+\s*x\s*\d+\s*(mg|g)',
    ],
    'grenzwert': [
        r'grenzwert|normalwert|referenz|cut.?off',
        r'<\s*\d+|>\s*\d+',
        r'über|unter.*(?:grenze|wert)',
    ],
    'klassifikation': [
        r'klassifikation|stadium|grad|typ\s+[ivx]+',
        r'garden|pauwels|ao|forrest|nyha|curb|fontaine|gold|child.?pugh',
    ],
}


def normalize_source_name(source: str) -> str:
    """Normalisiert Source-Namen für Matching."""
    # Entferne Pfade, normalisiere Leerzeichen
    name = Path(source).name.lower()
    # Entferne häufige Suffixe
    name = re.sub(r'\.(pdf|docx|doc|txt)$', '', name)
    # Normalisiere Unicode/Leerzeichen
    name = re.sub(r'\s+', '_', name)
    return name


def find_matching_chunks(source: str, chunk_dir: Path) -> List[Dict]:
    """Findet passende Chunks für eine Source-Datei."""
    normalized_source = normalize_source_name(source)
    matching_chunks = []
    
    for chunk_file in chunk_dir.glob('*.json'):
        chunk_name = chunk_file.stem.lower()
        
        # Direktes Matching
        if normalized_source in chunk_name or chunk_name.startswith(f'chunk_{normalized_source}'):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                    if isinstance(chunk_data, list):
                        matching_chunks.extend(chunk_data)
                    elif isinstance(chunk_data, dict):
                        matching_chunks.append(chunk_data)
            except Exception as e:
                print(f"⚠️  Fehler beim Laden von {chunk_file.name}: {e}")
                continue
    
    return matching_chunks


def extract_context_from_chunk(chunk: Dict) -> Dict[str, Any]:
    """Extrahiert Kontext aus einem Chunk."""
    context = {
        'patient': {},
        'mechanism': None,
        'klinik': [],
        'befunde': {},
        'diagnose': None,
        'differentialdiagnosen': [],
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
                context['klinik'].extend(value)
            elif isinstance(value, str):
                context['klinik'].append(value)
    
    # Befunde
    if 'imaging_findings' in chunk:
        context['befunde']['bildgebung'] = chunk['imaging_findings']
    if 'laboratory_findings' in chunk:
        context['befunde']['labor'] = chunk['laboratory_findings']
    
    # Diagnose
    context['diagnose'] = (
        chunk.get('suspected_diagnosis') or
        chunk.get('diagnosis') or
        chunk.get('verdachtsdiagnose')
    )
    if isinstance(context['diagnose'], list) and context['diagnose']:
        context['diagnose'] = context['diagnose'][0]
    
    # Differentialdiagnosen
    context['differentialdiagnosen'] = (
        chunk.get('differential_diagnoses') or
        chunk.get('differentialdiagnosen') or
        []
    )
    
    # Fallback: Aus Text extrahieren
    if 'text' in chunk and not any([context['patient'], context['mechanism'], context['klinik']]):
        text = chunk['text']
        # Versuche Patient-Alter zu finden
        age_match = re.search(r'(\d+)\s*(?:jahre|j\.|j\b)', text, re.IGNORECASE)
        if age_match:
            context['patient']['alter'] = age_match.group(1)
        
        # Versuche Geschlecht zu finden
        if re.search(r'\b(mann|männlich|m\.|patient)\b', text, re.IGNORECASE):
            context['patient']['geschlecht'] = 'm'
        elif re.search(r'\b(frau|weiblich|w\.|patientin)\b', text, re.IGNORECASE):
            context['patient']['geschlecht'] = 'w'
    
    return context


def categorize_context(context: Dict) -> str:
    """Kategorisiert Kontext-Qualität."""
    patient = context.get('patient', {})
    has_patient = bool(patient.get('alter') or patient.get('geschlecht'))
    has_mechanism = bool(context.get('mechanism'))
    has_klinik = len(context.get('klinik', [])) > 0
    befunde = context.get('befunde', {})
    has_befunde = bool(befunde.get('bildgebung') or befunde.get('labor'))
    has_diagnose = bool(context.get('diagnose'))
    
    score = sum([has_patient, has_mechanism, has_klinik, has_befunde, has_diagnose])
    
    if score >= 4:
        return 'context_found'
    elif score >= 2:
        return 'partial_context'
    else:
        return 'no_context'


def check_medgemma_relevant(frage: str, antwort: str, context: Dict) -> bool:
    """Prüft ob Frage/Antwort MedGemma-relevant ist."""
    combined_text = f"{frage} {antwort}".lower()
    
    # Prüfe alle MedGemma-Muster
    for category, patterns in MEDGEMMA_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return True
    
    # Prüfe Kontext auf Bildbefunde
    if context.get('befunde', {}).get('bildgebung'):
        return True
    
    return False


def merge_contexts(contexts: List[Dict]) -> Dict:
    """Mergt mehrere Kontexte zu einem."""
    merged = {
        'patient': {},
        'mechanism': None,
        'klinik': [],
        'befunde': {'bildgebung': [], 'labor': []},
        'diagnose': None,
        'differentialdiagnosen': [],
    }
    
    for ctx in contexts:
        # Patient: nimm ersten vollständigen
        if ctx['patient'] and not merged['patient']:
            merged['patient'] = ctx['patient']
        
        # Mechanism: nimm ersten
        if ctx['mechanism'] and not merged['mechanism']:
            merged['mechanism'] = ctx['mechanism']
        
        # Klinik: sammle alle
        merged['klinik'].extend(ctx['klinik'])
        
        # Befunde: sammle alle
        if ctx['befunde'].get('bildgebung'):
            if isinstance(ctx['befunde']['bildgebung'], list):
                merged['befunde']['bildgebung'].extend(ctx['befunde']['bildgebung'])
            else:
                merged['befunde']['bildgebung'].append(ctx['befunde']['bildgebung'])
        
        if ctx['befunde'].get('labor'):
            if isinstance(ctx['befunde']['labor'], list):
                merged['befunde']['labor'].extend(ctx['befunde']['labor'])
            else:
                merged['befunde']['labor'].append(ctx['befunde']['labor'])
        
        # Diagnose: nimm erste
        if ctx['diagnose'] and not merged['diagnose']:
            merged['diagnose'] = ctx['diagnose']
        
        # DD: sammle alle
        merged['differentialdiagnosen'].extend(ctx['differentialdiagnosen'])
    
    # Dedupliziere Listen
    merged['klinik'] = list(set(merged['klinik']))
    merged['differentialdiagnosen'] = list(set(merged['differentialdiagnosen']))
    
    return merged


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    issues_file = repo_root / '_OUTPUT' / 'kontext_fehlende_antworten.json'
    evidenz_file = repo_root / '_OUTPUT' / 'evidenz_antworten.json'
    chunk_dir = repo_root / '_DERIVED_CHUNKS' / 'CHUNKS'
    output_dir = repo_root / '_OUTPUT'
    
    # Lade Daten
    print("📥 Lade Daten...")
    with open(issues_file, 'r', encoding='utf-8') as f:
        issues = json.load(f)
    
    with open(evidenz_file, 'r', encoding='utf-8') as f:
        evidenz_data = json.load(f)
    
    # Erstelle Index für evidenz_antworten.json
    evidenz_index = {}
    for idx, item in enumerate(evidenz_data):
        if isinstance(item, dict):
            frage = item.get('frage', '') or item.get('question', '')
            if frage:
                evidenz_index[idx] = item
    
    print(f"✅ {len(issues)} Fragen geladen")
    print(f"✅ {len(evidenz_index)} Einträge in evidenz_antworten.json")
    print(f"✅ {len(list(chunk_dir.glob('*.json')))} Chunks verfügbar")
    
    # Verarbeite jede Frage
    batch_items = []
    stats = defaultdict(int)
    
    print("\n🔍 Suche Kontext für jede Frage...")
    
    for issue in issues:
        original_index = issue['index']
        frage = issue['frage']
        source = issue['source']
        
        # Hole vollständige Antwort aus evidenz_antworten.json
        antwort = issue.get('antwort_preview', '')
        if original_index in evidenz_index:
            full_item = evidenz_index[original_index]
            antwort = full_item.get('antwort', '') or full_item.get('answer', '') or antwort
        
        # Suche passende Chunks
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
        
        # Prüfe MedGemma-Relevanz
        medgemma_relevant = check_medgemma_relevant(frage, antwort, merged_context)
        if medgemma_relevant:
            stats['medgemma_relevant'] += 1
        
        # Erstelle Batch-Item
        batch_item = {
            'id': f"repair_{original_index:05d}",
            'original_index': original_index,
            'original_frage': frage,
            'original_antwort': antwort[:500] + ('...' if len(antwort) > 500 else ''),
            'source': source,
            'context_status': context_status,
            'extracted_context': merged_context,
            'medgemma_relevant': medgemma_relevant,
            'matched_chunks_count': len(chunks),
        }
        
        batch_items.append(batch_item)
        
        if len(batch_items) % 20 == 0:
            print(f"  Verarbeitet: {len(batch_items)}/{len(issues)}")
    
    print(f"\n✅ Verarbeitung abgeschlossen: {len(batch_items)} Items")
    
    # Statistik
    print("\n📊 Statistik:")
    print(f"  context_found: {stats['status_context_found']}")
    print(f"  partial_context: {stats['status_partial_context']}")
    print(f"  no_context: {stats['status_no_context']}")
    print(f"  medgemma_relevant: {stats['medgemma_relevant']}")
    
    # Speichere batch_repair_input.jsonl
    output_file = output_dir / 'batch_repair_input.jsonl'
    print(f"\n💾 Speichere {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in batch_items:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    print(f"✅ {len(batch_items)} Items gespeichert")
    
    # Erstelle batch_repair_instructions.md
    instructions_file = output_dir / 'batch_repair_instructions.md'
    print(f"\n📝 Erstelle {instructions_file}...")
    
    # Gruppiere nach Status
    context_found_items = [i for i in batch_items if i['context_status'] == 'context_found']
    partial_context_items = [i for i in batch_items if i['context_status'] == 'partial_context']
    no_context_items = [i for i in batch_items if i['context_status'] == 'no_context']
    medgemma_items = [i for i in batch_items if i['medgemma_relevant']]
    
    instructions = f"""# Batch-Reparatur Anleitung

**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Gesamt:** {len(batch_items)} Fragen

---

## 📊 Statistik

| Kategorie | Anzahl | Anteil |
|-----------|--------|--------|
| **context_found** | {stats['status_context_found']} | {stats['status_context_found']/len(batch_items)*100:.1f}% |
| **partial_context** | {stats['status_partial_context']} | {stats['status_partial_context']/len(batch_items)*100:.1f}% |
| **no_context** | {stats['status_no_context']} | {stats['status_no_context']/len(batch_items)*100:.1f}% |
| **medgemma_relevant** | {stats['medgemma_relevant']} | {stats['medgemma_relevant']/len(batch_items)*100:.1f}% |

---

## 🎯 Priorisierung

### HIGH Priority (sofort reparieren)
- **{len(context_found_items)} Fragen mit vollständigem Kontext**
- **{len(medgemma_items)} MedGemma-relevante Fragen** (Bilder/Dosierungen/Grenzwerte)

### MEDIUM Priority
- **{len(partial_context_items)} Fragen mit teilweisem Kontext** (kann ergänzt werden)

### LOW Priority
- **{len(no_context_items)} Fragen ohne Kontext** (als Template-Karten umbauen)

---

## 🤖 MedGemma Batch-Prompt (für Bild/Dosis/Grenzwert-Fragen)

**Anzahl:** {len(medgemma_items)} Fragen

### Prompt-Template:

```
Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung Münster.

Aufgabe: Repariere die folgende Prüfungsfrage mit Fallkontext.

**Original-Frage:** {{original_frage}}

**Extrahierter Fallkontext:**
- Patient: {{patient_info}}
- Unfallmechanismus: {{mechanism}}
- Klinik: {{klinik}}
- Bildgebung: {{bildgebung}}
- Labor: {{labor}}
- Verdachtsdiagnose: {{diagnose}}
- Differentialdiagnosen: {{dd}}

**Original-Antwort (unbrauchbar):**
{{original_antwort}}

**Anforderungen:**
1. Generiere eine prüfungsgerechte Antwort mit konkretem Fallbezug
2. Bei Bildern: Systematische Bildbeschreibung (Was sehe ich?)
3. Bei Dosierungen: Exakte Angaben (z.B. "2x 1000mg p.o.")
4. Bei Grenzwerten: Konkrete Zahlen mit Einheiten
5. Struktur: Definition → Ätiologie → Diagnostik → Therapie → Rechtliches

**Format:**
- Kurz, präzise (3-5 Sätze für Kernantwort)
- Fallbezug explizit erwähnen
- Keine generischen Formulierungen wie "ohne Falldarstellung nicht möglich"
```

### Batch-Verarbeitung:

```bash
# MedGemma-relevante Fragen filtern
cat _OUTPUT/batch_repair_input.jsonl | jq 'select(.medgemma_relevant == true)' > _OUTPUT/medgemma_batch.jsonl

# Für jede Frage:
# 1. Kontext aus extracted_context extrahieren
# 2. MedGemma API aufrufen mit Prompt-Template
# 3. Antwort validieren
# 4. In _OUTPUT/batch_repair_output.jsonl speichern
```

---

## 📝 Standard Batch-Prompt (für normale Fragen)

**Anzahl:** {len(batch_items) - len(medgemma_items)} Fragen

### Prompt-Template:

```
Du bist ein medizinischer Experte für die deutsche Kenntnisprüfung Münster.

Aufgabe: Repariere die folgende Prüfungsfrage mit Fallkontext.

**Original-Frage:** {{original_frage}}

**Extrahierter Fallkontext:**
{{extracted_context}}

**Original-Antwort (unbrauchbar):**
{{original_antwort}}

**Anforderungen:**
1. Generiere eine prüfungsgerechte Antwort mit konkretem Fallbezug
2. Struktur: Definition → Ätiologie → Diagnostik → Therapie → Rechtliches
3. Fallbezug explizit erwähnen
4. Keine generischen Formulierungen

**Format:**
- Kurz, präzise (3-5 Sätze für Kernantwort)
- Prüfungsformat Münster beachten
```

### Batch-Verarbeitung:

```bash
# Nach Kontext-Status filtern
cat _OUTPUT/batch_repair_input.jsonl | jq 'select(.context_status == "context_found")' > _OUTPUT/context_found_batch.jsonl

# Für jede Frage:
# 1. Kontext aus extracted_context extrahieren
# 2. LLM (GPT-5 oder Claude) mit Prompt-Template aufrufen
# 3. Antwort validieren
# 4. In _OUTPUT/batch_repair_output.jsonl speichern
```

---

## 📋 Top 10 Fragen mit vollständigem Kontext

"""
    
    # Top 10 context_found
    for i, item in enumerate(context_found_items[:10], 1):
        instructions += f"""
### {i}. {item['id']}

**Frage:** {item['original_frage'][:150]}...

**Kontext:**
- Patient: {item['extracted_context'].get('patient', {})}
- Mechanismus: {item['extracted_context'].get('mechanism', 'N/A')[:100]}
- Diagnose: {item['extracted_context'].get('diagnose', 'N/A')}

**MedGemma:** {'✅ Ja' if item['medgemma_relevant'] else '❌ Nein'}

"""
    
    instructions += f"""
---

## 🔧 Nächste Schritte

1. **Review:** `_OUTPUT/batch_repair_input.jsonl` durchgehen
2. **Priorisierung:** Mit context_found beginnen
3. **MedGemma:** {len(medgemma_items)} Fragen separat verarbeiten
4. **Standard:** Rest mit Standard-Prompt verarbeiten
5. **Validierung:** Alle reparierten Antworten prüfen
6. **Export:** In Anki-TSV exportieren

---

## 📁 Dateien

- `_OUTPUT/batch_repair_input.jsonl` - Eingabedaten (JSONL, {len(batch_items)} Zeilen)
- `_OUTPUT/batch_repair_output.jsonl` - Ausgabedaten (nach Reparatur)
- `_OUTPUT/kontext_fehlende_antworten.json` - Original-Liste
"""
    
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write(instructions)
    
    print(f"✅ Anleitung erstellt")
    
    print("\n✅ Batch-Vorbereitung abgeschlossen!")
    print(f"\n📁 Output-Dateien:")
    print(f"  - {output_file}")
    print(f"  - {instructions_file}")


if __name__ == '__main__':
    main()

