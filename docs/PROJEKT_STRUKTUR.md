# Projekt-Struktur: Drei-Kategorien-System

**Stand:** 2025-12-21

## Überblick

Dieses Projekt verwendet eine strikte Trennung in **DREI Kategorien**, die essentiell für die korrekte Funktion ist:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEDEXAM-AI DATENFLUSS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PRÜFUNGSPROTOKOLLE          FAKTEN                            │
│  (Input Typ 1)               (Input Typ 2)                     │
│  ┌─────────────┐             ┌─────────────┐                   │
│  │_GOLD_STANDARD│             │_BIBLIOTHEK  │                   │
│  │_EXTRACTED_   │             │_WISSENSBASIS│                   │
│  │  FRAGEN      │             │_FACT_CHECK_ │                   │
│  └──────┬──────┘             │  SOURCES    │                   │
│         │                     └──────┬──────┘                   │
│         │                            │                          │
│         ▼                            ▼                          │
│  ┌─────────────┐             ┌─────────────┐                   │
│  │   Fragen-   │             │  RAG Index  │                   │
│  │  Extraktion │             │   Builder   │                   │
│  └──────┬──────┘             └──────┬──────┘                   │
│         │                            │                          │
│         └────────────┬───────────────┘                          │
│                      ▼                                          │
│              ┌─────────────┐                                    │
│              │   OUTPUT    │                                    │
│              │ _OUTPUT/    │                                    │
│              └─────────────┘                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Kategorie 1: PRÜFUNGSPROTOKOLLE

### Zweck

Verständnis des Prüfungsablaufs, Themen-Priorisierung, Empfehlungen von Teilnehmern.

### Charakteristika

- Prüfungsberichte und -protokolle
- Erfahrungsberichte von Prüfungsteilnehmern
- Fälle aus Kenntnisprüfungen (KP)
- Prüfungsfragen und -antworten
- Tipps und Empfehlungen für die Prüfung
- Fachsprachprüfung (FSP) Materialien
- Anamnese-Übungen für Prüfungssimulation

### Verzeichnisse

| Verzeichnis | Inhalt |
|-------------|--------|
| `_GOLD_STANDARD/` | Kenntnisprüfung-Protokolle 2020-2025, Telegram Reports |
| `_EXTRACTED_FRAGEN/` | Extrahierte Frage-Blöcke, Q&A-Paare |

### RAG-Relevanz

**NICHT für RAG** — Diese Dateien dienen der Fragen-Extraktion und dem Prüfungskontext-Verständnis, nicht als Fakten-Quelle.

---

## Kategorie 2: FAKTEN

### Zweck

Evidenzbasierte Antwort-Generierung und Faktencheck.

### Charakteristika

- Leitlinien (AWMF, DGK, ESC, NVL, etc.)
- Lehrbuch-Material (Innere Medizin, Chirurgie)
- Arzneimittel und Pharmakologie
- Anatomie, Physiologie, Pathologie
- Klinische Notfälle und Therapie
- Laborwerte und Diagnostik
- EKG, Röntgen, MRT Interpretation

### Verzeichnisse

| Verzeichnis | Inhalt |
|-------------|--------|
| `_BIBLIOTHEK/` | 60 Leitlinien-PDFs nach Fachgebiet organisiert |
| `_WISSENSBASIS/` | Spezialgebiete (Rechtsmedizin, Strahlenschutz) |
| `_FACT_CHECK_SOURCES/` | Lehrbuch-Material (Innere Medizin I/II, Chirurgie, Pharmakologie) |

### RAG-Relevanz

**FÜR RAG** — Diese Dateien werden in die RAG Knowledge Base indexiert.

---

## Kategorie 3: OUTPUT

### Zweck

Generierte Ergebnisse und Validierungsberichte.

### Verzeichnisse

| Verzeichnis | Inhalt |
|-------------|--------|
| `_OUTPUT/` | evidenz_antworten.json, rag_knowledge_base.json, antworten_md/ |

---

## Kategorisierung von unsortierten Dateien

### Schlüsselwort-basierte Erkennung

**PRÜFUNGSPROTOKOLLE:**

```python
PROTOKOLL_KEYWORDS = [
    "kenntnisprüfung", "prüfung", "simulation", "fälle", "fall ",
    "protokoll", "fsp", "fachsprachprüfung", "düsseldorf", "münster",
    "anamnese", "arzt-arzt", "arztbrief", "dokumentation", "doku",
    "epikrise", "aufklärung", "übung", "lückentext", "lösung",
    "skript", "pp ", "ü1", "ü2", "ü3", "ü4", "ü5", "fb "
]
```

**FAKTEN:**

```python
FAKTEN_KEYWORDS = [
    "leitlinie", "s1_", "s2_", "s3_", "awmf", "prophylaxe", "therapie",
    "chirurgie", "innere", "anatomie", "physiologie", "pathologie",
    "schrauben", "naht", "ecg", "ekg", "mrt", "röntgen", "labor",
    "notfall", "hyperkaliämie", "hypokaliämie", "tetanus", "kompendium",
    "strahlen", "osteoporose", "vegetative", "endoskopie", "syndrom"
]
```

**SPRACHLICH/ADMINISTRATIV:**

```python
SPRACHLICH_KEYWORDS = [
    "konjunktion", "präfix", "nominalisierung", "verbal", "grammatik",
    "anmeldung", "antrag", "formular", "bewerbung", "azav"
]
```

### Grenzfälle

| Dateiname | Kategorie | Begründung |
|-----------|-----------|------------|
| "Anamnese Grundwortschatz.pdf" | PROTOKOLLE | Übungsmaterial für Prüfung |
| "Anamnese-Erhebung Leitlinie.pdf" | FAKTEN | Leitlinien-Dokument |
| "Schmerz Therapie S3.pdf" | FAKTEN | Leitlinie |
| "Schmerz Fall Simulation.pdf" | PROTOKOLLE | Prüfungssimulation |

---

## Restrukturierung (geplant)

### Schritt 1: Prüfungsprotokolle verschieben

```bash
mv _FACT_CHECK_SOURCES/pruefungsprotokolle/ _GOLD_STANDARD/archiv_protokolle/
```

### Schritt 2: Kreuzmich-Fragen verschieben

```bash
mv "_FACT_CHECK_SOURCES/Kreuzmich Fragen und Auswertungen/" _EXTRACTED_FRAGEN/kreuzmich/
```

### Schritt 3: Unsortierte kategorisieren

Siehe: `_AGENT_WORK/CODEX_PROMPT_UNSORTIERT_KATEGORISIERUNG.md`

---

## Wichtige Regeln

1. **Prüfungsprotokolle ≠ Fakten** — Diese Unterscheidung ist essentiell
2. **RAG nur aus FAKTEN** — Niemals Prüfungsprotokolle in den RAG-Index
3. **Duplikate vermeiden** — Vor dem Verschieben auf Duplikate prüfen
4. **Backup vor Änderungen** — Immer Backup erstellen vor Restrukturierung
