# 🤖 AI Code Reviewer Setup

Dieses Repository nutzt mehrere AI-Code-Reviewer für automatische Pull-Request-Reviews.

## Verfügbare AI-Reviewer

1. **Claude Code** (Anthropic)
2. **Gemini Code Assistant** (Google)
3. **GitHub Copilot**
4. **Codex**
5. **Cursorbot** (Cursor AI - Trial bis 11. Dezember)

## Konfiguration

### Repository Secrets einrichten

Gehe zu: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

#### Erforderliche Secrets:

| Secret Name | Beschreibung | Wo zu finden |
|------------|--------------|--------------|
| `ANTHROPIC_API_KEY` | Claude Code API Key | [Anthropic Console](https://console.anthropic.com/) |
| `GOOGLE_AI_API_KEY` | Gemini Code Assistant API Key | [Google AI Studio](https://makersuite.google.com/app/apikey) |
| `GITHUB_COPILOT_TOKEN` | GitHub Copilot Token (optional) | GitHub Copilot Settings |
| `CODEX_API_KEY` | Codex API Key | Codex Dashboard |
| `CODEX_API_URL` | Codex API URL (optional) | Standard: `https://api.codex.ai/v1` |
| `CURSOR_API_KEY` | Cursorbot API Key | [Cursor Dashboard](https://cursor.com/dashboard) |

### GitHub Copilot Alternative

GitHub Copilot funktioniert am besten als GitHub App:
1. Gehe zu [GitHub Copilot Settings](https://github.com/settings/copilot)
2. Installiere die GitHub Copilot App für dieses Repository
3. Die App erstellt automatisch Reviews bei Pull Requests

### Workflow-Verhalten

- **Automatische Reviews**: Alle konfigurierten Reviewer werden bei jedem Pull Request ausgeführt
- **Kommentar-Trigger**: Nutze `@claude`, `@gemini`, `@codex`, `@cursorbot` oder `@copilot` in PR-Kommentaren für gezielte Antworten
- **Review-Fokus** (Priorität):

  **1. Medizinische Präzision & Fachliche Richtigkeit:**
  - Medizinische Terminologie, Dosierungen und klinische Leitlinien
  - Potenzielle medizinische Fehlinformationen oder gefährliche Empfehlungen
  - Arzneimittelwechselwirkungen, Kontraindikationen und Sicherheitsprüfungen
  - Genauigkeit der medizinischen Datenverarbeitung

  **2. API-Token-Verschwendung:**
  - Unnötige API-Aufrufe oder redundante Requests
  - Fehlende Caching-Mechanismen (Prompt-Caching, Response-Caching)
  - Fehlende Budget-Checks vor API-Aufrufen
  - Ineffiziente Token-Nutzung (überdimensionierte Prompts, redundanter Kontext)
  - Fehlende Fehlerbehandlung, die Retry-Schleifen verursacht
  - Fehlende Rate-Limiting oder Token-Counting
  - Unangemessene max_tokens-Einstellungen
  - Duplizierte API-Aufrufe, die gebatcht werden könnten

  **3. Code-Qualität:**
  - Sicherheitsprobleme
  - Bugs
  - Best Practices

## mcp.json Konfiguration

Die `mcp.json` Datei ist bereits für folgende Integrationen konfiguriert:

- **Atlassian** (Jira)
- **Notion**
- **GitHub**
- **Filesystem**

### mcp.json Secrets konfigurieren

Ersetze die Platzhalter in `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "atlassian": {
      "env": {
        "ATLASSIAN_EMAIL": "deine-email@example.com",
        "ATLASSIAN_API_TOKEN": "dein-atlassian-token"
      }
    },
    "notion": {
      "env": {
        "NOTION_API_KEY": "dein-notion-token"
      }
    },
    "github": {
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "dein-github-pat"
      }
    }
  }
}
```

### API-Tokens erstellen

#### Atlassian API Token:
1. Gehe zu [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Klicke auf "Create API token"
3. Kopiere den Token in `mcp.json`

#### Notion Integration Token:
1. Gehe zu [Notion Integrations](https://www.notion.so/my-integrations)
2. Erstelle eine neue Integration
3. Kopiere den "Internal Integration Token" in `mcp.json`
4. Teile die Integration mit den gewünschten Seiten/Datenbanken

#### GitHub Personal Access Token:
1. Gehe zu [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Erstelle einen neuen Token mit `repo` Berechtigung
3. Kopiere den Token in `mcp.json`

## Troubleshooting

### Reviews werden nicht erstellt
- Prüfe, ob die Secrets korrekt gesetzt sind
- Prüfe die GitHub Actions Logs für Fehlermeldungen
- Stelle sicher, dass der Workflow aktiviert ist

### API-Fehler
- Überprüfe die API-Keys auf Gültigkeit
- Prüfe Rate Limits der jeweiligen APIs
- Stelle sicher, dass die API-Endpunkte korrekt sind

### Cursorbot Trial abgelaufen
- Der Cursorbot-Trial läuft bis zum 11. Dezember
- Nach Ablauf muss ein gültiger `CURSOR_API_KEY` gesetzt werden

## Workflow-Datei

Die Workflow-Datei befindet sich unter: `.github/workflows/ai-reviews.yml`

