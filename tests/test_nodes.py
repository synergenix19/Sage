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


# Task 11 / Sprint 4: freeflow_respond node — compose_prompt returns (system_str, user_str)
from sage_poc.nodes.freeflow_respond import freeflow_respond_node, compose_prompt

def test_compose_prompt_with_skill_instruction():
    state = make_state(
        message_en="I don't know... everything is my fault.",
        primary_intent="new_skill",
        step_instruction="Goal: identify thought. Technique: Socratic questioning. Tone: warm.",
        conversation_history=[],
        emotional_intensity=6,
    )
    system_str, user_str = compose_prompt(state)
    # Persona is in the system role
    assert "wellness" in system_str.lower() or "companion" in system_str.lower()
    # Skill instruction and user message are in the user role
    assert "socratic" in user_str.lower() or "identify thought" in user_str.lower()
    assert "everything is my fault" in user_str

def test_compose_prompt_without_skill_instruction():
    state = make_state(
        message_en="Hello, how are you?",
        primary_intent="general_chat",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=3,
    )
    system_str, user_str = compose_prompt(state)
    assert "wellness" in system_str.lower() or "companion" in system_str.lower()

def test_compose_prompt_blended_intent_injects_knowledge():
    """secondary_intent=info_request injects knowledge snippet into user role."""
    state = make_state(
        message_en="I feel hopeless. Also, what is CBT?",
        primary_intent="new_skill",
        secondary_intent="info_request",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=5,
    )
    system_str, user_str = compose_prompt(state)
    assert "blended" in user_str.lower() or "info_request" in user_str.lower()
    assert "cognitive behavioral" in user_str.lower()  # knowledge snippet in user role

def test_compose_prompt_primary_info_request_injects_knowledge():
    """P2-8: primary_intent=info_request alone must also inject knowledge (not only secondary)."""
    state = make_state(
        message_en="what is CBT and how does it work?",
        primary_intent="info_request",
        secondary_intent=None,
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=3,
    )
    system_str, user_str = compose_prompt(state)
    assert "cognitive behavioral" in user_str.lower(), \
        "Primary info_request intent must inject knowledge snippet into prompt"

def test_compose_prompt_clinical_flag_injects_adaptation():
    """Clinical adaptations belong in the system role (behavioral constraints)."""
    state = make_state(
        message_en="I've been drinking to cope",
        primary_intent="general_chat",
        step_instruction=None,
        conversation_history=[],
        emotional_intensity=5,
        clinical_flags=["substance_use"],
    )
    system_str, user_str = compose_prompt(state)
    assert "motivational interviewing" in system_str.lower()
    assert "judge" in system_str.lower()  # "do not judge" — in system behavioral guidance

def test_freeflow_respond_with_mocked_llm():
    """freeflow_respond calls llm.invoke with [{role:system,...},{role:user,...}] message list."""
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
    # Verify the LLM was called with a proper message list (not a raw string)
    call_args = mock_llm.invoke.call_args[0][0]
    assert isinstance(call_args, list), "llm.invoke must be called with a message list"
    roles = [m["role"] for m in call_args]
    assert roles == ["system", "user"], "Message list must have exactly [system, user] roles"


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

# Task 12B: low_confidence_respond node
from sage_poc.nodes.low_confidence_respond import low_confidence_respond_node

def test_low_confidence_respond_with_mocked_llm():
    state = make_state(
        message_en="I don't know... maybe",
        primary_intent="general_chat",
        intent_confidence=0.4,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content="I want to make sure I understand — could you tell me a bit more about what's on your mind?"
    )
    result = low_confidence_respond_node(state, llm=mock_llm)
    assert result["response_en"] is not None
    assert "low_confidence_respond" in result["path"]
    assert result.get("step_instruction") is None


# Sprint 2+3 — error handling and false-positive fixes

# P1-2: L1 exit whole-word matching
def test_l1_does_not_fire_on_stop_as_substring():
    """'I can't stop thinking' must not trigger L1 — 'stop' is a substring, not a standalone intent."""
    state = make_state(
        message_en="I can't stop thinking about what happened, it keeps replaying in my mind",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=6,
        engagement=6,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result.get("escalation_triggered") is None, \
        "Substring 'stop' in 'can\'t stop thinking' must not trigger L1 exit"
    assert result["active_skill_id"] == "cbt_thought_record", "Skill must remain active"


def test_l1_does_not_fire_on_leave_as_substring():
    """'I can't leave my house' must not trigger L1 via 'leave' substring."""
    state = make_state(
        message_en="I feel so anxious I can't leave my house anymore",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=7,
        engagement=5,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result.get("escalation_triggered") is None, \
        "Substring 'leave' in 'can\'t leave my house' must not trigger L1 exit"


def test_l1_still_fires_on_explicit_stop_request():
    """Explicit 'let's stop' must still trigger L1 exit after the whole-word fix."""
    state = make_state(
        message_en="Let's stop, I don't want to do this anymore.",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=5,
        engagement=3,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result.get("escalation_triggered") is not None
    assert result["escalation_triggered"]["level"] == "L1"


# P1-7: JSONDecodeError in intent_route
def test_intent_route_malformed_json_returns_defaults():
    """Malformed LLM JSON must not crash intent_route — defaults applied."""
    state = make_state(
        message_en="I keep thinking I'm a failure",
        active_skill_id=None,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content='{invalid: json, missing quotes}')
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "general_chat"
    assert result["emotional_intensity"] == 5
    assert result["engagement"] == 5
    assert result["intent_confidence"] == 0.5


def test_intent_route_no_json_in_response_returns_defaults():
    """LLM response with no JSON at all must not crash — defaults applied."""
    state = make_state(
        message_en="Hello there",
        active_skill_id=None,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(content="I cannot classify this message.")
    result = intent_route_node(state, llm=mock_llm)
    assert result["primary_intent"] == "general_chat"
    assert "intent_route" in result["path"]


# P2-7: _safe_int tolerates non-integer LLM output
def test_intent_route_string_intensity_coerced_to_int():
    """LLM returning emotional_intensity as a string (e.g. '7') must be coerced to int."""
    state = make_state(
        message_en="I feel okay",
        active_skill_id=None,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "general_chat", "emotional_intensity": "7", "engagement": "5.5", "intent_confidence": 0.8}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["emotional_intensity"] == 7
    assert result["engagement"] == 5
    assert isinstance(result["emotional_intensity"], int)


def test_intent_route_non_numeric_intensity_falls_back_to_default():
    """LLM returning 'high' for emotional_intensity must fall back to default 5."""
    state = make_state(
        message_en="I feel stressed",
        active_skill_id=None,
        conversation_history=[],
    )
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = MagicMock(
        content='{"primary_intent": "general_chat", "emotional_intensity": "high", "engagement": "medium", "intent_confidence": 0.7}'
    )
    result = intent_route_node(state, llm=mock_llm)
    assert result["emotional_intensity"] == 5
    assert result["engagement"] == 5


# P2-2: evaluate_step_policy unknown step_id returns stay (no StopIteration)
def test_evaluate_step_policy_unknown_step_id_returns_stay():
    """Unknown step_id must return 'stay' rather than raising StopIteration."""
    from sage_poc.skills.schema import load_skill
    skill = load_skill("cbt_thought_record")
    result = evaluate_step_policy(
        skill=skill,
        current_step_id="nonexistent_step",
        emotional_intensity=5,
        engagement=6,
    )
    assert result["action"] == "stay"
    assert result["next_step_id"] == "nonexistent_step"
    assert result["skill_complete"] is False


# P1-6: OpenRouter translation fallback (Ollama replaced by OpenRouter for translation)
def test_translate_to_english_falls_back_on_api_error():
    """When OpenRouter is unavailable, translate_to_english returns the original text."""
    from sage_poc.language import translate_to_english
    with patch("sage_poc.llm.get_responder") as mock_get_responder:
        mock_get_responder.return_value.invoke.side_effect = ConnectionError("API not available")
        result = translate_to_english("أريد الموت")
    assert result == "أريد الموت"


def test_translate_to_arabic_falls_back_on_api_error():
    """When OpenRouter is unavailable, translate_to_arabic returns the original text (English fallback)."""
    from sage_poc.language import translate_to_arabic
    with patch("sage_poc.llm.get_responder") as mock_get_responder:
        mock_get_responder.return_value.invoke.side_effect = ConnectionError("API not available")
        result = translate_to_arabic("That sounds really hard.")
    assert result == "That sounds really hard."


# P1-1 residual: missing CRISIS_KEYWORDS — "don't want to be alive" and "end it all"

def test_dont_want_to_be_alive_triggers_crisis():
    """'don't want to be alive' was absent from CRISIS_KEYWORDS — must now trigger crisis."""
    from sage_poc.nodes.safety_check import _contains_crisis
    flags = _contains_crisis("I just don't want to be alive anymore")
    assert len(flags) > 0, "'don't want to be alive' must trigger crisis detection"


def test_end_it_all_triggers_crisis():
    """'end it all' was absent from CRISIS_KEYWORDS — must now trigger crisis."""
    from sage_poc.nodes.safety_check import _contains_crisis
    flags = _contains_crisis("I just want to end it all, I can't take it anymore")
    assert len(flags) > 0, "'end it all' must trigger crisis detection"


# P2-6: ZWSP normalization — U+200B between characters must not defeat keyword detection

def test_crisis_keyword_with_zwsp_still_detected():
    """ZWSP (U+200B) injected into a crisis keyword must not defeat detection."""
    from sage_poc.nodes.safety_check import _contains_crisis
    # "want​to​die" — ZWSP between words
    flags = _contains_crisis("I want​ to die right now")
    assert len(flags) > 0, "ZWSP between words must not defeat crisis keyword detection"


# NEW-2: L1 false-positive regression tests — overly broad phrases removed

def test_l1_does_not_fire_on_dont_want_to_burden_you():
    """'I don't want to burden you' must not trigger L1 exit after removing 'don't want to'."""
    state = make_state(
        message_en="I really don't want to burden you with all of this",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=5,
        engagement=6,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result.get("escalation_triggered") is None, \
        "'don't want to burden you' must not trigger L1 exit"
    assert result["active_skill_id"] == "cbt_thought_record"


def test_l1_does_not_fire_on_want_to_stop_feeling_anxious():
    """'I want to stop feeling anxious' must not trigger L1 exit."""
    state = make_state(
        message_en="I want to stop feeling so anxious all the time",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=7,
        engagement=6,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result.get("escalation_triggered") is None, \
        "'want to stop feeling anxious' must not trigger L1 exit"
    assert result["active_skill_id"] == "cbt_thought_record"


def test_l1_does_not_fire_on_please_stop_being_harsh():
    """'please stop being so harsh on yourself' must not trigger L1 exit."""
    state = make_state(
        # 7 words — below completion_criteria threshold, so skill stays on identify_thought
        message_en="please stop being so harsh on yourself",
        active_skill_id="cbt_thought_record",
        active_step_id="identify_thought",
        emotional_intensity=5,
        engagement=7,
        clinical_flags=[],
    )
    result = skill_executor_node(state)
    assert result.get("escalation_triggered") is None, \
        "'please stop being harsh on yourself' must not trigger L1 exit"
    assert result["active_skill_id"] == "cbt_thought_record"
