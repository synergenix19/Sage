"""§2 calibration: per-route, per-language base thresholds (§5.4 ordering).

Carries two consistency requirements into the code, both already in the spec:
  - C1: 6a/BC3 parity is calibration-INDEPENDENT (curve area over the sweep); the
    calibrated τ feeds only 6b/BC4 point metrics. Locked here by a BC3-invariance test.
  - Fixture-calibrated τ is a TEST ARTIFACT — regenerated, never a frozen constant.
"""
import inspect

from sage_poc.routing_eval.calibration import calibrate_base_thresholds, ThresholdTable
from sage_poc.routing_eval.augrc import CellAUGRC
from sage_poc.routing_eval.blocking_checks import bc3_per_stratum_parity
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


def _rec(lang, route, score, expected, prior=None, held_out=False):
    return EvalRecord(
        utterance=f"{lang}-{route}-{score}-{expected}-{prior}",
        lang=lang,
        stratum="in_scope" if expected != ABSTAIN else "id_oos",
        expected_route=expected,
        scored_candidates=((route, score), ("x", round(score - 0.3, 4))),
        held_out=held_out,
        prior_state=prior,
    )


def _pos(lang, route, score, **kw):  # expected == route (should be covered)
    return _rec(lang, route, score, route, **kw)


def _neg(lang, route, score, **kw):  # route is top but should ABSTAIN (false match)
    return _rec(lang, route, score, ABSTAIN, **kw)


def test_per_route_threshold_separates_positives_from_negatives():
    recs = [
        _pos("en", "box_breathing", 0.70), _pos("en", "box_breathing", 0.66),
        _neg("en", "box_breathing", 0.40), _neg("en", "box_breathing", 0.44),
    ]
    table = calibrate_base_thresholds(recs, min_n=2, cluster_of={})
    tau = table.threshold("en", "box_breathing")
    assert 0.44 < tau <= 0.66, f"τ={tau} must separate negatives (≤0.44) from positives (≥0.66)"


def test_thresholds_are_calibrated_per_language_independently():
    recs = [
        _pos("en", "worry_time", 0.72), _pos("en", "worry_time", 0.70), _neg("en", "worry_time", 0.40),
        _pos("ar", "worry_time", 0.52), _pos("ar", "worry_time", 0.50), _neg("ar", "worry_time", 0.30),
    ]
    t = calibrate_base_thresholds(recs, min_n=2, cluster_of={})
    assert t.threshold("en", "worry_time") > t.threshold("ar", "worry_time"), \
        "EN and AR thresholds must be calibrated independently"


def test_below_min_n_route_falls_back_to_cluster_threshold():
    # box_breathing has only 1 positive (< min_n=2) -> cluster fallback;
    # sleep_hygiene (same cluster) is well-populated and defines the cluster threshold.
    recs = [
        _pos("en", "box_breathing", 0.80),                                   # 1 positive only
        _pos("en", "sleep_hygiene", 0.66), _pos("en", "sleep_hygiene", 0.64),
        _neg("en", "sleep_hygiene", 0.40),
    ]
    cof = {"box_breathing": "relax", "sleep_hygiene": "relax"}
    t = calibrate_base_thresholds(recs, min_n=2, cluster_of=cof)
    assert t.is_fallback("en", "box_breathing"), "sparse route must fall back to cluster"
    assert t.threshold("en", "box_breathing") == t.cluster_threshold("en", "relax")


def test_base_calibration_ignores_state_records():
    # §5.4: base τ is calibrated on prior_state=None ONLY. A state record that would
    # shift τ must be excluded from the base.
    base = [
        _pos("en", "dbt_tipp", 0.70), _pos("en", "dbt_tipp", 0.68),
        _neg("en", "dbt_tipp", 0.40),
    ]
    contaminating_state = [_neg("en", "dbt_tipp", 0.69, prior="active_issues=panic")]  # high FP w/ state
    tau_base = calibrate_base_thresholds(base, min_n=2, cluster_of={}).threshold("en", "dbt_tipp")
    tau_with_state = calibrate_base_thresholds(base + contaminating_state, min_n=2, cluster_of={}).threshold("en", "dbt_tipp")
    assert tau_base == tau_with_state, "state records must not move the base threshold"


def test_bc3_parity_is_independent_of_calibrated_tau():
    # C1: BC3 parity is curve-area, calibration-independent. τ must not leak into it.
    cells = {
        ("en", "in_scope"): CellAUGRC("en", "in_scope", 10, 0.20),
        ("ar", "in_scope"): CellAUGRC("ar", "in_scope", 10, 0.22),
    }
    bc3_before = bc3_per_stratum_parity(cells, delta=0.05, n_floor=8)
    _ = calibrate_base_thresholds(
        [_pos("en", "box_breathing", 0.7)] * 3 + [_neg("en", "box_breathing", 0.4)] * 2,
        min_n=2, cluster_of={},
    )
    bc3_after = bc3_per_stratum_parity(cells, delta=0.05, n_floor=8)
    assert bc3_before == bc3_after, "calibrated τ must not change BC3 parity"
    assert "tau" not in inspect.signature(bc3_per_stratum_parity).parameters, \
        "BC3 must not take τ — parity is calibration-independent by construction"


def test_fixture_tau_is_a_regenerated_artifact_not_a_frozen_constant():
    import sage_poc.routing_eval.calibration as cal
    recs = [_pos("en", "box_breathing", 0.7)] * 3 + [_neg("en", "box_breathing", 0.4)] * 2
    t1 = calibrate_base_thresholds(recs, min_n=2, cluster_of={})
    t2 = calibrate_base_thresholds(recs, min_n=2, cluster_of={})
    assert t1 == t2, "calibration must be deterministic / regenerated"
    frozen = [n for n in dir(cal) if n.isupper() and "THRESHOLD" in n]
    assert frozen == [], f"calibration must not freeze a threshold constant (test artifact only): {frozen}"
