from __future__ import annotations
from langchain_core.tools import tool


def make_record_tool(user_id: str, session_id: str, repo_override=None):
    """Return a LangChain tool that records a structured observation to the user's profile.

    Low-confidence observations (type='concern') also trigger a clinician review notification.
    Pool and repo are resolved at call time via deferred imports to avoid circular imports.
    repo_override is for testing only — allows injecting a mock repo without touching the pool.
    """

    @tool
    async def record_observation(
        observation_type: str,
        content: str,
        confidence: float = 0.8,
    ) -> str:
        """Record a structured observation about this user for their therapeutic profile.

        Use this when you notice something clinically meaningful that should persist
        across sessions (e.g., a coping technique that worked, a disclosed life stressor).

        Args:
            observation_type: One of 'insight', 'progress', 'agency', 'context_update', 'concern'.
            content: The observation text. Be specific and clinically useful.
            confidence: Your confidence in this observation (0.0-1.0). Default 0.8.
        """
        VALID_TYPES = {"insight", "progress", "agency", "context_update", "concern"}
        if observation_type not in VALID_TYPES:
            return f"invalid observation_type '{observation_type}'; must be one of {sorted(VALID_TYPES)}"
        try:
            from server import app  # noqa: PLC0415
            from sage_poc.memory.postgres_repository import PostgresMemoryRepository  # noqa: PLC0415
            from sage_poc.memory.notification import PostgresNotifier  # noqa: PLC0415
            pool = app.state._db_pool
            if pool is None:
                return "observation skipped: database unavailable"

            repo = repo_override if repo_override is not None else PostgresMemoryRepository(pool)

            # Load current profile, cap observations at 50, append new one
            current = await repo.get_therapeutic_profile(user_id) or {}
            observations: list = current.get("observations", [])
            if len(observations) >= 50:
                observations = observations[-49:]  # keep newest 49, make room for 1 more
            observations.append({
                "type": observation_type,
                "content": content,
                "confidence": confidence,
                "session_id": session_id,
            })
            profile = {**current, "observations": observations}
            await repo.upsert_therapeutic_profile(user_id, profile, session_id)

            # Notify clinician for low-confidence 'concern' observations
            if observation_type == "concern" and confidence < 0.7:
                notifier = PostgresNotifier(pool)
                await notifier.notify(
                    session_id=session_id,
                    user_id=user_id,
                    source="llm_flag_for_review",
                    severity="medium",
                    reason=f"Low-confidence concern recorded: {content[:200]}",
                )

            return f"observation recorded: {observation_type}"
        except Exception as exc:
            return f"observation failed: {exc}"

    return record_observation
