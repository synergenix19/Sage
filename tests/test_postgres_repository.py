import pytest
from unittest.mock import AsyncMock, MagicMock
from sage_poc.memory.postgres_repository import PostgresMemoryRepository

def _make_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=conn),
        __aexit__=AsyncMock(),
    ))
    return pool, conn

@pytest.mark.asyncio
async def test_get_profile_returns_none_when_missing():
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(return_value=None)
    repo = PostgresMemoryRepository(pool)
    assert await repo.get_therapeutic_profile("u1") is None

@pytest.mark.asyncio
async def test_get_profile_returns_dict():
    pool, conn = _make_pool()
    conn.fetchrow = AsyncMock(return_value={
        "effective_techniques": ["breathing"],
        "session_count": 2,
        "cultural_preferences": {},
        "mood_trajectory": [],
        "total_skills_completed": 1,
        "last_extraction_turn": 10,
    })
    repo = PostgresMemoryRepository(pool)
    result = await repo.get_therapeutic_profile("u1")
    assert result["session_count"] == 2

@pytest.mark.asyncio
async def test_upsert_profile_writes_history_and_main():
    pool, conn = _make_pool()
    conn.execute = AsyncMock()
    repo = PostgresMemoryRepository(pool)
    await repo.upsert_therapeutic_profile(
        "u1",
        {"effective_techniques": ["grounding"], "session_count": 1,
         "cultural_preferences": {}, "mood_trajectory": [],
         "total_skills_completed": 0, "last_extraction_turn": 5},
        session_id="s1",
    )
    # Two execute calls: one for history INSERT, one for upsert
    assert conn.execute.await_count == 2
