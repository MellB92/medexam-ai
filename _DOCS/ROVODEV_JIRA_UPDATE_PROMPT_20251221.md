# Rovodev Prompt: Jira auf aktuellen Repo-Stand bringen (MedExamAI)

**Datum:** 2025-12-21
**Ziel:** Jira-Board/Tickets auf den gleichen Stand bringen wie GitHub Repo + lokales Repo.

## Kontext / Ist-Stand (GitHub)

- Repo: https://github.com/MellB92/medexam-ai
- Default-Branch: `Medexamenai`

### Wichtige Ereignisse / Änderungen

1) **Secret Scanning / Push Protection behoben (History Rewrite)**
- Ursache: Secrets in der Git-Historie in `_ARCHIVE/quarantine_external/claude_exports_Medexamenai/` (Notion API Token, GitHub OAuth Token).
- Fix: History Cleanup via `git filter-repo --invert-paths --path _ARCHIVE/quarantine_external/claude_exports_Medexamenai/ --force`.
- Danach: `Medexamenai` wurde remote auf die bereinigte Historie aktualisiert.
- Issue geschlossen: **#6**
  - https://github.com/MellB92/medexam-ai/issues/6

**Wichtig für Team/Agents:**
- Wegen History-Rewrite kann es lokal zu Divergenz kommen.
- Standard-Fix: `git fetch origin && git checkout Medexamenai && git reset --hard origin/Medexamenai`.

2) **Phase-1 Repo Organisation Dokumentation (merged)**
- PR **#7** gemerged: https://github.com/MellB92/medexam-ai/pull/7
- Inhalt: nur `docs/guides/REPO_ORGANISATION.md`
- Keine Pipelines ausgeführt; canonical Dateien unangetastet.

3) **Workspace Hygiene / Agent-Artefakte**
- `.gitignore` erweitert:
  - `_AGENT_WORK/`
  - `AGENT_*.md`
- Ziel: untracked Noise reduzieren, IDE/Git stabilisieren.

4) **.env Migration & Key-Checks**
- `.env` vom alten Mac migriert.
- Smoke-Tests (HTTP):
  - Anthropic ✅
  - OpenAI ✅
  - Requesty ✅
  - Perplexity ✅ (Modell `sonar` OK; falsche Modellnamen → HTTP 400)

## Anweisung an Rovodev: Jira Update durchführen

Bitte in Jira (Projekt MED) die folgenden Updates eintragen. Wenn ein Ticket nicht existiert, erstelle es. Wenn es existiert, kommentiere/aktualisiere es.

### A) Ticket/Task: "Repo Security: History Cleanup (Secret Scan)" (neu oder bestehend)

**Beschreibung (copy/paste):**
- GitHub Push Protection blockierte Pushes wegen Secrets in der Historie.
- Bereinigung per `git filter-repo` für `_ARCHIVE/quarantine_external/claude_exports_Medexamenai/`.
- Remote-Branch `Medexamenai` wurde auf bereinigte Historie aktualisiert.
- Verweis: GitHub Issue #6 (geschlossen) https://github.com/MellB92/medexam-ai/issues/6

**Acceptance Criteria:**
- Jira dokumentiert: History-Rewrite durchgeführt + Team-Hinweis zur lokalen Synchronisation.
- Keine Secrets mehr in der GitHub-Historie (Push Protection grün).

### B) Ticket/Task: "Docs: Repo Organisation Guide (Phase 1)" (neu oder bestehend)

**Beschreibung:**
- PR #7 gemerged: https://github.com/MellB92/medexam-ai/pull/7
- Enthält: `docs/guides/REPO_ORGANISATION.md`

**Acceptance Criteria:**
- Jira enthält Link zum PR.
- Jira enthält kurze Zusammenfassung: Phase 1 = nur Doku, keine Datei-Moves, keine Pipeline-Ausführung.

### C) Ticket/Task: "DevEx: Git/Agent Workspace Hygiene" (neu oder bestehend)

**Beschreibung:**
- `.gitignore` erweitert, um lokale Agent-Artefakte zu ignorieren (`_AGENT_WORK/`, `AGENT_*.md`).
- Zweck: Cleaner Git-Status, weniger IDE-Probleme.

**Acceptance Criteria:**
- Jira enthält kurz die neuen `.gitignore` Regeln.
- Jira Hinweis: Lokale WIP-Änderungen in Stash ablegen (`git stash push -u`).

### D) Ticket/Task: ".env Migration + API Key Smoke Tests" (neu oder bestehend)

**Beschreibung:**
- `.env` Migration vom alten Mac abgeschlossen.
- Provider-Keys validiert mit minimalen HTTP-Requests.
- Perplexity: Modell `sonar` ist gültig.

**Acceptance Criteria:**
- Jira dokumentiert: Key-Checks ✅.
- Sicherheitsnote: `.env` bleibt ignoriert, keine Secrets committen.

## Output

- Poste die Jira-Links zu den aktualisierten/neu erstellten Tickets.
- Füge in jedem Ticket einen kurzen Änderungslog (Datum, was genau passiert ist).

