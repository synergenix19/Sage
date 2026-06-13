"""Tests for S2-7 B1 — the freeflow guided-protocol guardrail.

Clinical decision (B1, 2026-06-13): freeflow must not reproduce a structured
therapeutic protocol's step sequence as free prose (guided breathing, grounding
scripts, PMR, body scans, safe-place visualizations, TIPP-style resets). These
carry contraindication screening (an entry_screen on most) that prose delivery
routes around. The guardrail forbids LEADING the protocol turn-by-turn while
permitting supportive coping language (suggest + offer the guided version).

Scoping invariant: the guardrail is injected ONLY on freeflow turns (no
step_instruction). On skill-execution turns the executor must remain free to
deliver the protocol via the L3 step instruction.
"""
from unittest.mock import MagicMock, patch

from sage_poc.prompts.composer import compose_prompt


def _no_rules_mock():
    r = MagicMock()
    r.actions = []
    return r


def _build_state(**overrides):
    base = {
        "raw_message": "I am feeling really anxious",
        "detected_language": "en",
        "message_en": "I am feeling really anxious",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "code_switching": False,
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
        "rule_fired": None,
        "stale_skill_id": None,
        "re_escalation_within_monitoring": None,
        "third_party_crisis": False,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 1,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "prompt_layers": [],
        "token_usage": {},
        "knowledge_passages": None,
        "knowledge_abstain": False,
        "knowledge_source": None,
        "banned_opener_correction": None,
    }
    return {**base, **overrides}


def _compose(state):
    with patch(
        "sage_poc.prompts.composer.rules_engine.evaluate",
        return_value=_no_rules_mock(),
    ):
        return compose_prompt(state)


def test_guardrail_present_on_freeflow_turn():
    """A freeflow state (no step_instruction) must carry the guardrail block."""
    state = _build_state(primary_intent="general_chat", active_skill_id=None, step_instruction=None)
    system_str, user_str, layers = _compose(state)
    combined = system_str + "\n" + user_str
    assert "do not lead" in combined.lower()
    assert "guided" in combined.lower()
    assert "offer to start" in combined.lower()
    assert "freeflow_guardrail" in layers


def test_guardrail_present_on_freeflow_new_skill_unmatched():
    """new_skill intent with no active skill is still a freeflow turn -> guardrail present."""
    state = _build_state(primary_intent="new_skill", active_skill_id=None, step_instruction=None)
    system_str, user_str, layers = _compose(state)
    combined = system_str + "\n" + user_str
    assert "do not lead" in combined.lower()
    assert "freeflow_guardrail" in layers


def test_guardrail_absent_on_skill_execution_turn():
    """Skill-execution turn (active_skill_id + step_instruction + executed_step_id) must NOT
    carry the guardrail — the executor delivers the protocol via L3."""
    state = _build_state(
        primary_intent="skill_continuation",
        active_skill_id="dbt_tipp",
        executed_step_id="s1",
        step_instruction="Guide the user through the temperature change step.",
    )
    system_str, user_str, layers = _compose(state)
    combined = system_str + "\n" + user_str
    assert "do not lead the user step by step through a structured therapeutic protocol" not in combined.lower()
    assert "freeflow_guardrail" not in layers


def test_guardrail_allows_supportive_language():
    """The guardrail must explicitly permit suggesting/offering, not blanket-ban mentioning coping."""
    from sage_poc.prompts.loader import get_template

    content = get_template("freeflow_guardrail").content
    assert "may suggest" in content.lower()
    assert "offer to start" in content.lower()


def test_guardrail_content_clean():
    """No em dashes in the guardrail content string."""
    from sage_poc.prompts.loader import get_template

    content = get_template("freeflow_guardrail").content
    assert "—" not in content, "guardrail content must not contain em dashes"
