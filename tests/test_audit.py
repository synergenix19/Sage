import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_audit_state(**kwargs):
    defaults = {
        "session_id": "test-session-001",
        "turn_number": 1,
        "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.92,
        "active_skill_id": None,
        "active_step_id": None,
        "skill_match_method": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "knowledge_source": "",
        "crisis_state": "none",
        "crisis_flags": [],
        "clinical_flags": [],
        "engagement": 7,
        "emotional_intensity": 4,
        "model_version": "claude-sonnet-4-6",
        "latency_ms": None,
        "user_id": None,
        "gate_path": "standard",
    }
    return {**defaults, **kwargs}


@pytest.mark.asyncio
async def test_write_skips_when_url_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    # Re-import forces module-level vars to re-read env
    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)
    # Should return without error, no HTTP call
    await audit_mod.write_session_audit(make_audit_state())


@pytest.mark.asyncio
async def test_write_posts_correct_row(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    posted_json = {}

    class MockResponse:
        def raise_for_status(self): pass

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers, json):
            posted_json.update(json)
            return MockResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        await audit_mod.write_session_audit(make_audit_state(
            session_id="sess-abc",
            turn_number=2,
            primary_intent="new_skill",
            active_skill_id="box_breathing",
            crisis_state="none",
            crisis_flags=[],
            clinical_flags=[],
        ))

    assert posted_json["session_id"] == "sess-abc"
    assert posted_json["turn_number"] == 2
    assert posted_json["primary_intent"] == "new_skill"
    assert posted_json["active_skill_id"] == "box_breathing"
    assert posted_json["node_path"] == ["safety_check", "intent_route", "freeflow_respond", "output_gate"]
    assert posted_json["crisis_state"] == "none"
    assert posted_json["crisis_flags"] == []
    assert posted_json["clinical_flags"] == []
    assert isinstance(posted_json["knowledge_passage_ids"], list)


@pytest.mark.asyncio
async def test_write_extracts_passage_ids(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    posted_json = {}

    class MockResponse:
        def raise_for_status(self): pass

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers, json):
            posted_json.update(json)
            return MockResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        await audit_mod.write_session_audit(make_audit_state(
            knowledge_passages=[
                {"source_id": "cbt-001-en-000", "text": "...", "citation": "x", "relevance_score": 0.9},
                {"source_id": "cbt-001-en-001", "text": "...", "citation": "x", "relevance_score": 0.8},
            ],
            knowledge_source="node_6",
        ))

    assert posted_json["knowledge_passage_ids"] == ["cbt-001-en-000", "cbt-001-en-001"]
    assert posted_json["knowledge_source"] == "node_6"


@pytest.mark.asyncio
async def test_write_swallows_network_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    class BrokenClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            raise ConnectionError("network down")

    with patch("httpx.AsyncClient", return_value=BrokenClient()):
        # Must not raise
        await audit_mod.write_session_audit(make_audit_state())


@pytest.mark.asyncio
async def test_output_gate_schedules_audit_write(monkeypatch):
    """output_gate must schedule a write_session_audit task."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    write_calls = []

    async def mock_write(state):
        write_calls.append(state)

    monkeypatch.setattr("sage_poc.audit.write_session_audit", mock_write)
    monkeypatch.setattr("sage_poc.nodes.output_gate.write_session_audit", mock_write)

    from sage_poc.nodes.output_gate import output_gate_node
    from tests.test_nodes import make_state  # reuse existing helper

    state = make_state(
        raw_message="hello",
        response_en="I hear you.",
        gate_path="standard",
        path=["safety_check", "intent_route", "freeflow_respond"],
        turn_number=1,
        session_id="test-sess",
        user_id=None,
    )

    await output_gate_node(state)
    # Give the event loop a tick to run the task
    await asyncio.sleep(0)
    assert len(write_calls) == 1
    assert write_calls[0].get("session_id") == "test-sess"


@pytest.mark.asyncio
async def test_crisis_response_schedules_audit_write(monkeypatch):
    """crisis_response must schedule a write_session_audit task on crisis paths."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    write_calls = []

    async def mock_write(state):
        write_calls.append(state)

    monkeypatch.setattr("sage_poc.audit.write_session_audit", mock_write)
    monkeypatch.setattr("sage_poc.graph.write_session_audit", mock_write)

    # Import graph to access _crisis_response_node
    from sage_poc import graph as graph_mod

    state = {
        "path": ["safety_check"],
        "session_id": "crisis-sess",
        "turn_number": 2,
        "detected_language": "en",
        "crisis_flags": ["S1_keyword"],
        "clinical_flags": [],
        "active_skill_id": None,
        "crisis_state": "none",
        "conversation_history": [],
        "raw_message": "I want to end it",
        "message_en": "I want to end it",
    }

    await graph_mod._crisis_response_node(state)
    await asyncio.sleep(0)
    assert len(write_calls) == 1
    assert write_calls[0].get("session_id") == "crisis-sess"
    assert "crisis_response" in write_calls[0].get("path", [])
    assert write_calls[0].get("crisis_state") == "monitoring"
