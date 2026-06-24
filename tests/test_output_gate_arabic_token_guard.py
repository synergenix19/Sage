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

    async def fake_translate(text, *, strict=False):
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
    async def fake_translate(text, *, strict=False):
        return "كيف نومك مؤخرا؟"
    seen = {"n": 0}
    async def counting(text, *, strict=False):
        seen["n"] += 1
        return await fake_translate(text, strict=strict)
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=counting), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        await output_gate_node(make_state())
    assert seen["n"] == 1, "clean Arabic must not trigger a second translation"
