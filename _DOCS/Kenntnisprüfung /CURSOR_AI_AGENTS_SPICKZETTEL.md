# 🎯 Cursor AI-Agenten Spickzettel

> **Wichtig:** Command Palette öffnen mit `Shift + Cmd + P` (⇧⌘P)

---

## 1. Claude Code

| Aktion | Command-ID | Shortcut | Hinweis |
|--------|------------|----------|---------|
| **Command Palette öffnen** | – | **⇧⌘P** | Dann "Claude" tippen |
| Neue Konversation starten | `claude-vscode.newConversation` | ⌘N | Startet neuen Chat |
| Eingabefeld fokussieren/verlassen | `claude-vscode.focus` / `claude-vscode.blur` | ⌘Escape | Toggle (rein/raus) |
| Claude in Side Bar öffnen | `claude-vscode.sidebar.open` | – | Chat-Panel öffnen |
| Claude im neuen Tab öffnen | `claude-vscode.editor.open` | ⇧⌘Escape | Vollbild-Tab |
| Claude im Terminal öffnen | `claude-vscode.terminal.open` | – | Terminal-Modus |
| Proposed Changes annehmen | `claude-code.acceptProposedDiff` | – | Editor-Titel oder Command Palette |
| Proposed Changes ablehnen | `claude-code.rejectProposedDiff` | – | Editor-Titel oder Command Palette |
| @-Mention einfügen | `claude-vscode.insertAtMention` | ⌥K | Datei-Referenz |
| @-Mention auflösen | `claude-code.insertAtMentioned` | ⌥⌘K | Referenz einfügen |
| Logs anzeigen | `claude-vscode.showLogs` | – | Debugging |
| Logout | `claude-vscode.logout` | – | Abmelden |

---

## 2. Cursor AI (Chat, Composer, Agent)

| Aktion | Shortcut | Hinweis |
|--------|----------|---------|
| **Command Palette öffnen** | **⇧⌘P** | Zentraler Einstiegspunkt |
| Chat öffnen (AI Assistant) | ⌘L | Freies Chatten |
| Composer öffnen | ⌘I | Code-Änderungen im Editor |
| Composer Vollbild | ⇧⌘I | Größerer Arbeitsbereich |
| Agent Mode aktivieren | ⌘I → Agent-Icon klicken | "Autopilot" für komplexe Tasks |

---

## 3. Kilo Code

| Aktion | Methode | Hinweis |
|--------|---------|---------|
| Kilo-Panel öffnen | Icon in Side Bar | Oder: View → Open View → "Kilo Code" |
| Neue Anfrage | Text eingeben + Enter | Im Kilo-Panel |
| @-Mentions nutzen | `@datei.py` oder `@codebase` | Kontext geben |
| Modell wechseln | Model-Dropdown im Panel | UI-gesteuert |
| Code-Änderungen | "Apply" / "Reject" Buttons | Im Chat-Panel |

---

## 4. Roo Code

| Aktion | Shortcut / Methode | Hinweis |
|--------|-------------------|---------|
| Code Actions öffnen | ⌘. (Lightbulb) | Oder Rechtsklick → "Roo Code" |
| Command Palette | ⇧⌘P → "Roo Code ..." | Alle Roo-Aktionen |
| Explain Code | Code Actions → Explain | Code erklären |
| Improve Code | Code Actions → Improve | Verbesserungen |
| Fix Code | Code Actions → Fix | Fehler beheben |
| Add to Context | Code Actions → Add to Context | Code in Chat schicken |
| New Task | Code Actions → New Task | Neue Aufgabe erstellen |

**Terminal Actions** (Text markieren → Rechtsklick):
- Terminal: Add to Context
- Terminal: Fix Command
- Terminal: Explain Command

---

## 5. Rovo Dev (CLI)

| Aktion | Terminal-Befehl | Hinweis |
|--------|-----------------|---------|
| Rovo Dev starten (interaktiv) | `acli rovodev run` | Startet den Agenten |
| Einmaliger Befehl | `acli rovodev run "deine Aufgabe"` | Non-interactive |
| Shadow Mode | `acli rovodev run --shadow` | Arbeitet in Kopie |
| Config öffnen | `acli rovodev config` | Einstellungen ändern |

### Modell wechseln bei Rovo Dev:
1. Terminal: `acli rovodev config`
2. In der Datei `~/.rovodev/config.yml` unter `agent:` den Eintrag ändern:
   ```yaml
   agent:
     modelId: "auto"              # Standard
     # modelId: "claude-3.5-sonnet"  # Alternative
   ```
3. Speichern und Rovo Dev neu starten

---

## 🚀 Quick Reference - Die wichtigsten Shortcuts

| Was will ich tun? | Agent | Shortcut |
|-------------------|-------|----------|
| **Command Palette öffnen** | Alle | **⇧⌘P** |
| Claude Code fokussieren | Claude Code | ⌘Escape |
| Neuer Claude Chat | Claude Code | ⌘N |
| Cursor Chat öffnen | Cursor AI | ⌘L |
| Cursor Composer öffnen | Cursor AI | ⌘I |
| Code Actions (Lightbulb) | Roo Code | ⌘. |
| CLI Agent starten | Rovo Dev | `acli rovodev run` |

---

*Erstellt: 30.11.2025 | Für: Cursor IDE auf macOS*
