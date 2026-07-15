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


# ---------------------------------------------------------------------------
# Task 4: routing (entry + re-entry, gated) + crisis clears the marker.
#
# high_risk_response is the 3rd member of the SAFETY-EXIT class (crisis_response,
# medical_response, high_risk_response): routed from _route_after_safety, straight
# to END, bypassing output_gate. Wired exactly like medical_response (graph.py).
# Ratified precedence order is crisis > medical > hr (BOT BEHAVIOUR / v7.1 table).
#
# "voices in my head" / "i hear voices" is a CF-006 pattern (active=true, live in
# prod, unconditional), so these tests fire psychotic_disclosure WITHOUT needing
# tests/test_hr_crisis_precedence.py's _force_activate_hr_rules helper -- unlike
# the CF-009 phrase set ("people are following me...") used in tests/test_hr_routing.py,
# which requires force-activation.
# ---------------------------------------------------------------------------

from langgraph.checkpoint.memory import MemorySaver

from sage_poc.graph import _route_after_safety, build_graph
from sage_poc import config as _cfg


def _safety_state(**overrides) -> dict:
    base = {
        "is_safe": True,
        "crisis_state": "none",
        "medical_flags": [],
        "crisis_tier": None,
        "clinical_flags": [],
        "hr_terminal_step": None,
    }
    base.update(overrides)
    return base


# --- Direct _route_after_safety unit tests (mirrors test_medical_redflag_guard.py's
#     _routed() helper): precise, discriminating coverage of the router logic itself,
#     independent of the full graph / monitoring-window behaviour exercised below. ---

def test_hr_entry_routes_when_terminal_on_and_disclosure_present(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    state = _safety_state(clinical_flags=["psychotic_disclosure"])
    assert _route_after_safety(state) == "high_risk"


def test_hr_entry_off_when_terminal_flag_off(monkeypatch):
    # Terminal kill-switch OFF: even with HIGH_RISK_DETECTION_ENABLED on and a gated HR
    # disclosure present, routing must NOT go to high_risk_response -- falls through to
    # "safe" (the Stage-1 path in _route_after_intent picks it up from there, unchanged).
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", False)
    monkeypatch.setattr(_cfg, "HIGH_RISK_DETECTION_ENABLED", True)
    state = _safety_state(clinical_flags=["mania_disclosure"])
    assert _route_after_safety(state) == "safe"


def test_hr_reentry_routes_when_terminal_step_set(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    state = _safety_state(clinical_flags=[], hr_terminal_step="await_distress")
    assert _route_after_safety(state) == "high_risk"


def test_hr_reentry_off_when_terminal_flag_off(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", False)
    state = _safety_state(clinical_flags=[], hr_terminal_step="reask")
    assert _route_after_safety(state) == "safe"


def test_crisis_wins_over_hr_entry(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    state = _safety_state(is_safe=False, clinical_flags=["psychotic_disclosure"])
    assert _route_after_safety(state) == "crisis"


def test_crisis_wins_over_hr_reentry(monkeypatch):
    # The critical "mid-protocol SI turn goes to crisis, not back to HR" ordering
    # (Finding 3's routing half): a persisted hr_terminal_step must NOT override a
    # fresh unsafe turn -- crisis is checked before either HR branch.
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    state = _safety_state(is_safe=False, hr_terminal_step="await_distress")
    assert _route_after_safety(state) == "crisis"


def test_medical_wins_over_hr(monkeypatch):
    # Ratified order crisis > medical > hr: HR is checked strictly after medical.
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    monkeypatch.setattr(_cfg, "MEDICAL_REDFLAG_GUARD_ENABLED", True)
    state = _safety_state(medical_flags=["crushing"], clinical_flags=["psychotic_disclosure"])
    assert _route_after_safety(state) == "medical"


def test_hr_off_byte_identical_default(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", False)
    monkeypatch.setattr(_cfg, "HIGH_RISK_DETECTION_ENABLED", False)
    state = _safety_state(clinical_flags=["psychotic_disclosure"], hr_terminal_step="await_distress")
    # psychotic_disclosure normally always routes (flag_enabled irrelevant to it), but the
    # HIGH_RISK_TERMINAL_ENABLED kill-switch gates the entire Task-4 block -- OFF must be
    # byte-identical to pre-Task-4 behaviour regardless of clinical_flags/hr_terminal_step.
    assert _route_after_safety(state) == "safe"


# --- Full-graph tests (real compiled app.ainvoke, checkpointed, no network) ---

async def test_full_graph_flag_on_entry_then_score_delivers_higher(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    app = build_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": "hr4-entry-then-higher"}}

    turn1 = await app.ainvoke(
        {"raw_message": "I hear voices in my head", "path": []}, config=cfg,
    )
    assert turn1.get("gate_path") == "high_risk"
    assert turn1.get("hr_terminal_step") == "await_distress"
    assert "high_risk_response" in turn1.get("path", [])
    assert "hr_branch" not in turn1

    turn2 = await app.ainvoke({"raw_message": "8", "path": []}, config=cfg)
    assert turn2.get("gate_path") == "high_risk"
    assert turn2.get("hr_branch") == "higher"
    assert turn2.get("hr_distress_score") == 8
    assert turn2.get("hr_terminal_step") is None


async def test_full_graph_in_progress_skill_cleared_on_hr_entry(monkeypatch):
    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    app = build_graph(MemorySaver())
    result = await app.ainvoke(
        {
            "raw_message": "I hear voices in my head",
            "path": [],
            "active_skill_id": "box_breathing",
            "active_step_id": "step_2",
            "offered_skill_ids": ["box_breathing"],
        },
        config={"configurable": {"thread_id": "hr4-skill-cleared"}},
    )
    assert result.get("gate_path") == "high_risk"
    assert result.get("active_skill_id") is None
    assert result.get("active_step_id") is None
    assert result.get("offered_skill_ids") is None


async def test_full_graph_flag_off_routes_stage1_psychotic_referral(monkeypatch):
    # Flag OFF: the Task-4 block in _route_after_safety is entirely skipped, so this HR
    # disclosure must still reach the LIVE Stage-1 path (_route_after_intent -> skill_select
    # -> psychotic_referral auto-select), never high_risk_response.
    from tests.test_hr_crisis_precedence import _stub_intent_and_responder_llms

    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", False)
    _stub_intent_and_responder_llms(monkeypatch)

    app = build_graph(MemorySaver())
    result = await app.ainvoke(
        {"raw_message": "I hear voices in my head", "path": []},
        config={"configurable": {"thread_id": "hr4-flag-off-stage1"}},
    )
    assert result.get("gate_path") != "high_risk"
    assert "high_risk_response" not in result.get("path", [])
    assert result.get("skill_match_method") == "psychotic_disclosure_auto_select"
    assert result.get("completed_skill_id") == "psychotic_referral"
    assert result.get("psychotic_referral_delivered") is True


async def test_finding_3_crisis_clears_hr_markers_no_stale_resume(monkeypatch):
    """The 3-turn crisis-clears-state test (REQUIRED, blocks flip). The active-resumable
    bug's 4th appearance: a stateful thing (hr_terminal_step / hr_escalate_regardless) must
    not leave a resumable marker behind when a higher-precedence path (crisis) pierces it.

    Turn 1: HR entry (asks distress) -> turn 2: SI reply -> crisis pierces (gate_path ==
    "crisis"), never HR, even though hr_terminal_step=="await_distress" was persisted from
    turn 1 -- proving the crisis check is senior to the HR re-entry check. The DECISIVE
    assertion is turn 2's own returned state: hr_terminal_step and hr_escalate_regardless
    are cleared (the SG-2 reset added to _crisis_response_node), not merely inert this turn.
    Turn 3 (benign) then confirms no resumption end-to-end. Note: crisis_state becomes
    "monitoring" after turn 2, so turn 3 is actually routed by _route_after_safety's separate
    monitoring branch (which does not consult hr_terminal_step at all) -- an independent,
    correct guard that would mask a stale-marker bug on this specific next turn regardless.
    Turn 2's direct channel assertions are therefore what actually proves the fix; turn 3
    documents the full observable behaviour the brief asks for.
    """
    from tests.test_hr_crisis_precedence import _stub_intent_and_responder_llms

    monkeypatch.setattr(_cfg, "HIGH_RISK_TERMINAL_ENABLED", True)
    _stub_intent_and_responder_llms(monkeypatch)

    app = build_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": "hr4-finding3"}}

    turn1 = await app.ainvoke({"raw_message": "I hear voices in my head", "path": []}, config=cfg)
    assert turn1.get("gate_path") == "high_risk"
    assert turn1.get("hr_terminal_step") == "await_distress"

    turn2 = await app.ainvoke(
        {"raw_message": "nothing feels real and I want to die", "path": []}, config=cfg,
    )
    assert turn2.get("is_safe") is False
    assert turn2.get("gate_path") == "crisis"
    assert "crisis_response" in turn2.get("path", [])
    # SG-2 reset: BOTH HR channels cleared by the crisis turn.
    assert turn2.get("hr_terminal_step") is None
    assert turn2.get("hr_escalate_regardless") is False

    turn3 = await app.ainvoke(
        {"raw_message": "thank you, I'm okay now", "path": []}, config=cfg,
    )
    assert turn3.get("gate_path") != "high_risk"
    assert "high_risk_response" not in turn3.get("path", [])
    assert turn3.get("hr_terminal_step") is None
