# Codex (Assistant) – Aufgabenbriefing (Stand: 2025-12-21)

## KRITISCH: Drei-Kategorien-System

Das Projekt verwendet eine strikte Trennung in **DREI Kategorien**:

| Kategorie | Zweck | Für RAG? |
|-----------|-------|----------|
| **PRÜFUNGSPROTOKOLLE** | Prüfungsablauf, Themen, Empfehlungen, Fehleranalyse | NEIN |
| **FAKTEN** | Medizinisches Wissen (Leitlinien, Lehrbücher) | JA |
| **OUTPUT** | Generierte Ergebnisse | N/A |

### Kategorisierung bei unsortierten Dateien

Bei der Kategorisierung von Dateien aus `_FACT_CHECK_SOURCES/_unsortiert/` gelten folgende Regeln:

**→ PRÜFUNGSPROTOKOLLE** (nach `_GOLD_STANDARD/`):

- Kenntnisprüfung-Berichte, Fälle, Simulationen
- Fachsprachprüfung (FSP) Materialien
- Anamnese-Übungen, Dokumentationsübungen
- Erfahrungsberichte, Tipps von Teilnehmern

**→ FAKTEN** (in `_FACT_CHECK_SOURCES/` belassen oder `_BIBLIOTHEK/`):

- Leitlinien (AWMF S1/S2/S3)
- Lehrbuch-Inhalte (Anatomie, Pathologie, Therapie)
- Klinische Notfälle, Arzneimittel, Laborwerte
- EKG/MRT/Röntgen-Interpretation

**→ SPRACHLICH/ADMIN** (archivieren oder separat):

- Deutsch-Grammatik, Konjunktionen
- Anmeldeformulare, Anträge

Siehe: `_AGENT_WORK/CODEX_PROMPT_UNSORTIERT_KATEGORISIERUNG.md` für Codex-Task.

---

## Kurzstatus (verifiziert)
- Fragenbasis dedupe: 4.556 (Meaningful 2.527, Fragmente 2.029) – `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json`
- Meaningful Coverage: **100.0% (2.527/2.527)** – geprüft gegen `_OUTPUT/meaningful_missing.json`
- Hauptantwortdatei: `_OUTPUT/evidenz_antworten.json` (**4.505 Q&A**, 0 leere Fragen)
- Vollvalidierung (Relevanz-Check via OpenAI gpt-4o-mini): `_OUTPUT/validation_full_results.json`

## Aktueller Fokus
1) Fakten-/Quellen-Validierung (Perplexity + Leitlinien) als Stichprobe, nur echte Fehler patchen.
2) Fragmente (2.029) question-level als `unanswerable` flaggen, damit Coverage/Validation sinnvoll reportet (meaningful-only).
3) Inventar/Fachgebiete konsolidieren (question-level Export) für Mentor-Agent.

## Do/Don’t (wichtig)
- Frage-Strings niemals ändern; Merge/Validation matcht über exakten `frage`-Text.
- Vor jeder Mutation an `_OUTPUT/evidenz_antworten.json`: Backup mit Timestamp.
- Gute Antworten nicht „optimieren“ (Tokens sparen); nur echte fachliche Fehler korrigieren.

## Nützliche Commands
- Meaningful Coverage prüfen:
  - `python3 -c "import json; from pathlib import Path; mm=json.loads(Path('_OUTPUT/meaningful_missing.json').read_text()); qa=json.loads(Path('_OUTPUT/evidenz_antworten.json').read_text()); s=set(x['frage'] for x in qa); print(sum(1 for x in mm if x['question'] in s), '/', len(mm))"`
- Relevanz-Vollvalidierung (falls nötig re-run):
  - `PYTHONPATH=. .venv/bin/python3 scripts/validate_full_dataset.py --budget 10 --problematic-output _OUTPUT/problematic_answers_full.json`
