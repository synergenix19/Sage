"""Task 6 (Condition 1): V2 reranker ABSTAIN → Node 3 `low_confidence_respond`, NOT freeflow.

Cardinal Rule 5 + the clinician's signed premise: the −4.7pp recall was accepted because the lost
cases are recoverable soft-abstains that land in Node 3's empathic clarification, and the signed
soft-abstain-recovery monitoring assumes it. BOTH abstain producers must set the state key — the
semantic below-τ path AND the safety-critical keyword-veto path. Flag-off never sets it (byte-identical).
Driven via asyncio.run so it runs without pytest-asyncio.
"""
import asyncio

from sage_poc.graph import _route_after_skill_select
from sage_poc.nodes import skill_select as ss
from sage_poc.nodes.skill_select import skill_select_node


def _ss_state(**overrides):
    base = {
        "raw_message": "", "detected_language": "en", "message_en": "", "is_safe": True,
        "crisis_flags": [], "clinical_flags": [], "crisis_state": "none", "primary_intent": None,
        "secondary_intent": None, "intent_confidence": 1.0, "emotional_intensity": 5, "engagement": 7,
        "active_skill_id": None, "active_step_id": None, "path": [], "turn_count": 0,
        "conversation_history": [], "skill_match_method": None, "semantic_score": None,
    }
    base.update(overrides)
    return base


# --- graph routing (fast, no model) -----------------------------------------
def test_route_abstained_goes_to_low_confidence():
    assert _route_after_skill_select({"skill_select_abstained": True}) == "low_confidence"


def test_route_not_abstained_is_unchanged():
    assert _route_after_skill_select({"skill_select_abstained": False, "active_skill_id": "x"}) == "skill_executor"
    assert _route_after_skill_select({"primary_intent": "info_request"}) == "knowledge_retrieve"
    assert _route_after_skill_select({}) == "freeflow"


def test_route_abstain_wins_over_stale_active_skill():
    # A fresh abstain THIS turn must reach Node 3 even if a stale active_skill_id is present — the
    # abstain check is first. (Per-turn reset by _build_state prevents the inverse leak.)
    assert _route_after_skill_select({"skill_select_abstained": True, "active_skill_id": "x"}) == "low_confidence"


# --- producer 1: semantic below-τ ABSTAIN -----------------------------------
def test_semantic_abstain_sets_key_and_routes_node3(monkeypatch):
    monkeypatch.setattr(ss, "_rerank_enabled", lambda: True)
    monkeypatch.setattr(ss, "_semantic_match_with_runner_up", lambda *a, **k: (None, 0.1, None))
    result = asyncio.run(skill_select_node(_ss_state(message_en="the clouds look unusual over the hills today")))
    assert result.get("skill_select_abstained") is True
    assert result.get("active_skill_id") is None
    assert _route_after_skill_select(result) == "low_confidence"


# --- producer 2: keyword-veto ABSTAIN (safety-critical) ---------------------
def test_keyword_veto_sets_key_and_routes_node3(monkeypatch):
    monkeypatch.setattr(ss, "_rerank_enabled", lambda: True)
    monkeypatch.setattr(ss, "_keyword_rerank_veto", lambda *a, **k: True)
    result = asyncio.run(skill_select_node(_ss_state(message_en="I can't calm down")))
    assert result.get("skill_select_abstained") is True
    assert "keyword_rerank_veto" in result.get("path", [])
    assert _route_after_skill_select(result) == "low_confidence"


# --- flag-off byte-identical: key never set → freeflow ----------------------
def test_flag_off_abstain_no_key_and_freeflow(monkeypatch):
    monkeypatch.setattr(ss, "_rerank_enabled", lambda: False)
    monkeypatch.setattr(ss, "_semantic_match_with_runner_up", lambda *a, **k: (None, 0.1, None))
    result = asyncio.run(skill_select_node(_ss_state(message_en="the clouds look unusual over the hills today")))
    assert not result.get("skill_select_abstained")
    assert _route_after_skill_select(result) == "freeflow"
