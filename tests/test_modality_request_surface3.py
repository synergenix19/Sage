"""EMR Phase 2 surface 3 — offer-reply resolution (Option A, SIGNED).

The measured defect: "are there any exercises i can do" over a pending
[psychoed_anxiety, worry_time] offer was classified offer_ignored and dropped.
Option A (architecture signed 2026-07-28; clinical via the 2026-08-11 A1 pin):
promote-if-member, else route-with-release; released is NEVER declined; the LLM
offer-reply classification applies only when the detector did not fire.
"""
import json

import pytest

from sage_poc import config
from sage_poc.graph import _route_after_intent
from sage_poc.nodes.intent_route import intent_route_node


def _state(msg, offered, *, emr_on=True):
    return {
        "message_en": msg, "raw_message": msg, "detected_language": "en",
        "path": ["safety_check"], "conversation_history": [],
        "offered_skill_ids": offered, "declined_skills": [],
        "clinical_flags": [], "crisis_flags": [],
    }


class _OfferLLM:
    """Classifier stub whose offer_response we control per test."""
    def __init__(self, offer_response=None, choice=None):
        payload = {"primary_intent": "general_chat", "intent_confidence": 0.9,
                   "emotional_intensity": 4, "engagement": 6}
        if offer_response is not None:
            payload["offer_response"] = offer_response
            if choice:
                payload["offer_choice_skill_id"] = choice
        self._content = json.dumps(payload)
    @property
    def _msg(self):
        class _M:  # noqa: N801
            content = self._content
            response_metadata = {}
        return _M()
    async def ainvoke(self, _messages):
        return self._msg


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", True)


@pytest.mark.asyncio
async def test_promote_if_member_hinted(monkeypatch):
    """A breathing request over an offer CONTAINING box_breathing promotes it — the
    existing acceptance path, deterministic, regardless of the LLM's reply reading
    (stub says 'other', which would have released/dropped it)."""
    out = await intent_route_node(
        _state("actually could we do a breathing exercise", ["box_breathing", "worry_time"]),
        llm=_OfferLLM(offer_response="other"))
    assert out["offer_response"] == "accept"
    assert out["offer_choice_skill_id"] == "box_breathing"
    assert "modality_request_routed:offer_reply" in out["path"]
    assert "offer_accepted" in out["path"]
    assert "offer_ignored" not in out["path"]


@pytest.mark.asyncio
async def test_promote_if_member_generic_request_first_line_in_offer(monkeypatch):
    """A generic request over an offer containing a first-line member promotes the
    first binding-order member (spec ordering, not a guess at user choice)."""
    out = await intent_route_node(
        _state("are there any exercises i can do", ["grounding_5_4_3_2_1", "psychoed_anxiety"]),
        llm=_OfferLLM(offer_response="other"))
    assert out["offer_response"] == "accept"
    assert out["offer_choice_skill_id"] == "grounding_5_4_3_2_1"


@pytest.mark.asyncio
async def test_route_with_release_no_member_never_declines(monkeypatch):
    """THE measured defect trajectory: generic request over [psychoed_anxiety,
    worry_time]. No member -> release with the addendum's marker, NOT offer_ignored,
    and released skills never enter declined_skills (reoffer-eligible)."""
    out = await intent_route_node(
        _state("are there any exercises i can do", ["psychoed_anxiety", "worry_time"]),
        llm=_OfferLLM(offer_response="other"))
    assert out["offered_skill_ids"] is None
    assert "offer_released_modality_request" in out["path"]
    assert "offer_ignored" not in out["path"]
    assert "declined_skills" not in out or not out.get("declined_skills")
    assert out.get("offer_response") is None or out.get("offer_response") != "decline"


@pytest.mark.asyncio
async def test_released_turn_routes_to_skill_select_regardless_of_intent(monkeypatch):
    """The router's EMR redirect: the release turn (general_chat by the stub) still
    reaches skill_select, where the binding-table delivery runs."""
    out = await intent_route_node(
        _state("are there any exercises i can do", ["psychoed_anxiety", "worry_time"]),
        llm=_OfferLLM(offer_response="other"))
    route = _route_after_intent({**_state("", None), **out, "active_skill_id": None})
    assert route == "skill_select"


@pytest.mark.asyncio
async def test_genuine_ignore_still_releases_via_llm_path(monkeypatch):
    """Both-direction guard: detector silent ('anyway, about work...') -> the LLM
    path is untouched and a genuine ignore still releases as offer_ignored."""
    out = await intent_route_node(
        _state("anyway, about work, my boss moved the deadline again",
               ["box_breathing", "grounding_5_4_3_2_1"]),
        llm=_OfferLLM(offer_response="other"))
    assert "offer_ignored" in out["path"]
    assert "offer_released_modality_request" not in out["path"]
    assert out["offered_skill_ids"] is None


@pytest.mark.asyncio
async def test_genuine_decline_still_declines_never_reoffered(monkeypatch):
    """Both-direction guard: a real decline (detector silent) still writes
    declined_skills exactly as today."""
    out = await intent_route_node(
        _state("no thanks, not right now", ["box_breathing", "grounding_5_4_3_2_1"]),
        llm=_OfferLLM(offer_response="decline"))
    assert "offer_declined" in out["path"]
    assert set(out["declined_skills"]) == {"box_breathing", "grounding_5_4_3_2_1"}


@pytest.mark.asyncio
async def test_flag_off_llm_path_byte_identical(monkeypatch):
    monkeypatch.setattr(config, "MODALITY_REQUEST_ROUTING_ENABLED", False)
    out = await intent_route_node(
        _state("actually could we do a breathing exercise", ["box_breathing", "worry_time"]),
        llm=_OfferLLM(offer_response="other"))
    assert "modality_request_routed:offer_reply" not in out["path"]
    assert "offer_ignored" in out["path"]           # the LLM's reading stands when OFF


def test_router_redirect_guarded_on_active_skill():
    """Mid-skill requests are surface-1 territory: the redirect never fires with an
    active skill (positive: the skill_continuation branch keeps the executor route)."""
    state = {
        "primary_intent": "skill_continuation", "intent_confidence": 0.9,
        "active_skill_id": "box_breathing",
        "explicit_modality_request": {"requested": True, "modality_hint": None},
        "clinical_flags": [], "crisis_flags": [],
    }
    assert _route_after_intent(state) == "skill_executor"
