# Gemini CLI (Gemini 3 Pro) – Aufgabenbriefing (Stand: 2025-12-12)

## Aktueller Stand (verifiziert)
- Fragenbasis dedupe: 4.556 (Meaningful 2.527, Fragmente 2.029) in `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json`.
- Meaningful Coverage: **100.0% (2.527/2.527)**.
- Hauptantwortdatei: `_OUTPUT/evidenz_antworten.json` (**4.505 Q&A**).
- Relevanz-Vollvalidierung (gpt-4o-mini Judge): `_OUTPUT/validation_full_results.json` (Score 1–2 kommen überwiegend von Fragment-Fragen).

## Deine Aufgaben (Priorität)
### 1) Fragmente rekonstruieren (kontextbasiert, batchweise, automatisch weiter)
Ziel: Aus fragmentartigen Fragen echte, beantwortbare Fragen rekonstruieren (nur wenn klarer Kontext im Gold-Standard existiert).

Input:
- `_OUTPUT/fragmente_relevant.json` (≈385 Kandidaten; enthält `original`, `reconstructed`, `source_file`, `block_id`)

Output:
- `_OUTPUT/fragmente_reconstructed_batches.json` (append-only), Einträge:
  - `index`, `original`, `new_question`, `source_file`, `block_id`, `confidence`, `notes`

Arbeitsweise:
- In Batches von 20 (0–19, 20–39, …) bis Dateiende.
- Kontext nur in der angegebenen `source_file` unter `_GOLD_STANDARD/` prüfen (keine globale Volltextsuchen über alle Quellen).
- Wenn rekonstruierbar: `new_question` so nah wie möglich am Wortlaut des Dokuments; **keine neuen Inhalte erfinden**.
- Wenn nicht rekonstruierbar: markiere als `unanswerable_reason: "no_context"` und **keine Frage formulieren**.
- Automatisierung: schreibe/führe ein kleines Python-Skript aus, das Batches der Reihe nach verarbeitet und nach jedem Batch speichert (kein reines Chat-“Weiter?”).

### 2) Fakten-/Quellen-Stichprobe (Perplexity/Leitlinien)
Ziel: evidenzbasierte Quellenvorschläge für echte Verbesserungen, ohne gute Antworten unnötig umzuschreiben.

Input:
- `_OUTPUT/evidenz_antworten.json` (nur meaningful oder priorisiert: meaningful mit Score≤2)

Output:
- Kurzliste (JSON/MD): `{frage, issue, suggested_source_url_or_guideline, optional_fix_snippet}`

## Hinweise (wichtig)
- Relevanz-Validator ≠ Perplexity: der Relevanz-Check ist gpt-4o-mini; Perplexity ist für Web-Suche/Faktencheck.
- Fokus auf Evidenz/Quellen (AWMF/RKI/PEI/DocCheck/Fachinfo) und konkrete Korrekturen.
