import pytest
from fastapi.testclient import TestClient


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
    def _raise(state):
        raise RuntimeError("simulated graph failure")
    monkeypatch.setattr(srv, "_graph", type("G", (), {"invoke": staticmethod(_raise)})())
    client = get_client()
    res = client.post("/chat", json={
        "messages": [{"role": "user", "content": "hello"}],
        "session_id": "test",
    })
    assert res.status_code == 200
    assert res.text.startswith("[[SERVER_ERROR]]")
