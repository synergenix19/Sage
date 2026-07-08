import asyncio
import logging
import os
import httpx
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
        async def post(self, url, headers, json, **kwargs):
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
        async def post(self, url, headers, json, **kwargs):
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
async def test_write_swallows_network_error(monkeypatch, caplog):
    """A generic network error must not raise — but it must also not be quiet.
    A lost audit row is a lost audit row regardless of exception type, so this
    must log CRITICAL with the same "AUDIT FAILURE" token as an HTTPStatusError."""
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
        with caplog.at_level(logging.WARNING, logger="sage_poc.audit"):
            # Must not raise
            await audit_mod.write_session_audit(make_audit_state())

    critical_records = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert critical_records, "a dropped audit row must log CRITICAL, not lower"
    assert any("AUDIT FAILURE" in r.message for r in critical_records)


@pytest.mark.asyncio
async def test_write_connection_error_logs_critical(monkeypatch, caplog):
    """httpx.ConnectError (or any non-HTTPStatusError write failure) must be classified
    by consequence — an audit row was lost — not by exception type. It must log CRITICAL
    with the same "AUDIT FAILURE" token as an FK/HTTPStatusError drop."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    class BrokenClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            raise httpx.ConnectError("connection refused")

    with patch("httpx.AsyncClient", return_value=BrokenClient()):
        with caplog.at_level(logging.WARNING, logger="sage_poc.audit"):
            await audit_mod.write_session_audit(make_audit_state(
                session_id="conn-err-sess", turn_number=3,
            ))

    critical_records = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert critical_records, "ConnectError on write must log CRITICAL"
    assert any("AUDIT FAILURE" in r.message for r in critical_records)
    # Session/turn/user context must ride the generic-exception branch too.
    assert any("conn-err-sess" in r.message for r in critical_records)


@pytest.mark.asyncio
async def test_write_http_status_error_logs_critical(monkeypatch, caplog):
    """FK / constraint failures (HTTPStatusError) must log CRITICAL with the
    "AUDIT FAILURE" token — locks in the pre-existing branch."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    class MockResponse:
        status_code = 409
        text = "foreign key violation"
        def raise_for_status(self):
            raise httpx.HTTPStatusError("conflict", request=MagicMock(), response=self)

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, url, headers, json, **kwargs):
            return MockResponse()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        with caplog.at_level(logging.WARNING, logger="sage_poc.audit"):
            await audit_mod.write_session_audit(make_audit_state(
                session_id="fk-err-sess", turn_number=4,
            ))

    critical_records = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert critical_records, "HTTPStatusError on write must log CRITICAL"
    assert any("AUDIT FAILURE" in r.message for r in critical_records)


@pytest.mark.asyncio
async def test_precheck_warning_deduplicated(monkeypatch, caplog):
    """Sustained auth-API outage must warn ONCE on the pre-check, not per write —
    otherwise a degraded auth API turns into per-write warning spam. Fail-open
    (returns True) must be unchanged; a subsequent successful pre-check resets
    the suppression so a later failure warns again."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    class FailingClient:
        async def get(self, url, headers, **kwargs):
            raise httpx.ConnectError("auth API down")

    class OkClient:
        async def get(self, url, headers, **kwargs):
            class R:
                status_code = 200
            return R()

    with patch.object(audit_mod, "_get_audit_client", return_value=FailingClient()):
        with caplog.at_level(logging.WARNING, logger="sage_poc.audit"):
            for _ in range(5):
                result = await audit_mod._user_exists_in_auth("user-x")
                assert result is True, "fail-open behavior must be unchanged"

    warnings = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "could not verify user" in r.message
    ]
    assert len(warnings) == 1, (
        f"expected exactly one dedup'd warning across 5 failures, got {len(warnings)}"
    )

    caplog.clear()
    # A successful pre-check resets the suppression flag.
    with patch.object(audit_mod, "_get_audit_client", return_value=OkClient()):
        result = await audit_mod._user_exists_in_auth("user-x")
        assert result is True

    with patch.object(audit_mod, "_get_audit_client", return_value=FailingClient()):
        with caplog.at_level(logging.WARNING, logger="sage_poc.audit"):
            await audit_mod._user_exists_in_auth("user-x")

    warnings_after_reset = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "could not verify user" in r.message
    ]
    assert len(warnings_after_reset) == 1, (
        "a fresh failure after an intervening success must warn again"
    )


@pytest.mark.asyncio
async def test_identity_substitution_write_error_logs_critical(monkeypatch, caplog):
    """write_identity_substitution_audit drops are PDPL Art. 6 losses — both the
    HTTPStatusError branch and the generic-exception branch must log CRITICAL
    with the "AUDIT FAILURE" token, not logger.error."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    class BrokenClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw):
            raise httpx.ConnectError("connection refused")

    with patch("httpx.AsyncClient", return_value=BrokenClient()):
        with caplog.at_level(logging.WARNING, logger="sage_poc.audit"):
            await audit_mod.write_identity_substitution_audit(
                session_id="id-sub-sess",
                turn_number=1,
                rule_id="CUO-ID-001",
                original_response_hash="abc123",
                original_response_text="I am a therapist and I'm here to help.",
                substitute_with="I'm a wellness companion.",
                user_id="user-1",
            )

    critical_records = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert critical_records, "identity_substitution_audit write drop must log CRITICAL"
    assert any("AUDIT FAILURE" in r.message for r in critical_records)


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
async def test_write_skips_with_info_when_user_not_in_auth(monkeypatch, caplog):
    """user_id set but not in auth.users → INFO log, no POST to session_audit."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    post_calls = []

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, headers, **kwargs):
            # Simulate user not found in auth.users
            class R:
                status_code = 404
            return R()
        async def post(self, url, headers, json, **kwargs):
            post_calls.append(json)
            class R:
                def raise_for_status(self): pass
            return R()

    with patch("httpx.AsyncClient", return_value=MockClient()):
        import logging
        with caplog.at_level(logging.INFO, logger="sage_poc.audit"):
            await audit_mod.write_session_audit(
                make_audit_state(user_id="00000000-0000-0000-0000-001780638293")
            )

    assert post_calls == [], "must not write when user not in auth.users"
    assert any("not found in auth.users" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_write_proceeds_when_user_exists_in_auth(monkeypatch):
    """user_id set and present in auth.users → POST to session_audit fires."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")

    import importlib
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)

    post_calls = []

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def get(self, url, headers, **kwargs):
            # Simulate user found in auth.users
            class R:
                status_code = 200
            return R()
        async def post(self, url, headers, json, **kwargs):
            post_calls.append(json)
            class R:
                def raise_for_status(self): pass
            return R()

    real_uid = "a1b2c3d4-0000-0000-0000-000000000001"
    with patch("httpx.AsyncClient", return_value=MockClient()):
        await audit_mod.write_session_audit(make_audit_state(user_id=real_uid))

    assert len(post_calls) == 1, "must write when user exists in auth.users"
    assert post_calls[0]["user_id"] == real_uid


def test_build_session_audit_row_carries_served_latency_stages():
    """freeflow_gen_ms/translate_out_ms must ride the existing session_audit row
    (no second network write) — present when set on state, None when absent."""
    from sage_poc.audit import _build_session_audit_row

    row_present = _build_session_audit_row(make_audit_state(
        freeflow_gen_ms=812, translate_out_ms=143,
    ))
    assert row_present["freeflow_gen_ms"] == 812
    assert row_present["translate_out_ms"] == 143

    row_absent = _build_session_audit_row(make_audit_state())
    assert row_absent["freeflow_gen_ms"] is None
    assert row_absent["translate_out_ms"] is None


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
