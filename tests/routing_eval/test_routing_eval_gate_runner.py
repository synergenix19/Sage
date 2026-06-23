"""§5 gate runner — the V2-vs-V1 flip criteria (§8 gates 1–5).

This is THE gate: V2 flips on only when, against the frozen V1 baseline, mis-route rate
does not regress (gate 1), override mis-route is zero (gate 2), recall improves (gate 3),
abstain-correctness does not regress (gate 4), and the blocking checks pass — with gate 5
(reranker latency) a defined-negative: if the rerank hop isn't in budget it ships OFF and
gates 1–4 must still hold. Pure record logic; fixture-testable; built before the live path
is touched so the wiring has something to be measured against.
"""
from sage_poc.routing_eval.gate_runner import (
    RoutingMetrics,
    compute_routing_metrics,
    evaluate_flip,
)
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


def _r(expected, routed, override=False):
    cands = () if routed == ABSTAIN else ((routed, 0.7), ("x", 0.3))
    return EvalRecord(
        utterance=f"{expected}->{routed}",
        lang="en",
        stratum="in_scope" if expected != ABSTAIN else "id_oos",
        expected_route=expected,
        scored_candidates=cands,
        override_fired=override,
        held_out=True,
    )


def _routed_of(rec):
    return rec.scored_candidates[0][0] if rec.scored_candidates else ABSTAIN


def test_compute_metrics_recall_misroute_abstain():
    recs = [
        _r("cbt_thought_record", "cbt_thought_record"),  # correct route
        _r("box_breathing", "worry_time"),               # misroute (wrong skill)
        _r(ABSTAIN, ABSTAIN),                            # correct abstain
        _r(ABSTAIN, "sleep_hygiene"),                    # routed when should abstain → misroute
    ]
    m = compute_routing_metrics(recs, routed_of=_routed_of)
    assert m.recall == 0.5
    assert m.misroute_rate == 0.5
    assert m.abstain_correctness == 0.5


def test_override_misroute_counted():
    recs = [_r("box_breathing", "worry_time", override=True), _r(ABSTAIN, ABSTAIN)]
    assert compute_routing_metrics(recs, routed_of=_routed_of).override_misroute_count == 1


def _m(misroute, recall, abstain, override=0):
    return RoutingMetrics(misroute_rate=misroute, recall=recall,
                          abstain_correctness=abstain, override_misroute_count=override, n=100)


def test_flip_when_v2_better_and_blocking_pass():
    fv = evaluate_flip(_m(0.20, 0.60, 0.80), _m(0.10, 0.70, 0.85),
                       v2_blocking_pass=True, reranker_in_budget=True)
    assert fv.flip is True


def test_no_flip_when_misroute_regresses():
    fv = evaluate_flip(_m(0.10, 0.60, 0.80), _m(0.15, 0.70, 0.85),
                       v2_blocking_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.gate_misroute is False


def test_no_flip_when_recall_drops():
    fv = evaluate_flip(_m(0.10, 0.70, 0.80), _m(0.08, 0.65, 0.82),
                       v2_blocking_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.gate_recall is False


def test_no_flip_when_override_misroute_nonzero():
    fv = evaluate_flip(_m(0.10, 0.70, 0.80), _m(0.08, 0.72, 0.82, override=1),
                       v2_blocking_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.gate_override is False


def test_no_flip_when_blocking_fails_even_if_metrics_better():
    fv = evaluate_flip(_m(0.20, 0.60, 0.80), _m(0.05, 0.80, 0.90),
                       v2_blocking_pass=False, reranker_in_budget=True)
    assert fv.flip is False


def test_reranker_off_defined_negative_still_flips_if_gates_hold():
    fv = evaluate_flip(_m(0.20, 0.60, 0.80), _m(0.10, 0.70, 0.85),
                       v2_blocking_pass=True, reranker_in_budget=False)
    assert fv.flip is True            # gates 1–4 hold → flip with reranker OFF
    assert fv.reranker_shipped is False
