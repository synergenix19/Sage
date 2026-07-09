"""Phase-2 T3 — the containment conditional edge + AC-CRISIS-SUPREMACY (BLOCKING).

The one real architectural risk of Phase 2 is the moment containment enters the routing
order. The load-bearing guarantee is that crisis supremacy is STRUCTURAL, not a priority
comparison you could get wrong:

  safety_check --_route_after_safety--> {"crisis": crisis_response --> END}
                                        {"safe":   intent_route --> ... --> skill_select}

crisis_response is reached at Node 1 and terminates at END. skill_select — and therefore the
containment router (_route_after_skill_select), and therefore containment_directive, which is
only ever SET inside skill_select — is downstream of the crisis short-circuit and unreachable
on a crisis turn. So an utterance that overlaps a crisis signal AND a containment pattern
reaches crisis_response no matter which detector (keyword / semantic S1 / S7) fires the crisis,
because the win is positional. A containment-only turn (no crisis verdict) reaches the KB
pathway. Bidirectional, per the checkpoint pre-registration.

NOTE (empirical, 2026-07-10): the illustrative "harming my baby ... tonight I might actually do
it" fixture does NOT trip the deterministic crisis lexicon — such intent phrasing rests on the
semantic/S7 detectors. That is exactly why this suite asserts the positional invariant rather
than a keyword match: the guarantee must hold for whichever detector fires, so a keyword-keyed
test would be both brittle and understate the guarantee. End-to-end render is AC-RENDER (T4,
staging, Vee).
"""
from langgraph.graph import END

from sage_poc.graph import _route_after_safety, _route_after_skill_select, build_graph


def _state(**kw):
    s = {"is_safe": True, "path": [], "primary_intent": "general_chat"}
    s.update(kw)
    return s


# ── Direction A: crisis ∩ containment overlap → crisis wins (structural) ──────────────
def test_crisis_verdict_routes_to_crisis_even_with_containment_directive():
    # A containment_directive present in state is IRRELEVANT once safety_check returns a crisis
    # verdict: the safety router decides before skill_select ever runs. (In real flow the directive
    # could not even exist yet on a crisis turn — skill_select never executes — but asserting it is
    # present-and-ignored makes the supremacy explicit and regression-proof.)
    st = _state(is_safe=False,
                containment_directive={"family": "harm_intrusive", "rule_id": "x"})
    assert _route_after_safety(st) == "crisis"


def test_graph_crisis_branch_terminates_and_never_reaches_skill_select():
    # Structural proof from the COMPILED graph: safety_check's "crisis" successor is crisis_response,
    # crisis_response goes to END, and no edge leads from crisis_response into skill_select. Containment
    # is unreachable on a crisis turn by construction, not by a priority check that could be reordered.
    edges = build_graph().get_graph().edges
    pairs = {(e.source, e.target) for e in edges}
    assert ("crisis_response", "skill_select") not in pairs, "crisis must not fan into skill_select"
    assert any(s == "crisis_response" and t == END for s, t in pairs), "crisis_response must go to END"
    assert any(s == "safety_check" and t == "crisis_response" for s, t in pairs), \
        "safety_check must have a direct crisis_response successor"


# ── Direction B: containment-only → containment KB pathway ────────────────────────────
def test_containment_directive_routes_to_knowledge_retrieve():
    st = _state(containment_directive={"family": "ocd", "kb_topics": ["ocd_erp"], "rule_id": "ocd_x"})
    assert _route_after_skill_select(st) == "knowledge_retrieve"


def test_containment_supersedes_abstain_at_the_router():
    # belt-and-suspenders vs T2's node-level mutual exclusion: if both were ever set, contain wins.
    st = _state(containment_directive={"family": "ocd", "rule_id": "x"}, skill_select_abstained=True)
    assert _route_after_skill_select(st) == "knowledge_retrieve"


# ── Dormant: no directive → byte-identical to master routing ──────────────────────────
def test_no_directive_is_byte_identical_freeflow_fallback():
    assert _route_after_skill_select(_state()) == "freeflow"


def test_no_directive_info_request_still_reaches_knowledge_retrieve():
    # guard the pre-existing info_request→knowledge_retrieve edge is not shadowed by the new branch
    assert _route_after_skill_select(_state(primary_intent="info_request")) == "knowledge_retrieve"


def test_no_directive_active_skill_still_reaches_executor():
    assert _route_after_skill_select(_state(active_skill_id="box_breathing")) == "skill_executor"
