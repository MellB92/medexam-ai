# GitHub Copilot Agent Prompt – MedExamAI (Repo-Organisation, Phase 1 + Cleanup)

Kontext
- Lokales Repo: /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
- Feature-Branch (Phase 1): docs/repo-organisation-phase1
- Commit: "docs: Repo Organisation Guide + .gitignore (phase 1)"
- PR-Titel: "docs: Repo Organisation Guide + .gitignore (phase 1)"
- Ziel: Hochwertiger Push inkl. Secret-Scan-Compliance via History Cleanup; danach PR(s) erstellen
- Wichtige Regeln:
  - Keine Pipelines ausführen
  - Keine Änderung an _OUTPUT/canonical/evidenz_antworten.json
  - Phase‑1 PR enthält nur: docs/guides/REPO_ORGANISATION.md + .gitignore
  - Bei Sicherheitshinweisen stets die sichere Option (Cleanup) wählen

Vorbereitung
1) cd "/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617"
2) Git prüfen:
   - git status
   - git remote -v || git remote add origin "<GITHUB_REPO_URL>"
   - DEFAULT_BRANCH=$(git remote show origin | sed -n 's/  HEAD branch: //p' | head -n1 || echo "main")
3) Sicherstellen, dass gh CLI eingeloggt ist:
   - gh auth status

Schritt 1 – Empfohlen: History Cleanup (Secret-Scan konform)
1) Sicherheitsabfrage einbauen: "History-Rewrite bestätigen (ja/nein)?" – Fortfahren nur bei "ja".
2) Cleanup durchführen:
   - git fetch origin --prune || true
   - git checkout -B sanitized/no-secrets origin/$DEFAULT_BRANCH || git checkout -B sanitized/no-secrets $DEFAULT_BRANCH
   - Falls git-filter-repo fehlt: pip install --user git-filter-repo
   - git filter-repo --invert-paths --path _ARCHIVE/quarantine_external/claude_exports_Medexamenai/ --force
   - Verifizieren, dass der Pfad entfernt ist:
     - git ls-files | grep -q "^_ARCHIVE/quarantine_external/claude_exports_Medexamenai/" && echo "Unerwartet vorhanden" || echo "Pfad entfernt"
   - Push:
     - git push -u origin sanitized/no-secrets
   - Cleanup‑PR erstellen:
     - gh pr create --base "$DEFAULT_BRANCH" --head "sanitized/no-secrets" \
       --title "repo: history cleanup (remove archived secrets)" \
       --body "Entfernt archivierte Secret-Inhalte (Claude-Exports) aus der Historie. Erforderlich wegen Push Protection. Hinweis: Nach Merge ggf. Re-Clone/Rebase nötig."

Schritt 2 – Merge abwarten, Feature-Branch rebasen und Phase‑1 PR
1) Cleanup‑PR auf Merge pollen (alle 30–60s, max. 10 Min), danach:
   - git fetch origin --prune
   - git checkout docs/repo-organisation-phase1
   - git rebase origin/$DEFAULT_BRANCH
   - git push -u origin docs/repo-organisation-phase1
2) Phase‑1 PR erstellen:
   - gh pr create --base "$DEFAULT_BRANCH" --head "docs/repo-organisation-phase1" \
     --title "docs: Repo Organisation Guide + .gitignore (phase 1)" \
     --body "Phase 1: Nur Dokumentation + .gitignore; keine Moves. Enthält docs/guides/REPO_ORGANISATION.md und .gitignore-Updates. Keine Ausführung von Pipelines. Canonical bleibt unverändert."

Schritt 3 – Validierungs‑Checkliste
- PR enthält nur: docs/guides/REPO_ORGANISATION.md und .gitignore
- Kein anderer Code/keine Moves im Diff
- Secret‑Scan in PR grün, CI (falls vorhanden) grün

Alternativen (nur mit ausdrücklicher Anweisung)
- Weg B – Secret‑Unblock in GitHub und sofortige Token‑Rotation (nicht empfohlen)
- Weg C – Neues Repo ohne Alt‑Historie

Rollback/Abbruch
- Keine Force‑Pushes auf main/master
- Kein Cleanup ohne bestätigte Zustimmung
- Bei Fehlern mit filter‑repo: Fehlermeldung ausgeben und stoppen

Ergebnis/Reporting
- Nach Erfolg: Beide PR‑URLs ausgeben (Cleanup‑PR, Phase‑1 PR)
- Kurze Zusammenfassung: Default‑Branch, Branch‑Namen, Commits, PR‑Titel
- Falls Push Protection erneut greift: exakte Fehlermeldung protokollieren und ggf. zusätzliche Pfade für Cleanup vorschlagen
