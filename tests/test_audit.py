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
