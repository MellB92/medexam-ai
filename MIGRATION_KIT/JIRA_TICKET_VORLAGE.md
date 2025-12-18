# Jira-Ticket Vorlage: API-Keys Migration

**Erstellen unter:** https://xcorpiodbs.atlassian.net/jira/software/projects/MED/boards/7

---

## Ticket-Details

| Feld | Wert |
|------|------|
| **Projekt** | MED |
| **Typ** | Task |
| **Zusammenfassung** | Migration: API-Keys auf neues MacBook übertragen |
| **Priorität** | High |
| **Labels** | migration, infrastructure, security |

---

## Beschreibung (Copy-Paste)

```
h2. Beschreibung

Migration aller API-Schlüssel und Konfigurationsdateien auf das neue MacBook.

h2. Verschlüsselte Datei

* *Speicherort:* gdrive:/Medexamenai_Migration/env_migration_encrypted.zip
* *Passwort:* MedExam2025!

h2. Enthaltene API-Keys

|| Provider || Verwendung ||
| Requesty | Primary LLM Router |
| Anthropic | Direct Claude Access |
| AWS Bedrock | Claude via AWS |
| Perplexity | Leitlinien-Recherche (2 Keys) |
| OpenAI | Embeddings |
| Portkey | Multiprovider Gateway |

h2. Migrations-Anleitung

Siehe GitHub: [MOBILE_MIGRATION_GUIDE.md|https://github.com/MellB92/medexam-ai/blob/main/MIGRATION_KIT/MOBILE_MIGRATION_GUIDE.md]

h2. Sicherheitsmaßnahmen

# ZIP-Datei ist passwortgeschützt (AES-256)
# Alle sensiblen Daten in .gitignore
# chmod 600 auf .env und AWS credentials
# Nach Migration: Dateien aus Google Drive löschen
# Bei Verdacht auf Kompromittierung: Keys sofort rotieren

h2. Verknüpfte Issues

* GitHub Issue: [#5|https://github.com/MellB92/medexam-ai/issues/5]

h2. Checkliste

* [ ] Homebrew installiert
* [ ] Tools installiert (git, python, rclone, gh)
* [ ] GitHub authentifiziert
* [ ] Repo geklont
* [ ] rclone konfiguriert
* [ ] .env eingerichtet
* [ ] AWS credentials eingerichtet
* [ ] Python venv eingerichtet
* [ ] API-Tests bestanden
* [ ] Migrations-Dateien gelöscht
* [ ] Keys aus Google Drive entfernt

h2. Zeitaufwand

~25 Minuten

h2. Notfall-Kontakte für Key-Rotation

* Requesty: https://app.requesty.ai/settings/api-keys
* Anthropic: https://console.anthropic.com/settings/keys
* AWS: IAM Console > Security Credentials
* Perplexity: https://www.perplexity.ai/settings/api
* OpenAI: https://platform.openai.com/api-keys
* Portkey: https://app.portkey.ai/api-keys
```

---

## Nach dem Erstellen

1. Ticket-Nummer notieren (z.B. MED-15)
2. GitHub Issue #5 mit Jira-Ticket verlinken
3. In GitHub Issue kommentieren: "Jira: MED-XX"
