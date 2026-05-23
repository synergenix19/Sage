import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from sage_poc.memory.notification import ReviewNotifier, PostgresNotifier


def make_mock_pool():
    """Create a mock asyncpg pool with proper async context manager semantics."""
    conn = AsyncMock()
    conn.execute = AsyncMock()
    pool = MagicMock()
    pool.acquire = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
    return pool, conn


@pytest.mark.asyncio
async def test_postgres_notifier_executes_insert_and_notify():
    """PostgresNotifier.notify() calls conn.execute exactly twice: INSERT and pg_notify."""
    pool, conn = make_mock_pool()
    notifier = PostgresNotifier(pool)

    await notifier.notify(
        session_id="session-123",
        user_id="user-456",
        source="layer1_safety",
        severity="high",
        reason="Safety threshold exceeded",
    )

    # Assert execute was called exactly twice
    assert conn.execute.call_count == 2

    # Assert first call contains INSERT
    first_call_sql = conn.execute.call_args_list[0][0][0]
    assert "INSERT INTO clinician_review_queue" in first_call_sql

    # Assert second call contains pg_notify
    second_call_sql = conn.execute.call_args_list[1][0][0]
    assert "pg_notify" in second_call_sql


@pytest.mark.asyncio
async def test_postgres_notifier_passes_correct_args():
    """PostgresNotifier.notify() passes correct positional args to first execute call."""
    pool, conn = make_mock_pool()
    notifier = PostgresNotifier(pool)

    session_id = "sess-xyz"
    user_id = "user-abc"
    source = "llm_flag_for_review"
    severity = "critical"
    reason = "Crisis detected"

    await notifier.notify(
        session_id=session_id,
        user_id=user_id,
        source=source,
        severity=severity,
        reason=reason,
    )

    # Get first execute call (INSERT)
    first_call_args = conn.execute.call_args_list[0][0]
    # Args are: (sql_string, $1, $2, $3, $4, $5)
    assert first_call_args[1] == session_id
    assert first_call_args[2] == user_id
    assert first_call_args[3] == source
    assert first_call_args[4] == severity
    assert first_call_args[5] == reason


@pytest.mark.asyncio
async def test_postgres_notifier_notify_json_contains_session_id():
    """The JSON string in the second execute call (pg_notify) contains session_id."""
    pool, conn = make_mock_pool()
    notifier = PostgresNotifier(pool)

    session_id = "sess-final-test"

    await notifier.notify(
        session_id=session_id,
        user_id="user-xyz",
        source="manual",
        severity="medium",
        reason="Manual review requested",
    )

    # Get second execute call (pg_notify)
    second_call_args = conn.execute.call_args_list[1][0]
    # Args are: (sql_string, "clinician_review", json_string)
    json_string = second_call_args[2]
    payload = json.loads(json_string)

    assert payload["session_id"] == session_id


def test_reviewnotifier_is_abstract():
    """ReviewNotifier cannot be instantiated directly."""
    with pytest.raises(TypeError):
        ReviewNotifier()
