"""Tests for L2 intensity guidance — persona compliance fix.

Root cause (RCA 2026-05-30): 'Prioritise validation' at intensity >= 7 triggers
GPT-4o's RLHF-encoded reflective paraphrase behavior, overriding L0's ban on
'It sounds like' / 'That sounds' 600+ words earlier.
"""
import pytest


def test_high_intensity_guidance_no_prioritise_validation():
    """'Prioritise validation' must not appear in the high-intensity guidance string."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    assert "Prioritise validation" not in _INTENSITY_GUIDANCE["high"], (
        f"RC-A fix not applied. Current: {_INTENSITY_GUIDANCE['high']!r}"
    )


def test_high_intensity_guidance_names_specific_action():
    """The replacement must name the specific action, not an abstract directive."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    assert "Name the specific" in guidance, (
        f"High-intensity guidance must tell GPT-4o to name the specific thing said. Got: {guidance!r}"
    )


def test_high_intensity_guidance_carries_banned_opener_constraint():
    """The banned opener constraint must appear in L2 (generation point) not just L0."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    guidance = _INTENSITY_GUIDANCE["high"]
    assert "It sounds like" in guidance or "reflective opener" in guidance, (
        f"Banned opener constraint missing from high-intensity guidance. Got: {guidance!r}"
    )


def test_high_intensity_guidance_defers_guidance():
    """'Do NOT offer guidance yet' must be preserved."""
    from sage_poc.prompts.composer import _INTENSITY_GUIDANCE
    assert "guidance" in _INTENSITY_GUIDANCE["high"].lower()


def test_compose_prompt_intensity_8_no_prioritise_validation():
    """compose_prompt at intensity=8 must not emit 'Prioritise validation' in user prompt."""
    from sage_poc.prompts.composer import compose_prompt
    state = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 8,
        "engagement": 4,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "banned_opener_correction": None,
    }
    _, user_str, _ = compose_prompt(state)
    assert "Prioritise validation" not in user_str, (
        f"Composed user prompt must not contain 'Prioritise validation'. Excerpt: {user_str[:200]!r}"
    )


def test_compose_prompt_no_correction_when_none():
    """C-5b: When banned_opener_correction is None, compose_prompt must NOT emit [CORRECTION] block."""
    from sage_poc.prompts.composer import compose_prompt
    state = {
        "raw_message": "I am exhausted by everything",
        "message_en": "I am exhausted by everything",
        "detected_language": "en",
        "primary_intent": "general_chat",
        "secondary_intent": None,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "rule_fired": None,
        "escalation_triggered": None,
        "clinical_flags": [],
        "crisis_state": "none",
        "third_party_crisis": False,
        "code_switching": False,
        "s7_result": None,
        "conversation_history": [],
        "conversation_summary": None,
        "therapeutic_profile": None,
        "knowledge_passages": [],
        "knowledge_abstain": False,
        "stale_skill_id": None,
        "banned_opener_correction": None,
    }
    _, user_str, layers = compose_prompt(state)
    assert "[CORRECTION]" not in user_str, (
        "compose_prompt must NOT emit [CORRECTION] when banned_opener_correction is None. "
        f"user_str excerpt: {user_str[:200]!r}"
    )
    assert "banned_opener_correction" not in layers, (
        f"'banned_opener_correction' must not appear in prompt_layers when correction is None. Got: {layers}"
    )


# RETIRED in #58: test_compose_prompt_injects_correction_when_set verified the [CORRECTION] block
# the composer injected to drive the banned-opener REGENERATION. That injection was removed (banned
# openers are fixed by an inline rewrite in output_gate, not a re-generation), so banned_opener_
# correction is never set and the composer no longer emits a [CORRECTION] layer. Nothing to assert.
