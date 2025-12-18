# Migration Kit – Medexamenai

Diese Dateien helfen dir, das Projekt auf einen anderen Mac zu migrieren, ohne dass Fortschritt verloren geht.

## Was ist groß (Orientierung)

- `_FACT_CHECK_SOURCES/` (~4.1G) – optional, nur nötig wenn du die Quellen lokal weiter nutzen willst
- `_OUTPUT/` (~2.4G) – **wichtig** (alle erzeugten Artefakte & Checkpoints)
- `venv/` (~866M) – optional (du kannst es auf dem neuen Mac neu erstellen)
- `_BIBLIOTHEK/` (~319M) – empfohlen (Leitlinien/Manifest)
- `_GOLD_STANDARD/` (~278M) – empfohlen (Goldstandard PDFs/DOCX/ODT)

## WICHTIG: Secrets

Im Repo Root existiert eine `.env`. **Diese Datei enthält API‑Keys.**

- Für Migration: **nicht in öffentliche ZIPs/Cloud hochladen**.
- Wenn du per externer SSD direkt zwischen deinen eigenen Macs kopierst, kannst du `.env` mitnehmen.
- Für „saubere“ Migration: nutze `.env.example` und setze Keys danach neu.

## Option A (empfohlen): Vollständige Kopie per rsync

Kopiert alles (inkl. `_FACT_CHECK_SOURCES/`). Dauert länger, aber am wenigsten „Überraschungen“.

```bash
rsync -a --info=progress2 /Users/user/Medexamenai/ /Volumes/EXTERNAL/Medexamenai/
```

Alternativ: `MIGRATION_KIT/rsync_full.sh` (nimmt Zielpfad als erstes Argument).

## Option B: Schlanke Migration (ohne große Quellen & venv)

Reicht aus, um die Pipeline/Exports weiterzuführen.

```bash
rsync -a --info=progress2 \
  --exclude '.env' \
  --exclude 'venv/' \
  --exclude '_FACT_CHECK_SOURCES/' \
  /Users/user/Medexamenai/ /Volumes/EXTERNAL/Medexamenai/
```

Wenn du `_FACT_CHECK_SOURCES/` später doch brauchst, kannst du den Ordner separat nachziehen.

Alternativ: `MIGRATION_KIT/rsync_minimal.sh` (nimmt Zielpfad als erstes Argument).

## Option C (empfohlen bei Google Drive): Ein einziges Bundle (tar) + Upload

Viele einzelne Dateien nach Google Drive hochladen ist oft sehr langsam. Besser:
**ein einziges Archiv** erstellen und dieses hochladen.

### 1) Bundle erstellen (ohne `.git`, `backups/`, `dropbox_import/`, `venv/`, `.env`)

```bash
./MIGRATION_KIT/package_gdrive_bundle.sh
```

Optional (kleiner): ohne `_FACT_CHECK_SOURCES/`

```bash
./MIGRATION_KIT/package_gdrive_bundle.sh --slim
```

Optional: zusätzlich gzip (meist nur wenig Effekt bei PDFs)

```bash
./MIGRATION_KIT/package_gdrive_bundle.sh --gzip
```

Das Bundle landet in: `_OUTPUT/migration_bundles/`

### 2) Upload nach Google Drive via rclone

```bash
./MIGRATION_KIT/rclone_upload_bundle.sh _OUTPUT/migration_bundles/<BUNDLE>.tar gdrive: Medexamenai_Migration_20251217
```

## Download + Entpacken auf dem neuen Mac

1) Bundle aus Google Drive laden (Web UI oder rclone)
2) Entpacken:

```bash
mkdir -p ~/Medexamenai
tar -xf <BUNDLE>.tar -C ~/Medexamenai
```

## Validierung nach dem Umzug (auf dem neuen Mac)

1) Prüfe, ob die wichtigsten Artefakte da sind (Beispiele):

- `_OUTPUT/batch_corrected_20251216_064700.json`
- `_OUTPUT/batch_validated_20251216_064700.json`
- `_OUTPUT/evidenz_antworten_updated_20251216_142834.json`
- `AGENT_OVERVIEW.md`

2) Optional: Checksums prüfen (siehe `MIGRATION_KIT/checksums_*.txt`).

Beispiel:

```bash
./MIGRATION_KIT/verify_checksums.sh MIGRATION_KIT/checksums_<TS>.txt
```

## Weiterarbeiten auf dem neuen Mac

```bash
cd /path/to/Medexamenai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Dann sind alle Scripts wieder lauffähig. Pipeline‑Fortschritt steckt in `_OUTPUT/`.


