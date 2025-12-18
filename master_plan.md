# Medexamen.ai Masterplan

## Ziele
1. Stabilisierung der Generierungspipeline
2. Implementierung des Spaced-Repetition-Algorithmus
3. Bereinigung der offenen Fragenliste
4. Generierung von Antworten in kleinen Batches
5. Qualitätssicherung und Integration

## Kritische Pfade
- Fragenbasis
- Antworten
- Knowledge Base (KB)
- Offene-Liste (questions_missing_strict.json)
- Prompts
- Spaced-Repetition-Dateien
- Mentor-Agent-Dokumente

## Aufgaben pro Agent

### Claude Code (Cursor/Opus 4.5)
**Verantwortung:** Stabilisierung der Generierungspipeline
- KB-Load optimieren
- Websuche integrieren und stabilisieren
- Modellwahl logik verbessern
- Decimal-Fix prüfen und beheben
- MD-Export Filter implementieren (keine leeren/fraglichen Antworten)
- Logging und KB-Load Monitoring einrichten

### Kilo Code (Cursor/Spectre)
**Verantwortung:** Spaced-Repetition Implementierung
- Design finalisieren (spaced_repetition_design.md)
- Algorithmus implementieren (spaced_repetition/algorithm.py)
- Tests implementieren (spaced_repetition/test_algorithm.py)
- Integration mit Mentor-Agent skizzieren
- Dokumentation erstellen

### GitHub Copilot + Grok 4 (PyCharm)
**Verantwortung:** Unterstützung bei Spaced-Repetition
- Boilerplate Code generieren
- Refactoring Unterstützung
- Unit Tests Unterstützung
- Leichte Helferfunktionen für Klassifikation/Validierung
- Keine großen Architekturänderungen

### Mensch (Koordinator)
**Verantwortung:** Infrastruktur und Qualitätssicherung
- API-Keys klären (OpenAI/Vertex/Portkey)
- Unicode-Problem im OpenAI-Key fixen (\u2028 entfernen)
- Quotas überwachen
- Jira/Git Updates durchführen
- Freigaben erteilen
- Backups/Checkpoints anstoßen

### Codex (Lead)
**Verantwortung:** Generierung und Qualitätssicherung
- Offene Liste bereinigen (~147 sinnvolle Lücken aus questions_missing_strict.json)
- Generierung in kleinen Batches mit gpt-4o-mini
- Leitlinien-KB integrieren
- Websuche nutzen
- QC/Merge Prozesse durchführen
- MD-Stichproben erstellen
- Backup/Checkpoint nach jedem Lauf

## Nächste Schritte
1. Backup/Checkpoint jetzt erstellen
2. Claude Code: Generierungspipeline stabilisieren
3. Kilo Code: Spaced-Repetition Design finalisieren
4. GitHub Copilot: Kilo Code unterstützen
5. Mensch: API-Keys und Unicode-Problem fixen
6. Codex: Offene Liste bereinigen und erste Batch-Generierung starten

## Backup/Checkpoint-Reminder
- Vor jedem größeren Lauf Backup erstellen
- Nach jedem erfolgreichen Lauf Checkpoint speichern
- Kritische Dateien regelmäßig sichern:
  - questions_missing_strict.json
  - Generierte Antworten
  - Knowledge Base
  - Spaced-Repetition Code
  - Mentor-Agent Dokumente

## Klare Ansagen an die Agenten

### An Claude Code:
"Stabilisiere die Generierungspipeline (KB-Load, Websuche, Modellwahl). Prüfe Decimal-Fix, sorge dafür, dass MD-Export keine leeren/fraglichen Antworten durchlässt, Logs/KB-Load im Blick behalten."

### An Kilo Code:
"Fokus Spaced-Repetition: Design finalisieren (spaced_repetition_design.md), implementieren in spaced_repetition/algorithm.py, Tests in spaced_repetition/test_algorithm.py grün bekommen. Integration-Skizze zum Mentor-Agent (siehe mentor_agent_*)."

### An GitHub Copilot + Grok 4:
"Unterstütze Kilo bei Boilerplate/Refactors/Unittests im Spaced-Repetition-Ordner; leichte Helfer für Klassifikation/Validierung, keine großen Eingriffe."

### An Mensch:
"API-Keys/Quotas klären (OpenAI/Vertex/Portkey), Unicode-Problem im OpenAI-Key fixen (\u2028 entfernen), Jira/Git updaten, Freigaben geben, Backups/Checkpoints anstoßen."

### An Codex:
"Offene Liste bereinigen (~147 sinnvolle Lücken aus questions_missing_strict.json), Generierung in kleinen Batches mit gpt-4o-mini + Leitlinien-KB + Websuche, danach QC/Merge, MD-Stichprobe. Backup/Checkpoint jetzt und nach jedem Lauf."