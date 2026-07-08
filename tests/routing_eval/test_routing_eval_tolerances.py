"""Per-cell mis-route tolerance (the rule-of-three bound) — three risk profiles, not global.

The clinician's per-cell logic: easy cells (in_scope, far_oos, both langs) -> <=10%; the worst
cell (ar/id_oos, dialect x ID-OOS) -> <=4.6% under Arm A; path-assertion cells (crisis /
harm-to-others / medical-referral) -> NO percentage tolerance (judged by the harm gate). A
single uniform number would silently relax the worst cell to 10% — the F8-shaped error again.

Two separate questions that must NOT collapse: BC3 = "is the cell powered enough to render an
AUGRC parity verdict"; this gate = "is the mis-route point estimate within the cell's bound".
"""
import math

from sage_poc.routing_eval.augrc import CellAUGRC
from sage_poc.routing_eval.blocking_checks import bc3_per_stratum_parity
from sage_poc.routing_eval.tolerances import (
    misroute_tolerance_gate,
    misroute_upper_bound,
    n_floor_for,
    tolerance_for,
)


# --- per-cell config: three profiles -------------------------------------------------

def test_easy_cells_get_10pct_both_languages():
    for cell in (("en", "in_scope"), ("ar", "in_scope"), ("en", "far_oos"), ("ar", "far_oos")):
        assert tolerance_for(*cell) == 0.10


def test_worst_cell_is_tighter_than_easy_cells():
    assert tolerance_for("ar", "id_oos") == 0.046
    assert tolerance_for("ar", "id_oos") < tolerance_for("ar", "in_scope")


def test_path_assertion_cell_has_no_percentage_tolerance():
    # n/a stratum (crisis_invariance / medical_referral / harm-to-others) -> harm gate only
    assert tolerance_for("en", "n/a") is None
    assert tolerance_for("ar", "n/a") is None


# --- N floor is DERIVED from the tolerance (rule of three), not asserted -------------

def test_n_floor_is_three_over_tolerance():
    assert n_floor_for(0.10) == 30           # ceil(3/0.10)
    assert n_floor_for(0.046) == 66          # ceil(3/0.046) ~ 65


# --- the upper bound + the explicit stopping rule -----------------------------------

def test_zero_misroutes_bound_is_rule_of_three():
    assert misroute_upper_bound(0, 66) == math.ceil(0) or abs(misroute_upper_bound(0, 66) - 3/66) < 1e-9


def test_one_misroute_at_65_blows_past_the_worst_cell_bound():
    # the clinician's headline: <=4.6% is NOT a tolerance for one error
    ub = misroute_upper_bound(1, 65)
    assert ub > 0.046, "a single mis-route at N=65 must exceed the 4.6% bound"


def test_worst_cell_passes_at_zero_errors_but_fails_on_one():
    assert misroute_tolerance_gate(("ar", "id_oos"), misroutes=0, n=66).status == "pass"
    assert misroute_tolerance_gate(("ar", "id_oos"), misroutes=1, n=66).status == "fail"


def test_under_derived_floor_is_insufficient_not_pass():
    # 0 errors but only 40 samples — can't yet claim <=4.6%; not a silent pass
    assert misroute_tolerance_gate(("ar", "id_oos"), misroutes=0, n=40).status == "insufficient_n"


def test_path_assertion_cell_returns_no_tolerance_verdict():
    v = misroute_tolerance_gate(("ar", "n/a"), misroutes=3, n=5)
    assert v.status == "no_tolerance"      # judged by the harm gate, not a percentage


# --- the two gates must not collapse into each other --------------------------------

def test_tolerance_and_bc3_are_independent():
    # Same id_oos cells, N well above both floors. Vary ONLY the inputs each gate reads.
    # Case A: 0 mis-routes (tolerance PASS) but AR AUGRC far worse than EN+delta (BC3 FAIL).
    tol_pass = misroute_tolerance_gate(("ar", "id_oos"), misroutes=0, n=70)
    cells_bc3_fail = {("en", "id_oos"): CellAUGRC("en", "id_oos", 70, 0.10),
                      ("ar", "id_oos"): CellAUGRC("ar", "id_oos", 70, 0.40)}
    bc3 = bc3_per_stratum_parity(cells_bc3_fail, delta=0.05, n_floor=30)
    assert tol_pass.status == "pass" and bc3.strata["id_oos"].status == "fail"

    # Case B: 3 mis-routes (tolerance FAIL) but AUGRC parity holds (BC3 PASS).
    tol_fail = misroute_tolerance_gate(("ar", "id_oos"), misroutes=3, n=70)
    cells_bc3_pass = {("en", "id_oos"): CellAUGRC("en", "id_oos", 70, 0.10),
                      ("ar", "id_oos"): CellAUGRC("ar", "id_oos", 70, 0.12)}
    bc3b = bc3_per_stratum_parity(cells_bc3_pass, delta=0.05, n_floor=30)
    assert tol_fail.status == "fail" and bc3b.strata["id_oos"].status == "pass"
