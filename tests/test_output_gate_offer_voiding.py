"""S1-1a — offer voiding on fallback substitution (PR #4 audit merge-blocker).

Invariant: user-visible offer <=> promotable state. When output_gate exhausts the
banned-opener retry and substitutes _VETTED_FALLBACK_RESPONSE, the user sees generic
fallback text instead of the offer options. If the offer was created THIS turn
("skill_offer_made" in this turn's path), it must be voided — otherwise the next
turn can promote a skill the user never saw (observed live, audit session r1-04).

An offer created on an EARLIER turn (user already saw it) must NOT be cleared:
re-rendering it next turn is the correct behaviour there.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "response_en": "It sounds like you're really overwhelmed. What's been hardest?",
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
        "offered_skill_ids": None,
    }
    return {**base, **overrides}


def _run_gate(state):
    from sage_poc.nodes.output_gate import output_gate_node

    async def _call():
        with patch("sage_poc.nodes.output_gate.rules_engine.evaluate",
                   return_value=MagicMock(fired=[])):
            with patch("sage_poc.nodes.output_gate.async_translate_to_arabic",
                       AsyncMock(return_value="...")):
                with patch("sage_poc.nodes.output_gate.write_session_audit", AsyncMock()):
                    return await output_gate_node(state)
    return _call()


# RETIRED in #58: test_fallback_substitution_voids_offer_created_this_turn tested voiding on the
# retry-exhausted banned-opener substitution. That substitution no longer happens — a banned opener
# is now rewritten or passed through, both of which PRESERVE the offer text, so the user still sees
# the offer and there is nothing to void. The surviving displacing path (the empty fail-safe) is
# covered by test_empty_response_voids_offer_created_this_turn below.

@pytest.mark.asyncio
async def test_empty_response_voids_offer_created_this_turn():
    """#58 (re-pointed to the surviving path): an EMPTY response on an offer-creating turn triggers
    the empty fail-safe (generic text replaces the offer the user never saw), so the offer must be
    voided (offered_skill_ids -> None) with the offer_voided_fallback marker. The voiding invariant
    was re-homed from the removed banned-opener-fallback path to this empty fail-safe path."""
    state = _base_state(
        response_en="",
        offered_skill_ids=["worry_time"],
        path=["safety_check", "intent_route", "skill_select",
              "skill_offer_made", "freeflow_respond"],
    )

    result = await _run_gate(state)

    assert "output_gate_empty_fallback" in result.get("path", []), "empty fail-safe must fire"
    assert "offered_skill_ids" in result and result["offered_skill_ids"] is None, (
        f"Unseen offer must be voided on the empty fail-safe. Got: {result.get('offered_skill_ids')!r}"
    )
    assert "offer_voided_fallback" in result.get("path", [])


@pytest.mark.asyncio
async def test_empty_fallback_preserves_offer_from_prior_turn():
    """#58 (re-pointed): an offer from an EARLIER turn ("skill_offer_made" NOT in this turn's path)
    must NOT be voided when this turn degrades to the empty fail-safe — re-rendering next turn is
    correct there. Protects the prior-turn-preservation half of the invariant on the surviving path."""
    state = _base_state(
        response_en="",
        offered_skill_ids=["worry_time"],
        path=["safety_check", "intent_route", "freeflow_respond"],
    )

    result = await _run_gate(state)

    assert "output_gate_empty_fallback" in result.get("path", []), "empty fail-safe must fire"
    assert "offered_skill_ids" not in result, (
        "Prior-turn offer must survive a degraded reply — output_gate must not void it"
    )
    assert "offer_voided_fallback" not in result.get("path", [])


@pytest.mark.asyncio
async def test_normal_offer_turn_leaves_offer_untouched():
    """Clean (non-fallback) offer turn: the user saw the offer, so output_gate
    must not touch offered_skill_ids."""
    state = _base_state(
        response_en="Would you like to try a worry time exercise, or keep talking?",
        banned_opener_retry_count=0,
        offered_skill_ids=["worry_time"],
        path=["safety_check", "intent_route", "skill_select",
              "skill_offer_made", "freeflow_respond"],
    )

    result = await _run_gate(state)

    assert result.get("banned_opener_fallback_used") is False
    assert "offered_skill_ids" not in result, (
        "Normal offer turn: offered_skill_ids must be absent from the update "
        "so skill_select's value survives the channel merge"
    )
    assert "offer_voided_fallback" not in result.get("path", [])
