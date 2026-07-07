"""§3 anchor-attribution + anchor-count debias validation.

Attribution surfaces description anchors that won on mis-routes (the §2.1 prune-workflow
input). The debias validation tests whether FP rate correlates with anchor count, gated on
|r| point estimate + bootstrap CI (NOT significance), and returns `insufficient_power`
rather than a false green when the CI is too wide — the N=27 branch, shipping debias
precautionarily. Same idiom as BC3's `insufficient_to_assert`.
"""
from sage_poc.routing_eval.debias import (
    anchor_attribution,
    anchor_count_fp_correlation,
    validate_anchor_debias,
)
from sage_poc.routing_eval.schema import ABSTAIN, EvalRecord


def _won(skill, anchor_type, expected):
    return EvalRecord(
        utterance=f"{skill}-{anchor_type}-{expected}",
        lang="en",
        stratum="in_scope" if expected != ABSTAIN else "id_oos",
        expected_route=expected,
        scored_candidates=((skill, 0.6), ("x", 0.3)),
        winning_anchor_type=anchor_type,
    )


# --- attribution -------------------------------------------------------------

def test_attribution_flags_description_driven_misroutes():
    stats = anchor_attribution([_won("worry_time", "description", ABSTAIN)])
    assert stats["worry_time"].description_misroutes == 1
    assert stats["worry_time"].is_prune_candidate is True


def test_attribution_does_not_flag_exemplar_correct_wins():
    stats = anchor_attribution([_won("box_breathing", "exemplar", "box_breathing")])
    assert stats["box_breathing"].exemplar_wins == 1
    assert stats["box_breathing"].is_prune_candidate is False


# --- correlation -------------------------------------------------------------

def test_correlation_high_when_fp_tracks_anchor_count():
    pts = [(i, i / 10.0) for i in range(1, 11)]
    assert anchor_count_fp_correlation(pts, seed=1).r > 0.9


def test_correlation_low_when_independent():
    pts = [(i % 4, (i // 4 % 5) / 5.0) for i in range(200)]
    assert abs(anchor_count_fp_correlation(pts, seed=1).r) < 0.2


# --- debias validation (incl. the insufficient_power branch) -----------------

def test_debias_pass_when_after_low_and_tight():
    before = [(i, i / 200.0) for i in range(200)]            # high r before
    after = [(i % 4, (i // 4 % 5) / 5.0) for i in range(200)]  # independent → low r, tight CI
    v = validate_anchor_debias(before, after, seed=1)
    assert v.status == "pass"
    assert v.ship_debias is True


def test_debias_fail_when_after_still_correlated():
    after = [(i, i / 100.0) for i in range(100)]             # still perfectly correlated
    v = validate_anchor_debias(after, after, seed=1)
    assert v.status == "fail"
    assert v.ship_debias is False                            # this mechanism is wrong; escalate


def test_debias_insufficient_power_at_small_n_ships_precautionary():
    pts = [(1, 0.1), (2, 0.9), (3, 0.2), (4, 0.8), (5, 0.3), (6, 0.7)]  # N=6 → wide CI
    v = validate_anchor_debias(pts, pts, seed=1)
    assert v.status == "insufficient_power"   # not a false green
    assert v.ship_debias is True              # precautionary, per §6.1 pre-commit
