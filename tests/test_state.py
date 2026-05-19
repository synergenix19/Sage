from sage_poc.state import SageState

def test_state_has_required_fields():
    state: SageState = {
        "raw_message": "hello",
        "detected_language": "en",
        "message_en": "hello",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
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
    assert state["raw_message"] == "hello"
    assert state["path"] == []
    assert state["clinical_flags"] == []

def test_state_path_is_list():
    state: SageState = {
        "raw_message": "test",
        "detected_language": "en",
        "message_en": "test",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": ["substance_use"],
        "primary_intent": "general_chat",
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
    }
    assert len(state["path"]) == 4
    assert "intent_route" in state["path"]
    assert state["clinical_flags"] == ["substance_use"]
