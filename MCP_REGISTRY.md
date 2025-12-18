# 🔧 MCP Integration Registry - MedExamAI Projekt

**⚠️ PFLICHTLEKTÜRE FÜR ALLE AGENTEN ⚠️**

**Erstellt:** 2024-12-18  
**Status:** Aktiv  
**Letzte Aktualisierung:** 2024-12-18 14:00 UTC

---

## 📋 Übersicht

Dieses Dokument beschreibt **alle** verfügbaren Model Context Protocol (MCP) Server und externe Integrationen für das MedExamAI-Projekt. **Jeder Agent muss diese Datei lesen, bevor er Aufgaben ausführt.**

---

## 🚨 Pflicht für alle Agenten

✅ **VOR jeder Aufgabe:**
1. Diese Datei (`MCP_REGISTRY.md`) lesen
2. Verfügbare MCP-Server prüfen
3. API-Keys validieren (siehe [API Key Status Checker](#api-key-status-checker))
4. Budget-Limits prüfen (`config.yaml` → `budget.remaining`)
5. **Platzhalter-Policy:** Wenn Platzhalter unvermeidbar sind, müssen sie klar als Platzhalter markiert werden. Bevorzugt: direkt echte Werte einsetzen und Funktion testen. Keine stillen Dummy-Werte in Code, Config oder Commits.

❌ **NIEMALS:**
- Secrets loggen oder committen
- `_OUTPUT/evidenz_antworten.json` überschreiben (READ-ONLY!)
- API-Calls ohne Budget-Check ausführen
- MCP-Server verwenden ohne vorherige Verfügbarkeits-Prüfung

---

## 🔌 Aktive MCP-Server (GitHub Copilot)

**Konfigurationsdatei:** `~/.config/github-copilot/intellij/mcp.json`

### 1. 📁 Filesystem Server
**Status:** ✅ Aktiv  
**Zweck:** Direkter Dateizugriff auf das MedExamAI-Projekt  
**Command:** `npx -y @modelcontextprotocol/server-filesystem`  
**Args:** `/Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617`

**Verwendung:**
```
Liste alle JSON-Dateien in _OUTPUT mit "checkpoint" im Namen
Lies die ersten 50 Zeilen von evidenz_antworten.json
Erstelle eine neue Datei _OUTPUT/report_TIMESTAMP.md
```

**Wichtige Regeln:**
- ✅ Lesen: Alle Verzeichnisse
- ✅ Schreiben: `_OUTPUT/` (nur neue Dateien mit Timestamp!)
- ❌ NIEMALS überschreiben: `_OUTPUT/evidenz_antworten.json`
- ❌ Nicht anfassen: `_GOLD_STANDARD/`, `_BIBLIOTHEK/Leitlinien/`

---

### 2. 🧠 Memory Server
**Status:** ✅ Aktiv  
**Zweck:** Persistenter Kontext über Chat-Sessions hinweg  
**Command:** `npx -y @modelcontextprotocol/server-memory`

**Verwendung:**
```
Merke dir: Aktuelles Budget ist $170.99, 67 Problem-Items verbleibend
Was hast du über den letzten Batch-Run gespeichert?
Speichere Projektstatus: 339 Fragen bearbeitet, nächster Schritt ist Perplexity Fact-Check
```

**Best Practices:**
- Speichere wichtige Projekt-Metriken (Budget, offene Tasks, Fehler)
- Nutze für Long-Running-Tasks (Batch-Processing, RAG-Indexierung)
- Persistiere Checkpoint-Informationen

---

### 3. 🔍 Fetch Server
**Status:** ✅ Aktiv  
**Zweck:** HTTP-Requests für Leitlinien-Downloads und Web-Validierung  
**Command:** `npx -y @modelcontextprotocol/server-fetch`

**Verwendung:**
```
Hole die AWMF-Leitlinie von https://register.awmf.org/assets/guidelines/...
Prüfe ob die RKI-Seite erreichbar ist
Lade die ESC Guidelines für Herzinsuffizienz
```

**Wichtige URLs:**
- AWMF: `https://register.awmf.org/`
- RKI: `https://www.rki.de/`
- DocCheck: `https://flexikon.doccheck.com/`
- ESC: `https://www.escardio.org/Guidelines`

---

### 4. 📝 Git Server
**Status:** ✅ Aktiv  
**Zweck:** Versionskontrolle aus dem Chat  
**Command:** `npx -y @modelcontextprotocol/server-git`  
**Args:** `--repository /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617`

**Verwendung:**
```
Zeige die letzten 10 Commits
Was wurde heute geändert?
Erstelle einen Commit mit Nachricht "MCP Setup abgeschlossen"
```

**Git-Konfiguration:**
- User: `MedExamAI Agent`
- Email: `agent@medexam.ai` ⚠️ **PLATZHALTER** - Bitte durch echte E-Mail ersetzen!

---

## 🧪 Scientific Skills (Claude Code Integration)

**Status:** ⚠️ Partiell verfügbar (Dependencies prüfen!)  
**Modul:** `core/scientific_enrichment.py`  
**Dokumentation:** `_DOCS/SCIENTIFIC_SKILLS_WORKFLOW.md`

### Verfügbare Skills:

| Skill | Library | Zweck | Status |
|-------|---------|-------|--------|
| **PubMed Search** | `biopython` | Medizinische Literatur-Suche | ✅ Installiert |
| **ChEMBL Lookup** | `bioservices` | Pharmazeutische Datenbank | ✅ Installiert |
| **DataCommons** | `datacommons-pandas` | Epidemiologie-Statistiken | ✅ Installiert |
| **Molekül-Analyse** | `datamol` | Chemische Strukturen | ⚠️ Optional |

### Verwendung:
```python
from core.scientific_enrichment import ScientificEnrichmentPipeline

pipeline = ScientificEnrichmentPipeline()
result = pipeline.enrich_medical_question(
    question="Was ist die Standarddosis von Amoxicillin bei Pneumonie?",
    context="Ambulant erworbene Pneumonie, Erwachsener Patient"
)
```

### Wichtige Keywords für Auto-Enrichment:
- **Pharmakologie:** mg, dosis, antibiotik, betablocker, ace-hemmer
- **Epidemiologie:** prävalenz, inzidenz, mortalität, risiko

---

## 🔑 API-Keys & Provider

**Konfigurationsdatei:** `.env` (NICHT in Git committen!)  
**Beispiel:** `.env.example`

### Verfügbare Provider:

| Provider | Key Name | Budget (USD) | Status |
|----------|----------|--------------|--------|
| **Requesty** | `REQUESTY_API_KEY` | $69.95 | ⚠️ Prüfen |
| **Anthropic** | `ANTHROPIC_API_KEY` | $37.62 | ⚠️ Prüfen |
| **AWS Bedrock** | `AWS_BEDROCK_API_KEY` | $24.00 | ⚠️ Prüfen |
| **Comet API** | `COMET_API_KEY` | $8.65 | ⚠️ Prüfen |
| **Perplexity** | `PERPLEXITY_API_KEY_1` | $15.00 | ⚠️ Prüfen |
| **OpenRouter** | `OPENROUTER_API_KEY` | $5.78 | ⚠️ Prüfen |
| **OpenAI** | `OPENAI_API_KEY` | $9.99 | ⚠️ Prüfen |
| **Google Workspace** | `GOOGLE_APPLICATION_CREDENTIALS` | €217.75 | ⚠️ Prüfen |

**Gesamtbudget:** $170.99 + €217.75

### Budget-Warnschwelle:
- ⚠️ Warnung bei < $20.00 pro Provider
- 🛑 Stop bei < $5.00 pro Provider

---

## 🔍 API Key Status Checker

**Neues Tool:** `scripts/check_api_keys.py` (wird erstellt in nächstem Schritt)

### Verwendung:
```bash
# Alle Keys prüfen
python3 scripts/check_api_keys.py --all

# Einzelnen Provider prüfen
python3 scripts/check_api_keys.py --provider requesty

# Live-Budget abrufen
python3 scripts/check_api_keys.py --check-balance
```

### Output:
```
✅ REQUESTY_API_KEY: Valid, Balance: $69.95
✅ ANTHROPIC_API_KEY: Valid, Balance: $37.62
❌ OPENAI_API_KEY: Invalid or expired
⚠️ PERPLEXITY_API_KEY_1: Valid, Balance: $15.00 (Low balance warning!)
```

---

## 🌐 Externe Integrationen (Historisch)

### 1. Google Drive Integration
**Status:** 🔴 Nicht aktiv (nur rclone für Migration)  
**Dokumentation:** `MIGRATION_KIT/README.md`  
**Verwendung:** Nur für Backup/Migration, nicht für Runtime

### 2. Atlassian/Jira Integration
**Status:** 🔴 Nicht verfügbar  
**Hinweis:** Es gibt KEINEN offiziellen MCP-Server für Jira/Atlassian  
**Alternative:** Manuelle Task-Verwaltung in `TODO.md`  
**Historisch dokumentiert in:** `_ARCHIVE/quarantine_external/claude_exports_Medexamenai/`

### 3. GitHub Integration
**Status:** ✅ Via Git MCP Server (siehe oben)  
**Repository:** Noch nicht verbunden (lokales Repo only)

---

## 📊 Projekt-spezifische Constraints

### Read-Only Dateien:
```
❌ _OUTPUT/evidenz_antworten.json
❌ _GOLD_STANDARD/**/*
❌ _BIBLIOTHEK/Leitlinien/**/*
```

### Schreibbare Bereiche:
```
✅ _OUTPUT/tmp_*
✅ _OUTPUT/*_TIMESTAMP.json
✅ _OUTPUT/logs/
✅ _PROCESSING/
```

### Naming Convention für neue Dateien:
```
_OUTPUT/[prefix]_[descriptor]_YYYYMMDD_HHMMSS.[ext]

Beispiele:
- _OUTPUT/tmp_rovodev_triage_summary_20251218_140000.md
- _OUTPUT/batch_corrected_20251218_140000.json
- _OUTPUT/validation_report_20251218_140000.json
```

---

## 🔄 Update-Prozess

**Diese Datei aktualisieren wenn:**
1. Neue MCP-Server hinzugefügt werden
2. API-Keys geändert/hinzugefügt werden
3. Budget-Limits aktualisiert werden
4. Neue externe Integrationen verfügbar sind

**Update-Befehl:**
```bash
# Git Commit für Registry-Updates
git add MCP_REGISTRY.md
git commit -m "Update MCP Registry: [Beschreibung der Änderung]"
```

---

## 🆘 Troubleshooting

### MCP-Server startet nicht:
```bash
# NPX Cache leeren
npm cache clean --force

# Server manuell testen
npx -y @modelcontextprotocol/server-filesystem .
```

### API-Key ungültig:
```bash
# Keys prüfen
python3 scripts/check_api_keys.py --provider [name]

# .env neu laden
source .env  # oder IDE neu starten
```

### Budget überschritten:
1. `config.yaml` → `budget.remaining` aktualisieren
2. Alternative Provider wählen (siehe `core/unified_api_client.py`)
3. Lokale Modelle verwenden (sentence-transformers für Embeddings)

---

## 📚 Verwandte Dokumentation

- **MCP Setup Guide:** `MCP_SETUP_GUIDE.md`
- **Unified API Client:** `core/unified_api_client.py`
- **Budget Monitoring:** `core/token_budget_monitor.py`
- **Scientific Enrichment:** `core/scientific_enrichment.py`
- **RAG System:** `core/rag_system.py`
- **Project Status:** `PROJECT_STATUS.md`

---

**🔒 Sicherheit:** Niemals API-Keys in Logs, Commits oder Outputs!  
**📈 Monitoring:** Budget täglich prüfen via `check_api_keys.py`  
**🤝 Collaboration:** Alle Agenten müssen diese Registry kennen!

---

*Letzte Änderung: 2024-12-18 14:00 UTC*  
*Maintainer: GitHub Copilot Agent*
