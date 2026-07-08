"""Calibrated-V2 behavior #4: crisis-guardrail — enforce frozen ABSTAIN dispositions.

Architecture (mechanism mine / policy theirs): the safety lane DECLARES which clinical flags
carry skill_select_disposition: "abstain" on the flag definitions (clinical_flag_patterns.json);
skill_select is a pure CONSUMER. Under flag-on, if Node 1 set a clinical flag whose declared
disposition is "abstain", skill_select defers (no skill) — a flagged crisis-adjacent disclosure
isn't routed to a self-help skill even if it would score above threshold. A flag with NO declared
disposition routes as V1 (safe no-op default). Flag-off untouched. #4 does NOT detect crisis —
acute crisis is Node 1's job, intercepted upstream (BC1).

Seeded policy: substance_use → abstain (the one signed disposition: SBIRT-positive, refer, don't
coach). The other clinical flags are undeclared and route as V1 until the crisis sprint signs them.
"""
import pytest

from sage_poc.nodes import skill_select as ss


def _state(**kw):
    base = {
        "raw_message": "", "detected_language": "en", "message_en": "",
        "primary_intent": None, "crisis_state": "none", "clinical_flags": [],
        "active_skill_id": None, "offered_skill_ids": None, "offer_response": None,
        "therapeutic_profile": None, "path": [],
    }
    base.update(kw)
    return base


# --- the declaration is read by reference, seeded with the one signed entry -----------------

def test_substance_use_disposition_is_declared_abstain_in_flag_definitions():
    assert ss._flag_dispositions().get("substance_use") == "abstain"


def test_undeclared_flags_have_no_disposition_route_as_v1():
    disp = ss._flag_dispositions()
    for f in ("trauma_indicator", "eating_concern", "medication_mention"):
        assert disp.get(f) is None  # crisis sprint owns these; until signed, they route as V1


# --- the consumer mechanism --------------------------------------------------------------

@pytest.mark.asyncio
async def test_flag_on_substance_use_flagged_turn_abstains(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    # keyword-routable message; flag is what forces the defer, not the content
    result = await ss.skill_select_node(_state(
        message_en="i want to do some box breathing", clinical_flags=["substance_use"]))
    assert result.get("active_skill_id") is None
    assert not result.get("offered_skill_ids")           # pure freeflow, no offer
    assert "clinical_flag_abstain" in result["path"]     # auditable deferral reason


@pytest.mark.asyncio
async def test_flag_on_undeclared_flag_routes_as_v1(monkeypatch):
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    result = await ss.skill_select_node(_state(
        message_en="i want to do some box breathing", clinical_flags=["medication_mention"]))
    # undeclared flag does not defer -> routing proceeds (keyword match present)
    routed = result.get("active_skill_id") or result.get("offered_skill_ids")
    assert routed, "an undeclared flag must route as V1, not abstain"


@pytest.mark.asyncio
async def test_same_direction_substance_routes_flag_off_abstains_flag_on(monkeypatch):
    st = dict(message_en="i want to do some box breathing", clinical_flags=["substance_use"])
    monkeypatch.setenv("SKILL_ROUTING_V2", "0")
    off = await ss.skill_select_node(_state(**st))
    monkeypatch.setenv("SKILL_ROUTING_V2", "1")
    on = await ss.skill_select_node(_state(**st))
    routed_off = off.get("active_skill_id") or off.get("offered_skill_ids")
    routed_on = on.get("active_skill_id") or on.get("offered_skill_ids")
    assert routed_off, "flag-off must route as V1 (the bug #4 fixes)"
    assert not routed_on, "flag-on must defer the signed substance disposition"
