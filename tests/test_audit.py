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


def test_build_session_audit_row_embedding_timeout_conditional():
    """F4 degradation auditability (migration 019): the embedding_timeout key rides the row
    ONLY on a turn where the fallback actually fired — a normal turn's row must stay
    byte-identical to master (no key at all, not a null), same conditional discipline as
    tiering/precedence/medical/screen."""
    from sage_poc.audit import _build_session_audit_row

    row_fired = _build_session_audit_row(make_audit_state(embedding_timeout=True))
    assert row_fired["embedding_timeout"] is True

    row_normal = _build_session_audit_row(make_audit_state())
    assert "embedding_timeout" not in row_normal

    # Falsy state value (per-turn reset writes None) must also leave the row byte-identical.
    row_reset = _build_session_audit_row(make_audit_state(embedding_timeout=None))
    assert "embedding_timeout" not in row_reset


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


def test_build_session_audit_row_gate_path_unconditional():
    """P0-7: gate_path must ride the base row on EVERY turn, not just medical/derealization
    turns. A crisis-terminal state (no medical_flags, node_path without
    derealization_response) must still carry gate_path — pre-fix this key was absent
    entirely (silent NULL on crisis/HR/screen/standard rows)."""
    from sage_poc.audit import _build_session_audit_row

    crisis_row = _build_session_audit_row(make_audit_state(
        gate_path="crisis",
        medical_flags=None,
        path=["safety_check", "crisis_response"],
    ))
    assert crisis_row["gate_path"] == "crisis"

    # Both-direction: a plain standard turn with no gate_path set must still carry the key,
    # value None (never simply absent).
    standard_row = _build_session_audit_row(make_audit_state(gate_path=None))
    assert "gate_path" in standard_row
    assert standard_row["gate_path"] is None


def _old_shape_row(state: dict) -> dict:
    """Reconstructs the pre-fix (2026-08-18 P0-7) row shape for the row-equality matrix
    below, WITHOUT importing the old audit.py: gate_path used to ride the row only inside
    the medical_flags conditional or the derealization_response conditional. Every other
    stanza is untouched by this fix (see task-4 brief), so taking the current row and
    stripping gate_path when neither old trigger held exactly reproduces the old shape.
    """
    from sage_poc.audit import _build_session_audit_row

    row = _build_session_audit_row(state)
    had_medical_flags = bool(state.get("medical_flags"))
    had_derealization = "derealization_response" in (row.get("node_path") or [])
    old_row = dict(row)
    if not (had_medical_flags or had_derealization):
        old_row.pop("gate_path", None)
    return old_row


def test_build_session_audit_row_matches_old_shape_except_gate_path():
    """Row-equality matrix (byte-identity discipline): across flag/state combinations, the
    new row must equal the old row on every key EXCEPT gate_path. This pins that the fix
    touched ONLY gate_path's placement and nothing else in the row."""
    from sage_poc.audit import _build_session_audit_row

    matrix = [
        # crisis-terminal: old row had no gate_path key at all; new row must carry it.
        make_audit_state(gate_path="crisis", medical_flags=None, path=["safety_check", "crisis_response"]),
        # plain standard turn: same as above, key newly present with value None.
        make_audit_state(gate_path=None),
        # medical turn: old row already had gate_path (unchanged trigger) — same both sides.
        make_audit_state(gate_path="medical_review", medical_flags=["chest_pain"], path=["safety_check", "medical_flag_response"]),
        # derealization terminal: old row already had gate_path via the dedicated conditional.
        make_audit_state(gate_path="derealization_referral", medical_flags=None, path=["safety_check", "derealization_response"]),
        # HR terminal, no medical_flags, no derealization: old row lacked gate_path.
        make_audit_state(gate_path="hr_stage2", medical_flags=None, path=["safety_check", "high_risk_response"], hr_branch="stage2_distress", hr_distress_score=7),
        # screen turn, no medical_flags, no derealization: old row lacked gate_path.
        make_audit_state(gate_path="screen", medical_flags=None, path=["safety_check", "screen_node"], screen_asked=True, screen_answer_class="no", screen_branch_taken="continue"),
    ]

    for state in matrix:
        new_row = _build_session_audit_row(state)
        old_row = _old_shape_row(state)

        new_keys_minus_gate = {k: v for k, v in new_row.items() if k != "gate_path"}
        old_keys_minus_gate = {k: v for k, v in old_row.items() if k != "gate_path"}
        assert new_keys_minus_gate == old_keys_minus_gate, f"non-gate_path keys diverged for state {state.get('gate_path')!r}"

        # gate_path itself: new row always carries the key; old row carries it only when
        # medical_flags or derealization_response triggered.
        assert "gate_path" in new_row
        had_medical_flags = bool(state.get("medical_flags"))
        had_derealization = "derealization_response" in (state.get("path") or [])
        if had_medical_flags or had_derealization:
            assert "gate_path" in old_row
            assert new_row["gate_path"] == old_row["gate_path"]
        else:
            assert "gate_path" not in old_row
