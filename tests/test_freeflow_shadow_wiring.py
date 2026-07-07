import asyncio
from unittest.mock import patch, AsyncMock
import sage_poc.nodes.freeflow_respond as fr
from tests.test_freeflow_respond import fr_stub_llm


def _ar():
    return {"detected_language": "ar", "raw_message": "تعبت", "message_en": "tired",
            "path": [], "user_id": None, "session_id": "s1", "turn_number": 1}


def test_writes_eval_row_when_flag_on(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)
    payload = {"text": "مرحبا", "prompt_hash": "a"*16, "exemplar_version": "0.1",
               "generation_language": "ar_native", "gen_latency_ms": 4}
    writer = AsyncMock()
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=payload)), \
         patch.object(fr, "write_shadow_eval_row", new=writer):
        out = asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    writer.assert_awaited_once()
    kwargs = writer.await_args.kwargs
    assert kwargs["timed_out"] is False and "tool_loop_iterations" in kwargs
    assert "shadow_arabic" not in out and "response_en" in out  # nothing shadow leaks into state


def test_timeout_writes_censored_row(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.01)
    async def _hang(*a, **k):
        await asyncio.sleep(10)
    writer = AsyncMock()
    with patch.object(fr, "generate_shadow_arabic", new=_hang), \
         patch.object(fr, "write_shadow_eval_row", new=writer):
        asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    assert writer.await_args.kwargs["timed_out"] is True


def test_no_shadow_when_flag_off(monkeypatch):
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", False)
    writer = AsyncMock()
    with patch.object(fr, "write_shadow_eval_row", new=writer):
        asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    writer.assert_not_called()


def test_generation_failure_writes_nothing(monkeypatch):
    # Clarification #1: non-timeout generation failure (shadow returns None, not timed out)
    # must NOT write a row — an invalid measurement must not pollute the sample. Distinct from
    # timeout (which DOES write a censored row per test_timeout_writes_censored_row).
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 5.0)  # not a timeout; generator just returns None
    writer = AsyncMock()
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=None)), \
         patch.object(fr, "write_shadow_eval_row", new=writer):
        out = asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    writer.assert_not_called()          # generation failure → no row
    assert "response_en" in out          # served turn unaffected


def test_eval_write_failure_does_not_break_served_turn(monkeypatch):
    # Verification #1: a write raising/timing out must be swallowed; served turn intact.
    monkeypatch.setattr(fr, "NATIVE_ARABIC_SHADOW_ENABLED", True)
    monkeypatch.setattr(fr, "_SHADOW_TIMEOUT_S", 0.05)
    payload = {"text": "مرحبا", "prompt_hash": "a"*16, "exemplar_version": "0.1",
               "generation_language": "ar_native", "gen_latency_ms": 4}
    async def _boom(*a, **k):
        raise RuntimeError("supabase down")
    with patch.object(fr, "generate_shadow_arabic", new=AsyncMock(return_value=payload)), \
         patch.object(fr, "write_shadow_eval_row", new=_boom):
        out = asyncio.run(fr.freeflow_respond_node(_ar(), llm=fr_stub_llm()))
    assert "response_en" in out  # served turn completed despite write failure
