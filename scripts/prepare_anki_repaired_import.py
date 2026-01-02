#!/usr/bin/env python3
"""
Bereitet reparierte Fragen für Anki-Import vor
Erstellt TSV-Dateien für fallbasierte und Template-Karten
"""

import json
import csv
from pathlib import Path
from typing import List, Dict

def anki_sanitize_field(value: str) -> str:
    """
    Anki TSV Import: 1 Note pro Zeile.
    → Keine echten Zeilenumbrüche innerhalb eines Feldes (sonst „zerreißt“ der Import).
    Wir wandeln Newlines in <br> um und entfernen Tabs.
    """
    if value is None:
        return ""
    s = str(value)
    s = s.replace("\t", "    ")
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\n", "<br>")
    return s

def format_question_with_context(item: Dict) -> str:
    """Formatiert Frage mit Fallkontext."""
    frage = item['original_frage']
    context = item.get('extracted_context', {})
    
    # Füge Fallkontext zur Frage hinzu, falls vorhanden
    context_parts = []
    
    if context.get('patient'):
        patient = context['patient']
        if patient.get('alter'):
            context_parts.append(f"{patient['alter']} Jahre")
        if patient.get('geschlecht'):
            context_parts.append("männlich" if patient['geschlecht'] == 'm' else "weiblich")
    
    if context.get('mechanism'):
        context_parts.append(f"Unfallmechanismus: {context['mechanism']}")
    
    if context.get('klinik'):
        klinik_preview = ', '.join(context['klinik'][:3])
        if len(context['klinik']) > 3:
            klinik_preview += f" (+{len(context['klinik'])-3} weitere)"
        context_parts.append(f"Klinik: {klinik_preview}")
    
    if context_parts:
        context_str = f"[Fallkontext: {', '.join(context_parts)}]\n\n"
        return context_str + frage
    else:
        return frage


def extract_tags(item: Dict) -> str:
    """Extrahiert Tags aus Item."""
    tags = []
    
    # Basis-Tags
    tags.append('repaired::v1')
    tags.append('pipeline::context_repair_v2')
    qa_status = str(item.get('qa_status') or 'unverified').strip().lower()
    if qa_status not in {'unverified', 'verified', 'needs_review'}:
        qa_status = 'unverified'
    tags.append(f'qa::{qa_status}')
    
    # Context-Status
    context_status = item.get('context_status', 'unknown')
    tags.append(f'context::{context_status}')
    
    # Repair-Status
    repair_status = item.get('repair_status', 'unknown')
    tags.append(f'repair::{repair_status}')
    
    # MedGemma-Relevanz
    if item.get('medgemma_relevant'):
        tags.append('medgemma_relevant')
    
    # Source-basierte Tags
    source = item.get('source', '')
    if source:
        source_clean = Path(source).stem.replace(' ', '_').replace('.', '_')
        tags.append(f'source::{source_clean[:50]}')
    
    # Diagnose-basierte Tags
    context = item.get('extracted_context', {})
    if context.get('diagnose'):
        diag_clean = context['diagnose'].replace(' ', '_').replace(',', '').replace('(', '').replace(')', '')[:30]
        tags.append(f'diagnose::{diag_clean}')
    
    # Fachgebiet schätzen aus Diagnose/Frage
    frage_lower = item['original_frage'].lower()
    if any(x in frage_lower for x in ['fraktur', 'trauma', 'sturz', 'unfall']):
        tags.append('fachgebiet::Chirurgie')
    elif any(x in frage_lower for x in ['medikament', 'dosierung', 'pharmakologie']):
        tags.append('fachgebiet::Pharmakologie')
    elif any(x in frage_lower for x in ['röntgen', 'bildgebung', 'strahlenschutz']):
        tags.append('fachgebiet::Radiologie')
    elif any(x in frage_lower for x in ['rechtsmedizin', 'leichenschau', 'todeszeichen']):
        tags.append('fachgebiet::Rechtsmedizin')
    
    return ' '.join(tags)


def format_answer(item: Dict) -> str:
    """Formatiert Antwort."""
    repaired_answer = item.get('repaired_answer', '')
    if repaired_answer:
        return repaired_answer
    
    # Fallback: Original-Antwort
    return item.get('original_antwort', '')


def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    batch_input_file = repo_root / '_OUTPUT' / 'batch_repair_input.jsonl'
    output_dir = repo_root / '_OUTPUT'
    
    print("📦 Bereite reparierte Fragen für Anki-Import vor...\n")
    
    # Lade alle Items
    items = []
    with open(batch_input_file, 'r', encoding='utf-8') as f:
        for line in f:
            items.append(json.loads(line))
    
    print(f"✅ {len(items)} Fragen geladen")
    
    # Trenne in fallbasiert und Template
    fallbasiert = [item for item in items if item.get('repair_status') == 'repaired']
    templates = [item for item in items if item.get('repair_status') == 'template']
    
    print(f"📊 Fallbasiert: {len(fallbasiert)}")
    print(f"📊 Templates: {len(templates)}")
    
    # Funktion zum Erstellen einer TSV-Datei
    def create_tsv(items_list: List[Dict], output_file: Path, description: str):
        """Erstellt TSV-Datei für eine Liste von Items."""
        print(f"\n💾 Erstelle {description}...")
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            
            # Header (optional, Anki kann ohne Header)
            # writer.writerow(['Frage', 'Antwort', 'Tags'])
            
            for item in items_list:
                frage = format_question_with_context(item)
                antwort = format_answer(item)
                tags = extract_tags(item)
                writer.writerow([
                    anki_sanitize_field(frage),
                    anki_sanitize_field(antwort),
                    anki_sanitize_field(tags),
                ])
        
        print(f"✅ {output_file.name} erstellt ({len(items_list)} Karten)")
    
    # Erstelle alle TSV-Dateien
    create_tsv(items, output_dir / 'anki_repaired_ready.tsv', 'Alle reparierten Fragen')
    create_tsv(fallbasiert, output_dir / 'anki_repaired_fallbasiert.tsv', 'Fallbasierte Karten')
    create_tsv(templates, output_dir / 'anki_repaired_templates.tsv', 'Template-Karten')
    
    # Statistik
    print(f"\n📊 Zusammenfassung:")
    print(f"  Gesamt: {len(items)} Karten")
    print(f"  Fallbasiert: {len(fallbasiert)} Karten")
    print(f"  Templates: {len(templates)} Karten")
    
    # Zeige Beispiel
    if fallbasiert:
        example = fallbasiert[0]
        print(f"\n🔝 Beispiel (Fallbasiert):")
        print(f"  Frage: {format_question_with_context(example)[:100]}...")
        print(f"  Tags: {extract_tags(example)}")
    
    print("\n✅ Alle TSV-Dateien erstellt!")
    print("\n📋 Import-Reihenfolge:")
    print("  1. Ankizin_KP_Muenster_filtered.apkg (~18.297 Karten)")
    print("  2. Dellas_KP_Muenster_filtered.apkg (~4.943 Karten)")
    print(f"  3. anki_repaired_fallbasiert.tsv ({len(fallbasiert)} Karten)")
    print(f"  4. anki_repaired_templates.tsv ({len(templates)} Karten)")


if __name__ == '__main__':
    main()

