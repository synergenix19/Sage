from sage_poc.state import SageState

def test_state_accepts_prompt_layers():
    state: SageState = {
        "raw_message": "hi", "detected_language": "en", "message_en": "hi",
        "is_safe": True, "crisis_flags": [], "clinical_flags": [],
        "crisis_state": "none", "s7_result": None, "s7_method": None,
        "distress_trajectory": [], "code_switching": False,
        "primary_intent": None, "secondary_intent": None, "intent_confidence": 0.0,
        "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "executed_step_id": None,
        "step_instruction": None, "skill_match_method": None, "semantic_score": None,
        "escalation_triggered": None, "gate_path": None,
        "response_en": None, "response": None,
        "path": [], "turn_count": 0, "conversation_history": [],
        "prompt_layers": ["persona", "history"],
        "token_usage": {"input": 100, "output": 50, "total": 150},
    }
    assert state["prompt_layers"] == ["persona", "history"]
    assert state["token_usage"]["total"] == 150
