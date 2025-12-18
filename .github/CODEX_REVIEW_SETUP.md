# Codex / Multiagent Code Review Setup

Dieses Repository nutzt einen Multiagent-Workflow für automatische Pull-Request-Reviews im Projekt **Medexamenai**.

## 1. Verwendete Reviewer

- Claude Sonnet 4.5 (Anthropic)
- Gemini 2.5 Pro (Google AI / Gemini Code Assistant)
- Codex (OpenAI-kompatibel, z.B. GPT-4.1-mini)

GitHub Copilot, Claude Code und Cursorbot arbeiten in der IDE und profitieren indirekt von denselben APIs.

## 2. Benötigte GitHub Secrets

In `Settings → Secrets and variables → Actions`:

- ANTHROPIC_API_KEY
- GOOGLE_AI_API_KEY
- CODEX_API_KEY_DAGO  → API-Key für ChatGPT/Codex Account: dagobertduck@wolvers-bobadillas.net
- CODEX_API_KEY_ICLOUD → API-Key für ChatGPT/Codex Account: dbsnuklearmedizin@icloud.com
- optional CODEX_API_BASE (z.B. https://api.openai.com)

Der Standard-GITHUB_TOKEN ist automatisch vorhanden.

## 3. Trigger

- PR-Events (opened, synchronize, reopened): alle drei Reviewer.
  - Issue-Kommentare:
  - @claude → nur Claude-Job
  - @gemini → nur Gemini-Job
  - @codex → Codex-Job, nimmt automatisch iCloud wenn vorhanden, sonst Dagobert
  - @codex-icloud → erzwingt iCloud-Account
  - @codex-dago → erzwingt Dagobert-Account
  - @ai-review → triggert ALLE Reviewer (Claude, Gemini, Codex)

Zusätzlich können auf Pull Requests Labels genutzt werden, um den Codex-Account für automatische Reviews zu steuern:
- Label `codex:icloud` → nutzt iCloud-Account
- Label `codex:dagobert` → nutzt Dagobert-Account

## 4. Review-Fokus

1. Medizinische Präzision & fachliche Richtigkeit
2. API-Token-Verschwendung (Budget-Schutz)
3. Codequalität & Sicherheit

## 5. Troubleshooting

- „Skipped: … fehlt.“ → zugehöriger Secret-Key nicht gesetzt
- „API call failed“ → URL, Modellname, Key prüfen
- Zu viel Tokenverbrauch → MAX_DIFF_LENGTH im Workflow reduzieren

## 6. Einrichtungsschritte (Kurz)
1) In beiden ChatGPT/Codex-Accounts jeweils einen API-Key erzeugen.
2) In GitHub Repository Settings → Secrets and variables → Actions:
   - Secret `CODEX_API_KEY_ICLOUD` mit dem Key des Accounts dbsnuklearmedizin@icloud.com anlegen.
   - Secret `CODEX_API_KEY_DAGO` mit dem Key des Accounts dagobertduck@wolvers-bobadillas.net anlegen.
3) Optional PR-Label setzen (`codex:icloud` oder `codex:dagobert`) oder in Kommentaren @codex-icloud bzw. @codex-dago nutzen.
4) Ergebnis erscheint als PR-Kommentar „Codex Code Review (iCloud/Dagobert)“.

