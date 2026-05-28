"""Experiment 4.6 — Layer 1: intent_route_node classification tests.

Tests that intent_route_node correctly parses and writes both primary and
secondary intents from controlled LLM JSON responses. All tests mock
resilient_invoke so no live API key is required.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from tests.experiment_4_6.scenarios import ALL_SCENARIOS
from tests.experiment_4_6.conftest import make_intent_state


def _mock_response(primary_intent: str, secondary_intent, confidence: float = 0.85,
                   emotional_intensity: int = 5, engagement: int = 7) -> str:
    """Build a valid JSON string as the mocked LLM response."""
    return json.dumps({
        "primary_intent": primary_intent,
        "secondary_intent": secondary_intent,
        "intent_confidence": confidence,
        "emotional_intensity": emotional_intensity,
        "engagement": engagement,
    })


# ── Test 1: secondary_intent written for all 20 scenarios ────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=[s["id"] for s in ALL_SCENARIOS])
async def test_secondary_intent_written_for_all_scenarios(scenario):
    """RT-2 (parametrized): intent_route_node must write secondary_intent to state
    for all 20 blended scenarios, matching the value returned by the LLM.
    """
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = _mock_response(
        primary_intent=scenario["primary_intent"],
        secondary_intent=scenario["secondary_intent"],
        confidence=scenario["confidence"],
        emotional_intensity=scenario["emotional_intensity"],
        engagement=scenario["engagement"],
    )
    state = make_intent_state(
        message_en=scenario["message"],
        active_skill_id=scenario["active_skill_id"],
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["secondary_intent"] == scenario["secondary_intent"], (
        f"{scenario['id']}: expected secondary_intent={scenario['secondary_intent']!r}, "
        f"got {result['secondary_intent']!r}"
    )
    assert result["primary_intent"] == scenario["primary_intent"], (
        f"{scenario['id']}: expected primary_intent={scenario['primary_intent']!r}, "
        f"got {result['primary_intent']!r}"
    )


# ── Test 2: null secondary written as None ────────────────────────────────────

@pytest.mark.asyncio
async def test_null_secondary_written_as_none():
    """When the LLM returns secondary_intent: null, state must have secondary_intent=None."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = json.dumps({
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.91,
        "emotional_intensity": 3,
        "engagement": 8,
    })
    state = make_intent_state(message_en="Hey, how's it going?")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == "general_chat"
    assert result["secondary_intent"] is None, (
        f"secondary_intent should be None when LLM returns null, got {result['secondary_intent']!r}"
    )


# ── Test 3: malformed JSON → secondary defaults to None ──────────────────────

@pytest.mark.asyncio
async def test_malformed_json_secondary_defaults_to_none():
    """Malformed LLM response must not raise an exception.

    The node uses re.search + json.loads with try/except; on parse failure,
    data={} so secondary_intent defaults to None via data.get('secondary_intent').
    """
    from sage_poc.nodes.intent_route import intent_route_node

    state = make_intent_state(message_en="This message will get a broken response")

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value="not json")):
        # Must not raise
        result = await intent_route_node(state)

    assert result["secondary_intent"] is None, (
        f"secondary_intent must be None on malformed JSON, got {result['secondary_intent']!r}"
    )
    assert result["primary_intent"] == "general_chat", (
        f"primary_intent must fall back to 'general_chat' on malformed JSON, "
        f"got {result['primary_intent']!r}"
    )


# ── Test 4: primary_intent always written ────────────────────────────────────

_PRIMARY_SAMPLE_SCENARIOS = [s for s in ALL_SCENARIOS if s["id"] in ("B01", "B05", "B16")]


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", _PRIMARY_SAMPLE_SCENARIOS, ids=[s["id"] for s in _PRIMARY_SAMPLE_SCENARIOS])
async def test_primary_intent_always_written(scenario):
    """primary_intent must always be written to state, matching the LLM response."""
    from sage_poc.nodes.intent_route import intent_route_node

    mock_response = _mock_response(
        primary_intent=scenario["primary_intent"],
        secondary_intent=scenario["secondary_intent"],
        confidence=scenario["confidence"],
    )
    state = make_intent_state(
        message_en=scenario["message"],
        active_skill_id=scenario["active_skill_id"],
    )

    with patch("sage_poc.nodes.intent_route.resilient_invoke", AsyncMock(return_value=mock_response)):
        result = await intent_route_node(state)

    assert result["primary_intent"] == scenario["primary_intent"], (
        f"{scenario['id']}: expected primary_intent={scenario['primary_intent']!r}, "
        f"got {result['primary_intent']!r}"
    )
    assert "intent_route" in result["path"]
