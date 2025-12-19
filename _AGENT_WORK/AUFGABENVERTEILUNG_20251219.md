# Aufgabenverteilung: Claude Code + GPT-5.2 (PARALLEL)
**Datum:** 2025-12-19
**Status:** Die Zeit läuft - Projekt muss abgeschlossen werden!

---

## PARALLELE ARBEITSTEILUNG

### GPT-5.2 (Cursor) - Batch-Korrektur

| # | Aufgabe | Beschreibung |
|---|---------|--------------|
| 1 | API-Keys verifizieren | `python3 -c "from dotenv import load_dotenv..."` |
| 2 | **Batch-Korrektur** | 60 Problem-Items korrigieren |
| 3 | Merge durchführen | Nach Batch-Completion |
| 4 | Coverage validieren | Sollte 100% bleiben |

**Dein Befehl:**
```bash
PYTHONPATH=. python3 scripts/batch_correct_with_reasoning.py \
  --input _OUTPUT/batch_input_prepared_20251218_221551.json
```

---

### Claude Code (CLI) - Dokumentation & Manual Items

| # | Aufgabe | Beschreibung |
|---|---------|--------------|
| 1 | **7 manuelle Items** bearbeiten | Items die nicht via Batch korrigierbar sind |
| 2 | PROJECT_STATUS.md aktualisieren | Aktuellen Stand dokumentieren |
| 3 | TODO.md aktualisieren | Erledigte Tasks markieren |
| 4 | FINAL_REPORT erstellen | Abschlussbericht |

---

## KEINE ÜBERSCHNEIDUNGEN

| Ressource | GPT-5.2 | Claude Code |
|-----------|---------|-------------|
| `batch_correct_with_reasoning.py` | ✅ NUTZT | ❌ |
| `evidenz_antworten.json` | ✅ MERGED | ❌ LIEST NUR |
| `PROJECT_STATUS.md` | ❌ | ✅ SCHREIBT |
| `TODO.md` | ❌ | ✅ SCHREIBT |
| `FINAL_REPORT` | ❌ | ✅ ERSTELLT |
| 7 manuelle Items | ❌ | ✅ BEARBEITET |

---

## SYNCHRONISATION

1. GPT-5.2 startet Batch-Korrektur (dauert 30-60 Min)
2. Claude Code arbeitet parallel an Doku + Manual Items
3. Nach GPT-5.2 Merge → Claude Code validiert Coverage
4. Beide fertig → Projekt abgeschlossen

---

## API-KEYS (bereits konfiguriert)

```
Requesty: OK ✅
Anthropic: OK ✅
Perplexity_1: OK ✅
```

**START JETZT PARALLEL!**
