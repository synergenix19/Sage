# tests/test_third_party_span_suppression.py
#
# F1 (code_review.md 2026-08-17): span-scoped third-party crisis suppression.
#
# Spec basis: v7 §5.1 OR-fusion (any crisis signal -> crisis protocol) and
# Intelligence Evaluation T-10 (third-party report ALONE -> no crisis protocol
# for the current user, resources offered; nothing in T-10 licenses suppressing
# a co-occurring first-person disclosure). A third-party match may suppress only
# the direct-crisis match embedded in its own span; every ambiguous case
# (missing span, incomparable surfaces) fails toward crisis.
#
# Assertions anchor on behavior markers (is_safe, flag ids, routing target),
# never on clinical prose, per the assert-on-behavior convention.

import pytest
from unittest.mock import patch

from sage_poc.graph import _route_after_safety
from sage_poc.nodes.safety_check import safety_check_node, _suppressed_by_third_party
from sage_poc.rules.schemas import FiredRule

from tests.test_safety_node_integration import make_state


# ── Direction 1: compound message -> crisis fires (the F1 fix) ────────────────

class TestCompoundDirectPlusThirdParty:
    async def test_compound_en_direct_si_survives_third_party(self):
        # SK-EN-004 span and the passive-SI span are disjoint in this message:
        # the first-person disclosure must survive the third-party suppression.
        state = make_state(
            raw_message=(
                "my sister is suicidal and honestly everyone would be "
                "better off without me"
            )
        )
        result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "Compound message: first-person SI alongside a third-party report "
            "must not be safe (v7 §5.1 OR-fusion / T-10)"
        )
        assert "si_passive" in result["crisis_flags"]
        assert result["third_party_crisis"] is True, (
            "The third-party signal itself must still be recorded"
        )

    async def test_compound_routes_to_crisis(self):
        state = make_state(
            raw_message=(
                "my sister is suicidal and honestly everyone would be "
                "better off without me"
            )
        )
        result = await safety_check_node(state)
        assert _route_after_safety({**state, **result}) == "crisis"


# ── Direction 2: pure third-party byte-stable (regression pin, unchanged) ─────

class TestPureThirdPartyUnchanged:
    async def test_pure_third_party_stays_safe_with_marker(self):
        # T-10: third-party report alone -> no crisis protocol for the current
        # user; the third_party_crisis marker (the composer's resource-guidance
        # key) must be set. This pins the direction the F1 fix does NOT change.
        state = make_state(
            raw_message="my sister is suicidal and I don't know how to support her"
        )
        result = await safety_check_node(state)
        assert result["is_safe"] is True
        assert result["crisis_flags"] == []
        assert result["third_party_crisis"] is True

    async def test_pure_third_party_routes_safe(self):
        state = make_state(
            raw_message="my sister is suicidal and I don't know how to support her"
        )
        result = await safety_check_node(state)
        assert _route_after_safety({**state, **result}) == "safe"


# ── Direction 3: monitoring-phase re-escalation not suppressed ────────────────

class TestMonitoringReescalation:
    async def test_monitoring_compound_reescalates(self):
        # graph.py _route_after_safety monitoring branch reads the same is_safe
        # the wipe corrupted; a third-party mention in a monitoring turn must
        # not mask a co-occurring first-person signal. S7 is mocked RECOVERING
        # so the re-escalation can only come from the surviving S1 flag.
        state = make_state(
            raw_message=(
                "my sister is suicidal and honestly everyone would be "
                "better off without me"
            ),
            crisis_state="monitoring",
        )
        with patch(
            "sage_poc.nodes.safety_check.evaluate_s7",
            return_value=("RECOVERING", "mocked"),
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is False
        assert "si_passive" in result["crisis_flags"]
        assert result["monitoring_clear_turns"] == 0, (
            "A crisis fire must reset the step-down streak"
        )
        assert _route_after_safety({**state, **result}) == "crisis"


# ── Direction 4: cross-surface spans are incomparable -> crisis survives ──────

class TestCrossSurfaceSpans:
    async def test_arabic_direct_si_survives_en_third_party_translation(self):
        # Arabic first-person SI at position 0 of the raw text; the (partial)
        # English translation carries only the third-party clause, so the EN
        # third-party span numerically overlaps the AR-surface SI span.
        # Coordinates from different matched surfaces are not comparable:
        # the AR flag must survive (fail-toward-crisis).
        state = make_state(raw_message="ما عندي سبب اعيش وأختي تريد أن تموت")
        with patch(
            "sage_poc.nodes.safety_check.async_translate_to_english",
            return_value="my sister is suicidal",
        ):
            result = await safety_check_node(state)
        assert result["is_safe"] is False, (
            "AR-surface first-person SI must survive an EN-surface third-party "
            "match; cross-surface span coordinates are incomparable"
        )
        assert "si_passive" in result["crisis_flags"]
        assert result["third_party_crisis"] is True


# ── Fail-toward-crisis tie-breaks (unit level) ────────────────────────────────

def _fr(action_type, flag_id, span, surface):
    return FiredRule(
        rule_id="TEST",
        version="0",
        action={"type": action_type, "flag_id": flag_id},
        matched_span=span,
        matched_surface=surface,
    )


class TestFailTowardCrisisTieBreaks:
    def test_missing_span_on_third_party_does_not_suppress(self):
        si = _fr("crisis_flag", "si_passive", (0, 10), "en")
        tp = _fr("third_party_crisis", "third_party_si", None, "en")
        assert _suppressed_by_third_party(si, [tp]) is False

    def test_missing_span_on_direct_flag_does_not_suppress(self):
        si = _fr("crisis_flag", "si_passive", None, "en")
        tp = _fr("third_party_crisis", "third_party_si", (0, 10), "en")
        assert _suppressed_by_third_party(si, [tp]) is False

    def test_different_surfaces_do_not_suppress(self):
        si = _fr("crisis_flag", "si_passive", (0, 10), "ar")
        tp = _fr("third_party_crisis", "third_party_si", (0, 10), "en")
        assert _suppressed_by_third_party(si, [tp]) is False

    def test_same_surface_containment_suppresses(self):
        si = _fr("crisis_flag", "si_explicit", (3, 15), "en")
        tp = _fr("third_party_crisis", "third_party_si", (0, 20), "en")
        assert _suppressed_by_third_party(si, [tp]) is True

    def test_same_surface_disjoint_does_not_suppress(self):
        si = _fr("crisis_flag", "si_passive", (30, 45), "en")
        tp = _fr("third_party_crisis", "third_party_si", (0, 20), "en")
        assert _suppressed_by_third_party(si, [tp]) is False

    def test_partial_overlap_does_not_suppress(self):
        # Adversarial geometry: the direct match extends past the third-party
        # span. Containment (not any-overlap) governs; ambiguous partial
        # overlap fails toward crisis.
        si = _fr("crisis_flag", "si_explicit", (15, 30), "en")
        tp = _fr("third_party_crisis", "third_party_si", (0, 20), "en")
        assert _suppressed_by_third_party(si, [tp]) is False
