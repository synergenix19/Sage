from __future__ import annotations
import re
from abc import ABC, abstractmethod
from sage_poc.knowledge.models import KnowledgeResult
from sage_poc.knowledge.rewriter import normalize_arabic_query

_ARABIC_RE = re.compile(r"[؀-ۿ]")


class KnowledgeRepository(ABC):
    """Abstract retrieval interface. Swap the _search implementation for Azure
    AI Search at production; query preprocessing (rewrite) lives here in the
    base so every backend inherits it — see 2026-07-03 rewriter-wiring spec §2."""

    async def retrieve(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        """Template method: normalize the query, then delegate to the backend."""
        searched = self._preprocess_query(query)
        result = await self._search(searched, language, top_k)
        result.query_raw = query
        result.query_searched = searched
        return result

    @staticmethod
    def _contains_arabic(text: str) -> bool:
        return bool(_ARABIC_RE.search(text or ""))

    @classmethod
    def _preprocess_query(cls, query: str) -> str:
        # Script-gated, NOT language-flag-gated: the tool path supplies an
        # LLM-authored query that can mismatch conversation-level language.
        if cls._contains_arabic(query):
            return normalize_arabic_query(query)
        return query

    @abstractmethod
    async def _search(
        self,
        query: str,
        language: str = "en",
        top_k: int = 5,
    ) -> KnowledgeResult:
        """Backend retrieval over the ALREADY-normalized query. Returns
        KnowledgeResult with abstain=True when empty."""
        ...
