from __future__ import annotations
from abc import ABC, abstractmethod


class MemoryRepository(ABC):
    """Provider-agnostic interface for all cross-session memory operations.

    Implement this class to swap Postgres for any other store.
    All method signatures use only standard Python types.
    user_id is always an explicit parameter — no auth.uid() equivalent.
    """

    @abstractmethod
    async def get_therapeutic_profile(self, user_id: str) -> dict | None:
        ...

    @abstractmethod
    async def upsert_therapeutic_profile(
        self,
        user_id: str,
        profile: dict,
        session_id: str,
    ) -> None:
        """Write profile and append a versioned snapshot to history.
        session_id identifies which extraction triggered this update.
        """
        ...

    @abstractmethod
    async def save_session_summary(
        self,
        session_id: str,
        user_id: str,
        summary_text: str,
        embedding: list[float],
        safety_level: str,
        skills_used: list[str] | None = None,
        mood_score: float | None = None,
    ) -> None:
        """Persist a BGE-M3 embedded session summary. One row per session (upsert semantics).
        safety_level controls retrieval exclusion — crisis summaries are excluded by default.
        """
        ...

    @abstractmethod
    async def search_session_summaries(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 3,
        exclude_safety_levels: list[str] | None = None,
    ) -> list[dict]:
        """Return up to top_k prior session summaries similar to query_embedding.
        Each dict contains at minimum: summary_text, safety_level, similarity (float).
        exclude_safety_levels=['crisis'] is the recommended default for therapeutic retrieval.
        """
        ...

    @abstractmethod
    async def get_persisted_clinical_flags(self, user_id: str) -> list[str]:
        """Return the list of Category A clinical flags persisted across sessions.
        Returns [] if no profile row exists or the column is empty.
        """
        ...

    @abstractmethod
    async def write_persisted_clinical_flags(
        self, user_id: str, flags: list[str]
    ) -> None:
        """Upsert persisted_clinical_flags for user_id.
        Creates a minimal profile row if none exists yet.
        """
        ...
