"""Experiment 4.6 — Layer 1: compose_prompt blended intent injection tests.

Tests that compose_prompt correctly injects:
  - blended intent tag in L2 when secondary_intent is present
  - knowledge passages when primary OR secondary intent is info_request
  - no blended tag when secondary_intent is None
  - no knowledge when neither intent is info_request
"""
import pytest

from sage_poc.prompts.composer import compose_prompt, _build_l2_intent_block
from tests.experiment_4_6.conftest import make_compose_state


# ── Test 1: L2 block contains blended tag when secondary present ──────────────

def test_l2_block_contains_blended_tag_when_secondary_present():
    """_build_l2_intent_block must append '(blended with: <secondary>)' to content."""
    result = _build_l2_intent_block("new_skill", 5, secondary_intent="info_request")
    assert "blended with: info_request" in result, (
        f"Expected 'blended with: info_request' in L2 block, got: {result!r}"
    )


# ── Test 2: L2 block has no blended tag when secondary is None ───────────────

def test_l2_block_no_blended_tag_when_secondary_none():
    """_build_l2_intent_block must NOT include 'blended with' when secondary_intent is None."""
    result = _build_l2_intent_block("general_chat", 5, secondary_intent=None)
    assert "blended with" not in result, (
        f"'blended with' must not appear when secondary_intent=None, got: {result!r}"
    )


# ── Test 3: compose_prompt user string has blended tag ───────────────────────

def test_compose_prompt_l2_has_blended_tag():
    """When secondary_intent is set, compose_prompt user string must contain 'blended with: <secondary>'."""
    state = make_compose_state(
        primary_intent="new_skill",
        secondary_intent="info_request",
        message_en="I've been struggling — also, is CBT evidence-based?",
    )
    _, user_str, _ = compose_prompt(state)
    assert "blended with: info_request" in user_str, (
        f"Expected 'blended with: info_request' in user prompt, got excerpt: {user_str[:300]!r}"
    )


# ── Test 4: knowledge injected when secondary is info_request ─────────────────

def test_compose_prompt_knowledge_injected_with_secondary_info_request():
    """When secondary_intent='info_request' and knowledge_passages are present,
    compose_prompt must inject the passage text into the prompt."""
    state = make_compose_state(
        primary_intent="new_skill",
        secondary_intent="info_request",
        message_en="I've been struggling — also, is CBT evidence-based?",
        knowledge_passages=[{
            "text": "CBT is one of the most empirically supported psychological treatments.",
            "source_id": "cbt-001-en",
            "citation": "Beck (1979)",
            "relevance_score": 0.88,
        }],
        knowledge_abstain=False,
        step_instruction=None,
    )
    system_str, user_str, _ = compose_prompt(state)
    combined = system_str + user_str
    assert "CBT is one of the most empirically supported" in combined, (
        "Knowledge passage text must appear in prompt when knowledge_passages is set"
    )


# ── Test 5: no knowledge injection when secondary is general_chat ─────────────

def test_compose_prompt_knowledge_not_injected_for_secondary_general_chat():
    """When secondary_intent='general_chat' and knowledge_passages is empty,
    compose_prompt must NOT inject knowledge markers into the prompt."""
    state = make_compose_state(
        primary_intent="skill_continuation",
        secondary_intent="general_chat",
        message_en="I'm still working on it, just wanted to chat.",
        knowledge_passages=[],
        knowledge_abstain=False,
        step_instruction="Goal: identify thought.",
        active_skill_id="cbt_thought_record",
        executed_step_id=None,
    )
    system_str, user_str, _ = compose_prompt(state)
    combined = system_str + user_str
    # Knowledge markers only appear when L4 is present
    assert "[1]" not in combined, (
        "Knowledge citation '[1]' must not appear when no knowledge_passages are present"
    )
    assert "do not fabricate" not in combined.lower(), (
        "'do not fabricate' must not appear when knowledge_abstain=False and no passages"
    )


# ── Test 6: no blended tag when secondary is None ────────────────────────────

def test_compose_prompt_no_blended_tag_without_secondary():
    """When secondary_intent is None, compose_prompt must not include 'blended with'."""
    state = make_compose_state(
        primary_intent="general_chat",
        secondary_intent=None,
        message_en="Hey, how's it going?",
    )
    _, user_str, _ = compose_prompt(state)
    assert "blended with" not in user_str, (
        f"'blended with' must not appear when secondary_intent=None, got excerpt: {user_str[:300]!r}"
    )
