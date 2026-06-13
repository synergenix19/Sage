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


@pytest.mark.asyncio
async def test_fallback_substitution_voids_offer_created_this_turn():
    """Retry-exhausted fallback substitution on an offer-creating turn must void
    the offer (offered_skill_ids -> None) and append the audit marker
    "offer_voided_fallback" so the path explains the divergence."""
    state = _base_state(
        response_en="That sounds really tough. I'm here for you.",
        banned_opener_retry_count=1,
        offered_skill_ids=["worry_time"],
        path=["safety_check", "intent_route", "skill_select",
              "skill_offer_made", "freeflow_respond"],
    )

    result = await _run_gate(state)

    assert "offered_skill_ids" in result, (
        "Fallback substitution on an offer-creating turn must include "
        "offered_skill_ids in the state update to void the unseen offer"
    )
    assert result["offered_skill_ids"] is None, (
        f"Unseen offer must be voided. Got: {result['offered_skill_ids']!r}"
    )
    assert "offer_voided_fallback" in result.get("path", []), (
        "Audit trail must carry the offer_voided_fallback path marker"
    )
    # Sanity: fallback actually fired in this scenario
    assert result.get("banned_opener_fallback_used") is True


@pytest.mark.asyncio
async def test_fallback_substitution_preserves_offer_from_prior_turn():
    """Offer created on an EARLIER turn (user already saw it; "skill_offer_made"
    NOT in this turn's path) must NOT be touched when a later reply degrades —
    re-rendering next turn is correct there."""
    state = _base_state(
        response_en="That sounds really tough. I'm here for you.",
        banned_opener_retry_count=1,
        offered_skill_ids=["worry_time"],
        path=["safety_check", "intent_route", "freeflow_respond"],
    )

    result = await _run_gate(state)

    assert result.get("banned_opener_fallback_used") is True
    assert "offered_skill_ids" not in result, (
        "Prior-turn offer must survive a degraded reply — output_gate must not "
        "include offered_skill_ids in the update"
    )
    assert "offer_voided_fallback" not in result.get("path", [])


@pytest.mark.asyncio
async def test_empty_response_on_retry_voids_offer_created_this_turn():
    """Empty response after a retry (response_en="") substitutes the vetted
    fallback and must void an offer created THIS turn — the LLM rate-limit /
    token-budget failure path (output_gate.py ~line 255).  This sub-path is
    distinct from the banned-opener-exhausted branch: the response is empty
    rather than violating, but the offer-voiding invariant is identical because
    the user never saw the offer options in either case."""
    state = _base_state(
        response_en="",
        banned_opener_retry_count=1,
        offered_skill_ids=["worry_time"],
        path=["safety_check", "intent_route", "skill_select",
              "skill_offer_made", "freeflow_respond"],
    )

    result = await _run_gate(state)

    assert result.get("banned_opener_fallback_used") is True, (
        "Empty response on retry must set banned_opener_fallback_used=True"
    )
    assert "offered_skill_ids" in result, (
        "Empty-response fallback on an offer-creating turn must include "
        "offered_skill_ids in the state update to void the unseen offer"
    )
    assert result["offered_skill_ids"] is None, (
        f"Unseen offer must be voided. Got: {result['offered_skill_ids']!r}"
    )
    assert "offer_voided_fallback" in result.get("path", []), (
        "Audit trail must carry the offer_voided_fallback path marker"
    )


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
