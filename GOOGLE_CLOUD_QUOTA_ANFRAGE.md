# Google Cloud GPU Quota-Erhöhung - MedExam AI

**Datum:** 2025-12-23
**Projekt-ID:** medexamenai (alternativ: deft-ocean-465700-d7)
**Billing ID:** 01D10E-FF6287-F07606
**Region:** us-central1 (primär), europe-west4 (alternativ)
**Sales-Kontakt:** Tanert (tanert@google.com)

---

## Anfrage-Text (Deutsch)

```
Anfrage zur Kontingent-Erhöhung für "Custom model serving Nvidia A100 80GB GPUs"
von 1 auf 4 GPUs in us-central1.

Projekt: MedExam AI - Evidenzbasierte Prüfungsvorbereitung für medizinisches
Fachpersonal.

USE-CASE:
Wir entwickeln eine KI-gestützte Lernplattform, die medizinischem Personal hilft,
sich im Dschungel der medizinischen Fachinformationen zurechtzufinden. Unser System
nutzt spezialisierte LLM-Modelle für höchste medizinische Präzision und verbindet
aktuelle Leitlinien mit evidenzbasiertem Lernen.

Die Plattform adressiert ein kritisches Problem: Die Menge an medizinischem Wissen
verdoppelt sich alle 73 Tage. Ärzte und medizinisches Personal brauchen intelligente
Werkzeuge, die relevante Informationen filtern und prüfungsrelevant aufbereiten.

GPU-BEDARF:
MedGemma - das auf medizinische Anwendungen spezialisierte Modell von Google -
benötigt für optimale Inferenz-Performance 2-4 A100 GPUs. Die 4-GPU-Konfiguration
ermöglicht uns:
1. Schnelle Antwortzeiten für interaktives Lernen
2. Zuverlässigen Betrieb ohne Ausfallzeiten
3. Skalierung für wachsende Nutzerzahlen

VORHERIGE ABSTIMMUNG:
Dieser Use-Case wurde bereits mit Tanert (tanert@google.com) vom Google Cloud
Sales Team besprochen und abgestimmt. Bitte um zeitnahe Freigabe für unseren
Pilotbetrieb.

Vielen Dank.
```

---

## Anfrage-Text (Englisch)

```
Requesting quota increase for "Custom model serving Nvidia A100 80GB GPUs"
from 1 to 4 GPUs in us-central1.

Project: MedExam AI - Evidence-based exam preparation for medical professionals.

USE-CASE:
We are building an AI-powered learning platform that helps medical professionals
navigate the jungle of medical information. Our system leverages specialized LLM
models for highest medical precision, connecting current clinical guidelines with
evidence-based learning.

The platform addresses a critical challenge: Medical knowledge doubles every 73 days.
Physicians and healthcare professionals need intelligent tools that filter relevant
information and prepare it for exam success and clinical practice.

GPU REQUIREMENTS:
MedGemma - Google's specialized model for medical applications - requires 2-4 A100
GPUs for optimal inference performance. The 4-GPU configuration enables:
1. Fast response times for interactive learning
2. Reliable operation without downtime
3. Scalability for growing user base

PRIOR COORDINATION:
This use case has been discussed and agreed upon with Tanert (tanert@google.com)
from Google Cloud Sales Team. Please approve for our pilot deployment.

Thank you.
```

---

## Technische Begründung (für Nachfragen)

### Warum 4 GPUs?

| Konfiguration | Use-Case | Begründung |
|---------------|----------|------------|
| 1x A100 | Minimalbetrieb | Kein Failover, keine parallele Verarbeitung |
| 2x A100 | Basis | Ein Modell aktiv, ein Backup |
| **4x A100** | **Empfohlen** | 2 für Produktion, 2 für Testing/Updates |
| 8x A100 | Overkill | Für dieses Projekt nicht erforderlich |

### MedGemma Ressourcen-Bedarf

- **MedGemma-4B-IT**: 1x A100 (8-16GB VRAM)
- **MedGemma-27B-IT**: 2-4x A100 (40-80GB VRAM, Tensor-Parallelismus)

### Geschätzte Nutzung

```
Phase 1 (Pilot): 2 Wochen
- 500-1.000 GPU-Stunden
- Batch-Verarbeitung: 4.556 Fragen × 5 RAG-Durchläufe
- Kosten: ~$500-1.000 USD

Phase 2 (Produktion): Ongoing
- 100-200 GPU-Stunden/Monat
- Inkrementelle Updates, neue Protokolle
- Kosten: ~$100-200 USD/Monat
```

---

## Projekt-Statistiken

| Metrik | Wert |
|--------|------|
| Prüfungsprotokolle | 348 Dateien |
| Medizinische Leitlinien | 126 PDFs (AWMF, ESC, DGK) |
| Fachgebiete | 26 (Kardiologie, Neurologie, etc.) |
| Extrahierte Fragen | 9.633 (roh) |
| Deduplizierte Fragen | 4.556 |
| Generierte Antworten | 2.909 |
| RAG-Index Größe | 2.04 GB |
| Embedding-Einträge | 189.887 |

---

## Kontakte

- **Projekt-Owner:** dagoberto.bs@gmx.de / xcorpiodbs@gmail.com
- **Google Sales:** Tanert (tanert@google.com)
- **Projekt-URL:** (falls verfügbar)

---

## Anhang: Provider-Architektur

```
┌─────────────────────────────────────────────────────────┐
│                    MedExam AI                           │
│                 Multi-Provider System                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐            │
│  │Requesty │───→│Anthropic│───→│   AWS   │            │
│  │ (GPT)   │    │ Claude  │    │ Bedrock │            │
│  └─────────┘    └─────────┘    └─────────┘            │
│       │              │              │                  │
│       └──────────────┼──────────────┘                  │
│                      ▼                                 │
│              ┌─────────────┐                           │
│              │  Fallback   │                           │
│              │   Router    │                           │
│              └──────┬──────┘                           │
│                     │                                  │
│                     ▼                                  │
│     ┌───────────────────────────────────┐             │
│     │      MedGemma (Vertex AI)         │             │
│     │   Spezialisiert für Medizin       │             │
│     │   Budget: €217.75                 │             │
│     │   GPU: A100 80GB (4x requested)   │             │
│     └───────────────────────────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```
