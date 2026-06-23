"""§5 gate runner — the V2-vs-V1 flip criteria (§8 gates 1–5), composed PER-STRATUM.

The flip verdict is the function that will authorize flipping V2 on for real users, so every
gate is tested to BLOCK, not just to pass: each veto test holds the other gates green and
flips one red, asserting don't-flip — five independent vetoes — plus the composition test
that proves a strong English result cannot mask a weak Khaleeji ar/id_oos cell, plus that an
underpowered (insufficient_to_assert) cell blocks rather than passes.
"""
from sage_poc.routing_eval.augrc import CellAUGRC
from sage_poc.routing_eval.blocking_checks import bc3_per_stratum_parity
from sage_poc.routing_eval.gate_runner import (
    RoutingMetrics,
    compute_metrics_by_stratum,
    compute_routing_metrics,
    evaluate_flip,
)
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord

EN = ("en", "in_scope")
AR = ("ar", "id_oos")   # the worst cell


def _m(misroute, recall, abstain, override=0):
    return RoutingMetrics(misroute, recall, abstain, override, 50)


def _v1():
    return {EN: _m(0.20, 0.60, 0.80), AR: _m(0.25, 0.55, 0.78)}


def _v2():
    return {EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.62, 0.82)}   # better in every cell


def _bc3(ar_n=10):
    cells = {
        ("en", "in_scope"): CellAUGRC("en", "in_scope", 10, 0.20),
        ("ar", "in_scope"): CellAUGRC("ar", "in_scope", ar_n, 0.22),
    }
    return bc3_per_stratum_parity(cells, delta=0.05, n_floor=8)


# --- happy path --------------------------------------------------------------

def test_flip_when_all_strata_pass_bc3_pass_path_pass():
    fv = evaluate_flip(_v1(), _v2(), bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=True)
    assert fv.flip is True


# --- five independent per-stratum vetoes -------------------------------------

def test_veto_misroute():
    v2 = {EN: _m(0.10, 0.70, 0.85), AR: _m(0.30, 0.62, 0.82)}      # ar misroute 0.30 > 0.25
    fv = evaluate_flip(_v1(), v2, bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.per_stratum[AR].gate_misroute is False


def test_veto_override():
    v2 = {EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.62, 0.82, override=1)}
    fv = evaluate_flip(_v1(), v2, bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.per_stratum[AR].gate_override is False


def test_veto_recall():
    v2 = {EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.50, 0.82)}      # ar recall 0.50 < 0.55
    fv = evaluate_flip(_v1(), v2, bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.per_stratum[AR].gate_recall is False


def test_veto_abstain():
    v2 = {EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.62, 0.70)}      # ar abstain 0.70 < 0.78
    fv = evaluate_flip(_v1(), v2, bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=True)
    assert fv.flip is False and fv.per_stratum[AR].gate_abstain is False


def test_veto_blocking_checks():
    fv = evaluate_flip(_v1(), _v2(), bc3_result=_bc3(), path_checks_pass=False, reranker_in_budget=True)
    assert fv.flip is False


# --- composition: strong EN must not mask weak Khaleeji ----------------------

def test_strong_english_does_not_mask_weak_khaleeji():
    v2 = {EN: _m(0.02, 0.95, 0.97), AR: _m(0.30, 0.50, 0.78)}      # EN excellent, AR regresses
    fv = evaluate_flip(_v1(), v2, bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=True)
    assert fv.flip is False, "pooled improvement must not flip when the worst cell regresses"
    assert fv.per_stratum[EN].passed is True
    assert fv.per_stratum[AR].passed is False


def test_insufficient_to_assert_cell_blocks_flip():
    # Underpowered Khaleeji cell → BC3 not 'pass' → must block, not silently read as ✓.
    fv = evaluate_flip(_v1(), _v2(), bc3_result=_bc3(ar_n=3), path_checks_pass=True, reranker_in_budget=True)
    assert fv.bc3_passed is False
    assert fv.flip is False


# --- gate 5 defined-negative -------------------------------------------------

def test_reranker_off_defined_negative_still_flips():
    fv = evaluate_flip(_v1(), _v2(), bc3_result=_bc3(), path_checks_pass=True, reranker_in_budget=False)
    assert fv.flip is True and fv.reranker_shipped is False


# --- metric computation ------------------------------------------------------

def _r(expected, routed, lang="en", stratum=None, override=False):
    cands = () if routed == ABSTAIN else ((routed, 0.7), ("x", 0.3))
    return EvalRecord(
        utterance=f"{lang}-{expected}->{routed}",
        lang=lang,
        stratum=stratum or ("in_scope" if expected != ABSTAIN else "id_oos"),
        expected_route=expected,
        scored_candidates=cands,
        override_fired=override,
        held_out=True,
    )


def _routed_of(rec):
    return rec.scored_candidates[0][0] if rec.scored_candidates else ABSTAIN


def test_compute_metrics_recall_misroute_abstain():
    recs = [
        _r("cbt_thought_record", "cbt_thought_record"),
        _r("box_breathing", "worry_time"),
        _r(ABSTAIN, ABSTAIN),
        _r(ABSTAIN, "sleep_hygiene"),
    ]
    m = compute_routing_metrics(recs, routed_of=_routed_of)
    assert m.recall == 0.5 and m.misroute_rate == 0.5 and m.abstain_correctness == 0.5


def test_compute_metrics_by_stratum_groups_by_lang_and_stratum():
    recs = [
        _r("box_breathing", "box_breathing", lang="en", stratum="in_scope"),
        _r(ABSTAIN, "worry_time", lang="ar", stratum="id_oos"),
    ]
    by = compute_metrics_by_stratum(recs, routed_of=_routed_of)
    assert set(by.keys()) == {("en", "in_scope"), ("ar", "id_oos")}
    assert by[("ar", "id_oos")].misroute_rate == 1.0
