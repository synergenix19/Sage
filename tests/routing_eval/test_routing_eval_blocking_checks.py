"""§1.4 blocking checks BC1 (crisis-path-invariance) + BC2 (referral-exclusion).

The first thing proven for each check is that it FIRES on a case built to trip it —
a guardrail never observed to hard-fail is an unverified guardrail wearing a green check.
"""
from sage_poc.routing_eval.fixtures import (
    crisis_reaching_scorer,
    crisis_intercepted,
    referral_routed_to_excluded,
    referral_not_routed,
)
from sage_poc.routing_eval.blocking_checks import (
    bc1_crisis_path_invariance,
    bc2_referral_exclusion,
)


# --- BC1 fires ---------------------------------------------------------------

def test_bc1_fails_when_a_crisis_row_reached_skill_select():
    result = bc1_crisis_path_invariance([crisis_reaching_scorer()])
    assert result.passed is False
    assert "crisis-invariance-reached" in {r.utterance for r in result.offending}


def test_bc1_passes_when_crisis_intercepted():
    result = bc1_crisis_path_invariance([crisis_intercepted()])
    assert result.passed is True
    assert result.offending == ()


def test_bc1_ignores_non_crisis_rows():
    # A normal row that reached the scorer is fine — BC1 only governs crisis_invariance.
    from sage_poc.routing_eval.fixtures import stratified_set
    result = bc1_crisis_path_invariance(stratified_set(seed=1))
    assert result.passed is True


# --- BC2 fires ---------------------------------------------------------------

def test_bc2_fails_when_referral_row_routes_to_excluded_skill():
    result = bc2_referral_exclusion([referral_routed_to_excluded()])
    assert result.passed is False
    assert "referral-routed" in {r.utterance for r in result.offending}


def test_bc2_passes_when_referral_row_routes_elsewhere():
    result = bc2_referral_exclusion([referral_not_routed()])
    assert result.passed is True
    assert result.offending == ()
