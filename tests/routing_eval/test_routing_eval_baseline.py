"""§6 frozen-baseline management (CRADLE-style): freeze + per-stratum drift detection.

Once a gate-6 baseline is signed it is frozen; CI re-runs the harness and fails the build if
the current result drifts below it. Drift is detected PER (lang × stratum) cell — the fourth
layer at which per-stratum composition is enforced — so a strong English cell can never offset
a regressed Khaleeji ar/id_oos cell. Content-hashed for tamper/version detection.
"""
import json

import pytest

from sage_poc.routing_eval.baseline import (
    FrozenBaseline,
    UnresolvedDispositionError,
    check_freeze_readiness,
    detect_regression,
    freeze_baseline,
)
from sage_poc.routing_eval.gate_runner import RoutingMetrics
from sage_poc.routing_eval.schema import EvalRecord

EN = ("en", "in_scope")
AR = ("ar", "id_oos")


def _m(mis, rec, ab, ovr=0):
    return RoutingMetrics(mis, rec, ab, ovr, 50)


def _rec(lang="en", stratum="id_oos", disposition="settled", held_out=True):
    return EvalRecord(utterance="x", lang=lang, stratum=stratum, expected_route="ABSTAIN",
                      disposition=disposition, held_out=held_out)


def _base():
    # No unresolved dispositions -> freezes cleanly. Empty records is an explicit "nothing to gate".
    return freeze_baseline({EN: _m(0.10, 0.70, 0.85), AR: _m(0.15, 0.62, 0.82)}, [])


def test_freeze_roundtrips_through_json():
    b = _base()
    b2 = FrozenBaseline.from_jsonable(json.loads(json.dumps(b.to_jsonable())))
    assert b2.cells == b.cells


def test_content_hash_is_deterministic_and_changes_on_content_change():
    assert _base().content_hash == _base().content_hash
    changed = freeze_baseline({EN: _m(0.10, 0.70, 0.85), AR: _m(0.20, 0.62, 0.82)}, [])
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


# --- freeze-honesty: a borderline_pending row must BLOCK freeze (not just be remembered) ----

def test_freeze_refuses_a_cell_with_a_borderline_pending_disposition():
    recs = [_rec("en", "id_oos", "borderline_pending"), _rec("en", "id_oos", "settled")]
    with pytest.raises(UnresolvedDispositionError) as exc:
        freeze_baseline({EN: _m(0.10, 0.70, 0.85)}, recs)
    assert ("en", "id_oos") in exc.value.readiness.unresolved


def test_freeze_succeeds_when_every_disposition_is_settled():
    recs = [_rec("en", "id_oos", "settled"), _rec("ar", "in_scope", "settled")]
    b = freeze_baseline({EN: _m(0.10, 0.70, 0.85)}, recs)
    assert b.cells == {EN: _m(0.10, 0.70, 0.85)}


def test_check_freeze_readiness_reports_only_the_unresolved_cell():
    recs = [_rec("en", "id_oos", "borderline_pending"), _rec("ar", "far_oos", "settled")]
    fr = check_freeze_readiness(recs)
    assert fr.ready is False
    assert ("en", "id_oos") in fr.unresolved and ("ar", "far_oos") not in fr.unresolved


def test_non_heldout_borderline_row_does_not_block_freeze():
    # the freeze gate concerns the held-out eval cells; a non-held-out borderline row is not one
    fr = check_freeze_readiness([_rec("en", "id_oos", "borderline_pending", held_out=False)])
    assert fr.ready is True
