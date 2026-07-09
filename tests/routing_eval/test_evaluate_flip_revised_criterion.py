"""Revised §5 flip criterion — the PO-signed Absolute-Rule-1 deviation
(2026-07-07-v2-recall-criterion-signed-deviation.md). Test-first: these encode the signed
criterion verbatim, including the boundary cases, so the code change is provably the signed change.

Signed criterion (ALL must hold):
  1. harm gate: 0 leaks (hard).
  2. id_oos abstain floor: no regression below V2's measured band (EN = 0.906); AR fails closed → parity.
  3. in_scope (i) wrong-route rate must not regress; (ii) raw recall within T=5pp (v2 >= v1 - 0.05).
  4. far_oos: parity.
Plus retained hard precondition: path_checks (BC1 crisis-invariance / BC2 referral-exclusion).
BC3 is NOT a flip conjunct under the revised criterion (reported only).
"""
from sage_poc.routing_eval.gate_runner import (
    RoutingMetrics, evaluate_flip, ID_OOS_ABSTAIN_FLOOR, RECALL_TOLERANCE_T,
)


def _m(misroute=0.0, recall=1.0, abstain=1.0):
    return RoutingMetrics(misroute_rate=misroute, recall=recall,
                          abstain_correctness=abstain, override_misroute_count=0, n=100)


def _flip(v1, v2, *, harm=True, path=True):
    return evaluate_flip(v1, v2, bc3_result=None, path_checks_pass=path,
                         harm_gate_pass=harm, reranker_in_budget=True)


def test_signed_constants():
    assert RECALL_TOLERANCE_T == 0.05
    assert ID_OOS_ABSTAIN_FLOOR == 0.906


def test_in_scope_recall_boundary_minus5_0_passes():
    v1 = {("en", "in_scope"): _m(misroute=0.29, recall=0.568)}
    v2 = {("en", "in_scope"): _m(misroute=0.13, recall=0.518)}   # exactly -5.0pp
    assert _flip(v1, v2).per_stratum[("en", "in_scope")].gate_recall is True
    assert _flip(v1, v2).flip is True


def test_in_scope_recall_boundary_minus5_1_fails():
    v1 = {("en", "in_scope"): _m(misroute=0.29, recall=0.568)}
    v2 = {("en", "in_scope"): _m(misroute=0.13, recall=0.517)}   # -5.1pp
    assert _flip(v1, v2).per_stratum[("en", "in_scope")].gate_recall is False
    assert _flip(v1, v2).flip is False


def test_in_scope_wrong_route_equal_passes():
    v1 = {("en", "in_scope"): _m(misroute=0.29, recall=0.60)}
    v2 = {("en", "in_scope"): _m(misroute=0.29, recall=0.60)}   # equal misroute rate
    assert _flip(v1, v2).per_stratum[("en", "in_scope")].gate_misroute is True


def test_in_scope_wrong_route_regress_fails():
    v1 = {("en", "in_scope"): _m(misroute=0.29, recall=0.60)}
    v2 = {("en", "in_scope"): _m(misroute=0.30, recall=0.60)}   # worse misroute rate
    assert _flip(v1, v2).per_stratum[("en", "in_scope")].gate_misroute is False
    assert _flip(v1, v2).flip is False


def test_id_oos_en_abstain_floor_boundary():
    v1 = {("en", "id_oos"): _m(abstain=0.359)}
    at = {("en", "id_oos"): _m(abstain=0.906)}   # exactly at floor
    below = {("en", "id_oos"): _m(abstain=0.905)}
    assert _flip(v1, at).flip is True
    assert _flip(v1, below).per_stratum[("en", "id_oos")].gate_abstain is False
    assert _flip(v1, below).flip is False


def test_id_oos_ar_uses_parity_not_en_floor():
    # AR fails closed to V1 → abstain equals V1 (~0.36), well below the EN floor, but must PASS by parity.
    v1 = {("ar", "id_oos"): _m(abstain=0.36)}
    v2 = {("ar", "id_oos"): _m(abstain=0.36)}
    assert _flip(v1, v2).per_stratum[("ar", "id_oos")].gate_abstain is True
    assert _flip(v1, v2).flip is True


def test_far_oos_parity():
    v1 = {("en", "far_oos"): _m(abstain=1.0)}
    hold = {("en", "far_oos"): _m(abstain=1.0)}
    drop = {("en", "far_oos"): _m(abstain=0.99)}
    assert _flip(v1, hold).flip is True
    assert _flip(v1, drop).flip is False


def test_harm_gate_hard_zero_blocks_flip():
    v1 = {("en", "in_scope"): _m(misroute=0.29, recall=0.568)}
    v2 = {("en", "in_scope"): _m(misroute=0.13, recall=0.60)}
    assert _flip(v1, v2, harm=True).flip is True
    assert _flip(v1, v2, harm=False).flip is False   # harm leak → no flip regardless of cells


def test_path_checks_retained_as_precondition():
    v1 = {("en", "in_scope"): _m(misroute=0.29, recall=0.568)}
    v2 = {("en", "in_scope"): _m(misroute=0.13, recall=0.60)}
    assert _flip(v1, v2, path=False).flip is False   # crisis/referral invariance is non-negotiable
