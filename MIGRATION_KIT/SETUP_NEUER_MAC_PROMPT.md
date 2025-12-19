# Claude Code Prompt - Neuer Mac Setup & Sicherheits-Cleanup

**Kopiere diesen Prompt und führe ihn auf deinem neuen Mac in Claude Code aus.**

---

## PROMPT ZUM KOPIEREN

```
Ich bin auf einem neuen Mac und muss mein Medexamenai-Projekt sicher einrichten.
Bitte führe folgende Schritte der Reihe nach aus und bestätige jeden Schritt.

## PHASE 1: Projekt klonen

1. Klone das Repository:
   git clone https://github.com/MellB92/medexam-ai.git ~/Medexamenai
   cd ~/Medexamenai

2. Bestätige dass MIGRATION_KIT/ENV_MIGRATION_NEUES_MACBOOK.md existiert und lies den Inhalt.

## PHASE 2: API Keys einrichten

3. Erstelle die .env Datei im Projekt-Root (~/Medexamenai/.env):
   - Extrahiere den kompletten .env Block aus Abschnitt 1 der ENV_MIGRATION_NEUES_MACBOOK.md
   - Schreibe ihn in ~/Medexamenai/.env
   - Führe aus: chmod 600 ~/Medexamenai/.env

4. Erstelle AWS Credentials:
   - mkdir -p ~/.aws
   - Extrahiere den [default] Block für credentials aus Abschnitt 2
   - Schreibe ihn in ~/.aws/credentials
   - Extrahiere den [default] Block für config aus Abschnitt 2
   - Schreibe ihn in ~/.aws/config
   - Führe aus: chmod 600 ~/.aws/credentials ~/.aws/config

## PHASE 3: Python Environment

5. Richte Python ein:
   cd ~/Medexamenai
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

## PHASE 4: Verifizierung

6. Teste die API-Verbindungen mit diesem Python-Script:
   cd ~/Medexamenai && source .venv/bin/activate
   PYTHONPATH=. python3 -c "
   from dotenv import load_dotenv
   import os
   load_dotenv()
   print('=== API Key Check ===')
   keys = [
       ('Requesty', 'REQUESTY_API_KEY'),
       ('Anthropic', 'ANTHROPIC_API_KEY'),
       ('Perplexity', 'PERPLEXITY_API_KEY'),
       ('OpenAI', 'OPENAI_API_KEY'),
       ('Portkey', 'PORTKEY_API_KEY'),
       ('AWS Region', 'AWS_REGION')
   ]
   for name, key in keys:
       val = os.getenv(key)
       status = 'OK' if val else 'FEHLT'
       print(f'{name}: {status}')
   "

   Erwartetes Ergebnis: Alle sollten "OK" zeigen.

## PHASE 5: Sicherheits-Cleanup (KRITISCH!)

7. Entferne sensible Dateien aus Git-Tracking:
   cd ~/Medexamenai

   # Aus Git-Index entfernen (Datei bleibt lokal)
   git rm --cached MIGRATION_KIT/ENV_MIGRATION_NEUES_MACBOOK.md 2>/dev/null || echo "Datei war nicht im Index"

   # .gitignore aktualisieren
   cat >> .gitignore << 'GITIGNORE_ADDITIONS'

   # === SECURITY: Sensible Dateien ===
   .env
   .env.*
   *.env
   MIGRATION_KIT/ENV_MIGRATION_NEUES_MACBOOK.md
   MIGRATION_KIT/env_migration_encrypted.zip
   ~/.aws/credentials
   GITIGNORE_ADDITIONS

   # Duplikate entfernen
   sort -u .gitignore -o .gitignore

8. Prüfe ob sensible Dateien im Git-Verlauf sind:
   cd ~/Medexamenai
   echo "=== Checking Git History for Secrets ==="

   git log --all --oneline -- "MIGRATION_KIT/ENV_MIGRATION_NEUES_MACBOOK.md" | head -5
   git log --all --oneline -- ".env" | head -5

   Falls Commits gefunden werden, STOPPE und informiere mich!
   Die API-Keys müssen dann rotiert werden.

9. Commit der Sicherheitsänderungen:
   cd ~/Medexamenai
   git add .gitignore
   git commit -m "security: sensible Dateien von Git-Tracking ausschließen"
   git push origin main

## PHASE 6: Lokale Cleanup

10. Sichere und lösche die Migrations-Datei:
    # Backup auf Desktop
    cp ~/Medexamenai/MIGRATION_KIT/ENV_MIGRATION_NEUES_MACBOOK.md ~/Desktop/API_KEYS_BACKUP_$(date +%Y%m%d).md
    echo "Backup erstellt: ~/Desktop/API_KEYS_BACKUP_$(date +%Y%m%d).md"

    # Sensible Dateien aus Projekt löschen
    rm ~/Medexamenai/MIGRATION_KIT/ENV_MIGRATION_NEUES_MACBOOK.md
    rm ~/Medexamenai/MIGRATION_KIT/env_migration_encrypted.zip 2>/dev/null || true

    echo "Sensible Migrations-Dateien gelöscht."

## ABSCHLUSS

11. Zeige mir eine Zusammenfassung:
    - Wurden alle API-Keys erfolgreich eingerichtet?
    - Wurden sensible Dateien im Git-Verlauf gefunden?
    - Ist das Projekt einsatzbereit?

Falls sensible Dateien im Git-Verlauf gefunden wurden, liste mir die Links zum Rotieren der Keys auf.
```

---

## NACH DER MIGRATION

### Falls Keys im Git-Verlauf waren - ROTIEREN!

| Provider | Link zum Rotieren |
|----------|-------------------|
| Requesty | https://app.requesty.ai/settings/api-keys |
| Anthropic | https://console.anthropic.com/settings/keys |
| AWS | https://console.aws.amazon.com/iam/home#/security_credentials |
| Perplexity | https://www.perplexity.ai/settings/api |
| OpenAI | https://platform.openai.com/api-keys |
| Portkey | https://app.portkey.ai/api-keys |

---

## CHECKLISTE

- [ ] Repository geklont
- [ ] .env erstellt und mit chmod 600 geschützt
- [ ] AWS credentials erstellt und geschützt
- [ ] Python venv eingerichtet
- [ ] API-Verbindungen getestet (alle OK)
- [ ] Sensible Dateien aus Git-Tracking entfernt
- [ ] .gitignore aktualisiert und gepusht
- [ ] Git-Verlauf auf Secrets geprüft
- [ ] Lokale Migrations-Datei gelöscht
- [ ] Backup auf Desktop erstellt
- [ ] (Falls nötig) API-Keys rotiert

---

**Erstellt:** 2025-12-19
**Zweck:** Sichere Migration auf neuen Mac mit Cleanup sensibler Daten
