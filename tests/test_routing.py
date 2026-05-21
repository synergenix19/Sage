"""Parametrized tests for the three LangGraph conditional routing functions.

These tests exercise every branch of _route_after_safety, _route_after_intent,
and _route_after_skill_select without invoking the full graph. They are fast,
deterministic, and serve as the canonical documentation of routing logic.
"""
import pytest
from sage_poc.graph import _route_after_safety, _route_after_intent, _route_after_skill_select


def make_full_state(**overrides) -> dict:
    defaults = {
        "raw_message": "", "detected_language": "en", "message_en": "",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "none", "s7_result": None, "s7_method": None,
        "distress_trajectory": [], "code_switching": False,
        "primary_intent": None, "secondary_intent": None,
        "intent_confidence": 1.0, "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "escalation_triggered": None,
        "gate_path": None,
        "response_en": None, "response": None, "path": [], "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None, "semantic_score": None,
    }
    return {**defaults, **overrides}


# --- _route_after_safety ---

@pytest.mark.parametrize("is_safe,expected_route", [
    (True,  "safe"),
    (False, "crisis"),
])
def test_route_after_safety(is_safe, expected_route):
    state = make_full_state(is_safe=is_safe)
    assert _route_after_safety(state) == expected_route


# --- _route_after_intent ---

@pytest.mark.parametrize("primary_intent,confidence,active_skill,expected_route", [
    # Crisis always routes to crisis regardless of confidence
    ("crisis",             0.9,  None,                "crisis"),
    ("crisis",             0.3,  "cbt_thought_record", "crisis"),

    # Low confidence short-circuits before intent routing
    ("general_chat",       0.4,  None,                "low_confidence"),
    ("new_skill",          0.55, None,                "low_confidence"),
    ("skill_continuation", 0.59, "cbt_thought_record", "low_confidence"),

    # High-confidence normal routing
    ("general_chat",       0.9,  None,                "freeflow"),
    ("info_request",       0.8,  None,                "freeflow"),
    ("new_skill",          0.8,  None,                "skill_select"),
    ("skill_continuation", 0.85, "cbt_thought_record", "skill_executor"),

    # skill_continuation without an active skill → freeflow
    ("skill_continuation", 0.85, None,                "freeflow"),

    # exit_skill with an active skill → skill_executor (executor handles graceful close)
    ("exit_skill",         0.88, "cbt_thought_record", "skill_executor"),

    # exit_skill with no active skill → freeflow (nothing to exit)
    ("exit_skill",         0.88, None,                "freeflow"),

    # Boundary-violation intents bypass skill_select and freeflow_respond
    ("scope_refusal",      0.9,  None,                "gate"),
    ("jailbreak",          0.95, None,                "gate"),
])
def test_route_after_intent(primary_intent, confidence, active_skill, expected_route):
    state = make_full_state(
        primary_intent=primary_intent,
        intent_confidence=confidence,
        active_skill_id=active_skill,
    )
    assert _route_after_intent(state) == expected_route, (
        f"intent={primary_intent!r}, confidence={confidence}, "
        f"active_skill={active_skill!r} → expected {expected_route!r}"
    )


# --- _route_after_skill_select ---

@pytest.mark.parametrize("active_skill,expected_route", [
    ("cbt_thought_record", "skill_executor"),
    (None,                  "freeflow"),
])
def test_route_after_skill_select(active_skill, expected_route):
    state = make_full_state(active_skill_id=active_skill)
    assert _route_after_skill_select(state) == expected_route


# --- Boundary: confidence threshold is strictly < 0.6 ---

def test_route_intent_confidence_boundary_exactly_06_is_not_low():
    """0.6 is the threshold — exactly 0.6 must NOT route to low_confidence."""
    state = make_full_state(primary_intent="general_chat", intent_confidence=0.6)
    assert _route_after_intent(state) == "freeflow"


def test_route_intent_confidence_boundary_059_is_low():
    """0.59 (< 0.6) must route to low_confidence."""
    state = make_full_state(primary_intent="general_chat", intent_confidence=0.59)
    assert _route_after_intent(state) == "low_confidence"
