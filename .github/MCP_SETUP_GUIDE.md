# MCP & AI Code Review Setup – Medexamenai

## Übersicht

Dieses Projekt nutzt:
1. **MCP-Server** (Atlassian, GitHub, Notion) für IDE-Integration (Cursor/Claude)
2. **GitHub Actions** für automatische PR-Reviews (Claude, Gemini, Codex)

---

## Teil 1: MCP-Server für IDE (Cursor/Claude Desktop)

### Was sind MCP-Server?

Model Context Protocol (MCP) Server sind lokale Tools, die deiner IDE Zugriff auf externe Dienste geben:
- **Atlassian**: Jira-Tickets direkt in der IDE abfragen
- **GitHub**: Issues, PRs, Commits direkt verwalten
- **Notion**: Datenbanken/Seiten durchsuchen

### Speicherort der Konfiguration

| Tool | Pfad |
|------|------|
| **Cursor** (global) | `~/.cursor/mcp.json` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) |

### Deine bestehende Konfiguration

Du hast bereits eine MCP-Konfiguration in `~/.cursor/mcp.json`. Um sie zu aktivieren:

#### 1. API-Tokens erstellen

##### Atlassian (Jira/Confluence)

1. Öffne: https://id.atlassian.com/manage-profile/security/api-tokens
2. Klicke **"Create API token"**
3. Name: `Cursor MCP Server`
4. Token kopieren (wird nur einmal angezeigt!)

##### GitHub

1. Öffne: https://github.com/settings/tokens
2. Klicke **"Generate new token (classic)"**
3. Name: `Cursor MCP Server`
4. Scopes: `repo`, `read:org`, `read:user`
5. Token kopieren

##### Notion

1. Öffne: https://www.notion.so/my-integrations
2. Klicke **"New integration"**
3. Name: `Cursor MCP`
4. Workspace wählen
5. **Internal Integration Secret** kopieren (beginnt mit `secret_...`)
6. **Wichtig**: Datenbanken/Seiten für die Integration freigeben:
   - Öffne Notion-Seite → `···` → **Add connections** → deine Integration wählen

#### 2. Tokens in MCP-Config eintragen

```bash
# Öffne die Konfiguration
open -e ~/.cursor/mcp.json
```

Ersetze die Platzhalter:

```json
{
  "mcpServers": {
    "atlassian": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-atlassian"],
      "env": {
        "ATLASSIAN_URL": "https://xcorpiodbs.atlassian.net",
        "ATLASSIAN_EMAIL": "deine-email@example.com",
        "ATLASSIAN_API_TOKEN": "HIER-DEIN-TOKEN"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_HIER-DEIN-TOKEN"
      }
    },
    "notion": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-notion"],
      "env": {
        "NOTION_API_KEY": "secret_HIER-DEIN-TOKEN"
      }
    }
  }
}
```

#### 3. Cursor neu starten

Nach dem Speichern:
1. Cursor komplett beenden
2. Neu starten
3. Teste mit: `@claude Frag Atlassian nach offenen Tickets`

---

## Teil 2: GitHub Actions (Automatische PR-Reviews)

### Warum keine API-Keys im Repository?

**Sicherheitsrisiko**: API-Keys in GitHub Secrets sind für jeden mit Repo-Zugriff potentiell zugänglich.

### Option A: Subscription-basierte Services (EMPFOHLEN)

Diese Services nutzen ihre **eigene Authentifizierung** – du brauchst keine API-Keys zu verwalten:

| Service | Kosten | Installation |
|---------|--------|--------------|
| **CodeRabbit** | ~$12-20/Monat | [GitHub Marketplace](https://github.com/marketplace/coderabbitai) |
| **Gemini Code Assist** | Teil von Google Workspace | [Google Cloud Console](https://cloud.google.com/gemini/docs/codeassist) |
| **Copilot for PRs** | $10-19/Monat | GitHub Settings → Copilot → Enable PR reviews |

**Vorteil**: Kein Token-Management, keine Secrets, automatische Updates.

### Option B: Eigene API-Keys (nur für private/persönliche Repos)

Falls du trotzdem eigene API-Keys nutzen willst:

#### 1. API-Keys erstellen

##### Claude (Anthropic)

1. Öffne: https://console.anthropic.com/settings/keys
2. Erstelle neuen Key: `GitHub Actions Medexamenai`
3. **Wichtig**: Monatliches Budget setzen (z.B. $10)

##### Gemini (Google AI)

1. Öffne: https://aistudio.google.com/app/apikey
2. Erstelle API-Key
3. Optional: Quota in Google Cloud Console limitieren

##### OpenAI / OpenRouter (optional)

1. OpenAI: https://platform.openai.com/api-keys
2. OpenRouter: https://openrouter.ai/keys

#### 2. GitHub Secrets einrichten

1. Gehe zu: https://github.com/DEIN-USERNAME/Medexamenai/settings/secrets/actions
2. Klicke **"New repository secret"**
3. Füge hinzu:

| Name | Wert |
|------|------|
| `ANTHROPIC_API_KEY` | `sk-ant-api03-...` |
| `GOOGLE_AI_API_KEY` | `AIza...` |
| `CODEX_API_KEY` | OpenAI/OpenRouter Key (optional) |
| `CODEX_API_BASE` | `https://openrouter.ai/api/v1` (optional) |

#### 3. Workflow testen

1. Erstelle einen Test-Branch: `git checkout -b test-ai-review`
2. Mache eine kleine Änderung
3. Push & erstelle PR
4. Warte auf AI-Review-Kommentare

---

## Sicherheitsrichtlinien

### ⚠️ WICHTIG: Secrets niemals committen!

```bash
# Füge zur .gitignore hinzu (falls noch nicht vorhanden)
echo "mcp.json" >> .gitignore
echo ".cursor/mcp.json" >> .gitignore
echo ".env" >> .gitignore
```

### Token-Rotation (alle 3-6 Monate)

- Setze Kalender-Reminder für Token-Erneuerung
- Alte Tokens widerrufen nach Erneuerung

### Budget-Limits setzen

| Service | Budget-Limit |
|---------|--------------|
| Anthropic | https://console.anthropic.com/settings/limits |
| Google AI | https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas |
| OpenAI | https://platform.openai.com/usage |

**Empfohlene Limits für Medexamenai**:
- Claude: $10/Monat (ca. 200 PR-Reviews)
- Gemini: 1500 Requests/Tag (Standard-Quota ausreichend)

---

## Troubleshooting

### MCP-Server startet nicht

```bash
# Prüfe Node.js Installation
node --version  # Sollte v18+ sein

# Teste MCP-Server manuell
npx -y @modelcontextprotocol/server-github
```

### GitHub Actions Review schlägt fehl

1. Prüfe Secrets: Settings → Secrets → Actions
2. Prüfe Workflow-Logs: Actions → letzter Run → Job-Details
3. Häufige Fehler:
   - `401 Unauthorized`: API-Key falsch oder abgelaufen
   - `429 Too Many Requests`: Rate-Limit erreicht
   - `No diff found`: PR hat keine Code-Änderungen

### Atlassian MCP funktioniert nicht

1. Prüfe E-Mail: Muss exakt mit Atlassian-Account übereinstimmen
2. Prüfe URL: Format `https://DEIN-WORKSPACE.atlassian.net` (ohne `/` am Ende)
3. Teste API-Token:

```bash
curl -u "deine-email@example.com:DEIN-TOKEN" \
  https://xcorpiodbs.atlassian.net/rest/api/3/myself
```

---

## Zusammenfassung

✅ **MCP für IDE**: Tokens in `~/.cursor/mcp.json` eintragen, Cursor neu starten
✅ **GitHub Actions**: Entweder Subscription-Service (CodeRabbit) ODER eigene API-Keys in Secrets
✅ **Sicherheit**: Niemals Tokens committen, Budget-Limits setzen, regelmäßig rotieren

**Empfohlener Workflow**:
1. MCP-Server für IDE-Produktivität nutzen (Jira-Tickets, GitHub-Issues direkt bearbeiten)
2. CodeRabbit oder ähnlichen Service für PR-Reviews nutzen (keine Token-Verwaltung)
3. Falls eigene API-Keys: Monatliches Budget bei Providern setzen
