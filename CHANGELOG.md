# Changelog

## 2025-12-01
- Initial commit: Code, Doku, Config, Leitlinien-Manifest.
- Leitlinien-Pfad fest verdrahtet auf `_BIBLIOTHEK/Leitlinien/`.
- Multi-Provider Routing über `unified_api_client` (Requesty → Anthropic → Bedrock/Portkey → Comet → Perplexity → OpenRouter → OpenAI).

## 2025-12-21
- Repo-Hygiene/Security: GitHub Push Protection behoben durch History Cleanup (git-filter-repo) und Bereinigung des Branch `Medexamenai`.
- Doku: PR #7 gemerged (https://github.com/MellB92/medexam-ai/pull/7) – Repo Organisation Guide.
- Git: `.gitignore` erweitert um lokale Agent-Artefakte zu ignorieren (`_AGENT_WORK/`, `AGENT_*.md`).
