# 🎯 MedExamAI - Postmigrationsplan (Dezember 2025)

## 📋 Übersicht
Dieser Plan strukturiert die Arbeit nach der erfolgreichen Migration und dem Rebuild des Systems. Ziel ist die finale Vorbereitung auf die Kenntnisprüfung im März 2026 durch ein stabiles, evidenzbasiertes Lernsystem.

---

## 🏗️ Phase 1: Konsolidierung & Stabilisierung (Dez 2025)
*Fokus: Die neue Infrastruktur (RAG, Multi-Provider) zuverlässig machen.*

### 1.1 Synchronisation der Dokumentation
- [ ] **Status-Update:** `PROJECT_STATUS.md` und `TODO.md` auf den Stand von Dezember 2025 bringen.
- [ ] **Archivierung:** Veraltete Skripte aus dem Rebuild (2024) in `_ARCHIVE/` verschieben, falls redundant zu neuen `core/` Modulen.
- [ ] **Masterplan-Abgleich:** Sicherstellen, dass alle Agenten (Claude, Kilo, Codex) nach den im `master_plan.md` definierten Rollen arbeiten.

### 1.2 Pipeline-Härtung
- [ ] **KB-Load Optimierung:** Ladezeiten des RAG-Index minimieren (`build_rag_index.py`).
- [ ] **Error Handling:** Implementierung von `recovery_manager.py` und `crash_handler.py` in allen Batch-Skripten verifizieren.
- [ ] **API-Resilienz:** Überprüfung des `unified_api_client` auf korrekte Fallbacks bei Quota-Limits.

---

## 🚀 Phase 2: Skalierung der Inhalte (Jan 2026)
*Fokus: Masse mit Klasse – Generierung des kompletten Fragenkatalogs.*

### 2.1 Batch-Generierung
- [ ] **Offene Liste abarbeiten:** Die ~147 fehlenden Fragen aus `questions_missing_strict.json` generieren.
- [ ] **Evidenz-Integration:** Verstärkter Einsatz von `generate_evidenz_answers.py` unter Nutzung der AWMF-Leitlinien.
- [ ] **Qualitätssicherung:** Stichprobenartige Prüfung (10%) der generierten Antworten durch den `medical_validator.py`.

### 2.2 Wissensbasis-Erweiterung
- [ ] **Leitlinien-Update:** Prüfung, ob neuere Leitlinien (Stand Ende 2025) in `_BIBLIOTHEK/` integriert werden müssen.
- [ ] **ICD-10 Mapping:** Alle extrahierten Fragen final mit ICD-10 Codes taggen (via `category_classifier.py`).

---

## 🧠 Phase 3: Personalisierung & Spaced Repetition (Feb 2026)
*Fokus: Effizientes Lernen durch algorithmische Unterstützung.*

### 3.1 SRS-Implementierung (Spaced Repetition System)
- [ ] **Algorithmus:** Finalisierung von `spaced_repetition/algorithm.py` (basierend auf SM-2 oder ähnlichem).
- [ ] **Anki-Export:** Optimierung des `exam_formatter.py` für nahtlosen Import in Anki mit allen Metadaten (Kategorie, Quelle, Evidenz-Grad).
- [ ] **Fortschritts-Tracking:** Implementierung von `state_persistence.py` zur Speicherung des Lernstatus.

### 3.2 Mentor-Agent Integration
- [ ] **Interaktives Lernen:** Verknüpfung der RAG-Pipeline mit einem Chat-Interface (Mentor-Agent), um Rückfragen zu Antworten zu ermöglichen.

---

## 🎓 Phase 4: Finaler Check & Prüfungs-Simulation (März 2026)
*Fokus: Prüfungssicherheit.*

- [ ] **Simulation:** Generierung von Probeprüfungen basierend auf der `PRÜFUNGSSTRUKTUR_MÜNSTER.md`.
- [ ] **Last-Minute-Updates:** Schnelle Einarbeitung neuester Protokolle vom Januar/Februar 2026.
- [ ] **System-Freeze:** Keine Code-Änderungen mehr 2 Wochen vor der Prüfung, nur noch Content-Updates.

---

## 🛠️ Kritische Erfolgsfaktoren (KPIs)
1. **Validitätsrate:** > 95% der medizinischen Fakten müssen durch `medical_fact_checker.py` bestätigt sein.
2. **Abdeckung:** Mindestens 500 hochwertige Q&A-Paare aus dem Gold-Standard.
3. **Stabilität:** Null unvorhergesehene Abstürze in der Generierungspipeline.

---
**Nächster Schritt:** Ausführung des `complete_empty_answer_regen_workflow.py` um Lücken zu schließen.
