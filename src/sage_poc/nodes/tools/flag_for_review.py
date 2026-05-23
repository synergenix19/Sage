from __future__ import annotations
from langchain_core.tools import tool
from sage_poc.memory.notification import PostgresNotifier


def make_flag_tool(user_id: str, session_id: str):
    """Return a LangChain tool that queues the current session for clinician review.

    Source is always 'llm_flag_for_review' — set by the LLM when it detects
    concern that doesn't trigger the deterministic Layer 1 safety path.
    Pool is resolved at call time via deferred import to avoid circular imports.
    """

    @tool
    async def flag_for_review(reason: str, severity: str = "medium") -> str:
        """Flag this session for clinician review.

        Use when you detect concerning content that warrants professional attention
        but does not trigger immediate crisis protocol.

        Args:
            reason: Clear explanation of the concern warranting review.
            severity: One of 'low', 'medium', 'high', 'critical'. Default 'medium'.
        """
        try:
            from server import app  # noqa: PLC0415
            pool = app.state._db_pool
            if pool is None:
                return "review flag skipped: database unavailable"
            notifier = PostgresNotifier(pool)
            await notifier.notify(
                session_id=session_id,
                user_id=user_id,
                source="llm_flag_for_review",
                severity=severity,
                reason=reason,
            )
            return "flagged for review"
        except Exception as exc:
            return f"review flag failed: {exc}"

    return flag_for_review
