"""S1-1b — compensating offer void after an errored offer-creating turn.

Invariant: user-visible offer <=> promotable state. When graph.ainvoke times out
or errors on a turn whose checkpoint persisted an offer created THAT turn
("skill_offer_made" in the persisted per-turn path), the client got
[[SERVER_ERROR]] and never saw the offer — yet the next turn would promote it
(observed live, audit session e-r5-box T1).

The /chat error handlers run best-effort cleanup via
sage_poc.server_helpers._void_unseen_offer(graph, session_id), which clears
offered_skill_ids through graph.aupdate_state. Cleanup failure must never mask
the original error response.
"""
import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from server import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def session_id():
    return f"test-{uuid.uuid4()}"


class _StubCheckpointer:
    """Minimal AsyncPostgresSaver stand-in: aget returns a fixed checkpoint."""

    def __init__(self, channel_values):
        self._channel_values = channel_values
        self.aget_calls = []

    async def aget(self, config):
        self.aget_calls.append(config)
        return {"channel_values": dict(self._channel_values)}


class _FailingGraph:
    """Graph whose ainvoke raises; carries a stub checkpointer + aupdate_state mock."""

    def __init__(self, checkpointer, exc):
        self.checkpointer = checkpointer
        self._exc = exc
        self.aupdate_state = AsyncMock()

    async def ainvoke(self, state, config=None):
        raise self._exc


def _post_chat(client, session_id):
    return client.post("/chat", json={
        "messages": [{"role": "user", "content": "I keep worrying about everything"}],
        "session_id": session_id,
    })


def test_timeout_on_offer_creating_turn_voids_offer(monkeypatch, client, session_id):
    """ainvoke timeout + checkpoint holding a this-turn offer -> cleanup clears
    offered_skill_ids via aupdate_state, and the endpoint still errors."""
    from server import app

    checkpointer = _StubCheckpointer({
        "offered_skill_ids": ["worry_time"],
        "path": ["safety_check", "intent_route", "skill_select",
                 "skill_offer_made", "freeflow_respond"],
    })
    graph = _FailingGraph(checkpointer, asyncio.TimeoutError())
    monkeypatch.setattr(app.state, "_graph", graph)

    res = _post_chat(client, session_id)

    assert res.status_code == 200
    assert "[[SERVER_ERROR]]" in res.text, "error response must still reach the client"

    assert graph.aupdate_state.await_count == 1, (
        "compensating cleanup must clear the unseen offer via aupdate_state"
    )
    args = graph.aupdate_state.await_args.args
    assert args[0] == {"configurable": {"thread_id": session_id}}
    assert args[1] == {"offered_skill_ids": None}


def test_generic_error_on_offer_creating_turn_voids_offer(monkeypatch, client, session_id):
    """Non-timeout graph exception on an offer-creating turn also voids the offer."""
    from server import app

    checkpointer = _StubCheckpointer({
        "offered_skill_ids": ["worry_time"],
        "path": ["safety_check", "skill_select", "skill_offer_made"],
    })
    graph = _FailingGraph(checkpointer, RuntimeError("simulated graph failure"))
    monkeypatch.setattr(app.state, "_graph", graph)

    res = _post_chat(client, session_id)

    assert "[[SERVER_ERROR]]" in res.text
    assert graph.aupdate_state.await_count == 1
    assert graph.aupdate_state.await_args.args[1] == {"offered_skill_ids": None}


def test_error_with_prior_turn_offer_does_not_void(monkeypatch, client, session_id):
    """Offer pending from an EARLIER turn (no "skill_offer_made" in the persisted
    per-turn path): the user already saw it — must NOT be cleared."""
    from server import app

    checkpointer = _StubCheckpointer({
        "offered_skill_ids": ["worry_time"],
        "path": ["safety_check", "intent_route", "freeflow_respond"],
    })
    graph = _FailingGraph(checkpointer, asyncio.TimeoutError())
    monkeypatch.setattr(app.state, "_graph", graph)

    res = _post_chat(client, session_id)

    assert "[[SERVER_ERROR]]" in res.text
    assert graph.aupdate_state.await_count == 0, (
        "prior-turn offer must survive an errored later turn"
    )


def test_cleanup_failure_does_not_mask_error_response(monkeypatch, client, session_id):
    """Checkpoint access blowing up during cleanup must not mask [[SERVER_ERROR]]."""
    from server import app

    class _BrokenCheckpointer:
        async def aget(self, config):
            raise RuntimeError("checkpoint store unavailable")

    graph = _FailingGraph(_BrokenCheckpointer(), asyncio.TimeoutError())
    monkeypatch.setattr(app.state, "_graph", graph)

    res = _post_chat(client, session_id)

    assert res.status_code == 200
    assert "[[SERVER_ERROR]]" in res.text


# ---- helper-level unit tests (the exact function the handlers call) ----------

@pytest.mark.asyncio
async def test_void_unseen_offer_helper_clears_offer():
    from sage_poc.server_helpers import _void_unseen_offer

    checkpointer = _StubCheckpointer({
        "offered_skill_ids": ["worry_time"],
        "path": ["skill_select", "skill_offer_made"],
    })
    graph = _FailingGraph(checkpointer, RuntimeError("unused"))

    await _void_unseen_offer(graph, "sess-1")

    graph.aupdate_state.assert_awaited_once_with(
        {"configurable": {"thread_id": "sess-1"}},
        {"offered_skill_ids": None},
    )


@pytest.mark.asyncio
async def test_void_unseen_offer_helper_noop_without_checkpointer():
    from sage_poc.server_helpers import _void_unseen_offer

    graph = _FailingGraph(None, RuntimeError("unused"))
    await _void_unseen_offer(graph, "sess-1")  # must not raise
    graph.aupdate_state.assert_not_awaited()
