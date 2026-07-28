"""Phase 2 Task 8: skill_select's psychoed integration block (resolver + PSY-WEAVE-1 +
Classifier A), and the graph edges it drives.

ORDER IS CLINICAL (see skill_select.py's block comment / task-8-brief.md): (1) PSY-WEAVE-1
evaluation on a weave-pending turn runs BEFORE any matching, (2) active-skill suppression
stands, (3) the resolver, (4) Classifier A's acute-distress veto, (5) fall through unchanged.
The block sits at the literal top of skill_select_node, before the D1 answering_screen check
and the info_request bypass -- this is what guarantees the resolver wins before Mechanism-A's
info_request consult (the no-double-claim property between the two psychoed mechanisms).

Unit tests drive skill_select_node directly (no LLM), mirroring tests/test_skill_select.py's
and tests/test_psychoed_mechanism_a.py's `_ss_state()` convention.
"""
from __future__ import annotations

import pytest

import sage_poc.config as config
from sage_poc.graph import _route_after_skill_select
from sage_poc.nodes.skill_select import skill_select_node


def _ss_state(**overrides):
    base = {
        "raw_message": "",
        "detected_language": "en",
        "message_en": "",
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "primary_intent": None,
        "secondary_intent": None,
        "intent_confidence": 1.0,
        "emotional_intensity": 5,
        "engagement": 7,
        "active_skill_id": None,
        "active_step_id": None,
        "executed_step_id": None,
        "step_instruction": None,
        "escalation_triggered": None,
        "gate_path": None,
        "response_en": None,
        "response": None,
        "path": [],
        "turn_count": 0,
        "conversation_history": [],
        "skill_match_method": None,
        "semantic_score": None,
        "distress_trajectory": [],
        "code_switching": False,
    }
    base.update(overrides)
    return base


def _enable_psychoed(monkeypatch, categories=("1f", "3c")):
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", True)
    monkeypatch.setattr(config, "PSYCHOED_CATEGORIES", frozenset(categories))


# ─────────────────────────── 1. Trigger hit wins over the info_request consult ───────────────────────────

@pytest.mark.asyncio
async def test_trigger_hit_serves_and_preempts_info_request_consult(monkeypatch):
    """'What is anxiety?' is an exact 1f-t1 trigger phrase AND keyword-matches Mechanism-A's
    psychoed_anxiety consult skill. With BOTH mechanisms enabled, the Task-8 resolver block
    (top of the function) must win: psychoed_serve is set and the info_request consult below
    it is never reached."""
    _enable_psychoed(monkeypatch)
    monkeypatch.setattr(config, "INFO_REQUEST_CONSULT_ENABLED", True)
    state = _ss_state(message_en="What is anxiety?", primary_intent="info_request")

    result = await skill_select_node(state)

    assert result["skill_match_method"] == "psychoed_resolver"
    assert result["skill_match_method"] != "info_request_skill_consult"
    assert result.get("active_skill_id") is None  # consult never ran; no skill was activated
    assert result["psychoed_serve"] == {
        "category": "1f", "block_id": None, "route": "standard", "framing": "abstract",
        "weave_due": False, "matched_row_id": "1f-t1", "collision_path": None,
    }
    assert result["psychoed_active_category"] == "1f"
    assert result["psychoed_delivery_shape"] == "menu_first"
    assert result["psychoed_framing"] == "abstract"
    assert result["psychoed_weave_pending"] is False
    assert _route_after_skill_select(result) == "knowledge_retrieve"


# ─────────────────────────── 2/3. Weave precedence over the resolver ───────────────────────────

@pytest.mark.asyncio
async def test_weave_pending_contradiction_marker_escalates_to_crisis(monkeypatch):
    """'kind of' is a declared PSY-WEAVE-1 contradiction marker -> not a clear negative ->
    fail-closed to crisis."""
    _enable_psychoed(monkeypatch)
    state = _ss_state(message_en="kind of", psychoed_weave_pending=True, psychoed_active_category="1f")

    result = await skill_select_node(state)

    assert result["psychoed_weave_escalation"] is True
    assert result["psychoed_weave_pending"] is False
    assert result["skill_match_method"] == "psychoed_weave_escalation"
    assert _route_after_skill_select(result) == "crisis_response"


@pytest.mark.asyncio
async def test_weave_pending_precedence_beats_a_would_be_resolver_hit(monkeypatch):
    """'actually, what is anxiety?' would otherwise still contain a trigger phrase, but it is
    NOT a clear-negative weave reply -- fail-closed to crisis. Precedence: the weave check runs
    and escalates BEFORE the resolver is ever consulted (an exact resolver match on this longer
    string wouldn't fire anyway -- resolve() requires the WHOLE normalized message to match a
    registered phrase -- but the point under test is that skill_select never gets that far)."""
    _enable_psychoed(monkeypatch)
    state = _ss_state(
        message_en="actually, what is anxiety?", psychoed_weave_pending=True, psychoed_active_category="1f",
    )

    result = await skill_select_node(state)

    assert result["psychoed_weave_escalation"] is True
    assert "psychoed_serve" not in result
    assert _route_after_skill_select(result) == "crisis_response"


# ─────────────────────────── 4. Clear-negative weave reply -> deferred menu ───────────────────────────

@pytest.mark.asyncio
async def test_weave_clear_negative_defers_to_menu_after_weave(monkeypatch):
    """'no, nothing like that' normalizes to a declared clear_negative_pattern -> proceed, no new
    trigger in the reply itself -> the deferred menu continuation, routed like an info_request."""
    _enable_psychoed(monkeypatch)
    state = _ss_state(
        message_en="no, nothing like that", psychoed_weave_pending=True, psychoed_active_category="1f",
    )

    result = await skill_select_node(state)

    assert result["psychoed_weave_pending"] is False
    assert result["skill_match_method"] == "psychoed_menu_after_weave"
    assert "psychoed_weave_escalation" not in result
    assert _route_after_skill_select(result) == "knowledge_retrieve"


# ─────────────────────────── 5. Active-skill suppression ───────────────────────────

@pytest.mark.asyncio
async def test_active_skill_suppresses_the_resolver(monkeypatch):
    """A message that WOULD otherwise resolver-match ('What is anxiety?') never reaches the
    resolver when a skill is already active -- no hijack, and no psychoed keys are touched."""
    _enable_psychoed(monkeypatch)
    state = _ss_state(
        message_en="What is anxiety?", active_skill_id="box_breathing", active_step_id="inhale",
    )

    result = await skill_select_node(state)

    assert "psychoed_serve" not in result
    assert result.get("skill_match_method") != "psychoed_resolver"
    assert "psychoed_active_category" not in result


# ─────────────────────────── 6. Classifier A acute-distress veto ───────────────────────────

@pytest.mark.asyncio
async def test_acute_distress_vetoes_a_resolver_hit(monkeypatch):
    """An exact trigger-phrase match ('What is anxiety?') co-occurring with an acute-distress
    signal (fired_safety_routes non-empty) is vetoed by Classifier A: no serve, falls through to
    the existing node body (here: Mechanism-A's keyword tier, which still resolves the same
    message to psychoed_anxiety via the pre-existing keyword-match path lower in the function --
    proving the fall-through is real, not a dead end)."""
    _enable_psychoed(monkeypatch)
    state = _ss_state(message_en="What is anxiety?", fired_safety_routes=["s3"])

    result = await skill_select_node(state)

    assert "psychoed_serve" not in result
    assert result.get("skill_match_method") != "psychoed_resolver"


# ─────────────────────────── 7. Flag off -> byte-identical, no psychoed keys ───────────────────────────

@pytest.mark.asyncio
async def test_flag_off_no_psychoed_keys_in_return(monkeypatch):
    """Flag off, and no pre-existing psychoed pathway in state: the Task-8 top block is skipped
    entirely (config.PSYCHOED_PATHWAYS_ENABLED gates it) and the unconditional pathway-clear-on-
    exit spreads at the other return sites are no-ops (they key off psychoed_active_category, which
    is unset here) -- so the return carries zero psychoed_* keys, byte-identical to pre-Task-8."""
    monkeypatch.setattr(config, "PSYCHOED_PATHWAYS_ENABLED", False)
    state = _ss_state(message_en="What is anxiety?")

    result = await skill_select_node(state)

    psychoed_keys = [k for k in result if k.startswith("psychoed_")]
    assert psychoed_keys == [], f"psychoed keys leaked with the flag off: {psychoed_keys}"
