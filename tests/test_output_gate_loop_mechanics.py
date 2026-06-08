"""Phase C: Graph-level retry loop mechanics tests.

These simulate the state-machine behaviour of the full retry loop:
output_gate early return → routing decision → freeflow re-generation → final pass.
Tests cover all four termination paths and verify the retry counter never leaks
across turns.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langgraph.graph import END


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


def _no_violations():
    return MagicMock(fired=[])


# ---- C-1: Single-pass clean response — no loop needed ----------------------

@pytest.mark.asyncio
async def test_c1_single_pass_clean_response_routes_to_end():
    """C-1: A clean response completes output_gate normally and routes to END. No retry occurs."""
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.graph import _route_after_output_gate

    state = _base_state(
        response_en="The exhaustion you're carrying is real. What's been hardest this week?",
        banned_opener_retry_count=0,
        banned_opener_correction=None,
    )

    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result = await output_gate_node(state)

    assert result.get("response") is not None, "Clean response must be finalized"
    assert result.get("banned_opener_retry_count") == 0, "retry_count must stay 0 on clean pass"
    assert result.get("banned_opener_correction") is None
    assert _route_after_output_gate(result) == END


# ---- C-2: First violation → routing → clean retry → END ------------------

@pytest.mark.asyncio
async def test_c2_first_violation_then_clean_retry_routes_to_end():
    """C-2: Banned opener detected → early return → routing to freeflow → clean retry → END.

    Simulates the full loop state machine in two calls to output_gate_node:
    - Pass 1: banned opener → early return with correction flag
    - Pass 2: clean response (freeflow cleared correction) → normal completion
    """
    from sage_poc.nodes.output_gate import output_gate_node
    from sage_poc.graph import _route_after_output_gate

    # Pass 1: banned opener detected, early return
    state_pass1 = _base_state(
        response_en="It sounds like you're overwhelmed.",
        banned_opener_retry_count=0,
    )
    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        result1 = await output_gate_node(state_pass1)

    assert result1.get("banned_opener_retry_count") == 1
    assert result1.get("banned_opener_correction") is not None
    assert result1.get("response") is None or "response" not in result1

    # Routing sends back to freeflow_respond
    assert _route_after_output_gate(result1) == "freeflow_respond"

    # Pass 2: freeflow regenerated a clean response; freeflow_respond clears the correction
    state_pass2 = _base_state(
        response_en="The exhaustion you're carrying is real. What's been hardest?",
        banned_opener_retry_count=1,       # carried from pass 1
        banned_opener_correction=None,     # freeflow_respond clears it before output_gate reruns
    )
    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result2 = await output_gate_node(state_pass2)

    assert result2.get("response") is not None, "Clean retry must produce a finalized response"
    assert result2.get("banned_opener_retry_count") == 0, "retry_count must be reset after clean pass"
    assert result2.get("banned_opener_violation") is False
    assert _route_after_output_gate(result2) == END


# ---- C-3: Both attempts violate → proceed with flag → END (no infinite loop)

@pytest.mark.asyncio
async def test_c3_both_attempts_violate_substitutes_fallback_no_loop():
    """C-3: When both attempts produce banned openers, system substitutes the vetted fallback.
    User receives _VETTED_FALLBACK_RESPONSE, not the banned opener. No infinite loop."""
    from sage_poc.nodes.output_gate import output_gate_node, _VETTED_FALLBACK_RESPONSE
    from sage_poc.graph import _route_after_output_gate

    # Pass 1: banned opener → early return
    state1 = _base_state(
        response_en="It sounds like you're struggling.",
        banned_opener_retry_count=0,
    )
    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        result1 = await output_gate_node(state1)

    assert result1.get("banned_opener_retry_count") == 1
    assert _route_after_output_gate(result1) == "freeflow_respond"

    # Pass 2: freeflow still produced a banned opener; correction cleared by freeflow_respond
    state2 = _base_state(
        response_en="That sounds difficult.",
        banned_opener_retry_count=1,
        banned_opener_correction=None,
    )
    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                result2 = await output_gate_node(state2)

    assert result2.get("response") == _VETTED_FALLBACK_RESPONSE, (
        f"User must receive vetted fallback, not the banned opener. Got: {result2.get('response')!r}"
    )
    assert result2.get("banned_opener_fallback_used") is True
    assert result2.get("banned_opener_violation") is True, (
        "banned_opener_violation must be True when fallback is substituted — "
        "the violation occurred and must be recorded in the audit log"
    )
    assert result2.get("banned_opener_retry_count") == 0, "retry_count must reset for next turn"
    assert _route_after_output_gate(result2) == END, "Routing must return END — no further retry"


# ---- C-4: Retry count resets between turns — no cross-turn leakage --------

@pytest.mark.asyncio
async def test_c4_retry_count_reset_enables_fresh_retry_on_next_turn():
    """C-4: After a clean turn resets retry_count to 0, the next turn's banned opener
    triggers a retry (count=1). Stale counts from a prior turn do not block the retry.
    """
    from sage_poc.nodes.output_gate import output_gate_node

    # Turn N: clean pass → retry_count reset to 0
    clean_state = _base_state(
        response_en="The weight you're carrying is real.",
        banned_opener_retry_count=0,
    )
    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        with patch("sage_poc.nodes.output_gate.async_translate_to_arabic", AsyncMock(return_value="...")):
            with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                clean_result = await output_gate_node(clean_state)

    assert clean_result.get("banned_opener_retry_count") == 0, "Clean turn must reset counter"

    # Turn N+1: banned opener with count=0 (from clean_result) → should trigger one retry
    banned_state = _base_state(
        response_en="It sounds like you're struggling.",
        banned_opener_retry_count=0,  # fresh counter carried from clean turn
    )
    with patch("sage_poc.nodes.output_gate.rules_engine.evaluate", return_value=_no_violations()):
        banned_result = await output_gate_node(banned_state)

    assert banned_result.get("banned_opener_retry_count") == 1, (
        "New turn with fresh count=0 must get one retry, not be blocked"
    )
    assert banned_result.get("banned_opener_correction") is not None
