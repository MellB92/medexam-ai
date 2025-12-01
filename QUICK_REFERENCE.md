# ⚡ Quick Reference Card - MedExamAI

**1-Seiten-Übersicht für schnellen Zugriff**

---

## 🎯 Projekt-Übersicht

**Ziel:** Kenntnisprüfung März 2025 vorbereiten  
**Methode:** Echte Fragen aus 40 Prüfungsprotokollen extrahieren  
**Status:** ✅ Setup fertig, bereit für Entwicklung

---

## 📁 Wichtigste Verzeichnisse

```
_GOLD_STANDARD/      # 40 echte Prüfungsprotokolle
_EXTRACTED_FRAGEN/   # Extrahierte Fragen (Output)
_OUTPUT/             # Finale Q&A-Paare
scripts/             # Python-Skripte
```

---

## 🚀 Wichtigste Kommandos

### Extraktion starten
```bash
cd ~/Documents/Medexamenai
python3 scripts/extract_dialog_blocks.py
```

### Output prüfen
```bash
cat _EXTRACTED_FRAGEN/frage_bloecke.json | head -50
```

### Status checken
```bash
git status
ls -lh _GOLD_STANDARD/ | wc -l  # Sollte 40 sein
```

---

## 📚 Wichtigste Dokumente

| Datei | Verwendung |
|-------|------------|
| `README.md` | **START HIER** - Projektübersicht |
| `TODO.md` | Was ist zu tun? |
| `DEVELOPMENT.md` | Wie entwickeln? |
| `PROJECT_STATUS.md` | Aktueller Stand |

---

## 🔄 Die 4 Phasen

```
Phase 1: Extraktion      (2 Wochen)  ← AKTUELL
Phase 2: Generierung     (2 Wochen)
Phase 3: Validation      (2 Wochen)
Phase 4: Export          (1 Woche)
```

---

## ⚠️ Kritische Regeln

1. ❌ **NIEMALS** fiktive Cases erfinden
2. ✅ **IMMER** `source_tier: "gold_standard"` setzen
3. ✅ **IMMER** Backup vor Änderungen
4. ❌ **NIEMALS** Tier 1 und Tier 2 mischen

---

## 🐛 Häufige Probleme

**Problem:** OCR schlägt fehl  
**Lösung:** `pip install pytesseract`

**Problem:** Keine Fragen extrahiert  
**Lösung:** Prüfe PDF-Format, evtl. manuell konvertieren

**Problem:** JSON-Error  
**Lösung:** Prüfe UTF-8 Encoding

---

## 📞 Hilfe

**Dokumentation:** Siehe README.md  
**Fehler:** Siehe TODO.md → Known Issues  
**Entwicklung:** Siehe DEVELOPMENT.md

---

## ✅ Nächste Schritte

1. [ ] Testlauf: 1 Sample-PDF
2. [ ] GitHub Repo erstellen
3. [ ] Jira Projekt erstellen
4. [ ] Vollständige Extraktion (40 PDFs)

---

**Erstellt:** 2024-12-01  
**Projekt:** MedExamAI  
**Version:** 1.0
