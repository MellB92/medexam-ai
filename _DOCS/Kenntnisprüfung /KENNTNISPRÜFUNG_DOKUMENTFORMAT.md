# 📚 MedExam AI - Kenntnisprüfung Dokumentformat

> **Version:** 1.0 | **Datum:** 30.11.2025 | **Ziel:** März 2025 Kenntnisprüfung
> **Erstellt für:** Claude Code, Kilo Code, Roo Code, alle AI-Agenten im Projekt

---

## 🎯 Projektziel

**200-300 qualitativ hochwertige Q&A-Paare** für die Kernfächer:
- Innere Medizin (30% der Prüfung)
- Chirurgie (20%)
- Neurologie (10%)
- Gynäkologie (10%)
- Weitere Fächer (30%)

---

## 📋 TEIL 1: Erwartetes Prüfungsformat der Prüfer

### 1.1 Strukturierte Patientenvorstellung

```
PATIENT: [Name/Pseudonym], [Alter] Jahre, [Geschlecht]
HAUPTBESCHWERDE: [Leitsymptom seit X Tagen/Stunden]
VERDACHTSDIAGNOSE: [Primäre Verdachtsdiagnose]
DIFFERENTIALDIAGNOSEN:
  1. [DD1]
  2. [DD2]
  3. [DD3]
```

**Beispiel:**
```
PATIENT: Herr M., 58 Jahre, männlich
HAUPTBESCHWERDE: Akuter retrosternaler Schmerz seit 2 Stunden, Ausstrahlung in linken Arm
VERDACHTSDIAGNOSE: Akutes Koronarsyndrom (STEMI)
DIFFERENTIALDIAGNOSEN:
  1. Instabile Angina pectoris
  2. Aortendissektion
  3. Lungenembolie
```

---

### 1.2 Medizinische Antwortstruktur (PFLICHT-Schema)

**Jede medizinische Antwort MUSS diesem Schema folgen:**

```
══════════════════════════════════════════════════════════════
FRAGE: [Medizinisches Thema]
══════════════════════════════════════════════════════════════

1️⃣ DEFINITION / KLASSIFIKATION
   ├── Definition: [Präzise medizinische Definition]
   ├── Klassifikation: Nach [NAME]-Klassifikation unterscheidet man:
   │   • Typ/Grad I: [Beschreibung]
   │   • Typ/Grad II: [Beschreibung]
   │   • Typ/Grad III: [Beschreibung]
   └── ICD-10: [Code] - [Bezeichnung]

2️⃣ ÄTIOLOGIE / PATHOPHYSIOLOGIE
   ├── Ätiologie:
   │   • Häufigste Ursache (X%): [Ursache]
   │   • Zweithäufigste (Y%): [Ursache]
   │   • Weitere: [Ursachen]
   ├── Risikofaktoren: [Liste]
   └── Pathophysiologie: [Mechanismus]

3️⃣ KLINIK / DIAGNOSTIK
   ├── Leitsymptome:
   │   • [Symptom 1]
   │   • [Symptom 2]
   ├── Diagnostisches Vorgehen:
   │   → Zunächst: Anamnese und körperliche Untersuchung
   │   → Dann: [Labordiagnostik]
   │   → Anschließend: [Bildgebung]
   │   → Ggf.: [Spezialdiagnostik]
   └── Befunde: [Typische Befunde]

4️⃣ THERAPIE (MIT EXAKTEN DOSIERUNGEN!)
   ├── Akuttherapie / Notfallmaßnahmen:
   │   • [Maßnahme]: [DOSIS mg/kg oder absolute Dosis]
   ├── First-Line Therapie:
   │   • [Medikament]: [DOSIS] [Applikationsform] [Häufigkeit]
   ├── Second-Line Therapie:
   │   • [Alternative]: [DOSIS]
   ├── Operative Therapie (falls indiziert):
   │   • [Verfahren]: [Indikation]
   └── Supportive Maßnahmen: [Liste]

5️⃣ RECHTLICHE ASPEKTE
   ├── Aufklärungspflicht: §630e BGB - [Spezifische Anforderungen]
   ├── Dokumentationspflicht: §630f BGB
   ├── Behandlungsvertrag: §630a BGB
   └── Besonderheiten: [z.B. Betreuungsrecht, Patientenverfügung]

══════════════════════════════════════════════════════════════
LEITLINIEN-REFERENZ: [AWMF-Nummer] - [Titel] ([Jahr])
EVIDENZGRAD: [A/B/C/D]
══════════════════════════════════════════════════════════════
```

---

### 1.3 Standardformulierungen (PFLICHT)

| Situation | Standardformulierung |
|-----------|---------------------|
| Diagnostik-Beginn | "Zunächst Anamnese und körperliche Untersuchung, dann..." |
| Therapie-Hierarchie | "First-Line Therapie ist..., Second-Line bei Kontraindikation/Versagen..." |
| Klassifikation | "Nach [NAME]-Klassifikation unterscheidet man..." |
| Notfall-Vorgehen | "Nach dem ABCDE-Schema: Airway, Breathing, Circulation, Disability, Exposure" |
| Dosierungen | "[Medikament] [DOSIS] mg/kg KG i.v./p.o./s.c." |
| Rechtlich | "Gemäß §630e BGB ist der Patient über... aufzuklären" |

---

### 1.4 Wichtige Klassifikationen (mit Namen!)

| Erkrankung/Befund | Klassifikation | Stufen |
|-------------------|----------------|--------|
| Schenkelhalsfraktur | **Pauwels-Klassifikation** | I (<30°), II (30-50°), III (>50°) |
| Schenkelhalsfraktur | **Garden-Klassifikation** | I-IV |
| Herzinsuffizienz | **NYHA-Klassifikation** | I-IV |
| Angina pectoris | **CCS-Klassifikation** | I-IV |
| ASA-Score | **ASA-Klassifikation** | I-VI |
| GCS | **Glasgow Coma Scale** | 3-15 |
| Verbrennung | **Verbrennungsgrade** | I-III |
| Frakturen | **AO-Klassifikation** | A, B, C |
| Wunden | **Wundklassifikation** | I-IV |

---

### 1.5 Notfall-Schema (ABCDE)

Bei jeder Frage "Wie gehen Sie vor?" im Notfall-Kontext:

```
ABCDE-SCHEMA:

A - AIRWAY (Atemweg)
    → Atemwege freimachen, Inspektion, ggf. Intubation

B - BREATHING (Atmung)
    → Atemfrequenz, SpO2, Auskultation, O2-Gabe

C - CIRCULATION (Kreislauf)
    → Puls, RR, Rekapillarisierung, Venenzugang, Volumen

D - DISABILITY (Neurologie)
    → GCS, Pupillen, Blutzucker, Temperatur

E - EXPOSURE (Entkleiden/Umgebung)
    → Vollständige Untersuchung, Wärmeerhalt
```

---

## 📋 TEIL 2: Datenquellen und Verarbeitung

### 2.1 Vorhandene Daten

| Quelle | Anzahl | Status |
|--------|--------|--------|
| JSON-Chunks | 3.547 | ✅ Vorhanden |
| Klinische Fälle (extrahiert) | 4.058 | ✅ Konsolidiert |
| PDF-Quelldokumente | 981 | ✅ Input Bucket |
| GOLD_STANDARD PDFs | ~1.450 Fragen | ✅ Zu verarbeiten |

### 2.2 Qualitätsanforderungen (aus KAN-46)

- **Keine Template-basierten Fragen** (99.9% Ablehnungsrate bei altem System)
- **LLM-basierte Q&A-Generierung** mit reichem klinischem Kontext
- **Drei-Tier-Qualitätsbewertung:**
  - Tier 1: Exzellent (prüfungsreif)
  - Tier 2: Gut (mit minimaler Überarbeitung)
  - Tier 3: Ablehnen (unbrauchbar)
- **Ziel:** >80% Tier 1/2 Fragen

### 2.3 Evidenzgrade (aus KAN-54)

| Grad | Beschreibung | Verwendung |
|------|--------------|------------|
| **A** | Starke Evidenz | Randomisierte kontrollierte Studien, Meta-Analysen |
| **B** | Moderate Evidenz | Kohortenstudien, Fall-Kontroll-Studien |
| **C** | Schwache Evidenz | Fallserien, Expertenmeinungen |
| **D** | Expertenmeinung | Konsensus ohne Studienlage |

---

## 📋 TEIL 3: Output-Formate

### 3.1 Q&A-Paar (Einzelne Frage)

```json
{
  "id": "QA-INNERE-001",
  "fachgebiet": "Innere Medizin",
  "unterkategorie": "Kardiologie",
  "schwierigkeit": "Mittel",
  "frage": "Was sind die diagnostischen Kriterien für einen STEMI?",
  "antwort": {
    "definition": "ST-Hebungsinfarkt (STEMI) ist definiert als...",
    "aetiologie": "Häufigste Ursache (>90%): Ruptur atherosklerotischer Plaques...",
    "diagnostik": "Zunächst Anamnese und körperliche Untersuchung, dann 12-Kanal-EKG innerhalb von 10 Minuten...",
    "therapie": {
      "akut": "ASS 250-500mg i.v., Heparin 5000 IE i.v., Morphin 3-5mg i.v. bei Schmerzen",
      "first_line": "Primäre PCI innerhalb von 120 Minuten (Door-to-Balloon)",
      "second_line": "Fibrinolyse bei PCI-Verzögerung >120 min"
    },
    "rechtlich": "§630e BGB: Aufklärung über Risiken der PCI, Alternativen, Prognose"
  },
  "klassifikation": "Killip-Klassifikation I-IV",
  "leitlinie": "AWMF 019-013 - Akutes Koronarsyndrom (2023)",
  "evidenzgrad": "A",
  "keywords": ["STEMI", "Myokardinfarkt", "PCI", "Troponin", "EKG"]
}
```

### 3.2 Lernkarte (Anki-Format)

```
Front: Was sind die Killip-Klassifikation-Stufen bei akutem Myokardinfarkt?
Back: 
• Killip I: Keine Herzinsuffizienz
• Killip II: Leichte HI (Rasselgeräusche basal, S3-Galopp)
• Killip III: Lungenödem
• Killip IV: Kardiogener Schock
Tags: innere, kardio, stemi, klassifikation
```

### 3.3 Zusammenfassung (Stichpunkte)

```markdown
# STEMI - Essentials für Kenntnisprüfung

## Definition
- ST-Hebungsinfarkt durch kompletten Koronarverschluss
- EKG: ST-Hebung ≥1mm in ≥2 benachbarten Ableitungen

## Diagnostik (Reihenfolge!)
1. Anamnese + KU (< 5 min)
2. 12-Kanal-EKG (< 10 min)
3. Labor: Troponin I/T, CK-MB

## Therapie (Dosierungen!)
- ASS 250-500mg i.v.
- Heparin 5000 IE i.v.
- Primäre PCI < 120 min

## Klassifikation
- Killip I-IV (Herzinsuffizienz)
- TIMI-Score (Risikostratifizierung)

## Rechtlich
- §630e BGB: Aufklärungspflicht
```

---

## 📋 TEIL 4: Dateistruktur

```
Output Bucket/
├── MASTER_KENNTNISPRÜFUNG/
│   ├── 01_INNERE_MEDIZIN/
│   │   ├── Kardiologie/
│   │   │   ├── QA_Kardiologie.md
│   │   │   ├── QA_Kardiologie.json
│   │   │   └── Lernkarten_Kardiologie.txt
│   │   ├── Gastroenterologie/
│   │   ├── Pneumologie/
│   │   └── ...
│   ├── 02_CHIRURGIE/
│   │   ├── Unfallchirurgie/
│   │   ├── Viszeralchirurgie/
│   │   └── ...
│   ├── 03_NEUROLOGIE/
│   ├── 04_GYNAEKOLOGIE/
│   ├── 05_PAEDIATRIE/
│   ├── 06_NOTFALLMEDIZIN/
│   └── 99_RECHT_UND_ETHIK/
├── MOCK_EXAMS/
│   ├── Mock_Exam_001.md
│   └── ...
└── STATISTIKEN/
    ├── Coverage_Report.md
    └── Quality_Scores.json
```

---

## ✅ Checkliste für jedes Q&A-Paar

- [ ] Definition vorhanden und präzise
- [ ] Klassifikation mit NAME genannt
- [ ] Ätiologie mit Prozentangaben (wenn verfügbar)
- [ ] Diagnostik beginnt mit "Zunächst Anamnese und KU..."
- [ ] Therapie mit EXAKTEN Dosierungen (mg/kg oder absolut)
- [ ] First-Line / Second-Line unterschieden
- [ ] §630 BGB erwähnt (mindestens e, f, oder a)
- [ ] AWMF-Leitlinien-Referenz vorhanden
- [ ] Evidenzgrad angegeben (A/B/C/D)
- [ ] Keywords für Suche vorhanden

---

## 📌 Wichtige Hinweise

1. **NIEMALS erfundene Dosierungen** - Nur aus Leitlinien oder Fachinformation
2. **NIEMALS veraltete Leitlinien** - Aktualität prüfen (max. 5 Jahre alt)
3. **IMMER ICD-10 Codes** bei Diagnosen angeben
4. **IMMER §630 BGB** bei Therapie-Fragen erwähnen
5. **ABCDE-Schema** bei JEDER Notfall-Frage

---

*Dokument erstellt: 30.11.2025 | Für: MedExam AI Projekt | Ziel: Kenntnisprüfung März 2025*
