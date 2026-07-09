"""Native-AR monitoring-fallback bypass (#1 fix).

The empty-reply fail-safe on a post-crisis MONITORING turn re-surfaces the crisis helpline. On an
Arabic turn this must be served from a natively-authored ar_uae crisis_content rule, selected by
locale, and must NOT transit the translate-out LLM — mirroring the acute crisis card. The digits
come deterministically from CRISIS_CONFIG; routing them through the translator risks digit
corruption of a correct number (the direct-harm failure mode this fixes).
"""
import pytest
from unittest.mock import AsyncMock, patch

from sage_poc.config import CRISIS_CONFIG
from sage_poc.nodes.output_gate import output_gate_node


def make_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "ar",
        "message_en": "", "response_en": "",  # empty generation -> fail-safe fires
        "raw_message": "ما زلت أشعر بالسوء",
        "is_safe": True, "crisis_state": "monitoring", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None, "active_step_id": None,
        "emotional_intensity": 5, "engagement": 5, "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_arabic_monitoring_fallback_is_native_and_bypasses_translate():
    """AR monitoring blank turn -> native AR helpline copy, translate-out NEVER called."""
    translate = AsyncMock(return_value="TRANSLATOR_WAS_CALLED")

    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", new=translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state())

    translate.assert_not_called()  # bypass proof — the whole point of the fix
    resp = result["response"]
    # Native Arabic (contains Arabic script) and carries the deterministic config number verbatim.
    assert any("؀" <= ch <= "ۿ" for ch in resp), f"expected Arabic output, got: {resp!r}"
    assert CRISIS_CONFIG["number"] in resp, f"crisis number must be verbatim from config, got: {resp!r}"
    assert "output_gate_empty_fallback" in result["path"]


@pytest.mark.asyncio
async def test_english_monitoring_fallback_still_served():
    """EN monitoring blank turn -> EN helpline copy, no translate-out."""
    translate = AsyncMock(return_value="SHOULD_NOT_TRANSLATE_EN")
    with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", new=translate), \
         patch("sage_poc.nodes.output_gate.write_session_audit", new=AsyncMock()), \
         patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state(detected_language="en", raw_message="I still feel bad"))

    translate.assert_not_called()
    resp = result["response"]
    assert CRISIS_CONFIG["number"] in resp
    assert "output_gate_empty_fallback" in result["path"]
