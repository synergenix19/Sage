"""LLM-callable tool: flag session for clinician review (v7 §6.5.6).

The LLM calls this when it perceives cumulative distress, implicit hopelessness,
or ambiguous risk that Layer 1 safety rules did not catch.
source = 'llm_flag_for_review' distinguishes this from the deterministic path.

user_id and session_id are injected via closure — the LLM only provides
the semantic 'reason' and optional 'turn_context'.
"""
from __future__ import annotations
import logging
from langchain_core.tools import tool

_log = logging.getLogger(__name__)


def _get_notifier(pool):
    if pool is None:
        return None
    from sage_poc.memory.notification import PostgresNotifier
    return PostgresNotifier(pool)


def make_flag_tool(user_id: str, session_id: str):
    """Return a flag_for_review @tool with user_id and session_id injected."""

    # Pool is resolved at call time, not at factory time — avoids import order issues
    def _pool():
        try:
            from server import app  # noqa: PLC0415
            return getattr(app.state, "_db_pool", None)
        except Exception:
            return None

    @tool
    async def flag_for_review(
        reason: str,
        severity: str = "medium",
        turn_context: str = "",
        evidence_turns: list[int] = [],
    ) -> str:
        """Flag this session for clinician review.

        Call this when you notice subtle or cumulative risk that the safety
        rules didn't catch: sustained hopelessness, indirect disclosures,
        gradual withdrawal, ambiguous statements about self-harm.

        Args:
            reason:        What you noticed (e.g. 'cumulative hopelessness over 3 turns').
            severity:      'low' (daily batch), 'medium' or 'high' (notify within 4 hours).
            turn_context:  Optional excerpt showing the pattern (1-2 sentences).
            evidence_turns: Turn numbers that support the concern.
        """
        notifier = _get_notifier(_pool())
        if notifier is None:
            return "notifier_unavailable"
        try:
            await notifier.notify_review_required(
                user_id=user_id,
                session_id=session_id,
                reason=reason,
                source="llm_flag_for_review",
                payload={"turn_context": turn_context, "evidence_turns": evidence_turns},
                severity=severity,
            )
            return "flagged"
        except Exception as exc:
            _log.error("[flag_for_review] failed: %s", exc)
            return "error"

    return flag_for_review
