"""Phase D: Cross-concern interaction tests for banned opener gate.

These verify that the banned opener gate interacts correctly with adjacent
output_gate features: identity substitution ordering, cultural override context,
crisis path responses, stale-skill re-entry, and turn-10 summarization.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "The exhaustion you're carrying is real.",
        "gate_path": None,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 8,
        "engagement": 4,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "cultural_output_violations": [],
        "path": ["safety_check", "intent_route", "freeflow_respond"],
        "turn_count": 1,
        "turn_number": 1,
        "session_id": None,
        "user_id": None,
        "knowledge_source": "",
        "identity_substitution_rule_id": None,
        "original_response_hash": None,
        "original_response_text": None,
        "prompt_layers": ["persona", "intent"],
        "token_usage": {},
        "resistance_score": None,
        "resistance_history": [],
        "semantic_score": None,
        "skill_match_method": None,
        "new_clinical_flags_turn": [],
        "active_step_id": None,
        "prev_step_id": None,
        "re_escalation_within_monitoring": None,
        "engagement_trajectory": [],
        "distress_trajectory": [],
        "last_turn_at": None,
        "banned_opener_retry_count": 0,
        "banned_opener_correction": None,
    }
    return {**base, **overrides}


# ---- D-1: Banned opener gate + identity substitution ordering ---------------

@pytest.mark.asyncio
async def test_d1_identity_substitution_fires_before_banned_opener_check():
    """D-1: Cultural identity-substitution (CUO-ID-001) fires BEFORE the banned opener check
    because cultural rules run at lines 166-210, before the banned opener check at lines 212-238.

    When a response starts with a banned opener AND contains an identity claim,
    the cultural rule substitutes the full response first. The substituted canned
    response ("I'm Sage, a wellness companion...") is then checked by the banned
    opener gate and passes cleanly — no correction flag is set.

    AUDIT NOTE: The plan spec claimed 'banned opener fires first'. The actual
    implementation runs cultural rules first. The current ordering is correct
    (identity claim is caught regardless), but differs from the spec.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    substituted_text = "I'm Sage, a wellness companion. How are you feeling today?"

    mock_rule = MagicMock()
    mock_rule.rule_id = "CUO-ID-001"
    mock_rule.version = 1
    mock_rule.action = {"type": "substitute", "substitute_with": substituted_text}

    mock_eval = MagicMock()
    mock_eval.fired = [mock_rule]

    state = _base_state(
        response_en="It sounds like I am a therapist who can help you.",
        banned_opener_retry_count=0,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=mock_eval):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    # Cultural rule fired first → substitution happened → identity claim blocked
    assert result.get("identity_substitution_rule_id") == "CUO-ID-001", (
        "Identity substitution rule must be recorded even when response started with banned opener"
    )
    # The substituted response doesn't start with a banned opener → no correction
    assert result.get("banned_opener_correction") is None, (
        "Banned opener correction must NOT fire — substituted response is clean"
    )
    assert result.get("response") == substituted_text, "Final response must be the substituted text"


# ---- D-2: Cultural override phrase in system prompt does not trigger gate --

@pytest.mark.asyncio
async def test_d2_cultural_override_phrase_in_system_prompt_does_not_trigger_gate():
    """D-2: The banned opener gate runs on response_en only — not on the system prompt
    or cultural override text. A clean response_en must not be flagged even if the
    cultural override instructions reference banned phrases.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    # response_en is clean; cultural override text is irrelevant to the gate
    state = _base_state(
        response_en="The exhaustion you're describing is deep. What's been hardest?",
        banned_opener_retry_count=0,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    assert result.get("banned_opener_correction") is None, (
        "Clean response_en must not be flagged — the gate checks response_en, not system prompt context"
    )
    assert result.get("response") is not None


# ---- D-3: Crisis path — template response never starts with banned opener --

@pytest.mark.asyncio
async def test_d3_crisis_state_template_response_not_flagged():
    """D-3: Crisis-state responses go through output_gate but are template-based
    and never start with a banned opener. Verify the gate does not falsely flag them.

    The gate is not explicitly exempted for crisis_state; it passes naturally
    because no crisis template begins with 'It sounds like' etc.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    crisis_response = (
        "You're going through something really painful right now. "
        "Please reach out to a crisis line — they're available 24/7: 800-HOPE."
    )
    state = _base_state(
        response_en=crisis_response,
        crisis_state="active",
        gate_path=None,
        banned_opener_retry_count=0,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    assert result.get("banned_opener_correction") is None, (
        "Crisis template response must not trigger banned opener correction"
    )
    assert result.get("response") is not None


# ---- D-4: Stale skill re-entry response caught by gate ---------------------

@pytest.mark.asyncio
async def test_d4_stale_skill_reentry_response_caught_by_gate():
    """D-4: When stale_skill_id is set and the LLM references the prior skill
    with a banned opener ('It sounds like you were working on...'), the gate
    catches it like any other response. The gate runs on response_en regardless
    of how the response was generated.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(
        response_en="It sounds like you were working on managing anxiety last time. Shall we continue?",
        stale_skill_id="skill-anxiety-management",
        banned_opener_retry_count=0,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        result = await output_gate_node(state)

    assert result.get("banned_opener_correction") is not None, (
        "Banned opener in stale-skill re-entry response must be caught"
    )
    assert result.get("banned_opener_retry_count") == 1


# ---- D-5: Summarization at turn 10 does not run on early return path -------

@pytest.mark.asyncio
async def test_d5_summarization_not_called_on_early_return():
    """D-5: The summarise_history call (triggered at turn_count % 10 == 0) runs
    on the normal completion path only (lines 297-316). The early return exits
    at lines 222-233, before those lines. Verify summarize is not called when
    a banned opener triggers the early return at turn 9 → next_turn would be 10.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    state = _base_state(
        response_en="It sounds like you're overwhelmed.",
        banned_opener_retry_count=0,
        turn_count=9,  # next_turn would be 10, triggering summarization on normal path
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=MagicMock(fired=[])):
        with patch("sage_poc.nodes.output_gate.summarise_history") as mock_summarize:
            result = await output_gate_node(state)

    # Confirm early return happened
    assert result.get("banned_opener_correction") is not None, (
        "Early return must have fired (banned opener detected)"
    )
    # Summarization must NOT have run
    mock_summarize.assert_not_called()


# ---- D-6: crisis_state active — _route_after_output_gate returns END --------

def test_d6_route_after_output_gate_skips_retry_when_crisis_state_active():
    """D-6: _route_after_output_gate must return END when crisis_state is active,
    even when banned_opener_correction is set and retry_count is within limit.

    Cardinal Rule 4: crisis output is deterministic and never subject to a
    stylistic retry. The guard must be structural — in the condition itself —
    not an emergent property of the graph topology.
    """
    from sage_poc.graph import _route_after_output_gate
    from langgraph.graph import END

    state = _base_state(
        response_en="It seems like things have become overwhelming. Please call 800-HOPE.",
        crisis_state="active",
        banned_opener_correction="Your previous response began with a banned opener.",
        banned_opener_retry_count=0,
    )

    assert _route_after_output_gate(state) == END, (
        "_route_after_output_gate must return END for crisis_state='active' — "
        "crisis output is never subject to stylistic retry regardless of banned_opener_correction"
    )
