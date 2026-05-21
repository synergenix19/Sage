# tests/test_rules_integration.py
import pytest
from unittest.mock import patch
from sage_poc.rules.loader import reload_all
from sage_poc.nodes.safety_check import safety_check_node


@pytest.fixture(autouse=True)
def fresh_rules():
    reload_all()
    yield
    reload_all()


def _state(raw_message, clinical_flags=None):
    return {
        "raw_message": raw_message,
        "detected_language": "en",
        "message_en": raw_message,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": clinical_flags or [],
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }


# ── Crisis detection via Rules Service ──────────────────────────────────────

def test_safety_check_node_crisis_sets_is_safe_false():
    result = safety_check_node(_state("I want to die"))
    assert result["is_safe"] is False
    assert len(result["crisis_flags"]) > 0


def test_safety_check_node_safe_message():
    result = safety_check_node(_state("I feel anxious today"))
    assert result["is_safe"] is True
    assert result["crisis_flags"] == []


def test_safety_check_node_negation_no_crisis():
    result = safety_check_node(_state("I don't want to die"))
    assert result["is_safe"] is True, "Negation should suppress crisis flag"


def test_safety_check_node_clinical_flag_substance():
    result = safety_check_node(_state("I've been drinking to cope"))
    assert "substance_use" in result["clinical_flags"]


# ── Clinical flag carry-forward ──────────────────────────────────────────────

def test_clinical_flags_carry_forward_across_turns():
    """Flags from a prior turn are merged, not erased, by the next turn."""
    state = _state("I'm feeling better today", clinical_flags=["substance_use"])
    result = safety_check_node(state)
    assert "substance_use" in result["clinical_flags"], (
        "substance_use flag from prior turn must persist into turn 2"
    )


def test_new_clinical_flag_merges_with_existing():
    """New flag from current turn merges with flag persisted from prior turn."""
    state = _state("I was assaulted and I drink too much", clinical_flags=["substance_use"])
    result = safety_check_node(state)
    assert "substance_use" in result["clinical_flags"]
    assert "trauma_indicator" in result["clinical_flags"]


def test_no_duplicate_flags():
    """If the same flag fires again, it appears once, not twice."""
    state = _state("I drink a lot", clinical_flags=["substance_use"])
    result = safety_check_node(state)
    assert result["clinical_flags"].count("substance_use") == 1


# ── Crisis content ───────────────────────────────────────────────────────────
from sage_poc.rules import engine as rules_engine


def test_crisis_content_en_returns_uae_number():
    result = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "acute"})
    assert result.fired
    text = result.fired[0].action["response_text"]
    assert "800" in text and "4673" in text


def test_crisis_content_ar_returns_arabic_text():
    result = rules_engine.evaluate("crisis_content", {"language": "ar", "crisis_level": "acute"})
    assert result.fired
    text = result.fired[0].action["response_text"]
    assert "أنا" in text or "الإمارات" in text


def test_crisis_content_extended_returns_resource_list():
    result = rules_engine.evaluate("crisis_content", {"language": "en", "crisis_level": "extended"})
    assert result.fired
    resources = result.fired[0].action.get("resources", [])
    names = [r["name"] for r in resources]
    assert any("Estijaba" in n or "HOPE" in n for n in names)


# ── freeflow_respond compose_prompt via Rules Service ────────────────────────
from sage_poc.nodes.freeflow_respond import compose_prompt


def _freeflow_state(**overrides):
    base = {
        "raw_message": "I feel anxious",
        "detected_language": "en",
        "message_en": "I feel anxious",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "intent_confidence": 0.9,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "skill_match_method": None,
        "semantic_score": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
    }
    base.update(overrides)
    return base


def test_islamic_framing_injected_when_faith_keyword_present():
    state = _freeflow_state(message_en="I feel my faith in allah is fading")
    system_str, _ = compose_prompt(state)
    assert "ISLAMIC" in system_str or "sabr" in system_str or "ibtila" in system_str


def test_no_islamic_framing_without_faith_keyword():
    state = _freeflow_state(message_en="I feel really anxious today")
    system_str, _ = compose_prompt(state)
    assert "ibtila" not in system_str


def test_collectivist_framing_injected_when_family_keyword_present():
    state = _freeflow_state(message_en="My family expects me to be an engineer")
    system_str, _ = compose_prompt(state)
    assert "COLLECTIVIST" in system_str or "honour" in system_str or "COLLECTIVIST" in system_str.upper()


def test_clinical_adaptation_substance_injected_from_flag():
    state = _freeflow_state(clinical_flags=["substance_use"])
    system_str, _ = compose_prompt(state)
    assert "motivational interviewing" in system_str.lower() or "substance" in system_str.lower()


@pytest.mark.parametrize("flag,expected_keyword", [
    ("trauma_indicator", "trauma"),
    ("eating_concern", "body"),
    ("medication_mention", "prescriber"),
])
def test_clinical_adaptation_injected_per_flag(flag, expected_keyword):
    state = _freeflow_state(clinical_flags=[flag])
    system_str, _ = compose_prompt(state)
    assert expected_keyword in system_str.lower(), (
        f"Expected {expected_keyword!r} in system prompt for {flag}"
    )


def test_collectivist_framing_fires_on_arabic_keyword():
    """Arabic عيب (shame) in raw_message triggers collectivist injection even when
    the English translation does not contain a matching keyword."""
    state = _freeflow_state(
        message_en="I feel pressured",
        raw_message="أحس بالعيب",
        detected_language="ar",
    )
    system_str, _ = compose_prompt(state)
    assert "COLLECTIVIST" in system_str, (
        "Collectivist framing must fire on Arabic keyword عيب even without matching English translation"
    )


def test_secondary_intent_dialectical_framing_injected():
    state = _freeflow_state(
        primary_intent="new_skill",
        secondary_intent="info_request",
    )
    _, user_str = compose_prompt(state)
    assert "SECONDARY INTENT" in user_str or "dialectical" in user_str.lower()


def test_no_secondary_intent_framing_when_none():
    state = _freeflow_state(primary_intent="new_skill", secondary_intent=None)
    _, user_str = compose_prompt(state)
    assert "SECONDARY INTENT" not in user_str
