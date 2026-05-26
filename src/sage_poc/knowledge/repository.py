from __future__ import annotations
from abc import ABC, abstractmethod
from sage_poc.knowledge.models import KnowledgeResult


class KnowledgeRepository(ABC):
    """Abstract retrieval interface. Swap implementation for Azure AI Search at production."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        """Return top-k passages for query. Returns KnowledgeResult with abstain=True when empty."""
        ...
