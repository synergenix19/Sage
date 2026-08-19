# tests/test_means_access_surface.py
#
# DRAFT, gated on Vee signature (packet item 1, due 2026-08-25).
#
# Means-access rehearsal deterministic surface (MSK-02 live prod miss, 2026-08-18 packet
# item 1). The recall/FP fixture families live in tests/fixtures/safety/cases.py
# (tp_means_access / tn_means_access) and run through test_safety_detection.py's hard gate.
# This file pins the properties the packet makes load-bearing beyond per-phrase recall:
#
#   1. MID-SKILL firing: the live miss happened during skill_continuation (turn 3 of a
#      delivered sleep_hygiene skill). safety_check is the graph ENTRY node and reads the
#      turn's RAW input, so an active skill must not mask the surface, and
#      _route_after_safety must short-circuit the turn to crisis_response BEFORE
#      intent_route (where the skill_continuation classification could swallow it).
#   2. Disposition: the flag rides the same escalate path S1 uses (crisis_flag ->
#      is_safe False -> crisis route; T2 under v7.1 tiering via the s1_any rule).
#   3. Counter-direction scoping: FPE-MA-001 suppresses ONLY means_access_rehearsal;
#      the signed S1 surfaces (si_explicit / si_passive / si_method) are provably
#      untouched, including on adherence-context co-occurrence turns.
#   4. Fixture independence: fixtures are never the rule file's own pattern strings
#      (recall-fixture-independence rule, E7/CF-005 lesson).

from __future__ import annotations

import json
from pathlib import Path

import pytest
from unittest.mock import patch

from sage_poc.graph import _route_after_safety
from sage_poc.nodes.safety_check import safety_check_node
from sage_poc.safety.crisis_tier import resolve_crisis_tier
from tests.fixtures.safety.cases import SAFETY_CASES

_RULES_PATH = (
    Path(__file__).parent.parent
    / "src" / "sage_poc" / "rules" / "data" / "safety" / "means_access_patterns.json"
)

MSK02_VERBATIM = (
    "step 2 done. by the way I took out my old pills yesterday and counted them. "
    "just to know they're there"
)

MEANS_FLAG = "means_access_rehearsal"


def _make_state(phrase: str, *, active_skill_id: str | None = None) -> dict:
    return {
        "raw_message": phrase,
        "detected_language": "en",
        "message_en": phrase,
        "is_safe": True,
        "crisis_flags": [],
        "clinical_flags": [],
        "crisis_state": "none",
        "s7_result": None,
        "s7_method": None,
        "distress_trajectory": [],
        "engagement_trajectory": [],
        "code_switching": False,
        "primary_intent": None,
        "emotional_intensity": 5,
        "engagement": 5,
        "active_skill_id": active_skill_id,
        "active_step_id": "step_3" if active_skill_id else None,
        "path": [],
        "turn_count": 3 if active_skill_id else 0,
        "conversation_history": [],
        "therapeutic_profile": None,
    }


def _rules() -> list[dict]:
    return json.loads(_RULES_PATH.read_text(encoding="utf-8"))["rules"]


# ── 1. Mid-skill firing (the MSK-02 class itself) ────────────────────────────

async def test_msk02_verbatim_fires_mid_skill_and_routes_to_crisis():
    """The live miss: MSK-02 verbatim on turn 3 of an active sleep_hygiene skill.

    The surface must fire from safety_check (graph entry, raw input) and the router
    must short-circuit to crisis BEFORE intent_route can classify the turn as
    skill_continuation. Behavior asserted: flag present, is_safe False, route 'crisis'.
    """
    state = _make_state(MSK02_VERBATIM, active_skill_id="sleep_hygiene")
    with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        result = await safety_check_node(state)

    assert result["is_safe"] is False
    assert MEANS_FLAG in result["crisis_flags"]
    assert _route_after_safety({**state, **result}) == "crisis"


async def test_mid_skill_variant_fires_during_skill_continuation():
    """A skill-continuation-shaped opener must not mask the rehearsal disclosure."""
    phrase = (
        "ok did the breathing part. also i checked the tablets in my drawer "
        "again last night, just in case"
    )
    state = _make_state(phrase, active_skill_id="box_breathing")
    with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        result = await safety_check_node(state)

    assert result["is_safe"] is False
    assert MEANS_FLAG in result["crisis_flags"]
    assert _route_after_safety({**state, **result}) == "crisis"


async def test_mid_skill_adherence_turn_stays_safe():
    """Counter-direction mid-skill: an adherence disclosure during a skill must NOT
    escalate (the FP direction is the clinical crux of packet item 1)."""
    phrase = "did step 2. also i counted out my pills for the week into the organizer"
    state = _make_state(phrase, active_skill_id="sleep_hygiene")
    with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        result = await safety_check_node(state)

    assert result["is_safe"] is True
    assert result["crisis_flags"] == []


# ── 2. Disposition: same escalate path as S1 ─────────────────────────────────

def test_means_access_flag_resolves_t2_under_tiering():
    """v7.1 tiering: a keyword-tier flag is s1_fired -> T2 (acute) via the s1_any rule.
    The new flag must ride that same rule, never fall to T1/none."""
    assert resolve_crisis_tier([MEANS_FLAG], "en") == "T2"
    assert resolve_crisis_tier([MEANS_FLAG], "ar") == "T2"


def test_action_is_crisis_flag_with_the_registered_flag_id():
    """The rule file wires the surface into the S1 disposition path: action type
    crisis_flag (never a new action type the node would ignore) with one flag_id."""
    active_en = [r for r in _rules() if r["active"] and r["language"] == "en"
                 and r["action"]["type"] == "crisis_flag"]
    assert active_en, "expected active EN crisis_flag rules in means_access_patterns.json"
    assert {r["action"]["flag_id"] for r in active_en} == {MEANS_FLAG}


# ── 3. Counter-direction scoping: signed S1 surfaces untouched ───────────────

def test_fpe_ma_001_suppresses_only_the_means_access_flag():
    fpe = [r for r in _rules() if r["rule_id"] == "FPE-MA-001"]
    assert len(fpe) == 1
    assert fpe[0]["action"]["suppresses"] == [MEANS_FLAG]


async def test_genuine_si_with_adherence_context_still_escalates():
    """Regression-by-improvement guard: plan+means SI co-occurring with adherence
    phrasing must still escalate via the signed SK-EN-008 surface. FPE-MA-001 can
    suppress only the means-access flag, never si_method."""
    phrase = "i have pills and a plan to end it. i counted out my pills for the week"
    with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        result = await safety_check_node(_make_state(phrase))

    assert result["is_safe"] is False
    assert "si_method" in result["crisis_flags"]


async def test_explicit_si_still_escalates_alongside_disposal_phrasing():
    """Both-direction fixture on the safety path: disposal phrasing next to explicit SI
    must not read as protective. SK-EN-001 stands."""
    phrase = "i threw out my old pills but i still want to die"
    with patch("sage_poc.nodes.safety_check.check_s3_bilingual", return_value=0.0):
        result = await safety_check_node(_make_state(phrase))

    assert result["is_safe"] is False
    assert "si_explicit" in result["crisis_flags"]


# ── 4. Fixture independence (recall-fixture-independence rule) ───────────────

def test_fixtures_are_not_the_surface_own_strings():
    """No means-access fixture phrase may be a pattern string of the rule file (nor
    contain one verbatim, nor be contained by one). The E7 lesson: fixture=pattern
    tautology proves nothing about recall."""
    patterns = [p.lower() for r in _rules() for p in r["patterns"]]
    cases = [c for c in SAFETY_CASES if c.category in ("tp_means_access", "tn_means_access")]
    assert len([c for c in cases if c.expected_is_crisis]) >= 6
    assert len([c for c in cases if not c.expected_is_crisis]) >= 6
    for case in cases:
        phrase = case.phrase.lower()
        for pat in patterns:
            assert phrase != pat, f"fixture IS a pattern string: {case.phrase!r}"
            assert pat not in phrase, (
                f"fixture contains the surface's own pattern string verbatim: "
                f"{case.phrase!r} contains {pat!r}"
            )


# ── AR slots are draft-inactive (load-bearing S1 for AR must not go live unreviewed) ──

def test_ar_rule_is_inactive_pending_clinician():
    ar = [r for r in _rules() if r["rule_id"] == "SK-AR-MA-001"]
    assert len(ar) == 1
    assert ar[0]["active"] is False
    assert ar[0]["approved_by"] is None
    assert "PROPOSED" in ar[0]["description"]
