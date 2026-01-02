# Claude Code Auftrag: Pre-Import QA + Lernplan (MedExamAI) – aktualisiert

## Kontext
- Images-Pipeline abgeschlossen, MedGemma-Validierung vorbereitet.
- Bildzahlen korrigiert: Needs-Review 258 Bilder; Gesamt Bilderkarten 346; 27 eindeutige Medien.
- Externe Decks (Ankizin/Dellas) sind fertig, nur importieren.

## Guardrail (wichtig)
- Nutze das 5-teilige Prüfungsformat **nur**, wenn `content_type == disease` **und** `confidence ≥ 0.6`.
- Andernfalls: **kein** 5-Abschnitt-Schema → kurzes, evidenzbasiertes, flexibles Format (Ethik/Recht/Organisation), 3–6 Sätze, Unsicherheiten markieren.
- Marker wie `qa::needs_review`, `review::missing_context`, „kein verlässlicher Fallkontext“ → automatisch flexibles Format wählen.

## Pflichtaufgaben vor Import
1) Status checken & ggf. `ANKI_IMPORT_ANLEITUNG.md` Zahlen prüfen (258 / 346 / 27).
2) MedGemma-Validierung (nach gcloud auth):
   ```bash
   python3 scripts/validate_repaired_cards.py \
     --input _OUTPUT/openai_batch_all/medgemma_validation_queue_for_validate.jsonl \
     --output-report _OUTPUT/openai_batch_all/validation_report.md \
     --use-medgemma \
     --write-updated-batch \
     --budget-eur 10.0 \
     --max-items 150 \
     --only-repaired
   ```
3) Nachbereitung: Report prüfen; falls nötig `prepare_anki_repaired_import.py`.

## Lernplan (zu erstellen in `_OUTPUT/LEARNPLAN.md`)
- Reihenfolge: Ankizin → Dellas → HighYield → Final::OK → Final::NeedsReview.
- Tag-Fokus: `medgemma_relevant`, `qa::needs_review`, `risk::dose`, `risk::radiation`.
- Zielwerte: Neue Karten/Tag und Review-Last klar definieren; Wochenziele + Checkliste.

## Dateien/Decks (Importbereit)
- `_OUTPUT/with_images/anki_all_gpt52_with_images.tsv` (691; 88 mit Bildern)
- `_OUTPUT/with_images/anki_all_gpt52_needs_review_with_images.tsv` (1568; 258 mit Bildern)
- `_OUTPUT/media_images/` (27 Dateien → Anki `collection.media`)
- Externe: `Ankizin_KP_Muenster_filtered.apkg` (~18.297), `Dellas_KP_Muenster_filtered.apkg` (~4.943)
- Weitere: `anki_repaired_fallbasiert.tsv` (50), `anki_repaired_templates.tsv` (76)

## Optional
- Perplexity-Validierung (`perplexity_validation_queue.jsonl`) nach Rücksprache.
- Images-Pipeline für `anki_repaired_fallbasiert.tsv` / `anki_repaired_templates.tsv`.

