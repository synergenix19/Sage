import pytest
from unittest.mock import AsyncMock, patch
from sage_poc.nodes.directive_detect import detect_directive_request


def _state(message_en, history=None):
    return {"message_en": message_en, "conversation_history": history or []}


def test_explicit_delegation_phrases_detected():
    for phrase in [
        "just tell me what to do",
        "you tell me",
        "you decide",
        "you pick",
        "I want answers, not questions",
        "stop asking me questions",
        "you need to guide me, not ask me",
        "you're the one with the answers",
        "I don't need more questions",
    ]:
        assert detect_directive_request(_state(phrase)) is True, f"missed: {phrase!r}"


def test_frustration_repair_signal_after_a_question():
    history = [
        {"role": "user", "content": "my dad reacted badly"},
        {"role": "assistant", "content": "How does that usually affect you?"},
    ]
    assert detect_directive_request(_state("why do you keep questioning me", history)) is True


def test_repair_signal_requires_prior_question():
    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "I'm here with you."},
    ]
    assert detect_directive_request(_state("why", history)) is False


def test_genuine_first_question_is_not_directive():
    for phrase in [
        "How do I deal with my father's response like this?",
        "what should I think about here",
        "I feel anxious",
        "can you help me understand why I feel this way",
    ]:
        assert detect_directive_request(_state(phrase)) is False, f"false positive: {phrase!r}"


# ---------------------------------------------------------------------------
# D4: intent-gated info_request trigger (Step 1 -- failing tests)
# ---------------------------------------------------------------------------

def test_info_request_no_longer_triggers_directive():
    # D4 AMENDMENT (clinical ruling 2026-07-07, recorded against LOCK-QDISC-22): info_request
    # no longer sets directive_posture. A single-intent info_request now closes with one open
    # clarifying QUESTION (Abby-style triage), so answer-first must NOT strip it. Genuine
    # delegation still triggers directive_posture (see the _DIRECTIVE_PHRASES tests above).
    st = {"message_en": "can you give me a list of sleep tips?", "conversation_history": []}
    assert detect_directive_request(st, primary_intent="info_request") is False


def test_emotional_disclosure_question_does_not_trigger():
    # MUST-FIX: a bare question-mark does NOT trigger answer-first.
    # Emotional disclosures phrased as questions stay in Reflect mode so the earned
    # open question is not stripped (the section 5 carve-out).
    for q in ["am I broken?", "why do I always feel like this?", "what's wrong with me?", "is it my fault?"]:
        st = {"message_en": q, "conversation_history": []}
        assert detect_directive_request(st, primary_intent="new_skill") is False, q


def test_plain_emotional_disclosure_does_not_trigger():
    st = {"message_en": "i feel so overwhelmed and exhausted lately", "conversation_history": []}
    assert detect_directive_request(st, primary_intent="new_skill") is False


# ---------------------------------------------------------------------------
# Step 3b: audit marker test
# ---------------------------------------------------------------------------

def test_info_request_default_param_does_not_trigger():
    # Callers that omit primary_intent (legacy path) must not regress.
    st = {"message_en": "can you give me a list of sleep tips?", "conversation_history": []}
    assert detect_directive_request(st) is False


# ---------------------------------------------------------------------------
# Step 3b: audit marker in intent_route_node path
# ---------------------------------------------------------------------------

def _base_state(**overrides) -> dict:
    base = {
        "message_en": "what are some sleep hygiene tips?",
        "detected_language": "en",
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "crisis_flags": [],
        "clinical_flags": [],
        "conversation_history": [],
        "therapeutic_profile": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "path": ["safety_check"],
    }
    return {**base, **overrides}


@pytest.mark.asyncio
async def test_no_directive_marker_on_info_request_turn():
    """D4 amendment 2026-07-07: info_request must NOT set directive_posture, so the
    'directive_posture_set' marker is ABSENT and the clarifying question survives output_gate."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "info_request", "secondary_intent": null, '
        '"intent_confidence": 0.92, "emotional_intensity": 2, "engagement": 6}'
    )
    state = _base_state(message_en="what are some sleep hygiene tips?")
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["directive_posture"] is False, "D4 amendment: info_request must NOT set directive_posture"
    assert "directive_posture_set" not in result["path"], (
        f"'directive_posture_set' must be ABSENT on info_request after the amendment: {result['path']}"
    )


@pytest.mark.asyncio
async def test_audit_marker_absent_on_general_chat_turn():
    """Step 3b: 'directive_posture_set' must NOT appear in path for general_chat turns."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.88, "emotional_intensity": 3, "engagement": 5}'
    )
    state = _base_state(message_en="i feel a bit low today")
    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["directive_posture"] is False, "general_chat must not set directive_posture"
    assert "directive_posture_set" not in result["path"], (
        f"audit marker must not appear on non-directive turn: {result['path']}"
    )
