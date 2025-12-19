# ✅ TODO List - MedExamAI

> Aktualisierung: 2025-12-19 (Batch-Review Run 20251219 abgeschlossen)

### ✅ ERLEDIGT (19.12.2025)
- [x] 60 Problem-Items korrigiert (GPT-5-mini + Claude Opus 4.5)
- [x] Perplexity-Validierung durchgeführt (ok=25, maybe=18, problem=17)
- [x] 43 Antworten in evidenz_antworten.json gemerged
- [x] Coverage-Check bestätigt: 2.527/2.527 = 100%
- [x] Dokumentation aktualisiert (PROJECT_STATUS.md, TODO.md)
- [x] 7 manuelle Items dokumentiert mit AWMF-Korrekturen

### 🔴 NOCH OFFEN
1) **17 Problem-Items** aus Batch-Review (erfordern erneute Korrektur oder manuelle Prüfung)
2) **7 manuelle Items** mit detaillierten Korrekturvorschlägen bereit
   - Siehe `_OUTPUT/MANUAL_ITEMS_CORRECTIONS_20251219.md`
3) Optional: Zweite Batch-Runde für verbleibende 17 Items
4) Optional: Lern-Exports aktualisieren (`export_learning_materials.py --daily-plan`)


**Letzte Aktualisierung:** 2024-12-01
**Priorität:** 🔴 Hoch | 🟡 Mittel | 🟢 Niedrig

---

## 🔥 Diese Woche (02-08 Dez 2024)

### Extraktion testen

- [ ] 🔴 Testlauf mit 1 Sample-PDF (DOCX)
  ```bash
  python3 scripts/extract_dialog_blocks.py
  ```
- [ ] 🔴 Testlauf mit 1 Sample-PDF (gescannt)
- [ ] 🔴 Output validieren (ist JSON korrekt?)
- [ ] 🔴 Stichprobe: Sind Fragen echt oder halluziniert?
- [ ] 🟡 Bugfixes basierend auf Tests

### GitHub Setup

- [ ] 🔴 Repository erstellen
  - [ ] Push initial commit
  - [ ] README in GitHub anzeigen
  - [ ] .gitignore erstellen
- [ ] 🟡 GitHub Actions aktivieren
  - [ ] daily-backup.yml testen
  - [ ] ci.yml testen

### Dokumentation

- [x] ✅ README.md
- [x] ✅ DEVELOPMENT.md
- [x] ✅ MIGRATION_GUIDE.md
- [x] ✅ JIRA_INTEGRATION.md
- [x] ✅ PROJECT_STATUS.md
- [ ] 🟡 CHANGELOG.md erstellen

---

## 📅 Nächste Woche (09-15 Dez 2024)

### Vollständige Extraktion

- [ ] 🔴 Alle 40 PDFs/DOCX verarbeiten
- [ ] 🔴 Statistik generieren:
  - Anzahl Fragen total
  - Anzahl Dialog-Blöcke
  - Anzahl Fragen pro Dokument
  - Fehler/Probleme
- [ ] 🔴 Qualitätskontrolle (10% Stichprobe)
- [ ] 🟡 Problematische Dokumente identifizieren

### Antwort-Generierung starten

- [ ] 🔴 `generate_answers.py` - Grundgerüst erstellen
- [ ] 🟡 5-Punkte-Schema Template implementieren
- [ ] 🟡 AWMF-Leitlinien API recherchieren

---

## 📋 Backlog (Priorisiert)

### Phase 2: Antwort-Generierung (bis 31 Dez)

#### generate_answers.py

- [ ] 🔴 Basis-Implementierung
  - [ ] JSON Input laden
  - [ ] 5-Punkte-Schema Struktur
  - [ ] JSON Output schreiben
- [ ] 🔴 Leitlinien-Integration
  - [ ] AWMF Leitlinien abrufen
  - [ ] Relevante Leitlinie finden (per Keyword)
  - [ ] Text extrahieren
- [ ] 🟡 Dosierungen extrahieren
  - [ ] Pattern-Matching für mg/kg
  - [ ] Standard-Dosierungen DB aufbauen
  - [ ] Leitlinien nach Dosierungen durchsuchen
- [ ] 🟡 Klassifikationen zuordnen
  - [ ] Klassifikations-DB erweitern
  - [ ] Pattern-Matching (Garden, Pauwels, NYHA, etc.)
- [ ] 🟡 Rechtliche Aspekte
  - [ ] §630 BGB Template
  - [ ] Kontext-spezifische Anpassungen

#### Testing

- [ ] 🟡 Unit Tests für generate_answers.py
- [ ] 🟡 Test mit 10 Beispiel-Fragen
- [ ] 🟡 Manuelle Qualitätskontrolle

### Phase 3: Medical Validation (bis 15 Jan)

#### validate_medical.py

- [ ] 🔴 Dosage Validator
  - [ ] Bekannte Medikamente DB
  - [ ] Min/Max Dosierung-Ranges
  - [ ] mg/kg Validierung
  - [ ] Überdosierung erkennen
- [ ] 🔴 ICD-10 Validator
  - [ ] Geschlechts-spezifische Diagnosen
  - [ ] Alters-spezifische Diagnosen
  - [ ] Inkonsistenzen erkennen
- [ ] 🟡 Lab Value Validator
  - [ ] Referenzbereiche DB
  - [ ] Kritische Werte erkennen
  - [ ] Widersprüche zwischen Werten
- [ ] 🟡 Logic Consistency Validator
  - [ ] Kontraindikationen DB
  - [ ] Schwangerschaft + Medikament
  - [ ] Diagnostik → Therapie Konsistenz

#### Testing

- [ ] 🟡 Unit Tests für alle 4 Validatoren
- [ ] 🟡 Integration Test (gesamte Pipeline)
- [ ] 🟡 Quarantäne-Liste Output testen

### Phase 4: Export (bis 31 Jan)

#### export.py

- [ ] 🔴 Anki-Export
  - [ ] Anki .apkg Format recherchieren
  - [ ] Karten-Template erstellen
  - [ ] Front: Frage + Patient
  - [ ] Back: 5-Punkte-Antwort
  - [ ] Tags: Kategorie, Schwierigkeit
- [ ] 🟡 PDF-Export
  - [ ] PDF-Layout definieren
  - [ ] Schriftart, Größe, Formatierung
  - [ ] Table of Contents
- [ ] 🟢 Web-Interface (optional)
  - [ ] Einfacher HTML-Export
  - [ ] Statische Website generieren

---

## 🧪 Testing TODOs

### Unit Tests erstellen

- [ ] 🟡 tests/test_extract_questions.py
  - [ ] Test: Einfache Frage wird extrahiert
  - [ ] Test: Frage ohne "?" wird ignoriert
  - [ ] Test: `source_tier` ist korrekt gesetzt
  - [ ] Test: Keine Halluzinationen
- [ ] 🟡 tests/test_extract_dialog_blocks.py
  - [ ] Test: Dialog-Block mit Kontext
  - [ ] Test: F:/A: Pattern wird erkannt
  - [ ] Test: Kontext-Zeilen werden korrekt extrahiert
- [ ] 🟡 tests/test_generate_answers.py
  - [ ] Test: 5-Punkte-Schema vollständig
  - [ ] Test: Dosierungen extrahiert
  - [ ] Test: Klassifikationen zugeordnet
- [ ] 🟡 tests/test_validate_medical.py
  - [ ] Test: Überdosierung erkannt
  - [ ] Test: ICD-10 Inkonsistenz erkannt
  - [ ] Test: Lab Value Out-of-Range

### Integration Tests

- [ ] 🟢 End-to-End Test
  - [ ] PDF → Extraktion → Generierung → Validation → Export
  - [ ] Mit Sample-Daten
  - [ ] Timing/Performance messen

---

## 📚 Dokumentation TODOs

### Code-Dokumentation

- [ ] 🟡 Docstrings für alle Funktionen
- [ ] 🟡 Type Hints überall
- [ ] 🟢 Inline-Kommentare für komplexe Logik

### User-Dokumentation

- [ ] 🟡 QUICKSTART.md - 5-Minuten-Guide
- [ ] 🟢 FAQ.md - Häufige Fragen
- [ ] 🟢 TROUBLESHOOTING.md - Problemlösungen

### API-Dokumentation

- [ ] 🟢 Wenn Web-API gebaut wird
- [ ] 🟢 OpenAPI/Swagger Spec

---

## 🔧 Infrastructure TODOs

### GitHub

- [ ] 🔴 Repository erstellen
- [ ] 🔴 .gitignore erstellen
  ```
  .venv/
  __pycache__/
  *.pyc
  .pytest_cache/
  .DS_Store
  _OUTPUT/*.json
  backups/
  ```
- [ ] 🔴 LICENSE hinzufügen (MIT)
- [ ] 🟡 Branch protection rules
- [ ] 🟡 PR template
- [ ] 🟡 Issue templates

### CI/CD

- [x] ✅ .github/workflows/daily-backup.yml
- [x] ✅ .github/workflows/ci.yml
- [ ] 🟡 Test CI/CD Pipeline
- [ ] 🟡 Badge in README (Build Status)

### Jira

- [ ] 🔴 Projekt erstellen (MED)
- [ ] 🔴 Board konfigurieren
- [ ] 🔴 Epics anlegen
  - [ ] MED-001: Extraktion Pipeline
  - [ ] MED-010: Antwort-Generierung
  - [ ] MED-020: Medical Validation
  - [ ] MED-030: Export & Integration
- [ ] 🟡 Automation Rules aktivieren
- [ ] 🟡 GitHub Integration einrichten

---

## 🎨 Optional / Nice-to-Have

### Features

- [ ] 🟢 Web-Interface für manuelle Qualitätskontrolle
- [ ] 🟢 Dashboard mit Statistiken
- [ ] 🟢 Lernfortschritt-Tracking
- [ ] 🟢 Spaced Repetition Integration

### Tooling

- [ ] 🟢 Pre-commit hooks
  - [ ] Black (Code Formatting)
  - [ ] Pylint (Linting)
  - [ ] pytest (Run tests)
- [ ] 🟢 Docker Container
- [ ] 🟢 VS Code Extensions Empfehlungen

### Automatisierung

- [ ] 🟢 Automatische Leitlinien-Updates (monatlich)
- [ ] 🟢 Automatische Gold-Standard Checks (neue Protokolle?)
- [ ] 🟢 Slack Notifications bei CI/CD Failure

---

## 🐛 Known Issues / Bugs

### Aktuell

_Noch keine bekannten Bugs (Projekt ist neu)_

### Zu erwartende Probleme

- ⚠️ OCR bei gescannten PDFs könnte fehlschlagen
- ⚠️ Nicht alle PDFs haben einheitliche Struktur
- ⚠️ Manche Protokolle sind handschriftlich (Notizen)
- ⚠️ Dosierungen können in verschiedenen Formaten vorliegen

---

## 📊 Metriken zu tracken

### Extraktion

- [ ] Anzahl verarbeiteter Dokumente
- [ ] Anzahl extrahierter Fragen
- [ ] Anzahl Dialog-Blöcke
- [ ] Fehlerrate (%)
- [ ] Verarbeitungszeit pro Dokument

### Qualität

- [ ] Tier-1 Anteil (sollte 100% sein)
- [ ] Halluzinations-Rate (sollte 0% sein)
- [ ] Validation Pass Rate
- [ ] Manuelle Review Pass Rate

### Performance

- [ ] Verarbeitungszeit (Sekunden/Dokument)
- [ ] Memory Usage
- [ ] JSON Output Größe

---

## 🎓 Learning / Research TODOs

### Medizinisch

- [ ] 🟡 Alle Klassifikationen auflisten
  - [ ] Garden (Schenkelhalsfraktur)
  - [ ] Pauwels (Schenkelhalsfraktur)
  - [ ] Weber (Sprunggelenkfraktur)
  - [ ] NYHA (Herzinsuffizienz)
  - [ ] CHA2DS2-VASc (VHF Schlaganfallrisiko)
  - [ ] ... (weitere)
- [ ] 🟡 Standard-Dosierungen recherchieren (Top 50 Medikamente)
- [ ] 🟡 §630 BGB detailliert studieren

### Technisch

- [ ] 🟢 AWMF API Dokumentation lesen
- [ ] 🟢 Anki .apkg Format verstehen
- [ ] 🟢 OCR Best Practices

---

## 🔄 Regelmäßige Tasks

### Täglich

- [ ] ⏰ Commit & Push (Ende des Arbeitstages)
- [ ] ⏰ Backup-Status prüfen (GitHub Actions)

### Wöchentlich

- [ ] ⏰ Sprint Review (Sonntags)
- [ ] ⏰ PROJECT_STATUS.md aktualisieren
- [ ] ⏰ TODO.md aktualisieren
- [ ] ⏰ Jira Board aufräumen

### Monatlich

- [ ] ⏰ CHANGELOG.md aktualisieren
- [ ] ⏰ Dependencies updaten (`pip list --outdated`)
- [ ] ⏰ Backup-Integrität prüfen

---

## ✅ Completed (Archiv)

### Setup Phase (28 Nov - 01 Dez 2024)

- [x] ✅ Comet API analysiert
- [x] ✅ Root Cause identifiziert (LLM-Halluzinationen)
- [x] ✅ Neuer Ordner erstellt (~/Documents/Medexamenai)
- [x] ✅ Gold-Standard isoliert (40 Dateien)
- [x] ✅ Ordnerstruktur aufgebaut
- [x] ✅ config.yaml erstellt
- [x] ✅ extract_questions.py erstellt
- [x] ✅ extract_dialog_blocks.py erstellt
- [x] ✅ README.md geschrieben
- [x] ✅ DEVELOPMENT.md geschrieben
- [x] ✅ MIGRATION_GUIDE.md geschrieben
- [x] ✅ JIRA_INTEGRATION.md geschrieben
- [x] ✅ PROJECT_STATUS.md geschrieben
- [x] ✅ GitHub Workflows erstellt
- [x] ✅ requirements.txt erstellt

---

## 🎯 Priorities Summary

### P0 - Kritisch (Diese Woche)

1. Testlauf mit Sample-PDFs
2. GitHub Repository erstellen
3. Bugfixes

### P1 - Hoch (Nächste 2 Wochen)

1. Vollständige Extraktion (40 PDFs)
2. `generate_answers.py` implementieren
3. Qualitätskontrolle

### P2 - Mittel (Bis Ende Dezember)

1. Medical Validation Layer
2. Tests schreiben
3. Anki-Export

### P3 - Niedrig (Nice-to-Have)

1. Web-Interface
2. Performance-Optimierungen
3. Zusätzliche Exports

---

**📌 Nächste Aktion:** Testlauf mit 1 Sample-PDF durchführen!

```bash
cd ~/Documents/Medexamenai
python3 scripts/extract_dialog_blocks.py
# Dann Output prüfen: _EXTRACTED_FRAGEN/frage_bloecke.json
```
