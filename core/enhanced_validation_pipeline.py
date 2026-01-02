#!/usr/bin/env python3
"""
Enhanced Validation Pipeline (lightweight)
========================================

`scripts/generate_evidenz_answers.py` expects an `EnhancedValidationPipeline`
with:
- constructor: (rag_system=None, log_dir: Path, strict_mode: bool)
- method: validate_answer(answer: str, query: str, question_id: str) -> (answer, metadata_dict)

Design goals for MedExamAI:
- No extra heavy dependencies
- Conservative (avoid obvious hallucinations), but not overly strict
  (the answer generator uses short 3-5 sentence answers and would otherwise fail
   "structured answer" validators).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

def _jsonify(value: Any) -> Any:
    """Convert common non-JSON-native objects (e.g. Enums/Paths) to JSON-safe values."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return _jsonify(asdict(value))
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonify(v) for v in value]
    if isinstance(value, tuple):
        return [_jsonify(v) for v in value]
    if isinstance(value, set):
        return [_jsonify(v) for v in sorted(value, key=lambda x: str(x))]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


class EnhancedValidationPipeline:
    """Lightweight validation wrapper used during answer generation."""

    def __init__(
        self,
        rag_system: Any = None,
        log_dir: Optional[Path] = None,
        strict_mode: bool = True,
    ) -> None:
        self.rag_system = rag_system
        self.log_dir = Path(log_dir) if log_dir else Path("_OUTPUT/validation_logs")
        self.strict_mode = bool(strict_mode)

        # Lazy imports (keep this module dependency-light)
        try:
            from core.medical_validator import HallucinationDetector, MedicalValidationLayer  # type: ignore

            self._medical_validator = MedicalValidationLayer()
            self._halluc_detector = HallucinationDetector()
        except Exception as e:  # pragma: no cover
            logger.warning(f"Medical validator components not available: {e}")
            self._medical_validator = None
            self._halluc_detector = None

        try:
            from core.hallucination_filter import HallucinationFilter  # type: ignore

            # Medium threshold removes AI self-references + strong uncertainty markers.
            self._halluc_filter = HallucinationFilter(severity_threshold="medium", remove_sentences=True)
        except Exception as e:  # pragma: no cover
            logger.warning(f"HallucinationFilter not available: {e}")
            self._halluc_filter = None

        self.log_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"EnhancedValidationPipeline ready (strict_mode={self.strict_mode}, log_dir={self.log_dir})")

    def _safe_fallback_answer(self) -> str:
        # One short sentence, consistent with generator constraints.
        return "Keine sichere Antwort möglich basierend auf den vorliegenden Leitlinien-Auszügen."

    def validate_answer(
        self,
        *,
        answer: str,
        query: str,
        question_id: str = "unknown",
    ) -> Tuple[str, Dict[str, Any]]:
        """Validate (and optionally sanitize) an answer.

        Returns:
            (validated_answer, metadata)
        """
        started_at = datetime.now().isoformat(timespec="seconds")
        original_answer = answer or ""
        cleaned_answer = original_answer

        # 1) Basic hallucination phrase cleanup (AI-self references, uncertainty)
        halluc_matches = []
        if self._halluc_filter is not None and cleaned_answer.strip():
            try:
                cleaned_answer, halluc_matches = self._halluc_filter.filter(cleaned_answer)
            except Exception as e:  # pragma: no cover
                logger.warning(f"HallucinationFilter failed: {e}")

        # 2) Medical validation (dosages/labs/ICD/logic)
        med_meta: Dict[str, Any] = {}
        med_is_valid = True
        med_confidence = 0.75  # sensible default
        med_issues = []
        med_warnings = []
        if self._medical_validator is not None:
            try:
                res = self._medical_validator.validate_qa_pair(query, cleaned_answer)
                med_is_valid = bool(res.is_valid)
                med_confidence = float(getattr(res, "confidence_score", 0.75) or 0.75)
                med_meta = getattr(res, "metadata", {}) or {}
                med_issues = [i.to_dict() for i in getattr(res, "issues", [])]
                med_warnings = [w.to_dict() for w in getattr(res, "warnings", [])]
            except Exception as e:  # pragma: no cover
                logger.warning(f"MedicalValidationLayer failed: {e}")

        # 3) Hallucination risk (no extra RAG lookup to avoid double work)
        halluc_risk = 0.0
        halluc_issues = []
        if self._halluc_detector is not None and cleaned_answer.strip():
            try:
                halluc_risk, hi = self._halluc_detector.validate(cleaned_answer, rag_context=None, rag_sources=None)
                halluc_risk = float(halluc_risk or 0.0)
                halluc_issues = [i.to_dict() for i in (hi or [])]
            except Exception as e:  # pragma: no cover
                logger.warning(f"HallucinationDetector failed: {e}")

        # 4) Minimal local quality gate (avoid rejecting short-but-correct answers too often)
        text_len = len(cleaned_answer.strip())
        too_short = text_len < 60

        # Combined confidence (0..1)
        conf = max(0.0, min(1.0, 0.55 * med_confidence + 0.45 * (1.0 - halluc_risk)))

        # Decision
        is_valid = bool(med_is_valid) and (halluc_risk <= 0.65) and not too_short
        fallback_applied = False
        final_answer = cleaned_answer.strip()

        if self.strict_mode and (not is_valid):
            final_answer = self._safe_fallback_answer()
            fallback_applied = True

        meta: Dict[str, Any] = {
            "question_id": question_id,
            "generated_at": started_at,
            "strict_mode": self.strict_mode,
            "is_valid": bool(is_valid),
            "confidence": round(conf, 3),
            "scores": {
                "medical_confidence": round(float(med_confidence), 3),
                "hallucination_risk": round(float(halluc_risk), 3),
            },
            "fallback_applied": fallback_applied,
            "length": {
                "original": len(original_answer),
                "cleaned": len(cleaned_answer),
                "final": len(final_answer),
                "too_short": bool(too_short),
            },
            "issues": [],
            "warnings": [],
            "meta": {
                "medical": med_meta,
                "hallucination_filter_matches": [
                    _jsonify(asdict(m) if is_dataclass(m) else {"text": str(m)}) for m in (halluc_matches or [])
                ],
            },
        }

        # Merge issues/warnings (flattened for caller)
        # - issues: medical issues + hallucination issues
        # - warnings: medical warnings
        meta["issues"] = list(med_issues) + list(halluc_issues)
        meta["warnings"] = list(med_warnings)
        meta = _jsonify(meta)

        # Persist per-question log (safe: _OUTPUT is gitignored)
        try:
            out_path = self.log_dir / f"{question_id}.json"
            payload = {
                "query": query,
                "original_answer": original_answer,
                "cleaned_answer": cleaned_answer,
                "final_answer": final_answer,
                "validation": meta,
            }
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:  # pragma: no cover
            logger.debug(f"Could not write validation log: {e}")

        return final_answer, meta



