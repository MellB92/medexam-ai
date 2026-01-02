# Git Repository Setup für Multi-Agenten Zusammenarbeit

Dieses Repository wurde für die Zusammenarbeit mehrerer Cursor-Agenten konfiguriert.

## Konfiguration

### Git-Einstellungen
- **Merge-Tool**: vimdiff (kann geändert werden)
- **Conflict-Style**: diff3 (zeigt gemeinsamen Vorfahren)
- **Pull-Strategie**: merge (kein rebase)
- **Line-Endings**: Auto-Detection mit LF-Normalisierung

### Wichtige Dateien
- `.gitignore`: Definiert, welche Dateien nicht versioniert werden sollen
- `.gitattributes`: Definiert, wie verschiedene Dateitypen behandelt werden

## Verwendung mit mehreren Agenten

### Best Practices für Multi-Agenten-Workflow

1. **Bevor Sie arbeiten:**
   ```bash
   git pull origin main
   ```

2. **Während der Arbeit:**
   - Häufig committen (kleine, logische Commits)
   - Klare Commit-Messages verwenden
   - Konflikte früh erkennen und lösen

3. **Nach der Arbeit:**
   ```bash
   git add .
   git commit -m "Beschreibung der Änderungen"
   git push origin main
   ```

### Konflikte lösen

Wenn mehrere Agenten gleichzeitig an denselben Dateien arbeiten:

1. **Pull vor Push:**
   ```bash
   git pull origin main
   ```

2. **Konflikte identifizieren:**
   - Git zeigt betroffene Dateien an
   - Konflikte sind mit `<<<<<<<`, `=======`, `>>>>>>>` markiert

3. **Konflikte manuell lösen:**
   - Dateien öffnen und Konflikte auflösen
   - Alle Markierungen entfernen
   - Dateien speichern

4. **Nach Lösung:**
   ```bash
   git add <gelöste-dateien>
   git commit -m "Konflikte gelöst"
   git push origin main
   ```

### Dateien hinzufügen

Um spezifische Dateien zum Repository hinzuzufügen:

```bash
# Einzelne Datei
git add pfad/zur/datei.py

# Alle Python-Dateien
git add "**/*.py"

# Bestimmtes Verzeichnis
git add Medexamenai_migration_full_20251217_204617/core/

# Alle Änderungen (Vorsicht: prüfen Sie .gitignore)
git add .
```

### Status prüfen

```bash
# Kurze Übersicht
git status --short

# Detaillierte Übersicht
git status

# Was würde hinzugefügt werden?
git status --ignored
```

## Ausgeschlossene Dateien

Folgende Dateien/Verzeichnisse werden **nicht** versioniert:
- `__pycache__/` und Python-Cache-Dateien
- Virtual Environments (`venv/`, `.venv/`)
- IDE-Konfigurationen (`.vscode/`, `.idea/`)
- Temporäre Dateien (`*.tmp`, `*.log`, `*.bak`)
- Große Datenverzeichnisse (`_OUTPUT/`, `_FORENSIK/`, `_GOLD_STANDARD/`)
- PDF-Dateien in `_FACT_CHECK_SOURCES/`
- Archive (`*.tar`, `*.zip`)

## Nächste Schritte

1. **Git-Benutzer konfigurieren** (falls noch nicht geschehen):
   ```bash
   git config --global user.name "Ihr Name"
   git config --global user.email "ihre.email@example.com"
   ```

2. **Remote-Repository hinzufügen** (falls vorhanden):
   ```bash
   git remote add origin <repository-url>
   git branch -M main
   git push -u origin main
   ```

3. **Wichtige Projektdateien hinzufügen:**
   ```bash
   git add Medexamenai_migration_full_20251217_204617/*.md
   git add Medexamenai_migration_full_20251217_204617/*.py
   git add Medexamenai_migration_full_20251217_204617/*.txt
   git add Medexamenai_migration_full_20251217_204617/*.yaml
   git add Medexamenai_migration_full_20251217_204617/*.toml
   git commit -m "Projektdateien hinzugefügt"
   ```

## Hinweise

- **Große Dateien**: Das Repository enthält viele große Dateien. Überlegen Sie, ob Sie Git LFS verwenden möchten für:
  - PDF-Dateien
  - Große JSON-Dateien
  - Archive

- **Branching**: Für komplexe Features können Sie Branches verwenden:
  ```bash
  git checkout -b feature/neue-funktion
  # ... arbeiten ...
  git checkout main
  git merge feature/neue-funktion
  ```







