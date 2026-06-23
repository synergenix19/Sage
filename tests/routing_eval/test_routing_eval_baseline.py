"""§6 frozen-baseline management (CRADLE-style): freeze + per-stratum drift detection.

Once a gate-6 baseline is signed it is frozen; CI re-runs the harness and fails the build if
the current result drifts below it. Drift is detected PER (lang × stratum) cell — the fourth
layer at which per-stratum composition is enforced — so a strong English cell can never offset
a regressed Khaleeji ar/id_oos cell. Content-hashed for tamper/version detection.
"""
import json

from sage_poc.routing_eval.baseline import FrozenBaseline, detect_regression, freeze_baseline
from sage_poc.routing_eval.gate_runner import RoutingMetrics

EN = ("en", "in_scope")
AR = ("ar", "id_oos")


def _m(mis, rec, ab, ovr=0):
    return RoutingMetrics(mis, rec, ab, ovr, 50)


def _base():
    return freeze_baseline({EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.62, 0.82)})


def test_freeze_roundtrips_through_json():
    b = _base()
    b2 = FrozenBaseline.from_jsonable(json.loads(json.dumps(b.to_jsonable())))
    assert b2.cells == b.cells


def test_content_hash_is_deterministic_and_changes_on_content_change():
    assert _base().content_hash == _base().content_hash
    changed = freeze_baseline({EN: _m(0.10, 0.70, 0.85), AR: _m(0.20, 0.62, 0.82)})
    assert changed.content_hash != _base().content_hash


def test_no_regression_when_current_matches_frozen():
    b = _base()
    r = detect_regression(b.cells, b)
    assert r.regressed is False and r.cells == {}


def test_regression_when_a_cell_misroute_rises():
    r = detect_regression({EN: _m(0.10, 0.70, 0.85), AR: _m(0.25, 0.62, 0.82)}, _base())
    assert r.regressed is True and "misroute_up" in r.cells[AR]


def test_regression_when_a_cell_recall_drops():
    r = detect_regression({EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.50, 0.82)}, _base())
    assert "recall_down" in r.cells[AR]


def test_per_stratum_one_cell_regresses_even_if_another_improves():
    # EN improves dramatically, AR regresses — must flag AR, not net it out.
    r = detect_regression({EN: _m(0.02, 0.95, 0.97), AR: _m(0.30, 0.50, 0.70)}, _base())
    assert r.regressed is True
    assert AR in r.cells and EN not in r.cells


def test_override_increase_is_a_regression():
    r = detect_regression({EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.62, 0.82, ovr=1)}, _base())
    assert "override_up" in r.cells[AR]


def test_missing_cell_is_flagged_not_silently_ignored():
    r = detect_regression({EN: _m(0.10, 0.70, 0.85)}, _base())   # AR cell gone
    assert "cell_missing" in r.cells[AR]
