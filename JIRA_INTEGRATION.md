# 🎫 Jira Integration - MedExamAI

## Übersicht

Dieses Dokument beschreibt wie das MedExamAI-Projekt mit Jira integriert ist für Tracking, Automation und Zusammenarbeit.

---

## 🏗️ Projekt-Setup

### Jira-Projekt erstellen

```
Projekt-Name: MedExamAI
Projekt-Schlüssel: MED
Projekt-Typ: Kanban (oder Scrum)
```

### Board-Spalten

```
📋 Backlog → 🔄 To Do → 🚧 In Progress → ✅ Done → 🗄️ Archived
```

### Issue-Typen

| Typ | Icon | Verwendung |
|-----|------|------------|
| **Epic** | 📚 | Große Features (z.B. "Extraktion Pipeline") |
| **Story** | 📖 | User Stories (z.B. "Als User möchte ich...") |
| **Task** | ✅ | Aufgaben (z.B. "Implementiere extract_questions.py") |
| **Bug** | 🐛 | Fehler (z.B. "OCR schlägt bei PDF X fehl") |
| **Spike** | 🔬 | Forschung/Exploration |

---

## 📊 Epic-Struktur

### Epic 1: MED-001 - Extraktion Pipeline

**Ziel:** Extrahiere echte Prüfungsfragen aus Gold-Standard-Dokumenten

**Stories:**
- MED-002: Dialog-Block-Extraktion mit Kontext
- MED-003: Einzelfragen-Extraktion
- MED-004: OCR-Fallback für gescannte PDFs
- MED-005: Batch-Verarbeitung aller 40 Protokolle

**Akzeptanzkriterien:**
- [ ] Alle 40 PDFs/DOCX verarbeitet
- [ ] Mindestens 500 echte Fragen extrahiert
- [ ] Keine fiktiven Cases
- [ ] JSON-Output validiert

### Epic 2: MED-010 - Antwort-Generierung

**Ziel:** Generiere Antworten im 5-Punkte-Schema basierend auf Leitlinien

**Stories:**
- MED-011: AWMF-Leitlinien-Integration
- MED-012: 5-Punkte-Schema Implementierung
- MED-013: Dosierungs-Extraktion
- MED-014: Klassifikations-Erkennung

### Epic 3: MED-020 - Medical Validation

**Ziel:** Validiere Q&A-Paare auf medizinische Korrektheit

**Stories:**
- MED-021: Dosage Validator (mg/kg)
- MED-022: ICD-10 Validator (Geschlecht/Alter)
- MED-023: Lab Value Validator
- MED-024: Logical Consistency Validator

### Epic 4: MED-030 - Export & Integration

**Ziel:** Exportiere validierte Q&A nach Anki und andere Formate

**Stories:**
- MED-031: Anki-Export
- MED-032: PDF-Export
- MED-033: Web-Interface (optional)

---

## 🏷️ Label-Strategie

### Tier-Labels (KRITISCH!)

```
tier-1          # Alles aus Gold-Standard (höchste Priorität)
tier-2          # Bibliothek/Lehrbücher (später)
tier-unknown    # Quelle unklar (muss geklärt werden!)
```

### Komponenten-Labels

```
extraction      # Fragen-Extraktion
generation      # Antwort-Generierung
validation      # Medical Validation
export          # Export-Funktionen
documentation   # Dokumentation
testing         # Tests
infrastructure  # CI/CD, Setup
```

### Status-Labels

```
blocked         # Blockiert durch externes Hindernis
needs-review    # Code-Review erforderlich
needs-testing   # Manuelle Tests erforderlich
data-critical   # Datenverlust-Risiko (extra Vorsicht!)
```

### Prioritäts-Labels

```
p0-critical     # Kritisch - sofort (z.B. Datenverlust)
p1-high         # Hoch - diese Woche
p2-medium       # Mittel - dieser Sprint
p3-low          # Niedrig - Backlog
```

---

## 🤖 Jira Automation Rules

### Rule 1: Data-Critical Alert

**Trigger:** Label `data-critical` wird hinzugefügt

**Actions:**
1. Sende Email an Projekt-Owner
2. Kommentar: "⚠️ ACHTUNG: Datenverlust-Risiko! Vor Änderungen Backup erstellen."
3. Setze Priority auf "High"
4. Benachrichtige Slack-Channel (wenn konfiguriert)

**Jira Automation JQL:**
```
project = MED AND labels = data-critical
```

### Rule 2: Gold-Standard Protection

**Trigger:** Issue mit Label `tier-1` wird auf "In Progress" verschoben

**Actions:**
1. Kommentar: "✅ Gold-Standard Issue - strikte Tier-Trennung beachten!"
2. Checklist hinzufügen:
   - [ ] Backup erstellt?
   - [ ] `source_tier: "gold_standard"` gesetzt?
   - [ ] Keine fiktiven Cases?

### Rule 3: Auto-Close on PR Merge

**Trigger:** Pull Request mit "Closes MED-XXX" wird gemerged

**Actions:**
1. Issue auf "Done" verschieben
2. Kommentar: "✅ Automatisch geschlossen durch PR #{PR_NUMBER}"
3. Label `deployed` hinzufügen

### Rule 4: Stale Issue Warning

**Trigger:** Issue in "In Progress" > 7 Tage ohne Update

**Actions:**
1. Kommentar: "⏰ Dieses Issue ist seit 7 Tagen aktiv. Bitte Status aktualisieren."
2. Label `stale` hinzufügen
3. Assignee benachrichtigen

---

## 🔗 GitHub ↔ Jira Integration

### Commit-Format

```bash
# Format: <type>(MED-XXX): <description>

# Beispiele:
git commit -m "feat(MED-002): Add dialog block extraction with context"
git commit -m "fix(MED-021): Validate dosage ranges correctly"
git commit -m "docs(MED-005): Update extraction guide"
git commit -m "test(MED-003): Add test for single question extraction"
```

### Branch-Naming

```bash
# Format: <type>/MED-XXX-short-description

# Beispiele:
git checkout -b feature/MED-002-dialog-extraction
git checkout -b fix/MED-021-dosage-validation
git checkout -b docs/MED-005-extraction-guide
```

### Pull Request Template

```markdown
## Jira Issue
Closes [MED-XXX](https://your-jira.atlassian.net/browse/MED-XXX)

## Beschreibung
Kurze Beschreibung der Änderungen

## Änderungen
- [ ] Code-Änderungen
- [ ] Tests hinzugefügt
- [ ] Dokumentation aktualisiert

## Checklist (für data-critical Issues)
- [ ] Backup erstellt?
- [ ] Tier-Trennung beachtet?
- [ ] Keine Halluzinationen?
- [ ] Safety-Checks implementiert?

## Screenshots (falls relevant)
```

---

## 📈 Jira Dashboards

### Dashboard 1: Sprint Overview

**Widgets:**
1. **Sprint Burndown** - Verbleibende Story Points
2. **Issue Statistics** - Offene/In Progress/Done
3. **Recent Activity** - Letzte Updates
4. **Velocity Chart** - Story Points pro Sprint

### Dashboard 2: Gold-Standard Tracking

**Filter:** `project = MED AND labels = tier-1`

**Widgets:**
1. **Gold-Standard Issues** - Alle Tier-1 Issues
2. **Extraction Progress** - Wie viele PDFs verarbeitet?
3. **Quality Metrics** - Anzahl extrahierter Fragen
4. **Validation Status** - Medical Validation Fortschritt

### Dashboard 3: Data Safety

**Filter:** `project = MED AND labels = data-critical`

**Widgets:**
1. **Critical Issues** - Alle data-critical Issues
2. **Backup Status** - Letzte Backups
3. **Safety Violations** - Issues mit Problemen
4. **Recent Incidents** - Datenverlust-Events

---

## 📝 Issue Templates

### Template 1: Extraction Task

```markdown
**Titel:** Extract questions from [Document Name]

**Beschreibung:**
Extrahiere echte Prüfungsfragen aus dem Dokument.

**Dokument:**
- Dateiname: `Kenntnisprüfung Münster Protokolle 2023.docx`
- Pfad: `_GOLD_STANDARD/`
- Größe: ~4 MB

**Aufgaben:**
- [ ] Dokument mit `extract_dialog_blocks.py` verarbeiten
- [ ] Output validieren (Stichprobe)
- [ ] Anzahl extrahierter Fragen dokumentieren
- [ ] Bei Problemen: OCR-Fallback testen

**Akzeptanzkriterien:**
- [ ] Mindestens 20 Fragen extrahiert
- [ ] Keine fiktiven Cases
- [ ] JSON-Format korrekt
- [ ] `source_tier: "gold_standard"` gesetzt

**Labels:** `extraction`, `tier-1`, `p1-high`
```

### Template 2: Medical Validation Bug

```markdown
**Titel:** [Validator] Invalid result for [specific case]

**Validator:** Dosage Validator / ICD-10 / Lab Value / Logic

**Beschreibung:**
Beschreibe das Problem detailliert.

**Erwartetes Verhalten:**
Was sollte passieren?

**Tatsächliches Verhalten:**
Was passiert tatsächlich?

**Beispiel:**
```json
{
  "frage": "...",
  "validation_error": "..."
}
```

**Reproduktion:**
1. Schritt 1
2. Schritt 2
3. ...

**Labels:** `bug`, `validation`, `p1-high`
```

---

## 🔔 Benachrichtigungen

### Slack-Integration (optional)

**Channel:** `#medexamai-dev`

**Benachrichtigungen:**
- Neues Issue mit Label `data-critical`
- Issue in "Done" verschoben
- Pull Request erstellt/gemerged
- GitHub Actions Fehlschlag

**Webhook-URL:** (in Jira-Automation konfigurieren)

### Email-Benachrichtigungen

**Wichtige Events:**
- Issue assigned to you
- Issue blocked
- Comment mentions you
- Label `data-critical` added

---

## 📋 Sprint Planning

### Sprint-Länge

**2 Wochen** (empfohlen für agile Entwicklung)

### Sprint-Ziel Beispiele

**Sprint 1 (02-15 Dez):**
> "Extraktion von 40 Gold-Standard-Dokumenten abschließen"

**Sprint 2 (16-29 Dez):**
> "Antwort-Generierung im 5-Punkte-Schema implementieren"

**Sprint 3 (30 Dez - 12 Jan):**
> "Medical Validation Layer (4 Prüfer) fertigstellen"

---

## 📊 KPIs & Metrics

### Extraction Metrics

```jql
# Extrahierte Fragen (manuell tracken in Custom Field)
project = MED AND labels = extraction

# Erfolgreich verarbeitete Dokumente
project = MED AND labels = extraction AND status = Done
```

### Quality Metrics

```jql
# Validation Pass Rate
project = MED AND labels = validation AND status = Done

# Critical Issues (Datenverlust etc.)
project = MED AND labels = data-critical AND created >= -30d
```

### Velocity Tracking

```
Story Points pro Sprint (Fibonacci: 1, 2, 3, 5, 8, 13)
```

---

## 🛠️ Jira Admin Setup

### Custom Fields

1. **Extracted Questions Count** (Number)
   - Wie viele Fragen aus diesem Dokument extrahiert?

2. **Source Document** (Text)
   - Welches Gold-Standard-Dokument?

3. **Validation Pass Rate** (Percentage)
   - Wie viele Q&A-Paare bestanden Validation?

4. **Last Backup** (Date)
   - Wann wurde zuletzt ein Backup erstellt?

### Workflows

```
📋 Backlog
    ↓
🔄 To Do (Sprint geplant)
    ↓
🚧 In Progress (Aktiv)
    ↓
👀 Review (Code-Review)
    ↓
✅ Done (Fertig)
    ↓
🗄️ Archived (Nach 30 Tagen)
```

---

## 📞 Support & Kontakt

**Jira-Administrator:** [Dein Name]  
**Projekt-Owner:** [Dein Name]  
**Jira-URL:** https://your-jira.atlassian.net/browse/MED

---

## 🔄 Changelog

| Datum | Änderung |
|-------|----------|
| 2024-12-01 | Initial Setup für MedExamAI |
| TBD | GitHub Actions Integration |
| TBD | Slack Notifications Setup |

---

**Nächste Schritte:**

1. [ ] Jira-Projekt erstellen
2. [ ] Board konfigurieren
3. [ ] Automation Rules aktivieren
4. [ ] GitHub-Integration einrichten
5. [ ] Erste Issues anlegen (Epics)
