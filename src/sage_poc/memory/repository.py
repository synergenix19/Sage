from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional


class MemoryRepository(ABC):
    """Provider-agnostic interface for all cross-session memory operations.

    Implement this class to swap Postgres for any other store.
    All method signatures use only standard Python types.
    user_id is always an explicit parameter — no auth.uid() equivalent.
    """

    @abstractmethod
    async def get_therapeutic_profile(self, user_id: str) -> Optional[dict]:
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
        ...

    @abstractmethod
    async def search_session_summaries(
        self,
        user_id: str,
        query_embedding: list[float],
        top_k: int = 3,
        exclude_safety_levels: list[str] | None = None,
    ) -> list[dict]:
        ...
