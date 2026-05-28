"""Experiment 4.6 — Layer 1: routing invariance tests.

Tests that secondary_intent does NOT change the routing decision.
_route_after_intent routes on primary_intent only; secondary is
carried in state for prompt injection but is ignored for routing.
"""
import pytest

from sage_poc.graph import _route_after_intent
from tests.experiment_4_6.scenarios import ALL_SCENARIOS
from tests.experiment_4_6.conftest import make_compose_state


# ── Test 1: routing follows primary for all 20 scenarios ─────────────────────

@pytest.mark.parametrize("scenario", ALL_SCENARIOS, ids=[s["id"] for s in ALL_SCENARIOS])
def test_routing_follows_primary_for_all_scenarios(scenario):
    """_route_after_intent must return expected_route for all 20 blended scenarios.

    Routing is determined solely by primary_intent + active_skill_id + confidence.
    The secondary_intent field is present in state but must not change the output.
    """
    state = make_compose_state(
        primary_intent=scenario["primary_intent"],
        secondary_intent=scenario["secondary_intent"],
        active_skill_id=scenario["active_skill_id"],
        intent_confidence=scenario["confidence"],
    )
    result = _route_after_intent(state)
    assert result == scenario["expected_route"], (
        f"{scenario['id']} ({scenario['description']}): "
        f"primary={scenario['primary_intent']!r}, secondary={scenario['secondary_intent']!r}, "
        f"active_skill={scenario['active_skill_id']!r}, confidence={scenario['confidence']} "
        f"→ expected route={scenario['expected_route']!r}, got {result!r}"
    )


# ── Test 2: crisis overrides any secondary ────────────────────────────────────

_CRISIS_SCENARIOS = [s for s in ALL_SCENARIOS if s["id"] in ("B16", "B17")]


@pytest.mark.parametrize("scenario", _CRISIS_SCENARIOS, ids=[s["id"] for s in _CRISIS_SCENARIOS])
def test_crisis_overrides_any_secondary(scenario):
    """Crisis primary intent must always route to 'crisis' regardless of secondary."""
    state = make_compose_state(
        primary_intent="crisis",
        secondary_intent=scenario["secondary_intent"],
        active_skill_id=scenario["active_skill_id"],
        intent_confidence=scenario["confidence"],
    )
    assert _route_after_intent(state) == "crisis", (
        f"{scenario['id']}: crisis primary with secondary={scenario['secondary_intent']!r} "
        f"must route to 'crisis'"
    )


# ── Test 3: scope_refusal overrides secondary ─────────────────────────────────

_SCOPE_SCENARIOS = [s for s in ALL_SCENARIOS if s["id"] in ("B19", "B20")]


@pytest.mark.parametrize("scenario", _SCOPE_SCENARIOS, ids=[s["id"] for s in _SCOPE_SCENARIOS])
def test_scope_refusal_overrides_secondary(scenario):
    """scope_refusal primary intent must always route to 'gate' regardless of secondary."""
    state = make_compose_state(
        primary_intent="scope_refusal",
        secondary_intent=scenario["secondary_intent"],
        active_skill_id=None,
        intent_confidence=scenario["confidence"],
    )
    assert _route_after_intent(state) == "gate", (
        f"{scenario['id']}: scope_refusal with secondary={scenario['secondary_intent']!r} "
        f"must route to 'gate'"
    )


# ── Test 4: secondary does not change route for a fixed primary ───────────────

@pytest.mark.parametrize("secondary_intent", [
    "info_request",
    "general_chat",
    "exit_skill",
    None,
])
def test_secondary_does_not_change_route(secondary_intent):
    """For primary_intent='new_skill', varying secondary must always yield 'skill_select'."""
    state = make_compose_state(
        primary_intent="new_skill",
        secondary_intent=secondary_intent,
        active_skill_id=None,
        intent_confidence=0.85,
    )
    result = _route_after_intent(state)
    assert result == "skill_select", (
        f"primary='new_skill', secondary={secondary_intent!r} → expected 'skill_select', got {result!r}"
    )
