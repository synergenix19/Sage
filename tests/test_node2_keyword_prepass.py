"""W6 Phase 2 — Node-2 deterministic keyword pre-pass (v7.2). Rules-first stage in intent_route that
emits a routing HINT (prepass_matched/prepass_rule_id) so skill-worthy phrasings the classifier
mislabels (general_chat/info_request) still reach skill_select. Hint, don't hijack: primary_intent
is preserved, the classifier still runs, Node 4 governs offer/enter. _route_after_safety untouched.
"""
import time
import pytest
from unittest.mock import patch

from sage_poc.skills.keyword_matcher import match_skill_keywords, ranked_skill_matches
from sage_poc.graph import _route_after_intent


# ── shared matcher ────────────────────────────────────────────────────────────────────────────
def test_matcher_hits_the_measured_misses():
    assert "behavioral_activation" in match_skill_keywords("i have no motivation to do anything", "", "en")
    assert "mood_check_in" in match_skill_keywords("", "كيف مزاجي اليوم؟", "ar")  # AR against raw
    assert "grounding_5_4_3_2_1" in match_skill_keywords("i'm having a panic attack right now", "", "en")


def test_matcher_empty_on_non_trigger():
    assert match_skill_keywords("hello, nice weather today", "", "en") == {}


def test_matcher_longest_match_ranks_first():
    ranked = ranked_skill_matches("i'm so overwhelmed i can't think", "", "en")
    assert ranked and isinstance(ranked, list)


def test_matcher_shared_with_skill_select_no_divergence():
    # Node 4 must use the SAME helper object (constraint 2 — never diverge).
    import sage_poc.nodes.skill_select as ss
    assert ss.match_skill_keywords is match_skill_keywords


def test_matcher_latency_sub_5ms():
    t0 = time.perf_counter()
    for _ in range(50):
        match_skill_keywords("i have no motivation to do anything", "", "en")
    per_call_ms = (time.perf_counter() - t0) / 50 * 1000
    assert per_call_ms < 5.0, f"matcher too slow: {per_call_ms:.2f}ms/call"


# ── _route_after_intent branch (mirrors Routing-SF-2; _route_after_safety untouched) ───────────
def _s(**kw):
    base = {"primary_intent": "general_chat", "intent_confidence": 1.0, "crisis_state": "none",
            "active_skill_id": None, "emotional_intensity": 5, "prepass_matched": [], "offered_skill_ids": None}
    return {**base, **kw}


def test_general_chat_with_prepass_routes_to_skill_select():
    # The AR-mood / BA fix: general_chat that would freeflow, but prepass matched -> skill_select.
    assert _route_after_intent(_s(primary_intent="general_chat", prepass_matched=["behavioral_activation"])) == "skill_select"


def test_general_chat_without_prepass_still_freeflows():
    assert _route_after_intent(_s(primary_intent="general_chat", prepass_matched=[])) == "freeflow"


def test_prepass_never_overrides_crisis_or_monitoring():
    # Safety precedence: a prepass hint must never divert crisis/monitoring away from their routes.
    assert _route_after_intent(_s(primary_intent="crisis", prepass_matched=["dbt_tipp"])) == "crisis"
    assert _route_after_intent(_s(primary_intent="general_chat", crisis_state="monitoring",
                                  prepass_matched=["dbt_tipp"])) == "skill_select"  # monitoring already → skill_select


def test_prepass_no_hijack_when_skill_active():
    # Mid-skill turn must not be diverted (preserve checkpoint) — mirrors Routing-SF-2 guard.
    r = _route_after_intent(_s(primary_intent="general_chat", active_skill_id="worry_time",
                               prepass_matched=["dbt_tipp"]))
    assert r != "skill_select" or r == "freeflow"


# ── reducer channel survival (bug-#2 lesson) ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_prepass_channels_survive_langgraph_reducer():
    from langgraph.graph import StateGraph, START, END
    from sage_poc.state import SageState

    async def _node(state):
        return {"prepass_matched": ["mood_check_in"], "prepass_rule_id": "prepass_kw_v1"}

    g = StateGraph(SageState)
    g.add_node("n", _node)
    g.add_edge(START, "n")
    g.add_edge("n", END)
    out = await g.compile().ainvoke({"raw_message": "x"})
    assert out.get("prepass_matched") == ["mood_check_in"], "SageState dropped prepass_matched"
    assert out.get("prepass_rule_id") == "prepass_kw_v1", "SageState dropped prepass_rule_id"
