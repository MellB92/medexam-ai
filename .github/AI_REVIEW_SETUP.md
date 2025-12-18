# AI Code Review Setup - GitHub Actions

Dieser Workflow ermöglicht automatische Code-Reviews durch Claude (Anthropic) und Gemini (Google AI) bei Pull Requests.

## Funktionalität

- ✅ Automatische Code-Reviews bei jedem Pull Request
- ✅ Kommentare mit `@claude` oder `@gemini` in PRs/Issues
- ✅ Fokus auf medizinische Genauigkeit, Sicherheit und Code-Qualität
- ✅ Unterstützung für Python, JavaScript, TypeScript, Markdown

## Setup

### 1. GitHub Secrets konfigurieren

Gehe zu: `Settings > Secrets and variables > Actions` in deinem Repository

Füge folgende Secrets hinzu:

#### Für Claude Reviews:
- **Name:** `ANTHROPIC_API_KEY`
- **Wert:** Dein Anthropic API Key (von https://console.anthropic.com/)

#### Für Gemini Reviews:
- **Name:** `GOOGLE_AI_API_KEY`
- **Wert:** Dein Google AI API Key (von https://aistudio.google.com/app/apikey)

### 2. API Keys erhalten

#### Anthropic (Claude):
1. Gehe zu: https://console.anthropic.com/
2. Erstelle einen Account oder logge dich ein
3. Gehe zu "API Keys"
4. Klicke auf "Create Key"
5. Kopiere den Key (beginnt mit `sk-ant-...`)

#### Google AI (Gemini):
1. Gehe zu: https://aistudio.google.com/app/apikey
2. Klicke auf "Create API Key"
3. Wähle ein Projekt aus oder erstelle ein neues
4. Kopiere den generierten Key

### 3. Workflow aktivieren

Der Workflow ist bereits aktiviert, sobald die Datei `.github/workflows/ai-reviews.yml` existiert.

**Wichtig:**
- Der Workflow läuft nur, wenn die entsprechenden Secrets gesetzt sind
- Wenn keine Secrets vorhanden sind, wird eine Info-Nachricht ausgegeben

## Verwendung

### Automatische Reviews

Bei jedem Pull Request werden automatisch Reviews erstellt (falls API Keys vorhanden):

- **Claude:** Reviewt alle Code-Änderungen (*.py, *.js, *.ts, *.tsx, *.md)
- **Gemini:** Reviewt Python-Änderungen (*.py)

### Manuelle AI-Anfragen

Du kannst in PR-Kommentaren die AI direkt ansprechen:

- `@claude` - Stelle Claude eine Frage
- `@gemini` - Stelle Gemini eine Frage
- `@ai-review` - Zeige Hilfe-Text an

**Beispiel:**
```
@claude Kannst du mir erklären, warum diese Funktion so implementiert wurde?
```

## Kosten

### Anthropic (Claude):
- **Modell:** Claude Opus 4.5 (beste Preis-Leistung)
- **API Modellname:** `claude-opus-4.5`
- **Preis:** $5 pro 1M Input-Tokens, $25 pro 1M Output-Tokens
- **Typische Review:** ~0.02-0.08$ pro PR (abhängig von Diff-Größe)
- **Vorteil:** Höchste Genauigkeit und Effizienz, löst Probleme oft in einem Durchlauf
- **Hinweis:** Falls der Modellname nicht funktioniert, prüfe die verfügbaren Modelle in der Anthropic Console oder verwende temporär `claude-3-5-sonnet-20241022` als Fallback

### Google AI (Gemini):
- **Modell:** Gemini 1.5 Flash
- **Preis:** Kostenlos für moderate Nutzung, dann Pay-as-you-go
- **Typische Review:** Meist kostenlos, bei hoher Nutzung ~$0.01 pro PR

## Troubleshooting

### Reviews werden nicht erstellt:
1. Prüfe, ob die Secrets korrekt gesetzt sind
2. Prüfe die GitHub Actions Logs
3. Stelle sicher, dass der Workflow nicht deaktiviert ist

### API-Fehler:
- **401 Unauthorized:** API Key ist falsch oder abgelaufen
- **429 Too Many Requests:** Rate Limit erreicht, warte kurz
- **500 Internal Server Error:** Temporärer Fehler, versuche es später erneut

### Workflow läuft nicht:
- Prüfe, ob der Branch `main` oder `master` heißt (Workflow ist bereits aktiv)
- Prüfe die GitHub Actions Berechtigungen
- Stelle sicher, dass Actions für das Repository aktiviert sind

## Deaktivieren

Um den Workflow zu deaktivieren:

1. Lösche oder benenne um: `.github/workflows/ai-reviews.yml`
2. Oder entferne die Secrets (Workflow läuft dann ohne Reviews)

## Erweiterte Konfiguration

### Review-Prompt anpassen

Bearbeite die `content`-Felder in `.github/workflows/ai-reviews.yml`:

```yaml
"content": "Review this code diff for a medical exam AI project. Focus on: 1) Medical accuracy risks 2) Security issues 3) Code quality. Be concise and actionable.\n\nDiff:\n$DIFF"
```

### Dateitypen ändern

Bearbeite die `git diff` Befehle:

```bash
# Aktuell: Python, JS, TS, TSX, Markdown
DIFF=$(git diff ... -- '*.py' '*.js' '*.ts' '*.tsx' '*.md' ...)

# Beispiel: Nur Python
DIFF=$(git diff ... -- '*.py' ...)
```

### Max Token Limit anpassen

Ändere `max_tokens` in den API-Aufrufen (höhere Werte = längere Reviews, aber teurer).

## Sicherheit

⚠️ **WICHTIG:**
- API Keys sind als GitHub Secrets gespeichert und werden nicht im Code angezeigt
- Reviews enthalten keine sensiblen Daten (nur Code-Diffs)
- Stelle sicher, dass der Workflow nur auf vertrauenswürdigen Branches läuft

## Alternative: GitHub Apps

Wenn du keine API Keys verwalten möchtest, kannst du GitHub Apps verwenden:

- **CodeRabbit:** https://github.com/apps/coderabbit
- **GitHub Copilot:** Aktiviert in Repository Settings
- **Gemini for GitHub:** Offizielle Google Integration

Diese Apps verwenden ihre eigene Authentifizierung und Abrechnung.

