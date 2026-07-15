"""Tests for the HR-class disclosure routing helper (HR-1 Stage 1 Task 2)
and its wiring into the live routing/skill-select path (Task 3).

hr_disclosure_present is the single source of the "does an HR-class
disclosure route this turn" rule. psychotic_disclosure always routes
(the psychosis path is live in prod); mania/dissociation are gated
behind HIGH_RISK_DETECTION_ENABLED.
"""

import pytest

import sage_poc.config as config
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


# ── Task 3: wiring into _route_after_intent + skill_select_node ───────────────
# Broadens the LIVE psychotic-referral route so mania/dissociation disclosures
# reach the same psychotic_referral terminal, gated by HIGH_RISK_DETECTION_ENABLED.
# Flag OFF must stay byte-identical to today's psychotic-only behaviour.

def _route_state(clinical_flags, **overrides):
    from tests.test_routing import make_full_state
    defaults = dict(
        primary_intent="general_chat",
        intent_confidence=0.9,
        crisis_state="none",
        clinical_flags=clinical_flags,
        active_skill_id=None,
    )
    defaults.update(overrides)
    return make_full_state(**defaults)


def _select_state(clinical_flags, **overrides):
    defaults = {
        "raw_message": "disclosure turn",
        "message_en": "disclosure turn",
        "detected_language": "en",
        "clinical_flags": clinical_flags,
        "crisis_flags": [],
        "is_safe": True,
        "crisis_state": "none",
        "active_skill_id": None,
        "active_step_id": None,
        "primary_intent": "general_chat",
        "path": ["safety_check", "intent_route"],
        "therapeutic_profile": None,
        "turn_number": 2,
        "psychotic_referral_delivered": None,
    }
    defaults.update(overrides)
    return defaults


@pytest.mark.parametrize("flag_name", ["mania_disclosure", "dissociation_disclosure"])
@pytest.mark.asyncio
async def test_flag_on_gated_disclosure_routes_and_auto_selects(flag_name, monkeypatch):
    from sage_poc.graph import _route_after_intent
    from sage_poc.nodes.skill_select import skill_select_node

    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)

    route_state = _route_state([flag_name])
    assert _route_after_intent(route_state) == "skill_select"

    select_state = _select_state([flag_name])
    result = await skill_select_node(select_state)
    assert result["active_skill_id"] == "psychotic_referral"
    assert result["skill_match_method"] == "psychotic_disclosure_auto_select"


@pytest.mark.parametrize("flag_name", ["mania_disclosure", "dissociation_disclosure"])
def test_flag_off_gated_disclosure_does_not_route(flag_name, monkeypatch):
    from sage_poc.graph import _route_after_intent

    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", False)

    route_state = _route_state([flag_name])
    # Falls through unchanged: general_chat, high confidence, no other
    # branch matches -> freeflow (same as any other unrelated clinical flag).
    assert _route_after_intent(route_state) == "freeflow"


@pytest.mark.parametrize("flag_enabled", [True, False])
@pytest.mark.asyncio
async def test_psychotic_disclosure_routes_regardless_of_flag(flag_enabled, monkeypatch):
    from sage_poc.graph import _route_after_intent
    from sage_poc.nodes.skill_select import skill_select_node

    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", flag_enabled)

    route_state = _route_state(["psychotic_disclosure"])
    assert _route_after_intent(route_state) == "skill_select"

    select_state = _select_state(["psychotic_disclosure"])
    result = await skill_select_node(select_state)
    assert result["active_skill_id"] == "psychotic_referral"
    assert result["skill_match_method"] == "psychotic_disclosure_auto_select"


@pytest.mark.parametrize(
    "flag_name", ["psychotic_disclosure", "mania_disclosure", "dissociation_disclosure"]
)
@pytest.mark.asyncio
async def test_delivered_guard_suppresses_reselection_for_all_hr_flags(flag_name, monkeypatch):
    from sage_poc.graph import _route_after_intent
    from sage_poc.nodes.skill_select import skill_select_node

    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)

    route_state = _route_state([flag_name], psychotic_referral_delivered=True)
    assert _route_after_intent(route_state) == "freeflow"

    select_state = _select_state([flag_name], psychotic_referral_delivered=True)
    result = await skill_select_node(select_state)
    assert result.get("active_skill_id") != "psychotic_referral"


# ── Task 4 (Stage 1.5): full-graph red/control drives ────────────────────────
# The four HR presentations named in the design spec's problem statement as previously
# MISSED by the pre-HR-1 graph, driven through the REAL compiled graph (app.ainvoke),
# not just the routing helper/skill_select unit tests above. Mirrors
# tests/test_medical_redflag_guard.py's end-to-end style and reuses
# tests/test_hr_crisis_precedence.py's force-activation/LLM-stub helpers so CF-007/008/009
# (which ship active=false pending clinician ratification, see tests/test_rules_safety_hr.py)
# actually fire inside safety_check_node, and intent_route/freeflow_respond complete
# offline with no OPENROUTER_API_KEY.
#
# psychotic_referral is a one-step skill that always completes in the turn it is
# selected (see skill_executor's psychotic_referral_delivered NOTE), so by the time
# app.ainvoke reaches END, active_skill_id has already been cleared back to None --
# that is the skill's normal completed state. completed_skill_id / skill_match_method /
# psychotic_referral_delivered are the correct end-of-graph markers that the referral
# fired this turn (same reasoning as test_hr_crisis_precedence.py's dissociation-only case).

from tests.test_hr_crisis_precedence import (  # noqa: E402
    _force_activate_hr_rules,
    _stub_intent_and_responder_llms,
)

_HR_RED_DRIVES = [
    "People are following me and watching me",
    "I haven't slept for days but I feel amazing and unstoppable",
    "I think people are reading my thoughts",
    "I feel completely detached from reality, nothing feels real",
]

# Must-NOT-fire controls (verbatim from tests/test_rules_safety_hr.py's control list):
# grief, panic-derealization, an everyday idiom, and ordinary excitement, each a close
# lexical neighbour of a real HR trigger phrase. None carry an HR clinical flag even
# with CF-007/008/009 force-activated (see test_rules_safety_hr.py's own control tests);
# this block additionally proves that full-graph routing follows through, all the way
# to the referral, never firing on them either.
_HR_CONTROLS = [
    "nothing's felt real since the funeral",
    "everything felt unreal during the panic attack",
    "this promotion doesn't feel real",
    "I have so much energy today after the gym",
]


@pytest.mark.parametrize("drive", _HR_RED_DRIVES)
@pytest.mark.asyncio
async def test_full_graph_red_drive_reaches_psychotic_referral_flag_on(drive, monkeypatch):
    _force_activate_hr_rules(monkeypatch)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)
    _stub_intent_and_responder_llms(monkeypatch)

    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": drive, "path": []},
        config={"configurable": {"thread_id": f"hr4-red-on-{hash(drive)}"}},
    )

    assert result.get("skill_match_method") == "psychotic_disclosure_auto_select", drive
    assert result.get("completed_skill_id") == "psychotic_referral", drive
    assert result.get("psychotic_referral_delivered") is True, drive


@pytest.mark.parametrize("drive", _HR_RED_DRIVES)
@pytest.mark.asyncio
async def test_full_graph_red_drive_gets_current_offer_flag_off(drive, monkeypatch):
    """Flag OFF -- and CF-007/008/009 NOT force-activated, i.e. today's actual shipped
    rule set (active=false) -- reproduces the real pre-HR-1 baseline exactly: none of
    the four drives reach the referral. This is what "proves the gate": Task 1-3's
    detection+routing is what closes the gap, not some other side effect of this test
    file. Each drive still gets whatever the existing graph does for it today (an
    offer, general_chat freeflow, etc.) -- this test only pins that it is NOT the
    referral, not what the alternative is.
    """
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", False)
    _stub_intent_and_responder_llms(monkeypatch)

    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": drive, "path": []},
        config={"configurable": {"thread_id": f"hr4-red-off-{hash(drive)}"}},
    )

    assert result.get("skill_match_method") != "psychotic_disclosure_auto_select", drive
    assert result.get("completed_skill_id") != "psychotic_referral", drive
    assert not result.get("psychotic_referral_delivered"), drive


@pytest.mark.parametrize("control", _HR_CONTROLS)
@pytest.mark.asyncio
async def test_full_graph_control_never_reaches_psychotic_referral(control, monkeypatch):
    _force_activate_hr_rules(monkeypatch)
    monkeypatch.setattr(config, "HIGH_RISK_DETECTION_ENABLED", True)
    _stub_intent_and_responder_llms(monkeypatch)

    from sage_poc.graph import build_graph
    app = build_graph()
    result = await app.ainvoke(
        {"raw_message": control, "path": []},
        config={"configurable": {"thread_id": f"hr4-control-{hash(control)}"}},
    )

    assert result.get("skill_match_method") != "psychotic_disclosure_auto_select", control
    assert result.get("completed_skill_id") != "psychotic_referral", control
    assert not result.get("psychotic_referral_delivered"), control
