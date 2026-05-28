"""Experiment 4.6 — Layer 1: L1 word budget calculation tests.

Tests that _compute_l1_budget returns the correct budget value based on
whether the state has a skill step, a primary info_request, or a
secondary info_request.

Budget constants (from composer.py):
  _L1_BASE_BUDGET = 450   (when has_skill OR has_knowledge)
  _L1_FLEX_BUDGET = 600   (otherwise)

Budget logic (from composer.py lines 104-121):
  has_skill    = bool(state.get("step_instruction"))
  has_knowledge = (primary_intent == "info_request" OR secondary_intent == "info_request")
  return BASE if (has_skill or has_knowledge) else FLEX
"""
import pytest

from sage_poc.prompts.composer import _compute_l1_budget
from tests.experiment_4_6.conftest import make_compose_state

_BASE = 450
_FLEX = 600


# ── Test 1: secondary=info_request → BASE budget ─────────────────────────────

def test_secondary_info_request_returns_base_budget():
    """secondary_intent='info_request' triggers has_knowledge → BASE budget (450)."""
    state = make_compose_state(
        primary_intent="new_skill",
        secondary_intent="info_request",
        step_instruction=None,
    )
    assert _compute_l1_budget(state) == _BASE, (
        f"Expected BASE budget ({_BASE}) when secondary='info_request', "
        f"got {_compute_l1_budget(state)}"
    )


# ── Test 2: primary=info_request → BASE budget ───────────────────────────────

def test_primary_info_request_returns_base_budget():
    """primary_intent='info_request' triggers has_knowledge → BASE budget (450)."""
    state = make_compose_state(
        primary_intent="info_request",
        secondary_intent=None,
        step_instruction=None,
    )
    assert _compute_l1_budget(state) == _BASE, (
        f"Expected BASE budget ({_BASE}) when primary='info_request', "
        f"got {_compute_l1_budget(state)}"
    )


# ── Test 3: has skill step → BASE budget ─────────────────────────────────────

def test_has_skill_returns_base_budget():
    """step_instruction present triggers has_skill → BASE budget (450)."""
    state = make_compose_state(
        primary_intent="skill_continuation",
        secondary_intent=None,
        step_instruction="Goal: identify thought.",
    )
    assert _compute_l1_budget(state) == _BASE, (
        f"Expected BASE budget ({_BASE}) when step_instruction is set, "
        f"got {_compute_l1_budget(state)}"
    )


# ── Test 4: general_chat with no knowledge → FLEX budget ─────────────────────

def test_general_chat_no_knowledge_returns_flex_budget():
    """No skill, no info_request → FLEX budget (600) for richer freeflow turns."""
    state = make_compose_state(
        primary_intent="general_chat",
        secondary_intent=None,
        step_instruction=None,
    )
    assert _compute_l1_budget(state) == _FLEX, (
        f"Expected FLEX budget ({_FLEX}) when primary='general_chat' and no skill/knowledge, "
        f"got {_compute_l1_budget(state)}"
    )


# ── Test 5: general_chat + general_chat secondary → FLEX budget ───────────────

def test_general_chat_with_secondary_general_chat_returns_flex_budget():
    """primary=general_chat + secondary=general_chat (neither is info_request) → FLEX budget."""
    state = make_compose_state(
        primary_intent="general_chat",
        secondary_intent="general_chat",
        step_instruction=None,
    )
    assert _compute_l1_budget(state) == _FLEX, (
        f"Expected FLEX budget ({_FLEX}) when both intents are general_chat, "
        f"got {_compute_l1_budget(state)}"
    )


# ── Test 6: skill_continuation + info_request secondary → BASE budget ─────────

def test_skill_continuation_with_info_secondary_returns_base_budget():
    """skill_continuation + secondary=info_request: both has_skill (via step_instruction)
    AND has_knowledge conditions are true → BASE budget (450)."""
    state = make_compose_state(
        primary_intent="skill_continuation",
        secondary_intent="info_request",
        step_instruction="Goal: identify thought.",
    )
    assert _compute_l1_budget(state) == _BASE, (
        f"Expected BASE budget ({_BASE}) when skill_continuation + step_instruction + "
        f"secondary=info_request, got {_compute_l1_budget(state)}"
    )
