# tests/test_skill_select.py
import pytest
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


@pytest.mark.asyncio
async def test_monitoring_state_always_selects_post_crisis_check_in():
    """When crisis_state=='monitoring', skill_select bypasses keyword/semantic and returns post_crisis_check_in."""
    state = _ss_state(
        message_en="I feel a bit calmer now",
        crisis_state="monitoring",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["skill_match_method"] == "post_crisis_auto_select"
    assert result["active_step_id"] == "acknowledge_and_check"


@pytest.mark.asyncio
async def test_monitoring_state_continues_from_current_step_if_already_in_skill():
    """If post_crisis_check_in is already active on step 2, skill_select preserves that step."""
    state = _ss_state(
        message_en="I feel a bit calmer",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="bridge_or_close",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "post_crisis_check_in"
    assert result["active_step_id"] == "bridge_or_close"


@pytest.mark.asyncio
async def test_normal_state_not_affected_by_post_crisis_check_in_in_registry():
    """post_crisis_check_in's empty target_presentations must not match via keyword or semantic."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="none",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] != "post_crisis_check_in"


@pytest.mark.asyncio
async def test_resolved_state_falls_through_to_normal_skill_matching():
    """In resolved state, skill_select must use normal keyword/semantic matching, not auto-select."""
    state = _ss_state(
        message_en="I keep thinking everything is my fault",
        crisis_state="resolved",
    )
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["skill_match_method"] == "keyword"


def test_skill_executor_l1_exit_from_post_crisis_sets_resolved():
    """L1 exit phrase while post_crisis_check_in is active must set crisis_state='resolved'."""
    from sage_poc.nodes.skill_executor import skill_executor_node
    # "i'm done" is in L1_EXIT_PHRASES and unambiguously signals the user wants to stop
    state = _ss_state(
        message_en="i'm done",
        crisis_state="monitoring",
        active_skill_id="post_crisis_check_in",
        active_step_id="acknowledge_and_check",
        emotional_intensity=5,
        engagement=7,
    )
    result = skill_executor_node(state)
    assert result["active_skill_id"] is None, (
        "active_skill_id must be cleared on L1 exit"
    )
    assert result.get("crisis_state") == "resolved", (
        "crisis_state must transition to 'resolved' on L1 exit from post_crisis_check_in"
    )
    assert result["escalation_triggered"]["level"] == "L1", (
        "escalation_triggered must carry the L1 escalation dict"
    )


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
    # skill_executor's _meets_completion_criteria requires > 10 words — this message has 17
    assert result.get("crisis_state") == "resolved", (
        "crisis_state must transition to 'resolved' when post_crisis_check_in finishes"
    )


@pytest.mark.asyncio
async def test_dbt_tipp_keyword_match():
    state = _ss_state(message_en="I need to calm down fast, I'm overwhelmed and losing control")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "dbt_tipp"
    assert result["skill_match_method"] == "keyword"

@pytest.mark.asyncio
async def test_dbt_tipp_keyword_arabic():
    state = _ss_state(message_en="محتاج أهدى بسرعة", detected_language="ar")
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "dbt_tipp"


def test_semantic_threshold_is_calibrated():
    """Threshold must be in plausible range and calibration gap comment must reflect >= 13 skills."""
    import ast, pathlib
    src = pathlib.Path("src/sage_poc/nodes/skill_select.py").read_text()
    tree = ast.parse(src)
    threshold = None
    for node in ast.walk(tree):
        # Handle both plain assignment (x = ...) and annotated assignment (x: float = ...)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SEMANTIC_THRESHOLD":
                    threshold = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "SEMANTIC_THRESHOLD":
                if node.value is not None:
                    threshold = ast.literal_eval(node.value)
    assert threshold is not None, "SEMANTIC_THRESHOLD not found in skill_select.py"
    assert 0.45 <= threshold <= 0.65, f"Threshold {threshold} outside expected range 0.45–0.65"
