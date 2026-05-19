# tests/test_nodes.py
import pytest
from sage_poc.nodes.safety_check import safety_check_node, CRISIS_KEYWORDS

def make_state(**kwargs):
    defaults = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    return {**defaults, **kwargs}

def test_safe_english_message():
    state = make_state(raw_message="I feel sad today")
    result = safety_check_node(state)
    assert result["is_safe"] is True
    assert result["detected_language"] == "en"
    assert result["message_en"] == "I feel sad today"
    assert result["clinical_flags"] == []
    assert "safety_check" in result["path"]

def test_crisis_english_message():
    state = make_state(raw_message="I want to kill myself")
    result = safety_check_node(state)
    assert result["is_safe"] is False
    assert len(result["crisis_flags"]) > 0

def test_crisis_keywords_list_not_empty():
    assert len(CRISIS_KEYWORDS) >= 5

def test_clinical_flag_substance_use():
    state = make_state(raw_message="I've been drinking heavily every night to cope")
    result = safety_check_node(state)
    assert result["is_safe"] is True  # not a crisis
    assert "substance_use" in result["clinical_flags"]
    assert result["crisis_flags"] == []

def test_clinical_flag_trauma():
    state = make_state(raw_message="Someone hurt me and I can't stop thinking about it")
    result = safety_check_node(state)
    assert "trauma_indicator" in result["clinical_flags"]

def test_clinical_flag_medication():
    state = make_state(raw_message="I'm on antidepressants but I don't know the right dosage")
    result = safety_check_node(state)
    assert "medication_mention" in result["clinical_flags"]

def test_no_clinical_flags_for_general_message():
    state = make_state(raw_message="I feel really sad and hopeless today")
    result = safety_check_node(state)
    assert result["clinical_flags"] == []

# Requires Ollama — tests Arabic crisis detection path
@pytest.mark.slow
def test_crisis_arabic_message():
    state = make_state(raw_message="أريد الموت الآن")
    result = safety_check_node(state)
    assert result["is_safe"] is False
    assert result["detected_language"] == "ar"
    assert len(result["crisis_flags"]) > 0

@pytest.mark.slow
def test_araglish_code_switching():
    """Araglish message: Arabic Unicode override classifies as Arabic even mid-English sentence."""
    state = make_state(raw_message="I feel بخير today, maybe things will get better")
    result = safety_check_node(state)
    assert result["detected_language"] == "ar"
    assert result["is_safe"] is True


from unittest.mock import patch, MagicMock
from sage_poc.nodes.intent_route import intent_route_node, build_intent_prompt

def test_intent_prompt_contains_message():
    state = make_state(message_en="I feel like everything is my fault, always", active_skill_id=None)
    prompt = build_intent_prompt(state)
    assert "everything is my fault" in prompt
    assert "active_skill_id" in prompt.lower() or "no active skill" in prompt.lower()

def test_intent_route_with_mocked_llm():
    state = make_state(
        message_en="I keep thinking I'm a failure",
        active_skill_id=None,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "new_skill", "emotional_intensity": 7, "engagement": 6, "intent_confidence": 0.9}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "new_skill"
    assert result["emotional_intensity"] == 7
    assert result["engagement"] == 6
    assert result["intent_confidence"] == 0.9
    assert "intent_route" in result["path"]

def test_intent_route_skill_continuation():
    state = make_state(
        message_en="Hmm, I think maybe it was partly my fault but not entirely",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        conversation_history=[{"role": "assistant", "content": "What thought is going through your mind?"}],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "skill_continuation", "emotional_intensity": 5, "engagement": 7, "intent_confidence": 0.85}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "skill_continuation"
    assert result["engagement"] == 7

def test_intent_route_classifies_exit_skill():
    state = make_state(
        message_en="I don't want to do this anymore, can we stop?",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "exit_skill", "emotional_intensity": 4, "engagement": 3, "intent_confidence": 0.88}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "exit_skill"


from sage_poc.nodes.skill_select import skill_select_node

def test_selects_cbt_for_negative_thought():
    state = make_state(
        message_en="I keep thinking I'm a failure, it's always my fault",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["active_step_id"] == "identify_thought"
    assert "skill_select" in result["path"]

def test_no_skill_for_general_chat():
    state = make_state(
        message_en="What is the weather like?",
        primary_intent="new_skill",
    )
    result = skill_select_node(state)
    assert result["active_skill_id"] is None


from sage_poc.nodes.skill_executor import skill_executor_node, evaluate_step_policy

def test_evaluate_step_policy_high_intensity_triggers_validate_only():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="identify_thought",
        emotional_intensity=9,
        engagement=6,
    )
    assert action["action"] == "validate_only"
    assert "validate" in action["instruction"].lower() or "distress" in action["instruction"].lower()

def test_evaluate_step_policy_normal_intensity_advances_to_next_step():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="identify_thought",
        emotional_intensity=5,
        engagement=6,
    )
    assert action["action"] == "advance"
    assert "goal" in action["instruction"].lower()
    assert action["next_step_id"] == "explore_distortion"
    assert not action.get("skill_complete")

def test_evaluate_step_policy_last_step_marks_skill_complete():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="balanced_thought",
        emotional_intensity=5,
        engagement=7,
    )
    assert action["action"] == "complete"
    assert action["skill_complete"] is True

def test_recovery_from_validate_only_override():
    """High intensity pauses progression; normal intensity resumes on the SAME step."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")

    # Turn N: intensity 9 → validate_only fires, step stays at identify_thought
    high = evaluate_step_policy(
        skill=skill, current_step_id="identify_thought",
        emotional_intensity=9, engagement=7,
    )
    assert high["action"] == "validate_only"
    assert high["next_step_id"] == "identify_thought"  # held in place

    # Turn N+1: intensity drops to 5 → no rule fires, advance to explore_distortion
    normal = evaluate_step_policy(
        skill=skill, current_step_id="identify_thought",
        emotional_intensity=5, engagement=7,
    )
    assert normal["action"] == "advance"
    assert normal["next_step_id"] == "explore_distortion"  # resumes

def test_evaluate_step_policy_low_engagement_triggers_check_in():
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="explore_distortion",
        emotional_intensity=4,
        engagement=2,
    )
    assert action["action"] == "check_in"

def test_skill_executor_node_produces_instruction():
    # message_en must be > 10 words for completion_criteria to allow advancement
    state = make_state(
        message_en="I don't know what to do, everything is always my fault.",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=6,
        engagement=7,
    )
    result = skill_executor_node(state)
    assert result["step_instruction"] is not None
    assert len(result["step_instruction"]) > 20
    assert result["executed_step_id"] == "identify_thought"
    assert result["active_step_id"] == "explore_distortion"
    assert result["escalation_triggered"] is None
    assert "skill_executor" in result["path"]

def test_completion_criteria_short_response_holds_step():
    """Short user response (≤ 10 words) holds the step — proves the hook exists."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    action = evaluate_step_policy(
        skill=skill,
        current_step_id="identify_thought",
        emotional_intensity=5,
        engagement=7,
        message_en="okay",  # 1 word — too short to advance
    )
    assert action["action"] == "stay"
    assert action["next_step_id"] == "identify_thought"  # held in place
    assert not action["skill_complete"]

def test_skill_executor_l1_exit_when_user_wants_to_stop():
    state = make_state(
        message_en="I don't want to do this anymore, let's stop.",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=5,
        engagement=3,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result["escalation_triggered"]["level"] == "L1"
    assert result["active_skill_id"] is None  # skill exited
    assert result["executed_step_id"] == "explore_distortion"

def test_skill_executor_l2_flag_on_clinical_signal():
    state = make_state(
        message_en="I've been drinking every night to cope",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=6,
        engagement=6,
        clinical_flags=["substance_use"],
    )
    result = skill_executor_node(state)
    assert result["escalation_triggered"]["level"] == "L2"
    # Skill stays active for L2 (flag only, not exit)
    assert result["active_skill_id"] == "cbt_thought_record"


# Task 12A: knowledge module
from sage_poc.knowledge import lookup_knowledge

def test_knowledge_lookup_exact_phrase():
    result = lookup_knowledge("what is anxiety")
    assert result is not None
    assert len(result) > 20

def test_knowledge_lookup_embedded_phrase():
    result = lookup_knowledge("Can you tell me what is CBT and how does it work?")
    assert result is not None

def test_knowledge_lookup_no_match_returns_none():
    result = lookup_knowledge("I feel sad today")
    assert result is None


# Task 11: freeflow_respond node
from sage_poc.nodes.freeflow_respond import freeflow_respond_node, compose_prompt

def test_compose_prompt_with_skill_instruction():
    state = make_state(
        message_en="I don't know... everything is my fault.",
        primary_intent="new_skill",
        step_instruction="Goal: identify thought. Technique: Socratic questioning. Tone: warm.",
        conversation_history=[],
        emotional_intensity=6,
    )
    prompt = compose_prompt(state)
    assert "wellness" in prompt.lower() or "companion" in prompt.lower()  # L0
    assert "socratic" in prompt.lower() or "identify thought" in prompt.lower()  # L3
    assert "everything is my fault" in prompt

def test_compose_prompt_without_skill_instruction():
    state = make_state(
        message_en="Hello, how are you?",
        primary_intent="general_chat",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=3,
    )
    prompt = compose_prompt(state)
    assert "wellness" in prompt.lower() or "companion" in prompt.lower()

def test_compose_prompt_blended_intent_injects_knowledge():
    state = make_state(
        message_en="I feel hopeless. Also, what is CBT?",
        primary_intent="new_skill",
        secondary_intent="info_request",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=5,
    )
    prompt = compose_prompt(state)
    assert "blended" in prompt.lower() or "info_request" in prompt.lower()
    assert "cognitive behavioral" in prompt.lower()  # knowledge snippet injected

def test_compose_prompt_clinical_flag_injects_adaptation():
    state = make_state(
        message_en="I've been drinking to cope",
        primary_intent="general_chat",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=5,
        clinical_flags=["substance_use"],
    )
    prompt = compose_prompt(state)
    assert "motivational interviewing" in prompt.lower()
    assert "judge" in prompt.lower()  # "do not judge"

def test_freeflow_respond_with_mocked_llm():
    state = make_state(
        message_en="I keep thinking I'm a failure.",
        step_instruction="Goal: identify the thought. Technique: Socratic questioning.",
        conversation_history=[],
        emotional_intensity=6,
        engagement=7,
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="That sounds really hard. When you say you feel like a failure, what specifically are you telling yourself?")
    result = freeflow_respond_node(state, llm=mock_llm)
    assert result["response_en"] is not None
    assert "freeflow_respond" in result["path"]


# Task 12: output_gate node
from sage_poc.nodes.output_gate import output_gate_node

def test_output_gate_english_passthrough():
    state = make_state(
        detected_language="en",
        response_en="That sounds really difficult. What thought is coming up for you?",
        path=["safety_check", "intent_route", "skill_select", "skill_executor", "freeflow_respond"],
    )
    result = output_gate_node(state)
    assert result["response"] == "That sounds really difficult. What thought is coming up for you?"
    assert "output_gate" in result["path"]

def test_output_gate_arabic_response_is_translated():
    state = make_state(
        detected_language="ar",
        response_en="I hear you. That sounds incredibly hard.",
        path=["safety_check", "intent_route"],
    )
    with patch("sage_poc.nodes.output_gate.translate_to_arabic") as mock_translate:
        mock_translate.return_value = "أسمعك. يبدو هذا صعباً للغاية."
        result = output_gate_node(state)
    assert result["response"] == "أسمعك. يبدو هذا صعباً للغاية."
    mock_translate.assert_called_once_with("I hear you. That sounds incredibly hard.")
