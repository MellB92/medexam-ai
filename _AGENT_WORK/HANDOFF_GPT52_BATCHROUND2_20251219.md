# Handoff: GPT‑5.2 Batch-Runde 2 → Claude Code (2025-12-19)

## TL;DR

Batch-Runde 2 ist **technisch durchgelaufen** (Korrektur + Web-Validierung + Merge/Promotion).  
Coverage bleibt **100%**. Es bleiben **17** Items als „problem“ zur manuellen/zweiten Runde.

---

## Run-IDs / Artefakte

- **RUN_ID:** `20251219_082951`

### Korrektur
- Corrected JSON: `_OUTPUT/batch_corrected_20251219_082951.json`
- Corrected Checkpoint: `_OUTPUT/batch_corrected_20251219_082951_checkpoint.jsonl`
- LLM-Kosten (Correction stage): ~`2.23 USD` (laut Script-Output)

### Web-Validierung (Perplexity)
- Validated JSON: `_OUTPUT/batch_validated_20251219_082951.json`
- Validated Checkpoint: `_OUTPUT/batch_validated_20251219_082951_checkpoint.jsonl`
- Summary: `ok=25, maybe=18, problem=17, error=0`

### Finalize / Merge Outputs
- Updated evidenz file (generated): `_OUTPUT/evidenz_antworten_updated_20251219_095605.json`
- Report: `_OUTPUT/batch_review_report_20251219_095605.md`
- Remaining issues: `_OUTPUT/batch_review_remaining_issues_20251219_095605.json` (**n=17**)

### Promotion + Backup
- Canonical promoted: `_OUTPUT/evidenz_antworten.json`
- Backup created: `_OUTPUT/evidenz_antworten_backup_20251219_095619.json`

### Coverage
- meaningful coverage: `2527/2527 = 100.0%`

---

## Was jetzt offen ist (für Claude)

1) **Doku aktualisieren** (PROJECT_STATUS/TODO/Final Report) mit den oben genannten Artefakten.
2) **Manuelle/zweite Runde**:
   - Die 17 Remaining-Issues sind in `_OUTPUT/batch_review_remaining_issues_20251219_095605.json`.
   - Diese sind *zusätzlich* zu den ursprünglich separat geplanten „7 manuellen Items“ (falls diese Liste noch gilt).

Empfehlung: Wenn Ziel weiterhin „nur 7 manuell“, dann müssen die 17 Remaining-Issues entweder:
- durch eine gezielte zweite Batch-Korrektur-Runde (nur diese 17 Items) reduziert werden, **oder**
- manuell priorisiert werden (z. B. nur STIKO/Leitlinien-Updates zuerst).


