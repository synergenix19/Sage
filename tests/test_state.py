from sage_poc.state import SageState
import typing

def test_state_has_required_fields():
    state: SageState = {
        "raw_message": "hello",
        "detected_language": "en",
        "message_en": "hello",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
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
        "skill_match_method": None,
        "semantic_score": None,
        "cultural_output_violations": [],
    }
    assert state["raw_message"] == "hello"
    assert state["crisis_state"] == "none"
    assert state["s7_result"] is None
    assert state["cultural_output_violations"] == []

def test_state_has_crisis_state_not_legacy_bool():
    hints = typing.get_type_hints(SageState)
    assert "crisis_state" in hints, "SageState must declare crisis_state"
    assert "s7_result" in hints, "SageState must declare s7_result"
    assert "s7_method" in hints, "SageState must declare s7_method"
    assert "crisis_occurred_this_session" not in hints, "legacy field must be removed"

def test_state_has_cultural_output_violations():
    hints = typing.get_type_hints(SageState)
    assert "cultural_output_violations" in hints, (
        "SageState must declare cultural_output_violations — "
        "output_gate_node writes this key but it was absent from the schema"
    )

def test_state_path_is_list():
    state: SageState = {
        "raw_message": "test",
        "detected_language": "en",
        "message_en": "test",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": ["substance_use"],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 3,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": "identify_thought",
        "step_instruction": None,
        "escalation_triggered": {"level": "L2", "reason": "substance detected"},
        "response_en": "I'm here for you.",
        "response": "I'm here for you.",
        "path": ["safety_check", "intent_route", "freeflow_respond", "output_gate"],
        "turn_count": 1,
        "conversation_history": [{"role": "user", "content": "test"}],
        "skill_match_method": None,
        "semantic_score": None,
        "cultural_output_violations": [],
    }
    assert len(state["path"]) == 4
    assert state["crisis_state"] == "none"
