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


# RETIRED in #58 (mechanism removed): C-2 / C-3 / C-4 exercised the banned-opener retry LOOP state
# machine — early-return with a correction flag, freeflow re-entry (_route_after_output_gate ->
# "freeflow_respond"), retry_count carry/reset, and canned-fallback-on-second-violation. That entire
# loop was removed: a banned opener is now fixed by a SINGLE inline rewrite in output_gate (no second
# generation, no re-entry), so the "no infinite loop" property these guarded is now structural (there
# is no loop). The single-pass contract (rewrite / pass-through / no re-entry) is covered by
# test_banned_opener_rewrite.py and the migrated tests in test_output_gate_banned_opener.py.
