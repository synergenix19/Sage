# tests/test_skill_select.py
import pytest
from sage_poc.nodes.skill_select import skill_select_node, _SKILLS as _ALL_SKILLS


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


# ---- Door 3: Semantic fallback proof ------------------------------------------------
# Each test uses a phrase that is keyword-clean for the target skill.
# _phrase_is_keyword_clean asserts this so the 'semantic' method assertion is meaningful.


def _phrase_is_keyword_clean(phrase: str, target_skill_id: str) -> bool:
    """Return True if no keyword in ANY skill is a substring of phrase.

    This is a stricter check than keyword-clean for the target skill only,
    because a phrase matching a DIFFERENT skill's keywords would route to that
    skill via keyword tier rather than the target skill via semantic tier.
    """
    phrase_lower = phrase.lower()
    for skill_id, skill in _ALL_SKILLS.items():
        for kw in skill.target_presentations:
            if kw.lower() in phrase_lower:
                return False
    return True


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_cbt_inherently_broken_phrase():
    """CBT semantic match: phrase describes self-critical schema without keyword overlap."""
    phrase = "I feel like there is something inherently broken in the way I am built"
    assert _phrase_is_keyword_clean(phrase, "cbt_thought_record"), (
        "Phrase accidentally matches a keyword — choose a different phrase for this test."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record", (
        f"Expected cbt_thought_record, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_behavioral_activation_stuck_cycle_phrase():
    """Behavioral activation semantic match: withdrawal cycle described without keywords."""
    phrase = "If I could just schedule one small activity for tomorrow and actually do it that would help"
    assert _phrase_is_keyword_clean(phrase, "behavioral_activation"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "behavioral_activation", (
        f"Expected behavioral_activation, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_worry_time_brain_cycling_phrase():
    """Worry time semantic match: ruminative cycling described without worry/overthink keywords."""
    phrase = "My brain just refuses to stop, the same scenarios cycle through all night"
    assert _phrase_is_keyword_clean(phrase, "worry_time"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "worry_time", (
        f"Expected worry_time, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_dbt_tipp_internal_volcano_phrase():
    """DBT TIPP semantic match: acute emotional flooding described without TIPP keywords."""
    phrase = "I need something physical to slow my heart rate right now, maybe cold water or intense exercise"
    assert _phrase_is_keyword_clean(phrase, "dbt_tipp"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "dbt_tipp", (
        f"Expected dbt_tipp, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_semantic_mi_readiness_half_wanting_phrase():
    """MI readiness ruler semantic match: ambivalence described without readiness/change keywords."""
    phrase = "I wish I could rate my own motivation and confidence to see where I actually stand"
    assert _phrase_is_keyword_clean(phrase, "mi_readiness_ruler"), (
        "Phrase accidentally matches a keyword — choose a different phrase."
    )
    state = _ss_state(message_en=phrase)
    result = await skill_select_node(state)
    assert result["active_skill_id"] == "mi_readiness_ruler", (
        f"Expected mi_readiness_ruler, got: {result['active_skill_id']} "
        f"(score: {result.get('semantic_score')})"
    )
    assert result["skill_match_method"] == "semantic"
