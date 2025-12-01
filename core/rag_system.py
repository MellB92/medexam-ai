#!/usr/bin/env python3
"""
MedExamAI RAG System
====================

Retrieval-Augmented Generation System für medizinische Prüfungsvorbereitung.

Features:
- Embedding-Generierung (lokal oder OpenAI)
- Semantische Suche über Fragen und Leitlinien
- Wissensbasis-Aufbau aus Gold-Standard-Dokumenten
- Kontextabfrage für Antwortgenerierung
- Kosten-Tracking für API-Nutzung

Autor: MedExamAI Team
"""

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Dict, Optional, Any, Union, Tuple
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RAGConfig:
    """Konfiguration für das RAG-System."""

    # Chunking-Parameter
    chunk_size: int = 500
    chunk_overlap: int = 100

    # Embedding-Parameter
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536  # OpenAI text-embedding-3-small

    # Retrieval-Parameter
    top_k: int = 5
    similarity_threshold: float = 0.7

    # Verarbeitungsparameter
    batch_size: int = 32

    # Kosten-Tracking
    cost_per_1m_tokens: float = 0.02  # $0.02 per 1M tokens für text-embedding-3-small

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EmbeddedContent:
    """Inhalt mit Embedding-Vektor."""
    content_id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]
    source_module: str  # z.B. "gold_standard", "leitlinien", "fragen"
    source_tier: str  # "tier1_gold" oder "tier2_bibliothek"
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResult:
    """Ergebnis einer semantischen Suche."""
    content_id: str
    text: str
    similarity_score: float
    metadata: Dict[str, Any]
    source_module: str
    source_tier: str
    rank: int


@dataclass
class CostTracker:
    """Kosten-Tracker für API-Nutzung."""
    total_tokens: int = 0
    total_cost: float = 0.0
    budget_limit: float = 200.0  # €200 Budget

    def add_usage(self, tokens: int, cost_per_1m: float = 0.02) -> None:
        self.total_tokens += tokens
        self.total_cost += tokens * cost_per_1m / 1_000_000

    @property
    def remaining_budget(self) -> float:
        return max(0, self.budget_limit - self.total_cost)

    @property
    def budget_exhausted(self) -> bool:
        return self.total_cost >= self.budget_limit

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.total_tokens,
            "total_cost_eur": round(self.total_cost, 4),
            "remaining_budget_eur": round(self.remaining_budget, 2),
            "budget_exhausted": self.budget_exhausted
        }


class EmbeddingCache:
    """Cache für Embeddings zur Vermeidung von Neuberechnung."""

    def __init__(self, cache_dir: str = ".embedding_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "embeddings.json"
        self.cache: Dict[str, Dict] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Cache geladen: {len(self.cache)} Embeddings")
            except Exception as e:
                logger.error(f"Cache-Ladefehler: {e}")
                self.cache = {}

    def _save_cache(self) -> None:
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f)
            logger.debug(f"Cache gespeichert: {len(self.cache)} Embeddings")
        except Exception as e:
            logger.error(f"Cache-Speicherfehler: {e}")

    def get(self, text: str) -> Optional[List[float]]:
        key = self._generate_key(text)
        entry = self.cache.get(key)
        return entry.get("embedding") if entry else None

    def set(self, text: str, embedding: List[float], metadata: Dict = None) -> None:
        key = self._generate_key(text)
        self.cache[key] = {
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
        }

    def save(self) -> None:
        self._save_cache()

    @staticmethod
    def _generate_key(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()


class MedicalRAGSystem:
    """
    Haupt-RAG-System für medizinische Inhalte.

    Integriert:
    - Embedding-Generierung (lokal oder OpenAI)
    - Semantische Suche
    - Wissensbasis-Management
    - Tier-basierte Suche (Gold-Standard priorisiert)
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        use_openai: bool = False,
        cache_dir: str = ".embedding_cache"
    ):
        self.config = config or RAGConfig()
        self.use_openai = use_openai
        self.embedding_cache = EmbeddingCache(cache_dir)
        self.knowledge_base: Dict[str, EmbeddedContent] = {}
        self.index_by_module: Dict[str, List[str]] = defaultdict(list)
        self.index_by_tier: Dict[str, List[str]] = defaultdict(list)
        self.cost_tracker = CostTracker()

        # OpenAI-Client initialisieren wenn gewünscht
        self.openai_client = None
        if use_openai:
            self._init_openai()

        logger.info(f"MedicalRAGSystem initialisiert (OpenAI: {use_openai})")

    def _init_openai(self) -> None:
        """Initialisiert OpenAI-Client."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY nicht gefunden. Fallback auf lokale Embeddings.")
                self.use_openai = False
                return
            self.openai_client = OpenAI(api_key=api_key)
            logger.info("OpenAI-Client initialisiert")
        except ImportError:
            logger.warning("OpenAI-Paket nicht installiert. Fallback auf lokale Embeddings.")
            self.use_openai = False

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generiert Embedding für einen Text.

        Args:
            text: Zu embedden der Text

        Returns:
            Embedding-Vektor als Liste von Floats
        """
        # Cache prüfen
        cached = self.embedding_cache.get(text)
        if cached:
            return cached

        if self.use_openai and self.openai_client:
            return self._generate_openai_embedding(text)
        else:
            return self._generate_local_embedding(text)

    def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generiert Embedding über OpenAI API."""
        try:
            response = self.openai_client.embeddings.create(
                model=self.config.embedding_model,
                input=text[:8000]  # Max Input-Länge
            )
            embedding = response.data[0].embedding

            # Kosten tracken
            tokens = response.usage.total_tokens
            self.cost_tracker.add_usage(tokens, self.config.cost_per_1m_tokens)

            # Cache speichern
            self.embedding_cache.set(text, embedding)

            return embedding

        except Exception as e:
            logger.error(f"OpenAI Embedding-Fehler: {e}")
            return self._generate_local_embedding(text)

    def _generate_local_embedding(self, text: str) -> List[float]:
        """
        Generiert lokales Embedding (deterministisch für Konsistenz).

        Hinweis: Für Produktion sollte ein echtes Embedding-Modell
        wie sentence-transformers verwendet werden.
        """
        # Deterministisches Embedding basierend auf Text-Hash
        np.random.seed(hash(text) % (2**32))
        embedding = np.random.randn(self.config.embedding_dimension).tolist()

        # Normalisieren
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = (np.array(embedding) / norm).tolist()

        # Cache speichern
        self.embedding_cache.set(text, embedding)

        return embedding

    def add_to_knowledge_base(
        self,
        texts: Union[str, List[str]],
        source_module: str,
        source_tier: str = "tier1_gold",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Fügt Texte zur Wissensbasis hinzu.

        Args:
            texts: Einzelner Text oder Liste von Texten
            source_module: Quellmodul (z.B. "gold_standard", "leitlinien")
            source_tier: "tier1_gold" oder "tier2_bibliothek"
            metadata: Zusätzliche Metadaten

        Returns:
            Anzahl hinzugefügter Einträge
        """
        if isinstance(texts, str):
            texts = [texts]

        added = 0
        for text in texts:
            if not text or len(text.strip()) < 10:
                continue

            embedding = self.generate_embedding(text)
            content_id = f"{source_module}_{hashlib.md5(text.encode()).hexdigest()[:12]}"

            content = EmbeddedContent(
                content_id=content_id,
                text=text,
                embedding=embedding,
                metadata=metadata or {},
                source_module=source_module,
                source_tier=source_tier,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S")
            )

            self.knowledge_base[content_id] = content
            self.index_by_module[source_module].append(content_id)
            self.index_by_tier[source_tier].append(content_id)
            added += 1

        logger.info(f"{added} Einträge zur Wissensbasis hinzugefügt ({source_module}, {source_tier})")
        return added

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        source_modules: Optional[List[str]] = None,
        source_tiers: Optional[List[str]] = None,
        min_similarity: Optional[float] = None,
        prioritize_tier1: bool = True
    ) -> List[SearchResult]:
        """
        Semantische Suche in der Wissensbasis.

        Args:
            query: Suchanfrage
            top_k: Anzahl der Top-Ergebnisse
            source_modules: Filter nach Quellmodulen
            source_tiers: Filter nach Tiers
            min_similarity: Minimum Ähnlichkeit
            prioritize_tier1: Tier1 (Gold-Standard) priorisieren

        Returns:
            Liste von SearchResult, sortiert nach Ähnlichkeit
        """
        if not self.knowledge_base:
            logger.warning("Wissensbasis ist leer")
            return []

        top_k = top_k or self.config.top_k
        min_similarity = min_similarity or self.config.similarity_threshold

        # Query Embedding
        query_embedding = self.generate_embedding(query)
        query_vector = np.array(query_embedding)

        # Ähnlichkeiten berechnen
        similarities: List[Tuple[str, float]] = []

        for content_id, content in self.knowledge_base.items():
            # Filter anwenden
            if source_modules and content.source_module not in source_modules:
                continue
            if source_tiers and content.source_tier not in source_tiers:
                continue

            content_vector = np.array(content.embedding)
            similarity = self._cosine_similarity(query_vector, content_vector)

            # Tier1 Bonus wenn priorisiert
            if prioritize_tier1 and content.source_tier == "tier1_gold":
                similarity *= 1.1  # 10% Bonus für Gold-Standard

            if similarity >= min_similarity:
                similarities.append((content_id, similarity))

        # Sortieren nach Ähnlichkeit
        similarities.sort(key=lambda x: x[1], reverse=True)

        # SearchResults erstellen
        results: List[SearchResult] = []
        for rank, (content_id, similarity) in enumerate(similarities[:top_k], 1):
            content = self.knowledge_base[content_id]
            results.append(SearchResult(
                content_id=content_id,
                text=content.text,
                similarity_score=min(1.0, similarity),  # Cap bei 1.0
                metadata=content.metadata,
                source_module=content.source_module,
                source_tier=content.source_tier,
                rank=rank
            ))

        logger.info(f"Suche: {len(results)} Ergebnisse für '{query[:50]}...'")
        return results

    def get_context_for_question(
        self,
        question: str,
        max_context_length: int = 3000,
        include_tier2: bool = False
    ) -> Dict[str, Any]:
        """
        Holt relevanten Kontext für eine Frage.

        Args:
            question: Die Frage
            max_context_length: Maximale Kontextlänge in Zeichen
            include_tier2: Auch Tier2 (Bibliothek) einbeziehen

        Returns:
            Dictionary mit Kontext, Quellen und Metadaten
        """
        # Erst Tier1 durchsuchen
        tier1_results = self.search(
            query=question,
            top_k=self.config.top_k,
            source_tiers=["tier1_gold"],
            min_similarity=0.5
        )

        # Optional Tier2 hinzufügen
        tier2_results = []
        if include_tier2 and len(tier1_results) < 3:
            tier2_results = self.search(
                query=question,
                top_k=self.config.top_k - len(tier1_results),
                source_tiers=["tier2_bibliothek"],
                min_similarity=0.5
            )

        all_results = tier1_results + tier2_results

        # Kontext zusammenbauen
        context_parts: List[str] = []
        sources: List[Dict[str, Any]] = []
        current_length = 0

        for result in all_results:
            if current_length + len(result.text) > max_context_length:
                break

            context_parts.append(result.text)
            sources.append({
                "content_id": result.content_id,
                "source_module": result.source_module,
                "source_tier": result.source_tier,
                "similarity": round(result.similarity_score, 3),
                "rank": result.rank
            })
            current_length += len(result.text)

        return {
            "question": question,
            "context": context_parts,
            "context_combined": "\n\n".join(context_parts),
            "sources": sources,
            "tier1_count": len(tier1_results),
            "tier2_count": len(tier2_results),
            "total_context_length": current_length
        }

    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Berechnet Cosinus-Ähnlichkeit zwischen zwei Vektoren."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken über die Wissensbasis zurück."""
        return {
            "total_items": len(self.knowledge_base),
            "by_module": {
                module: len(ids)
                for module, ids in self.index_by_module.items()
            },
            "by_tier": {
                tier: len(ids)
                for tier, ids in self.index_by_tier.items()
            },
            "cache_size": len(self.embedding_cache.cache),
            "cost_summary": self.cost_tracker.get_summary()
        }

    def save_knowledge_base(self, path: str) -> None:
        """Speichert die Wissensbasis als JSON."""
        data = {
            "knowledge_base": {
                k: v.to_dict() for k, v in self.knowledge_base.items()
            },
            "statistics": self.get_statistics(),
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Wissensbasis gespeichert: {path}")

    def load_knowledge_base(self, path: str) -> None:
        """Lädt eine Wissensbasis aus JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        kb_data = data.get("knowledge_base", {})
        for content_id, content_dict in kb_data.items():
            content = EmbeddedContent(**content_dict)
            self.knowledge_base[content_id] = content
            self.index_by_module[content.source_module].append(content_id)
            self.index_by_tier[content.source_tier].append(content_id)

        logger.info(f"Wissensbasis geladen: {len(self.knowledge_base)} Einträge")


# Global instance
_rag_system: Optional[MedicalRAGSystem] = None


def get_rag_system(
    config: Optional[RAGConfig] = None,
    use_openai: bool = False
) -> MedicalRAGSystem:
    """Gibt die globale RAG-System-Instanz zurück."""
    global _rag_system
    if _rag_system is None:
        _rag_system = MedicalRAGSystem(config, use_openai)
    return _rag_system


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)

    rag = MedicalRAGSystem(use_openai=False)

    # Test-Daten hinzufügen
    test_questions = [
        "Wie diagnostizieren Sie eine akute Pankreatitis?",
        "Welche Therapieoptionen gibt es bei Herzinsuffizienz?",
        "Was sind die Symptome eines Myokardinfarkts?",
    ]

    rag.add_to_knowledge_base(
        test_questions,
        source_module="gold_standard",
        source_tier="tier1_gold"
    )

    # Suche testen
    results = rag.search("Pankreatitis Diagnose", top_k=3)

    print("\n=== Suchergebnisse ===")
    for r in results:
        print(f"[{r.rank}] Score: {r.similarity_score:.3f}")
        print(f"    {r.text[:100]}...")
        print()

    print("\n=== Statistiken ===")
    print(json.dumps(rag.get_statistics(), indent=2))
