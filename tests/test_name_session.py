"""Tests for POST /name-session endpoint."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


def _make_pool(name_row: dict | None, execute_ok: bool = True):
    """Build a minimal asyncpg pool mock."""
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=name_row)
    pool.execute = AsyncMock(return_value="UPDATE 1" if execute_ok else None)
    return pool


def _make_llm_response(text: str):
    msg = MagicMock()
    msg.content = text
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=msg)
    return llm


@pytest.mark.asyncio
async def test_name_session_generates_and_saves_name():
    """When session has no name, LLM generates one and DB is updated."""
    from server import app

    app.state._db_pool = _make_pool({"name": None})

    with patch("server.get_classifier", return_value=_make_llm_response("Feeling Overwhelmed At Work")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/name-session", json={
                "session_id": "sess-001",
                "user_id": "user-001",
                "message": "I've been so stressed at work lately",
            })

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["name"] == "Feeling Overwhelmed At Work"
    app.state._db_pool.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_name_session_skips_when_already_named():
    """When session already has a name, endpoint returns skipped and makes no LLM call."""
    from server import app

    app.state._db_pool = _make_pool({"name": "Existing Title"})

    with patch("server.get_classifier") as mock_get:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/name-session", json={
                "session_id": "sess-002",
                "user_id": "user-001",
                "message": "hello",
            })

    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"
    mock_get.assert_not_called()


@pytest.mark.asyncio
async def test_name_session_skips_when_no_db():
    """When no DB pool is configured, returns skipped without error."""
    from server import app

    app.state._db_pool = None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/name-session", json={
            "session_id": "sess-003",
            "user_id": "user-001",
            "message": "hello",
        })

    assert resp.status_code == 200
    assert resp.json()["status"] == "skipped"


@pytest.mark.asyncio
async def test_name_session_falls_back_to_message_truncation_on_llm_failure():
    """When LLM raises, name falls back to first 30 chars of message."""
    from server import app

    app.state._db_pool = _make_pool({"name": None})
    failing_llm = MagicMock()
    failing_llm.ainvoke = AsyncMock(side_effect=Exception("LLM timeout"))

    with patch("server.get_classifier", return_value=failing_llm):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/name-session", json={
                "session_id": "sess-004",
                "user_id": "user-001",
                "message": "I've been feeling really anxious and overwhelmed",
            })

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["name"] == "I've been feeling really anxio"


@pytest.mark.asyncio
async def test_name_session_requires_auth_when_api_key_set(monkeypatch):
    """When SAGE_API_KEY env var is set, missing key returns 401.

    monkeypatch.setenv modifies os.environ directly, which works because the endpoint
    reads os.environ.get("SAGE_API_KEY", "") at call time (not at import time). If the
    key lookup is ever hoisted to module level for caching, this test will silently pass
    even when auth is broken — extract the key check into a testable function at that point.
    """
    from server import app

    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    app.state._db_pool = _make_pool({"name": None})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/name-session", json={
            "session_id": "sess-005",
            "user_id": "user-001",
            "message": "hello",
        })

    assert resp.status_code == 401
