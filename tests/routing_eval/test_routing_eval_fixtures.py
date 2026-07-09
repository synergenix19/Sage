"""§1 harness — fixture generator: deterministic + adversarial by construction.

The harness's value is that each blocking check is proven to FIRE on a case built
to trip it (the "exercise it, don't declare it" discipline). That requires the
fixture generator to (a) be deterministic for a given seed so the frozen baseline
(§6) is reproducible, and (b) ship adversarial cases, not happy-path ones.
"""
from sage_poc.routing_eval.fixtures import (
    crisis_reaching_scorer,
    crisis_intercepted,
    referral_routed_to_excluded,
    referral_not_routed,
    stratified_set,
)


def test_stratified_set_is_deterministic_for_a_seed():
    a = stratified_set(seed=7)
    b = stratified_set(seed=7)
    assert a == b, "same seed must yield identical fixtures (frozen-baseline reproducibility)"


def test_different_seeds_differ():
    assert stratified_set(seed=7) != stratified_set(seed=8)


def test_crisis_reaching_scorer_is_rigged_to_trip_BC1():
    # A crisis-invariance row whose path WRONGLY reaches skill_select — BC1 must catch this.
    r = crisis_reaching_scorer()
    assert r.case_kind == "crisis_invariance"
    assert r.reached_skill_select is True


def test_crisis_intercepted_is_clean():
    r = crisis_intercepted()
    assert r.case_kind == "crisis_invariance"
    assert r.reached_skill_select is False


def test_referral_routed_to_excluded_is_rigged_to_trip_BC2():
    # A referral-exclusion row whose top candidate is an excluded referral skill — BC2 must catch.
    r = referral_routed_to_excluded()
    assert r.case_kind == "referral_exclusion"
    top_skill = r.scored_candidates[0][0]
    assert top_skill in {"psychotic_referral", "post_crisis_check_in"}


def test_referral_not_routed_is_clean():
    r = referral_not_routed()
    assert r.case_kind == "referral_exclusion"
    assert r.scored_candidates[0][0] not in {"psychotic_referral", "post_crisis_check_in"}


def test_stratified_set_covers_all_lang_stratum_cells():
    recs = stratified_set(seed=7)
    cells = {(r.lang, r.stratum) for r in recs}
    for lang in ("en", "ar"):
        for stratum in ("in_scope", "id_oos", "far_oos"):
            assert (lang, stratum) in cells, f"missing cell {(lang, stratum)}"


def test_stratified_set_includes_an_underpowered_cell():
    # At least one (lang,stratum) held-out cell has too few rows for a stable verdict —
    # this is what proves BC3 returns insufficient_to_assert rather than a silent pass.
    recs = [r for r in stratified_set(seed=7) if r.held_out]
    from collections import Counter
    counts = Counter((r.lang, r.stratum) for r in recs)
    assert min(counts.values()) < 5, "need an underpowered cell to exercise BC3's floor"


def test_stratified_set_includes_degenerate_ar_id_oos():
    # The worst cell must carry hard cases: a near-tie top margin and an override-fired row.
    worst = [r for r in stratified_set(seed=7) if r.lang == "ar" and r.stratum == "id_oos"]
    assert any(r.override_fired for r in worst), "need an override-fired row in ar/id_oos"
    margins = [
        r.scored_candidates[0][1] - r.scored_candidates[1][1]
        for r in worst
        if len(r.scored_candidates) >= 2
    ]
    assert any(m < 0.05 for m in margins), "need a thin-margin (near-tie) row in ar/id_oos"
