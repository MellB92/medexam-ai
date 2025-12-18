# 📋 KOPIERVORLAGE FÜR CLAUDE CODE

> **Anleitung:** 
> 1. `Shift + Cmd + P` → Command Palette öffnen
> 2. "Claude" tippen → Claude Code öffnen
> 3. Den Text unten kopieren und einfügen

---

## PROMPT (KOPIEREN AB HIER):

```
Ich beauftrage dich mit der Erstellung von 200-300 prüfungskonformen Q&A-Paaren für die deutsche Kenntnisprüfung (März 2026).

DATENQUELLEN:
- Klinische Fälle: Output Bucket/MASTER_PRUEFUNGSVORBEREITUNG_M3.json (4.058 Fälle)
- Dokumentformat: Output Bucket/KENNTNISPRÜFUNG_DOKUMENTFORMAT.md (LIES ZUERST!)
- Auftrag: Output Bucket/CLAUDE_CODE_AUFTRAG.md (für Details)

PFLICHT-ANTWORTFORMAT für JEDE medizinische Frage:

1️⃣ DEFINITION / KLASSIFIKATION
   - Klassifikation IMMER mit NAME (z.B. "Nach Pauwels-Klassifikation...")
   - ICD-10 Code

2️⃣ ÄTIOLOGIE / PATHOPHYSIOLOGIE
   - Ursachen mit Prozentangaben
   - Risikofaktoren

3️⃣ KLINIK / DIAGNOSTIK
   - IMMER beginnen: "Zunächst Anamnese und körperliche Untersuchung, dann..."
   - Schritt-für-Schritt

4️⃣ THERAPIE (KRITISCH!)
   - EXAKTE Dosierungen: mg/kg oder absolute Dosis
   - "First-Line Therapie ist..., Second-Line..."
   - NIEMALS "übliche Dosis" - IMMER konkrete Zahlen!

5️⃣ RECHTLICHE ASPEKTE
   - §630e BGB (Aufklärung)
   - §630f BGB (Dokumentation)
   - Mindestens EINEN Paragraphen erwähnen!

6️⃣ LEITLINIE + EVIDENZGRAD
   - AWMF-Nummer, Titel, Jahr
   - Evidenzgrad A/B/C/D

BEI NOTFALL-FRAGEN → ABCDE-Schema PFLICHT:
A-Airway, B-Breathing, C-Circulation, D-Disability, E-Exposure

VERTEILUNG:
- Innere Medizin (30%): ~90 Q&A
- Chirurgie (20%): ~60 Q&A  
- Neurologie (10%): ~30 Q&A
- Gynäkologie (10%): ~30 Q&A
- Weitere (30%): ~90 Q&A

ARBEITSSCHRITTE:
1. Lies KENNTNISPRÜFUNG_DOKUMENTFORMAT.md
2. Lade MASTER_PRUEFUNGSVORBEREITUNG_M3.json
3. Erstelle Output-Ordner: Output Bucket/MASTER_KENNTNISPRÜFUNG/
4. Generiere Q&A-Paare nach Format
5. Speichere als .md und .json pro Fachgebiet
6. STOPPE NICHT bis 200-300 Q&A erstellt sind!

QUALITÄTSREGELN:
❌ VERBOTEN: Erfundene Dosierungen, veraltete Leitlinien, generische Antworten
✅ PFLICHT: Exakte Dosierungen, aktuelle AWMF, Klassifikationen mit Namen, §630 BGB

Beginne JETZT mit Phase 1 und arbeite kontinuierlich bis alle Phasen abgeschlossen sind.
```

---

## ALTERNATIVE: KURZVERSION (wenn Langversion zu viel)

```
Lies zuerst: Output Bucket/KENNTNISPRÜFUNG_DOKUMENTFORMAT.md und Output Bucket/CLAUDE_CODE_AUFTRAG.md

Dann: Generiere 200-300 Q&A-Paare aus MASTER_PRUEFUNGSVORBEREITUNG_M3.json nach dem Schema:
1) Definition/Klassifikation (mit NAME!)
2) Ätiologie
3) Diagnostik ("Zunächst Anamnese und KU, dann...")
4) Therapie (EXAKTE Dosierungen!)
5) Rechtlich (§630 BGB)
6) Leitlinie + Evidenzgrad

STOPPE NICHT bis fertig. Bei Notfall → ABCDE-Schema. Speichere unter Output Bucket/MASTER_KENNTNISPRÜFUNG/
```

---

## NACH DEM START: Folge-Prompts falls nötig

### Falls Claude Code pausiert:
```
Setze die Q&A-Generierung fort. Du warst bei [Fachgebiet/Nummer]. 
Arbeite weiter bis 200-300 Q&A-Paare erstellt sind.
```

### Falls Qualität nicht stimmt:
```
Die letzten Q&A-Paare haben keine exakten Dosierungen. 
Überarbeite sie mit konkreten mg/kg Angaben aus AWMF-Leitlinien.
```

### Für Fortschrittsbericht:
```
Zeige mir den aktuellen Stand:
- Anzahl erstellter Q&A-Paare
- Verteilung nach Fachgebiet
- Qualitäts-Tier-Verteilung
```

---

*Erstellt: 30.11.2025 | Für direkte Verwendung in Claude Code (Cursor)*
