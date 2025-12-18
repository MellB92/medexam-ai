# MCP Integration für MedExamAI

## Was ist MCP?

**Model Context Protocol (MCP)** ist ein offener Standard, der es KI-Assistenten ermöglicht, 
mit externen Tools und Datenquellen zu kommunizieren. In PyCharm können Sie MCP-Server 
mit GitHub Copilot Chat verwenden, um erweiterte Funktionalitäten zu nutzen.

---

## Installation & Setup

### Voraussetzungen

- ✅ Node.js (installiert: v25.2.1)
- ✅ npx (installiert: v11.6.2)
- PyCharm mit GitHub Copilot Plugin

### Schritt 1: MCP-Server in PyCharm konfigurieren

1. Öffne **PyCharm** → **Settings/Preferences** (⌘ + ,)
2. Navigiere zu: **Tools** → **GitHub Copilot** → **MCP Servers**
3. Klicke auf **+** um einen neuen Server hinzuzufügen
4. Konfiguriere jeden Server einzeln (siehe unten)

### Schritt 2: Server einzeln hinzufügen

#### 🗂️ Filesystem Server
Ermöglicht direkten Dateizugriff auf das Projekt.

```
Name: filesystem
Command: npx
Arguments: -y @modelcontextprotocol/server-filesystem /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
```

#### 🔍 Fetch Server
Ermöglicht HTTP-Requests (z.B. für Leitlinien-Downloads).

```
Name: fetch
Command: npx
Arguments: -y @modelcontextprotocol/server-fetch
```

#### 🧠 Memory Server
Persistenter Kontext über Chat-Sessions hinweg.

```
Name: memory
Command: npx
Arguments: -y @modelcontextprotocol/server-memory
```

#### 📝 Git Server
Git-Operationen direkt aus dem Chat.

```
Name: git
Command: npx
Arguments: -y @modelcontextprotocol/server-git --repository /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617
```

#### 🌐 Brave Search Server (Optional - API Key erforderlich)
Web-Suche für medizinische Faktenprüfung.

```
Name: brave-search
Command: npx
Arguments: -y @modelcontextprotocol/server-brave-search
Environment: BRAVE_API_KEY=<dein-api-key>
```
API Key erhalten: https://brave.com/search/api/

#### 🗃️ SQLite Server
Datenbankzugriff für strukturierte Daten.

```
Name: sqlite
Command: npx
Arguments: -y @modelcontextprotocol/server-sqlite --db-path /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617/_OUTPUT/medexam.db
```

#### 🌐 Puppeteer Server
Browser-Automatisierung für Leitlinien-Scraping.

```
Name: puppeteer
Command: npx
Arguments: -y @modelcontextprotocol/server-puppeteer
```

#### 🧩 Sequential Thinking Server
Mehrstufiges Reasoning für komplexe medizinische Fragen.

```
Name: sequential-thinking
Command: npx
Arguments: -y @modelcontextprotocol/server-sequential-thinking
```

---

## Verwendung im GitHub Copilot Chat

### Beispiel-Prompts für MedExamAI:

#### Mit Filesystem MCP:
```
@workspace Lies die Datei _OUTPUT/evidenz_antworten.json und zeige mir 
die letzten 5 Einträge mit niedrigem Score.
```

#### Mit Fetch MCP:
```
Lade die AWMF-Leitlinie für Herzinsuffizienz von 
https://register.awmf.org/assets/guidelines/nvl-006l_S3_Chronische_Herzinsuffizienz_2023-12.pdf
```

#### Mit Memory MCP:
```
Merke dir: Aktuelles Projekt ist MedExamAI mit 339 verbleibenden Fragen. 
Budget: $170.99. Priorität: Perplexity Fact-Checking abschließen.
```

#### Mit Git MCP:
```
Zeige mir die letzten 5 Commits und welche Dateien geändert wurden.
```

#### Mit SQLite MCP:
```
Erstelle eine Tabelle für alle Fragen mit Score < 3 aus evidenz_antworten.json
```

#### Mit Brave Search MCP:
```
Suche nach "STIKO Impfempfehlung Influenza 2024" auf AWMF und RKI
```

#### Mit Puppeteer MCP:
```
Öffne die ESC Guidelines Seite und extrahiere alle PDF-Links für Kardiologie
```

---

## Testen der MCP-Server

### Terminal-Test (vor PyCharm-Integration):

```bash
# Filesystem Server testen
npx -y @modelcontextprotocol/server-filesystem /Users/entropie/Documents/Medexamenai_Migration/Medexamenai_migration_full_20251217_204617

# Fetch Server testen  
npx -y @modelcontextprotocol/server-fetch

# Memory Server testen
npx -y @modelcontextprotocol/server-memory
```

Wenn keine Fehler auftreten, ist der Server bereit für PyCharm.

---

## Spezifische MedExamAI Use Cases

### 1. RAG-Index erstellen mit Filesystem + SQLite
```
Erstelle einen SQLite-Index aller Leitlinien in _BIBLIOTHEK/Leitlinien 
mit Titel, Fachgebiet und Dateipfad.
```

### 2. Faktenprüfung mit Brave Search
```
Prüfe ob "Amoxicillin 3x1g bei Pneumonie" korrekt ist. 
Suche in AWMF und DocCheck Leitlinien.
```

### 3. Batch-Verarbeitung mit Filesystem
```
Liste alle JSON-Dateien in _OUTPUT die "checkpoint" im Namen haben 
und zeige deren Größe und Datum.
```

### 4. Leitlinien-Download mit Fetch + Puppeteer
```
Lade alle fehlenden Leitlinien aus guideline_urls.py herunter 
und speichere sie in _BIBLIOTHEK/Leitlinien.
```

### 5. Kontext-Persistenz mit Memory
```
Speichere den aktuellen Projektstatus:
- 339 Fragen mit leerem Antwortfeld
- 75 Fragen mit Score < 3
- Budget: $170.99 verbleibend
- Nächster Schritt: Perplexity Fact-Check für restliche 68 Fragen
```

---

## Fehlerbehebung

### Problem: "MCP Server nicht erreichbar"
```bash
# Prüfe Node.js Installation
node --version
npx --version

# Cache leeren
npx clear-npx-cache
```

### Problem: "Permission denied"
```bash
# Stelle sicher, dass der Pfad lesbar ist
ls -la /Users/entropie/Documents/Medexamenai_Migration/
```

### Problem: "Module not found"
```bash
# MCP-Pakete manuell installieren
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-fetch
npm install -g @modelcontextprotocol/server-memory
```

---

## Konfigurationsdatei

Die vollständige MCP-Konfiguration ist in `mcp_config.json` gespeichert.
Sie können diese Datei auch direkt in PyCharm importieren, falls unterstützt.

---

## Weitere Ressourcen

- [MCP Dokumentation](https://modelcontextprotocol.io/)
- [Offizielle MCP Server](https://github.com/modelcontextprotocol/servers)
- [PyCharm GitHub Copilot Docs](https://www.jetbrains.com/help/pycharm/github-copilot.html)

---

*Erstellt: 2025-12-18 für MedExamAI Projekt*

