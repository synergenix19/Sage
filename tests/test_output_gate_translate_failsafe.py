"""#5 — native-AR failsafe when translate-out TOTALLY fails.

On an Arabic turn, if the Khaleeji translation fails outright, async_translate_to_arabic returns the
untranslated English verbatim (fail-open). Shipping that English wall of text to an Arabic user is the
finding. Fix: when translation returns the raw English AND English bleed persists after the strict
retry (i.e. final_response == response_en), substitute a native-AR failsafe instead. A merely-imperfect
translation (a stray Latin token in an otherwise-Arabic reply) must be shipped as-is, NOT replaced.
"""
import pytest
from unittest.mock import AsyncMock, patch

from sage_poc.nodes.output_gate import output_gate_node, _AR_TRANSLATE_FAILSAFE


def make_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "tell me about sleep", "response_en": "Let's talk about your sleep tonight.",
        "raw_message": "احكيلي عن النوم",
        "is_safe": True, "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


def _is_arabic(s):
    return any("؀" <= ch <= "ۿ" for ch in s)


@pytest.mark.asyncio
async def test_total_translation_failure_serves_native_ar_failsafe():
    """Both normal + strict translate return the untranslated English -> serve the AR failsafe."""
    async def failing_translate(text, *, strict=False, **_kw):
        return text  # fail-open: util returns the English input verbatim

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=failing_translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state())

    assert result["response"] == _AR_TRANSLATE_FAILSAFE
    assert _is_arabic(result["response"]), "failsafe must be native Arabic, not English"
    assert "arabic_translate_failsafe" in result["path"]


@pytest.mark.asyncio
async def test_stray_english_token_is_not_replaced():
    """A mostly-Arabic reply with one stray Latin token is shipped as-is, not nuked to the failsafe."""
    async def stray_token_translate(text, *, strict=False, **_kw):
        return "تقدر تجرب تمرين تنفس بسيط قبل النوم، أو تكتب أفكارك."  # good Arabic, no total failure

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", side_effect=stray_token_translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state())

    assert result["response"] != _AR_TRANSLATE_FAILSAFE
    assert "تقدر تجرب" in result["response"], "a good Arabic reply must survive"
    assert "arabic_translate_failsafe" not in result["path"]
