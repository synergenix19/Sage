"""Transport-level shape proof for task 7d (audit.py Supabase insert consolidation).

Byte-identical row-write behavior is a PDPL compliance-artifact constraint: the
consolidation onto _supabase_insert must not change the URL, header keys, or
JSON body actually POSTed for any of the three call sites. These tests mock
httpx.AsyncClient (same pattern as tests/test_audit.py) and assert on the
captured request shape rather than on any credential value.
"""
import importlib
from unittest.mock import patch

import pytest


class _MockResponse:
    def raise_for_status(self):
        pass


class _RecordingClient:
    """Captures every POST call's url/headers/json for later assertion."""

    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, url, headers, json, **kwargs):
        self.calls.append({"url": url, "headers": headers, "json": json})
        return _MockResponse()

    async def get(self, url, headers, **kwargs):
        class R:
            status_code = 200
        return R()


def _fresh_audit_module(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://transport-test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "transport-test-key")
    import sage_poc.audit as audit_mod
    importlib.reload(audit_mod)
    return audit_mod


@pytest.mark.asyncio
async def test_write_identity_substitution_audit_transport_shape(monkeypatch):
    audit_mod = _fresh_audit_module(monkeypatch)
    client = _RecordingClient()

    with patch("httpx.AsyncClient", return_value=client):
        await audit_mod.write_identity_substitution_audit(
            session_id="sess-1",
            turn_number=3,
            rule_id="RULE-1",
            original_response_hash="hash-1",
            original_response_text="original text",
            substitute_with="substitute text",
            user_id=None,
        )

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["url"] == "https://transport-test.supabase.co/rest/v1/identity_substitution_audit"
    assert set(call["headers"].keys()) == {"apikey", "Authorization", "Content-Type", "Prefer"}
    assert call["headers"]["Content-Type"] == "application/json"
    assert call["headers"]["Prefer"] == "return=minimal"
    assert call["headers"]["Authorization"].startswith("Bearer ")
    assert call["json"] == {
        "session_id": "sess-1",
        "turn_number": 3,
        "rule_id": "RULE-1",
        "original_response_hash": "hash-1",
        "original_response_text": "original text",
        "substitute_with": "substitute text",
        "user_id": None,
    }


@pytest.mark.asyncio
async def test_write_session_audit_row_transport_shape_merge_duplicates(monkeypatch):
    """The production Prefer variant: write_session_audit always calls
    _write_session_audit_row with prefer='resolution=merge-duplicates'."""
    audit_mod = _fresh_audit_module(monkeypatch)
    client = _RecordingClient()
    row = {"session_id": "sess-2", "turn_number": 5, "user_id": None}

    with patch("httpx.AsyncClient", return_value=client):
        await audit_mod._write_session_audit_row(row, prefer="resolution=merge-duplicates", label="session_audit")

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["url"] == "https://transport-test.supabase.co/rest/v1/session_audit"
    assert set(call["headers"].keys()) == {"apikey", "Authorization", "Content-Type", "Prefer"}
    assert call["headers"]["Prefer"] == "resolution=merge-duplicates"
    assert call["json"] == row


@pytest.mark.asyncio
async def test_write_session_audit_row_transport_shape_return_minimal(monkeypatch):
    """_write_session_audit_row's prefer is a passthrough parameter, not hardcoded
    to the one value the current single production caller happens to use — prove
    the other Prefer variant rides the header unchanged too."""
    audit_mod = _fresh_audit_module(monkeypatch)
    client = _RecordingClient()
    row = {"session_id": "sess-3", "turn_number": 7, "user_id": None}

    with patch("httpx.AsyncClient", return_value=client):
        await audit_mod._write_session_audit_row(row, prefer="return=minimal", label="session_audit")

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["url"] == "https://transport-test.supabase.co/rest/v1/session_audit"
    assert call["headers"]["Prefer"] == "return=minimal"
    assert call["json"] == row


@pytest.mark.asyncio
async def test_write_session_audit_row_fail_open_on_http_error(monkeypatch, caplog):
    """_write_session_audit_row must swallow a raised httpx.HTTPStatusError from
    _supabase_insert (fail-open, loud via logger.critical) rather than propagate it."""
    import logging
    audit_mod = _fresh_audit_module(monkeypatch)

    class _Response:
        status_code = 500
        text = "server error"

    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, url, headers, json, **kwargs):
            import httpx
            request = httpx.Request("POST", url)
            response = httpx.Response(500, text="server error", request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    row = {"session_id": "sess-4", "turn_number": 9, "user_id": None}
    with patch("httpx.AsyncClient", return_value=_FailingClient()):
        with caplog.at_level(logging.CRITICAL, logger="sage_poc.audit"):
            # Must not raise.
            await audit_mod._write_session_audit_row(row, prefer="resolution=merge-duplicates", label="session_audit")

    assert any("AUDIT FAILURE" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_existing_supabase_insert_caller_transport_shape_shadow_eval(monkeypatch):
    """shadow_eval.write_shadow_eval_row is an existing _supabase_insert caller
    (default prefer). Its request shape must be unaffected by the prefer param
    addition."""
    audit_mod = _fresh_audit_module(monkeypatch)
    import sage_poc.shadow_eval as shadow_eval_mod
    importlib.reload(shadow_eval_mod)
    client = _RecordingClient()

    state = {"session_id": "sess-5", "turn_number": 1, "message_en": "hello", "clinical_flags": []}
    with patch("httpx.AsyncClient", return_value=client):
        await shadow_eval_mod.write_shadow_eval_row(
            state, payload=None, tool_loop_iterations=0, timed_out=True,
        )

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["url"] == "https://transport-test.supabase.co/rest/v1/shadow_register_eval"
    assert set(call["headers"].keys()) == {"apikey", "Authorization", "Content-Type", "Prefer"}
    assert call["headers"]["Prefer"] == "return=minimal"
    assert call["json"]["session_id"] == "sess-5"
    assert call["json"]["shadow_timed_out"] is True
