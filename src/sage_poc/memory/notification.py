from __future__ import annotations
from abc import ABC, abstractmethod
import json


class ReviewNotifier(ABC):
    """Provider-agnostic interface for clinician review notifications.

    Implement this class to swap Postgres for any other notification backend.
    """

    @abstractmethod
    async def notify(
        self,
        session_id: str,
        user_id: str,
        source: str,  # 'layer1_safety' | 'llm_flag_for_review' | 'manual'
        severity: str,  # 'low' | 'medium' | 'high' | 'critical'
        reason: str,
    ) -> None:
        """Queue a session for clinician review.

        Args:
            session_id: Unique identifier for the session.
            user_id: Unique identifier for the user.
            source: Origin of the review request.
            severity: Review urgency level.
            reason: Human-readable explanation for the review.
        """
        ...


class PostgresNotifier(ReviewNotifier):
    """ReviewNotifier backed by asyncpg pool.

    Persists review queue to clinician_review_queue table and triggers
    real-time notification via pg_notify.
    """

    def __init__(self, pool) -> None:
        self._pool = pool

    async def notify(
        self,
        session_id: str,
        user_id: str,
        source: str,
        severity: str,
        reason: str,
    ) -> None:
        async with self._pool.acquire() as conn:
            # Upsert to review queue
            await conn.execute(
                """
                INSERT INTO clinician_review_queue
                  (session_id, user_id, source, severity, reason)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (session_id) DO UPDATE
                  SET source = EXCLUDED.source,
                      severity = EXCLUDED.severity,
                      reason = EXCLUDED.reason,
                      updated_at = now()
                """,
                session_id,
                user_id,
                source,
                severity,
                reason,
            )
            # Trigger real-time notification
            await conn.execute(
                "SELECT pg_notify($1, $2)",
                "clinician_review",
                json.dumps(
                    {
                        "session_id": session_id,
                        "source": source,
                        "severity": severity,
                    }
                ),
            )
