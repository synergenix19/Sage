import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.output_gate import output_gate_node


def make_state(**kw):
    base = {
        "gate_path": None, "path": [], "detected_language": "en",
        "message_en": "Same", "response_en": "", "is_safe": True,
        "crisis_state": "none", "crisis_flags": [], "clinical_flags": [],
        "conversation_history": [], "turn_count": 0, "conversation_summary": None,
        "session_id": "s1", "user_id": "u1", "active_skill_id": None,
        "active_step_id": None, "emotional_intensity": 5, "engagement": 5,
        "banned_opener_retry_count": 0,
    }
    return {**base, **kw}


@pytest.mark.asyncio
async def test_empty_response_substituted_on_normal_turn():
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(make_state(response_en=""))
    assert result["response"].strip(), "blank reply must never reach the user"
    assert "output_gate_empty_fallback" in result["path"]


@pytest.mark.asyncio
async def test_empty_response_on_monitoring_turn_resurfaces_resources():
    state = make_state(response_en="", crisis_state="monitoring")
    with patch("sage_poc.nodes.output_gate._log_clinical_review", new=AsyncMock()):
        result = await output_gate_node(state)
    assert "800 46342" in result["response"], "monitoring blank must re-surface the crisis line"
    assert "999" in result["response"]
