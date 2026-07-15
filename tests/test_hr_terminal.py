"""HR-1 Stage 2 Task 2 — SAGE_HIGH_RISK_TERMINAL kill-switch + the §HR fixed-copy
constants (docs/superpowers/specs/2026-07-16-hr1-stage2-terminal-design.md,
"Fixed copy" section). Config data only: assert on the constant VALUES, never
via the LLM.

The flag uses the same strict, inverted-default idiom as ROUTE_PRECEDENCE_ENABLED
(config.py:170-178): only a literal "true" (case-insensitive, whitespace-stripped)
enables; unset / empty / whitespace / any other garbage -> OFF. This is what
survives Railway's empty-string env-injection bug.
"""
import importlib

import sage_poc.config as config


def test_high_risk_terminal_default_off_with_no_env_set():
    assert config.HIGH_RISK_TERMINAL_ENABLED is False


def test_strict_idiom_only_literal_true_enables(monkeypatch):
    # Values that must NOT enable the flag, including truthy-looking garbage and
    # the Railway empty-string injection case.
    for off_value in ("1", "yes", "", "false", "on", "  ", "truex"):
        monkeypatch.setenv("SAGE_HIGH_RISK_TERMINAL", off_value)
        importlib.reload(config)
        assert config.HIGH_RISK_TERMINAL_ENABLED is False, repr(off_value)

    # Case-insensitive / whitespace-tolerant literal "true" DOES enable (matches
    # the ROUTE_PRECEDENCE_ENABLED idiom's .strip().lower() == "true" semantics).
    for on_value in ("true", "TRUE", " true ", "True"):
        monkeypatch.setenv("SAGE_HIGH_RISK_TERMINAL", on_value)
        importlib.reload(config)
        assert config.HIGH_RISK_TERMINAL_ENABLED is True, repr(on_value)

    # Restore clean default state for any tests that import config afterward.
    monkeypatch.delenv("SAGE_HIGH_RISK_TERMINAL", raising=False)
    importlib.reload(config)
    assert config.HIGH_RISK_TERMINAL_ENABLED is False


def test_unset_defaults_off_after_reload(monkeypatch):
    monkeypatch.delenv("SAGE_HIGH_RISK_TERMINAL", raising=False)
    importlib.reload(config)
    assert config.HIGH_RISK_TERMINAL_ENABLED is False


# --- §HR fixed copy (verbatim) ---

def test_distress_question_verbatim_anchor():
    assert config.HR_DISTRESS_QUESTION == (
        "On a scale of 0 to 10, how distressing is this for you right now?"
    )
    assert "0 to 10" in config.HR_DISTRESS_QUESTION


def test_supportive_message_verbatim():
    assert config.HR_SUPPORTIVE_MESSAGE == (
        "Thank you for telling me what's going on for you. What you're describing "
        "sounds really difficult, and I want to make sure you get support from "
        "someone who can help properly with this."
    )


def test_lower_redirect_contains_see_a_doctor_anchor():
    assert "doctor or mental health professional" in config.HR_REDIRECT_LOWER


def test_reask_is_gentle_and_content_neutral():
    # Single re-ask: still carries the 0-10 question, does not probe the experience
    # itself (no "why", "what happened", "tell me more").
    assert "0 to 10" in config.HR_REASK
    for probing_phrase in ("why", "what happened", "tell me more"):
        assert probing_phrase not in config.HR_REASK.lower()


def test_no_em_dashes_in_any_copy_constant():
    # Project convention: em dashes never appear in copy that reaches the LLM/user.
    for name in (
        "HR_DISTRESS_QUESTION",
        "HR_SUPPORTIVE_MESSAGE",
        "HR_REDIRECT_LOWER",
        "HR_REASK",
    ):
        value = getattr(config, name)
        assert "—" not in value, f"{name} contains an em dash"


def test_higher_redirect_not_hardcoded_composes_from_crisis_pathway():
    # The 999/ER branch must NOT duplicate a literal resource list in config;
    # it composes from select_crisis_resources()/CRISIS_CONFIG (single-sourced
    # crisis directory), same as the rest of the crisis pathway.
    assert hasattr(config, "select_crisis_resources")
    assert hasattr(config, "CRISIS_CONFIG")
    if hasattr(config, "HR_REDIRECT_HIGHER_LEAD"):
        assert "—" not in config.HR_REDIRECT_HIGHER_LEAD
        # A lead-in template must not itself contain a resource number/link —
        # those come exclusively from the crisis pathway.
        assert "999" not in config.HR_REDIRECT_HIGHER_LEAD


# ---------------------------------------------------------------------------
# Task 3: high_risk_response_node -- the 2-3 turn deterministic terminal.
#
# Call the node directly with constructed state dicts (no graph/checkpointer).
# Per house convention: assert on gate_path / hr_branch / hr_terminal_step /
# hr_distress_score, NEVER on the copy strings' prose, and NEVER on
# active_skill_id for "completion" (it is unconditionally cleared on entry).
# ---------------------------------------------------------------------------

import pytest

from sage_poc.nodes.high_risk_response import high_risk_response_node


def _base_state(**overrides) -> dict:
    state = {
        "path": [],
        "message_en": "",
        "hr_terminal_step": None,
        "active_skill_id": "box_breathing",
        "active_step_id": "step_2",
        "offered_skill_ids": ["box_breathing"],
    }
    state.update(overrides)
    return state


async def test_entry_asks_question_and_sets_await_distress():
    state = _base_state(message_en="I feel really overwhelmed today")
    result = await high_risk_response_node(state)

    assert result["gate_path"] == "high_risk"
    assert result["hr_terminal_step"] == "await_distress"
    assert result["hr_escalate_regardless"] is False
    # Entry-clear of skill-flow fields (medical_response.py structural precedent),
    # not asserted as "completion" -- asserted because the node is REQUIRED to clear
    # them so an in-progress skill cannot resume next turn.
    assert result["active_skill_id"] is None
    assert result["active_step_id"] is None
    assert result["offered_skill_ids"] is None


async def test_finding_1_mania_behavior_underway_escalates_regardless_of_low_score():
    entry_state = _base_state(
        message_en="I've been spending loads of money and I feel unstoppable"
    )
    entry_result = await high_risk_response_node(entry_state)
    assert entry_result["hr_escalate_regardless"] is True

    branch_state = _base_state(
        message_en="2",
        hr_terminal_step=entry_result["hr_terminal_step"],
        hr_escalate_regardless=entry_result["hr_escalate_regardless"],
    )
    branch_result = await high_risk_response_node(branch_state)

    # Critical case: a low numeric score (2) must NOT mask risky-behavior-underway
    # evidence carried in from entry. Must NOT be "lower".
    assert branch_result["hr_branch"] == "higher"
    assert branch_result["hr_branch"] != "lower"
    assert branch_result["hr_terminal_step"] is None
    assert branch_result["hr_escalate_regardless"] is False


async def test_await_distress_low_score_routes_lower():
    # HR_HIGH_FLOOR is 7, inclusive (hr_distress.py: "score >= HR_HIGH_FLOOR -> higher"),
    # so the low-score case must use a score strictly below the floor. "4" is
    # unambiguous; it is not the boundary value itself.
    state = _base_state(
        message_en="4",
        hr_terminal_step="await_distress",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_branch"] == "lower"
    assert result["hr_distress_score"] == 4
    assert result["hr_terminal_step"] is None
    assert result["hr_escalate_regardless"] is False


async def test_await_distress_floor_boundary_score_routes_higher():
    # Boundary check: HR_HIGH_FLOOR=7 is INCLUSIVE ("score >= HR_HIGH_FLOOR -> higher"
    # in hr_distress.resolve_hr_branch, the signed Task 1 constant). A score of exactly
    # 7 must route higher, not lower.
    state = _base_state(
        message_en="7",
        hr_terminal_step="await_distress",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_branch"] == "higher"
    assert result["hr_distress_score"] == 7
    assert result["hr_terminal_step"] is None


async def test_await_distress_high_score_routes_higher():
    state = _base_state(
        message_en="9",
        hr_terminal_step="await_distress",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_branch"] == "higher"
    assert result["hr_distress_score"] == 9
    assert result["hr_terminal_step"] is None


async def test_await_distress_risk_language_routes_higher_no_reask():
    state = _base_state(
        message_en="they're outside right now",
        hr_terminal_step="await_distress",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_branch"] == "higher"
    assert result["hr_terminal_step"] is None


async def test_await_distress_non_answer_reasks_once():
    state = _base_state(
        message_en="who told you that",
        hr_terminal_step="await_distress",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_terminal_step"] == "reask"
    assert "hr_branch" not in result


async def test_reask_non_answer_fails_to_higher():
    state = _base_state(
        message_en="still nothing",
        hr_terminal_step="reask",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_branch"] == "higher"
    assert result["hr_terminal_step"] is None
    assert result["hr_escalate_regardless"] is False


async def test_reask_clean_score_routes_lower():
    state = _base_state(
        message_en="3",
        hr_terminal_step="reask",
        hr_escalate_regardless=False,
    )
    result = await high_risk_response_node(state)

    assert result["hr_branch"] == "lower"
    assert result["hr_distress_score"] == 3
    assert result["hr_terminal_step"] is None
    assert result["hr_escalate_regardless"] is False
