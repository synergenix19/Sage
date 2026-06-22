"""§1.4 BC3 (per-stratum parity + per-cell power floor) and BC4 (split-reporting).

BC3 asserts AUGRC[ar][s] <= AUGRC[en][s] + delta per stratum, but renders a binding
verdict only above a per-cell N floor — underpowered cells return insufficient_to_assert,
never a silent pass (H4). BC4 reports 6b-i (abstain-correctness +/- Wald CI) and 6b-ii
(override-mis-route count + rule-of-three upper bound) as SEPARATE numbers, never fused (F2).
"""
import math

from sage_poc.routing_eval.augrc import CellAUGRC
from sage_poc.routing_eval.blocking_checks import bc3_per_stratum_parity, bc4_split_report
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


def _cells(en_augrc, ar_augrc, en_n=10, ar_n=10, stratum="in_scope"):
    return {
        ("en", stratum): CellAUGRC("en", stratum, en_n, en_augrc),
        ("ar", stratum): CellAUGRC("ar", stratum, ar_n, ar_augrc),
    }


# --- BC3 ---------------------------------------------------------------------

def test_bc3_passes_when_ar_within_delta_of_en():
    r = bc3_per_stratum_parity(_cells(0.20, 0.22), delta=0.05, n_floor=8)
    assert r.passed is True
    assert r.strata["in_scope"].status == "pass"


def test_bc3_fails_when_ar_exceeds_en_plus_delta():
    r = bc3_per_stratum_parity(_cells(0.20, 0.30), delta=0.05, n_floor=8)
    assert r.passed is False
    assert r.strata["in_scope"].status == "fail"


def test_bc3_underpowered_cell_is_insufficient_not_pass_and_not_fail():
    # AR cell below the floor: even though 0.21 <= 0.20+0.05 numerically, we cannot assert.
    r = bc3_per_stratum_parity(_cells(0.20, 0.21, ar_n=3), delta=0.05, n_floor=8)
    assert r.strata["in_scope"].status == "insufficient_to_assert"
    assert r.passed is False  # insufficient is never a silent pass


def test_bc3_is_per_stratum_one_fail_blocks_overall():
    cells = {}
    cells.update(_cells(0.20, 0.22, stratum="in_scope"))   # pass
    cells.update(_cells(0.20, 0.40, stratum="id_oos"))     # fail
    r = bc3_per_stratum_parity(cells, delta=0.05, n_floor=8)
    assert r.strata["in_scope"].status == "pass"
    assert r.strata["id_oos"].status == "fail"
    assert r.passed is False


# --- BC4 ---------------------------------------------------------------------

def _ar_idoos(util, top_score, override=False):
    return EvalRecord(
        utterance=util, lang="ar", stratum="id_oos", expected_route=ABSTAIN,
        scored_candidates=((("dbt_tipp", top_score)), ("worry_time", top_score - 0.1)),
        override_fired=override,
    )


def test_bc4_reports_abstain_correctness_and_misroute_as_separate_numbers():
    rows = [
        _ar_idoos("a", 0.40),                 # abstains (correct, top<0.5)
        _ar_idoos("b", 0.60),                 # routes (incorrect abstain)
        _ar_idoos("c", 0.30),                 # abstains (correct)
        _ar_idoos("d", 0.55, override=True),  # covered + override + wrong -> override misroute
    ]
    rep = bc4_split_report(rows, tau=0.50)
    assert rep.n == 4
    # 6b-i: 2 of 4 correctly abstain
    assert rep.abstain_correctness == 0.5
    expected_halfwidth = 1.96 * math.sqrt(0.5 * 0.5 / 4)
    assert math.isclose(rep.ac_ci_high - rep.abstain_correctness, expected_halfwidth, rel_tol=1e-9)
    # 6b-ii: exactly one override misroute — reported separately, NOT folded into 6b-i
    assert rep.override_misroute_count == 1
    # the two are distinct fields; there is no single fused 6b token
    assert not hasattr(rep, "combined_6b")
    assert not hasattr(rep, "passed")


def test_bc4_rule_of_three_upper_bound_when_zero_override_misroutes():
    rows = [_ar_idoos("a", 0.40), _ar_idoos("b", 0.30), _ar_idoos("c", 0.45)]  # no override misroutes
    rep = bc4_split_report(rows, tau=0.50)
    assert rep.override_misroute_count == 0
    assert math.isclose(rep.override_misroute_upper_bound, 3.0 / 3, rel_tol=1e-9)
