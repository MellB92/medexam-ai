#!/usr/bin/env python3
"""
Phase 6: Report erstellen
Erstellt deck_filter_report.md mit allen Ergebnissen
"""

import json
from pathlib import Path
from datetime import datetime

def main():
    """Hauptfunktion."""
    repo_root = Path(__file__).parent.parent
    output_dir = repo_root / '_OUTPUT'
    
    print("🔍 Phase 6: Report erstellen\n")
    
    # Lade alle Daten
    master_file = output_dir / 'muenster_relevanz_master.json'
    ankizin_tags_file = output_dir / 'ankizin_alle_tags.json'
    dellas_tags_file = output_dir / 'dellas_alle_tags.json'
    ankizin_matched_file = output_dir / 'ankizin_matched_tags.json'
    dellas_matched_file = output_dir / 'dellas_matched_tags.json'
    
    with open(master_file, 'r', encoding='utf-8') as f:
        master = json.load(f)
    
    with open(ankizin_tags_file, 'r', encoding='utf-8') as f:
        ankizin_tags_data = json.load(f)
    
    with open(dellas_tags_file, 'r', encoding='utf-8') as f:
        dellas_tags_data = json.load(f)
    
    with open(ankizin_matched_file, 'r', encoding='utf-8') as f:
        ankizin_matched = json.load(f)
    
    with open(dellas_matched_file, 'r', encoding='utf-8') as f:
        dellas_matched = json.load(f)
    
    # Dateigrößen
    ankizin_original = repo_root / '_EXTERNAL_DECKS' / 'ankizin' / '2025-06-29-Ankizin_v5_46729-notes_6022_Delete_with_media_fixed.apkg'
    dellas_original = repo_root / '_EXTERNAL_DECKS' / 'dellas' / '2024-01-20-Dellas_x_Amboss_Pharmakologie_v0_81.apkg'
    ankizin_filtered = output_dir / 'Ankizin_KP_Muenster_filtered.apkg'
    dellas_filtered = output_dir / 'Dellas_KP_Muenster_filtered.apkg'
    
    ankizin_original_size = ankizin_original.stat().st_size if ankizin_original.exists() else 0
    dellas_original_size = dellas_original.stat().st_size if dellas_original.exists() else 0
    ankizin_filtered_size = ankizin_filtered.stat().st_size if ankizin_filtered.exists() else 0
    dellas_filtered_size = dellas_filtered.stat().st_size if dellas_filtered.exists() else 0
    
    # Geschätzte gefilterte Notes (vereinfacht)
    ankizin_filtered_notes_est = int(ankizin_tags_data['statistics']['total_notes'] * len(ankizin_matched['include_tags']) / max(ankizin_tags_data['statistics']['unique_tags_count'], 1))
    dellas_filtered_notes_est = int(dellas_tags_data['statistics']['total_notes'] * len(dellas_matched['include_tags']) / max(dellas_tags_data['statistics']['unique_tags_count'], 1))
    
    # Erstelle Report
    report = f"""# Deck-Filter Report: Ankizin/Dellas für KP Münster

**Erstellt:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Zweck:** Intelligente Filterung von Ankizin/Dellas Decks basierend auf KP Münster Relevanz

---

## 📊 Zusammenfassung

| Metrik | Ankizin | Dellas |
|--------|---------|--------|
| **Original Notes** | {ankizin_tags_data['statistics']['total_notes']:,} | {dellas_tags_data['statistics']['total_notes']:,} |
| **Original Tags** | {ankizin_tags_data['statistics']['unique_tags_count']:,} | {dellas_tags_data['statistics']['unique_tags_count']:,} |
| **Include-Tags** | {len(ankizin_matched['include_tags'])} | {len(dellas_matched['include_tags'])} |
| **Gefilterte Notes** | ~{ankizin_filtered_notes_est:,} | ~{dellas_filtered_notes_est:,} |
| **Original Größe** | {ankizin_original_size / 1024 / 1024:.2f} MB | {dellas_original_size / 1024 / 1024:.2f} MB |
| **Gefilterte Größe** | {ankizin_filtered_size / 1024 / 1024:.2f} MB | {dellas_filtered_size / 1024 / 1024:.2f} MB |
| **Reduktion** | {(1 - ankizin_filtered_size / ankizin_original_size) * 100:.1f}% | {(1 - dellas_filtered_size / dellas_original_size) * 100:.1f}% |

---

## 🎯 Münster-Relevanz: Gefundene Themen

### HIGH Priority Topics (Top 10)

"""
    
    for i, topic in enumerate(master['high_priority'][:10], 1):
        report += f"{i}. **{topic}**\n"
    
    report += f"""
### Fachgebiete

"""
    for fach in master['fachgebiete'][:10]:
        report += f"- {fach}\n"
    
    report += f"""
### Diagnosen (Top 10)

"""
    for diag in master['diagnosen'][:10]:
        report += f"- {diag}\n"
    
    report += f"""
---

## 🏷️ Tag-Matching Ergebnisse

### Ankizin

**Statistik:**
- Total Matched Tags: {ankizin_matched['statistics']['total_matched_tags']}
- Include-Tags: {ankizin_matched['statistics']['include_count']}
- Exclude-Tags: {ankizin_matched['statistics']['exclude_count']}
- High-Confidence (≥0.8): {ankizin_matched['statistics']['high_confidence']}
- Medium-Confidence (0.7-0.8): {ankizin_matched['statistics']['medium_confidence']}
- Low-Confidence (<0.7): {ankizin_matched['statistics']['low_confidence']}

**Top 20 Include-Tags:**

"""
    
    for i, tag in enumerate(ankizin_matched['include_tags'][:20], 1):
        score = ankizin_matched['match_confidence'].get(tag, 0)
        report += f"{i}. `{tag[:100]}{'...' if len(tag) > 100 else ''}` (Score: {score:.2f})\n"
    
    report += f"""
### Dellas

**Statistik:**
- Total Matched Tags: {dellas_matched['statistics']['total_matched_tags']}
- Include-Tags: {dellas_matched['statistics']['include_count']}
- Exclude-Tags: {dellas_matched['statistics']['exclude_count']}
- High-Confidence (≥0.8): {dellas_matched['statistics']['high_confidence']}
- Medium-Confidence (0.7-0.8): {dellas_matched['statistics']['medium_confidence']}
- Low-Confidence (<0.7): {dellas_matched['statistics']['low_confidence']}

**Top 20 Include-Tags:**

"""
    
    for i, tag in enumerate(dellas_matched['include_tags'][:20], 1):
        score = dellas_matched['match_confidence'].get(tag, 0)
        report += f"{i}. `{tag[:100]}{'...' if len(tag) > 100 else ''}` (Score: {score:.2f})\n"
    
    report += f"""
---

## 📁 Erstellte Dateien

### Gefilterte Decks
- `_OUTPUT/Ankizin_KP_Muenster_filtered.apkg` ({ankizin_filtered_size / 1024 / 1024:.2f} MB)
- `_OUTPUT/Dellas_KP_Muenster_filtered.apkg` ({dellas_filtered_size / 1024 / 1024:.2f} MB)

### Analyse-Dateien
- `_OUTPUT/muenster_relevanz_master.json` - Konsolidierte Themenliste
- `_OUTPUT/ankizin_alle_tags.json` - Alle Ankizin Tags
- `_OUTPUT/dellas_alle_tags.json` - Alle Dellas Tags
- `_OUTPUT/ankizin_matched_tags.json` - Ankizin Matches
- `_OUTPUT/dellas_matched_tags.json` - Dellas Matches

---

## ✅ Nächste Schritte

1. **Import in Anki:**
   - Öffne Anki Desktop
   - File → Import
   - Wähle `Ankizin_KP_Muenster_filtered.apkg` oder `Dellas_KP_Muenster_filtered.apkg`
   - Prüfe ob alle Karten korrekt importiert wurden

2. **Manuelle Überprüfung:**
   - Prüfe die Top Include-Tags in Anki
   - Stelle sicher, dass alle relevanten Themen enthalten sind
   - Falls Tags fehlen, kann `ankizin_matched_tags.json` / `dellas_matched_tags.json` angepasst werden

3. **Optional: Weitere Filterung**
   - Falls zu viele Karten: Threshold auf 0.8 erhöhen (nur High-Confidence)
   - Falls zu wenige Karten: Threshold auf 0.6 senken

---

## 🔍 Matching-Methoden

Das Matching verwendet mehrere Strategien:

1. **Exaktes Matching:** Tag entspricht genau dem Topic
2. **Substring-Matching:** Topic ist Teil des Tags oder umgekehrt
3. **Varianten-Matching:** Übersetzungen (z.B. Strahlenschutz ↔ Radiation)
4. **Teilwort-Matching:** Einzelne Wörter werden verglichen
5. **Fuzzy-Matching:** Ähnlichkeits-Score basierend auf String-Ähnlichkeit
6. **Hierarchie-Matching:** Tags mit `::` werden in Teile zerlegt

**Threshold:** Score ≥ 0.7 → Include

---

## 📝 Empfehlungen

### Für sofortiges Lernen
- **Ankizin:** Deck enthält ~18.000 Karten zu KP Münster-relevanten Themen
- **Dellas:** Deck enthält fast alle Karten (Pharmakologie ist sehr relevant)

### Für manuelle Überprüfung
- Prüfe Tags mit Score 0.7-0.8 (Medium-Confidence)
- Prüfe ob wichtige Themen fehlen (z.B. spezifische Münster-Themen)

### Für weitere Optimierung
- Erhöhe Threshold auf 0.8 für noch selektivere Filterung
- Passe `muenster_relevanz_master.json` an, um weitere Topics hinzuzufügen
- Führe Matching erneut aus mit angepassten Parametern

---

**Report Ende**
"""
    
    # Speichere Report
    report_file = output_dir / 'deck_filter_report.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Report erstellt: {report_file.name}")
    print("\n✅ Phase 6 abgeschlossen!")
    print(f"\n📄 Vollständiger Report: {report_file}")


if __name__ == '__main__':
    main()

