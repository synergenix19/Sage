# tests/test_session_audit_integration.py
"""Integration test: full turn through the server produces a session_audit row.

Originally required a live server on http://localhost:8765. Rewritten to use
the session-scoped `asgi_client` fixture (ASGI in-process, real Supabase) so
this test runs in CI permanently without a pre-started server.

The test uses a mocked LLM (general_chat intent + clean response) so it is
deterministic and does not call Azure OpenAI in CI.

Prerequisites: SUPABASE_URL and SUPABASE_SERVICE_KEY in .env.
"""
import asyncio
import os
import time
import pytest
import httpx
from unittest.mock import patch

pytestmark = pytest.mark.integration

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")


@pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="SUPABASE_URL and SUPABASE_SERVICE_KEY required for integration test",
)
@pytest.mark.asyncio
async def test_session_audit_row_written_after_turn(asgi_client):
    """Full turn through the in-process server produces a session_audit row.

    Verifies:
    - HTTP 200 from /chat
    - One audit row written to Supabase session_audit with correct fields
    - node_path is non-empty
    - crisis_state is 'none' for a benign message
    """
    from tests.conftest import make_mock_llm, _INTENT_JSON_GENERAL_CHAT

    session_id = f"integration-test-{int(time.time())}"

    intent_llm = make_mock_llm([_INTENT_JSON_GENERAL_CHAT])
    responder_llm = make_mock_llm(["How has today been treating you so far?"])

    with patch("sage_poc.nodes.intent_route.get_classifier", return_value=intent_llm), \
         patch("sage_poc.nodes.intent_route.get_fallback_classifier", return_value=intent_llm), \
         patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=responder_llm), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=responder_llm):

        resp = await asgi_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "I feel a bit stressed today"}],
                "session_id": session_id,
            },
        )

    assert resp.status_code == 200

    # Allow the async audit write to complete
    await asyncio.sleep(1.5)

    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{SUPABASE_URL}/rest/v1/session_audit",
            headers=headers,
            params={"session_id": f"eq.{session_id}", "select": "*"},
        )
        assert r.status_code == 200
        rows = r.json()

    assert len(rows) >= 1, f"Expected at least 1 audit row, got {len(rows)}"
    row = rows[0]
    assert row["session_id"] == session_id
    assert row["turn_number"] == 1
    assert row["node_path"], "node_path must not be empty"
    assert row["primary_intent"] is not None, "primary_intent must be set"
    assert row["crisis_state"] == "none", f"Expected crisis_state=none, got {row['crisis_state']}"
