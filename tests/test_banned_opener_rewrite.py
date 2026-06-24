"""#58 — opener-rewrite helper (register-preserving fix). New behaviour; the legacy
regen/retry contract in test_output_gate_banned_opener.py is migrated in Tasks 2-3."""
import asyncio
import pytest
from unittest.mock import patch
from sage_poc.nodes import output_gate


@pytest.mark.asyncio
async def test_rewrite_opener_passes_context_and_returns_text():
    captured = {}

    class _Msg:
        content = "You're carrying a lot with these deadlines. The lack of sleep makes it heavier."

    class _FakeClassifier:
        async def ainvoke(self, messages, *a, **k):
            captured["messages"] = messages
            return _Msg()

    with patch.object(output_gate, "get_classifier", lambda: _FakeClassifier()):
        out = await output_gate._rewrite_opener(
            response_en="It sounds like things are hard right now. The lack of sleep makes it heavier.",
            opener="It sounds like",
            user_message_en="deadlines keep piling up and I can't sleep",
        )
    joined = " ".join(m["content"] for m in captured["messages"])
    assert "It sounds like" in joined and "deadlines keep piling up" in joined
    assert out.startswith("You're carrying")
    assert "it sounds like" not in out.lower()


@pytest.mark.asyncio
async def test_rewrite_opener_times_out_to_empty(monkeypatch):
    class _Slow:
        async def ainvoke(self, *a, **k):
            await asyncio.sleep(10)
            return "never"

    monkeypatch.setattr(output_gate, "get_classifier", lambda: _Slow())
    monkeypatch.setattr(output_gate, "_OPENER_REWRITE_TIMEOUT", 0.2)
    out = await output_gate._rewrite_opener(
        "It sounds like things are hard.", "It sounds like", "msg"
    )
    assert out == ""


@pytest.mark.asyncio
async def test_rewrite_opener_empty_input_returns_empty():
    assert await output_gate._rewrite_opener("", "It sounds like", "msg") == ""
