"""
MedExamAI Core Module
=====================
Enthält die Kernfunktionalitäten für das RAG-System:
- RAG Integration mit Embedding und Semantic Search
- Leitlinien-Fetcher (AWMF, DGIM, ESC, etc.)
- Medical Validation Layer (Dosierung, ICD-10, Labor, Logik)
"""

from .rag_system import (
    MedicalRAGSystem,
    EmbeddedContent,
    SearchResult,
    RAGConfig,
    get_rag_system,
)

from .guideline_fetcher import (
    GuidelineFetcher,
    GuidelineMetadata,
    detect_medical_themes,
    fetch_guidelines_for_text,
)

from .medical_validator import (
    MedicalValidationLayer,
    ValidationResult,
    ValidationIssue,
    ValidationSeverity,
    validate_medical_content,
)

__all__ = [
    # RAG
    "MedicalRAGSystem",
    "EmbeddedContent",
    "SearchResult",
    "RAGConfig",
    "get_rag_system",
    # Guidelines
    "GuidelineFetcher",
    "GuidelineMetadata",
    "detect_medical_themes",
    "fetch_guidelines_for_text",
    # Validation
    "MedicalValidationLayer",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_medical_content",
]
