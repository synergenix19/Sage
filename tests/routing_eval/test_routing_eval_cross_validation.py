"""§2b k-fold cross-validation: pooled out-of-fold prediction so per-route thresholds
can be fit AND evaluated on disjoint data without halving cells below their N-floor.

Two correctness properties the gate depends on:
  - PARTITION + STRATIFIED: every record in exactly one fold; each (lang × stratum) cell
    spread evenly across folds, so per-fold calibration stays representative and the pooled
    OOF covers full N (the whole reason k-fold beats split-in-half here).
  - NO LEAKAGE: a record's routing decision uses a threshold table calibrated on folds that
    EXCLUDE it — the property that makes OOF an honest held-out measurement.
"""
from collections import Counter, defaultdict

from sage_poc.routing_eval.cross_validation import assign_folds
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


def _rec(lang, stratum, i):
    expected = "box_breathing" if stratum == "in_scope" else ABSTAIN
    return EvalRecord(
        utterance=f"{lang}-{stratum}-{i}", lang=lang, stratum=stratum, expected_route=expected,
    )


def _balanced_set():
    return [
        _rec(lang, stratum, i)
        for lang in ("en", "ar")
        for stratum in ("in_scope", "id_oos", "far_oos")
        for i in range(10)
    ]


def test_folds_partition_every_record_exactly_once():
    recs = _balanced_set()
    folds = assign_folds(recs, k=5, seed=0)
    assert len(folds) == len(recs)
    assert set(folds) == {0, 1, 2, 3, 4}
    sizes = Counter(folds)
    assert max(sizes.values()) - min(sizes.values()) <= 1, f"unbalanced fold sizes: {sizes}"


def test_fold_assignment_is_deterministic_for_a_seed():
    recs = _balanced_set()
    assert assign_folds(recs, k=5, seed=0) == assign_folds(recs, k=5, seed=0)


def test_folds_are_stratified_each_cell_spread_evenly():
    recs = _balanced_set()
    folds = assign_folds(recs, k=5, seed=0)
    cell_folds = defaultdict(Counter)
    for r, f in zip(recs, folds):
        cell_folds[(r.lang, r.stratum)][f] += 1
    for cell, c in cell_folds.items():
        assert max(c.values()) - min(c.values()) <= 1, f"{cell} not stratified across folds: {c}"


# --- cycle 2: pooled out-of-fold prediction --------------------------------
from sage_poc.routing_eval.cross_validation import cross_validate_oof
from sage_poc.routing_eval.calibration import calibrate_base_thresholds
from dataclasses import replace


def _scored(lang, stratum, route, score, expected, i):
    return EvalRecord(
        utterance=f"{lang}-{stratum}-{route}-{i}", lang=lang, stratum=stratum,
        expected_route=expected,
        scored_candidates=((route, score), ("x_other", round(score - 0.3, 4))),
    )


def test_oof_covers_every_record_exactly_once_tagged_by_fold():
    recs = [_scored("en", "in_scope", "box_breathing", 0.70, "box_breathing", i) for i in range(20)]
    recs += [_scored("en", "id_oos", "box_breathing", 0.40, ABSTAIN, i) for i in range(20)]
    oof = cross_validate_oof(recs, k=5, seed=0, min_n=2, cluster_of={})
    assert len(oof) == len(recs)
    assert sorted(id(p.record) for p in oof) == sorted(id(r) for r in recs)  # each record once
    assert {p.fold for p in oof} == {0, 1, 2, 3, 4}


def test_no_leakage_excluding_a_records_fold_drops_route_below_min_n():
    # box_breathing has exactly 4 TPs (one per fold 0-3 via round-robin). With min_n=4 the FULL
    # set earns it an own threshold; but each OOF fold EXCLUDES one TP -> 3 < 4 -> cluster
    # fallback. So leakage (counting the test fold) would flip used_fallback False; absence of
    # leakage forces it True. The 'calm' cluster is populated by sleep_hygiene so fallback resolves.
    cluster_of = {"box_breathing": "calm", "sleep_hygiene": "calm"}
    recs = [_scored("en", "in_scope", "box_breathing", 0.70, "box_breathing", i) for i in range(4)]
    recs += [_scored("en", "in_scope", "sleep_hygiene", 0.66, "sleep_hygiene", i) for i in range(5)]
    recs += [_scored("en", "id_oos", "sleep_hygiene", 0.40, ABSTAIN, i) for i in range(5)]
    # Control: on the FULL set, box_breathing earns its own threshold (4 TPs >= min_n=4).
    full = calibrate_base_thresholds([replace(r, held_out=False) for r in recs], min_n=4, cluster_of=cluster_of)
    assert not full.is_fallback("en", "box_breathing"), "control: full set should earn own threshold"
    # OOF: every box_breathing record must be on cluster fallback (its fold's TP excluded).
    oof = cross_validate_oof(recs, k=5, seed=0, min_n=4, cluster_of=cluster_of)
    bb = [p for p in oof if p.record.expected_route == "box_breathing"]
    assert len(bb) == 4
    assert all(p.used_fallback for p in bb), \
        f"leakage: box_breathing should fall back when its own fold is held out, got {[p.used_fallback for p in bb]}"


def test_oof_end_to_end_separates_in_scope_from_id_oos():
    recs = [_scored("en", "in_scope", "box_breathing", 0.70, "box_breathing", i) for i in range(15)]
    recs += [_scored("en", "id_oos", "box_breathing", 0.40, ABSTAIN, i) for i in range(15)]
    oof = cross_validate_oof(recs, k=5, seed=0, min_n=2, cluster_of={})
    by = {id(p.record): p for p in oof}
    routed_ok = sum(by[id(r)].routed == "box_breathing" for r in recs if r.stratum == "in_scope")
    abstain_ok = sum(by[id(r)].routed == ABSTAIN for r in recs if r.stratum == "id_oos")
    assert routed_ok == 15, f"in_scope routed correctly: {routed_ok}/15"
    assert abstain_ok == 15, f"id_oos abstained correctly: {abstain_ok}/15"


# --- cycle 3: pooled-OOF -> tolerance-gate bridge ---------------------------
from sage_poc.routing_eval.cross_validation import oof_cell_misroutes, oof_tolerance_verdicts, OOFPrediction


def _pred(lang, stratum, expected, routed, acceptable=()):
    rec = EvalRecord(
        utterance=f"{lang}-{stratum}-{expected}-{routed}-{len(acceptable)}", lang=lang, stratum=stratum,
        expected_route=expected, acceptable_routes=acceptable,
    )
    return OOFPrediction(rec, 0, routed, 0.5, False)


def test_over_route_on_abstain_cell_counts_as_misroute():
    preds = [_pred("en", "id_oos", ABSTAIN, "dbt_tipp") for _ in range(3)]
    preds += [_pred("en", "id_oos", ABSTAIN, ABSTAIN) for _ in range(2)]
    assert oof_cell_misroutes(preds)[("en", "id_oos")] == (3, 5)


def test_in_scope_abstain_is_safe_miss_but_wrong_skill_is_a_misroute():
    preds = [
        _pred("en", "in_scope", "box_breathing", ABSTAIN),        # safe coverage miss -> not counted
        _pred("en", "in_scope", "box_breathing", "worry_time"),   # wrong skill -> counted
    ]
    assert oof_cell_misroutes(preds)[("en", "in_scope")] == (1, 2)


def test_acceptable_routes_are_not_misroutes():
    preds = [_pred("en", "in_scope", "box_breathing", "sleep_hygiene", acceptable=("sleep_hygiene",))]
    assert oof_cell_misroutes(preds)[("en", "in_scope")] == (0, 1)


def test_clean_abstain_cell_yields_a_tolerance_verdict():
    preds = [_pred("en", "id_oos", ABSTAIN, ABSTAIN) for _ in range(70)]
    v = {x.cell: x for x in oof_tolerance_verdicts(preds)}
    assert v[("en", "id_oos")].misroutes == 0
    assert v[("en", "id_oos")].status in ("pass", "insufficient_n")
