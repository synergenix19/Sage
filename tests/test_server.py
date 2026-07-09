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


# ── E2E crisis-card disposition through the HTTP entrypoint (v7.1 tiering) ─────────────────────
# The gap that let five green proof-sets coexist with flag-OFF deployed behaviour: NO test crossed
# server.py's /chat response assembly. server.py read is_safe directly and rendered the RED card on
# any is_safe=False — including a warm T1 turn (is_safe = len(crisis_flags)==0, so False whenever a
# signal fired). These mock the graph result and assert the card follows crisis_tier, not is_safe.
def _graph_result(**over):
    base = {"is_safe": True, "response": "ok", "path": [], "crisis_flags": []}
    base.update(over)
    return base


def test_chat_T1_warm_turn_emits_no_crisis_card(monkeypatch, client, session_id):
    # THE BUG: a T1 warm turn has is_safe=False (s3_semantic fired) but crisis_tier="T1" — it must
    # render the WARM reply, NOT the RED card. Reproduces the deployed prod behaviour at the HTTP layer.
    import server
    monkeypatch.setattr(server, "CRISIS_TIERING_ENABLED", True)

    async def _mock(state):
        return _graph_result(is_safe=False, crisis_tier="T1",
                             crisis_flags=["s3_semantic"], response="That sounds really heavy. I'm here with you.")
    _patch_graph(monkeypatch, _mock)
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "i am feeling hopeless"}], "session_id": session_id})
    assert res.status_code == 200
    assert not res.text.startswith("[[CRISIS_DETECTED]]"), \
        "T1 warm turn wrongly rendered the RED crisis card (server.py is_safe reader bug)"


def test_chat_T2_turn_emits_crisis_card(monkeypatch, client, session_id):
    import server
    monkeypatch.setattr(server, "CRISIS_TIERING_ENABLED", True)

    async def _mock(state):
        return _graph_result(is_safe=False, crisis_tier="T2", crisis_flags=["si_explicit"],
                             path=["safety_check", "crisis_response"], response="Please reach out now.")
    _patch_graph(monkeypatch, _mock)
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "i want to kill myself"}], "session_id": session_id})
    assert res.text.startswith("[[CRISIS_DETECTED]]")


def test_chat_flag_off_binary_card_on_unsafe(monkeypatch, client, session_id):
    # Kill-switch / legacy path: tiering OFF -> card follows is_safe (crisis_tier not computed).
    import server
    monkeypatch.setattr(server, "CRISIS_TIERING_ENABLED", False)

    async def _mock(state):
        return _graph_result(is_safe=False, crisis_tier=None, crisis_flags=["si_explicit"], response="...")
    _patch_graph(monkeypatch, _mock)
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "x"}], "session_id": session_id})
    assert res.text.startswith("[[CRISIS_DETECTED]]")


# ── REAL-graph E2E (crosses reducer AND HTTP — the boundary bug #2 + bug #1 lived at) ──────────
# The mocked tests above verify server.py's disposition; these drive the ACTUAL compiled graph so a
# regression in either the state channel (bug #2: crisis_tier dropped) OR the entrypoint (bug #1:
# card on is_safe) fails the test. This is the class-closure the whole saga was missing.
def test_chat_T2_real_graph_card_and_tier_header(client, session_id):
    # Fast (S1 keyword, no LLM): a T2 phrase -> RED card + X-Sage-Crisis-Tier: T2 through the real graph.
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}], "session_id": session_id})
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")
    assert res.headers.get("X-Sage-Crisis-Tier") == "T2", \
        f"T2 phrase did not resolve crisis_tier=T2 through the graph (bug #2 regressed?): {res.headers.get('X-Sage-Crisis-Tier')!r}"


@pytest.mark.slow
def test_chat_T1_real_graph_hopeless_warm_no_card(client, session_id):
    # THE class-closure E2E: "i am feeling hopeless" through the REAL graph (S3 semantic + freeflow).
    # crisis_tier=T1 must SURVIVE the reducer (bug #2) AND the entrypoint must render WARM, no RED card
    # (bug #1). Fails if either regresses. Slow: BGE-M3 encode + freeflow LLM.
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "i am feeling hopeless"}], "session_id": session_id})
    assert res.status_code == 200
    assert res.headers.get("X-Sage-Crisis-Tier") == "T1", \
        f"hopeless did not resolve T1 through the graph (crisis_tier dropped by reducer?): {res.headers.get('X-Sage-Crisis-Tier')!r}"
    assert not res.text.startswith("[[CRISIS_DETECTED]]"), \
        "T1 warm turn wrongly rendered the RED crisis card (entrypoint is_safe reader?)"


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


def test_health_version_exposes_skill_media_flag(monkeypatch, client):
    """/health/version must report skill_media_enabled + its raw env so the Item-3 flag flip is
    prod-OBSERVABLE (custody standard), mirroring crisis_tiering_enabled. The reported value must
    use the SAME resolution as the emit gate (_skill_media_enabled) so it can never drift from
    what actually fires."""
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    monkeypatch.setenv("SAGE_SKILL_MEDIA_ENABLED", "true")
    res = client.get("/health/version", headers={"X-Sage-Api-Key": "test-secret"})
    assert res.status_code == 200
    body = res.json()
    assert body["skill_media_enabled"] is True
    assert body["skill_media_raw_env"] == "true"

    monkeypatch.setenv("SAGE_SKILL_MEDIA_ENABLED", "")   # default-OFF
    res = client.get("/health/version", headers={"X-Sage-Api-Key": "test-secret"})
    assert res.json()["skill_media_enabled"] is False


def test_health_version_reports_crisis_copy_templated(monkeypatch, client):
    """/health/version attests whether the deployed crisis copy is TEMPLATED — a mechanism-level
    provenance signal for the byte-identical templating (build_sha can be a stale label; the crisis
    output is identical either way, so neither distinguishes a real templated deploy from a stale
    literal one). This tree carries {{crisis_}} placeholders, so it must report True."""
    monkeypatch.setenv("SAGE_API_KEY", "test-secret")
    res = client.get("/health/version", headers={"X-Sage-Api-Key": "test-secret"})
    assert res.status_code == 200
    assert res.json()["crisis_copy_templated"] is True


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


# ── Native-Arabic shadow containment: API-layer assertion (Task 7 merge gate item (a)) ─────────
# The node-level sentinel test (tests/test_shadow_never_served.py) proves the shadow text never
# enters the node's return dict. This test crosses the HTTP boundary too: it drives an Arabic turn
# with NATIVE_ARABIC_SHADOW_ENABLED=True and a monkeypatched shadow generator returning a
# distinctive sentinel, through a mock graph that actually calls the real freeflow_respond_node
# (not a hand-built stand-in dict, so the wiring itself is exercised) — then asserts the sentinel
# is absent from the streamed HTTP body AND from every response header.
def test_chat_arabic_shadow_sentinel_never_in_http_payload(monkeypatch, client, session_id):
    import sage_poc.nodes.freeflow_respond as fr
    from unittest.mock import patch, AsyncMock
    from server import app
    from tests.test_freeflow_respond import fr_stub_llm

    _SENTINEL = "ZZZ_SHADOW_SENTINEL_ﷺ_NEVER_SERVE"
    shadow_payload = {
        "text": _SENTINEL, "prompt_hash": "x" * 16, "exemplar_version": "0.1",
        "generation_language": "ar_native", "gen_latency_ms": 3,
    }
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)

    async def _mock(state):
        with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=shadow_payload)), \
             patch.object(fr, "write_shadow_eval_row", new=AsyncMock()):
            node_out = await fr.freeflow_respond_node(
                {**state, "detected_language": "ar", "raw_message": "تعبت", "message_en": "tired",
                 "path": [], "user_id": None, "session_id": session_id, "turn_number": 1},
                llm=fr_stub_llm(),
            )
        return {**_graph_result(), "response": node_out["response_en"], "path": node_out["path"],
                "detected_language": "ar"}

    class _MockGraph:
        async def ainvoke(self, state, config=None, **kwargs):
            return await _mock(state)

    monkeypatch.setattr(app.state, "_graph", _MockGraph())
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "تعبت"}],
        "session_id": session_id,
    })
    assert res.status_code == 200
    assert _SENTINEL not in res.text, "shadow sentinel leaked into the served HTTP body"
    for name, value in res.headers.items():
        assert _SENTINEL not in value, f"shadow sentinel leaked into response header {name!r}"
