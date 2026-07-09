import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.output_gate import output_gate_node


def make_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "I can't sleep", "response_en": "Tell me about your sleep.",
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_latin_word_in_arabic_output_triggers_strict_retranslate():
    """First translation leaks an English word; the guard re-translates strict and the
    leaked word is gone (RC-5 / feedback #4: 'نومك lately')."""
    calls = {"n": 0}

    async def fake_translate(text, *, strict=False, **_kw):
        calls["n"] += 1
        # First (non-strict) call leaks English; strict retry is clean.
        return "كيف نومك lately؟" if not strict else "كيف نومك مؤخرا؟"

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=fake_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state())

    assert calls["n"] == 2, "guard must re-translate once when Latin words remain"
    assert "lately" not in result["response"]
    assert "arabic_token_guard_retranslate" in result["path"]


@pytest.mark.asyncio
async def test_clean_arabic_output_not_retranslated():
    async def fake_translate(text, *, strict=False, **_kw):
        return "كيف نومك مؤخرا؟"
    seen = {"n": 0}
    async def counting(text, *, strict=False, **_kw):
        seen["n"] += 1
        return await fake_translate(text, strict=strict, **_kw)
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=counting), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(make_state())
    assert seen["n"] == 1, "clean Arabic must not trigger a second translation"


@pytest.mark.asyncio
async def test_translate_out_ms_times_only_translate_block_excludes_gate_overhead():
    """translate_out_ms (§5 served-arm timer) must reflect the async_translate_to_arabic
    call's own delay, not the surrounding gate work (cultural check, format strip, audit
    build). Patch the translate call with a ~50ms delay and assert the captured timer is
    close to that delay, not blown out by unrelated gate overhead."""
    async def slow_translate(text, *, strict=False, **_kw):
        await asyncio.sleep(0.05)
        return "كيف نومك مؤخرا؟"

    audit_states = []

    async def mock_write(state):
        audit_states.append(state)

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=slow_translate), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=mock_write):
        await output_gate_node(make_state())
        await asyncio.sleep(0)  # let the audit-write task run

    assert len(audit_states) == 1
    translate_out_ms = audit_states[0]["translate_out_ms"]
    assert translate_out_ms is not None
    assert 50 <= translate_out_ms < 300, (
        f"expected translate_out_ms to reflect the ~50ms translate delay only, got {translate_out_ms}"
    )


@pytest.mark.asyncio
async def test_translate_out_ms_none_when_translate_out_does_not_run():
    """English turn (no translate-out) leaves translate_out_ms unset -> None in the audit row."""
    audit_states = []

    async def mock_write(state):
        audit_states.append(state)

    with patch("sage_poc.nodes.output_gate.write_session_audit", new=mock_write):
        await output_gate_node(make_state(detected_language="en"))
        await asyncio.sleep(0)

    assert len(audit_states) == 1
    assert audit_states[0].get("translate_out_ms") is None
