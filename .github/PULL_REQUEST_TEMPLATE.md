## Zusammenfassung

- [ ] Änderungen kurz beschrieben
- [ ] Relevante Tickets/Issues verlinkt

## Checks

- [ ] Tests/Lint ausgeführt (oder nicht nötig)
- [ ] Keine großen Dateien/Derived-Daten committed
- [ ] `.env`/Secrets nicht im Diff
- [ ] AI-Review Trigger geprüft (`@claude`, `@gemini`, `@codex` oder Sammel-Alias `@ai-review`)
- [ ] CI "Quality Gate" grün bzw. bekannte Ausnahmen verlinkt

## Notizen

- Automatische Reviews laufen über `.github/workflows/ai-reviews.yml`
- `@ai-review` in PR-Kommentaren triggert alle Reviewer (Claude, Gemini, Codex). Einzelne Reviewer per `@claude`/`@gemini`/`@codex`.
- Bei fehlenden API-Keys: GitHub Apps (Claude/Gemini/CodeRabbit) oder `@ai-review` Kommentar nutzen
