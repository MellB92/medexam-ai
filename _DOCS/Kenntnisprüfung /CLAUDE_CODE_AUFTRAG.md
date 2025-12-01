# 🤖 CLAUDE CODE AUFTRAG: Q&A-Generierung für Kenntnisprüfung

> **WICHTIG:** Diesen Prompt in Claude Code (Cursor Extension) einfügen
> **Shortcut:** `Shift + Cmd + P` → "Claude" → Claude Code öffnen
> **Anweisung:** NICHT AUFHÖREN bis die Aufgabe vollständig erledigt ist!

---

## 📋 AUFTRAG AN CLAUDE CODE

```
═══════════════════════════════════════════════════════════════════════════════
🎯 MISSION: Generiere prüfungskonforme Q&A-Paare für die Kenntnisprüfung März 2025
═══════════════════════════════════════════════════════════════════════════════

Du bist ein medizinischer Prüfungsexperte für die deutsche Kenntnisprüfung.
Deine Aufgabe ist es, aus vorhandenen klinischen Fällen hochwertige Q&A-Paare 
zu generieren, die EXAKT dem deutschen Prüfungsformat entsprechen.

ARBEITE KONTINUIERLICH bis alle Aufgaben erledigt sind. STOPPE NICHT.

═══════════════════════════════════════════════════════════════════════════════
📁 DATENQUELLEN
═══════════════════════════════════════════════════════════════════════════════

1. Klinische Fälle: /Users/user/Documents/Pruefungsvorbereitung/Comet API/Output Bucket/MASTER_PRUEFUNGSVORBEREITUNG_M3.json
   → 4.058 extrahierte klinische Fälle

2. GOLD_STANDARD PDFs: /Users/user/Documents/Pruefungsvorbereitung/Comet API/Input Bucket/
   → ~1.450 Original-Prüfungsfragen

3. Dokumentformat: Lies zuerst KENNTNISPRÜFUNG_DOKUMENTFORMAT.md im selben Ordner

═══════════════════════════════════════════════════════════════════════════════
📐 PFLICHT-ANTWORTFORMAT FÜR JEDE MEDIZINISCHE FRAGE
═══════════════════════════════════════════════════════════════════════════════

JEDE Antwort MUSS diesem Schema folgen:

1️⃣ DEFINITION / KLASSIFIKATION
   - Präzise medizinische Definition
   - Klassifikation IMMER mit NAME (z.B. "Nach Pauwels-Klassifikation...")
   - ICD-10 Code angeben

2️⃣ ÄTIOLOGIE / PATHOPHYSIOLOGIE
   - Häufigste Ursachen mit Prozentangaben
   - Risikofaktoren
   - Pathomechanismus

3️⃣ KLINIK / DIAGNOSTIK
   - IMMER beginnen mit: "Zunächst Anamnese und körperliche Untersuchung, dann..."
   - Diagnostik-Algorithmus Schritt für Schritt
   - Typische Befunde

4️⃣ THERAPIE (KRITISCH: EXAKTE DOSIERUNGEN!)
   - Akuttherapie: [Medikament] [DOSIS in mg/kg ODER absolute Dosis] [Applikation]
   - First-Line Therapie ist...
   - Second-Line bei Kontraindikation/Versagen...
   - NIEMALS "übliche Dosis" schreiben - IMMER exakte mg/kg Angaben!

5️⃣ RECHTLICHE ASPEKTE
   - §630a BGB: Behandlungsvertrag
   - §630e BGB: Aufklärungspflicht
   - §630f BGB: Dokumentationspflicht
   - Mindestens EINEN Paragraphen erwähnen!

6️⃣ LEITLINIEN-REFERENZ
   - AWMF-Nummer
   - Titel und Jahr
   - Evidenzgrad (A/B/C/D)

═══════════════════════════════════════════════════════════════════════════════
🚨 NOTFALL-FRAGEN: ABCDE-SCHEMA PFLICHT
═══════════════════════════════════════════════════════════════════════════════

Bei JEDER Frage "Wie gehen Sie vor?" im Notfall-Kontext:

A - AIRWAY: Atemwege freimachen, Inspektion, ggf. Intubation
B - BREATHING: Atemfrequenz, SpO2, Auskultation, O2-Gabe
C - CIRCULATION: Puls, RR, Venenzugang, Volumen
D - DISABILITY: GCS, Pupillen, BZ
E - EXPOSURE: Vollständige Untersuchung, Wärmeerhalt

═══════════════════════════════════════════════════════════════════════════════
📊 WICHTIGE KLASSIFIKATIONEN (IMMER MIT NAMEN!)
═══════════════════════════════════════════════════════════════════════════════

- Schenkelhalsfraktur: Pauwels I-III, Garden I-IV
- Herzinsuffizienz: NYHA I-IV
- Angina pectoris: CCS I-IV
- Bewusstsein: Glasgow Coma Scale 3-15
- Verbrennungen: Grad I-III
- OP-Risiko: ASA I-VI
- Frakturen: AO-Klassifikation A/B/C

═══════════════════════════════════════════════════════════════════════════════
🎯 AUFGABEN (IN DIESER REIHENFOLGE ABARBEITEN)
═══════════════════════════════════════════════════════════════════════════════

PHASE 1: VORBEREITUNG
□ Lies KENNTNISPRÜFUNG_DOKUMENTFORMAT.md vollständig
□ Lade MASTER_PRUEFUNGSVORBEREITUNG_M3.json
□ Analysiere die Struktur der klinischen Fälle
□ Erstelle Output-Ordnerstruktur unter Output Bucket/MASTER_KENNTNISPRÜFUNG/

PHASE 2: Q&A-GENERIERUNG (HAUPTAUFGABE)
□ Für jeden klinischen Fall:
  □ Generiere 2-3 prüfungsrelevante Fragen
  □ Formatiere Antworten nach dem PFLICHT-Schema
  □ Füge exakte Dosierungen aus Leitlinien hinzu
  □ Ergänze §630 BGB Referenzen
  □ Ordne dem richtigen Fachgebiet zu

□ Priorisierung nach Fachgebiet:
  □ Innere Medizin (30%): ~90 Q&A
  □ Chirurgie (20%): ~60 Q&A
  □ Neurologie (10%): ~30 Q&A
  □ Gynäkologie (10%): ~30 Q&A
  □ Weitere (30%): ~90 Q&A
  
  GESAMT-ZIEL: 200-300 Q&A-Paare

PHASE 3: QUALITÄTSKONTROLLE
□ Prüfe JEDES Q&A-Paar gegen Checkliste:
  □ Definition vorhanden?
  □ Klassifikation mit NAME?
  □ Dosierungen exakt?
  □ §630 BGB erwähnt?
  □ Leitlinie referenziert?

□ Kategorisiere in Qualitäts-Tiers:
  □ Tier 1: Prüfungsreif (keine Änderung nötig)
  □ Tier 2: Gut (minimale Überarbeitung)
  □ Tier 3: Ablehnen (neu generieren)

PHASE 4: OUTPUT-ERSTELLUNG
□ Erstelle für jedes Fachgebiet:
  □ QA_[Fachgebiet].md - Markdown-Format
  □ QA_[Fachgebiet].json - Strukturierte Daten
  □ Lernkarten_[Fachgebiet].txt - Anki-Format

□ Erstelle Statistik-Report:
  □ Anzahl Q&A pro Fachgebiet
  □ Qualitäts-Verteilung (Tier 1/2/3)
  □ Abdeckung der Kernthemen

═══════════════════════════════════════════════════════════════════════════════
⚠️ QUALITÄTSREGELN (NIEMALS VERLETZEN!)
═══════════════════════════════════════════════════════════════════════════════

❌ VERBOTEN:
- Erfundene Dosierungen
- Veraltete Leitlinien (>5 Jahre)
- Template-basierte generische Fragen
- Antworten ohne Struktur
- Fehlende rechtliche Aspekte

✅ PFLICHT:
- Exakte Dosierungen (mg/kg oder absolut)
- Aktuelle AWMF-Leitlinien
- Klassifikationen mit Namen
- §630 BGB bei Therapie-Fragen
- ABCDE bei Notfällen

═══════════════════════════════════════════════════════════════════════════════
📝 BEISPIEL: SO SOLL EINE ANTWORT AUSSEHEN
═══════════════════════════════════════════════════════════════════════════════

FRAGE: Was sind die diagnostischen Kriterien und die Therapie des STEMI?

ANTWORT:

1️⃣ DEFINITION / KLASSIFIKATION
Der ST-Hebungsinfarkt (STEMI) ist definiert als myokardiale Ischämie mit 
typischer Klinik und ST-Hebung ≥1mm in ≥2 zusammenhängenden Ableitungen.

Nach Killip-Klassifikation unterscheidet man:
• Killip I: Keine Herzinsuffizienz
• Killip II: Leichte HI (Rasselgeräusche, S3)
• Killip III: Lungenödem
• Killip IV: Kardiogener Schock

ICD-10: I21.0-I21.3

2️⃣ ÄTIOLOGIE / PATHOPHYSIOLOGIE
Häufigste Ursache (>90%): Ruptur atherosklerotischer Plaques mit 
thrombotischem Verschluss einer Koronararterie.

Risikofaktoren: Hypertonie, Diabetes, Rauchen, Hyperlipidämie, 
positive Familienanamnese, Adipositas.

3️⃣ KLINIK / DIAGNOSTIK
Zunächst Anamnese und körperliche Untersuchung, dann:
• 12-Kanal-EKG innerhalb von 10 Minuten (ST-Hebung, neue Q-Zacken)
• Labor: Troponin I/T (>99. Perzentile), CK-MB
• Echokardiographie: Wandbewegungsstörungen
• Koronarangiographie: Diagnosesicherung und Intervention

4️⃣ THERAPIE
Akuttherapie:
• ASS 250-500mg i.v. (Loading)
• Heparin 5000 IE i.v. Bolus
• Morphin 3-5mg i.v. bei Schmerzen (titriert)
• O2 nur bei SpO2 <90%

First-Line Therapie ist die primäre PCI innerhalb von 120 Minuten 
(Door-to-Balloon-Zeit).

Second-Line bei PCI-Verzögerung >120 min: Fibrinolyse mit 
Tenecteplase 0,5mg/kg i.v. (max. 50mg).

Sekundärprophylaxe:
• ASS 100mg/d dauerhaft
• P2Y12-Inhibitor (Ticagrelor 90mg 2x/d) für 12 Monate
• Statin hochdosiert (Atorvastatin 80mg/d)
• ACE-Hemmer, Betablocker nach Stabilisierung

5️⃣ RECHTLICHE ASPEKTE
Gemäß §630e BGB ist der Patient über die Risiken der PCI (Blutung, 
Gefäßverletzung, Kontrastmittelallergie), Alternativen (Fibrinolyse) 
und Prognose aufzuklären. Bei Bewusstlosigkeit: mutmaßlicher Wille, 
Dokumentation gemäß §630f BGB.

LEITLINIE: AWMF 019-013 - Akutes Koronarsyndrom (2023)
EVIDENZGRAD: A

═══════════════════════════════════════════════════════════════════════════════
🚀 STARTE JETZT - ARBEITE BIS FERTIG!
═══════════════════════════════════════════════════════════════════════════════

1. Öffne das Projekt: /Users/user/Documents/Pruefungsvorbereitung/Comet API/
2. Lies KENNTNISPRÜFUNG_DOKUMENTFORMAT.md
3. Lade die klinischen Fälle
4. Generiere Q&A-Paare nach obigem Format
5. STOPPE NICHT bis 200-300 Q&A-Paare erstellt sind!

Bei Fragen oder Unklarheiten: Frag den Benutzer, aber STOPPE NICHT die Arbeit.

═══════════════════════════════════════════════════════════════════════════════
```

---

## 🔧 Troubleshooting

### Falls Claude Code abbricht:
1. Kopiere den Fortschritt
2. Öffne neue Konversation (`Cmd + N`)
3. Füge Kontext ein: "Setze fort bei Phase X, Aufgabe Y"
4. Weiter arbeiten

### Falls Dateien nicht gefunden:
```bash
# Im Terminal prüfen:
ls -la "/Users/user/Documents/Pruefungsvorbereitung/Comet API/Output Bucket/"
```

### Falls Qualität nicht ausreicht:
- Prompt anpassen
- Mehr Beispiele geben
- Kleinere Batches verarbeiten

---

## 📊 Erwartetes Ergebnis

Nach Abschluss sollte existieren:

```
Output Bucket/MASTER_KENNTNISPRÜFUNG/
├── 01_INNERE_MEDIZIN/
│   ├── QA_Innere_Medizin.md (~90 Q&A)
│   ├── QA_Innere_Medizin.json
│   └── Lernkarten_Innere_Medizin.txt
├── 02_CHIRURGIE/
│   ├── QA_Chirurgie.md (~60 Q&A)
│   └── ...
├── [weitere Fachgebiete]
└── STATISTIKEN/
    ├── Quality_Report.md
    └── Coverage_Report.md
```

**GESAMT: 200-300 prüfungskonforme Q&A-Paare**

---

*Auftrag erstellt: 30.11.2025 | Für: Claude Code in Cursor | Projekt: MedExam AI*
