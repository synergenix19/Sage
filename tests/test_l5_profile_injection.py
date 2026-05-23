"""Tests for L5 cross-session profile injection into compose_prompt().

Covers audit item L5-1: _build_cross_session_block output must appear in the
composed system prompt when a non-empty therapeutic_profile is in state.
"""
from unittest.mock import MagicMock, patch

import pytest

from sage_poc.prompts.composer import (
    _build_cross_session_block,
    _build_l5_user_context_block,
    compose_prompt,
)


_BASE_STATE: dict = {
    "raw_message": "I've been struggling again",
    "detected_language": "en",
    "message_en": "I've been struggling again",
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
    "engagement": 6,
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
    "turn_count": 3,
    "conversation_history": [],
    "prompt_layers": [],
    "token_usage": {},
    "therapeutic_profile": None,
}


def _no_rules():
    cultural = MagicMock()
    cultural.actions = []
    injection = MagicMock()
    injection.actions = []

    def _eval(cat, _ctx):
        return cultural if cat == "cultural" else injection

    return _eval


def _make_state(**kwargs):
    return {**_BASE_STATE, **kwargs}


# ---------------------------------------------------------------------------
# _build_cross_session_block unit tests
# ---------------------------------------------------------------------------


def test_cross_session_block_empty_profile_returns_empty_string():
    assert _build_cross_session_block(None) == ""
    assert _build_cross_session_block({}) == ""


def test_cross_session_block_effective_techniques_appear():
    block = _build_cross_session_block({"effective_techniques": ["box breathing", "grounding"]})
    assert "box breathing" in block
    assert "grounding" in block


def test_cross_session_block_ineffective_techniques_appear():
    block = _build_cross_session_block({"ineffective_techniques": ["journaling"]})
    assert "journaling" in block
    assert "avoid" in block.lower()


def test_cross_session_block_distortion_patterns_appear():
    block = _build_cross_session_block({"distortion_patterns": ["catastrophising"]})
    assert "catastrophising" in block


def test_cross_session_block_disclosed_concerns_appear():
    block = _build_cross_session_block({"disclosed_concerns": ["work stress", "family conflict"]})
    assert "work stress" in block
    assert "family conflict" in block


def test_cross_session_block_communication_style_appears():
    block = _build_cross_session_block({"communication_style": "prefers short responses"})
    assert "prefers short responses" in block


def test_cross_session_block_religious_framing_flag():
    block = _build_cross_session_block({"cultural_preferences": {"religious_framing": True}})
    assert "religious" in block.lower()


def test_cross_session_block_family_context_flag():
    block = _build_cross_session_block({"cultural_preferences": {"family_context": True}})
    assert "family" in block.lower()


def test_cross_session_block_session_count_singular():
    block = _build_cross_session_block({
        "session_count": 1,
        "effective_techniques": ["breathing"],
    })
    assert "1 previous session:" in block


def test_cross_session_block_session_count_plural():
    block = _build_cross_session_block({
        "session_count": 4,
        "effective_techniques": ["breathing"],
    })
    assert "4 previous sessions:" in block


def test_cross_session_block_empty_lists_returns_empty_string():
    profile = {
        "effective_techniques": [],
        "ineffective_techniques": [],
        "distortion_patterns": [],
        "disclosed_concerns": [],
    }
    assert _build_cross_session_block(profile) == ""


# ---------------------------------------------------------------------------
# _build_l5_user_context_block: profile-only path (no clinical flags)
# ---------------------------------------------------------------------------


def test_l5_block_fires_for_profile_alone_no_flags():
    """L5 fires when therapeutic_profile has content even with no clinical flags."""
    block = _build_l5_user_context_block(
        clinical_flags=[],
        intensity=5,
        engagement=6,
        therapeutic_profile={"effective_techniques": ["mindfulness"], "session_count": 2},
    )
    assert block is not None
    assert "mindfulness" in block


def test_l5_block_returns_none_when_profile_empty_and_no_flags():
    block = _build_l5_user_context_block(
        clinical_flags=[],
        intensity=5,
        engagement=6,
        therapeutic_profile=None,
    )
    assert block is None


def test_l5_block_combines_flags_and_profile():
    block = _build_l5_user_context_block(
        clinical_flags=["substance_use"],
        intensity=7,
        engagement=5,
        therapeutic_profile={"effective_techniques": ["grounding"], "session_count": 3},
    )
    assert block is not None
    assert "motivational" in block.lower()   # substance_use flag text
    assert "grounding" in block              # profile content


# ---------------------------------------------------------------------------
# compose_prompt integration: profile injection end-to-end
# ---------------------------------------------------------------------------


def test_compose_prompt_user_context_layer_fires_for_profile():
    """user_context layer appears in layers when therapeutic_profile is non-empty."""
    state = _make_state(therapeutic_profile={
        "effective_techniques": ["box breathing"],
        "session_count": 2,
    })
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, _, layers = compose_prompt(state)
    assert "user_context" in layers


def test_compose_prompt_profile_text_appears_in_user_str():
    """Cross-session profile content appears in the user-role string."""
    state = _make_state(therapeutic_profile={
        "effective_techniques": ["box breathing"],
        "session_count": 2,
    })
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, _ = compose_prompt(state)
    assert "box breathing" in user_str


def test_compose_prompt_no_user_context_layer_when_profile_empty():
    """user_context layer absent when profile is None and no clinical flags."""
    state = _make_state(therapeutic_profile=None, clinical_flags=[])
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, _, layers = compose_prompt(state)
    assert "user_context" not in layers


def test_compose_prompt_profile_block_precedes_user_message():
    """Profile context is injected before the USER: line in the user-role string."""
    state = _make_state(
        therapeutic_profile={"effective_techniques": ["grounding"], "session_count": 1},
        message_en="I feel overwhelmed again",
    )
    with patch("sage_poc.prompts.composer.rules_engine.evaluate", side_effect=_no_rules()):
        _, user_str, _ = compose_prompt(state)
    assert user_str.index("grounding") < user_str.index("USER: I feel overwhelmed again")
