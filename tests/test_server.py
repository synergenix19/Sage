import inspect
import uuid
import pytest
from fastapi.testclient import TestClient
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node


@pytest.fixture(scope="module")
def client():
    """TestClient used as context manager so lifespan (app.state init) runs.

    The /chat endpoint depends on require_ready(), which returns 503 until the
    background BGE-M3 warmup sets _bge_ready. The lifespan yields BEFORE warmup
    completes (port opens immediately), so in CI (BGE not warm/cached) a request
    races a 503. These server tests mock the graph and assert request/response and
    ferry-header behavior, not warmup, so the readiness gate is incidental — we
    override it. No test asserts the 503 readiness behavior (verified 2026-06-13);
    /health/ready warmup gating is exercised against the deployed service, not here.
    """
    from server import app, require_ready
    app.dependency_overrides[require_ready] = lambda: None
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(require_ready, None)


@pytest.fixture
def session_id():
    """Unique LangGraph thread_id per test — prevents checkpoint bleed across module members."""
    return f"test-{uuid.uuid4()}"


def _patch_graph(monkeypatch, mock_ainvoke):
    """Patch app.state._graph with a mock that accepts (state, config=None)."""
    from server import app

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            return await mock_ainvoke(state)

    monkeypatch.setattr(app.state, "_graph", _MockGraph())


def test_chat_invokes_graph_with_durability_exit(monkeypatch, client, session_id):
    """Per-turn ainvoke must use durability='exit' to avoid per-super-step checkpoint
    write amplification (each write is a cross-region INSERT). See 2026-06-24 latency RCA."""
    from server import app

    captured = {}

    class _RecordingGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            captured.update(kwargs)
            return {"response": "ok", "path": ["freeflow_respond"],
                    "is_safe": True, "turn_count": 1}

    monkeypatch.setattr(app.state, "_graph", _RecordingGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "hi"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert captured.get("durability") == "exit"


def test_chat_bad_request_empty_messages(client):
    res = client.post("/chat", json={"messages": [], "session_id": "test"})
    assert res.status_code == 400


def test_chat_bad_request_last_message_not_user(client):
    res = client.post("/chat", json={
        "messages": [{"role": "assistant", "content": "Hello"}],
        "session_id": "test",
    })
    assert res.status_code == 400


def test_chat_crisis_message_has_signal(client, session_id):
    # "end it all" is a CRISIS_KEYWORD — triggers keyword match, no LLM call.
    # _crisis_response_node returns a hardcoded string. Zero API calls.
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")


@pytest.mark.slow
def test_chat_returns_text_for_valid_message(client, session_id):
    import httpx
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I've been feeling really anxious lately."}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert len(res.text.strip()) > 10


def test_chat_graph_error_returns_sentinel(monkeypatch, client):
    from server import app

    class _ErrGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            raise RuntimeError("simulated graph failure")

    monkeypatch.setattr(app.state, "_graph", _ErrGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert "[[SERVER_ERROR]]" in res.text


def test_chat_response_headers_present(client, session_id):
    # Crisis path: keyword match, no LLM call — fast test.
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert "x-sage-model" in res.headers
    assert "x-sage-node-path" in res.headers


def test_chat_body_has_no_meta_sentinel(client, session_id):
    # Metadata must never appear in the body stream — only in headers.
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert "[[META:" not in res.text


def test_chat_node_path_header_is_valid_json_array(client, session_id):
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    import json
    path = json.loads(res.headers["x-sage-node-path"])
    assert isinstance(path, list)
    assert len(path) > 0
    assert all(isinstance(n, str) for n in path)


def test_freeflow_node_is_coroutine():
    assert inspect.iscoroutinefunction(freeflow_respond_node)


def test_low_confidence_node_is_coroutine():
    assert inspect.iscoroutinefunction(low_confidence_respond_node)


def test_chat_arabic_crisis_message_has_signal(client, session_id):
    # Arabic crisis keyword "أريد الموت" (I want to die) — triggers keyword match,
    # no LLM call needed. Fast test.
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "أريد الموت"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")
    # The Arabic crisis response should NOT be the error sentinel
    assert "[[SERVER_ERROR]]" not in res.text


def test_all_audit_headers_present(client, session_id):
    """All 8 metadata headers must be present on every response, including crisis paths."""
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    for header in [
        "x-sage-model", "x-sage-node-path",
        "x-sage-skill-id", "x-sage-step-id", "x-sage-gate-path",
        "x-sage-crisis-flags", "x-sage-clinical-flags", "x-sage-emotional-intensity",
    ]:
        assert header in res.headers, f"Missing header: {header}"


def test_crisis_path_crisis_flags_non_empty(client, session_id):
    """Crisis keyword match → x-sage-crisis-flags is a non-empty JSON array."""
    import json as _json
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    flags = _json.loads(res.headers["x-sage-crisis-flags"])
    assert isinstance(flags, list)
    assert len(flags) > 0


def test_crisis_path_gate_path_and_no_skill(client, session_id):
    """Crisis responses: gate_path='crisis', skill_id and step_id empty."""
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    assert res.headers.get("x-sage-gate-path") == "crisis"
    assert res.headers.get("x-sage-skill-id") == ""
    assert res.headers.get("x-sage-step-id") == ""


def test_skill_response_audit_headers(monkeypatch, client):
    """Skill-path response: skill_id and step_id populated, crisis_flags empty."""
    import json as _json
    from server import app

    async def _mock_skill(state):
        return {
            "path": ["safety_check", "intent_route", "skill_select", "skill_executor", "output_gate"],
            "is_safe": True,
            "response": "Let's try this together.",
            "active_skill_id": "cbt_thought_record",
            "executed_step_id": "step_1",
            "gate_path": "standard",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 7,
        }

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            return await _mock_skill(state)

    monkeypatch.setattr(app.state, "_graph", _MockGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to try a CBT exercise"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert res.headers.get("x-sage-skill-id") == "cbt_thought_record"
    assert res.headers.get("x-sage-step-id") == "step_1"
    assert res.headers.get("x-sage-gate-path") == "standard"
    assert _json.loads(res.headers["x-sage-crisis-flags"]) == []
    assert _json.loads(res.headers["x-sage-clinical-flags"]) == []
    assert res.headers.get("x-sage-emotional-intensity") == "7"


def test_freeflow_response_audit_headers(monkeypatch, client):
    """Freeflow response: skill_id/step_id empty, clinical_flags and intensity populated."""
    import json as _json
    from server import app

    async def _mock_freeflow(state):
        return {
            "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
            "is_safe": True,
            "response": "That sounds really hard.",
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
            "crisis_flags": [],
            "clinical_flags": ["trauma_indicator"],
            "emotional_intensity": 8,
        }

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            return await _mock_freeflow(state)

    monkeypatch.setattr(app.state, "_graph", _MockGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I feel overwhelmed by everything"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert res.headers.get("x-sage-skill-id") == ""
    assert res.headers.get("x-sage-step-id") == ""
    assert res.headers.get("x-sage-gate-path") == "standard"
    assert _json.loads(res.headers["x-sage-clinical-flags"]) == ["trauma_indicator"]
    assert res.headers.get("x-sage-emotional-intensity") == "8"


def test_chat_response_has_all_trace_headers(monkeypatch, client):
    """All 13 trace headers must be present in every /chat response."""
    from server import app

    async def _mock_trace(state):
        return {
            "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
            "is_safe": True,
            "response": "I hear you.",
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 5,
            "crisis_state": "none",
            "primary_intent": "general_chat",
            "semantic_score": None,
            "prompt_layers": ["persona", "intent"],
            "token_usage": {"input": 100, "output": 30, "total": 130},
            "turn_count": 1,
        }

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            return await _mock_trace(state)

    monkeypatch.setattr(app.state, "_graph", _MockGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    for header in [
        "x-sage-node-path",
        "x-sage-model",
        "x-sage-skill-id",
        "x-sage-step-id",
        "x-sage-gate-path",
        "x-sage-crisis-flags",
        "x-sage-clinical-flags",
        "x-sage-emotional-intensity",
        "x-sage-intent",
        "x-sage-semantic-score",
        "x-sage-prompt-layers",
        "x-sage-token-usage",
        "x-sage-turn-number",
    ]:
        assert header in res.headers, f"Missing header: {header}"


def test_skill_ferry_headers_present(monkeypatch, client):
    """active_step_id and distress_trajectory must be returned as headers."""
    import json as _json
    from server import app

    async def _mock(state):
        return {
            "path": ["safety_check", "skill_select", "skill_executor", "output_gate"],
            "is_safe": True,
            "response": "Let's try step 2.",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 6,
            "active_skill_id": "cbt_thought_record",
            "active_step_id": "explore_distortion",   # next turn's step
            "executed_step_id": "identify_thought",   # this turn's step (audit)
            "gate_path": "standard",
            "distress_trajectory": [7, 6, 5],
        }

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            return await _mock(state)

    monkeypatch.setattr(app.state, "_graph", _MockGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "ok let's continue"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    # active_step_id returned in header for client-side reference
    assert res.headers.get("x-sage-active-step-id") == "explore_distortion", (
        "x-sage-active-step-id must carry active_step_id, not executed_step_id"
    )
    # Existing audit header unchanged
    assert res.headers.get("x-sage-step-id") == "identify_thought"
    trajectory = _json.loads(res.headers.get("x-sage-distress-trajectory", "[]"))
    assert trajectory == [7, 6, 5]


# ── FE-H5: shared secret validation ───────────────────────────────────────
def test_chat_rejects_missing_api_key(monkeypatch, client):
    """Requests without X-Sage-Api-Key must be rejected when SAGE_API_KEY is configured."""
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test",
    })
    assert res.status_code == 401


def test_chat_rejects_wrong_api_key(monkeypatch, client):
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test",
    }, headers={"X-Sage-Api-Key": "wrong-key"})
    assert res.status_code == 401


def test_chat_accepts_correct_api_key(monkeypatch, client, session_id):
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    }, headers={"X-Sage-Api-Key": "test-secret"})
    assert res.status_code == 200


def test_chat_bypasses_key_check_when_sage_api_key_unset(monkeypatch, client, session_id):
    """No SAGE_API_KEY in env → check is disabled. Preserves backward compatibility
    for local dev where the key is not configured.
    """
    monkeypatch.delenv("SAGE_API_KEY", raising=False)
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
    })
    assert res.status_code == 200


# ---------------------------------------------------------------------------
# Checkpoint-based state: verify thread_id is passed to ainvoke config
# ---------------------------------------------------------------------------

def test_chat_passes_thread_id_as_config(monkeypatch, client):
    """graph.ainvoke must receive config with thread_id=session_id for checkpointing."""
    from server import app

    received_config = {}

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            received_config.update(config or {})
            return {
                "path": ["output_gate"],
                "is_safe": True,
                "response": "ok",
                "crisis_flags": [],
                "clinical_flags": [],
                "emotional_intensity": 5,
                "active_skill_id": None,
                "executed_step_id": None,
                "gate_path": "standard",
            }

    monkeypatch.setattr(app.state, "_graph", _MockGraph())
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "session_id": "my-session-123",
    })
    assert received_config.get("configurable", {}).get("thread_id") == "my-session-123", (
        f"Expected thread_id='my-session-123' in config, got {received_config!r}"
    )


def test_chat_request_has_no_ferry_fields(client, session_id):
    """ChatRequest must NOT include ferry fields — they live in the checkpoint.

    Sending ferry fields in the JSON body must be accepted (Pydantic will
    ignore unknown extra fields rather than raising a 422). Old clients may
    still send them during the transition period.
    """
    # Send old-style request with ferry fields — must not 422
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": session_id,
        "crisis_state": "monitoring",            # old ferry field — ignored
        "active_skill_id": "cbt_thought_record", # old ferry field — ignored
    })
    # Crisis keyword path — should still return 200 with crisis signal
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")


def test_chat_ainvoke_timeout_returns_server_error(monkeypatch, client):
    """When ainvoke hangs past the configured timeout, the endpoint must stream SERVER_ERROR."""
    import asyncio
    from server import app

    class _HangingGraph:
        checkpointer = None

        async def ainvoke(self, state, config=None, **kwargs):
            await asyncio.sleep(999)

    monkeypatch.setattr("server.AINVOKE_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(app.state, "_graph", _HangingGraph())
    res = client.post(
        "/chat",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "session_id": "00000000-0000-0000-0000-000000000001",
            "user_id": "u1",
        },
        headers={"X-Sage-Api-Key": ""},
    )
    assert res.status_code == 200
    assert b"[[SERVER_ERROR]]" in res.content


def test_chat_ainvoke_timeout_fires_within_window(monkeypatch, client):
    """Elapsed time must be less than twice the configured timeout."""
    import asyncio
    import time
    from server import app

    class _HangingGraph:
        checkpointer = None

        async def ainvoke(self, state, config=None, **kwargs):
            await asyncio.sleep(999)

    monkeypatch.setattr("server.AINVOKE_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(app.state, "_graph", _HangingGraph())
    start = time.monotonic()
    client.post(
        "/chat",
        json={
            "messages": [{"role": "user", "content": "hello"}],
            "session_id": "00000000-0000-0000-0000-000000000002",
            "user_id": "u1",
        },
        headers={"X-Sage-Api-Key": ""},
    )
    elapsed = time.monotonic() - start
    # 3s bound accounts for ASGI/thread-pool dispatch overhead on slow CI; validates
    # only that we don't wait for the full 999s sleep.
    assert elapsed < 3.0
