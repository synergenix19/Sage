from __future__ import annotations
import json
from abc import ABC, abstractmethod


class ReviewNotifier(ABC):
    """Abstraction over the clinician notification mechanism.

    PostgresNotifier uses standard LISTEN/NOTIFY (any Postgres host).
    Swap by writing a new subclass (email, webhook, Slack, etc.).
    """

    @abstractmethod
    async def notify_review_required(
        self,
        user_id: str,
        session_id: str,
        reason: str,
        source: str,
        payload: dict,
        severity: str = "medium",
    ) -> None:
        """Send a review notification.

        Args:
            source:   'layer1_safety' (deterministic) or 'llm_flag_for_review' (LLM-perceived).
                      Clinicians use this to understand why the session was flagged.
            severity: 'low' (daily batch), 'medium' or 'high' (notify within 4 hours). v7 §6.5.6.
        """
        ...


class PostgresNotifier(ReviewNotifier):
    """Writes to clinician_review_queue and fires pg_notify for real-time delivery."""

    CHANNEL = "clinician_review"

    def __init__(self, pool) -> None:
        self._pool = pool

    async def notify_review_required(
        self,
        user_id: str,
        session_id: str,
        reason: str,
        source: str,
        payload: dict,
        severity: str = "medium",
    ) -> None:
        message = json.dumps({
            **payload,
            "user_id": user_id, "session_id": session_id,
            "reason": reason, "source": source, "severity": severity,
        })
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO public.clinician_review_queue
                  (user_id, session_id, reason, source, severity, payload, status, flags_timeline)
                VALUES ($1, $2::uuid, $3, $4, $5, $6::jsonb, 'pending', jsonb_build_array($6::jsonb))
                ON CONFLICT (session_id) DO UPDATE SET
                  reason          = EXCLUDED.reason,
                  source          = EXCLUDED.source,
                  severity        = EXCLUDED.severity,
                  payload         = EXCLUDED.payload,
                  flags_timeline  = clinician_review_queue.flags_timeline || jsonb_build_array(EXCLUDED.payload::jsonb),
                  updated_at      = now()
                """,
                user_id, session_id, reason, source, severity, message,
            )
            await conn.execute("SELECT pg_notify($1, $2)", self.CHANNEL, message)
