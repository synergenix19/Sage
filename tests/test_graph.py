import pytest
from unittest.mock import patch, MagicMock


def make_e2e_state(raw_message: str, **overrides) -> dict:
    base = {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": "",
        "is_safe": False,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 0.0,
        "emotional_intensity": 5,
        "engagement": 7,
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
    return {**base, **overrides}


@pytest.mark.slow
def test_english_general_chat_e2e():
    """English general chat: safety → intent → freeflow → output. No skill."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("Hello, I just wanted to check in."))
    assert result["is_safe"] is True
    assert result["response"] is not None
    assert "safety_check" in result["path"]
    assert "output_gate" in result["path"]


@pytest.mark.slow
def test_english_crisis_message_stops_at_safety():
    """Crisis message: safety_check fires, graph ends, no LLM called."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("I want to kill myself tonight"))
    assert result["is_safe"] is False
    assert "safety_check" in result["path"]
    assert "intent_route" not in result["path"]
    assert result["response"] is not None
    assert "crisis" in result["response"].lower() or "help" in result["response"].lower()


@pytest.mark.slow
def test_english_skill_routing_e2e():
    """New skill intent: routes through skill_select → executor → respond."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("I keep thinking everything is my fault, always", emotional_intensity=6))
    assert result["is_safe"] is True
    assert "skill_select" in result["path"]
    assert result["active_skill_id"] == "cbt_thought_record"
    assert result["executed_step_id"] == "identify_thought"
    assert result["active_step_id"] == "explore_distortion"
    assert result["step_instruction"] is not None
    assert result["response"] is not None
    print(f"\n[TEST] Path: {result['path']}")
    print(f"[TEST] Step used: {result['executed_step_id']} → next: {result['active_step_id']}")
    print(f"[TEST] Response: {result['response']}")


@pytest.mark.slow
def test_cbt_full_3_step_progression_e2e():
    """Full CBT thought record: 3 turns, advances through all steps, skill clears on completion."""
    from sage_poc.graph import build_graph
    graph = build_graph()

    r1 = graph.invoke(make_e2e_state(
        "I keep thinking that everything is my fault, always, and I cannot escape it",
        emotional_intensity=6,
    ))
    assert r1["active_skill_id"] == "cbt_thought_record"
    assert r1["executed_step_id"] == "identify_thought"
    assert r1["active_step_id"] == "explore_distortion"

    r2 = graph.invoke(make_e2e_state(
        "I tell myself I'm worthless and that nothing will ever change",
        active_skill_id=r1["active_skill_id"],
        active_step_id=r1["active_step_id"],
        conversation_history=r1["conversation_history"],
        emotional_intensity=r1.get("emotional_intensity", 6),
        engagement=r1.get("engagement", 7),
    ))
    assert r2["executed_step_id"] == "explore_distortion"
    assert r2["active_step_id"] == "balanced_thought"

    r3 = graph.invoke(make_e2e_state(
        "My friend said something kind yesterday... maybe I'm not totally worthless",
        active_skill_id=r2["active_skill_id"],
        active_step_id=r2["active_step_id"],
        conversation_history=r2["conversation_history"],
        emotional_intensity=r2.get("emotional_intensity", 5),
        engagement=r2.get("engagement", 7),
    ))
    assert r3["executed_step_id"] == "balanced_thought"
    assert r3["active_skill_id"] is None
    print(f"\n[TEST] Full CBT path T3: {r3['path']}")


@pytest.mark.slow
def test_clinical_flag_detected_in_e2e():
    """Substance use message passes crisis check but sets clinical_flags."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state("I've been drinking heavily every night to cope with the stress"))
    assert result["is_safe"] is True
    assert "substance_use" in result.get("clinical_flags", [])
    assert result["response"] is not None


@pytest.mark.slow
def test_escalation_l1_exit_mid_skill():
    """User says stop mid-skill: executor L1 fires, skill clears, graceful close generated."""
    from sage_poc.graph import build_graph
    graph = build_graph()
    result = graph.invoke(make_e2e_state(
        "I don't want to do this anymore, can we stop please",
        active_skill_id="cbt_thought_record",
        active_step_id="explore_distortion",
        emotional_intensity=5,
    ))
    assert result["active_skill_id"] is None
    assert result.get("escalation_triggered", {}).get("level") == "L1"
    assert result["response"] is not None


@pytest.mark.slow
def test_session_full_lifecycle_e2e():
    """Full session: greeting → CBT skill (3 steps) → completion → freeflow. One connected flow."""
    from sage_poc.graph import build_graph
    graph = build_graph()

    # Turn 1: Greeting — general chat, no skill
    r1 = graph.invoke(make_e2e_state("Hello, I have been feeling really overwhelmed lately"))
    assert r1["is_safe"] is True
    assert r1["active_skill_id"] is None
    assert r1["response"] is not None
    print(f"\n[LIFECYCLE] Turn 1 (greeting) path: {r1['path']}")

    # Turn 2: Skill trigger — message > 10 words so completion_criteria allows first step to advance
    r2 = graph.invoke(make_e2e_state(
        "I keep thinking that everything is my fault, always, and I cannot shake it",
        conversation_history=r1["conversation_history"],
        emotional_intensity=6, engagement=7,
    ))
    assert r2["active_skill_id"] == "cbt_thought_record"
    assert r2["executed_step_id"] == "identify_thought"
    assert r2["active_step_id"] == "explore_distortion"
    print(f"[LIFECYCLE] Turn 2 (skill start) executed: {r2['executed_step_id']} → next: {r2['active_step_id']}")

    # Turn 3: User responds to identify_thought prompt (> 10 words → advances)
    r3 = graph.invoke(make_e2e_state(
        "I tell myself that I am worthless and that nothing good will ever happen to me",
        active_skill_id=r2["active_skill_id"],
        active_step_id=r2["active_step_id"],
        conversation_history=r2["conversation_history"],
        emotional_intensity=r2.get("emotional_intensity", 6),
        engagement=r2.get("engagement", 7),
    ))
    assert r3["executed_step_id"] == "explore_distortion"
    assert r3["active_step_id"] == "balanced_thought"
    print(f"[LIFECYCLE] Turn 3 (step 2) executed: {r3['executed_step_id']} → next: {r3['active_step_id']}")

    # Turn 4: User responds to explore_distortion → skill complete
    r4 = graph.invoke(make_e2e_state(
        "My friend said something kind to me yesterday and maybe I am not all bad after all",
        active_skill_id=r3["active_skill_id"],
        active_step_id=r3["active_step_id"],
        conversation_history=r3["conversation_history"],
        emotional_intensity=r3.get("emotional_intensity", 5),
        engagement=r3.get("engagement", 7),
    ))
    assert r4["executed_step_id"] == "balanced_thought"
    assert r4["active_skill_id"] is None  # skill complete, cleared
    print(f"[LIFECYCLE] Turn 4 (skill complete) path: {r4['path']}")

    # Turn 5: Back to freeflow — no active skill
    r5 = graph.invoke(make_e2e_state(
        "Thank you so much, that really helped me think differently about things",
        conversation_history=r4["conversation_history"],
        emotional_intensity=r4.get("emotional_intensity", 4),
        engagement=r4.get("engagement", 7),
    ))
    assert r5["active_skill_id"] is None
    assert r5["response"] is not None
    assert "skill_select" not in r5["path"]
    print(f"[LIFECYCLE] Turn 5 (freeflow close) path: {r5['path']}")
    print("\n[LIFECYCLE] Full session lifecycle confirmed.")
