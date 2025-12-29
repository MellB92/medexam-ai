# Rovo Dev Prompt: Jira auf aktuellen Repo-Stand bringen (Projekt MED / Medexamenai)

**Datum:** 2025-12-21  
**Ziel:** Jira (Projekt **MED**) soll den aktuellen Stand von GitHub + lokalem Repo korrekt widerspiegeln – inkl. Security-Fix (History Rewrite), Doku-PR, Workspace Hygiene, `.env`-Migration/Key-Checks – **ohne** dabei Secrets zu veröffentlichen.

---

## 0) Sicherheits- & Arbeitsregeln (Mittelweg: Schutz vor nachteiligen Änderungen ohne „alles verbieten“)

> Diese Regeln sind absichtlich so formuliert, dass ein Coding-Agent produktiv arbeiten kann, ohne dass unbemerkte gefährliche Änderungen passieren.

### 0.1 Prinzip: „Read → Plan → Diff → Apply → Verify“

1) **Read:** Erst Kontext lesen (bestehende Tickets, Repo-Status, relevante Dateien).  
2) **Plan:** Kurzen Plan schreiben (max. 10 Zeilen) + was *nicht* angefasst wird.  
3) **Diff-orientiert:** Änderungen nur als **kleine, nachvollziehbare Diffs** durchführen (keine massiven Rewrites ohne explizite Freigabe).  
4) **Verify:** Nach Änderungen: Tests/Lints/Checks ausführen oder begründen, warum nicht.

### 0.2 „Protected Areas“ (niemals automatisch verändern)

- **Secrets & Credentials:** `.env`, API Keys, Tokens, private Exports.
- **Canonical/Output-Daten:** z.B. `_OUTPUT/**`, große JSON-Assets, Exporte (nur ändern, wenn Auftrag explizit + Backup/Checksum).
- **History/Rewrite Operationen:** `git filter-repo`, `rebase --onto`, `reset --hard` etc. nur mit ausdrücklicher Zustimmung.

### 0.3 „Change Gates“ (welche Änderungen sind erlaubt?)

- **Sofort erlaubt (Low Risk):** reine Doku-Edits, Kommentare, Formatting, `.gitignore`, CI-Konfiguration – **wenn** Diff klein + Review möglich.
- **Erlaubt nach Kurz-Freigabe (Medium Risk):** refactors, API-Signaturen, Skript-Änderungen, die Outputs beeinflussen.
- **Nur nach expliziter Freigabe (High Risk):** Datenmigrationen, History-Rewrite, Änderungen an `_OUTPUT/**` oder Produktionsdaten.

### 0.4 Safety-Mechanik, die du im Repo nutzen kannst (Empfehlungen)

- **Branch + PR Pflicht:** Agent arbeitet nie direkt auf Default-Branch.
- **Protected Branches:** Require PR reviews, status checks, linear history.
- **Pre-commit + CI:** formatter/lint/tests verhindern „silent breakage“.
- **Automatische Backups für kritische Ordner:** z.B. `_OUTPUT/` nur über Skripte, die vorab eine Kopie/Checksum erzeugen.
- **Datei-Wächter (Optional):** CI-Job, der Änderungen an Protected Areas blockiert (Fail wenn `_OUTPUT/**` geändert).

---

## 1) Kontext / Ist-Stand (GitHub / Repo)

- Repo: https://github.com/MellB92/medexam-ai
- Default-Branch: `Medexamenai`

### 1.1 Wichtige Ereignisse / Änderungen (zusammengefasst)

#### A) Secret Scanning / Push Protection behoben (History Rewrite)
- Ursache: Secrets lagen in der Git-Historie in `_ARCHIVE/quarantine_external/claude_exports_Medexamenai/` (u.a. Notion API Token, GitHub OAuth Token).
- Fix: History Cleanup via:
  - `git filter-repo --invert-paths --path _ARCHIVE/quarantine_external/claude_exports_Medexamenai/ --force`
- Danach: Remote-Branch `Medexamenai` wurde auf bereinigte Historie aktualisiert.
- Referenz: GitHub Issue **#6** (geschlossen)
  - https://github.com/MellB92/medexam-ai/issues/6

**Wichtig für Team/Agents (lokale Sync nach History-Rewrite):**
- `git fetch origin && git checkout Medexamenai && git reset --hard origin/Medexamenai`
- Achtung: lokale Änderungen vorher sichern (z.B. `git stash push -u`).

#### B) Phase-1 Repo Organisation Dokumentation (merged)
- PR **#7** gemerged: https://github.com/MellB92/medexam-ai/pull/7
- Inhalt: `docs/guides/REPO_ORGANISATION.md`
- Phase 1 = **nur Dokumentation**: keine Datei-Moves, keine Pipeline-Ausführung, keine Änderungen an canonical Daten.

#### C) Workspace Hygiene / Agent-Artefakte
- `.gitignore` erweitert:
  - `_AGENT_WORK/`
  - `AGENT_*.md`
- Ziel: untracked Noise reduzieren, IDE/Git stabilisieren.

#### D) `.env` Migration & API Key Smoke Tests
- `.env` vom alten Mac migriert (lokal).
- Smoke-Tests (HTTP) erfolgreich:
  - Anthropic ✅
  - OpenAI ✅
  - Requesty ✅
  - Perplexity ✅ (Modell `sonar` gültig; falsche Modellnamen → HTTP 400)

---

## 2) Jira-Update durchführen (Projekt MED)

**Projekt:** MED (https://xcorpiodbs.atlassian.net/browse/MED)

### 2.1 Erst suchen statt sofort neu anlegen

1) **Suche nach bestehenden Tickets**, bevor du neue erstellst:
   - Keywords: `history rewrite`, `secret scanning`, `push protection`, `git filter-repo`
   - `repo organisation`, `REPO_ORGANISATION.md`, `PR #7`
   - `gitignore`, `agent artifacts`, `workspace hygiene`
   - `.env migration`, `smoke test`, `perplexity sonar`

2) **Wichtiger Anker:** Prüfe, ob das Epic **MED-18** ("🔄 Batch Review Run 20251216 – Stabilisierung und Finalisierung") diese Arbeiten abdecken soll.
   - Wenn inhaltlich passend: als **Sub-Tasks** unter MED-18 anlegen.
   - Wenn nicht passend: separate Tasks/Bugs anlegen, aber **MED-18 referenzieren**, falls es Kontext liefert.

3) **Wenn Ticket existiert:**
   - Description ergänzen + Links hinzufügen
   - **Kommentar** mit kurzem Change-Log (Datum + was passiert ist)

4) **Wenn Ticket nicht existiert:**
   - Neues Ticket anlegen (Task/Bug je nach Board-Konvention)
   - Inhalt unten copy/paste

**Security-Hinweis:** Keine Secret-Werte posten. Keine `.env` Inhalte posten.

---

## 3) Tickets (Copy/Paste Content)

> Für jedes Ticket gilt: Wenn bereits vorhanden → **Description erweitern + Kommentar mit Change-Log**. Wenn neu → **Ticket anlegen** und untenstehenden Inhalt verwenden.

---

### Ticket A) Repo Security: History Cleanup (Secret Scan / Push Protection)

**Titel:** Repo Security: History Cleanup (Secret Scan / Push Protection)

**Typ (Vorschlag):** Bug oder Task (Security)

**Labels (Vorschlag):** `security`, `git`, `history-rewrite`

**Beschreibung (copy/paste):**
- GitHub Push Protection blockierte Pushes wegen Secrets in der Git-Historie.
- Ursache: Sensitive Dateien/Exports lagen historisch unter:
  - `_ARCHIVE/quarantine_external/claude_exports_Medexamenai/`
- Bereinigung durchgeführt via `git filter-repo` (History Rewrite):
  - `git filter-repo --invert-paths --path _ARCHIVE/quarantine_external/claude_exports_Medexamenai/ --force`
- Remote-Branch `Medexamenai` wurde auf bereinigte Historie aktualisiert.
- Referenz: GitHub Issue #6 (geschlossen)
  - https://github.com/MellB92/medexam-ai/issues/6

**Team-Hinweis (lokal):**
- Nach History-Rewrite kann es lokal zu Divergenz kommen.
- Standard-Fix:
  - `git fetch origin && git checkout Medexamenai && git reset --hard origin/Medexamenai`
- Vorher lokale Änderungen sichern (z.B. `git stash push -u`).

**Acceptance Criteria:**
- Jira dokumentiert den History-Rewrite inkl. Team-Anleitung zur lokalen Synchronisation.
- Push Protection ist wieder grün (keine Secrets mehr in der Historie).
- Keine Secret-Werte im Ticket enthalten.

**Change-Log (als Kommentar anlegen):**
- 2025-12-21: History Cleanup via `git filter-repo`; Branch `Medexamenai` auf bereinigte Historie aktualisiert; Team-Sync-Anweisung ergänzt.

---

### Ticket B) Docs: Repo Organisation Guide (Phase 1)

**Titel:** Docs: Repo Organisation Guide (Phase 1)

**Typ (Vorschlag):** Task / Documentation

**Labels (Vorschlag):** `docs`, `repo-structure`

**Beschreibung (copy/paste):**
- PR #7 gemerged:
  - https://github.com/MellB92/medexam-ai/pull/7
- Enthält:
  - `docs/guides/REPO_ORGANISATION.md`
- Phase 1 umfasst ausschließlich Dokumentation:
  - keine Datei-Moves
  - keine Pipeline-Ausführung
  - keine Änderungen an „canonical“ Daten/Outputs

**Acceptance Criteria:**
- Jira enthält Link zum PR.
- Jira enthält Kurz-Zusammenfassung von Phase 1 (nur Doku, keine Moves/Pipelines).

**Change-Log (als Kommentar anlegen):**
- 2025-12-21: PR #7 dokumentiert; Phase-1 Scope klargestellt (nur Doku).

---

### Ticket C) DevEx: Git/Agent Workspace Hygiene (.gitignore)

**Titel:** DevEx: Git/Agent Workspace Hygiene (.gitignore)

**Typ (Vorschlag):** Task / DevEx

**Labels (Vorschlag):** `devex`, `git`, `cleanup`

**Beschreibung (copy/paste):**
- `.gitignore` wurde erweitert, um lokale Agent-Artefakte zu ignorieren:
  - `_AGENT_WORK/`
  - `AGENT_*.md`
- Zweck:
  - cleaner Git-Status (weniger untracked noise)
  - weniger IDE/Indexing-Probleme
  - stabilere Agent-Workflows

**Acceptance Criteria:**
- Jira dokumentiert die neuen `.gitignore` Regeln.
- Jira enthält Hinweis zum Sichern lokaler WIP-Änderungen (z.B. `git stash push -u`).

**Change-Log (als Kommentar anlegen):**
- 2025-12-21: `.gitignore` erweitert (_AGENT_WORK/, AGENT_*.md) für Workspace Hygiene.

---

### Ticket D) Ops/Dev: `.env` Migration + API Key Smoke Tests

**Titel:** `.env` Migration + API Key Smoke Tests

**Typ (Vorschlag):** Task / Ops

**Labels (Vorschlag):** `ops`, `configuration`, `keys`

**Beschreibung (copy/paste):**
- Lokale `.env` Migration vom alten Mac abgeschlossen (nur lokal; `.env` bleibt ignoriert).
- Provider-Keys validiert mit minimalen HTTP-Requests (Smoke Tests):
  - Anthropic ✅
  - OpenAI ✅
  - Requesty ✅
  - Perplexity ✅ (gültiges Modell: `sonar`; falsche Modellnamen → HTTP 400)
- Keine Secrets/Werte im Ticket posten.

**Acceptance Criteria:**
- Jira dokumentiert: Key-Checks erfolgreich (ohne Secret-Werte).
- Sicherheitsnote: `.env` bleibt ignoriert; keine Secrets committen.

**Change-Log (als Kommentar anlegen):**
- 2025-12-21: `.env` migriert; Provider-Smoketests erfolgreich; Perplexity Modell `sonar` bestätigt.

---

## 4) Output (Pflicht)

Wenn die Jira-Updates abgeschlossen sind, poste:
- Links zu allen aktualisierten/neu erstellten Tickets
- Kurzer Status je Ticket (neu/aktualisiert, ob unter MED-18 als Subtask oder separat)
- Hinweis, ob irgendwo Security/Secrets-relevante Inhalte absichtlich weggelassen wurden
