"""§2b k-fold cross-validation for the routing-eval harness.

Why this exists: the calibrated retrieval-core fits per-route thresholds, which must be
evaluated on data disjoint from the fit set. Splitting each cell in half drops id_oos (71→35)
and far_oos (36→18) below their N-floors (66 / 30). k-fold instead reuses every cell at full
N via pooled out-of-fold prediction — each record is scored by a threshold table calibrated on
the folds that exclude it. Stratified + deterministic so folds stay representative and
reproducible (the frozen-baseline requirement, §6).
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, replace

from sage_poc.routing_eval.calibration import calibrate_base_thresholds
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord
from sage_poc.routing_eval.tolerances import ToleranceVerdict, misroute_tolerance_gate


def assign_folds(records: list[EvalRecord], *, k: int, seed: int) -> list[int]:
    """Stratified deterministic fold assignment. Returns a fold index per record, parallel to
    `records`. Within each (lang, stratum) cell the members are shuffled by `seed` then dealt
    round-robin across the k folds, so every cell is spread as evenly as possible (max-min ≤ 1)
    and the pooled out-of-fold set covers full N."""
    rng = random.Random(seed)
    by_cell: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, r in enumerate(records):
        by_cell[(r.lang, r.stratum)].append(idx)

    folds = [0] * len(records)
    for cell in sorted(by_cell):                      # sorted for determinism across runs
        members = by_cell[cell][:]
        rng.shuffle(members)
        for position, idx in enumerate(members):
            folds[idx] = position % k
    return folds


@dataclass(frozen=True)
class OOFPrediction:
    """One out-of-fold routing decision. `routed` is a skill_id or ABSTAIN; `threshold_used`
    is the τ applied to the top candidate; `used_fallback` is True when the route rode its
    cluster threshold (own-threshold not earned in this fold's calibration set)."""
    record: EvalRecord
    fold: int
    routed: str
    threshold_used: float
    used_fallback: bool


def cross_validate_oof(
    records: list[EvalRecord],
    *,
    k: int,
    seed: int,
    min_n: int,
    cluster_of: dict[str, str],
) -> list[OOFPrediction]:
    """Pooled out-of-fold prediction. For each fold, calibrate per-route thresholds on the
    OTHER folds (flagged as the calibration slice) and decide each held-out record by applying
    its top candidate's threshold: route iff top score ≥ τ, else ABSTAIN. Every record is
    predicted exactly once, by a table that excluded it — an honest held-out measurement at
    full per-cell N. A route the calibration set never saw → ABSTAIN (no evidence to vouch,
    the safe direction given the over-firing failure mode)."""
    folds = assign_folds(records, k=k, seed=seed)
    preds: list[OOFPrediction] = []
    for f in range(k):
        calib = [replace(r, held_out=False) for r, fold in zip(records, folds) if fold != f]
        table = calibrate_base_thresholds(calib, min_n=min_n, cluster_of=cluster_of)
        for r, fold in zip(records, folds):
            if fold != f:
                continue
            if not r.scored_candidates:
                preds.append(OOFPrediction(r, f, ABSTAIN, 1.0, True))
                continue
            route, score = r.scored_candidates[0]
            try:
                tau = table.threshold(r.lang, route)
            except KeyError:                          # route unseen in calibration → cannot vouch
                preds.append(OOFPrediction(r, f, ABSTAIN, 1.0, True))
                continue
            routed = route if score >= tau else ABSTAIN
            preds.append(OOFPrediction(r, f, routed, tau, table.is_fallback(r.lang, route)))
    return preds


def _is_misroute(pred: OOFPrediction) -> bool:
    """Tolerance-gate mis-route semantics. On an ABSTAIN-expected cell, routing to any skill is
    a (safety-relevant) mis-route. On an in_scope cell, routing to the WRONG skill is a mis-route
    but ABSTAIN is a safe coverage-miss (counted by AUGRC, not the tolerance bound).
    `acceptable_routes` (blended/comorbid, incl. ABSTAIN) are never mis-routes."""
    exp = pred.record.expected_route
    if pred.routed == exp or pred.routed in pred.record.acceptable_routes:
        return False
    if exp == ABSTAIN:
        return True                                    # over-route into a skill
    return pred.routed != ABSTAIN                      # wrong-skill counts; safe ABSTAIN-miss does not


def oof_cell_misroutes(preds: list[OOFPrediction]) -> dict[tuple[str, str], tuple[int, int]]:
    """Per (lang, stratum) cell -> (misroutes, n) from pooled OOF predictions."""
    agg: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for p in preds:
        cell = (p.record.lang, p.record.stratum)
        agg[cell][1] += 1
        if _is_misroute(p):
            agg[cell][0] += 1
    return {cell: (m, n) for cell, (m, n) in agg.items()}


def oof_tolerance_verdicts(preds: list[OOFPrediction]) -> list[ToleranceVerdict]:
    """Pooled-OOF tolerance gate: each cell's mis-route bound vs its per-cell tolerance."""
    return [
        misroute_tolerance_gate(cell, misroutes=m, n=n)
        for cell, (m, n) in sorted(oof_cell_misroutes(preds).items())
    ]
