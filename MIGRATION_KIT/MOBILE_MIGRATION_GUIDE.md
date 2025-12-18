# Mobile Migration Guide - Neues MacBook

**Für unterwegs - Schnellanleitung zur API-Key Migration**

---

## Voraussetzungen

- Neues MacBook mit Internetzugang
- Homebrew installiert
- GitHub-Zugang (für Repo-Clone)
- Google-Account (für Drive-Zugriff)

---

## Schritt 1: Basis-Tools installieren (5 Min)

```bash
# Homebrew (falls nicht vorhanden)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Benötigte Tools
brew install git python@3.9 rclone gh
```

---

## Schritt 2: GitHub authentifizieren (2 Min)

```bash
gh auth login
# Browser öffnet sich -> GitHub Login
```

---

## Schritt 3: Projekt klonen (2 Min)

```bash
cd ~
gh repo clone MellB92/medexam-ai Medexamenai
cd Medexamenai
```

---

## Schritt 4: rclone für Google Drive einrichten (3 Min)

```bash
rclone config

# Folgende Eingaben:
# n) New remote
# name> gdrive
# Storage> drive (oder Nummer für Google Drive)
# client_id> (leer lassen, Enter)
# client_secret> (leer lassen, Enter)
# scope> 1 (Full access)
# root_folder_id> (leer lassen, Enter)
# service_account_file> (leer lassen, Enter)
# Edit advanced config> n
# Use auto config> y
# Browser öffnet sich -> Google Login
# Configure as team drive> n
# y) Yes this is OK
# q) Quit config
```

---

## Schritt 5: Verschlüsselte Datei herunterladen (1 Min)

```bash
rclone copy gdrive:/Medexamenai_Migration/env_migration_encrypted.zip ~/Downloads/
cd ~/Downloads
unzip env_migration_encrypted.zip
```

**Passwort:** `MedExam2025!`

---

## Schritt 6: .env Datei einrichten (2 Min)

```bash
cd ~/Medexamenai

# Inhalte aus der Anleitung kopieren
nano .env
# INHALT AUS ENV_MIGRATION_NEUES_MACBOOK.md EINFÜGEN
# Ctrl+O, Enter, Ctrl+X

# Berechtigungen setzen
chmod 600 .env
```

---

## Schritt 7: AWS Credentials einrichten (2 Min)

```bash
mkdir -p ~/.aws

# Credentials (aus der verschlüsselten Migrations-Datei kopieren!)
nano ~/.aws/credentials
# Inhalt aus ENV_MIGRATION_NEUES_MACBOOK.md einfügen
# Format:
# [default]
# aws_access_key_id = <AUS_MIGRATIONS_DATEI>
# aws_secret_access_key = <AUS_MIGRATIONS_DATEI>

# Config
cat > ~/.aws/config << 'EOF'
[default]
region = us-east-1
output = json
profile = default
EOF

chmod 600 ~/.aws/credentials ~/.aws/config
```

**WICHTIG:** Die AWS-Credentials stehen in der verschlüsselten Datei `ENV_MIGRATION_NEUES_MACBOOK.md`!

---

## Schritt 8: Python Environment einrichten (5 Min)

```bash
cd ~/Medexamenai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Schritt 9: Verbindungen testen (1 Min)

```bash
PYTHONPATH=. .venv/bin/python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()

providers = [
    ('Requesty', 'REQUESTY_API_KEY'),
    ('Anthropic', 'ANTHROPIC_API_KEY'),
    ('Perplexity', 'PERPLEXITY_API_KEY'),
    ('OpenAI', 'OPENAI_API_KEY'),
    ('Portkey', 'PORTKEY_API_KEY'),
]

print('=== API-Key Status ===')
for name, key in providers:
    status = 'OK' if os.getenv(key) else 'FEHLT'
    print(f'{name}: {status}')
"
```

---

## Schritt 10: Aufräumen (1 Min)

```bash
# Migrations-Dateien löschen
rm ~/Downloads/env_migration_encrypted.zip
rm ~/Downloads/ENV_MIGRATION_NEUES_MACBOOK.md

# Optional: Aus Google Drive löschen
rclone delete gdrive:/Medexamenai_Migration/env_migration_encrypted.zip
```

---

## Checkliste

- [ ] Homebrew installiert
- [ ] Git, Python, rclone, gh installiert
- [ ] GitHub authentifiziert
- [ ] Repo geklont
- [ ] rclone mit Google Drive verbunden
- [ ] Verschlüsselte Datei heruntergeladen
- [ ] .env Datei erstellt und geschützt
- [ ] AWS Credentials eingerichtet
- [ ] Python venv eingerichtet
- [ ] API-Verbindungen getestet
- [ ] Migrations-Dateien gelöscht

---

## Troubleshooting

### rclone kann sich nicht mit Google Drive verbinden
```bash
rclone config reconnect gdrive:
```

### Python-Module fehlen
```bash
pip install python-dotenv anthropic openai boto3
```

### Permission denied bei .env
```bash
chmod 600 .env
ls -la .env  # sollte -rw------- zeigen
```

---

## Zeitaufwand gesamt: ~25 Minuten

**Support:** Bei Problemen siehe Jira-Ticket MED-XX oder GitHub Issue.
