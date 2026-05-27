# tests/test_session_audit_integration.py
import os
import asyncio
import pytest
import httpx

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SAGE_API_KEY = os.environ.get("SAGE_API_KEY", "")

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not SUPABASE_URL or not SUPABASE_SERVICE_KEY,
    reason="SUPABASE_URL and SUPABASE_SERVICE_KEY required for integration test",
)
@pytest.mark.asyncio
async def test_session_audit_row_written_after_turn():
    """Full turn through the POC server produces a session_audit row with correct fields."""
    import time
    session_id = f"integration-test-{int(time.time())}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            "http://localhost:8765/chat",
            json={
                "messages": [{"role": "user", "content": "I feel a bit stressed today"}],
                "session_id": session_id,
            },
            headers={"X-Sage-Api-Key": SAGE_API_KEY} if SAGE_API_KEY else {},
        )
        assert resp.status_code == 200

    # Wait for the async write to complete
    await asyncio.sleep(1.0)

    # Query Supabase directly to verify the row
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

    assert len(rows) == 1, f"Expected 1 audit row, got {len(rows)}"
    row = rows[0]
    assert row["session_id"] == session_id
    assert row["turn_number"] == 1
    assert len(row["node_path"]) > 0, "node_path must not be empty"
    assert row["primary_intent"] is not None, "primary_intent must be set"
    assert row["crisis_state"] is not None, "crisis_state must be set"
    assert row["crisis_state"] == "none", f"Expected crisis_state=none, got {row['crisis_state']}"
