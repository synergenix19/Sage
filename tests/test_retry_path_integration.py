"""Integration tests for the banned-opener retry path.

Three things to verify that unit tests cannot reach:
  A. output_gate_banned_opener_retry appears in X-Sage-Node-Path (HTTP header)
     and in the LangGraph path state after a full turn.
  B. write_session_audit fires on the early-return path with the retry marker
     in node_path, and the row lands in Supabase (real write, not mock).
  C. When both attempts produce a banned opener, the system proceeds with
     banned_opener_violation flagged and returns non-empty copy — no crash,
     no infinite loop.

Empirical question also answered here:
  Does GPT-4o near-match evade on attempt #2 (e.g. "Sounds like three weeks…")?
  These tests use scripted LLM responses — record a known-evasion string and
  assert the second-failure → END branch is exercised deterministically.

All tests use the session-scoped `asgi_client` fixture (ASGI in-process, real
Supabase, mocked LLM). Marked @pytest.mark.integration — run with:
  uv run pytest tests/test_retry_path_integration.py -m integration -v

Prerequisites: SUPABASE_URL and SUPABASE_SERVICE_KEY in .env (loaded via
sage_poc.config.load_dotenv at import time).
"""
import asyncio
import json
import os
import time
import pytest
import httpx
from unittest.mock import patch

pytestmark = pytest.mark.integration

_SUPABASE_URL = os.environ.get("SUPABASE_URL") or ""
_SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or ""

# Dog transcript — the message that started this whole investigation
_DOG_MESSAGE = "hi, i'm worried, my dog is not pooping for 3 weeks"

# Banned opener responses (scripted to guarantee gate fires)
_BANNED_FIRST = "It sounds like you're really worried about your dog. Three weeks is a long time."
_BANNED_SECOND = "That sounds really difficult. Have you tried a different vet?"

# Clean retry response — should clear the gate
_CLEAN_RETRY = "Three weeks without relief. What has the vet said so far?"

# Near-match evasion — "Sounds like" without leading "It"/"That" prefix; does NOT match the regex
# This simulates GPT-4o dropping the banned token but keeping the reflective structure
_NEAR_MATCH_EVASION = "Sounds like your dog has been struggling for a while. That must be stressful."


def _supabase_headers() -> dict:
    return {
        "apikey": _SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {_SUPABASE_SERVICE_KEY}",
    }


async def _fetch_audit_rows(session_id: str) -> list[dict]:
    """Query Supabase session_audit for all rows with the given session_id."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(
            f"{_SUPABASE_URL}/rest/v1/session_audit",
            headers=_supabase_headers(),
            params={"session_id": f"eq.{session_id}", "select": "*"},
        )
        r.raise_for_status()
        return r.json()


def _chat_headers(sage_api_key: str = "") -> dict:
    h = {}
    if sage_api_key:
        h["X-Sage-Api-Key"] = sage_api_key
    return h


@pytest.fixture
def _intent_mock():
    """Patch intent_route and fallback to return general_chat without calling real LLM."""
    from tests.conftest import make_mock_llm, _INTENT_JSON_GENERAL_CHAT
    intent_llm = make_mock_llm([_INTENT_JSON_GENERAL_CHAT])
    with patch("sage_poc.nodes.intent_route.get_classifier", return_value=intent_llm), \
         patch("sage_poc.nodes.intent_route.get_fallback_classifier", return_value=intent_llm):
        yield intent_llm


# ── Test A ──────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _SUPABASE_URL,
    reason="SUPABASE_URL required"
)
@pytest.mark.asyncio
async def test_retry_marker_in_node_path_header(asgi_client, _intent_mock):
    """A: When the first response is a banned opener and the retry succeeds,
    output_gate_banned_opener_retry must appear in the X-Sage-Node-Path header.

    This is the empirical answer to the original question: does the retry loop
    fire and is it visible in the response trace?
    """
    from tests.conftest import make_mock_llm
    responder = make_mock_llm([_BANNED_FIRST, _CLEAN_RETRY])

    with patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=responder), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=responder):

        resp = await asgi_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": _DOG_MESSAGE}],
                "session_id": f"retry-test-A-{int(time.time())}",
            },
        )

    assert resp.status_code == 200
    path = json.loads(resp.headers["x-sage-node-path"])
    assert "output_gate_banned_opener_retry" in path, (
        f"Expected output_gate_banned_opener_retry in X-Sage-Node-Path. Got: {path}"
    )
    # Full response must be the clean retry, not the banned opener
    body = resp.text.strip()
    assert body, "Response body must not be empty"
    assert not body.startswith("It sounds like"), (
        "Final response must not be the banned opener — gate should have caught it"
    )


# ── Test B ──────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _SUPABASE_URL or not _SUPABASE_SERVICE_KEY,
    reason="SUPABASE_URL and SUPABASE_SERVICE_KEY required"
)
@pytest.mark.asyncio
async def test_audit_row_written_on_early_return_path(asgi_client, _intent_mock):
    """B: write_session_audit must fire on the early-return path.

    Verifies that the Cosmos/Supabase session_audit table receives a row with
    output_gate_banned_opener_retry in node_path before the retry fires. This
    closes the PDPL traceability gap: the detection event is independently
    auditable, not just the final completed pass.

    Expected: at least one audit row for the session contains
    output_gate_banned_opener_retry in its node_path array.
    """
    from tests.conftest import make_mock_llm
    session_id = f"retry-test-B-{int(time.time())}"
    responder = make_mock_llm([_BANNED_FIRST, _CLEAN_RETRY])

    with patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=responder), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=responder):

        resp = await asgi_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": _DOG_MESSAGE}],
                "session_id": session_id,
            },
        )

    assert resp.status_code == 200

    # Allow async audit writes to flush
    await asyncio.sleep(1.5)

    rows = await _fetch_audit_rows(session_id)
    assert len(rows) >= 1, f"Expected at least 1 audit row, got {len(rows)}"

    retry_rows = [
        r for r in rows
        if "output_gate_banned_opener_retry" in (r.get("node_path") or [])
    ]
    assert retry_rows, (
        f"Expected at least one audit row with output_gate_banned_opener_retry in node_path. "
        f"Got rows: {[r.get('node_path') for r in rows]}"
    )


# ── Test C ──────────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not _SUPABASE_URL,
    reason="SUPABASE_URL required"
)
@pytest.mark.asyncio
async def test_second_failure_substitutes_vetted_fallback(asgi_client, _intent_mock):
    """C: When both attempts produce banned openers, the user must receive
    _VETTED_FALLBACK_RESPONSE — not the banned opener and not empty copy.

    Tests the second-failure → fallback-substitution → END branch end-to-end.
    Verifies: (1) response body equals the vetted constant, (2) retry marker
    in path, (3) max-1-retry enforced (freeflow_respond count <= 2),
    (4) output_gate_fallback_substituted appears in path.
    """
    from sage_poc.nodes.output_gate import _VETTED_FALLBACK_RESPONSE
    from tests.conftest import make_mock_llm
    # Both attempts return banned openers
    responder = make_mock_llm([_BANNED_FIRST, _BANNED_SECOND])

    with patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=responder), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=responder):

        resp = await asgi_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": _DOG_MESSAGE}],
                "session_id": f"retry-test-C-{int(time.time())}",
            },
        )

    assert resp.status_code == 200, "System must not crash on double banned-opener failure"
    body = " ".join(resp.text.strip().split())  # normalise streaming whitespace
    assert body == _VETTED_FALLBACK_RESPONSE, (
        f"User must receive the vetted fallback constant when retry is exhausted. "
        f"Got: {body!r}"
    )

    path = json.loads(resp.headers["x-sage-node-path"])
    assert "output_gate_banned_opener_retry" in path, "Retry marker must be in path"
    assert "output_gate_fallback_substituted" in path, (
        "Fallback substitution must appear in path so reviewers can distinguish "
        "'fallback substituted' from 'violation passed through'"
    )

    freeflow_count = path.count("freeflow_respond")
    assert freeflow_count <= 2, (
        f"Max-1 retry means at most 2 freeflow passes. Got {freeflow_count}: {path}"
    )


# ── Test C-audit: fallback substitution audit row ───────────────────────────

@pytest.mark.skipif(
    not _SUPABASE_URL or not _SUPABASE_SERVICE_KEY,
    reason="SUPABASE_URL and SUPABASE_SERVICE_KEY required"
)
@pytest.mark.asyncio
async def test_fallback_substitution_audit_row_written(asgi_client, _intent_mock):
    """C-audit: When fallback is substituted, a Supabase audit row with
    output_gate_fallback_substituted in node_path must be written.

    Distinct from the early-return row (Test B). A reviewer reading the audit log
    must be able to distinguish 'fallback substituted' from 'violation passed through.'
    """
    from tests.conftest import make_mock_llm
    session_id = f"retry-test-C-audit-{int(time.time())}"
    responder = make_mock_llm([_BANNED_FIRST, _BANNED_SECOND])

    with patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=responder), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=responder):

        resp = await asgi_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": _DOG_MESSAGE}],
                "session_id": session_id,
            },
        )

    assert resp.status_code == 200
    await asyncio.sleep(1.5)

    rows = await _fetch_audit_rows(session_id)
    assert rows, f"Expected audit rows for session {session_id}"

    fallback_rows = [
        r for r in rows
        if "output_gate_fallback_substituted" in (r.get("node_path") or [])
    ]
    assert fallback_rows, (
        f"Expected at least one audit row with output_gate_fallback_substituted in node_path. "
        f"Got rows: {[r.get('node_path') for r in rows]}"
    )


# ── Test D: near-match evasion ──────────────────────────────────────────────

@pytest.mark.skipif(
    not _SUPABASE_URL,
    reason="SUPABASE_URL required"
)
@pytest.mark.asyncio
async def test_near_match_evasion_clears_gate(asgi_client, _intent_mock):
    """D: 'Sounds like' (without leading 'It'/'That') does NOT match _BANNED_OPENER_RE.

    This is the near-match evasion case: GPT-4o drops the banned token prefix but
    keeps the reflective structure. The current regex does not catch it. This test
    documents the known gap deterministically so a future tightening of the pattern
    can be validated against this fixture.

    Expected: no retry fires (output_gate_banned_opener_retry absent from path).
    The evasion passes through. Flag for clinician/content review.
    """
    from tests.conftest import make_mock_llm
    responder = make_mock_llm([_NEAR_MATCH_EVASION])

    with patch("sage_poc.nodes.freeflow_respond.get_responder", return_value=responder), \
         patch("sage_poc.nodes.freeflow_respond.get_fallback_responder", return_value=responder):

        resp = await asgi_client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": _DOG_MESSAGE}],
                "session_id": f"retry-test-D-{int(time.time())}",
            },
        )

    assert resp.status_code == 200
    path = json.loads(resp.headers["x-sage-node-path"])

    # The evasion string does not match the current regex — gate passes it through
    assert "output_gate_banned_opener_retry" not in path, (
        "Near-match evasion 'Sounds like...' must not match _BANNED_OPENER_RE. "
        "If this assertion fails, the regex was tightened — update this test to "
        "use a string that still evades the new pattern."
    )
