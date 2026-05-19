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
