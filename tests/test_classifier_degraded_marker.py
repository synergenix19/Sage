"""`classifier_degraded` positive path marker (fast-follow ledger 2026-07-28, item Q-a).

C3 discipline: guards assert the POSITIVE path. Today the degraded classifier route
(primary + pinned fallback exhausted -> static neutral fallback serves the turn) is
distinguishable only by inference (no JSON -> general_chat @ confidence 0.5) — a
silence-shaped gap. The marker is the exclusion key for distributional matrix runs
(count/exclude degraded turns per fixture) and separates "low_confidence via genuine
boundary uncertainty" from "low_confidence via classifier unavailability" (RT-1).

Contract (behavior-anchored):
  - PRESENT when the static-fallback shape is detected: no parseable JSON in the
    classifier reply (the same detection the Q-a end-to-end test exercises).
  - ABSENT on healthy turns.
  - ABSENT on GENUINE low-confidence classifications: valid JSON with confidence 0.4
    must NOT carry the marker — that population belongs to Node 3, not to degradation.
Pure additive path marker, no flag (same class as existing lifecycle markers).
"""
import pytest
from unittest.mock import AsyncMock, patch


def _base_state(**overrides) -> dict:
    base = {
        "message_en": "I've been feeling down for weeks",
        "raw_message": "I've been feeling down for weeks",
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


async def _run(mock_response: str, **state_overrides) -> dict:
    from sage_poc.nodes.intent_route import intent_route_node
    state = _base_state(**state_overrides)
    with patch("sage_poc.nodes.intent_route.resilient_invoke",
               AsyncMock(return_value=mock_response)):
        return await intent_route_node(state)


@pytest.mark.asyncio
async def test_marker_present_on_static_fallback_shape():
    """The static neutral fallback is PROSE, not JSON — the exact Q-a shape."""
    result = await _run("I'm here with you. Please give me just a moment.")
    assert "classifier_degraded" in result["path"]
    # and the degraded route still resolves to the neutral defaults it always did
    assert result["primary_intent"] == "general_chat"
    assert result["intent_confidence"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_marker_present_on_unparseable_json():
    result = await _run('{"primary_intent": "general_chat", ')  # truncated -> JSONDecodeError
    assert "classifier_degraded" in result["path"]


@pytest.mark.asyncio
async def test_marker_absent_on_healthy_turn():
    result = await _run(
        '{"primary_intent": "new_skill", "secondary_intent": null, '
        '"intent_confidence": 0.87, "emotional_intensity": 6, "engagement": 7}'
    )
    assert "classifier_degraded" not in result["path"]
    assert result["primary_intent"] == "new_skill"


@pytest.mark.asyncio
async def test_marker_absent_on_genuine_low_confidence():
    """A VALID parse at confidence 0.4 is boundary uncertainty (Node 3's population),
    not degradation — the marker must not conflate the two (RT-1 closure dependency)."""
    result = await _run(
        '{"primary_intent": "general_chat", "secondary_intent": null, '
        '"intent_confidence": 0.4, "emotional_intensity": 4, "engagement": 5}'
    )
    assert "classifier_degraded" not in result["path"]
    assert result["intent_confidence"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_marker_absent_even_when_valid_parse_defaults_confidence():
    """Valid JSON that omits intent_confidence also resolves to 0.5 — but it PARSED, so it
    is not the degraded route. Detection anchors on the parse failure, not on 0.5."""
    result = await _run('{"primary_intent": "info_request"}')
    assert "classifier_degraded" not in result["path"]
    assert result["intent_confidence"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_degraded_marker_coexists_with_intent_route_marker():
    """Additive: the standard lifecycle marker is untouched; degraded is appended, not a swap."""
    result = await _run("no json here")
    assert "intent_route" in result["path"]
    assert result["path"].index("classifier_degraded") > result["path"].index("intent_route")
