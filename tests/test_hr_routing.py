"""Tests for the HR-class disclosure routing helper (HR-1 Stage 1 Task 2).

hr_disclosure_present is the single source of the "does an HR-class
disclosure route this turn" rule. psychotic_disclosure always routes
(the psychosis path is live in prod); mania/dissociation are gated
behind HIGH_RISK_DETECTION_ENABLED.
"""

from sage_poc.safety.hr_disclosure import hr_disclosure_present


def test_psychotic_disclosure_always_routes_even_flag_off():
    assert hr_disclosure_present(["psychotic_disclosure"], flag_enabled=False) is True


def test_mania_disclosure_gated_off():
    assert hr_disclosure_present(["mania_disclosure"], flag_enabled=False) is False


def test_mania_disclosure_routes_when_flag_enabled():
    assert hr_disclosure_present(["mania_disclosure"], flag_enabled=True) is True


def test_dissociation_disclosure_routes_when_flag_enabled():
    assert hr_disclosure_present(["dissociation_disclosure"], flag_enabled=True) is True


def test_dissociation_disclosure_gated_off():
    assert hr_disclosure_present(["dissociation_disclosure"], flag_enabled=False) is False


def test_empty_flags_never_routes():
    assert hr_disclosure_present([], flag_enabled=True) is False


def test_none_flags_treated_as_empty():
    assert hr_disclosure_present(None, flag_enabled=True) is False


def test_psychotic_plus_mania_routes_on_psychotic_alone():
    assert (
        hr_disclosure_present(
            ["psychotic_disclosure", "mania_disclosure"], flag_enabled=False
        )
        is True
    )
