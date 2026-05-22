import inspect
import pytest
from fastapi.testclient import TestClient
from sage_poc.nodes.freeflow_respond import freeflow_respond_node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node


def get_client():
    from server import app
    import httpx
    client = TestClient(app)
    client.timeout = httpx.Timeout(10.0)
    return client


def test_chat_bad_request_empty_messages():
    client = get_client()
    res = client.post("/chat", json={"messages": [], "session_id": "test"})
    assert res.status_code == 400


def test_chat_bad_request_last_message_not_user():
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "assistant", "content": "Hello"}],
        "session_id": "test",
    })
    assert res.status_code == 400


def test_chat_crisis_message_has_signal():
    # "end it all" is a CRISIS_KEYWORD — triggers keyword match, no LLM call.
    # _crisis_response_node returns a hardcoded string. Zero API calls.
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")


@pytest.mark.slow
def test_chat_returns_text_for_valid_message():
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I've been feeling really anxious lately."}],
        "session_id": "test-session",
    }, timeout=30)
    assert res.status_code == 200
    assert len(res.text.strip()) > 10


def test_chat_graph_error_returns_sentinel(monkeypatch):
    import server as srv

    async def _raise_ainvoke(state):
        raise RuntimeError("simulated graph failure")

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_raise_ainvoke)})())
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert "[[SERVER_ERROR]]" in res.text


def test_chat_response_headers_present():
    # Crisis path: keyword match, no LLM call — fast test.
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.status_code == 200
    assert "x-sage-model" in res.headers
    assert "x-sage-node-path" in res.headers


def test_chat_body_has_no_meta_sentinel():
    # Metadata must never appear in the body stream — only in headers.
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.status_code == 200
    assert "[[META:" not in res.text


def test_chat_node_path_header_is_valid_json_array():
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
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


def test_chat_arabic_crisis_message_has_signal():
    # Arabic crisis keyword "أريد الموت" (I want to die) — triggers keyword match,
    # no LLM call needed. Fast test.
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "أريد الموت"}],
        "session_id": "test-session",
    })
    assert res.status_code == 200
    assert res.text.startswith("[[CRISIS_DETECTED]]")
    # The Arabic crisis response should NOT be the error sentinel
    assert "[[SERVER_ERROR]]" not in res.text


def test_all_audit_headers_present():
    """All 8 metadata headers must be present on every response, including crisis paths."""
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.status_code == 200
    for header in [
        "x-sage-model", "x-sage-node-path",
        "x-sage-skill-id", "x-sage-step-id", "x-sage-gate-path",
        "x-sage-crisis-flags", "x-sage-clinical-flags", "x-sage-emotional-intensity",
    ]:
        assert header in res.headers, f"Missing header: {header}"


def test_crisis_path_crisis_flags_non_empty():
    """Crisis keyword match → x-sage-crisis-flags is a non-empty JSON array."""
    import json as _json
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    flags = _json.loads(res.headers["x-sage-crisis-flags"])
    assert isinstance(flags, list)
    assert len(flags) > 0


def test_crisis_path_gate_path_and_no_skill():
    """Crisis responses: gate_path='crisis', skill_id and step_id empty."""
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "I want to end it all"}],
        "session_id": "test-session",
    })
    assert res.headers.get("x-sage-gate-path") == "crisis"
    assert res.headers.get("x-sage-skill-id") == ""
    assert res.headers.get("x-sage-step-id") == ""


def test_crisis_state_resolved_not_coerced_to_none(monkeypatch):
    """crisis_state='resolved' must survive the _build_state boundary.

    BE-C1: _VALID_CRISIS_STATES previously omitted 'resolved', so the post-
    crisis warmth window was silently dropped on the first turn after check-in.
    """
    import server as srv

    received_states = []

    async def _capture_state(state):
        received_states.append(state.get("crisis_state"))
        return {
            "path": ["safety_check", "output_gate"],
            "is_safe": True,
            "response": "I hear you.",
            "crisis_state": "resolved",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 5,
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_capture_state)})())
    client = get_client()
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "I'm feeling much better now"}],
        "session_id": "test",
        "crisis_state": "resolved",
    })
    assert received_states == ["resolved"], (
        f"Expected graph to receive crisis_state='resolved' but got {received_states}. "
        "Check _VALID_CRISIS_STATES in server.py."
    )


def test_skill_response_audit_headers(monkeypatch):
    """Skill-path response: skill_id and step_id populated, crisis_flags empty."""
    import server as srv
    import json as _json

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

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_mock_skill)})())
    client = get_client()
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


def test_freeflow_response_audit_headers(monkeypatch):
    """Freeflow response: skill_id/step_id empty, clinical_flags and intensity populated."""
    import server as srv
    import json as _json

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

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_mock_freeflow)})())
    client = get_client()
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


def test_chat_response_has_all_trace_headers(monkeypatch):
    """All 13 trace headers must be present in every /chat response."""
    import server as srv

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

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_mock_trace)})())
    client = get_client()
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


def test_active_skill_id_ferried_into_graph_state(monkeypatch):
    """active_skill_id from the request must reach the graph as-is.

    BE-C5: _build_state previously hardcoded active_skill_id=None, so
    multi-turn skills always restarted from scratch through the HTTP API.
    """
    import server as srv

    received = {}

    async def _capture(state):
        received["active_skill_id"] = state.get("active_skill_id")
        received["active_step_id"] = state.get("active_step_id")
        return {
            "path": ["output_gate"],
            "is_safe": True,
            "response": "ok",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": [],
            "emotional_intensity": 5,
            "active_skill_id": "cbt_thought_record",
            "executed_step_id": None,
            "gate_path": "standard",
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_capture)})())
    client = get_client()
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "continue"}],
        "session_id": "test",
        "active_skill_id": "cbt_thought_record",
        "active_step_id": "explore_distortion",
    })
    assert received["active_skill_id"] == "cbt_thought_record", (
        f"Graph received active_skill_id={received['active_skill_id']!r}, expected 'cbt_thought_record'"
    )
    assert received["active_step_id"] == "explore_distortion"


def test_clinical_flags_ferried_into_graph_state(monkeypatch):
    """clinical_flags from prior turns must be carried into the new turn's state."""
    import server as srv

    received = {}

    async def _capture(state):
        received["clinical_flags"] = state.get("clinical_flags")
        return {
            "path": ["output_gate"],
            "is_safe": True,
            "response": "ok",
            "crisis_state": "none",
            "crisis_flags": [],
            "clinical_flags": ["trauma_indicator"],
            "emotional_intensity": 5,
            "active_skill_id": None,
            "executed_step_id": None,
            "gate_path": "standard",
        }

    monkeypatch.setattr(srv, "_graph", type("G", (), {"ainvoke": staticmethod(_capture)})())
    client = get_client()
    client.post("/chat", json={
        "messages": [{"role": "user", "content": "I feel okay"}],
        "session_id": "test",
        "clinical_flags": ["trauma_indicator"],
    })
    assert received["clinical_flags"] == ["trauma_indicator"], (
        f"Graph received clinical_flags={received['clinical_flags']!r}, expected ['trauma_indicator']"
    )
