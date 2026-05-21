# tests/test_skill_select.py
from sage_poc.nodes.skill_select import skill_select_node


def _ss_state(**overrides):
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


def test_monitoring_state_always_selects_post_crisis_check_in():
    """When crisis_state=='monitoring', skill_select bypasses keyword/semantic and returns post_crisis_check_in."""
    state = _ss_state(
        message_en="I feel a bit calmer now",
        crisis_state="monitoring",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["skill_match_method"] == "post_crisis_auto_select"
    assert result["active_step_id"] == "acknowledge_and_check"


def test_monitoring_state_continues_from_current_step_if_already_in_skill():
    """If post_crisis_check_in is already active on step 2, skill_select preserves that step."""
    state = _ss_state(
        message_en="I feel a bit calmer",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["active_step_id"] == "bridge_or_close"


def test_normal_state_not_affected_by_post_crisis_check_in_in_registry():
    """post_crisis_check_in's empty target_presentations must not match via keyword or semantic."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="none",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] != "post_crisis_check_in"


def test_resolved_state_falls_through_to_normal_skill_matching():
    """In resolved state, skill_select must use normal keyword/semantic matching, not auto-select."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="resolved",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword"


def test_skill_executor_sets_resolved_when_post_crisis_skill_completes():
    """skill_executor_node must write crisis_state='resolved' when post_crisis_check_in finishes."""
    from sage_poc.nodes.skill_executor import skill_executor_node
    state = _ss_state(
        message_en="I feel much steadier now and I think I am okay to continue with my day",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
        emotional_intensity=3,
        engagement=8,
    )
    result = skill_executor_node(state)
    assert result["active_skill_id"] is None, "Skill must be cleared when bridge_or_close completes"
    assert result["crisis_state"] == "resolved", (
        "crisis_state must transition to 'resolved' when post_crisis_check_in finishes"
    )
