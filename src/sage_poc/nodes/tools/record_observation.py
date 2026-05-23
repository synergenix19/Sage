"""LLM-callable tool: record a per-turn clinical observation (v7 §6.5.4).

Captures insight events, progress signals, agency signals, and context updates
in real time — things a post-session extractor would miss because they're
momentary (e.g., 'user identified their own distortion without prompting').

Low-confidence observations are also forwarded to the clinician review queue
rather than silently stored as confirmed facts.
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from langchain_core.tools import tool

_log = logging.getLogger(__name__)

_VALID_OBSERVATION_TYPES = {"insight", "progress", "agency", "context_update", "concern"}
_VALID_CONFIDENCE = {"high", "medium", "low"}


def _get_notifier(pool):
    if pool is None:
        return None
    from sage_poc.memory.notification import PostgresNotifier
    return PostgresNotifier(pool)


def make_record_tool(
    user_id: str,
    pool,
    session_id: str = "",
    repo_override=None,  # for testing
):
    """Return a record_observation @tool with user_id injected."""

    def _get_repo():
        if repo_override:
            return repo_override
        if pool is None:
            return None
        from sage_poc.memory.postgres_repository import PostgresMemoryRepository
        return PostgresMemoryRepository(pool)

    @tool
    async def record_observation(
        observation: str,
        observation_type: str,
        confidence: str,
    ) -> str:
        """Record a clinical observation about this user for cross-session continuity.

        Call this when you notice: the user identified their own cognitive distortion
        (insight), a technique worked or mood shifted (progress), the user set a goal
        or took agency (agency), or a life circumstance changed (context_update).

        Args:
            observation:      What you observed (factual, 1-2 sentences).
            observation_type: One of: insight, progress, agency, context_update, concern.
            confidence:       'high' (explicitly stated), 'medium' (likely), or 'low' (inferred).
                              Low-confidence observations are flagged for clinician review.
        """
        if observation_type not in _VALID_OBSERVATION_TYPES:
            return f"invalid observation_type: {observation_type}"
        if confidence not in _VALID_CONFIDENCE:
            confidence = "low"

        repo = _get_repo()
        if repo is None:
            return "repo_unavailable"

        try:
            existing = await repo.get_therapeutic_profile(user_id) or {}
            observations = existing.get("observations", [])
            observations.append({
                "text":              observation,
                "type":              observation_type,
                "confidence":        confidence,
                "recorded_at":       datetime.now(timezone.utc).isoformat(),
            })
            observations = observations[-50:]  # cap to last 50

            existing["observations"] = observations
            await repo.upsert_therapeutic_profile(
                user_id=user_id,
                profile=existing,
                session_id=session_id,
            )

            # Low-confidence observations go to clinician review (v7 §6.5.4)
            if confidence == "low" and session_id:
                notifier = _get_notifier(pool)
                if notifier:
                    try:
                        await notifier.notify_review_required(
                            user_id=user_id,
                            session_id=session_id,
                            reason=f"low-confidence observation: {observation[:100]}",
                            source="llm_flag_for_review",
                            payload={"observation_type": observation_type},
                        )
                    except Exception as exc:
                        _log.warning("[record_observation] notify failed: %s", exc)

            return "recorded"
        except Exception as exc:
            _log.error("[record_observation] failed: %s", exc)
            return "error"

    return record_observation
