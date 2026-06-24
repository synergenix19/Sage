"""Calibrated-V2 behavior #2: explicit ABSTAIN.

Behavior #1 already ABSTAINs when the absolute gate's above-set is empty. #2 closes the
below-threshold loophole: the cluster-argmax floor (0.42, below the 0.4593 threshold) today
routes a within-cluster winner that clears NO threshold — the primary id_oos over-route source.

Two tightenings (clinical/eng sign-off 2026-06-24):
  1. Cluster-argmax fires ABOVE the winner's τ, never below. Flag-off keeps the 0.42 floor
     (byte-identical). Flag-on: a below-τ within-cluster winner ABSTAINs, but an above-τ one
     STILL gets the tiebreak — so the id_oos fix doesn't regress legitimate in_scope cluster
     disambiguation (the already-weak 66% cell).
  2. ABSTAIN = pure no-offer freeflow. No runner-up is surfaced (a runner-up offer on an
     ABSTAIN-disposition is the softer form of the exact failure). Leaves the clean path the
     G5 crisis-resource backstop attaches to later.

Decision logic is unit-tested via _route_decision (no model load); flag-off byte-identical is
proven end-to-end by the wrong-skill stash-control (240/250, same 10).
"""
from sage_poc.nodes import skill_select as ss


def _cluster_ab(sid):
    return "C" if sid in ("a", "b") else None


def test_flag_off_cluster_argmax_routes_below_threshold(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    monkeypatch.setattr(ss, "_skill_cluster", _cluster_ab)
    ranked = [("a", 0.43), ("b", 0.42)]          # same cluster, both BELOW 0.4593, second>=floor
    best, score, ru = ss._route_decision(ranked, "en", "msg")
    assert best == "a"                            # V1: 0.42 floor routes below threshold


def test_flag_on_below_tau_within_cluster_abstains_with_no_offer(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", None)   # global τ = 0.4593
    monkeypatch.setattr(ss, "_skill_cluster", _cluster_ab)
    ranked = [("a", 0.43), ("b", 0.42)]
    best, score, ru = ss._route_decision(ranked, "en", "msg")
    assert best is None                           # tightening 1: below-τ argmax -> ABSTAIN
    assert ru is None                             # tightening 2: no runner-up offer


def test_flag_on_above_tau_within_cluster_still_breaks_tie(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", None)
    monkeypatch.setattr(ss, "_skill_cluster", _cluster_ab)
    ranked = [("a", 0.50), ("b", 0.48)]          # same cluster, both ABOVE 0.4593
    best, score, ru = ss._route_decision(ranked, "en", "msg")
    assert best == "a"                            # tightening 1b: tiebreak preserved above τ


def test_flag_on_abstain_when_nothing_clears_tau_has_no_offer(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE", None)
    monkeypatch.setattr(ss, "_skill_cluster", lambda sid: None)   # no clustering
    ranked = [("a", 0.40), ("b", 0.30)]          # nothing clears 0.4593
    best, score, ru = ss._route_decision(ranked, "en", "msg")
    assert best is None and ru is None            # pure freeflow, no offer


def test_flag_on_per_route_tau_gates_cluster_argmax(monkeypatch):
    # winner clears the GLOBAL threshold but not its own raised τ -> still ABSTAINs.
    from sage_poc.routing_eval.calibration import ThresholdTable
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    monkeypatch.setattr(ss, "_THRESHOLD_TABLE",
                        ThresholdTable(per_route={("en", "a"): 0.60}, cluster={}, route_cluster={}, fallback=frozenset()))
    monkeypatch.setattr(ss, "_skill_cluster", _cluster_ab)
    # a: 0.50 > global 0.4593 but < a's τ 0.60. b: 0.45 fires the 0.42 cluster floor but clears
    # no threshold of its own (global fallback 0.4593), so nothing routes -> ABSTAIN.
    ranked = [("a", 0.50), ("b", 0.45)]
    best, score, ru = ss._route_decision(ranked, "en", "msg")
    assert best is None                           # gated by per-route τ, not global
