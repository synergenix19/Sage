import pytest
from sage_poc.memory.notification import ReviewNotifier

def test_review_notifier_is_abstract():
    with pytest.raises(TypeError):
        ReviewNotifier()

@pytest.mark.asyncio
async def test_postgres_notifier_inserts_and_notifies():
    from unittest.mock import AsyncMock, MagicMock
    from sage_poc.memory.notification import PostgresNotifier
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(),
    ))
    conn.execute = AsyncMock()
    notifier = PostgresNotifier(pool)
    await notifier.notify_review_required(
        user_id="u1", session_id="s1",
        reason="crisis_flags", source="layer1_safety",
        payload={"flags": ["suicidal_ideation"]},
    )
    assert conn.execute.await_count == 2  # INSERT + NOTIFY
