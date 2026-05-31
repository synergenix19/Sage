"""Parametrized tests for the three LangGraph conditional routing functions.

These tests exercise every branch of _route_after_safety, _route_after_intent,
and _route_after_skill_select without invoking the full graph. They are fast,
deterministic, and serve as the canonical documentation of routing logic.
"""
import pytest
from sage_poc.graph import _route_after_safety, _route_after_intent, _route_after_skill_select, _route_after_skill_executor


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
    ("info_request",       0.8,  None,                "skill_select"),
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


# --- _route_after_safety with monitoring state ---

def test_route_safe_in_monitoring_when_s1_s6_safe_and_s7_recovering():
    """In monitoring state with S1-S6 clear and S7=RECOVERING, route to safe."""
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="RECOVERING",
    )
    assert _route_after_safety(state) == "safe"


def test_route_safe_in_monitoring_when_s7_still_distressed():
    """STILL_DISTRESSED does NOT re-route to crisis -- post_crisis_check_in handles it."""
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="STILL_DISTRESSED",
    )
    assert _route_after_safety(state) == "safe"


def test_route_safe_in_monitoring_when_s7_unclear():
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="UNCLEAR",
    )
    assert _route_after_safety(state) == "safe"


def test_route_crisis_in_monitoring_when_s7_new_crisis():
    """S7=NEW_CRISIS re-routes to crisis even when S1-S6 didn't fire."""
    state = make_full_state(
        is_safe=True,
        crisis_state="monitoring",
        s7_result="NEW_CRISIS",
    )
    assert _route_after_safety(state) == "crisis"


def test_route_crisis_in_monitoring_when_s1_s6_fire():
    """Direct S1-S6 crisis flag always routes to crisis regardless of monitoring state."""
    state = make_full_state(
        is_safe=False,
        crisis_state="monitoring",
        s7_result="STILL_DISTRESSED",
    )
    assert _route_after_safety(state) == "crisis"


def test_info_request_no_active_skill_routes_to_knowledge_retrieve():
    state = make_full_state(
        primary_intent="info_request",
        active_skill_id=None,
        crisis_state="none",
    )
    assert _route_after_skill_select(state) == "knowledge_retrieve"


def test_info_request_with_active_skill_routes_to_skill_executor():
    """Mid-protocol info question must go to executor, not knowledge_retrieve."""
    state = make_full_state(
        primary_intent="info_request",
        active_skill_id="cbt_thought_record",
        crisis_state="none",
    )
    assert _route_after_skill_select(state) == "skill_executor"


def test_non_info_request_no_skill_routes_to_freeflow():
    state = make_full_state(
        primary_intent="general_chat",
        active_skill_id=None,
    )
    assert _route_after_skill_select(state) == "freeflow"


# --- _route_after_skill_executor ---

def test_route_after_skill_executor_re_escalation_routes_to_crisis():
    """skill_executor detects re-escalation (s7_result=NEW_CRISIS) → crisis_response."""
    state = make_full_state(re_escalation_within_monitoring=True)
    assert _route_after_skill_executor(state) == "crisis"


def test_route_after_skill_executor_no_re_escalation_routes_to_freeflow():
    """Normal skill execution (no re-escalation) → freeflow_respond."""
    state = make_full_state(re_escalation_within_monitoring=False)
    assert _route_after_skill_executor(state) == "freeflow"


def test_route_after_skill_executor_none_routes_to_freeflow():
    """re_escalation_within_monitoring=None (initial state) → freeflow_respond."""
    state = make_full_state(re_escalation_within_monitoring=None)
    assert _route_after_skill_executor(state) == "freeflow"


def test_route_after_skill_executor_monitoring_no_reescalation_routes_to_freeflow():
    """Monitoring session with STILL_DISTRESSED (S7 not NEW_CRISIS) → freeflow."""
    state = make_full_state(
        crisis_state="monitoring",
        s7_result="STILL_DISTRESSED",
        re_escalation_within_monitoring=False,
    )
    assert _route_after_skill_executor(state) == "freeflow"

# ── New skill routing disambiguation tests (2026-05-31) ────────────────────
# skill_select_node is async; asyncio_mode = "auto" in pyproject.toml handles this.
# Tier 1 routing = exact substring match against target_presentations in SKILL_REGISTRY order.
# Tests embed exact target_presentation phrases so routing is deterministic (Tier 1, no LLM).

async def test_cognitive_restructuring_routes_for_unhelpful_thinking_pattern():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="My thinking patterns are unhelpful and I need to break them",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "cognitive_restructuring", (
        f"Expected cognitive_restructuring, got {result.get('active_skill_id')!r}. "
        "Confirm 'thinking patterns are unhelpful' is in cognitive_restructuring.target_presentations."
    )


async def test_cbt_thought_record_routes_for_catastrophizing():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I keep catastrophizing about everything that could go wrong",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "cbt_thought_record", (
        f"Expected cbt_thought_record, got {result.get('active_skill_id')!r}"
    )


async def test_interpersonal_effectiveness_routes_for_relationship_navigation():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I have relationship problems in my family and don't know how to navigate them",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "interpersonal_effectiveness", (
        f"Expected interpersonal_effectiveness, got {result.get('active_skill_id')!r}"
    )


async def test_assertive_communication_routes_for_boundary_expression():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I want to practice saying no to people who ask too much of me",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "assertive_communication", (
        f"Expected assertive_communication, got {result.get('active_skill_id')!r}"
    )


async def test_financial_anxiety_routes_for_gulf_financial_distress():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="My visa depends on my job and the thought of unemployment terrifies me",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "financial_anxiety", (
        f"Expected financial_anxiety, got {result.get('active_skill_id')!r}"
    )


async def test_grief_loss_routes_for_bereavement():
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I lost my father recently and I don't know how to grieve",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") == "grief_loss", (
        f"Expected grief_loss, got {result.get('active_skill_id')!r}"
    )


async def test_financial_anxiety_does_not_capture_general_anxiety():
    # Lane-keeping: asserts financial_anxiety stays in its lane.
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="I feel anxious all the time and my heart races",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "financial_anxiety", (
        f"financial_anxiety captured a general anxiety trigger. Got: {result.get('active_skill_id')!r}"
    )


async def test_grief_loss_does_not_capture_relationship_conflict():
    # Lane-keeping: asserts grief_loss stays in its lane.
    from sage_poc.nodes.skill_select import skill_select_node
    state = make_full_state(
        message_en="My relationship broke down and I need to work through the conflict",
        primary_intent="new_skill",
        intent_confidence=0.9,
    )
    result = await skill_select_node(state)
    assert result.get("active_skill_id") != "grief_loss", (
        f"grief_loss captured a relationship conflict trigger. Got: {result.get('active_skill_id')!r}"
    )
