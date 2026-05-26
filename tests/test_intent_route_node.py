"""Integration tests for intent_route_node: LLM response parsing and state output.

These tests mock resilient_invoke to return controlled JSON strings.
They verify that intent_route_node correctly parses the LLM output and
writes all expected fields to state — including secondary_intent (RT-2).

test_routing.py covers the routing functions (_route_after_intent, etc.) with
pre-set state values. These tests are the complementary layer: they prove the
node itself produces the state values that the routing functions rely on.
"""
import pytest
from unittest.mock import AsyncMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "message_en": "I've been feeling down for weeks",
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
async def test_rt2_secondary_intent_parsed_and_written():
    """RT-2: secondary_intent must be written to state when LLM returns a blended intent."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "new_skill", "secondary_intent": "info_request", '
        '"intent_confidence": 0.87, "emotional_intensity": 6, "engagement": 7}'
    )
    state = _base_state(
        message_en="I've been blaming myself for everything — also, is CBT something that could help?",
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "new_skill", (
        f"Expected primary_intent='new_skill', got '{result['primary_intent']}'"
    )
    assert result["secondary_intent"] == "info_request", (
        f"RT-2 FAIL: secondary_intent should be 'info_request', got '{result['secondary_intent']}'"
    )
    assert result["intent_confidence"] == pytest.approx(0.87)
    assert result["emotional_intensity"] == 6
    assert result["engagement"] == 7
    assert "intent_route" in result["path"]


@pytest.mark.asyncio
async def test_secondary_intent_is_none_when_llm_returns_null():
    """When LLM returns secondary_intent: null, state must have secondary_intent=None."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.91, "emotional_intensity": 3, "engagement": 8}'
    )
    state = _base_state(message_en="Hey, how's it going?")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["secondary_intent"] is None


@pytest.mark.asyncio
async def test_intent_route_low_confidence_writes_correct_confidence():
    """When LLM returns low confidence, intent_confidence in state must be < 0.6."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.42, "emotional_intensity": 4, "engagement": 3}'
    )
    state = _base_state(message_en="I don't know... just stuff I guess")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["intent_confidence"] < 0.6, (
        f"Expected intent_confidence < 0.6 for ambiguous message, got {result['intent_confidence']}"
    )
    assert result["intent_confidence"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_intent_route_defaults_to_general_chat_on_malformed_json():
    """Malformed LLM response must not raise — defaults to general_chat with confidence 0.5."""
    from sage_poc.nodes.intent_route import intent_route_node

    state = _base_state(message_en="test message")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value="NOT JSON AT ALL")):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["intent_confidence"] == pytest.approx(0.5)
    assert result["secondary_intent"] is None


@pytest.mark.asyncio
async def test_intent_route_path_appended():
    """intent_route node must append 'intent_route' to the path field."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = (
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.9, "emotional_intensity": 5, "engagement": 5}'
    )
    state = _base_state(path=["safety_check"])

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["path"] == ["safety_check", "intent_route"]
