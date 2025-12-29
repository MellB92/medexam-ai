"""
MedExamAI Core Module
=====================
Enthält die Kernfunktionalitäten für das RAG-System:
- RAG Integration mit Embedding und Semantic Search
- Leitlinien-Fetcher (AWMF, DGIM, ESC, etc.)
- Medical Validation Layer (Dosierung, ICD-10, Labor, Logik)
"""

from .guideline_fetcher import (
    GuidelineFetcher,
    GuidelineMetadata,
    detect_medical_themes,
    fetch_guidelines_for_text,
)
from .medical_validator import (
    MedicalValidationLayer,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_medical_content,
)
from .rag_system import (
    EmbeddedContent,
    MedicalRAGSystem,
    RAGConfig,
    SearchResult,
    get_rag_system,
)
from .unified_api_client import (
    BudgetExceededError,
    UnifiedAPIClient,
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
    # API Client
    "UnifiedAPIClient",
    "BudgetExceededError",
]
