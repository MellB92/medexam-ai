# 🚀 CODEX PROMPT: Aufgaben 2-5 (MedExamAI Prüfungsformat-Konvertierung)

**Basierend auf:** Aufgabe 1 ✅ abgeschlossen (3,170 Q&A pairs validiert)
**Nächste Schritte:** Aufgaben 2-5

---

## 📋 STATUS NACH AUFGABE 1

### ✅ Was funktioniert:
- **3,170 Q&A pairs** erfolgreich geladen
- Backup erstellt: `~/Documents/Pruefungsvorbereitung/BACKUP_30NOV/`
- Struktur: Dict mit `timestamp`, `original_file`, `stats`, `qa_pairs`

### ⚠️ Identifizierte Lücken:
| Feld | Status | Lösung |
|------|--------|--------|
| `question` / `answer` | ✅ Vorhanden | Direkt mappen |
| `source` / `quelle` | ❌ Fehlt | Aus `source_case_title` ableiten |
| `category` / `kategorie` | ❌ Fehlt | Aus `specialty` / `tags` ableiten |
| `patientenvorstellung` | ❌ Fehlt | Synthetisch generieren |
| `dosierungen` | ⚠️ Teilweise | Mit Perplexity anreichern |
| `klassifikationen` | ⚠️ Teilweise | Extrahieren + verifizieren |

---

## 🎯 AUFGABE 2: Konvertierung ins Prüfungsformat

### 2.1 ZIELFORMAT (Kenntnisprüfung Deutschland)

**Basierend auf offiziellem IMPP-Format** (Referenz: [DOI 10.1055/a-1553-3962](https://doi.org/10.1055/a-1553-3962))

```json
{
  "id": "KP-0001",
  "frage": "Was ist eine Pneumonie?",
  
  "patientenvorstellung": {
    "format": "[Name], [Alter] Jahre → [Hauptbeschwerde] → V.a. [Verdachtsdiagnose] → DD: [Differentialdiagnosen]",
    "beispiel": "Herr Müller, 65 Jahre, Husten seit 5 Tagen → V.a. ambulant erworbene Pneumonie → DD: akute Bronchitis, Tuberkulose, Lungenkarzinom"
  },
  
  "antwort": {
    "1_definition": {
      "inhalt": "Pneumonie: Akute Entzündung des Lungenparenchyms mit Infiltration der Alveolen.",
      "klassifikation": "Nach ATS/IDSA: CAP (ambulant erworben), HAP (nosokomial), VAP (beatmungsassoziiert)",
      "hinweis": "IMMER Klassifikation MIT Autorennamen nennen!"
    },
    
    "2_aetiologie": {
      "inhalt": "Häufigste Erreger: S. pneumoniae (40-50%), H. influenzae, M. pneumoniae, Legionellen.",
      "risikofaktoren": "Alter >65, COPD, Immunsuppression, Aspiration, Rauchen",
      "pathophysiologie": "Erregerinvasion → Alveolarschädigung → Exsudation → Konsolidierung"
    },
    
    "3_diagnostik": {
      "vorgehen": "Zunächst Anamnese und körperliche Untersuchung, dann:",
      "schritte": [
        "1. Inspektion: Tachypnoe, Zyanose, Nasenflügeln",
        "2. Auskultation: Feuchte Rasselgeräusche, Bronchialatmen",
        "3. Perkussion: Dämpfung über Infiltrat",
        "4. Labor: CRP↑, Leukozyten↑, PCT bei bakteriell",
        "5. Bildgebung: Röntgen-Thorax in 2 Ebenen, ggf. CT"
      ],
      "klassifikation_scores": ["CRB-65", "CURB-65", "PSI-Score (Fine)"]
    },
    
    "4_therapie": {
      "first_line": "Amoxicillin 3×1g p.o. für 5-7 Tage",
      "second_line": "Moxifloxacin 400mg 1×/d p.o. für 5 Tage",
      "schwere_cap": "Ampicillin/Sulbactam 3×3g i.v. + Azithromycin 500mg i.v.",
      "dosierungen": [
        "Amoxicillin: 3×1000mg p.o.",
        "Moxifloxacin: 1×400mg p.o.",
        "Ampicillin/Sulbactam: 3×3g i.v.",
        "Azithromycin: 1×500mg i.v."
      ],
      "hinweis": "IMMER exakte Dosierungen in mg, Frequenz und Dauer angeben!"
    },
    
    "5_rechtlich": {
      "paragraph": "§630d BGB (Einwilligung), §630e BGB (Aufklärung), §630f BGB (Dokumentation)",
      "aufklaerung": "Über Diagnose, Prognose, Therapieoptionen, Risiken, Alternativen",
      "dokumentation": "Befunde, Diagnose, Therapie, Aufklärungsgespräch",
      "hinweis": "Bei invasiven Maßnahmen: Schriftliche Einwilligung!"
    }
  },
  
  "notfall_schema": null,
  
  "metadata": {
    "quelle": "AWMF S3-Leitlinie Pneumonie 2021",
    "specialty": "Pneumologie/Innere Medizin",
    "schwierigkeit": "mittel",
    "tags": ["Infektiologie", "Pneumologie", "Antibiotika"],
    "pruefungsrelevanz": "hoch",
    "letzte_aktualisierung": "2025-11-30"
  }
}
```

### 2.2 NOTFALL-SCHEMA (für Akut-Fälle)

```json
"notfall_schema": {
  "A_airway": {
    "check": "Atemwege frei?",
    "action": "Kopf überstrecken, Esmarch-Handgriff, Guedel-/Wendl-Tubus",
    "eskalation": "Intubation bei GCS ≤8"
  },
  "B_breathing": {
    "check": "Atmung vorhanden? SpO2?",
    "action": "O2 15L/min via Maske, Ziel SpO2 >94%",
    "eskalation": "Beatmung bei Ateminsuffizienz"
  },
  "C_circulation": {
    "check": "Puls tastbar? RR? Rekapzeit?",
    "action": "2 großlumige Zugänge (≥18G), Volumen 500ml NaCl",
    "eskalation": "Katecholamine bei persistierender Hypotonie"
  },
  "D_disability": {
    "check": "GCS? Pupillen? BZ?",
    "action": "Neurologische Kurzuntersuchung",
    "eskalation": "CCT bei fokalen Defiziten"
  },
  "E_exposure": {
    "check": "Entkleiden, Temperatur, Ganzkörperinspektion",
    "action": "Wärmeerhalt, Traumacheck",
    "eskalation": "Fokussierte Sonographie (FAST)"
  }
}
```

### 2.3 KONVERTIERUNGS-SKRIPT

Erstelle `scripts/convert_to_exam_format.py`:

```python
#!/usr/bin/env python3
"""
MedExamAI: Konvertierung ins Kenntnisprüfung-Format
===================================================

Konvertiert Q&A pairs in das standardisierte Prüfungsformat.
Integriert Sicherheitsmechanismen aus MEDEXAMAI_SICHERHEIT_UND_VALIDIERUNG.md
"""

import json
import re
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict

# ============================================================================
# SICHERHEITS-FUNKTIONEN (aus Teil 1 integriert)
# ============================================================================

def safe_backup(filepath: str) -> str:
    """Erstellt Backup bevor Daten verändert werden."""
    import shutil
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{filepath}.backup_{timestamp}"
    if os.path.exists(filepath):
        shutil.copy2(filepath, backup_path)
        print(f"✅ Backup erstellt: {backup_path}")
    return backup_path

def safe_filter(data: list, filter_func, name: str = "filter") -> list:
    """Filter mit Sicherheitsprüfung - STOPPT bei >90% Verlust."""
    original_count = len(data)
    filtered = [d for d in data if filter_func(d)]
    filtered_count = len(filtered)
    
    loss_percent = (1 - filtered_count / original_count) * 100 if original_count > 0 else 0
    
    if loss_percent > 90:
        raise ValueError(f"🚫 KRITISCH: {name} würde {loss_percent:.1f}% löschen. Abgebrochen!")
    
    if loss_percent > 50:
        print(f"⚠️ WARNUNG: {name} entfernt {loss_percent:.1f}% der Daten")
        print(f"   Original: {original_count} → Nach Filter: {filtered_count}")
    
    print(f"✅ {name}: {original_count} → {filtered_count} ({loss_percent:.1f}% entfernt)")
    return filtered

# ============================================================================
# KLASSIFIKATIONEN & DOSIERUNGEN (Referenzdaten)
# ============================================================================

KNOWN_CLASSIFICATIONS = {
    # Kardiologie
    "NYHA": "New York Heart Association - Herzinsuffizienz-Stadien I-IV",
    "CHA2DS2-VASc": "Schlaganfallrisiko bei Vorhofflimmern (0-9 Punkte)",
    "HAS-BLED": "Blutungsrisiko unter Antikoagulation",
    "KILLIP": "Killip-Klassifikation - Herzinfarkt-Schweregrad",
    "TIMI": "Thrombolysis in Myocardial Infarction - Risikoscore",
    
    # Pneumologie
    "CRB-65": "Pneumonie-Schweregrad (ambulant): Confusion, Respiration, BP, Alter",
    "CURB-65": "Pneumonie-Schweregrad (stationär) + Urea",
    "PSI": "Pneumonia Severity Index (Fine-Score)",
    "GOLD": "COPD-Schweregrad nach Global Initiative",
    
    # Trauma/Orthopädie
    "GARDEN": "Garden-Klassifikation - Schenkelhalsfraktur I-IV",
    "PAUWELS": "Pauwels-Klassifikation - Frakturwinkel",
    "AO": "AO-Klassifikation - Frakturen",
    "GUSTILO": "Gustilo-Anderson - Offene Frakturen I-III",
    
    # Neurologie
    "HUNT-HESS": "Hunt und Hess - Subarachnoidalblutung",
    "FISHER": "Fisher-Skala - SAB im CT",
    "GCS": "Glasgow Coma Scale (3-15)",
    "NIHSS": "NIH Stroke Scale - Schlaganfall-Schwere",
    
    # Onkologie
    "TNM": "Tumor-Node-Metastasis Klassifikation",
    "FIGO": "Gynäkologische Tumoren",
    "ANN-ARBOR": "Ann-Arbor-Stadien - Lymphome",
    "GLEASON": "Gleason-Score - Prostatakarzinom",
    
    # Gastroenterologie
    "CHILD-PUGH": "Child-Pugh-Score - Leberzirrhose",
    "MELD": "Model for End-Stage Liver Disease",
    "FORREST": "Forrest-Klassifikation - GI-Blutung",
    "RANSON": "Ranson-Kriterien - Pankreatitis",
    
    # Nephrologie
    "KDIGO": "Kidney Disease: Improving Global Outcomes - AKI/CKD",
    "AKIN": "Acute Kidney Injury Network",
    
    # Psychiatrie
    "ICD-10-F": "Psychiatrische Diagnosen nach ICD-10",
    "GAF": "Global Assessment of Functioning",
}

DOSAGE_PATTERNS = [
    r'\d+\s*(?:mg|g|µg|mcg|ml|IE|IU)(?:/(?:kg|d|h|Tag|Stunde))?',
    r'\d+[x×]\d+\s*(?:mg|g)',
    r'\d+-\d+-\d+',  # Schema wie 1-0-1
    r'\d+\s*(?:mg|g)\s*(?:p\.?o\.|i\.?v\.|s\.?c\.|i\.?m\.)',
]

# ============================================================================
# DATENKLASSEN
# ============================================================================

@dataclass
class ExamQuestion:
    """Prüfungsfrage im Zielformat."""
    id: str
    frage: str
    patientenvorstellung: Optional[str]
    antwort: Dict
    klassifikationen: List[str]
    dosierungen: List[str]
    quelle: str
    notfall_schema: Optional[Dict]
    metadata: Dict
    
    # Enrichment-Flags
    needs_dose_enrichment: bool = False
    needs_classification_verification: bool = False
    needs_legal_enrichment: bool = False

# ============================================================================
# KONVERTIERUNGSLOGIK
# ============================================================================

class ExamFormatConverter:
    """Konvertiert Q&A pairs ins Kenntnisprüfung-Format."""
    
    def __init__(self, input_file: str, output_file: str):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.stats = defaultdict(int)
        self.enrichment_needed = []
        
    def load_data(self) -> List[Dict]:
        """Lädt Q&A pairs aus Backup."""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle verschiedene Strukturen
        if isinstance(data, dict) and 'qa_pairs' in data:
            return data['qa_pairs']
        elif isinstance(data, list):
            return data
        else:
            raise ValueError(f"Unbekannte Datenstruktur: {type(data)}")
    
    def extract_classifications(self, text: str) -> List[str]:
        """Extrahiert bekannte Klassifikationen aus Text."""
        found = []
        text_upper = text.upper()
        
        for name, description in KNOWN_CLASSIFICATIONS.items():
            if name in text_upper:
                found.append(f"{name} ({description.split(' - ')[0] if ' - ' in description else name})")
        
        return list(set(found))
    
    def extract_dosages(self, text: str) -> List[str]:
        """Extrahiert Dosierungen aus Text."""
        dosages = []
        
        for pattern in DOSAGE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dosages.extend(matches)
        
        return list(set(dosages))
    
    def generate_patient_presentation(self, qa: Dict) -> str:
        """Generiert synthetische Patientenvorstellung."""
        # Versuche Infos aus verschiedenen Feldern zu extrahieren
        question = qa.get('question', qa.get('frage', ''))
        answer = qa.get('answer', qa.get('antwort', ''))
        specialty = qa.get('specialty', 'Innere Medizin')
        
        # Einfache Heuristik - kann später mit LLM verbessert werden
        if 'Notfall' in question or 'akut' in question.lower():
            return f"Patient, unbekanntes Alter, Notaufnahme → Akute Symptomatik → V.a. {question[:50]}... → DD: siehe Antwort"
        else:
            return f"Patient in {specialty}-Sprechstunde → {question[:60]}... → Systematische Abklärung erforderlich"
    
    def parse_answer_to_schema(self, answer: str) -> Dict:
        """Zerlegt Antwort in 5-Punkte-Schema."""
        schema = {
            "1_definition": None,
            "2_aetiologie": None,
            "3_diagnostik": None,
            "4_therapie": None,
            "5_rechtlich": None
        }
        
        # Versuche Abschnitte zu erkennen
        answer_lower = answer.lower()
        
        # Definition
        if 'definition' in answer_lower or 'ist ein' in answer_lower or 'bezeichnet' in answer_lower:
            # Extrahiere ersten Satz oder Abschnitt
            first_sentence = answer.split('.')[0] + '.'
            schema["1_definition"] = first_sentence
        
        # Ätiologie
        aetiologie_markers = ['ursache', 'ätiologie', 'risikofaktor', 'pathophysiologie', 'entsteh']
        for marker in aetiologie_markers:
            if marker in answer_lower:
                schema["2_aetiologie"] = "TODO_enrich"
                break
        
        # Diagnostik
        diagnostik_markers = ['diagnostik', 'untersuchung', 'labor', 'bildgebung', 'anamnese']
        for marker in diagnostik_markers:
            if marker in answer_lower:
                schema["3_diagnostik"] = "TODO_enrich"
                break
        
        # Therapie
        therapie_markers = ['therapie', 'behandlung', 'medikament', 'mg', 'dosierung']
        for marker in therapie_markers:
            if marker in answer_lower:
                schema["4_therapie"] = "TODO_enrich"
                break
        
        # Rechtlich (fast immer TODO)
        schema["5_rechtlich"] = "TODO_enrich: §630d-f BGB prüfen"
        
        # Fallback: Gesamte Antwort als Definition wenn nichts erkannt
        if not any(schema.values()):
            schema["1_definition"] = answer[:500] + "..." if len(answer) > 500 else answer
        
        return schema
    
    def is_emergency_topic(self, qa: Dict) -> bool:
        """Prüft ob Notfall-Thema."""
        emergency_keywords = [
            'notfall', 'reanimation', 'schock', 'akut', 'anaphylaxie',
            'herzinfarkt', 'apoplex', 'polytrauma', 'sepsis', 'acs',
            'kammerflimmern', 'asystolie', 'bewusstlos'
        ]
        
        text = (qa.get('question', '') + qa.get('answer', '')).lower()
        return any(kw in text for kw in emergency_keywords)
    
    def create_emergency_schema(self) -> Dict:
        """Erstellt Standard-ABCDE-Schema."""
        return {
            "A_airway": "Atemwege freimachen, Kopf überstrecken, Guedel-Tubus",
            "B_breathing": "O2 15L/min via Maske, SpO2 Ziel >94%",
            "C_circulation": "2 großlumige Zugänge, Volumen, ggf. Katecholamine",
            "D_disability": "GCS, Pupillen, BZ messen",
            "E_exposure": "Entkleiden, Temperatur, Ganzkörperinspektion"
        }
    
    def convert_single(self, qa: Dict, index: int) -> ExamQuestion:
        """Konvertiert einzelnes Q&A pair."""
        self.stats['total'] += 1
        
        # Basis-Felder
        question = qa.get('question', qa.get('frage', ''))
        answer = qa.get('answer', qa.get('antwort', ''))
        
        # Quelle ableiten
        source = (
            qa.get('source') or 
            qa.get('quelle') or 
            qa.get('source_case_title', '').split(' - ')[0] if qa.get('source_case_title') else None or
            'Quelle nicht angegeben'
        )
        
        # Klassifikationen & Dosierungen extrahieren
        full_text = question + ' ' + answer
        classifications = self.extract_classifications(full_text)
        dosages = self.extract_dosages(answer)
        
        # Antwort ins Schema überführen
        answer_schema = self.parse_answer_to_schema(answer)
        
        # Flags setzen
        needs_dose = len(dosages) == 0 and any(kw in answer.lower() for kw in ['therapie', 'behandlung', 'medikament'])
        needs_classification = len(classifications) == 0
        needs_legal = answer_schema.get('5_rechtlich', '').startswith('TODO')
        
        if needs_dose:
            self.stats['needs_dose_enrichment'] += 1
        if needs_classification:
            self.stats['needs_classification'] += 1
        if needs_legal:
            self.stats['needs_legal'] += 1
        
        # Notfall-Schema
        notfall = self.create_emergency_schema() if self.is_emergency_topic(qa) else None
        if notfall:
            self.stats['emergency_topics'] += 1
        
        # Metadata
        metadata = {
            "quelle": source,
            "specialty": qa.get('specialty', 'Allgemein'),
            "tags": qa.get('tags', []),
            "original_id": qa.get('id', f"orig_{index}"),
            "konvertiert_am": datetime.now().isoformat()
        }
        
        return ExamQuestion(
            id=f"KP-{index:04d}",
            frage=question,
            patientenvorstellung=self.generate_patient_presentation(qa),
            antwort=answer_schema,
            klassifikationen=classifications,
            dosierungen=dosages,
            quelle=source,
            notfall_schema=notfall,
            metadata=metadata,
            needs_dose_enrichment=needs_dose,
            needs_classification_verification=needs_classification,
            needs_legal_enrichment=needs_legal
        )
    
    def convert_all(self) -> List[Dict]:
        """Konvertiert alle Q&A pairs."""
        print("\n" + "="*60)
        print("🔄 STARTE KONVERTIERUNG INS PRÜFUNGSFORMAT")
        print("="*60)
        
        # Backup erstellen
        safe_backup(str(self.output_file))
        
        # Daten laden
        qa_pairs = self.load_data()
        print(f"📥 Geladen: {len(qa_pairs)} Q&A pairs")
        
        # Konvertieren
        converted = []
        for i, qa in enumerate(qa_pairs):
            try:
                exam_q = self.convert_single(qa, i + 1)
                converted.append(asdict(exam_q))
            except Exception as e:
                print(f"⚠️ Fehler bei Index {i}: {e}")
                self.stats['errors'] += 1
        
        # Statistik ausgeben
        print("\n" + "-"*60)
        print("📊 KONVERTIERUNGS-STATISTIK:")
        print("-"*60)
        print(f"  ✅ Erfolgreich konvertiert: {len(converted)}")
        print(f"  🏥 Notfall-Themen (ABCDE): {self.stats['emergency_topics']}")
        print(f"  💊 Braucht Dosierungs-Enrichment: {self.stats['needs_dose_enrichment']}")
        print(f"  📋 Braucht Klassifikations-Verifizierung: {self.stats['needs_classification']}")
        print(f"  ⚖️ Braucht Rechtliches Enrichment: {self.stats['needs_legal']}")
        print(f"  ❌ Fehler: {self.stats['errors']}")
        
        return converted
    
    def save(self, data: List[Dict]):
        """Speichert konvertierte Daten."""
        # Sicherstellen, dass Output-Verzeichnis existiert
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Gespeichert: {self.output_file}")
        print(f"   Größe: {self.output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    def run(self):
        """Hauptmethode."""
        converted = self.convert_all()
        self.save(converted)
        
        # Enrichment-Liste für Aufgabe 3
        enrichment_file = self.output_file.parent / "enrichment_needed.json"
        enrichment_list = [
            q for q in converted 
            if q.get('needs_dose_enrichment') or 
               q.get('needs_classification_verification') or 
               q.get('needs_legal_enrichment')
        ]
        
        with open(enrichment_file, 'w', encoding='utf-8') as f:
            json.dump(enrichment_list, f, ensure_ascii=False, indent=2)
        
        print(f"📝 Enrichment-Liste: {enrichment_file} ({len(enrichment_list)} Einträge)")
        
        return converted


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='MedExamAI: Konvertierung ins Prüfungsformat')
    parser.add_argument('--input', '-i', 
                        default='~/Documents/Pruefungsvorbereitung/BACKUP_30NOV/qa_enhanced_quality.json',
                        help='Input-Datei (Q&A pairs)')
    parser.add_argument('--output', '-o',
                        default='output/kenntnisprufung_formatted.json',
                        help='Output-Datei (Prüfungsformat)')
    
    args = parser.parse_args()
    
    # Pfade expandieren
    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()
    
    converter = ExamFormatConverter(str(input_path), str(output_path))
    converter.run()
```

---

## 🤖 AUFGABE 3: Perplexity API Enrichment

### 3.1 Setup & Konfiguration

```python
#!/usr/bin/env python3
"""
MedExamAI: Perplexity API Enrichment
====================================

Ergänzt fehlende Dosierungen, Klassifikationen und rechtliche Paragraphen.
"""

import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
import requests

# ============================================================================
# KONFIGURATION
# ============================================================================

PERPLEXITY_KEYS = [
    os.getenv("PERPLEXITY_API_KEY_1"),
    os.getenv("PERPLEXITY_API_KEY_2"),
]

PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

# Rate Limiting
REQUESTS_PER_MINUTE = 20
REQUEST_DELAY = 60 / REQUESTS_PER_MINUTE

# Cache
CACHE_DIR = Path("cache")
CACHE_FILE = CACHE_DIR / "perplexity_enrichment.json"

# ============================================================================
# QUERY TEMPLATES (Deutsch, medizinisch präzise)
# ============================================================================

TEMPLATES = {
    "dosierung": """
Du bist ein deutscher Facharzt. Beantworte präzise nach aktueller AWMF-Leitlinie:

FRAGE: Exakte Dosierung von {medikament} bei {indikation}?

ANTWORTFORMAT:
- Standarddosis: [mg/Frequenz/Dauer]
- Niereninsuffizienz: [Anpassung]
- Kontraindikationen: [Liste]
- Leitlinie: [Quelle mit Jahr]

Antworte NUR mit den Fakten, keine Einleitung.
""",

    "klassifikation": """
Du bist ein deutscher Facharzt. Beantworte präzise:

FRAGE: Welche Klassifikation(en) gibt es für {krankheit}?

ANTWORTFORMAT pro Klassifikation:
- Name: [z.B. NYHA, Garden, etc.]
- Autor/Organisation: [wer hat sie entwickelt]
- Stufen/Stadien: [kurze Beschreibung jeder Stufe]
- Klinische Relevanz: [wann anwenden]

Antworte NUR mit den Fakten.
""",

    "rechtlich": """
Du bist ein deutscher Medizinrechtler. Beantworte präzise:

FRAGE: Welche rechtlichen Aspekte sind bei {kontext} relevant?

ANTWORTFORMAT:
- Relevante Paragraphen: §630d, §630e, §630f BGB etc.
- Aufklärungspflicht: [was muss aufgeklärt werden]
- Dokumentationspflicht: [was muss dokumentiert werden]
- Besonderheiten: [z.B. bei Minderjährigen, Notfall]

Antworte NUR mit den Fakten.
"""
}

# ============================================================================
# ENRICHMENT ENGINE
# ============================================================================

class PerplexityEnricher:
    """Enrichment via Perplexity API."""
    
    def __init__(self):
        self.cache = self._load_cache()
        self.current_key_index = 0
        self.request_count = 0
        self.stats = {"total": 0, "cached": 0, "api_calls": 0, "errors": 0}
    
    def _load_cache(self) -> Dict:
        """Lädt Cache."""
        CACHE_DIR.mkdir(exist_ok=True)
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Speichert Cache."""
        with open(CACHE_FILE, 'w') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
    
    def _get_cache_key(self, query: str) -> str:
        """Generiert Cache-Key."""
        return hashlib.md5(query.encode()).hexdigest()
    
    def _get_api_key(self) -> Optional[str]:
        """Rotiert durch API Keys."""
        for i in range(len(PERPLEXITY_KEYS)):
            key = PERPLEXITY_KEYS[(self.current_key_index + i) % len(PERPLEXITY_KEYS)]
            if key:
                self.current_key_index = (self.current_key_index + i + 1) % len(PERPLEXITY_KEYS)
                return key
        return None
    
    def _call_api(self, prompt: str) -> Optional[str]:
        """Ruft Perplexity API auf."""
        api_key = self._get_api_key()
        if not api_key:
            print("❌ Keine gültigen API Keys verfügbar")
            return None
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {"role": "system", "content": "Du bist ein präziser deutscher Medizinexperte."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(PERPLEXITY_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API-Fehler: {e}")
            self.stats['errors'] += 1
            return None
    
    def query(self, template_name: str, **kwargs) -> Optional[str]:
        """Führt Query aus (mit Caching)."""
        self.stats['total'] += 1
        
        # Template füllen
        template = TEMPLATES.get(template_name)
        if not template:
            print(f"❌ Unbekanntes Template: {template_name}")
            return None
        
        prompt = template.format(**kwargs)
        cache_key = self._get_cache_key(prompt)
        
        # Cache prüfen
        if cache_key in self.cache:
            self.stats['cached'] += 1
            return self.cache[cache_key]
        
        # Rate Limiting
        time.sleep(REQUEST_DELAY)
        
        # API aufrufen
        result = self._call_api(prompt)
        
        if result:
            self.cache[cache_key] = result
            self._save_cache()
            self.stats['api_calls'] += 1
        
        return result
    
    def enrich_question(self, question: Dict) -> Dict:
        """Reichert einzelne Frage an."""
        enriched = question.copy()
        
        # Dosierung ergänzen
        if question.get('needs_dose_enrichment'):
            # Extrahiere Medikament aus Therapie-Abschnitt
            therapie = question.get('antwort', {}).get('4_therapie', '')
            if therapie and therapie != 'TODO_enrich':
                # Versuche Medikament zu identifizieren (vereinfacht)
                result = self.query('dosierung', 
                                    medikament='[aus Kontext]', 
                                    indikation=question.get('frage', '')[:100])
                if result:
                    enriched['antwort']['4_therapie'] = result
                    enriched['needs_dose_enrichment'] = False
        
        # Klassifikation ergänzen
        if question.get('needs_classification_verification'):
            krankheit = question.get('frage', '')[:100]
            result = self.query('klassifikation', krankheit=krankheit)
            if result:
                # Parse Klassifikationen aus Antwort
                enriched['klassifikationen_details'] = result
                enriched['needs_classification_verification'] = False
        
        # Rechtliches ergänzen
        if question.get('needs_legal_enrichment'):
            kontext = question.get('frage', '')[:100]
            result = self.query('rechtlich', kontext=kontext)
            if result:
                enriched['antwort']['5_rechtlich'] = result
                enriched['needs_legal_enrichment'] = False
        
        return enriched
    
    def enrich_all(self, questions: List[Dict], max_enrichments: int = 100) -> List[Dict]:
        """Reichert alle Fragen an (mit Limit)."""
        print("\n" + "="*60)
        print("🤖 STARTE PERPLEXITY ENRICHMENT")
        print("="*60)
        
        enriched = []
        enrichment_count = 0
        
        for i, q in enumerate(questions):
            needs_enrichment = (
                q.get('needs_dose_enrichment') or
                q.get('needs_classification_verification') or
                q.get('needs_legal_enrichment')
            )
            
            if needs_enrichment and enrichment_count < max_enrichments:
                print(f"  🔄 Enriching {q.get('id', i)}...")
                enriched_q = self.enrich_question(q)
                enriched.append(enriched_q)
                enrichment_count += 1
            else:
                enriched.append(q)
            
            if (i + 1) % 100 == 0:
                print(f"  📊 Fortschritt: {i + 1}/{len(questions)}")
        
        # Statistik
        print("\n" + "-"*60)
        print("📊 ENRICHMENT-STATISTIK:")
        print("-"*60)
        print(f"  📥 Total Queries: {self.stats['total']}")
        print(f"  💾 Aus Cache: {self.stats['cached']}")
        print(f"  🌐 API-Aufrufe: {self.stats['api_calls']}")
        print(f"  ❌ Fehler: {self.stats['errors']}")
        
        return enriched


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='MedExamAI: Perplexity Enrichment')
    parser.add_argument('--input', '-i',
                        default='output/kenntnisprufung_formatted.json',
                        help='Input-Datei (formatierte Fragen)')
    parser.add_argument('--output', '-o',
                        default='output/kenntnisprufung_enriched.json',
                        help='Output-Datei (angereicherte Fragen)')
    parser.add_argument('--max', '-m', type=int, default=100,
                        help='Max. Anzahl Enrichments (Default: 100)')
    
    args = parser.parse_args()
    
    # Laden
    with open(args.input, 'r') as f:
        questions = json.load(f)
    
    print(f"📥 Geladen: {len(questions)} Fragen")
    
    # Enrichen
    enricher = PerplexityEnricher()
    enriched = enricher.enrich_all(questions, max_enrichments=args.max)
    
    # Speichern
    with open(args.output, 'w') as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Gespeichert: {args.output}")
```

---

## 📄 AUFGABE 4: Post-Mortem Bericht

**Bereits definiert - siehe ursprünglichen Prompt.**

Erstelle `docs/POST_MORTEM_DATENVERLUST_30NOV.md` mit:
- Timeline des Vorfalls
- Root Cause Analyse
- Präventionsmaßnahmen
- Lessons Learned

---

## 🛡️ AUFGABE 5: Automatisierung & Validierung

### 5.1 Input/Output Validator

**Integriere den vollständigen Code aus `MEDEXAMAI_SICHERHEIT_UND_VALIDIERUNG.md`:**

- `InputOutputValidator` Klasse
- `quality_sample_check()` Funktion
- CLI-Validierungsskript

### 5.2 GitHub Actions

Erstelle `.github/workflows/backup-qa-data.yml` (siehe Dokument)

### 5.3 Validierungs-Workflow

```bash
# Nach JEDER Pipeline-Operation ausführen:

# 1. Input/Output Coverage prüfen
python validation/input_output_validator.py \
  --input ./input_bucket \
  --output ./output/kenntnisprufung_enriched.json

# 2. Qualitätsstichprobe
python validation/quality_sample.py \
  --file ./output/kenntnisprufung_enriched.json \
  --sample 20

# 3. State-Files prüfen
python scripts/state_monitor.py --dir ./output
```

---

## ✅ DEFINITION OF DONE (Gesamt)

| Aufgabe | Kriterium | Status |
|---------|-----------|--------|
| 2 | `kenntnisprufung_formatted.json` mit 3,170 Einträgen | ⏳ |
| 2 | Mindestens 100 Fragen im 5-Punkte-Schema | ⏳ |
| 2 | `enrichment_needed.json` mit Flags erstellt | ⏳ |
| 3 | Perplexity-Skript funktioniert | ⏳ |
| 3 | Mindestens 10 Dosierungs-Lookups erfolgreich | ⏳ |
| 3 | `kenntnisprufung_enriched.json` erstellt | ⏳ |
| 4 | Post-Mortem Bericht vollständig | ⏳ |
| 5 | GitHub Backup-Workflow committed | ⏳ |
| 5 | Validierungs-Skripte lauffähig | ⏳ |

---

## 🚀 STARTE JETZT MIT AUFGABE 2

```bash
# 1. Skript erstellen
mkdir -p scripts output

# 2. convert_to_exam_format.py erstellen (Code oben)

# 3. Ausführen
python scripts/convert_to_exam_format.py \
  --input ~/Documents/Pruefungsvorbereitung/BACKUP_30NOV/qa_enhanced_quality.json \
  --output output/kenntnisprufung_formatted.json

# 4. Ergebnis prüfen
python3 -c "import json; d=json.load(open('output/kenntnisprufung_formatted.json')); print(f'✅ {len(d)} Fragen konvertiert'); print(json.dumps(d[0], indent=2, ensure_ascii=False)[:1000])"
```

**Berichte nach Abschluss von Aufgabe 2 mit:**
1. Anzahl konvertierter Fragen
2. Statistik (Notfälle, Enrichment-Bedarf)
3. Beispiel-Output (1 Frage im Zielformat)
4. Offene TODOs
