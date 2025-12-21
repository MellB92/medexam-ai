# Medexamenai - Projekt-Kontext

## Projektziel
Medizinisches Prufungsvorbereitungssystem fur die **Kenntnisprufung** (Approbationsprufung fur auslandische arzte in Deutschland).

## Kernfunktionen
1. **Fragen-Datenbank**: Extraktion und Deduplizierung von Prufungsfragen
2. **Antwort-Generierung**: KI-gestutzte Antworten basierend auf Leitlinien
3. **Fakten-Verifikation**: Prufung medizinischer Fakten gegen Perplexity/Leitlinien
4. **RAG-System**: Retrieval-Augmented Generation fur prazise Antworten

## Wichtige Verzeichnisse
- `_GOLD_STANDARD/` - Original-Prufungsprotokolle (39 PDFs/DOCX/ODT)
- `_EXTRACTED_FRAGEN/` - Extrahierte und deduplizierte Fragen
- `_OUTPUT/` - Generierte Antworten und Checkpoints
- `_OUTPUT/antworten_md/` - Verifizierte MD-Exports (Timestamps 04.12.2025)
- `_BIBLIOTHEK/Leitlinien/` - AWMF-Leitlinien nach Fachgebiet

## Kernskripte
- `scripts/generate_evidenz_answers.py` - Evidenzbasierte Antwort-Generierung (mit Checkpoint/Resume)
- `scripts/dedupe_questions.py` - Deduplizierung MIT Nuancen-Erkennung (WICHTIG!)
- `scripts/recover_evidenz_answers.py` - Wiederherstellung nach Datenverlust
- `scripts/analyze_dedupe_quality.py` - Dedupe-Qualitätsanalyse (NEU 08.12.2025)
- `scripts/reconstruct_fragments.py` - Fragment-Rekonstruktion mit Kontext (NEU 08.12.2025)
- `scripts/filter_with_context.py` - Kontextuelle Relevanz-Filterung mit GPT-5-mini (NEU 08.12.2025)
- `scripts/merge_fragments.py` - Merge relevante Fragmente in Workflow (NEU 08.12.2025)
- `core/rag_system.py` - RAG-Implementierung
- `core/medical_fact_checker.py` - Medizinische Faktenprufung

---

## KRITISCHER WORKFLOW-STATUS (Stand: 2025-12-08 07:45 CET, verifiziert)

### WORKFLOW (nur verifizierte Artefakte nutzen)

```
Gold-Standard PDFs/DOCX/ODT (39 Dateien, _GOLD_STANDARD/)
        ↓
    EXTRAKTION (Fragen werden EXTRAHIERT, nicht generiert!)
        ↓
   frage_bloecke_original.json (9.633 Fragen roh)
        ↓
    DEDUPLIZIERUNG mit scripts/dedupe_questions.py
    (inkl. MedicalNuanceDetector - schützt klinische Unterschiede)
        ↓
   frage_bloecke_dedupe_verifiziert.json (4.556 eindeutige Fragen)
        ↓
    FRAGMENT-PIPELINE (NEU 08.12.2025):
    1. analyze_dedupe_quality.py → Qualitätsanalyse
    2. reconstruct_fragments.py → Block-Kontext hinzufügen
    3. filter_with_context.py → GPT-5-mini Relevanz-Filterung
    4. merge_fragments.py → Integration in Hauptworkflow
        ↓
    KI-GENERIERUNG via Requesty/OpenAI (GPT-5-mini reasoning:high)
        ↓
   evidenz_antworten.json (Hauptdatei)
```

### AKTUELLER DATENSTAND (08.12.2025)

| Metrik | Wert | Datei |
|--------|------|-------|
| Gold-Standard Dokumente | 39 | `_GOLD_STANDARD/` (gezählt, pdf/docx/odt) |
| Rohe Fragen extrahiert | 9.633 | `_EXTRACTED_FRAGEN/frage_bloecke_original.json` |
| Nach verifizierter Dedupe | 4.556 | `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json` |
| Antworten gesamt | 2.909 | `_OUTPUT/evidenz_antworten.json` |
| Antworten mit Inhalt (>50 chars) | 2.725 (93.7%) | `_OUTPUT/evidenz_antworten.json` |
| Fragmente identifiziert | 427 | `_OUTPUT/fragmente_zur_klassifikation.json` |
| Fragmente relevant (nach GPT-5-mini) | ~350 (geschätzt) | `_OUTPUT/fragmente_relevant.json` |

### FRAGMENT-PIPELINE (NEU 08.12.2025)

```bash
# 1. Dedupe-Qualitätsanalyse
python scripts/analyze_dedupe_quality.py

# 2. Fragment-Rekonstruktion mit Block-Kontext
python scripts/reconstruct_fragments.py

# 3. Kontextuelle Relevanz-Filterung (GPT-5-mini reasoning:high)
python scripts/filter_with_context.py

# 4. Merge in Hauptworkflow
python scripts/merge_fragments.py
```

### DEDUPLIZIERUNG (verifiziert)
```bash
PYTHONPATH=. .venv/bin/python3 scripts/dedupe_questions.py \
  --input _EXTRACTED_FRAGEN/frage_bloecke_original.json \
  --output _EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json \
  --string-threshold 0.85 \
  --semantic-threshold 0.80
```

### NUANCEN-ERKENNUNG (MedicalNuanceDetector)

Das System in `scripts/dedupe_questions.py` schützt klinisch relevante Unterschiede:

**Beispiele die NICHT zusammengefasst werden:**
- "Therapie Herzinsuffizienz" vs "Therapie HFrEF" vs "Therapie HFpEF"
- "Diabetes Typ 1" vs "Diabetes Typ 2" vs "Gestationsdiabetes"
- "Pneumonie ambulant" vs "Pneumonie nosokomial" vs "Pneumonie atypisch"

**Enthaltene Qualifier:** Herzinsuffizienz, Hypertonie, Infarkt, Pneumonie, Asthma, COPD, Diabetes, Hepatitis, Schlaganfall, Niereninsuffizienz, Sepsis, etc.

### OFFENE PROBLEME (TODO)

1. **Kontextlose Fragen** - "Was meinen Sie damit?", "Und dann?" haben keinen Sinn ohne Kontext
2. **Fallketten zerstört** - Zusammengehörige Fragen eines klinischen Falls wurden getrennt
3. **Block-Logik fehlt** - Fragen sollten mit ihrem Original-Kontext behalten werden

---

## ANTWORT-QUELLEN (07.12.2025)

| Quelle | Anzahl | Qualität |
|--------|--------|----------|
| MD-Exports (04.12.2025) | 707 | ✅ KI-generiert, verifiziert |
| JSON-Antworten bereinigt | 2.771 | 🔎 Mischung (KI + Prüfungsprotokolle), Clean-Kopie |

**Verifizierte Antworten:** Die MD-Dateien in `_OUTPUT/antworten_md/` (Timestamps 04.12.2025) sind die sicherste Quelle aus dem Requesty/Anthropic Workflow.

**Quarantäne:** Alles unter `_ARCHIVE/quarantine_external/` NICHT verwenden (z.B. `frage_bloecke_komplett_dedupe.json`, `frage_bloecke_neue_extraktion.json`, Desktop-Exports).

---

## CHECKPOINT-SYSTEM & SICHERHEIT

- Checkpoints eingerichtet; standardmäßig `--resume` verwenden
- Sicherheitsnetz aktiv: Abbruch wenn Datei existiert ohne `--resume`
- `--force-new` erstellt automatisch Backups

**Antworten generieren (sicher):**
```bash
PYTHONPATH=. PYTHONUNBUFFERED=1 .venv/bin/python3 scripts/generate_evidenz_answers.py \
  --process-all --batch-size 100 --budget 50.0 --resume 2>&1
```

---

## API-KONFIGURATION

**Requesty-Routing (gefixt 05.12.2025):**
- High complexity: `("requesty", "anthropic/claude-opus-4-5")`
- Low/Medium: `("requesty", "openai/o4-mini:high")`

---

## RECOVERY-PLAYBOOK

Falls `_OUTPUT/evidenz_antworten.json` beschädigt/überschrieben:

```bash
# 1. Trockendurchlauf
PYTHONPATH=. .venv/bin/python3 scripts/recover_evidenz_answers.py --verbose

# 2. Anwenden
PYTHONPATH=. .venv/bin/python3 scripts/recover_evidenz_answers.py --apply --verbose

# 3. Weiter generieren
PYTHONPATH=. .venv/bin/python3 scripts/generate_evidenz_answers.py --resume --process-all
```

Details: `docs/incidents/2025-12-05-answer-loss.md`

---

## CODING-AGENT WORKFLOW (verifiziert)

1) **Fragenbasis**: `_EXTRACTED_FRAGEN/frage_bloecke_dedupe_verifiziert.json` (4.556 Fragen, Nuancen geschützt). Keine anderen Dedupe-Dateien nutzen.
2) **Antwortbasis**: `_OUTPUT/evidenz_antworten_clean.json` (2.771 Einträge; 3 invalide entfernt). Original bleibt als Referenz in `_OUTPUT/evidenz_antworten.json`.
3) **Verifizierte Antworten**: `_OUTPUT/antworten_md/evidenz_antworten_{01,02,03}.md` (707 Fragen) als Goldreferenz.
4) **Quarantäne meiden**: Dateien unter `_ARCHIVE/quarantine_external/` nicht verwenden (Desktop-Exports, „regen/komplett/neue_extraktion“).
5) **Generierung**: Nur mit `--resume` starten. Beispiel:
   ```bash
   PYTHONPATH=. PYTHONUNBUFFERED=1 .venv/bin/python3 scripts/generate_evidenz_answers.py \
     --process-all --batch-size 100 --budget 50.0 --resume
   ```
6) **Mapping/Monitoring**: Frage→Antwort-Matching mit Normalisierung + gleicher `source_file` (kein globales Substring-Raten). Ergebnisse in `_OUTPUT/question_status_verified*.json` ablegen.
7) **Qualität**: Kontextlose Fragen separat listen; Fallketten nicht auseinanderreißen; Nuancen-Schutz beibehalten.

## NÄCHSTE SCHRITTE (offen)

- [ ] Frage→Antwort-Mapping mit verifizierten Inputs fertigstellen und Summary schreiben.
- [ ] Filter für kontextlose Fragen/Fallketten ergänzen.
- [ ] Fehlende Antworten generieren (nur nach Mapping).
- [ ] Qualitäts-Review der Prüfungsprotokoll-Antworten.

---

## Entwickler
**Soloentwickler**: Dagoberto (er/ihm)

## Jira-Board
https://xcorpiodbs.atlassian.net/jira/software/projects/MED/boards/7
Ticket: MED-11 - Antwort-Generierung

## Technologie-Stack
- Python 3.9+
- pypdf, python-docx, odfpy für Dokumenten-Extraktion
- sklearn für TF-IDF/Cosinus-Ähnlichkeit (Dedupe)
- Requesty/Anthropic für KI-Generierung
- RAG-System mit Leitlinien

---

## Projektgedächtnis / Letzte Änderungen (Stand: 2025-12-21)

### GitHub / Repo-Hygiene / Security

**Problem (Push Protection):**
- GitHub Push Protection hat Pushes blockiert wegen Secrets in der Git-Historie.
- Betroffene Pfade: `_ARCHIVE/quarantine_external/claude_exports_Medexamenai/` (u. a. Notion API Token, GitHub OAuth Token).

**Fix (History Cleanup):**
- History wurde lokal per `git filter-repo` bereinigt (invert-paths).
- Bereinigter Branch: `sanitized/no-secrets`.
- Danach wurde der Remote-Branch `Medexamenai` per Force-Update auf die bereinigte Historie gesetzt.
- GitHub Issue geschlossen: #6.

**Wichtig für alle Agents:**
- Dieses Repo hat einen History-Rewrite hinter sich. Wenn ein Agent Divergenzen sieht:
  - `git fetch origin`
  - `git checkout Medexamenai`
  - `git reset --hard origin/Medexamenai`

### Dokumentation / PRs

- PR #7 (Phase 1 Repo-Organisation Guide) wurde gemerged:
  - https://github.com/MellB92/medexam-ai/pull/7
  - Enthält genau 1 Datei: `docs/guides/REPO_ORGANISATION.md`
  - Keine Pipelines ausgeführt, canonical Dateien unangetastet.

### Workspace-Hygiene (untracked Noise vermeiden)

**Symptom:** Viele lokale (untracked) Agent-Artefakte haben Git/IDE-Workflows gestört.

**Fix:** `.gitignore` erweitert um lokale Agent-Artefakte zu ignorieren:
- `_AGENT_WORK/`
- `AGENT_*.md`

**Empfehlung:**
- Alles, was nur lokal/debug ist, bleibt in `_AGENT_WORK/`.
- Falls du etwas davon dauerhaft brauchst: in `/docs/` oder `/scripts/` überführen und als PR sauber reviewen.

### .env Migration & Key-Checks

- `.env` wurde vom alten Mac migriert.
- Smoke-Tests für Provider-Keys:
  - Anthropic: OK
  - OpenAI: OK
  - Requesty: OK
  - Perplexity: OK (Wichtig: Modell `sonar` funktioniert; falsche Modellnamen führen zu HTTP 400)

**Hinweis:** Niemals Secrets in Logs/Commits. `.env` bleibt in `.gitignore`.

### Git Stash Konvention (um Branches clean zu halten)

- Wenn lokale untracked/modified Dateien Pull/Merge blockieren:
  - `git stash push -u -m "WIP ..."`
- Stashes sind bewusst erlaubt, um `Medexamenai` clean zu halten.

