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

# Observation types that modify the cross-session therapeutic profile in ways that affect
# future skill selection or prompt injection. Writes of these types always go to clinician
# review regardless of confidence — they cannot be silently persisted by the LLM alone.
_PROFILE_MODIFYING_TYPES = {"concern"}
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

            # Audit entry on every profile write — this write has no session_audit row
            # (it originates from freeflow tool use, not output_gate). Log structured
            # data so operators can reconstruct what changed and when.
            _log.info(
                "[record_observation] profile_write user=%s session=%s type=%s confidence=%s observation=%.120s",
                user_id, session_id, observation_type, confidence, observation,
            )

            # Clinician review gate:
            # - Low-confidence observations: always reviewed (uncertain facts)
            # - Profile-modifying types (concern): always reviewed regardless of confidence,
            #   because these can influence future session framing and skill selection.
            # A discretionary LLM tool call must not silently modify the therapeutic record
            # without a human review checkpoint for writes of clinical consequence.
            needs_review = (
                confidence == "low"
                or observation_type in _PROFILE_MODIFYING_TYPES
            )
            if needs_review and session_id:
                notifier = _get_notifier(pool)
                if notifier:
                    try:
                        await notifier.notify_review_required(
                            user_id=user_id,
                            session_id=session_id,
                            reason=f"{observation_type} observation ({confidence} confidence): {observation[:100]}",
                            source="llm_flag_for_review",
                            payload={"observation_type": observation_type, "confidence": confidence},
                        )
                    except Exception as exc:
                        _log.warning("[record_observation] notify failed: %s", exc)

            return "recorded"
        except Exception as exc:
            _log.error("[record_observation] failed: %s", exc)
            return "error"

    return record_observation
