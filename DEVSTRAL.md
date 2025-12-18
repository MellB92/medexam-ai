# Devstral (Kilo Code) – Aufgabenbriefing (Stand: 2025-12-12)

## Kurzstatus (verifiziert)
- Fragenbasis dedupe: 4.556 (Meaningful 2.527, Fragmente 2.029) – `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json`
- Meaningful Coverage: **100.0% (2.527/2.527)** – keine Restlücken.
- Hauptantwortdatei: `_OUTPUT/evidenz_antworten.json` (**4.505 Q&A**)

## Deine Aufgaben (Priorität)
### 1) Fragmente „ausbuchen“ (question-level, NICHT block-level)
Ziel: Fragmente zählen nicht als Lücke und werden bei Validierung/Reports separat behandelt.

Input:
- `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json` (1.293 Blöcke, 4.556 Fragen)

Output (neu, canonical):
- `_OUTPUT/fragmente_flags_question_level.json` (4.556 Zeilen: `block_id`, `source_file`, `frage`, `is_fragment`, `reason`)

Regeln:
- Fragmente sind kurze/kontextlose Fragen („Und?“, „Was noch?“, „wo?“, „Warum?“ ohne Referenz).
- NICHT einfach „multi-question block = Fragment“ (das ist falsch; Blöcke enthalten regulär mehrere Fragen).
- Rekonstruierbare Fragmente (Gemini liefert `new_question`) separat markieren: `is_fragment=false`, `reason="reconstructed"`.

### 2) Fachgebiets-Tags konsolidieren
Es existieren bereits Artefakte (block-level):
- `_OUTPUT/full_data_with_fachgebiete.json` (1.293 Blöcke)
- `_OUTPUT/fachgebiete_inventory.csv`, `_OUTPUT/fachgebiete_inventory.md`

Ziel: question-level Inventar (4.556 Zeilen), damit der Mentor-Agent pro Frage ein Fachgebiet hat.
Output (neu):
- `_OUTPUT/fachgebiete_inventory_questions.csv` (Spalten: `block_id,source_file,frage,fachgebiet,confidence`)

### 3) Merge-Sicherheit
- Frage-Strings nie ändern.
- Vor Änderungen an `_OUTPUT/evidenz_antworten.json`: Backup.

## Hinweise
- Fragmente nicht beantworten (außer rekonstruierbar mit Gold-Standard-Kontext).
- Übergabe an Assistant: Pfade + Counts + kurze Validierung der Summen (4.556 / 2.527 / 2.029).
